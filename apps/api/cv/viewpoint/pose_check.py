# -*- coding: utf-8 -*-
"""viewpoint/pose_check.py — Uji awal MediaPipe Pose pada foto back-view (Fase 0).

Mengukur detection rate landmark (bahu/kepala) per viewpoint, untuk memutuskan
apakah MediaPipe cukup andal sebagai basis gate.

Gate: shoulder_rate(back) >= 0.70 DAN head_rate >= 0.80 -> LULUS.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\pose_check.py --per-view 30
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import CV_DIR, POSE_MODEL, POSE_MODEL_HEAVY, SEED
from common.io_utils import load_json, save_json

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground_truth"
REPORTS = HERE / "reports"
FIGURES = REPORTS / "figures"

VIEWPOINT_SOURCES = [
    GT_DIR / "viewpoint_verification_A.json",
    CV_DIR / "annotation" / "ground_truth" / "_archive_annotator_A_p240_v2.json",
]
BACK_VP = {"back", "back_left", "back_right", "belakang"}

POSE_MODELS = {"lite": POSE_MODEL, "heavy": POSE_MODEL_HEAVY}
LM = {"nose": 0, "ear_L": 7, "ear_R": 8, "shoulder_L": 11, "shoulder_R": 12}


def make_landmarker(model_path: Path, min_det: float = 0.3):
    opts = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE, num_poses=1,
        min_pose_detection_confidence=min_det, min_pose_presence_confidence=min_det,
        output_segmentation_masks=False,
    )
    return vision.PoseLandmarker.create_from_options(opts)


def extract_landmarks(landmarker, img_path: Path, v_min: float, coord_tol: float = 0.15) -> dict:
    try:
        im = Image.open(img_path).convert("RGB")
    except Exception as exc:
        return {"error": f"load_fail: {exc}", "shoulder_ok": False, "head_ok": False}
    arr = np.asarray(im)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
    try:
        res = landmarker.detect(mp_img)
    except Exception as exc:
        return {"error": f"detect_fail: {exc}", "shoulder_ok": False, "head_ok": False}
    if not res.pose_landmarks:
        return {"error": "no_pose", "shoulder_ok": False, "head_ok": False}

    lm = res.pose_landmarks[0]

    def get(idx):
        p = lm[idx]
        return {"x": float(p.x), "y": float(p.y), "vis": float(p.visibility)}

    lms = {k: get(v) for k, v in LM.items()}

    def vis(name):
        p = lms[name]
        return (p["vis"] >= v_min and -coord_tol <= p["x"] <= 1 + coord_tol and -coord_tol <= p["y"] <= 1 + coord_tol)

    shoulder_ok = vis("shoulder_L") and vis("shoulder_R")
    head_ok = any(vis(c) for c in ("ear_L", "ear_R", "nose"))
    out = {"shoulder_ok": shoulder_ok, "head_ok": head_ok, "ears_ok": vis("ear_L") and vis("ear_R")}
    if shoulder_ok:
        out["W_shoulder_norm"] = round(abs(lms["shoulder_L"]["x"] - lms["shoulder_R"]["x"]), 4)
    return out


def summarize(records: list[dict]) -> dict:
    by = defaultdict(list)
    for r in records:
        by[r["view_group"]].append(r)
    out = {}
    for vg, rows in sorted(by.items()):
        n = len(rows)
        sh = sum(1 for r in rows if r.get("shoulder_ok"))
        hd = sum(1 for r in rows if r.get("head_ok"))
        out[vg] = {"n": n, "shoulder_ok": sh, "shoulder_rate": round(sh / n, 4) if n else None,
                   "head_ok": hd, "head_rate": round(hd / n, 4) if n else None}
    return out


def decide_gate(summary: dict, sh_thr=0.70, head_thr=0.80) -> dict:
    back = summary.get("back", {})
    sr, hr = back.get("shoulder_rate"), back.get("head_rate")
    if sr is None and hr is None:
        return {"status": "NO_DATA"}
    if sr is not None and sr >= sh_thr and (hr or 0) >= head_thr:
        status = "LULUS"
    elif hr is not None and hr >= head_thr:
        status = "LULUS_P4_HEAD"
    elif sr is not None and sr >= 0.50:
        status = "KONDISIONAL"
    else:
        status = "PIVOT"
    return {"status": status, "shoulder_back_rate": sr, "head_back_rate": hr,
            "shoulder_threshold": sh_thr, "head_threshold": head_thr}


def main():
    ap = argparse.ArgumentParser(description="Fase 0: uji MediaPipe Pose back-view.")
    ap.add_argument("--per-view", type=int, default=30)
    ap.add_argument("--v-min", type=float, default=0.5)
    ap.add_argument("--min-det", type=float, default=0.3)
    ap.add_argument("--model", default="lite", choices=["lite", "heavy"])
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=str(REPORTS / "pose_feasibility.json"))
    args = ap.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)

    # kumpulkan viewpoint map
    vp_map = {}
    for src in VIEWPOINT_SOURCES:
        if src.exists():
            data = load_json(src)
            recs = data if isinstance(data, list) else data.get("records", [])
            for r in recs:
                iid, vp = r.get("image_id"), r.get("viewpoint")
                if iid and vp:
                    vp_map.setdefault(iid, vp)

    if not vp_map:
        print("ERROR: tak ada anotasi viewpoint.")
        return

    import random
    rng = random.Random(args.seed)
    by_view = defaultdict(list)
    for iid, vp in vp_map.items():
        by_view[vp].append(iid)
    sample = {}
    for vp, ids in by_view.items():
        ids = sorted(ids); rng.shuffle(ids); sample[vp] = ids[: args.per_view]

    print(f"=== Fase 0: pose_check ===\ndataset: {CV_DIR/'dataset'}")
    model_path = POSE_MODELS.get(args.model, POSE_MODEL)
    lk = make_landmarker(model_path, args.min_det)

    def grp(vp):
        return "back" if vp in BACK_VP else ("front" if vp == "front" else ("side" if vp == "side" else "unknown"))

    records = []
    for vp, ids in sorted(sample.items()):
        for iid in ids:
            p = CV_DIR / iid.replace("figaro1k/", "dataset/figaro1k/", 1)
            if not p.exists():
                continue
            r = extract_landmarks(lk, p, args.v_min)
            r.update({"image_id": iid, "viewpoint_annotated": vp, "view_group": grp(vp)})
            records.append(r)
    lk.close()

    summary = summarize(records)
    gate = decide_gate(summary)
    save_json(args.out, {
        "phase": "0_pose_feasibility", "model": args.model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_total": len(records), "summary_by_viewpoint": summary, "gate": gate,
        "error_counts": dict(Counter(r.get("error") for r in records if r.get("error"))),
        "records": records,
    })
    print(f"\n{'viewpoint':10s} {'n':>4s} {'shoulder':>9s} {'head':>7s}")
    for vg, s in summary.items():
        print(f"{vg:10s} {s['n']:>4d} {s['shoulder_rate']:>9.3f} {s['head_rate']:>7.3f}")
    print(f"\nGATE: {gate['status']} (shoulder_back={gate.get('shoulder_back_rate')})")
    print(f"Report -> {args.out}")


if __name__ == "__main__":
    main()
