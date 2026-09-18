# -*- coding: utf-8 -*-
"""Training hair_length v4 — anti-overfit + stratified split + mixup/cutmix.

Perbaikan menyeluruh:
  1. STRATIFIED split per (kelas) -> val stabil & seimbang antar kelas.
  2. Augmentasi kuat: RandomResizedCrop, flip, color jitter, rotation, erasing.
  3. Mixup / CutMix -> kurangi overfit, haluskan batas antar kelas.
  4. Progressive unfreeze + cosine LR + label smoothing.
  5. Class weight (imbalance) + early stop + simpan terbaik.

Sumber label bersih: hairstyle40 (label eksplisit) + balgald + figaro-extra.
Figaro utama (label geometris noise) DIBUANG default (--include-figaro untuk memakai).

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\scripts\\train_length_v4.py
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
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from torchvision import models

BASE = Path(__file__).resolve().parents[1]
WEIGHTS = BASE / "weights"
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

EPOCHS = 40
BATCH = 32
LR_HEAD = 2e-3
LR_FULL = 3e-4
WEIGHT_DECAY = 3e-4
DROPOUT = 0.4
LABEL_SMOOTH = 0.1
WARMUP_EPOCHS = 2
PATIENCE = 10
VAL_RATIO = 0.2
MIXUP_ALPHA = 0.2
CUTMIX_ALPHA = 1.0
MIX_PROB = 0.3
SEED = 42
OPSET = 14


class AugDataset(Dataset):
    def __init__(self, base: Path, items: list[tuple[str, int]], train: bool):
        self.base = base
        self.items = items
        self.train = train

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        pt, label = self.items[idx]
        t = torch.load(self.base / pt, weights_only=True, map_location="cpu").squeeze(0)
        if not self.train:
            return t, label
        # random resized crop (scale 0.7-1.0) via pad+crop
        t = self._rrc(t, 0.75)
        if random.random() < 0.5:
            t = torch.flip(t, dims=[2])
        # rotation ringan
        if random.random() < 0.3:
            ang = random.uniform(-12, 12)
            t = self._rotate(t, ang)
        # brightness/contrast
        if random.random() < 0.7:
            t = t * random.uniform(0.85, 1.15) + random.uniform(-0.15, 0.15)
        # erasing
        if random.random() < 0.3:
            eh, ew = random.randint(16, 48), random.randint(16, 48)
            y0, x0 = random.randint(0, 224 - eh), random.randint(0, 224 - ew)
            t = t.clone()
            t[:, y0 : y0 + eh, x0 : x0 + ew] = 0.0
        return t, label

    @staticmethod
    def _rrc(t: torch.Tensor, min_scale: float) -> torch.Tensor:
        s = random.uniform(min_scale, 1.0)
        c = int(224 * s)
        pad = torch.nn.functional.pad(t, (8, 8, 8, 8), mode="reflect")
        i = random.randint(0, pad.shape[1] - c)
        j = random.randint(0, pad.shape[2] - c)
        crop = pad[:, i : i + c, j : j + c]
        return F.interpolate(crop.unsqueeze(0), size=(224, 224), mode="bilinear", align_corners=False).squeeze(0)

    @staticmethod
    def _rotate(t: torch.Tensor, angle: float) -> torch.Tensor:
        rad = np.deg2rad(angle)
        theta = torch.tensor([[np.cos(rad), -np.sin(rad), 0.0], [np.sin(rad), np.cos(rad), 0.0]], dtype=torch.float32)
        grid = F.affine_grid(theta.unsqueeze(0), (1, 3, 224, 224), align_corners=False)
        return F.grid_sample(t.unsqueeze(0), grid, align_corners=False, padding_mode="reflection").squeeze(0)


def build_model() -> nn.Module:
    m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    m.classifier = nn.Sequential(nn.Dropout(p=DROPOUT), nn.Linear(m.last_channel, len(LENGTH_CLASSES)))
    return m


def set_backbone_grad(model, enabled):
    for p in model.features.parameters():
        p.requires_grad = enabled


def stratified_split(entries, val_ratio, seed):
    """Bagi per kelas (dan per sumber) agar val seimbang."""
    rng = random.Random(seed)
    by_cls = defaultdict(list)
    for e in entries:
        by_cls[e["kelas"]].append(e)
    train, val = [], []
    for cls, ents in by_cls.items():
        rng.shuffle(ents)
        n_val = max(1, int(len(ents) * val_ratio))
        val.extend(ents[:n_val])
        train.extend(ents[n_val:])
    return train, val


def mixup_cutmix(x, y, n_cls):
    r = random.random()
    if r < MIX_PROB:
        lam = np.random.beta(MIXUP_ALPHA, MIXUP_ALPHA)
        idx = torch.randperm(x.size(0), device=x.device)
        x = lam * x + (1 - lam) * x[idx]
        return x, y, y[idx], lam
    if r < MIX_PROB * 2:
        lam = np.random.beta(CUTMIX_ALPHA, CUTMIX_ALPHA)
        idx = torch.randperm(x.size(0), device=x.device)
        bbx1 = int(224 * np.sqrt(1 - lam))
        x[:, :, :bbx1, :] = x[idx, :, :bbx1, :]
        return x, y, y[idx], lam
    return x, y, None, 1.0


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-figaro", action="store_true", help="pakai figaro (label geometris noise)")
    ap.add_argument("--tag", default="v4")
    args = ap.parse_args()

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    all_entries = idx["index"]["train"] + idx["index"]["val"]
    if not args.include_figaro:
        all_entries = [e for e in all_entries if e["sumber"] != "figaro"]

    train_e, val_e = stratified_split(all_entries, VAL_RATIO, SEED)
    print(f"device={DEVICE} | train={len(train_e)} val={len(val_e)} | include_figaro={args.include_figaro}")
    print(f"  train dist: { {c: sum(1 for e in train_e if e['kelas']==c) for c in LENGTH_CLASSES} }")
    print(f"  val dist  : { {c: sum(1 for e in val_e if e['kelas']==c) for c in LENGTH_CLASSES} }")

    ci = {c: i for i, c in enumerate(LENGTH_CLASSES)}
    train_ds = AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in train_e], train=True)
    val_ds = AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in val_e], train=False)

    pin = DEVICE.type == "cuda"
    train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True, num_workers=0, pin_memory=pin, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=0, pin_memory=pin)

    # class weight
    counts = np.array([sum(1 for e in train_e if e["kelas"] == c) for c in LENGTH_CLASSES], dtype=float)
    w = counts.sum() / (len(LENGTH_CLASSES) * np.maximum(counts, 1))
    cw = torch.tensor(w, dtype=torch.float32).to(DEVICE)
    crit = nn.CrossEntropyLoss(weight=cw, label_smoothing=LABEL_SMOOTH)

    model = build_model().to(DEVICE)
    set_backbone_grad(model, False)
    opt = torch.optim.AdamW([p for p in model.classifier.parameters() if p.requires_grad], lr=LR_HEAD, weight_decay=WEIGHT_DECAY)

    pth = WEIGHTS / f"hair_length_{args.tag}_mobilenetv2.pth"
    onnx_path = WEIGHTS / f"hair_length_{args.tag}.onnx"

    best_acc, best_cm, best_ep = 0.0, None, 0
    no_improve = 0
    t0 = time.time()
    for epoch in range(1, EPOCHS + 1):
        if epoch == WARMUP_EPOCHS + 1:
            set_backbone_grad(model, True)
            opt = torch.optim.AdamW(model.parameters(), lr=LR_FULL, weight_decay=WEIGHT_DECAY)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS - WARMUP_EPOCHS)
            print("  [unfreeze backbone + cosine]")

        model.train()
        run_corr = run_tot = 0
        for x, y in train_loader:
            x, y = x.to(DEVICE, non_blocking=pin), y.to(DEVICE, non_blocking=pin)
            x, ya, yb, lam = mixup_cutmix(x, y, len(LENGTH_CLASSES))
            opt.zero_grad()
            out = model(x)
            if yb is None:
                loss = crit(out, ya)
            else:
                loss = lam * crit(out, ya) + (1 - lam) * crit(out, yb)
            loss.backward()
            opt.step()
            run_corr += (out.argmax(1) == y).sum().item()
            run_tot += x.size(0)
        if epoch > WARMUP_EPOCHS:
            sched.step()
        tr_acc = run_corr / max(run_tot, 1)
        _, va_acc, cm = evaluate(model, val_loader, crit)
        lr_now = opt.param_groups[0]["lr"]
        print(f"epoch {epoch:2d}/{EPOCHS} train_acc={tr_acc:.4f} val_acc={va_acc:.4f} gap={tr_acc-va_acc:+.3f} lr={lr_now:.1e} ({time.time()-t0:.0f}s)")

        if va_acc > best_acc:
            best_acc, best_cm, best_ep, no_improve = va_acc, cm, epoch, 0
            torch.save(model.state_dict(), pth)
        else:
            no_improve += 1
            if epoch > WARMUP_EPOCHS and no_improve >= PATIENCE:
                print(f"  early stop (patience {PATIENCE})")
                break

    print(f"\nbest val_acc={best_acc:.4f} @ epoch {best_ep}")

    model.load_state_dict(torch.load(pth, weights_only=True, map_location="cpu"))
    model.to("cpu").eval()
    for f in (onnx_path, onnx_path.with_suffix(".onnx.data")):
        f.unlink(missing_ok=True)
    torch.onnx.export(model, torch.randn(1, 3, 224, 224), str(onnx_path), input_names=["input"], output_names=["logits"], opset_version=OPSET, dynamo=False, external_data=False)

    (WEIGHTS / f"_train_report_length_{args.tag}.json").write_text(
        json.dumps(
            {
                "task": "hair_length",
                "version": args.tag,
                "include_figaro": args.include_figaro,
                "classes": LENGTH_CLASSES,
                "train": len(train_ds),
                "val": len(val_ds),
                "val_distribution": {c: sum(1 for e in val_e if e["kelas"] == c) for c in LENGTH_CLASSES},
                "hyperparams": {"epochs": EPOCHS, "batch": BATCH, "lr_head": LR_HEAD, "lr_full": LR_FULL, "warmup": WARMUP_EPOCHS, "patience": PATIENCE, "dropout": DROPOUT, "label_smooth": LABEL_SMOOTH, "mixup": MIXUP_ALPHA, "cutmix": CUTMIX_ALPHA, "val_ratio": VAL_RATIO},
                "best_val_acc": round(best_acc, 4),
                "best_epoch": best_ep,
                "confusion_matrix": best_cm,
                "onnx": str(onnx_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"ONNX -> {onnx_path}")


if __name__ == "__main__":
    main()
