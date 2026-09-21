# -*- coding: utf-8 -*-
"""viewpoint/evaluate.py — Bandingkan CNN vs heuristik secara JUJUR (anti-leakage).

Evaluasi hanya pada sampel yang TIDAK dipakai training (held-out), dengan
split yang sama seperti train_cnn.py (seed + VAL_RATIO yang identik).

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\evaluate.py --annotators A
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
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
DATASET = HERE / "dataset" / "index.json"

VAL_RATIO = 0.25
SPLIT_SEED = 42


def human_label(r: dict) -> str | None:
    if r["is_correct"] == "ya":
        return r["model_prediction"]
    if r["is_correct"] == "tidak":
        return r.get("correction")
    return None


def main():
    ap = argparse.ArgumentParser(description="CNN vs heuristik (jujur, anti-leakage).")
    ap.add_argument("--annotators", nargs="*", default=["A"])
    ap.add_argument("--seed", type=int, default=SPLIT_SEED)
    ap.add_argument("--val-ratio", type=float, default=VAL_RATIO)
    ap.add_argument("--dataset", default=str(DATASET), help="Index dataset (default: dataset/index.json)")
    ap.add_argument("--model", default=str(CNN_PTH), help="Model CNN .pth")
    ap.add_argument("--out", default=str(REPORTS / "viewpoint_cnn_vs_heuristic.json"))
    args = ap.parse_args()

    ds = load_json(args.dataset)["records"]
    ci = {c: i for i, c in enumerate(VIEWPOINT_CLASSES)}

    # buat split SAMA seperti train_cnn.py -> dapat daftar val (held-out)
    rng = random.Random(args.seed)
    by = defaultdict(list)
    for r in ds:
        by[r["label"]].append(r)
    val_ids = set()
    for _, ents in by.items():
        ents = sorted(ents, key=lambda e: e["image_id"]); rng.shuffle(ents)
        n = max(1, int(len(ents) * args.val_ratio))
        for e in ents[:n]:
            val_ids.add(e["image_id"])
    relmap = {r["image_id"]: r["relpath"] for r in ds}

    # ground truth manusia (hanya yang held-out)
    gt = {}
    for a in args.annotators:
        p = GT_DIR / f"viewpoint_verification_{a}.json"
        if p.exists():
            for r in load_json(p).get("records", []):
                gt[r["image_id"]] = human_label(r)
    held = {iid: lab for iid, lab in gt.items() if lab and iid in val_ids}
    print(f"verifikasi total: {len(gt)} | held-out (eval jujur): {len(held)}")

    # heuristik
    preds = {r["image_id"]: r for r in load_json(PRED).get("records", [])} if PRED.exists() else {}
    n = corr_h = 0
    for iid, lab in held.items():
        if iid not in preds:
            continue
        n += 1
        if preds[iid].get("predicted_viewpoint") == lab:
            corr_h += 1
    acc_h = corr_h / n if n else 0.0

    result = {"timestamp": datetime.now(timezone.utc).isoformat(), "n_eval": n,
              "held_out_only": True, "heuristic_accuracy": round(acc_h, 4)}

    if Path(args.model).exists() and n:
        try:
            import torch, torch.nn as nn
            from torchvision import models
            from PIL import Image
            model = models.efficientnet_v2_s(weights=None)
            model.classifier[1] = nn.Sequential(nn.Dropout(0.3), nn.Linear(model.classifier[1].in_features, len(VIEWPOINT_CLASSES)))
            model.load_state_dict(torch.load(args.model, map_location="cpu", weights_only=True))
            model.eval()

            def predict(relpath):
                im = Image.open(CV_DIR / relpath).convert("RGB").resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR)
                f = np.asarray(im, dtype=np.float32) / 255.0
                t = ((f - np.array(IMAGENET_MEAN, np.float32)) / np.array(IMAGENET_STD, np.float32)).transpose(2, 0, 1)
                with torch.no_grad():
                    out = model(torch.from_numpy(np.ascontiguousarray(t))[None, ...])
                return VIEWPOINT_CLASSES[int(out.argmax(1))]

            corr_c = nc = 0
            cm = defaultdict(Counter)
            for iid, lab in held.items():
                if iid not in relmap:
                    continue
                nc += 1
                p = predict(relmap[iid])
                if p == lab:
                    corr_c += 1
                else:
                    cm[p][lab] += 1
            result["cnn_accuracy"] = round(corr_c / nc, 4) if nc else None
            result["cnn_n_eval"] = nc
            result["cnn_confusion"] = {k: dict(v) for k, v in cm.items()}
        except Exception as exc:
            result["cnn_error"] = str(exc)[:200]

    save_json(args.out, result)
    print("\n=== CNN vs Heuristik (held-out, JUJUR) ===")
    print(f"  heuristik: {result['heuristic_accuracy']:.2%} (n={n})")
    if "cnn_accuracy" in result:
        print(f"  CNN      : {result['cnn_accuracy']:.2%} (n={result.get('cnn_n_eval')})")
        if result.get("cnn_confusion"):
            print(f"  CNN salah (pred->gt): {result['cnn_confusion']}")
    print(f"\nReport -> {args.out}")


if __name__ == "__main__":
    main()
