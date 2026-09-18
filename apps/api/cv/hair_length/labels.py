# -*- coding: utf-8 -*-
"""hair_length/labels.py — Label tetap panjang rambut."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import HAIR_LENGTH_CLASSES  # noqa: F401

HAIR_LENGTH_LABELS = HAIR_LENGTH_CLASSES
LABELS_ID = {
    "pendek": "Pendek",
    "pendek-menengah": "Pendek-Menengah",
    "menengah": "Menengah",
    "panjang": "Panjang",
}
