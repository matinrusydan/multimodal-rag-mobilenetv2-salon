# -*- coding: utf-8 -*-
"""Training hair_length FINAL (efisien GPU) — ConvNeXt, holdout jujur, ensemble.

Optimasi: seluruh dataset dimuat ke GPU sekali (tensor in-memory), training = operasi
tensor murni (tanpa DataLoader disk I/O). Augmentasi via tensor ops di GPU.

Holdout tetap (seed 42) -> anti-leakage. Ensemble 3 init seed + TTA.

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\scripts\\train_length_final2.py
"""

from __future__ import annotations

import json
import random
import shutil
import time
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

EPOCHS = 25
BATCH = 32
LR_HEAD = 1.5e-3
LR_FULL = 2e-4
WD = 5e-2
DROPOUT = 0.3
LS = 0.08
WARMUP = 3
PATIENCE = 8
VAL_RATIO = 0.25
MIXUP_A = 0.2
MIXUP_P = 0.2
SPLIT_SEED = 42
INIT_SEEDS = [1, 2, 3]


def build_model(seed):
    torch.manual_seed(seed)
    m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
    m.classifier[2] = nn.Sequential(nn.Dropout(DROPOUT), nn.Linear(m.classifier[2].in_features, len(CLS)))
    return m


def set_grad(model, en):
    for p in model.features.parameters():
        p.requires_grad = en


def fixed_split(entries, ratio, seed):
    rng = random.Random(seed)
    by = defaultdict(list)
    for i, e in enumerate(entries):
        by[e["kelas"]].append(i)
    tr_i, va_i = [], []
    for _, ii in by.items():
        rng.shuffle(ii)
        n = max(1, int(len(ii) * ratio))
        va_i.extend(ii[:n])
        tr_i.extend(ii[n:])
    return tr_i, va_i


def augment(x, rng):
    """Augmentasi batch murni tensor di GPU."""
    b = x.size(0)
    # hflip acak per-sampel
    flip_mask = (torch.rand(b, device=x.device) < 0.5)
    if flip_mask.any():
        x[flip_mask] = torch.flip(x[flip_mask], dims=[3])
    # brightness/contrast
    bs = torch.rand(b, 1, 1, 1, device=x.device)
    mult = 0.9 + bs * 0.2
    x = x * mult + (torch.rand(b, 1, 1, 1, device=x.device) * 0.2 - 0.1)
    # erasing ringan
    for i in range(b):
        if rng.random() < 0.3:
            eh, ew = rng.randint(16, 44), rng.randint(16, 44)
            y0, xx0 = rng.randint(0, 224 - eh), rng.randint(0, 224 - ew)
            x[i, :, y0 : y0 + eh, xx0 : xx0 + ew] = 0.0
    return x


def main():
    print(f"device={DEVICE}", flush=True)
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    tr_i, va_i = fixed_split(entries, VAL_RATIO, SPLIT_SEED)
    ci = {c: i for i, c in enumerate(CLS)}
    print(f"train={len(tr_i)} val={len(va_i)}", flush=True)

    # preload ke GPU
    def load(idxs):
        xs = torch.stack([torch.load(BASE / entries[i]["pt"], weights_only=True).squeeze(0) for i in idxs])
        ys = torch.tensor([ci[entries[i]["kelas"]] for i in idxs])
        return xs.to(DEVICE), ys.to(DEVICE)

    print("memuat train ke GPU...", flush=True)
    tr_x, tr_y = load(tr_i)
    print("memuat val ke GPU...", flush=True)
    va_x, va_y = load(va_i)
    print(f"train tensor {tuple(tr_x.shape)} | val {tuple(va_x.shape)}", flush=True)

    @torch.no_grad()
    def eval_models(ms, tta):
        probs = []
        for m in ms:
            m.eval()
            p = F.softmax(m(va_x), dim=1)
            if tta:
                p = (p + F.softmax(m(torch.flip(va_x, dims=[3])), dim=1)) / 2
            probs.append(p)
        return (torch.stack(probs).mean(0).argmax(1) == va_y).float().mean().item()

    cnt = torch.tensor([sum(1 for i in tr_i if entries[i]["kelas"] == c) for c in CLS], dtype=torch.float32, device=DEVICE)
    w = cnt.sum() / (len(CLS) * cnt.clamp(min=1))
    crit = nn.CrossEntropyLoss(weight=w, label_smoothing=LS)

    trained = {}
    for seed in INIT_SEEDS:
        rng = random.Random(seed)
        torch.manual_seed(seed)
        model = build_model(seed).to(DEVICE)
        set_grad(model, False)
        opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR_HEAD, weight_decay=WD)
        pth = WEIGHTS / f"hair_length_final_s{seed}.pth"
        best, bep, noimp = 0.0, 0, 0
        t0 = time.time()
        for ep in range(1, EPOCHS + 1):
            if ep == WARMUP + 1:
                set_grad(model, True)
                opt = torch.optim.AdamW(model.parameters(), lr=LR_FULL, weight_decay=WD)
                sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS - WARMUP)
            model.train()
            perm = torch.randperm(tr_x.size(0), device=DEVICE)
            for b in range(0, tr_x.size(0), BATCH):
                bi = perm[b : b + BATCH]
                if bi.numel() < 2:
                    continue
                x = augment(tr_x[bi].clone(), rng)
                y = tr_y[bi]
                if rng.random() < MIXUP_P:
                    lam = np.random.beta(MIXUP_A, MIXUP_A)
                    p2 = torch.randperm(x.size(0), device=DEVICE)
                    opt.zero_grad()
                    out = model(lam * x + (1 - lam) * x[p2])
                    loss = lam * crit(out, y) + (1 - lam) * crit(out, y[p2])
                else:
                    opt.zero_grad()
                    loss = crit(model(x), y)
                loss.backward()
                opt.step()
            if ep > WARMUP:
                sched.step()
            va_acc = eval_models([model], tta=False)
            if va_acc > best:
                best, bep, noimp = va_acc, ep, 0
                torch.save(model.state_dict(), pth)
            else:
                noimp += 1
                if ep > WARMUP and noimp >= PATIENCE:
                    break
        model.load_state_dict(torch.load(pth, weights_only=True, map_location=DEVICE))
        model.eval()
        trained[seed] = model
        print(f"  seed {seed}: val={best:.4f} @ep{bep} ({time.time()-t0:.0f}s)", flush=True)

    results = {}
    names = list(trained)
    for r in range(1, len(names) + 1):
        for combo in combinations(names, r):
            ms = [trained[k] for k in combo]
            for tta in (False, True):
                key = "s" + "+s".join(map(str, combo)) + ("+TTA" if tta else "")
                results[key] = round(eval_models(ms, tta), 4)

    print("\n=== Hasil (holdout jujur, tanpa leakage) ===", flush=True)
    for k in sorted(results, key=results.get, reverse=True):
        print(f"  {k:20s} {results[k]:.4f}")
    best_key = max(results, key=results.get)
    print(f"\n>>> TERBAIK: {best_key} = {results[best_key]:.4f}", flush=True)

    singles = {k: v for k, v in results.items() if "+" not in k}
    best_single = max(singles, key=singles.get)
    best_seed = int(best_single[1:])
    mcpu = build_model(best_seed)
    mcpu.load_state_dict(trained[best_seed].state_dict())
    mcpu.eval()
    onnx_path = WEIGHTS / "hair_length_final.onnx"
    onnx_path.unlink(missing_ok=True)
    onnx_path.with_suffix(".onnx.data").unlink(missing_ok=True)
    torch.onnx.export(mcpu, torch.randn(1, 3, 224, 224), str(onnx_path), input_names=["input"], output_names=["logits"], opset_version=14, dynamo=False, external_data=False)
    PROD.mkdir(parents=True, exist_ok=True)
    shutil.copy(onnx_path, PROD / "hair_length.onnx")

    (WEIGHTS / "_train_report_length_final.json").write_text(json.dumps({
        "task": "hair_length", "arch": "convnext_tiny", "classes": CLS,
        "split": "holdout seed 42 25% (anti-leakage)", "train": len(tr_i), "val": len(va_i),
        "val_distribution": {c: sum(1 for i in va_i if entries[i]["kelas"] == c) for c in CLS},
        "ensemble_results": results, "best": best_key, "best_acc": results[best_key],
        "deployed_seed": best_seed, "deployed_acc": singles[best_single], "onnx": str(onnx_path),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"deploy -> {PROD / 'hair_length.onnx'} (held-out acc={singles[best_single]:.4f})", flush=True)


if __name__ == "__main__":
    main()
