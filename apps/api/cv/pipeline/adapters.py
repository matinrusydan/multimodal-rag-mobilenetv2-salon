# -*- coding: utf-8 -*-
"""pipeline/adapters.py — Adaptor ke apps/ai (runtime).

Menjembatani struktur modular baru dengan path model yang dibaca brain engine
(apps/ai/cv/weights). Tidak mengubah apps/ai; hanya menyediakan mapping path.
"""

from __future__ import annotations

from pathlib import Path

CV_DIR = Path(__file__).resolve().parents[1]        # apps/api/cv
ROOT = CV_DIR.parents[1]                            # repo root
AI_WEIGHTS = ROOT / "apps" / "ai" / "cv" / "weights"


def model_paths() -> dict:
    """Path model untuk produksi (yang dibaca apps/ai)."""
    return {
        "hair_type": str(AI_WEIGHTS / "hair_type.onnx"),
        "hair_length": str(AI_WEIGHTS / "hair_length.onnx"),
        "viewpoint_cnn": str(CV_DIR / "viewpoint" / "weights" / "viewpoint_cnn.pth"),
    }


def local_model_paths() -> dict:
    """Path model di struktur modular (eksperimen/lokal)."""
    return {
        "hair_type": str(CV_DIR / "hair_type" / "weights" / "hair_type.onnx"),
        "hair_length": str(CV_DIR / "hair_length" / "weights" / "hair_length.onnx"),
        "viewpoint_cnn": str(CV_DIR / "viewpoint" / "weights" / "viewpoint_cnn.pth"),
    }


def deploy_hint(which: str) -> str:
    """Petunjuk menyalin model modular -> apps/ai."""
    src = local_model_paths().get(which, "?")
    dst = model_paths().get(which, "?")
    return f"copy '{src}' -> '{dst}'"
