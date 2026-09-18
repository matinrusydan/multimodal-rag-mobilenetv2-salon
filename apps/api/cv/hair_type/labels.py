# -*- coding: utf-8 -*-
"""hair_type/labels.py — Label tetap jenis rambut."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import HAIR_TYPE_CLASSES  # noqa: F401

HAIR_TYPE_LABELS = HAIR_TYPE_CLASSES
LABELS_ID = {
    "lurus": "Lurus",
    "bergelombang": "Bergelombang",
    "keriting": "Keriting",
    "sangat-keriting": "Sangat Keriting",
}
