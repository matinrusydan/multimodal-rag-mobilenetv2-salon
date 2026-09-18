# -*- coding: utf-8 -*-
"""Ensemble + TTA untuk model ConvNeXt hair_length (final, akurasi tertinggi).

Menggabungkan beberapa model ConvNeXt (seed berbeda) via rata-rata softmax +
Test-Time Augmentation (hflip). Memilih konfigurasi terbaik -> salin model
champion terbaik ke produksi.

Jalankan:
  python apps\\api\\cv\\scripts\\ensemble_convnext.py
"""

from __future__ import annotations

import json
import shutil
from itertools import combinations
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

BASE = Path(__file__).resolve().parents[1]
WEIGHTS = BASE / "weights"
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"
PROD = BASE.parents[1] / "ai" / "cv" / "weights"
CLS = ["pendek", "pendek-menengah", "menengah", "panjang"]

CANDS = ["hair_length_champion.onnx", "hair_length_champ_s7.onnx", "hair_length_champ_s123.onnx", "hair_length_champ_s2024.onnx"]
VAL_RATIO = 0.25
SEED = 42


def softmax(x):
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def split(entries, ratio, seed):
    import random
    from collections import defaultdict

    rng = random.Random(seed)
    by = defaultdict(list)
    for e in entries:
        by[e["kelas"]].append(e)
    va = []
    for _, ents in by.items():
        rng.shuffle(ents)
        va.extend(ents[: max(1, int(len(ents) * ratio))])
    return va


def main():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    va = split(entries, VAL_RATIO, SEED)
    # index val terkecil (seed 2024 pakai split berbeda) -> pakai split seed 42 utk semua
    print(f"val (split seed 42, ratio {VAL_RATIO}): {len(va)}")

    sess = {}
    for name in CANDS:
        p = WEIGHTS / name
        if p.exists():
            sess[name] = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
    print(f"model: {list(sess)}")

    # preload tensor val
    tensors = [(torch.load(BASE / e["pt"], weights_only=True).numpy().astype(np.float32), CLS.index(e["kelas"])) for e in va]

    def acc_for(sub, tta):
        cor = 0
        for a, t in tensors:
            probs = []
            for s in sub.values():
                iname = s.get_inputs()[0].name
                probs.append(softmax(s.run(None, {iname: a})[0])[0])
                if tta:
                    probs.append(softmax(s.run(None, {iname: a[:, :, :, ::-1].copy()})[0])[0])
            if int(np.argmax(np.mean(probs, axis=0))) == t:
                cor += 1
        return cor / len(tensors)

    results = {}
    names = list(sess)
    for r in range(1, len(names) + 1):
        for combo in combinations(names, r):
            sub = {k: sess[k] for k in combo}
            for tta in (False, True):
                key = "+".join(k.replace("hair_length_", "").replace(".onnx", "") for k in combo) + ("+TTA" if tta else "")
                results[key] = round(acc_for(sub, tta), 4)
                print(f"  {key:55s} {results[key]:.4f}")

    best_key = max(results, key=results.get)
    print(f"\n>>> TERBAIK: {best_key} = {results[best_key]:.4f}")

    # deploy model individu terbaik (single-file, ringan)
    singles = {k: v for k, v in results.items() if "+" not in k}
    best_single = max(singles, key=singles.get)
    tag = best_single.replace("hair_length_", "").replace(".onnx", "")
    shutil.copy(WEIGHTS / f"hair_length_{tag}.onnx", PROD / "hair_length.onnx")
    print(f"deploy: {tag} -> produksi (acc={singles[best_single]:.4f})")

    (BASE / "reports" / "hair_length_convnext_ensemble.json").write_text(
        json.dumps({"val": len(va), "results": results, "best": best_key, "best_acc": results[best_key], "deployed_single": best_single, "deployed_acc": singles[best_single]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
