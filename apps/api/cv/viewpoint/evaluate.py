# -*- coding: utf-8 -*-
"""viewpoint/evaluate.py — Bandingkan CNN viewpoint vs heuristik pada val yang sama.

CNN dipakai bila tersedia (weights/viewpoint_cnn.pth). Heuristik dihitung dari
prediksi gate.py. Keduanya diukur pada data verifikasi manusia.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\evaluate.py --annotators A
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import CV_DIR, IMAGENET_MEAN, IMAGENET_STD, INPUT_SIZE, VIEWPOINT_CLASSES
from common.io_utils import load_json, save_json

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground_truth"
REPORTS = HERE / "reports"
PRED = REPORTS / "viewpoint_predictions.json"
CNN_PTH = HERE / "weights" / "viewpoint_cnn.pth"


def human_label(r: dict) -> str | None:
    if r["is_correct"] == "ya":
        return r["model_prediction"]
    if r["is_correct"] == "tidak":
        return r.get("correction")
    return None


def main():
    ap = argparse.ArgumentParser(description="Bandingkan CNN vs heuristik (viewpoint).")
    ap.add_argument("--annotators", nargs="*", default=["A"])
    ap.add_argument("--out", default=str(REPORTS / "viewpoint_cnn_vs_heuristic.json"))
    args = ap.parse_args()

    # ground truth manusia
    gt = {}
    for a in args.annotators:
        p = GT_DIR / f"viewpoint_verification_{a}.json"
        if p.exists():
            for r in load_json(p).get("records", []):
                gt[r["image_id"]] = human_label(r)

    # prediksi heuristik
    preds = {r["image_id"]: r for r in load_json(PRED).get("records", [])} if PRED.exists() else {}

    # evaluasi heuristik
    n = corr_h = 0
    for iid, label in gt.items():
        if not label or iid not in preds:
            continue
        n += 1
        if preds[iid].get("predicted_viewpoint") == label:
            corr_h += 1
    acc_h = corr_h / n if n else 0.0

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_eval": n,
        "heuristic_accuracy": round(acc_h, 4),
    }

    # evaluasi CNN (jika model ada)
    if CNN_PTH.exists() and preds:
        try:
            import torch
            import torch.nn as nn
            from torchvision import models
            from PIL import Image

            model = models.efficientnet_v2_s(weights=None)
            model.classifier[1] = nn.Sequential(nn.Dropout(0.3), nn.Linear(model.classifier[1].in_features, len(VIEWPOINT_CLASSES)))
            model.load_state_dict(torch.load(CNN_PTH, map_location="cpu", weights_only=True))
            model.eval()
            ci = {c: i for i, c in enumerate(VIEWPOINT_CLASSES)}

            def predict(relpath):
                im = Image.open(CV_DIR / relpath).convert("RGB").resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR)
                f = np.asarray(im, dtype=np.float32) / 255.0
                t = ((f - np.array(IMAGENET_MEAN, np.float32)) / np.array(IMAGENET_STD, np.float32)).transpose(2, 0, 1)
                with torch.no_grad():
                    out = model(torch.from_numpy(np.ascontiguousarray(t))[None, ...])
                return VIEWPOINT_CLASSES[int(out.argmax(1))]

            corr_c = n_c = 0
            for iid, label in gt.items():
                if not label or iid not in preds:
                    continue
                n_c += 1
                if predict(preds[iid]["relpath"]) == label:
                    corr_c += 1
            result["cnn_accuracy"] = round(corr_c / n_c, 4) if n_c else None
            result["cnn_n_eval"] = n_c
        except Exception as exc:
            result["cnn_error"] = str(exc)[:200]

    save_json(args.out, result)
    print("=== Viewpoint: CNN vs Heuristik ===")
    print(f"  heuristik: {result['heuristic_accuracy']:.2%} (n={n})")
    if "cnn_accuracy" in result:
        print(f"  CNN      : {result['cnn_accuracy']:.2%} (n={result.get('cnn_n_eval')})")
    print(f"\nReport -> {args.out}")


if __name__ == "__main__":
    main()
