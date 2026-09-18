# -*- coding: utf-8 -*-
"""viewpoint/gate.py — Gate posisi (heuristik 3 kelas: depan/samping/belakang).

Vonis keras: selalu pilih satu kelas. Hanya "belakang" yang diterima untuk
analisis rambut; depan/samping -> minta foto ulang.

Sinyal (MediaPipe pretrained):
  - Face Landmarker : fitur wajah asli (mata/hidung/mulut)
  - Pose Landmarker : geometri (hidung-telinga, bahu, lengan)
  - BlazeFace       : pendukung (sering false-positive -> bukan bukti utama)

CATATAN: heuristik ini mentok ~80% (batas MediaPipe). CNN menyusul (train_cnn.py).

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\gate.py --source figaro --all
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

# pastikan root apps/api/cv ada di sys.path (impor common.*)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from common.constants import (
    CV_DIR, FACE_LM_MODEL, FACE_MODEL, POSE_MODEL, SEED, VIEWPOINT_CLASSES,
)
from common.io_utils import collect_images, save_json

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground_truth"
REPORTS = HERE / "reports"

# Indeks landmark pose relevan
LM_NOSE = 0
LM_EYE_L, LM_EYE_R = 2, 5
LM_EAR_L, LM_EAR_R = 7, 8
LM_MOUTH_L, LM_MOUTH_R = 9, 10
LM_SH_L, LM_SH_R = 11, 12
LM_ELBOW_L, LM_ELBOW_R = 13, 14


# ------------------------------------------------------------------
# Model loaders
# ------------------------------------------------------------------
def make_pose(model_path: Path, min_det: float = 0.3):
    opts = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE, num_poses=1,
        min_pose_detection_confidence=min_det, min_pose_presence_confidence=min_det,
        output_segmentation_masks=False,
    )
    return vision.PoseLandmarker.create_from_options(opts)


def make_face(model_path: Path, min_det: float = 0.3):
    opts = vision.FaceDetectorOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        min_detection_confidence=min_det,
    )
    return vision.FaceDetector.create_from_options(opts)


def make_face_landmarker(model_path: Path, min_det: float = 0.3):
    opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE, num_faces=1,
        min_face_detection_confidence=min_det, min_face_presence_confidence=min_det,
        output_face_blendshapes=False, output_facial_transformation_matrixes=False,
    )
    return vision.FaceLandmarker.create_from_options(opts)


# ------------------------------------------------------------------
# Sinyal
# ------------------------------------------------------------------
def face_landmark_signal(landmarker, arr: np.ndarray) -> dict:
    if landmarker is None:
        return {"face_lm_present": False, "n_landmarks": 0}
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
    try:
        res = landmarker.detect(mp_img)
    except Exception as exc:
        return {"face_lm_present": False, "n_landmarks": 0, "error": str(exc)}
    if not res.face_landmarks:
        return {"face_lm_present": False, "n_landmarks": 0}
    return {"face_lm_present": True, "n_landmarks": len(res.face_landmarks[0])}


def face_signal(face_detector, arr: np.ndarray) -> dict:
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
    try:
        res = face_detector.detect(mp_img)
    except Exception as exc:
        return {"face_present": False, "face_bbox_ratio": 0.0, "error": str(exc)}
    if not res.detections:
        return {"face_present": False, "face_bbox_ratio": 0.0}
    h, w = arr.shape[:2]
    best = 0.0
    for det in res.detections:
        bb = det.bounding_box
        best = max(best, (bb.width * bb.height) / float(w * h))
    return {"face_present": True, "face_bbox_ratio": round(float(best), 4)}


def pose_signal(pose_landmarker, arr: np.ndarray, v_min: float = 0.5) -> dict:
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
    try:
        res = pose_landmarker.detect(mp_img)
    except Exception as exc:
        return {"pose_present": False, "error": str(exc)}
    if not res.pose_landmarks:
        return {"pose_present": False}

    lm = res.pose_landmarks[0]

    def get(idx):
        p = lm[idx]
        return {"x": float(p.x), "y": float(p.y), "vis": float(p.visibility)}

    nose, eye_l, eye_r = get(LM_NOSE), get(LM_EYE_L), get(LM_EYE_R)
    ear_l, ear_r = get(LM_EAR_L), get(LM_EAR_R)
    mouth_l, mouth_r = get(LM_MOUTH_L), get(LM_MOUTH_R)
    sh_l, sh_r = get(LM_SH_L), get(LM_SH_R)
    el_l, el_r = get(LM_ELBOW_L), get(LM_ELBOW_R)

    out = {
        "pose_present": True, "nose": nose,
        "eye_l": eye_l, "eye_r": eye_r, "ear_l": ear_l, "ear_r": ear_r,
        "mouth_l": mouth_l, "mouth_r": mouth_r, "sh_l": sh_l, "sh_r": sh_r,
        "elbow_l": el_l, "elbow_r": el_r,
    }
    eyes_both = eye_l["vis"] >= v_min and eye_r["vis"] >= v_min
    mouth_present = mouth_l["vis"] >= v_min or mouth_r["vis"] >= v_min
    nose_present = nose["vis"] >= v_min

    frontal_geom_ok = False
    if eyes_both and nose_present:
        eye_mid = (eye_l["x"] + eye_r["x"]) / 2.0
        eye_sep = abs(eye_r["x"] - eye_l["x"])
        if eye_sep > 0.02:
            nose_offset = abs(nose["x"] - eye_mid) / eye_sep
            if nose_offset < 1.2:
                frontal_geom_ok = True
    out["frontal_face_strong"] = bool(eyes_both and mouth_present and nose_present and frontal_geom_ok)
    out["eyes_both_visible"] = eyes_both

    ears_both = ear_l["vis"] >= v_min and ear_r["vis"] >= v_min
    out["ears_both_visible"] = ears_both
    out["nose_visible"] = nose_present

    sh_both = sh_l["vis"] >= v_min and sh_r["vis"] >= v_min
    out["shoulder_both_visible"] = sh_both
    if sh_both:
        out["shoulder_width"] = round(abs(sh_l["x"] - sh_r["x"]), 4)
        out["shoulder_vis_diff"] = round(abs(sh_l["vis"] - sh_r["vis"]), 4)
    out["shoulder_one_only"] = bool((sh_l["vis"] >= v_min) != (sh_r["vis"] >= v_min))
    out["elbow_one_only"] = bool((el_l["vis"] >= v_min) != (el_r["vis"] >= v_min))
    return out


# ------------------------------------------------------------------
# Keputusan
# ------------------------------------------------------------------
def decide_viewpoint(face: dict, pose: dict, face_lm: dict | None = None) -> tuple[str, float, dict]:
    """Vonis 3 kelas. Lihat docstring modul."""
    face_lm = face_lm or {}
    detail = {}
    evid = {c: [] for c in VIEWPOINT_CLASSES}
    v_min = 0.5

    lm_present = face_lm.get("face_lm_present", False)
    face_present = face.get("face_present", False)
    bbox = face.get("face_bbox_ratio", 0.0)
    pose_present = pose.get("pose_present", False)
    frontal_strong = pose.get("frontal_face_strong", False)

    if frontal_strong:
        evid["depan"].append(1.0)
        detail["frontal"] = "frontal kuat (mata+hidung+mulut)"
    elif lm_present:
        evid["depan"].append(0.4)
        detail["face_lm_weak"] = "fitur wajah ada (tidak frontal kuat)"
    if face_present and not lm_present and not frontal_strong:
        detail["blazeface_only"] = f"bbox={bbox} (diabaikan)"

    if pose_present:
        nose, ear_l, ear_r = pose.get("nose", {}), pose.get("ear_l", {}), pose.get("ear_r", {})
        el_vis, er_vis = ear_l.get("vis", 0.0), ear_r.get("vis", 0.0)
        ears_both = el_vis >= v_min and er_vis >= v_min
        sh_both = pose.get("shoulder_both_visible", False)
        sh_one = pose.get("shoulder_one_only", False)
        elbow_one = pose.get("elbow_one_only", False)
        nose_x = nose.get("x", 0.5)
        x_left = min(ear_l.get("x", 0.0), ear_r.get("x", 1.0))
        x_right = max(ear_l.get("x", 0.0), ear_r.get("x", 1.0))
        ear_width = abs(x_right - x_left)

        if sh_both and not frontal_strong:
            evid["belakang"].append(0.4)
            detail["shoulders_both"] = "2 bahu -> belakang"
        if sh_one:
            evid["samping"].append(0.7)
            detail["shoulder_one"] = "1 bahu -> samping"
        if elbow_one:
            evid["samping"].append(0.5)
            detail["elbow_one"] = "1 siku -> samping"
        if (sh_one or elbow_one) and not lm_present and not frontal_strong:
            evid["depan"] = [(min(evid["depan"]) if evid["depan"] else 0.0)]
            detail["frontal_veto"] = "1 sisi tubuh + tanpa frontal kuat -> frontal diragukan"
        if ears_both and ear_width > 1e-4 and not frontal_strong:
            rel = (nose_x - x_left) / ear_width
            if 0.15 <= rel <= 0.85 and abs(el_vis - er_vis) < 0.25:
                evid["belakang"].append(0.3)
            elif rel < 0.15 or rel > 0.85:
                evid["samping"].append(0.5)
        if (sh_both or ears_both) and not frontal_strong:
            evid["belakang"].append(0.3)
            detail["back_nonfrontal"] = "belakang (muka mungkin menoleh)"

    scores = {c: float(np.sum(evid[c])) for c in VIEWPOINT_CLASSES}
    if max(scores.values()) == 0.0:
        scores["belakang"] = 0.05
        return "belakang", 0.10, {"scores": scores, "detail": {"fallback": "no signal"}}

    cls = max(scores, key=scores.get)
    top = scores[cls]
    second = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0.0
    conf = max(0.3, min(0.99, round((top - second) / top, 4))) if top > 0 else 0.0
    return cls, conf, {"scores": {k: round(v, 3) for k, v in scores.items()}, "detail": detail}


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Gate viewpoint (heuristik 3 kelas).")
    ap.add_argument("--source", default="figaro", choices=["figaro", "extra", "all"])
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--v-min", type=float, default=0.5)
    ap.add_argument("--min-det", type=float, default=0.3)
    ap.add_argument("--out", default=str(REPORTS / "viewpoint_predictions.json"))
    args = ap.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    print("=== Gate Viewpoint (heuristik) ===")

    items = collect_images(args.source)
    if not args.all and args.max > 0:
        items = items[: args.max]
    print(f"gambar: {len(items)}")

    for m in (POSE_MODEL, FACE_MODEL):
        if not m.exists():
            print(f"ERROR: model tidak ada: {m}")
            return

    pose_lk = make_pose(POSE_MODEL, args.min_det)
    face_det = make_face(FACE_MODEL, args.min_det)
    face_lm_lk = make_face_landmarker(FACE_LM_MODEL, args.min_det) if FACE_LM_MODEL.exists() else None

    records = []
    for i, item in enumerate(items, 1):
        p = CV_DIR / item["relpath"]
        try:
            arr = np.asarray(Image.open(p).convert("RGB"))
        except Exception as exc:
            records.append({**item, "error": f"load: {exc}"})
            continue
        face = face_signal(face_det, arr)
        face_lm = face_landmark_signal(face_lm_lk, arr)
        pose = pose_signal(pose_lk, arr, args.v_min)
        cls, conf, detail = decide_viewpoint(face, pose, face_lm)
        records.append({
            **item, "predicted_viewpoint": cls, "confidence": conf,
            "face": face, "face_lm": face_lm,
            "pose": {k: v for k, v in pose.items() if k in (
                "pose_present", "ears_both_visible", "nose_visible", "shoulder_width",
                "frontal_face_strong", "eyes_both_visible", "shoulder_both_visible",
                "shoulder_one_only", "elbow_one_only", "shoulder_vis_diff")},
            "decision_detail": detail,
        })
        if i % 50 == 0:
            print(f"  {i}/{len(items)}...", flush=True)

    pose_lk.close()
    face_det.close()
    if face_lm_lk:
        face_lm_lk.close()

    dist = Counter(r.get("predicted_viewpoint", "error") for r in records)
    report = {
        "phase": "viewpoint_gate", "method": "heuristic",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": args.source, "n_total": len(records),
        "distribution": dict(dist), "classes": VIEWPOINT_CLASSES,
        "records": records,
    }
    save_json(args.out, report)
    print("\n=== Distribusi ===")
    for c in VIEWPOINT_CLASSES:
        print(f"  {c:10s} {dist.get(c, 0)}")
    print(f"\nReport -> {args.out}")


if __name__ == "__main__":
    main()
