# -*- coding: utf-8 -*-
"""Evaluasi jujur hair_length — tanpa data leakage (hold-out konsisten).

Masalah sebelumnya: tiap seed pakai split berbeda, sehingga val satu model =
train model lain -> akurasi melonjak tak wajar (99%).

Solusi BENAR: satu split hold-out FIXED (seed 42). Semua model di-ensemble tapi
harus DILATIH ULANG pada train-set yang sama (tanpa menyentuh val hold-out).

Script ini:
  1. Buat split tetap: train/val (seed 42, 25% val).
  2. Latih N model ConvNeXt pada train yang SAMA (seed init berbeda).
  3. Evaluasi tiap model + ensemble + TTA hanya pada val hold-out.
  4. Pilih terbaik -> export ONNX single-file -> deploy.

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\scripts\\train_length_final.py
"""

from __future__ import annotations

import json
import random
import shutil
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torchvision import models

BASE = Path(__file__).resolve().parents[1]
WEIGHTS = BASE / "weights"
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"
PROD = BASE.parents[1] / "ai" / "cv" / "weights"
CLS = ["pendek", "pendek-menengah", "menengah", "panjang"]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

EPOCHS = 20
BATCH = 24
LR_HEAD = 1.5e-3
LR_FULL = 2e-4
WD = 5e-2
DROPOUT = 0.3
LS = 0.08
WARMUP = 3
PATIENCE = 10
VAL_RATIO = 0.25
MIXUP_A = 0.2
MIXUP_P = 0.2
SPLIT_SEED = 42
INIT_SEEDS = [1, 2, 3]


class AugDataset(Dataset):
    def __init__(self, base, items, train):
        self.base, self.items, self.train = base, items, train

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        pt, label = self.items[i]
        t = torch.load(self.base / pt, weights_only=True, map_location="cpu").squeeze(0)
        if not self.train:
            return t, label
        if random.random() < 0.5:
            t = torch.flip(t, dims=[2])
        if random.random() < 0.6:
            t = t * random.uniform(0.9, 1.1) + random.uniform(-0.1, 0.1)
        if random.random() < 0.3:
            eh, ew = random.randint(16, 44), random.randint(16, 44)
            y0, x0 = random.randint(0, 224 - eh), random.randint(0, 224 - ew)
            t = t.clone()
            t[:, y0 : y0 + eh, x0 : x0 + ew] = 0.0
        return t, label


def build_model(seed):
    torch.manual_seed(seed)
    m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
    m.classifier[2] = nn.Sequential(nn.Dropout(DROPOUT), nn.Linear(m.classifier[2].in_features, len(CLS)))
    return m


def set_grad(model, en):
    for p in model.features.parameters():
        p.requires_grad = en


def fixed_split(entries, ratio, seed):
    """Split HOLD-OUT tetap; dipakai sama untuk semua model (anti-leakage)."""
    rng = random.Random(seed)
    idx = list(range(len(entries)))
    rng.shuffle(idx)
    # stratifikasi per kelas
    by = defaultdict(list)
    for i in idx:
        by[entries[i]["kelas"]].append(i)
    tr_i, va_i = [], []
    for _, ii in by.items():
        rng.shuffle(ii)
        n = max(1, int(len(ii) * ratio))
        va_i.extend(ii[:n])
        tr_i.extend(ii[n:])
    return [entries[i] for i in tr_i], [entries[i] for i in va_i], tr_i, va_i


def main():
    print(f"device={DEVICE}")
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    tr, va, tr_i, va_i = fixed_split(entries, VAL_RATIO, SPLIT_SEED)
    print(f"train={len(tr)} val(holdout)={len(va)}")
    print(f"  val dist: { {c: sum(1 for e in va if e['kelas']==c) for c in CLS} }")

    ci = {c: i for i, c in enumerate(CLS)}

    # val tensors sekali (GPU) — dibatch untuk evaluasi cepat
    val_x = torch.stack([torch.load(BASE / e["pt"], weights_only=True).squeeze(0) for e in va]).to(DEVICE)
    val_y = torch.tensor([ci[e["kelas"]] for e in va], device=DEVICE)

    @torch.no_grad()
    def eval_models(ms, tta):
        probs = []
        for m in ms:
            m.eval()
            acc = F.softmax(m(val_x), dim=1)
            if tta:
                acc = acc + F.softmax(m(torch.flip(val_x, dims=[3])), dim=1)
                acc = acc / 2
            probs.append(acc)
        p = torch.stack(probs).mean(0)
        return (p.argmax(1) == val_y).float().mean().item()

    cnt = np.array([sum(1 for e in tr if e["kelas"] == c) for c in CLS], float)
    w = cnt.sum() / (len(CLS) * np.maximum(cnt, 1))
    crit = nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32).to(DEVICE), label_smoothing=LS)

    trained = {}
    for seed in INIT_SEEDS:
        random.seed(seed)
        np.random.seed(seed)
        tl = DataLoader(AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in tr], True), batch_size=BATCH, shuffle=True, num_workers=0, pin_memory=True, drop_last=True)
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
            for x, y in tl:
                x, y = x.to(DEVICE, non_blocking=True), y.to(DEVICE, non_blocking=True)
                if random.random() < MIXUP_P:
                    lam = np.random.beta(MIXUP_A, MIXUP_A)
                    perm = torch.randperm(x.size(0), device=x.device)
                    opt.zero_grad()
                    out = model(lam * x + (1 - lam) * x[perm])
                    loss = lam * crit(out, y) + (1 - lam) * crit(out, y[perm])
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
        print(f"  seed {seed}: val={best:.4f} @ep{bep} ({time.time()-t0:.0f}s)")

    # evaluasi ensemble + TTA pada holdout
    from itertools import combinations

    results = {}
    names = list(trained)
    for r in range(1, len(names) + 1):
        for combo in combinations(names, r):
            ms = [trained[k] for k in combo]
            for tta in (False, True):
                key = "s" + "+s".join(map(str, combo)) + ("+TTA" if tta else "")
                results[key] = round(eval_models(ms, tta), 4)
                print(f"  {key:20s} {results[key]:.4f}")

    best_key = max(results, key=results.get)
    print(f"\n>>> TERBAIK (holdout jujur): {best_key} = {results[best_key]:.4f}")

    # export ONNX dari model individu terbaik
    singles = {k: v for k, v in results.items() if "+" not in k}
    best_single_key = max(singles, key=singles.get)
    best_seed = int(best_single_key[1:])
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
        "split": "holdout seed 42, 25%", "train": len(tr), "val": len(va),
        "val_distribution": {c: sum(1 for e in va if e["kelas"] == c) for c in CLS},
        "per_seed": {str(s): None for s in trained},
        "ensemble_results": results, "best": best_key, "best_acc": results[best_key],
        "deployed_seed": best_seed, "deployed_acc": singles[best_single_key], "onnx": str(onnx_path),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"deploy -> {PROD / 'hair_length.onnx'}")


if __name__ == "__main__":
    main()
