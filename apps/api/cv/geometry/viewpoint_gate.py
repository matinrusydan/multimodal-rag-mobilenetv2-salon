# -*- coding: utf-8 -*-
"""TAHAP 1 — Gate Viewpoint: prediksi posisi (depan/samping/belakang).

3 kelas (belakang_nyerong digabung ke belakang). Model WAJIB memilih 1 kelas
(paksa pilih). Verifikasi manusia memakai output ini (mode pengukuran).

Sinyal yang dipakai (voting):
  1. Face detector (BlazeFace) → adanya wajah + ukuran bbox
  2. Face Mesh (MediaPipe) → ada fitur wajah (mata/hidung/mulut)?
  3. Pose (MediaPipe) → orientasi (hidung vs telinga visibility, bahu)

Aturan keputusan (heuristik awal, akan dikalibrasi dengan verifikasi manusia):
  - Wajah JELAS (face bbox besar) -> "depan"
  - Profil (satu telinga dominan, hidung menyamping) -> "samping"
  - Tidak ada wajah, ada telinga simetris + bahu -> "belakang" atau "belakang_nyerong"

Output: prediksi per gambar + skor keyakinan (bukan hard abstain).

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" geometry\\viewpoint_gate.py --help
  & ".venv\\Scripts\\python.exe" geometry\\viewpoint_gate.py --source figaro --max 60
  & ".venv\\Scripts\\python.exe" geometry\\viewpoint_gate.py --source figaro --all

Isolated: menulis ke geometry/reports/. Tidak menyentuh scripts/ lama.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
BASE = Path(__file__).resolve().parents[1]          # apps/api/cv
GEO = Path(__file__).resolve().parents[0]
WEIGHTS = BASE / "weights"
REPORTS = GEO / "reports"
FIGARO = BASE / "dataset" / "figaro1k"
EXTRA = BASE / "dataset" / "extra"

POSE_MODEL = WEIGHTS / "pose_landmarker_lite.task"
FACE_MODEL = WEIGHTS / "blaze_face_short_range.tflite"
FACE_LM_MODEL = WEIGHTS / "face_landmarker.task"

# Kelas viewpoint — 3 kelas (belakang_nyerong digabung ke belakang)
VIEWPOINT_CLASSES = ["depan", "samping", "belakang"]

# Landmark pose relevan
LM_NOSE = 0
LM_EYE_L = 2
LM_EYE_R = 5
LM_EAR_L = 7
LM_EAR_R = 8
LM_MOUTH_L = 9
LM_MOUTH_R = 10
LM_SH_L = 11
LM_SH_R = 12
LM_ELBOW_L = 13
LM_ELBOW_R = 14
LM_WRIST_L = 15
LM_WRIST_R = 16

SEED = 42


# ------------------------------------------------------------------
# Model loaders
# ------------------------------------------------------------------
def make_pose(model_path: Path, min_det: float = 0.3):
    opts = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=min_det,
        min_pose_presence_confidence=min_det,
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
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=min_det,
        min_face_presence_confidence=min_det,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    return vision.FaceLandmarker.create_from_options(opts)


def face_landmark_signal(landmarker, arr: np.ndarray) -> dict:
    """Sinyal wajah ASLI via Face Landmarker (mata/hidung/mulut).

    Lebih andal daripada BlazeFace yang sering false-positive pada rambut.
    Kembalikan: n_landmarks, ada fitur kunci (mata+hidung+mulut)?
    """
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
    try:
        res = landmarker.detect(mp_img)
    except Exception as exc:
        return {"face_lm_present": False, "n_landmarks": 0, "error": str(exc)}
    if not res.face_landmarks:
        return {"face_lm_present": False, "n_landmarks": 0}
    lm = res.face_landmarks[0]
    return {"face_lm_present": True, "n_landmarks": len(lm)}


# ------------------------------------------------------------------
# Sinyal extraction
# ------------------------------------------------------------------
def face_signal(face_detector, arr: np.ndarray) -> dict:
    """Deteksi wajah; kembalikan ada/tidak + ukuran relatif bbox."""
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
    try:
        res = face_detector.detect(mp_img)
    except Exception as exc:
        return {"face_present": False, "face_bbox_ratio": 0.0, "error": str(exc)}
    if not res.detections:
        return {"face_present": False, "face_bbox_ratio": 0.0}
    # ambil deteksi terbesar
    h, w = arr.shape[:2]
    best = None
    for det in res.detections:
        bb = det.bounding_box
        ratio = (bb.width * bb.height) / float(w * h)
        if best is None or ratio > best:
            best = ratio
    return {"face_present": True, "face_bbox_ratio": round(float(best), 4)}


def pose_signal(pose_landmarker, arr: np.ndarray, v_min: float = 0.5) -> dict:
    """Ekstrak orientasi dari pose landmarks."""
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

    nose = get(LM_NOSE)
    eye_l = get(LM_EYE_L)
    eye_r = get(LM_EYE_R)
    ear_l = get(LM_EAR_L)
    ear_r = get(LM_EAR_R)
    mouth_l = get(LM_MOUTH_L)
    mouth_r = get(LM_MOUTH_R)
    sh_l = get(LM_SH_L)
    sh_r = get(LM_SH_R)
    elbow_l = get(LM_ELBOW_L)
    elbow_r = get(LM_ELBOW_R)

    out = {
        "pose_present": True,
        "nose": nose,
        "eye_l": eye_l, "eye_r": eye_r,
        "ear_l": ear_l, "ear_r": ear_r,
        "mouth_l": mouth_l, "mouth_r": mouth_r,
        "sh_l": sh_l, "sh_r": sh_r,
        "elbow_l": elbow_l, "elbow_r": elbow_r,
    }
    # Sinyal wajah frontal: 2 mata + hidung + mulut terdeteksi jelas
    # DIPERKETAT: MediaPipe sering berhalusinasi memunculkan landmark wajah
    # pada foto belakang. Syarat tambahan: hidung harus di ANTARA mata (simetris)
    # dan mata cukup terpisah (bukan berimpit di tepi).
    eyes_both = eye_l["vis"] >= v_min and eye_r["vis"] >= v_min
    mouth_present = mouth_l["vis"] >= v_min or mouth_r["vis"] >= v_min
    nose_present = nose["vis"] >= v_min

    frontal_geom_ok = False
    if eyes_both and nose_present:
        ex_l, ex_r = eye_l["x"], eye_r["x"]
        eye_mid = (ex_l + ex_r) / 2.0
        eye_sep = abs(ex_r - ex_l)
        # mata harus cukup lebar (tidak berimpit) & hidung dekat tengah mata
        if eye_sep > 0.02:
            nose_offset = abs(nose["x"] - eye_mid) / eye_sep
            if nose_offset < 1.2:  # hidung di sekitar tengah mata
                frontal_geom_ok = True

    out["frontal_face_strong"] = bool(eyes_both and mouth_present and nose_present and frontal_geom_ok)
    out["eyes_both_visible"] = eyes_both

    # Sinyal telinga: apakah keduanya terlihat? (belakang -> dua telinga simetris)
    ears_both = ear_l["vis"] >= v_min and ear_r["vis"] >= v_min
    out["ears_both_visible"] = ears_both
    out["nose_visible"] = nose_present

    # Sinyal bahu: 2 bahu simetris (belakang) vs 1 bahu dominan (samping)
    sh_both = sh_l["vis"] >= v_min and sh_r["vis"] >= v_min
    out["shoulder_both_visible"] = sh_both
    if sh_both:
        out["shoulder_width"] = round(abs(sh_l["x"] - sh_r["x"]), 4)
        out["shoulder_vis_diff"] = round(abs(sh_l["vis"] - sh_r["vis"]), 4)
    # 1 bahu saja terlihat -> indikasi samping
    sh_one = (sh_l["vis"] >= v_min) != (sh_r["vis"] >= v_min)
    out["shoulder_one_only"] = bool(sh_one)

    # Sinyal lengan: 1 siku terlihat -> indikasi samping (profil)
    elbow_one = (elbow_l["vis"] >= v_min) != (elbow_r["vis"] >= v_min)
    out["elbow_one_only"] = bool(elbow_one)

    return out


# ------------------------------------------------------------------
# Decision (vote-based, paksa pilih)
# ------------------------------------------------------------------
def decide_viewpoint(face: dict, pose: dict, face_lm: dict | None = None) -> tuple[str, float, dict]:
    """Kembalikan (kelas_viewpoint, confidence, detail_skor). 3 kelas.

    Kelas: depan / samping / belakang. (belakang_nyerong digabung ke belakang.)

    Sinyal (v3):
      DEPAN   : wajah FRONTAL kuat -> 2 mata + hidung + mulut TERDETEKSI & simetris.
                (DIPERKETAT: rambut pendek yang memperlihatkan rahang/telinga/bahu
                 TIDAK cukup untuk disebut depan.)
      SAMPING : 1 bahu/lengan dominan (asimetri), hidung keluar rentang telinga.
      BELAKANG: 2 bahu simetris, tidak ada wajah frontal. Termasuk:
                - 2 telinga simetris
                - badan belakang + muka menoleh (tidak frontal) -> tetap belakang
                - rambut pendek (rahang/telinga terlihat) tanpa wajah frontal -> belakang
    """
    face_lm = face_lm or {}
    detail = {}
    evid = {c: [] for c in VIEWPOINT_CLASSES}

    face_present = face.get("face_present", False)
    bbox = face.get("face_bbox_ratio", 0.0)
    lm_present = face_lm.get("face_lm_present", False)
    pose_present = pose.get("pose_present", False)
    v_min = 0.5

    frontal_strong = pose.get("frontal_face_strong", False)

    # --- DEPAN: HANYA jika wajah frontal kuat ---
    # Aturan diperketat: jangan anggap "depan" hanya karena fitur wajah terdeteksi
    # (rambut pendek bisa memicu fitur telinga/rahang). Butuh frontal kuat.
    if frontal_strong:
        evid["depan"].append(1.0)
        detail["frontal"] = "2 mata + hidung + mulut terdeteksi (frontal kuat)"
    elif lm_present:
        # fitur wajah ada tapi tidak frontal kuat -> dukungan lemah saja
        evid["depan"].append(0.4)
        detail["face_lm_weak"] = "fitur wajah ada tapi tidak frontal kuat"

    # BlazeFace tanpa fitur wajah -> jangan jadikan bukti depan (sering false-positive)
    if face_present and not lm_present and not frontal_strong:
        detail["blazeface_only"] = f"bbox={bbox} (diabaikan; butuh bukti frontal)"

    # --- sinyal pose ---
    if pose_present:
        nose = pose.get("nose", {})
        ear_l = pose.get("ear_l", {})
        ear_r = pose.get("ear_r", {})
        nose_vis = nose.get("vis", 0.0)
        el_vis = ear_l.get("vis", 0.0)
        er_vis = ear_r.get("vis", 0.0)
        ears_both = el_vis >= v_min and er_vis >= v_min

        sh_both = pose.get("shoulder_both_visible", False)
        sh_one = pose.get("shoulder_one_only", False)
        elbow_one = pose.get("elbow_one_only", False)

        nose_x = nose.get("x", 0.5)
        el_x = ear_l.get("x", 0.0)
        er_x = ear_r.get("x", 1.0)
        x_left = min(el_x, er_x)
        x_right = max(el_x, er_x)
        ear_width = abs(x_right - x_left)

        # --- BELAKANG: 2 bahu simetris ---
        # HANYA diberi bobot jika TIDAK ada bukti frontal kuat.
        # (foto depan juga punya 2 bahu terlihat -> jangan menang melawan frontal)
        if sh_both and not frontal_strong:
            evid["belakang"].append(0.4)
            detail["shoulders_both"] = "2 bahu simetris -> belakang"

        # --- SAMPING: 1 bahu / 1 lengan saja (profil) ---
        # elbow_one_only adalah sinyal paling berguna untuk samping pada data ini.
        # Front-depan biasanya 2 lengan simetris; samping -> 1 siku/lengan menonjol.
        if sh_one:
            evid["samping"].append(0.7)
            detail["shoulder_one"] = "hanya 1 bahu terlihat -> samping"
        if elbow_one:
            evid["samping"].append(0.5)
            detail["elbow_one"] = "hanya 1 siku terlihat -> samping"

        # VETO frontal: hanya bila frontal TIDAK kuat (agar foto depan tetap depan)
        if (sh_one or elbow_one) and not lm_present and not frontal_strong:
            evid["depan"] = [(min(evid["depan"]) if evid["depan"] else 0.0)]
            detail["frontal_veto"] = "1 sisi tubuh terlihat + tak ada frontal kuat -> frontal diragukan"

        # --- geometri hidung-telinga (hanya bila bukan frontal kuat) ---
        if ears_both and ear_width > 1e-4 and not frontal_strong:
            rel = (nose_x - x_left) / ear_width
            diff_vis = abs(el_vis - er_vis)
            detail["geom"] = f"nose_rel={rel:.2f}, ear_w={ear_width:.3f}"
            if 0.15 <= rel <= 0.85 and diff_vis < 0.25:
                evid["belakang"].append(0.3)
            elif rel < 0.15 or rel > 0.85:
                evid["samping"].append(0.5)

        # --- muka menoleh tapi ada indikasi belakang: tetap belakang ---
        # (didukung: 2 bahu/2 telinga simetris, meski tidak frontal)
        if (sh_both or ears_both) and not frontal_strong:
            evid["belakang"].append(0.3)
            detail["back_nonfrontal"] = "belakang; muka mungkin menoleh"

    # --- agregasi skor ---
    scores = {c: float(np.sum(evid[c])) for c in VIEWPOINT_CLASSES}

    if max(scores.values()) == 0.0:
        scores["belakang"] = 0.05
        detail["fallback"] = "no strong signal (confidence rendah)"
        return "belakang", 0.10, {"scores": {k: round(v, 3) for k, v in scores.items()}, "detail": detail}

    cls = max(scores, key=scores.get)
    top = scores[cls]
    second = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0.0
    conf = (top - second) / top if top > 0 else 0.0
    conf = max(0.3, min(0.99, round(conf, 4)))
    return cls, conf, {"scores": {k: round(v, 3) for k, v in scores.items()}, "detail": detail}


# ------------------------------------------------------------------
# Dataset collection
# ------------------------------------------------------------------
def collect_images(source: str) -> list[dict]:
    items = []
    if source in ("figaro", "all"):
        for t in ["lurus", "bergelombang", "keriting", "sangat-keriting"]:
            for p in sorted((FIGARO / t).glob("*.jpg")):
                items.append({
                    "image_id": f"figaro1k/{t}/{p.name}",
                    "relpath": str(p.relative_to(BASE)).replace("\\", "/"),
                    "source": "figaro1k",
                })
    if source in ("extra", "all"):
        for d in sorted(EXTRA.iterdir()) if EXTRA.exists() else []:
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.jpg")):
                items.append({
                    "image_id": f"extra/{d.name}/{p.name}",
                    "relpath": str(p.relative_to(BASE)).replace("\\", "/"),
                    "source": "extra",
                })
    return items


def main():
    ap = argparse.ArgumentParser(description="Tahap 1 — Gate viewpoint (paksa pilih 4 kelas).")
    ap.add_argument("--source", default="figaro", choices=["figaro", "extra", "all"])
    ap.add_argument("--max", type=int, default=0, help="Batasi jumlah gambar (0=semua)")
    ap.add_argument("--all", action="store_true", help="Proses semua gambar")
    ap.add_argument("--v-min", type=float, default=0.5)
    ap.add_argument("--min-det", type=float, default=0.3)
    ap.add_argument("--out", default=str(REPORTS / "viewpoint_predictions.json"))
    ap.add_argument("--pred-paradigm", default="gate_v1", help="Versi/tag paradigma gate")
    args = ap.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    print("=== TAHAP 1: Gate Viewpoint (paksa pilih) ===")
    print(f"source={args.source}")

    items = collect_images(args.source)
    if not args.all and args.max > 0:
        items = items[: args.max]
    print(f"gambar diproses: {len(items)}")

    if not POSE_MODEL.exists() or not FACE_MODEL.exists():
        print(f"ERROR: model tidak lengkap. pose={POSE_MODEL.exists()} face={FACE_MODEL.exists()}")
        return

    pose_lk = make_pose(POSE_MODEL, args.min_det)
    face_det = make_face(FACE_MODEL, args.min_det)
    face_lm_lk = None
    if FACE_LM_MODEL.exists():
        face_lm_lk = make_face_landmarker(FACE_LM_MODEL, args.min_det)
        print(f"Face Landmarker: {FACE_LM_MODEL.name}")
    else:
        print("WARN: face_landmarker.task tidak ada -> pakai BlazeFace saja (kurang andal)")

    records = []
    for i, item in enumerate(items, 1):
        p = BASE / item["relpath"]
        try:
            im = Image.open(p).convert("RGB")
            arr = np.asarray(im)
        except Exception as exc:
            records.append({**item, "error": f"load: {exc}"})
            continue

        face = face_signal(face_det, arr)
        face_lm = face_landmark_signal(face_lm_lk, arr) if face_lm_lk else {}
        pose = pose_signal(pose_lk, arr, args.v_min)
        cls, conf, detail = decide_viewpoint(face, pose, face_lm)

        records.append({
            **item,
            "predicted_viewpoint": cls,
            "confidence": conf,
            "face": face,
            "face_lm": face_lm,
            "pose": {k: v for k, v in pose.items() if k in (
                "pose_present", "ears_both_visible", "nose_visible", "shoulder_width",
                "frontal_face_strong", "eyes_both_visible", "shoulder_both_visible",
                "shoulder_one_only", "elbow_one_only", "shoulder_vis_diff",
            )},
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
        "phase": "1_viewpoint_gate",
        "paradigm": args.pred_paradigm,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": args.source,
        "n_total": len(records),
        "distribution": dict(dist),
        "classes": VIEWPOINT_CLASSES,
        "note": "Prediksi paksa pilih (4 kelas). Verifikasi manusia memakai file ini.",
        "records": records,
    }
    out = Path(args.out)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== DISTRIBUSI PREDIKSI ===")
    for c in VIEWPOINT_CLASSES:
        print(f"  {c:18s} {dist.get(c, 0)}")
    if dist.get("error"):
        print(f"  error: {dist['error']}")
    print(f"\nReport -> {out}")


if __name__ == "__main__":
    main()
