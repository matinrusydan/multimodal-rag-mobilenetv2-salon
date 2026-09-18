# -*- coding: utf-8 -*-
"""Training hair_length CHAMPION — ConvNeXt-Tiny, dataset diperkaya, anti over/underfit.

Hasil bench: convnext_tiny (80.97%) > resnet50 (80.4%) > effnet_b0 (80.2%)
             > mobilenet_v3 (77.5%) > mobilenet_v2 (77.2%).
ConvNeXt-Tiny dipilih sebagai model champion (akurasi tertinggi).

Resep final:
  - label bersih (tanpa figaro-noise)
  - augmentasi sedang + mixup ringan (alpha 0.2, prob 0.2)
  - stratified val 25%, warmup head, cosine, label smoothing, class weight
  - epoch lebih banyak + patience, simpan terbaik

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\scripts\\train_length_champion.py
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

EPOCHS = 40
BATCH = 24
LR_HEAD = 1.5e-3
LR_FULL = 2e-4
WD = 5e-2
DROPOUT = 0.3
LS = 0.08
WARMUP = 3
PATIENCE = 12
VAL_RATIO = 0.25
MIXUP_A = 0.2
MIXUP_P = 0.25
SEED = 42
OPSET = 14


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


def build_model():
    m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
    m.classifier[2] = nn.Sequential(nn.Dropout(DROPOUT), nn.Linear(m.classifier[2].in_features, len(CLS)))
    return m


def set_grad(model, en):
    for p in model.features.parameters():
        p.requires_grad = en


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
    n = len(CLS)
    cm = [[0] * n for _ in range(n)]
    cor = tot = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            pred = model(x).argmax(1)
            for t, p in zip(y.tolist(), pred.tolist(), strict=False):
                cm[t][p] += 1
            cor += (pred == y).sum().item()
            tot += x.size(0)
    return cor / max(tot, 1), cm


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--tag", default="champion")
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    tr, va = split(entries, VAL_RATIO, args.seed)
    print(f"device={DEVICE} train={len(tr)} val={len(va)}")
    print(f"  val dist: { {c: sum(1 for e in va if e['kelas']==c) for c in CLS} }")

    ci = {c: i for i, c in enumerate(CLS)}
    tl = DataLoader(AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in tr], True), batch_size=BATCH, shuffle=True, num_workers=0, pin_memory=True, drop_last=True)
    vl = DataLoader(AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in va], False), batch_size=BATCH, shuffle=False, num_workers=0, pin_memory=True)

    cnt = np.array([sum(1 for e in tr if e["kelas"] == c) for c in CLS], float)
    w = cnt.sum() / (len(CLS) * np.maximum(cnt, 1))
    crit = nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32).to(DEVICE), label_smoothing=LS)

    model = build_model().to(DEVICE)
    set_grad(model, False)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR_HEAD, weight_decay=WD)

    pth = WEIGHTS / f"hair_length_{args.tag}.pth"
    onnx_path = WEIGHTS / f"hair_length_{args.tag}.onnx"
    best, bcm, bep, noimp = 0.0, None, 0, 0
    t0 = time.time()
    for ep in range(1, EPOCHS + 1):
        if ep == WARMUP + 1:
            set_grad(model, True)
            opt = torch.optim.AdamW(model.parameters(), lr=LR_FULL, weight_decay=WD)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS - WARMUP)
            print("  [unfreeze + cosine]")
        model.train()
        rc = rt = 0
        for x, y in tl:
            x, y = x.to(DEVICE, non_blocking=True), y.to(DEVICE, non_blocking=True)
            if random.random() < MIXUP_P:
                lam = np.random.beta(MIXUP_A, MIXUP_A)
                perm = torch.randperm(x.size(0), device=x.device)
                x = lam * x + (1 - lam) * x[perm]
                opt.zero_grad()
                out = model(x)
                loss = lam * crit(out, y) + (1 - lam) * crit(out, y[perm])
            else:
                opt.zero_grad()
                out = model(x)
                loss = crit(out, y)
            loss.backward()
            opt.step()
            rc += (out.argmax(1) == y).sum().item()
            rt += x.size(0)
        if ep > WARMUP:
            sched.step()
        tr_acc = rc / max(rt, 1)
        va_acc, cm = evaluate(model, vl, crit)
        print(f"epoch {ep:2d}/{EPOCHS} train={tr_acc:.4f} val={va_acc:.4f} gap={tr_acc-va_acc:+.3f} ({time.time()-t0:.0f}s)")
        if va_acc > best:
            best, bcm, bep, noimp = va_acc, cm, ep, 0
            torch.save(model.state_dict(), pth)
        else:
            noimp += 1
            if ep > WARMUP and noimp >= PATIENCE:
                print(f"  early stop (patience {PATIENCE})")
                break

    print(f"\nbest val_acc={best:.4f} @ep{bep}")
    model.load_state_dict(torch.load(pth, weights_only=True, map_location="cpu"))
    model.to("cpu").eval()
    for f in (onnx_path, onnx_path.with_suffix(".onnx.data")):
        f.unlink(missing_ok=True)
    torch.onnx.export(model, torch.randn(1, 3, 224, 224), str(onnx_path), input_names=["input"], output_names=["logits"], opset_version=OPSET, dynamo=False, external_data=False)
    (WEIGHTS / f"_train_report_length_{args.tag}.json").write_text(json.dumps({
        "task": "hair_length", "arch": "convnext_tiny", "classes": CLS,
        "train": len(tr), "val": len(va),
        "val_distribution": {c: sum(1 for e in va if e["kelas"] == c) for c in CLS},
        "best_val_acc": round(best, 4), "best_epoch": bep,
        "confusion_matrix": bcm, "onnx": str(onnx_path),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ONNX -> {onnx_path}")


if __name__ == "__main__":
    main()
