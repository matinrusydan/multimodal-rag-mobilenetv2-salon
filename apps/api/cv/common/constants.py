# -*- coding: utf-8 -*-
"""Konstanta bersama — label tetap & path config. JANGAN ubah nama kelas sembarangan."""

from __future__ import annotations

from pathlib import Path

# ------------------------------------------------------------------
# Path
# ------------------------------------------------------------------
CV_DIR = Path(__file__).resolve().parents[1]        # apps/api/cv
WEIGHTS = CV_DIR / "weights"                       # model ONNX
DATASET = CV_DIR / "dataset"                       # dataset mentah
FIGARO = DATASET / "figaro1k"
EXTRA = DATASET / "extra"

# ------------------------------------------------------------------
# Label tetap (konsisten dengan apps/ai & UI — jangan diubah)
# ------------------------------------------------------------------

# Hair type — 4 kelas
HAIR_TYPE_CLASSES = ["lurus", "bergelombang", "keriting", "sangat-keriting"]

# Hair length — 4 kelas
HAIR_LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]

# ------------------------------------------------------------------
# Preprocessing
# ------------------------------------------------------------------
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
INPUT_SIZE = 224
RESIZE_SIDE = 256

SEED = 42
