# -*- coding: utf-8 -*-
"""pipeline/run.py — Orkestrasi end-to-end: foto -> viewpoint -> type + length.

Alur:
  foto -> [viewpoint/gate] vonis
     - depan/samping -> STOP (retake)
     - belakang -> lanjut
  -> hair_type ONNX + hair_length ONNX (apps/ai weights)
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
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "viewpoint"))

from common.constants import HAIR_LENGTH_CLASSES, HAIR_TYPE_CLASSES, INPUT_SIZE, VIEWPOINT_ACCEPTED
from common.preprocessing import preprocess_file

HERE = Path(__file__).resolve().parent


def run_viewpoint(arr: np.ndarray) -> dict:
    """Vonis viewpoint via heuristik (viewpoint/gate)."""
    try:
        from gate import make_face, make_face_landmarker, make_pose, decide_viewpoint, face_signal, face_landmark_signal, pose_signal
        from common.constants import FACE_LM_MODEL, FACE_MODEL, POSE_MODEL
        pose_lk = make_pose(POSE_MODEL, 0.3)
        face_det = make_face(FACE_MODEL, 0.3)
        face_lm_lk = make_face_landmarker(FACE_LM_MODEL, 0.3) if FACE_LM_MODEL.exists() else None
        face = face_signal(face_det, arr)
        face_lm = face_landmark_signal(face_lm_lk, arr)
        pose = pose_signal(pose_lk, arr, 0.5)
        cls, conf, _ = decide_viewpoint(face, pose, face_lm)
        pose_lk.close(); face_det.close()
        if face_lm_lk:
            face_lm_lk.close()
        return {"viewpoint": cls, "confidence": conf, "valid": cls in VIEWPOINT_ACCEPTED}
    except Exception as exc:
        return {"viewpoint": None, "confidence": None, "valid": False, "error": str(exc)[:150]}


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

    tensor, roi = preprocess_file(args.image)

    vp = run_viewpoint(roi)
    result = {"image": str(args.image), "viewpoint": vp}

    if not vp["valid"]:
        result["decision"] = "retake"
        result["message"] = "Foto terlihat bukan dari belakang. Mohon foto ulang dari arah belakang."
    else:
        paths = model_paths()
        ht = run_onnx(Path(paths["hair_type"]), tensor, HAIR_TYPE_CLASSES)
        hl = run_onnx(Path(paths["hair_length"]), tensor, HAIR_LENGTH_CLASSES)
        result["decision"] = "ok"
        result["hair_type"] = ht
        result["hair_length"] = hl

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=== Pipeline Result ===")
        print(f"  viewpoint: {vp['viewpoint']} (conf {vp['confidence']})")
        print(f"  decision : {result['decision']}")
        if result["decision"] == "ok":
            print(f"  hair_type: {result['hair_type']}")
            print(f"  hair_length: {result['hair_length']}")


if __name__ == "__main__":
    main()
