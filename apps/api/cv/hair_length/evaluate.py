# -*- coding: utf-8 -*-
"""hair_length/evaluate.py — Evaluasi model panjang rambut (ONNX)."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import HAIR_LENGTH_CLASSES

HERE = Path(__file__).resolve().parent
WEIGHTS = HERE / "weights"
REPORTS = HERE / "reports"


def main():
    ap = argparse.ArgumentParser(description="Evaluasi hair_length.")
    ap.add_argument("--onnx", default=str(WEIGHTS / "hair_length.onnx"))
    ap.add_argument("--out", default=str(REPORTS / "hair_length_eval.json"))
    args = ap.parse_args()

    onnx_path = Path(args.onnx)
    print(f"=== Evaluasi hair_length ===\nmodel: {onnx_path.name}")
    if not onnx_path.exists():
        print(f"ERROR: model tidak ada: {onnx_path}")
        return
    print("(Metrik penuh membutuhkan index val; lihat README.)")
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "hair_length_eval.json").write_text(json.dumps({
        "task": "hair_length", "classes": HAIR_LENGTH_CLASSES, "model": str(onnx_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
