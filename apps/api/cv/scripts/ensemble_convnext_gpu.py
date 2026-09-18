# -*- coding: utf-8 -*-
"""Ensemble + TTA hair_length (ConvNeXt) memakai torch di GPU.

Membaca bobot .pth (bukan ONNX) -> inferensi GPU cepat. Rata-rata softmax
seluruh model + TTA hflip; pilih kombinasi terbaik lalu export ONNX champion
dari model individu terbaik.

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\scripts\\ensemble_convnext_gpu.py
"""

from __future__ import annotations

import json
import random
import shutil
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models

BASE = Path(__file__).resolve().parents[1]
WEIGHTS = BASE / "weights"
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"
PROD = BASE.parents[1] / "ai" / "cv" / "weights"
CLS = ["pendek", "pendek-menengah", "menengah", "panjang"]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
VAL_RATIO = 0.25
SEED = 42

CANDS = {
    "champion": "hair_length_champion.pth",
    "s7": "hair_length_champ_s7.pth",
    "s123": "hair_length_champ_s123.pth",
    "s2024": "hair_length_champ_s2024.pth",
}


def build_model():
    m = models.convnext_tiny(weights=None)
    m.classifier[2] = nn.Sequential(nn.Dropout(0.3), nn.Linear(m.classifier[2].in_features, len(CLS)))
    return m


def split(entries, ratio, seed):
    rng = random.Random(seed)
    by = defaultdict(list)
    for e in entries:
        by[e["kelas"]].append(e)
    va = []
    for _, ents in by.items():
        rng.shuffle(ents)
        va.extend(ents[: max(1, int(len(ents) * ratio))])
    return va


@torch.no_grad()
def ensemble_acc(models_list, tensors, tta):
    """tensors: list[(tensor(1,3,224,224) GPU, label)]"""
    cor = 0
    for x, t in tensors:
        probs = []
        for m in models_list:
            probs.append(F.softmax(m(x), dim=1))
            if tta:
                probs.append(F.softmax(m(torch.flip(x, dims=[3])), dim=1))
        p = torch.stack(probs).mean(0)
        if int(p.argmax(1).item()) == t:
            cor += 1
    return cor / len(tensors)


def main():
    print(f"device={DEVICE}")
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    va = split(entries, VAL_RATIO, SEED)
    print(f"val: {len(va)}")

    # preload tensor val ke GPU
    tensors = []
    for e in va:
        x = torch.load(BASE / e["pt"], weights_only=True).to(DEVICE)
        tensors.append((x, CLS.index(e["kelas"])))

    models_loaded = {}
    for tag, fn in CANDS.items():
        p = WEIGHTS / fn
        if not p.exists():
            continue
        m = build_model().to(DEVICE)
        m.load_state_dict(torch.load(p, weights_only=True, map_location=DEVICE))
        m.eval()
        models_loaded[tag] = m
    print(f"model: {list(models_loaded)}")

    results = {}
    names = list(models_loaded)
    for r in range(1, len(names) + 1):
        for combo in combinations(names, r):
            ms = [models_loaded[k] for k in combo]
            for tta in (False, True):
                key = "+".join(combo) + ("+TTA" if tta else "")
                results[key] = round(ensemble_acc(ms, tensors, tta), 4)
                print(f"  {key:30s} {results[key]:.4f}")

    best_key = max(results, key=results.get)
    print(f"\n>>> TERBAIK: {best_key} = {results[best_key]:.4f}")

    # export ONNX dari model individu terbaik (single-file)
    singles = {k: v for k, v in results.items() if "+" not in k}
    best_single = max(singles, key=singles.get)
    print(f"model individu terbaik: {best_single} ({singles[best_single]:.4f})")

    m = models_loaded[best_single]
    m_cpu = build_model()
    m_cpu.load_state_dict(m.state_dict())
    m_cpu.eval()
    onnx_path = WEIGHTS / f"hair_length_{best_single}_final.onnx"
    onnx_path.unlink(missing_ok=True)
    onnx_path.with_suffix(".onnx.data").unlink(missing_ok=True)
    torch.onnx.export(m_cpu, torch.randn(1, 3, 224, 224), str(onnx_path), input_names=["input"], output_names=["logits"], opset_version=14, dynamo=False, external_data=False)

    PROD.mkdir(parents=True, exist_ok=True)
    shutil.copy(onnx_path, PROD / "hair_length.onnx")
    print(f"deploy -> {PROD / 'hair_length.onnx'}")

    (BASE / "reports" / "hair_length_convnext_ensemble.json").write_text(
        json.dumps({"val": len(va), "device": str(DEVICE), "results": results, "best": best_key, "best_acc": results[best_key], "deployed": best_single, "deployed_acc": singles[best_single]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
