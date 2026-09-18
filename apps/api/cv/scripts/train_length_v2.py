# -*- coding: utf-8 -*-
"""Training hair_length v2 — anti-overfit (augmentasi online + freeze + early stop).

Perbaikan dari v1:
  - Augmentasi ONLINE (random resized crop, hflip, color jitter) -> variasi nyata,
    mengurangi overfit (v1: train 100% vs val 75%).
  - Freeze backbone pada fase warmup (latih classifier dulu), lalu unfreeze.
  - Early stopping + simpan bobot terbaik.
  - Class weight (atasi imbalance: menengah hanya 150 sampel).

Jalankan (venv ComfyUI/GPU):
  $env:PYTHONIOENCODING='utf-8'
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\scripts\\train_length_v2.py
"""

from __future__ import annotations

import argparse
import json
import random
import time
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

EPOCHS = 25
BATCH = 32
LR_HEAD = 2e-3   # fase warmup (classifier saja)
LR_FULL = 3e-4   # fase fine-tune (seluruh network)
WEIGHT_DECAY = 1e-4
DROPOUT = 0.3
LABEL_SMOOTH = 0.05
WARMUP_EPOCHS = 2
PATIENCE = 6
SEED = 42
OPSET = 14

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class AugDataset(Dataset):
    """Membaca tensor NCHW ternormalisasi, lalu augmentasi di ruang ternormalisasi.

    Karena tensor sudah ternormalisasi ImageNet, augmentasi dilakukan dengan
    mengembalikan ke [0,1] dulu (denorm) untuk color jitter, lalu norm ulang.
    Crop/flip tidak butuh denorm.
    """

    def __init__(self, base: Path, entries: list[dict], train: bool, classes: list[str]):
        self.base = base
        self.cls_to_idx = {c: i for i, c in enumerate(classes)}
        self.items = [(base / e["pt"], self.cls_to_idx[e["kelas"]]) for e in entries if e["kelas"] in self.cls_to_idx]
        self.train = train

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        path, label = self.items[idx]
        t = torch.load(path, weights_only=True, map_location="cpu").squeeze(0)  # (3,224,224) ternormalisasi

        if self.train:
            # random crop ringan (pad 16 -> crop 224)
            pad = torch.nn.functional.pad(t, (16, 16, 16, 16), mode="reflect")
            i = random.randint(0, 32)
            j = random.randint(0, 32)
            t = pad[:, j : j + 224, i : i + 224]
            if random.random() < 0.5:
                t = torch.flip(t, dims=[2])  # hflip
            # brightness/contrast kecil di ruang ternormalisasi
            if random.random() < 0.5:
                t = t + random.uniform(-0.1, 0.1)
            # erasing (cutout) kecil
            if random.random() < 0.3:
                eh, ew = random.randint(20, 50), random.randint(20, 50)
                y0 = random.randint(0, 224 - eh)
                x0 = random.randint(0, 224 - ew)
                t = t.clone()
                t[:, y0 : y0 + eh, x0 : x0 + ew] = 0.0
        return t, label


def build_model() -> nn.Module:
    m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    m.classifier = nn.Sequential(nn.Dropout(p=DROPOUT), nn.Linear(m.last_channel, len(LENGTH_CLASSES)))
    return m


def set_backbone_grad(model: nn.Module, enabled: bool) -> None:
    for p in model.features.parameters():
        p.requires_grad = enabled


def class_weights(entries: list[dict]) -> torch.Tensor:
    counts = {c: 0 for c in LENGTH_CLASSES}
    for e in entries:
        if e["kelas"] in counts:
            counts[e["kelas"]] += 1
    total = sum(counts.values()) or 1
    w = [total / (len(LENGTH_CLASSES) * max(counts[c], 1)) for c in LENGTH_CLASSES]
    return torch.tensor(w, dtype=torch.float32)


def evaluate(model, loader, crit) -> tuple[float, float, list[list[int]]]:
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
    ap.add_argument("--exclude-sources", default="", help="sumber yang DIBUANG, mis. 'figaro' (label noisy)")
    ap.add_argument("--figaro-classes", default="", help="bila diisi, ambil figaro HANYA untuk kelas ini (mis. 'panjang,menengah')")
    ap.add_argument("--tag", default="v2", help="suffix nama model")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    exclude = {s.strip() for s in args.exclude_sources.split(",") if s.strip()}
    figaro_only = {s.strip() for s in args.figaro_classes.split(",") if s.strip()}

    def keep(e: dict) -> bool:
        if e["sumber"] in exclude:
            return False
        # figaro: hanya pertahankan bila kelasnya diizinkan (label geometris andal utk kelas ini)
        if e["sumber"] == "figaro" and figaro_only and e["kelas"] not in figaro_only:
            return False
        return True

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    train_entries = [e for e in idx["index"]["train"] if keep(e)]
    val_entries = [e for e in idx["index"]["val"] if keep(e)]
    print(f"exclude={exclude or '-'} figaro_only={figaro_only or '-'}")

    train_ds = AugDataset(BASE, train_entries, train=True, classes=LENGTH_CLASSES)
    val_ds = AugDataset(BASE, val_entries, train=False, classes=LENGTH_CLASSES)
    print(f"device={DEVICE} train={len(train_ds)} val={len(val_ds)}")

    pin = DEVICE.type == "cuda"
    train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True, num_workers=0, pin_memory=pin, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=0, pin_memory=pin)

    model = build_model().to(DEVICE)
    cw = class_weights(train_entries).to(DEVICE)
    crit = nn.CrossEntropyLoss(weight=cw, label_smoothing=LABEL_SMOOTH)

    set_backbone_grad(model, False)  # warmup: latih head dulu
    params_head = [p for p in model.classifier.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params_head, lr=LR_HEAD, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="max", factor=0.5, patience=2)

    pth = WEIGHTS / f"hair_length_{args.tag}_mobilenetv2.pth"
    onnx_path = WEIGHTS / f"hair_length_{args.tag}.onnx"

    best_acc, best_cm, best_epoch = 0.0, None, 0
    no_improve = 0
    t0 = time.time()
    for epoch in range(1, EPOCHS + 1):
        if epoch == WARMUP_EPOCHS + 1:
            set_backbone_grad(model, True)
            opt = torch.optim.AdamW(model.parameters(), lr=LR_FULL, weight_decay=WEIGHT_DECAY)
            sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="max", factor=0.5, patience=2)
            print("  [unfreeze backbone]")

        model.train()
        run_corr = run_tot = 0
        for x, y in train_loader:
            x, y = x.to(DEVICE, non_blocking=pin), y.to(DEVICE, non_blocking=pin)
            opt.zero_grad()
            out = model(x)
            loss = crit(out, y)
            loss.backward()
            opt.step()
            run_corr += (out.argmax(1) == y).sum().item()
            run_tot += x.size(0)
        tr_acc = run_corr / max(run_tot, 1)
        _, va_acc, cm = evaluate(model, val_loader, crit)
        sched.step(va_acc)
        lr_now = opt.param_groups[0]["lr"]
        print(f"epoch {epoch:2d}/{EPOCHS} train_acc={tr_acc:.4f} val_acc={va_acc:.4f} lr={lr_now:.1e} ({time.time()-t0:.0f}s)")

        if va_acc > best_acc:
            best_acc, best_cm, best_epoch = va_acc, cm, epoch
            no_improve = 0
            torch.save(model.state_dict(), pth)
        else:
            no_improve += 1
            if epoch > WARMUP_EPOCHS and no_improve >= PATIENCE:
                print(f"  early stop (tanpa perbaikan {PATIENCE} epoch)")
                break

    print(f"\nbest val_acc={best_acc:.4f} @ epoch {best_epoch}")

    model.load_state_dict(torch.load(pth, weights_only=True, map_location="cpu"))
    model.to("cpu").eval()
    for f in (onnx_path, onnx_path.with_suffix(".onnx.data")):
        f.unlink(missing_ok=True)
    torch.onnx.export(model, torch.randn(1, 3, 224, 224), str(onnx_path), input_names=["input"], output_names=["logits"], opset_version=OPSET, dynamo=False, external_data=False)

    (WEIGHTS / f"_train_report_length_{args.tag}.json").write_text(
        json.dumps(
            {
                "task": "hair_length",
                "version": "v2-anti-overfit",
                "dataset": "merged (figaro + hairstyle40)",
                "classes": LENGTH_CLASSES,
                "train": len(train_ds),
                "val": len(val_ds),
                "hyperparams": {"epochs": EPOCHS, "batch": BATCH, "lr_head": LR_HEAD, "lr_full": LR_FULL, "warmup": WARMUP_EPOCHS, "patience": PATIENCE, "dropout": DROPOUT, "label_smooth": LABEL_SMOOTH},
                "best_val_acc": round(best_acc, 4),
                "best_epoch": best_epoch,
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
