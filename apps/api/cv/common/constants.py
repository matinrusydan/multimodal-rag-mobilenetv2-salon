# -*- coding: utf-8 -*-
"""Konstanta bersama — label tetap & path config. JANGAN ubah nama kelas sembarangan."""

from __future__ import annotations

from pathlib import Path

# ------------------------------------------------------------------
# Path
# ------------------------------------------------------------------
CV_DIR = Path(__file__).resolve().parents[1]        # apps/api/cv
WEIGHTS = CV_DIR / "weights"                       # model MediaPipe & ONNX
DATASET = CV_DIR / "dataset"                       # dataset mentah
FIGARO = DATASET / "figaro1k"
EXTRA = DATASET / "extra"

# Model MediaPipe (pretrained)
POSE_MODEL = WEIGHTS / "pose_landmarker_lite.task"
POSE_MODEL_HEAVY = WEIGHTS / "pose_landmarker_heavy.task"
FACE_MODEL = WEIGHTS / "blaze_face_short_range.tflite"
FACE_LM_MODEL = WEIGHTS / "face_landmarker.task"

# ------------------------------------------------------------------
# Label tetap (konsisten dengan apps/ai & UI — jangan diubah)
# ------------------------------------------------------------------

# Viewpoint (gate posisi) — 3 kelas
VIEWPOINT_CLASSES = ["depan", "samping", "belakang"]
VIEWPOINT_LABELS_ID = {"depan": "Depan", "samping": "Samping", "belakang": "Belakang"}

# Hair type — 4 kelas
HAIR_TYPE_CLASSES = ["lurus", "bergelombang", "keriting", "sangat-keriting"]

# Hair length — 4 kelas
HAIR_LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]

# Kelas viewpoint yang DITERIMA untuk analisis rambut
VIEWPOINT_ACCEPTED = {"belakang"}

# ------------------------------------------------------------------
# Preprocessing
# ------------------------------------------------------------------
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
INPUT_SIZE = 224
RESIZE_SIDE = 256

SEED = 42
