# -*- coding: utf-8 -*-
"""Diagnosa: akurasi model hair_length_merged DIPECAH per sumber dataset.

Tujuan: cek apakah sampel Figaro (label geometris/noisy) menurunkan akurasi.
Mengelompokkan val set menurut 'sumber' (figaro, hs40, bald, figaro-extra) lalu
hitung akurasi per kelompok.

Jalankan (venv AI atau global yang punya onnxruntime+torch):
  python apps\\api\\cv\\scripts\\diagnose_by_source.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

BASE = Path(__file__).resolve().parents[1]
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"
MODEL = BASE / "weights" / "hair_length_merged.onnx"
CLS = ["pendek", "pendek-menengah", "menengah", "panjang"]


def main() -> None:
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    sess = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
    iname, oname = sess.get_inputs()[0].name, sess.get_outputs()[0].name

    by_source: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for e in idx["index"]["val"]:
        a = torch.load(BASE / e["pt"], weights_only=True).numpy().astype(np.float32)
        pred = int(np.argmax(sess.run([oname], {iname: a})[0][0]))
        by_source[e["sumber"]].append((CLS.index(e["kelas"]), pred))

    print(f"val total: {sum(len(v) for v in by_source.values())}\n")
    for src, pairs in sorted(by_source.items()):
        n = len(pairs)
        acc = sum(1 for t, p in pairs if t == p) / n if n else 0
        # per kelas
        per = defaultdict(lambda: [0, 0])
        for t, p in pairs:
            per[CLS[t]][1] += 1
            if t == p:
                per[CLS[t]][0] += 1
        detail = " ".join(f"{c}:{v[0]}/{v[1]}" for c, v in sorted(per.items()))
        print(f"  {src:14s} n={n:4d} acc={acc:.3f} | {detail}")

    # train set juga (untuk cek overfit per sumber)
    print("\ntrain per sumber:")
    by_train: dict[str, int] = defaultdict(int)
    for e in idx["index"]["train"]:
        by_train[e["sumber"]] += 1
    for s, n in sorted(by_train.items()):
        print(f"  {s:14s} n={n}")


if __name__ == "__main__":
    main()
