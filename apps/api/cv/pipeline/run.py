# -*- coding: utf-8 -*-
"""pipeline/run.py — Orkestrasi end-to-end: foto -> type + length.

Alur:
  foto -> preprocessing -> hair_type ONNX + hair_length ONNX
  -> hasil JSON

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" pipeline\\run.py --image path\\foto.jpg
  & ".venv\\Scripts\\python.exe" pipeline\\run.py --image path\\foto.jpg --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import HAIR_LENGTH_CLASSES, HAIR_TYPE_CLASSES
from common.preprocessing import preprocess_file

HERE = Path(__file__).resolve().parent


def run_onnx(onnx_path: Path, arr_tensor: np.ndarray, classes: list[str]) -> dict:
    """Klasifikasi via ONNX. arr_tensor: NCHW float32."""
    import onnxruntime as ort
    if not onnx_path.exists():
        return {"label": None, "confidence": None, "error": f"model tidak ada: {onnx_path.name}"}
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0].name
    out = sess.run(None, {inp: arr_tensor})[0]
    logits = np.asarray(out, dtype=np.float32)[0]
    e = np.exp(logits - logits.max()); probs = e / e.sum()
    idx = int(probs.argmax())
    return {"label": classes[idx], "confidence": round(float(probs[idx]), 4)}


def main():
    ap = argparse.ArgumentParser(description="Pipeline CV end-to-end.")
    ap.add_argument("--image", required=True)
    ap.add_argument("--json", action="store_true", help="Output JSON saja")
    args = ap.parse_args()

    from pipeline.adapters import model_paths
    parts = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(parts))

    tensor, _ = preprocess_file(args.image)
    paths = model_paths()
    ht = run_onnx(Path(paths["hair_type"]), tensor, HAIR_TYPE_CLASSES)
    hl = run_onnx(Path(paths["hair_length"]), tensor, HAIR_LENGTH_CLASSES)
    result = {
        "image": str(args.image),
        "decision": "ok",
        "hair_type": ht,
        "hair_length": hl,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=== Pipeline Result ===")
        print(f"  decision : {result['decision']}")
        if result["decision"] == "ok":
            print(f"  hair_type: {result['hair_type']}")
            print(f"  hair_length: {result['hair_length']}")


if __name__ == "__main__":
    main()
