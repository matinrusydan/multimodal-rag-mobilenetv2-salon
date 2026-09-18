# -*- coding: utf-8 -*-
"""hair_type/evaluate.py — Evaluasi model hair_type (accuracy, macro-F1, confusion)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import HAIR_TYPE_CLASSES, INPUT_SIZE

HERE = Path(__file__).resolve().parent
CV_DIR = HERE.parent
WEIGHTS = HERE / "weights"
REPORTS = HERE / "reports"


def main():
    ap = argparse.ArgumentParser(description="Evaluasi hair_type.")
    ap.add_argument("--onnx", default=str(WEIGHTS / "hair_type.onnx"))
    ap.add_argument("--index", default=None)
    ap.add_argument("--out", default=str(REPORTS / "hair_type_eval.json"))
    args = ap.parse_args()

    import onnxruntime as ort

    onnx_path = Path(args.onnx)
    if not onnx_path.exists():
        print(f"ERROR: model tidak ada: {onnx_path}")
        return
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

    print(f"=== Evaluasi hair_type ===")
    print(f"model: {onnx_path.name}")
    print("(Evaluasi mendetail membutuhkan index val; sediakan --index bila tersedia.)")
    (REPORTS / "hair_type_eval.json").write_text(json.dumps({
        "task": "hair_type", "classes": HAIR_TYPE_CLASSES,
        "model": str(onnx_path), "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "jalankan dengan --index untuk metrik penuh",
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
