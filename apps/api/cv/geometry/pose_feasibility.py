# -*- coding: utf-8 -*-
"""FASE 0 — Verifikasi Gate: Uji MediaPipe Pose pada foto back-view.

Tujuan: membuktikan secara empiris apakah landmark anatomi (khususnya BAHU)
dapat dideteksi andal pada foto back-view. Ini gerbang kritis sebelum
membangun pipeline geometris.

Mengukur:
  - Detection rate landmark bahu (kiri & kanan) per viewpoint
  - Detection rate landmark kepala (telinga/hidung)
  - Stabilitas rasio head:shoulder (koefisien variasi)
  - Perbandingan detection rate antar-viewpoint (back / front / side)

Gate: shoulder_rate(back) >= 0.70 DAN head_rate >= 0.80 -> LULUS

Sumber model pose:
  weights/pose_landmarker_lite.task (diunduh otomatis bila tidak ada)

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" geometry\\pose_feasibility.py --help
  & ".venv\\Scripts\\python.exe" geometry\\pose_feasibility.py
  & ".venv\\Scripts\\python.exe" geometry\\pose_feasibility.py --per-view 15 --v-min 0.5

Isolated: hanya menulis ke geometry/reports/. Tidak menyentuh scripts/ lama.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

# MediaPipe Tasks (versi 1.x tidak punya legacy solutions)
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
BASE = Path(__file__).resolve().parents[1]          # apps/api/cv
DATASET = BASE / "dataset" / "figaro1k"
WEIGHTS = BASE / "weights"
GEO_DIR = Path(__file__).resolve().parents[0]        # apps/api/cv/geometry
REPORTS = GEO_DIR / "reports"
FIGURES = REPORTS / "figures"

POSE_MODEL = WEIGHTS / "pose_landmarker_lite.task"
POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
POSE_MODELS = {
    "lite": (
        WEIGHTS / "pose_landmarker_lite.task",
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
    ),
    "full": (
        WEIGHTS / "pose_landmarker_full.task",
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_full/float16/1/pose_landmarker_full.task",
    ),
    "heavy": (
        WEIGHTS / "pose_landmarker_heavy.task",
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
    ),
}

# Anotasi viewpoint yang ada (arsip A v2: 240 record dgn kolom viewpoint)
VIEWPOINT_SOURCES = [
    BASE / "annotation" / "ground_truth" / "_archive_annotator_A_p240_v2.json",
    BASE / "annotation" / "ground_truth" / "annotator_A_p240.json",
]

# ------------------------------------------------------------------
# Indeks landmark MediaPipe Pose
# ------------------------------------------------------------------
LM = {
    "nose": 0,
    "ear_L": 7,
    "ear_R": 8,
    "shoulder_L": 11,
    "shoulder_R": 12,
    "hip_L": 23,
    "hip_R": 24,
}

# Viewpoint valid untuk proyek
BACK_VIEWPOINTS = {"back", "back_left", "back_right"}

SEED = 42


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------
def ensure_pose_model(which: str = "lite") -> Path:
    path, url = POSE_MODELS.get(which, POSE_MODELS["lite"])
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    WEIGHTS.mkdir(parents=True, exist_ok=True)
    print(f"  Mengunduh model pose '{which}' -> {path.name} ...")
    urllib.request.urlretrieve(url, path)
    print(f"  Selesai: {path.stat().st_size/1e6:.1f} MB")
    return path


def load_viewpoint_map() -> dict[str, str]:
    """Baca anotasi viewpoint yang ada -> {image_id: viewpoint}."""
    for src in VIEWPOINT_SOURCES:
        if src.exists():
            data = json.loads(src.read_text(encoding="utf-8"))
            result = {}
            for rec in data:
                iid = rec.get("image_id")
                vp = rec.get("viewpoint")
                if iid and vp:
                    result[iid] = vp
            if result:
                print(f"  Viewpoint source: {src.relative_to(BASE)} ({len(result)} records)")
                return result
    return {}


def image_id_to_path(image_id: str) -> Path:
    """figaro1k/<type>/<frame>.jpg -> dataset/figaro1k/<type>/<frame>.jpg"""
    return BASE / image_id.replace("figaro1k/", "dataset/figaro1k/", 1)


def build_sample(vp_map: dict[str, str], per_view: int, seed: int) -> dict[str, list[str]]:
    """Sampling stratified per viewpoint dari anotasi yang ada."""
    import random

    rng = random.Random(seed)
    by_view: dict[str, list[str]] = defaultdict(list)
    for iid, vp in vp_map.items():
        by_view[vp].append(iid)

    sample: dict[str, list[str]] = {}
    for vp, ids in by_view.items():
        ids = sorted(ids)
        rng.shuffle(ids)
        sample[vp] = ids[:per_view]
    return sample


def normalize_viewpoint_label(vp: str) -> str:
    """Kelompokkan viewpoint ke kategori kasar untuk analisis."""
    if vp in BACK_VIEWPOINTS:
        return "back"
    if vp == "front":
        return "front"
    if vp == "side":
        return "side"
    return "unknown"


# ------------------------------------------------------------------
# Pose extraction
# ------------------------------------------------------------------
def make_landmarker(model_path: Path, min_det: float, complexity_hint: str = "lite"):
    opts = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=min_det,
        min_pose_presence_confidence=min_det,
        output_segmentation_masks=False,
    )
    return vision.PoseLandmarker.create_from_options(opts)


def extract_landmarks(landmarker, img_path: Path, v_min: float, coord_tol: float = 0.15) -> dict:
    """Jalankan pose, kembalikan landmark relevan + flag detection.

    coord_tol: toleransi koordinat di luar frame (mis. x=-0.05 masih diterima
    bila visibility tinggi). Default 0.15.
    """
    try:
        im = Image.open(img_path).convert("RGB")
    except Exception as exc:
        return {"error": f"load_fail: {exc}", "shoulder_ok": False, "head_ok": False}

    w, h = im.size
    arr = np.asarray(im)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
    try:
        res = landmarker.detect(mp_img)
    except Exception as exc:
        return {"error": f"detect_fail: {exc}", "shoulder_ok": False, "head_ok": False}

    if not res.pose_landmarks:
        return {"error": "no_pose", "shoulder_ok": False, "head_ok": False, "landmarks": {}}

    lm = res.pose_landmarks[0]

    def point(name: str):
        idx = LM[name]
        p = lm[idx]
        return {
            "x": round(float(p.x), 4),
            "y": round(float(p.y), 4),
            "visibility": round(float(p.visibility), 4),
        }

    lms = {name: point(name) for name in LM}

    def visible(name: str) -> bool:
        p = lms[name]
        return (
            p["visibility"] >= v_min
            and -coord_tol <= p["x"] <= 1.0 + coord_tol
            and -coord_tol <= p["y"] <= 1.0 + coord_tol
        )

    shoulder_ok = visible("shoulder_L") and visible("shoulder_R")
    # Acuan kepala (P4): minimal satu dari ear/nose terdeteksi
    head_candidates = ["ear_L", "ear_R", "nose"]
    head_ok = any(visible(c) for c in head_candidates)
    # Kedua telinga (lebih stabil) untuk unit tinggi kepala
    ears_ok = visible("ear_L") and visible("ear_R")

    out = {
        "image_wh": [w, h],
        "landmarks": lms,
        "shoulder_ok": shoulder_ok,
        "head_ok": head_ok,
        "ears_ok": ears_ok,
    }

    # --- Metrik acuan bahu ---
    if shoulder_ok:
        ys = (lms["shoulder_L"]["y"] + lms["shoulder_R"]["y"]) / 2
        ws = abs(lms["shoulder_L"]["x"] - lms["shoulder_R"]["x"])
        out["y_shoulder_norm"] = round(ys, 4)
        out["W_shoulder_norm"] = round(ws, 4)
        head_pts = [c for c in head_candidates if visible(c)]
        if head_pts:
            hy = np.mean([lms[c]["y"] for c in head_pts])
            H_head = abs(hy - ys)
            out["H_head_norm"] = round(float(H_head), 4)
            if ws > 1e-6:
                out["R_head_shoulder"] = round(float(H_head / ws), 4)

    # --- Metrik acuan kepala (P4): jarak antar-telinga sbg skala lebar kepala ---
    if ears_ok:
        we = abs(lms["ear_L"]["x"] - lms["ear_R"]["x"])
        out["W_ear_norm"] = round(float(we), 4)
    return out


# ------------------------------------------------------------------
# Analysis
# ------------------------------------------------------------------
def summarize(records: list[dict]) -> dict:
    """Ringkas detection rate per viewpoint kasar."""
    by_view: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_view[r["view_group"]].append(r)

    summary = {}
    for vg, rows in sorted(by_view.items()):
        n = len(rows)
        sh = sum(1 for r in rows if r.get("shoulder_ok"))
        hd = sum(1 for r in rows if r.get("head_ok"))
        ea = sum(1 for r in rows if r.get("ears_ok"))
        ratios = [r["R_head_shoulder"] for r in rows if r.get("R_head_shoulder")]
        cv = None
        if len(ratios) >= 2:
            mu = float(np.mean(ratios))
            sd = float(np.std(ratios, ddof=1))
            cv = round(sd / mu, 4) if mu > 0 else None
        summary[vg] = {
            "n": n,
            "shoulder_ok": sh,
            "shoulder_rate": round(sh / n, 4) if n else None,
            "head_ok": hd,
            "head_rate": round(hd / n, 4) if n else None,
            "ears_ok": ea,
            "ears_rate": round(ea / n, 4) if n else None,
            "R_head_shoulder_mean": round(float(np.mean(ratios)), 4) if ratios else None,
            "R_head_shoulder_cv": cv,
        }
    return summary


def decide_gate(summary: dict, shoulder_thresh: float, head_thresh: float = 0.80) -> dict:
    """Keputusan gate. Utama: bahu. Fallback (P4): kepala."""
    back = summary.get("back", {})
    sr = back.get("shoulder_rate")
    hr = back.get("head_rate")
    er = back.get("ears_rate")
    if sr is None and hr is None:
        return {"status": "NO_DATA", "reason": "tidak ada sampel back-view"}

    # Gate utama: BAHU
    if sr is not None and sr >= shoulder_thresh and (hr is not None and hr >= head_thresh):
        status = "LULUS"
        basis = "shoulder"
    # Gate alternatif P4: KEPALA (bila bahu gagal tapi kepala andal)
    elif hr is not None and hr >= head_thresh:
        status = "LULUS_P4_HEAD"
        basis = "head"
    elif sr is not None and sr >= 0.50:
        status = "KONDISIONAL"
        basis = "shoulder_weak"
    else:
        status = "PIVOT"
        basis = "none"
    return {
        "status": status,
        "basis": basis,
        "shoulder_back_rate": sr,
        "head_back_rate": hr,
        "ears_back_rate": er,
        "shoulder_threshold": shoulder_thresh,
        "head_threshold": head_thresh,
    }


# ------------------------------------------------------------------
# Visualization
# ------------------------------------------------------------------
def draw_overlays(records: list[dict], landmarker, v_min: float, max_ok: int = 6, max_fail: int = 6):
    """Simpan contoh OK & FAIL dengan titik landmark (digambar manual)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def draw_manual(ax, img_path, title):
        im = Image.open(img_path).convert("RGB")
        arr = np.asarray(im).copy()
        h, w = arr.shape[:2]
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(im))
        res = landmarker.detect(mp_img)
        if res.pose_landmarks:
            for p in res.pose_landmarks[0]:
                x, y = int(p.x * w), int(p.y * h)
                if 0 <= x < w and 0 <= y < h:
                    col = [0, 0, 255] if p.visibility >= v_min else [255, 0, 0]
                    arr[max(0, y - 2):y + 3, max(0, x - 2):x + 3] = col
        ax.imshow(arr)
        ax.set_title(title, fontsize=8)
        ax.axis("off")

    ok = [r for r in records if r.get("shoulder_ok") and r.get("view_group") == "back"][:max_ok]
    fail = [r for r in records if not r.get("shoulder_ok") and r.get("view_group") == "back"][:max_fail]

    for tag, items in (("ok", ok), ("fail", fail)):
        if not items:
            continue
        cols = 3
        rows = max(1, (len(items) + cols - 1) // cols)
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.2, rows * 3.6))
        axes = np.atleast_2d(axes)
        for i, ax in enumerate(axes.flat):
            if i >= len(items):
                ax.axis("off")
                continue
            r = items[i]
            img_path = image_id_to_path(r["image_id"])
            draw_manual(ax, img_path, f"{r['image_id'].split('/')[-2]}/{r['image_id'].split('/')[-1]}\nsh={r.get('shoulder_ok')}")
        fig.suptitle(f"Back-view: {tag.upper()} ({len(items)})", fontsize=11, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        out = FIGURES / f"pose_{tag}.png"
        fig.savefig(out, dpi=100, bbox_inches="tight")
        plt.close(fig)
        print(f"  Figure -> {out.name}")


def draw_viewpoint_comparison(summary: dict):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    views = [v for v in ("back", "front", "side", "unknown") if v in summary]
    if not views:
        return
    sh = [summary[v]["shoulder_rate"] or 0 for v in views]
    hd = [summary[v]["head_rate"] or 0 for v in views]

    x = np.arange(len(views))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width / 2, sh, width, label="Shoulder", color="#2e7d32")
    ax.bar(x + width / 2, hd, width, label="Head", color="#1565c0")
    ax.axhline(0.70, color="red", linestyle="--", linewidth=1, label="Gate bahu 0.70")
    ax.axhline(0.80, color="orange", linestyle=":", linewidth=1, label="Gate kepala 0.80")
    ax.set_xticks(x)
    ax.set_xticklabels(views)
    ax.set_ylabel("Detection rate")
    ax.set_ylim(0, 1.05)
    ax.set_title("Detection Rate MediaPipe Pose per Viewpoint")
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = FIGURES / "viewpoint_comparison.png"
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figure -> {out.name}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Fase 0: uji MediaPipe Pose pada foto back-view.")
    ap.add_argument("--per-view", type=int, default=30, help="Sampel per viewpoint (default 30)")
    ap.add_argument("--v-min", type=float, default=0.5, help="Ambang visibility landmark (default 0.5)")
    ap.add_argument("--min-det", type=float, default=0.3, help="Ambang deteksi pose (default 0.3)")
    ap.add_argument("--model", default="lite", choices=["lite", "full", "heavy"], help="Varian model pose")
    ap.add_argument("--seed", type=int, default=SEED, help="Seed sampling (default 42)")
    ap.add_argument("--out", default=str(REPORTS / "pose_feasibility.json"), help="Output JSON")
    ap.add_argument("--no-fig", action="store_true", help="Lewati pembuatan figur")
    args = ap.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    print("=== FASE 0: Verifikasi Gate (MediaPipe Pose back-view) ===")
    print(f"Dataset: {DATASET}")

    vp_map = load_viewpoint_map()
    if not vp_map:
        print("ERROR: tidak ada anotasi viewpoint. Jalankan anotasi dulu.")
        return

    sample = build_sample(vp_map, args.per_view, args.seed)
    total = sum(len(v) for v in sample.values())
    print(f"Sampel: {total} gambar")
    for vp, ids in sorted(sample.items()):
        print(f"  {vp:12s}: {len(ids)}")

    model = ensure_pose_model(args.model)
    print(f"Model pose: {model.name}")
    landmarker = make_landmarker(model, args.min_det)

    records = []
    print("\nMemproses...")
    for vp, ids in sorted(sample.items()):
        for iid in ids:
            img_path = image_id_to_path(iid)
            if not img_path.exists():
                continue
            r = extract_landmarks(landmarker, img_path, args.v_min)
            r["image_id"] = iid
            r["viewpoint_annotated"] = vp
            r["view_group"] = normalize_viewpoint_label(vp)
            records.append(r)
        done = sum(1 for r in records if r["viewpoint_annotated"] == vp)
        print(f"  {vp:12s}: {done} diproses")

    landmarker.close()

    summary = summarize(records)
    gate = decide_gate(summary, 0.70)

    report = {
        "phase": "0_pose_feasibility",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {"per_view": args.per_view, "v_min": args.v_min, "min_det": args.min_det, "seed": args.seed, "model": args.model},
        "n_total": len(records),
        "summary_by_viewpoint": summary,
        "gate": gate,
        "records": records,
    }

    # Tambahkan ringkasan error/nodetect
    errors = Counter(r.get("error") for r in records if r.get("error"))
    report["error_counts"] = dict(errors)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Visualisasi
    if not args.no_fig:
        print("\nMembuat figur...")
        try:
            landmarker2 = make_landmarker(model, args.min_det)
            draw_overlays(records, landmarker2, args.v_min)
            landmarker2.close()
        except Exception as exc:
            print(f"  WARN figur overlay: {exc}")
        try:
            draw_viewpoint_comparison(summary)
        except Exception as exc:
            print(f"  WARN figur comparison: {exc}")

    # Ringkasan konsol
    print("\n=== RINGKASAN ===")
    print(f"{'viewpoint':12s} {'n':>4s} {'shoulder':>10s} {'head':>8s} {'ears':>8s} {'CV(R)':>8s}")
    for vg, s in summary.items():
        cvv = s["R_head_shoulder_cv"] if s["R_head_shoulder_cv"] is not None else float("nan")
        print(f"{vg:12s} {s['n']:>4d} {s['shoulder_rate']:>10.3f} {s['head_rate']:>8.3f} "
              f"{s.get('ears_rate', float('nan')):>8.3f} {cvv:>8.3f}")

    print("\n=== GATE ===")
    print(f"  Status: {gate['status']} (basis: {gate.get('basis')})")
    print(f"  Shoulder(back) = {gate.get('shoulder_back_rate')} (ambang {gate.get('shoulder_threshold')})")
    print(f"  Head(back)     = {gate.get('head_back_rate')} (ambang {gate.get('head_threshold')})")
    print(f"  Ears(back)     = {gate.get('ears_back_rate')}")
    if errors:
        print(f"  Error/nodetect: {dict(errors)}")
    print(f"\nReport -> {out}")


if __name__ == "__main__":
    main()
