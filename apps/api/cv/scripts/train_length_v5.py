# -*- coding: utf-8 -*-
"""Training hair_length v5 — augmentasi MODERAT + fine-tune bertahap.

Berdasarkan eksperimen:
  - v4 (augmentasi berat + mixup/cutmix) -> 78.9% (UNDERFIT: augmentasi terlalu kuat).
  - clean (augmentasi ringan) -> 84.0% (terbaik, tapi overfit gap +16%).

v5 = keseimbangan:
  - Augmentasi MODERAT: hflip, brightness kecil, erasing ringan (tanpa mixup/cutmix).
  - Fine-tune bertahap: warmup head (3 ep) -> unfreeze backbone dgn LR rendah lebih lama.
  - Cosine + early stop + EMA bobot (kurangi varians val).
  - Stratified split + class weight.

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\scripts\\train_length_v5.py
"""

from __future__ import annotations

import argparse
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

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

EPOCHS = 35
BATCH = 32
LR_HEAD = 1.5e-3
LR_FULL = 2e-4
WEIGHT_DECAY = 2e-4
DROPOUT = 0.35
LABEL_SMOOTH = 0.08
WARMUP_EPOCHS = 3
PATIENCE = 12
VAL_RATIO = 0.2
EMA_DECAY = 0.999
SEED = 42
OPSET = 14


class AugDataset(Dataset):
    """Tensor sudah ternormalisasi ImageNet; augmentasi moderat."""

    def __init__(self, base: Path, items, train: bool):
        self.base = base
        self.items = items
        self.train = train

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        pt, label = self.items[idx]
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


def build_model() -> nn.Module:
    m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    m.classifier = nn.Sequential(nn.Dropout(p=DROPOUT), nn.Linear(m.last_channel, len(LENGTH_CLASSES)))
    return m


def set_backbone_grad(model, enabled):
    for p in model.features.parameters():
        p.requires_grad = enabled


def stratified_split(entries, val_ratio, seed):
    rng = random.Random(seed)
    by = defaultdict(list)
    for e in entries:
        by[e["kelas"]].append(e)
    tr, va = [], []
    for _, ents in by.items():
        rng.shuffle(ents)
        n = max(1, int(len(ents) * val_ratio))
        va.extend(ents[:n])
        tr.extend(ents[n:])
    return tr, va


class EMA:
    def __init__(self, model, decay):
        self.decay = decay
        self.shadow = {k: v.detach().clone() for k, v in model.state_dict().items()}

    def update(self, model):
        for k, v in model.state_dict().items():
            if v.dtype.is_floating_point:
                self.shadow[k] = self.decay * self.shadow[k] + (1 - self.decay) * v.detach()
            else:
                self.shadow[k] = v.detach().clone()

    def apply(self, model):
        model.load_state_dict(self.shadow, strict=False)


def evaluate(model, loader, crit):
    model.eval()
    n = len(LENGTH_CLASSES)
    cm = [[0] * n for _ in range(n)]
    correct = total = 0
    loss_sum = 0.0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            out = model(x)
            loss_sum += crit(out, y).item() * x.size(0)
            pred = out.argmax(1)
            for t, p in zip(y.tolist(), pred.tolist(), strict=False):
                cm[t][p] += 1
            correct += (pred == y).sum().item()
            total += x.size(0)
    return loss_sum / max(total, 1), correct / max(total, 1), cm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v5")
    args = ap.parse_args()

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    train_e, val_e = stratified_split(entries, VAL_RATIO, SEED)
    print(f"device={DEVICE} train={len(train_e)} val={len(val_e)}")
    print(f"  val dist: { {c: sum(1 for e in val_e if e['kelas']==c) for c in LENGTH_CLASSES} }")

    ci = {c: i for i, c in enumerate(LENGTH_CLASSES)}
    train_ds = AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in train_e], True)
    val_ds = AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in val_e], False)
    pin = DEVICE.type == "cuda"
    tl = DataLoader(train_ds, batch_size=BATCH, shuffle=True, num_workers=0, pin_memory=pin, drop_last=True)
    vl = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=0, pin_memory=pin)

    counts = np.array([sum(1 for e in train_e if e["kelas"] == c) for c in LENGTH_CLASSES], float)
    w = counts.sum() / (len(LENGTH_CLASSES) * np.maximum(counts, 1))
    cw = torch.tensor(w, dtype=torch.float32).to(DEVICE)
    crit = nn.CrossEntropyLoss(weight=cw, label_smoothing=LABEL_SMOOTH)

    model = build_model().to(DEVICE)
    set_backbone_grad(model, False)
    opt = torch.optim.AdamW([p for p in model.classifier.parameters() if p.requires_grad], lr=LR_HEAD, weight_decay=WEIGHT_DECAY)
    ema = EMA(model, EMA_DECAY)

    pth = WEIGHTS / f"hair_length_{args.tag}_mobilenetv2.pth"
    onnx_path = WEIGHTS / f"hair_length_{args.tag}.onnx"

    best_acc, best_cm, best_ep, no_imp = 0.0, None, 0, 0
    t0 = time.time()
    for epoch in range(1, EPOCHS + 1):
        if epoch == WARMUP_EPOCHS + 1:
            set_backbone_grad(model, True)
            opt = torch.optim.AdamW(model.parameters(), lr=LR_FULL, weight_decay=WEIGHT_DECAY)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS - WARMUP_EPOCHS)
            print("  [unfreeze + cosine]")

        model.train()
        rc = rt = 0
        for x, y in tl:
            x, y = x.to(DEVICE, non_blocking=pin), y.to(DEVICE, non_blocking=pin)
            opt.zero_grad()
            out = model(x)
            loss = crit(out, y)
            loss.backward()
            opt.step()
            ema.update(model)
            rc += (out.argmax(1) == y).sum().item()
            rt += x.size(0)
        if epoch > WARMUP_EPOCHS:
            sched.step()
        tr_acc = rc / max(rt, 1)

        # evaluasi pada model EMA (stabil)
        backup = {k: v.detach().clone() for k, v in model.state_dict().items()}
        ema.apply(model)
        _, va_acc, cm = evaluate(model, vl, crit)
        model.load_state_dict(backup)

        lr_now = opt.param_groups[0]["lr"]
        print(f"epoch {epoch:2d}/{EPOCHS} train={tr_acc:.4f} val(ema)={va_acc:.4f} gap={tr_acc-va_acc:+.3f} lr={lr_now:.1e} ({time.time()-t0:.0f}s)")

        if va_acc > best_acc:
            best_acc, best_cm, best_ep, no_imp = va_acc, cm, epoch, 0
            best_state = {k: v.detach().clone() for k, v in ema.shadow.items()}
            torch.save(best_state, pth)
        else:
            no_imp += 1
            if epoch > WARMUP_EPOCHS and no_imp >= PATIENCE:
                print(f"  early stop (patience {PATIENCE})")
                break

    print(f"\nbest val_acc={best_acc:.4f} @ epoch {best_ep}")
    model.load_state_dict(torch.load(pth, weights_only=True, map_location="cpu"), strict=False)
    model.to("cpu").eval()
    for f in (onnx_path, onnx_path.with_suffix(".onnx.data")):
        f.unlink(missing_ok=True)
    torch.onnx.export(model, torch.randn(1, 3, 224, 224), str(onnx_path), input_names=["input"], output_names=["logits"], opset_version=OPSET, dynamo=False, external_data=False)

    (WEIGHTS / f"_train_report_length_{args.tag}.json").write_text(json.dumps({
        "task": "hair_length", "version": args.tag, "classes": LENGTH_CLASSES,
        "train": len(train_ds), "val": len(val_ds),
        "val_distribution": {c: sum(1 for e in val_e if e["kelas"] == c) for c in LENGTH_CLASSES},
        "hyperparams": {"epochs": EPOCHS, "batch": BATCH, "lr_head": LR_HEAD, "lr_full": LR_FULL, "warmup": WARMUP_EPOCHS, "patience": PATIENCE, "dropout": DROPOUT, "label_smooth": LABEL_SMOOTH, "ema_decay": EMA_DECAY, "val_ratio": VAL_RATIO},
        "best_val_acc": round(best_acc, 4), "best_epoch": best_ep,
        "confusion_matrix": best_cm, "onnx": str(onnx_path),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ONNX -> {onnx_path}")


if __name__ == "__main__":
    main()
