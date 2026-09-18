# -*- coding: utf-8 -*-
"""Diagnosa menyeluruh hair_length: distribusi, gap train-val, eval per-kelas.

Menjalankan inferensi train & val pada model untuk mengukur over/underfit.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

BASE = Path(__file__).resolve().parents[1]
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"
CLS = ["pendek", "pendek-menengah", "menengah", "panjang"]


def infer(sess, pt_path, clsid):
    a = torch.load(BASE / pt_path, weights_only=True).numpy().astype(np.float32)
    pred = int(np.argmax(sess.run(None, {sess.get_inputs()[0].name: a})[0][0]))
    return clsid, pred


def eval_split(sess, entries, name):
    cm = np.zeros((4, 4), int)
    for e in entries:
        t, p = infer(sess, e["pt"], CLS.index(e["kelas"]))
        cm[t, p] += 1
    n = cm.sum()
    acc = np.trace(cm) / n if n else 0
    print(f"\n{name}: n={n} acc={acc:.4f}")
    for i, c in enumerate(CLS):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp
        pr = tp / (tp + fp) if tp + fp else 0
        rc = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0
        print(f"  {c:16s} P={pr:.3f} R={rc:.3f} F1={f1:.3f} n={cm[i, :].sum()}")
    return acc


def main() -> None:
    idx = json.loads(INDEX.read_text(encoding="utf-8"))

    # distribusi
    print("=== Distribusi dataset (semua) ===")
    for split in ("train", "val"):
        ents = idx["index"][split]
        print(f"  {split}: {len(ents)} | {dict(Counter(e['kelas'] for e in ents))}")
        print(f"     sumber: {dict(Counter(e['sumber'] for e in ents))}")

    # model clean
    model = BASE / "weights" / "hair_length_clean.onnx"
    sess = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])

    # clean subset
    train_clean = [e for e in idx["index"]["train"] if e["sumber"] != "figaro"]
    val_clean = [e for e in idx["index"]["val"] if e["sumber"] != "figaro"]

    print(f"\n=== Evaluasi {model.name} ===")
    tr = eval_split(sess, train_clean, "TRAIN (clean)")
    va = eval_split(sess, val_clean, "VAL (clean)")
    print(f"\nGAP train-val: {tr - va:+.4f}")
    if tr - va > 0.10:
        print("  -> OVERFIT (gap > 10%)")
    elif tr < 0.80 and va < 0.80:
        print("  -> UNDERFIT (keduanya rendah)")
    else:
        print("  -> GAP SEHAT")


if __name__ == "__main__":
    main()
