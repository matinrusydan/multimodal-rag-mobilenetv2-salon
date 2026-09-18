# -*- coding: utf-8 -*-
"""Ekstraksi fitur geometris rambut dari GT mask Figaro-1k (Fase 3.0).

Sumber: apps/api/cv/dataset/figaro-1k.zip
  - Original/{Training,Testing}/FrameXXXXX-org.jpg
  - GT/{Training,Testing}/FrameXXXXX-gt.pbm   (mask biner rambut, putih=rambut)

Untuk setiap citra dihitung fitur geometris dari GT mask:
  - area_ratio      : luas rambut / luas citra           (massa rambut relatif)
  - bbox_h, bbox_w  : tinggi & lebar bounding box rambut (piksel)
  - bbox_aspect     : bbox_h / bbox_w                    (memanjang = panjang)
  - fill_ratio      : luas rambut / (bbox_h * bbox_w)    (kerapatan dalam bbox)
  - solidity        : luas rambut / luas convex hull      (kepadatan massa; coil→rendah)
  - span_ratio      : bbox_h / image_h                    (seberapa jauh rambut membentang vertikal)
  - face_ratio      : bbox_h / tinggi_wajah (bila wajah terdeteksi) — normalisasi antar-foto
  - thickness_index : area_ratio / span_ratio             (proxy ketebalan massa)

Normalisasi rasio (mengikuti arahan): foto user bisa close-up s/d punggung, jadi
rasio memakai acuan WAJAH (selalu ada) via deteksi wajah mediapipe; bila wajah
tak terdeteksi, pakai span_ratio sebagai fallback.

Output:
  apps/api/cv/reports/hair_geometry.json         (fitur per frame + ringkasan per kelas)
  apps/api/cv/reports/hair_geometry_summary.json (statistik per kelas)

Jalankan (venv CV: cv2 + skimage + mediapipe + PIL):
  apps\\api\\cv\\.venv\\Scripts\\python.exe apps\\api\\cv\\scripts\\extract_hair_geometry.py [--max N] [--no-face]
"""

from __future__ import annotations

import argparse
import io
import json
import statistics
import urllib.request
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parents[1]
DATASET_ZIP = BASE / "dataset" / "figaro-1k.zip"
REPORTS = BASE / "reports"
OUT_JSON = REPORTS / "hair_geometry.json"
OUT_SUMMARY = REPORTS / "hair_geometry_summary.json"
FACE_MODEL = BASE / "weights" / "blaze_face_short_range.tflite"
FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_detector/"
    "blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
)

# Kelas Figaro -> 4 kelas salon (urutan frame)
CLASSES = [
    ("lurus", 1, 150),
    ("bergelombang", 151, 300),
    ("keriting", 301, 450),
    ("sangat-keriting", 451, 600),
]


def class_of(frame: int) -> str | None:
    for name, lo, hi in CLASSES:
        if lo <= frame <= hi:
            return name
    return None


def load_mask(pbm_bytes: bytes) -> np.ndarray | None:
    """PBM P4 -> numpy bool (True=rambut/putih)."""
    try:
        img = Image.open(io.BytesIO(pbm_bytes))
        arr = np.array(img)
        return arr > 0
    except Exception:
        return None


def ensure_face_model() -> Path | None:
    if FACE_MODEL.exists():
        return FACE_MODEL
    try:
        FACE_MODEL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FACE_MODEL_URL, FACE_MODEL)
        return FACE_MODEL
    except Exception as exc:
        print(f"WARN: gagal unduh face model: {exc}")
        return None


class FaceDetector:
    """Wrapper mediapipe tasks FaceDetector (opsional)."""

    def __init__(self) -> None:
        self.detector = None
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision

            model_path = ensure_face_model()
            if model_path is None:
                return
            opts = vision.FaceDetectorOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
                min_detection_confidence=0.3,
            )
            self.detector = vision.FaceDetector.create_from_options(opts)
        except Exception as exc:
            print(f"WARN: face detector tidak aktif: {exc}")

    def face_height(self, bgr: np.ndarray) -> float | None:
        if self.detector is None:
            return None
        try:
            import mediapipe as mp

            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = self.detector.detect(mp_img)
            if not res.detections:
                return None
            # ambil deteksi terbesar
            boxes = []
            h, w = bgr.shape[:2]
            for det in res.detections:
                bb = det.bounding_box
                boxes.append((bb.width * bb.height, bb.height))
            boxes.sort(reverse=True)
            return float(boxes[0][1])
        except Exception:
            return None


def largest_component(mask: np.ndarray) -> np.ndarray:
    """Ambil komponen terhubung terbesar (buang noise)."""
    num, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8
    )
    if num <= 1:
        return mask
    # label 0 = background
    areas = stats[1:, cv2.CC_STAT_AREA]
    idx = int(np.argmax(areas)) + 1
    return labels == idx


def geometry_features(mask: np.ndarray, image_h: int, face_h: float | None) -> dict:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return {}
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    bbox_w = x1 - x0 + 1
    bbox_h = y1 - y0 + 1
    area = int(mask.sum())
    img_area = image_h * (image_h if image_h else 1)
    image_w = int(mask.shape[1])

    # convex hull solidity (kepadatan massa; coil/kribo cenderung rendah)
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull_area = 0.0
    if contours:
        biggest = max(contours, key=cv2.contourArea)
        hull = cv2.convexHull(biggest)
        hull_area = float(cv2.contourArea(hull))

    area_ratio = area / (image_h * image_w) if image_h and image_w else 0.0
    span_ratio = bbox_h / image_h if image_h else 0.0
    fill_ratio = area / (bbox_h * bbox_w) if bbox_h and bbox_w else 0.0
    solidity = area / hull_area if hull_area > 0 else 0.0
    thickness_index = area_ratio / span_ratio if span_ratio > 0 else 0.0

    return {
        "img_h": image_h,
        "img_w": image_w,
        "area": area,
        "area_ratio": round(area_ratio, 5),
        "bbox_h": bbox_h,
        "bbox_w": bbox_w,
        "bbox_aspect": round(bbox_h / bbox_w, 4) if bbox_w else 0.0,
        "fill_ratio": round(fill_ratio, 4),
        "solidity": round(solidity, 4),
        "span_ratio": round(span_ratio, 4),
        "thickness_index": round(thickness_index, 4),
        "face_h": round(face_h, 1) if face_h else None,
        "face_ratio": round(bbox_h / face_h, 4) if face_h else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="batasi jumlah citra (0=semua)")
    ap.add_argument("--no-face", action="store_true", help="lewati deteksi wajah")
    args = ap.parse_args()

    if not DATASET_ZIP.exists():
        raise SystemExit(f"zip tidak ditemukan: {DATASET_ZIP}")

    REPORTS.mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(DATASET_ZIP)
    names = set(z.namelist())

    detector = None if args.no_face else FaceDetector()
    frames = sorted(
        int(p.stem.split("Frame")[1].split("-")[0])
        for p in (Path(n) for n in names)
        if "Original" in str(p) and p.name.endswith("-org.jpg")
        and p.stem.startswith("Frame")
    )
    if args.max:
        frames = frames[: args.max]

    records: list[dict] = []
    misses = 0
    for i, frame in enumerate(frames, 1):
        cls = class_of(frame)
        if cls is None:
            continue
        org_candidates = [n for n in names if f"Frame{frame:05d}-org.jpg" in n]
        gt_candidates = [n for n in names if f"Frame{frame:05d}-gt.pbm" in n]
        if not org_candidates or not gt_candidates:
            misses += 1
            continue
        img_bytes = z.read(org_candidates[0])
        mask = load_mask(z.read(gt_candidates[0]))
        if mask is None:
            misses += 1
            continue

        bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            misses += 1
            continue
        image_h, image_w = bgr.shape[:2]
        # pastikan ukuran mask = ukuran citra
        if mask.shape != (image_h, image_w):
            mask = cv2.resize(mask.astype(np.uint8), (image_w, image_h), interpolation=cv2.INTER_NEAREST) > 0

        mask = largest_component(mask)
        face_h = None if detector is None else detector.face_height(bgr)
        feats = geometry_features(mask, image_h, face_h)
        if not feats:
            misses += 1
            continue
        feats.update({"frame": frame, "kelas": cls})
        records.append(feats)
        if i % 50 == 0:
            print(f"  {i}/{len(frames)} diproses...")

    z.close()

    OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    # ringkasan per kelas
    summary: dict[str, dict] = {}
    keys = ["area_ratio", "bbox_aspect", "fill_ratio", "solidity", "span_ratio", "thickness_index", "face_ratio"]
    for cls, _, _ in CLASSES:
        rows = [r for r in records if r["kelas"] == cls]
        if not rows:
            continue
        summary[cls] = {"n": len(rows)}
        for k in keys:
            vals = [r[k] for r in rows if r.get(k) is not None]
            if vals:
                summary[cls][k] = {
                    "mean": round(statistics.mean(vals), 4),
                    "median": round(statistics.median(vals), 4),
                    "stdev": round(statistics.pstdev(vals), 4) if len(vals) > 1 else 0.0,
                    "min": round(min(vals), 4),
                    "max": round(max(vals), 4),
                }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nSelesai. {len(records)} citra, {misses} dilewati.")
    print(f"JSON    -> {OUT_JSON}")
    print(f"Summary -> {OUT_SUMMARY}\n")
    for cls, s in summary.items():
        ar = s.get("area_ratio", {})
        ba = s.get("bbox_aspect", {})
        sol = s.get("solidity", {})
        print(f"  {cls:16s} n={s['n']:3d} area_ratio={ar.get('mean')} bbox_aspect={ba.get('mean')} solidity={sol.get('mean')}")


if __name__ == "__main__":
    main()
