# -*- coding: utf-8 -*-
"""Bandingkan backbone untuk hair_length (MobileNetV2 vs V3 vs EfficientNet-B0 vs ResNet50).

Tujuan: apakah arsitektur jadi bottleneck? Evaluasi adil: split & resep sama.
Resep: label bersih, augmentasi sedang, stratified val 25%, early stop, warmup.

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\scripts\\bench_backbones.py
"""

from __future__ import annotations

import json
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models

BASE = Path(__file__).resolve().parents[1]
WEIGHTS = BASE / "weights"
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"

CLS = ["pendek", "pendek-menengah", "menengah", "panjang"]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

EPOCHS = 18
BATCH = 32
LR_HEAD = 1.5e-3
LR_FULL = 2.5e-4
WD = 2e-4
DROPOUT = 0.35
LS = 0.08
WARMUP = 3
PATIENCE = 6
VAL_RATIO = 0.25
SEED = 42


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
            t = t * random.uniform(0.92, 1.08) + random.uniform(-0.08, 0.08)
        if random.random() < 0.25:
            eh, ew = random.randint(16, 40), random.randint(16, 40)
            y0, x0 = random.randint(0, 224 - eh), random.randint(0, 224 - ew)
            t = t.clone()
            t[:, y0 : y0 + eh, x0 : x0 + ew] = 0.0
        return t, label


def make_model(name):
    if name == "mobilenet_v2":
        m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        m.classifier = nn.Sequential(nn.Dropout(DROPOUT), nn.Linear(m.last_channel, len(CLS)))
        return m, "features"
    if name == "mobilenet_v3_large":
        m = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, len(CLS))
        return m, "features"
    if name == "efficientnet_b0":
        m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(CLS))
        return m, "features"
    if name == "resnet50":
        m = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, len(CLS))
        return m, "nobn"
    if name == "convnext_tiny":
        m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, len(CLS))
        return m, "features"
    raise ValueError(name)


def set_grad(model, backbone_attr, enabled, name):
    if name == "resnet50":
        for p in model.parameters():
            p.requires_grad = enabled
        if not enabled:
            for p in model.fc.parameters():
                p.requires_grad = True
    else:
        for p in getattr(model, backbone_attr).parameters():
            p.requires_grad = enabled


def split(entries, ratio, seed):
    rng = random.Random(seed)
    by = defaultdict(list)
    for e in entries:
        by[e["kelas"]].append(e)
    tr, va = [], []
    for _, ents in by.items():
        rng.shuffle(ents)
        n = max(1, int(len(ents) * ratio))
        va.extend(ents[:n])
        tr.extend(ents[n:])
    return tr, va


def evaluate(model, loader, crit):
    model.eval()
    cor = tot = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            cor += (model(x).argmax(1) == y).sum().item()
            tot += x.size(0)
    return cor / max(tot, 1)


def train_one(name, train_e, val_e):
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    ci = {c: i for i, c in enumerate(CLS)}
    tl = DataLoader(AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in train_e], True), batch_size=BATCH, shuffle=True, num_workers=0, pin_memory=True, drop_last=True)
    vl = DataLoader(AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in val_e], False), batch_size=BATCH, shuffle=False, num_workers=0, pin_memory=True)
    cnt = np.array([sum(1 for e in train_e if e["kelas"] == c) for c in CLS], float)
    w = cnt.sum() / (len(CLS) * np.maximum(cnt, 1))
    crit = nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32).to(DEVICE), label_smoothing=LS)

    model, bb = make_model(name)
    model = model.to(DEVICE)
    set_grad(model, bb, False, name)
    head = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(head, lr=LR_HEAD, weight_decay=WD)
    best, bep, noimp = 0.0, 0, 0
    t0 = time.time()
    for ep in range(1, EPOCHS + 1):
        if ep == WARMUP + 1:
            set_grad(model, bb, True, name)
            opt = torch.optim.AdamW(model.parameters(), lr=LR_FULL, weight_decay=WD)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS - WARMUP)
        model.train()
        for x, y in tl:
            x, y = x.to(DEVICE, non_blocking=True), y.to(DEVICE, non_blocking=True)
            opt.zero_grad()
            loss = crit(model(x), y)
            loss.backward()
            opt.step()
        if ep > WARMUP:
            sched.step()
        va = evaluate(model, vl, crit)
        if va > best:
            best, bep, noimp = va, ep, 0
        else:
            noimp += 1
            if ep > WARMUP and noimp >= PATIENCE:
                break
    print(f"  {name:20s} val={best:.4f} @ep{bep} ({time.time()-t0:.0f}s)")
    return best


def main():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    tr, va = split(entries, VAL_RATIO, SEED)
    print(f"device={DEVICE} train={len(tr)} val={len(va)}")
    results = {}
    for name in ["mobilenet_v2", "mobilenet_v3_large", "efficientnet_b0", "resnet50", "convnext_tiny"]:
        try:
            results[name] = round(train_one(name, tr, va), 4)
        except Exception as e:
            print(f"  {name:20s} GAGAL: {str(e)[:100]}")
    print("\n=== Hasil backbone ===")
    for k, v in sorted(results.items(), key=lambda kv: -kv[1]):
        print(f"  {k:20s} {v:.4f}")
    (WEIGHTS / "_bench_backbones.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
