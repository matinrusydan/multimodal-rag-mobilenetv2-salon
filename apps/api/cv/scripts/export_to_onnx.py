# -*- coding: utf-8 -*-
"""Training MobileNetV2 (hair_type, 4 kelas) -> export ONNX + label mapping.

Dataset: apps/api/cv/preprocessed/  (train/*.pt x3 augmentasi, val/*.pt)
  - tensor NCHW (1,3,224,224), sudah dinormalisasi ImageNet + augmentasi train.
Output:
  apps/api/cv/weights/hair_type.onnx  (opset 17, input 'input' 1x3x224x224)
  apps/api/cv/weights/hair_type_labels.json
  apps/api/cv/weights/_train_report.json

Catatan: hair_length (panjang rambut) belum punya dataset labeled -> hanya
hair_type yang di-train sekarang (task 07-cv.md, item pending).
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models

BASE = Path(__file__).resolve().parents[1]
PRE = BASE / "preprocessed"
WEIGHTS = BASE / "weights"

CLASSES = ["lurus", "bergelombang", "keriting", "sangat-keriting"]
LABEL_JSON = WEIGHTS / "hair_type_labels.json"
ONNX_PATH = WEIGHTS / "hair_type.onnx"
REPORT = WEIGHTS / "_train_report.json"

# Hyper-param (CPU-friendly, prototip skripsi per AGENTS.md)
EPOCHS = 12
BATCH = 32
LR = 1e-3
WEIGHT_DECAY = 1e-4
SEED = 42
OPSET = 17
# Simpan state (.pth) juga untuk re-export / evaluasi lanjutan
PTH_PATH = WEIGHTS / "hair_type_mobilenetv2.pth"


class TensorFolder(Dataset):
    """Dataset dari folder .pt tensor NCHW (1,3,224,224), flattens ke (3,224,224)."""

    def __init__(self, root: Path):
        self.root = root
        self.items: list[tuple[Path, int]] = []
        for i, cls in enumerate(CLASSES):
            d = root / cls
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.pt")):
                self.items.append((p, i))

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        path, label = self.items[idx]
        t = torch.load(path, weights_only=True, map_location="cpu")
        t = t.squeeze(0)  # (3,224,224)
        return t, label


def build_model() -> nn.Module:
    m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    m.classifier[1] = nn.Linear(m.last_channel, len(CLASSES))
    return m


def evaluate(model: nn.Module, loader: DataLoader) -> tuple[float, float]:
    model.eval()
    correct = 0
    total = 0
    loss_sum = 0.0
    crit = nn.CrossEntropyLoss()
    with torch.no_grad():
        for x, y in loader:
            out = model(x)
            loss = crit(out, y)
            loss_sum += loss.item() * x.size(0)
            correct += (out.argmax(1) == y).sum().item()
            total += x.size(0)
    return loss_sum / total, correct / total


def main() -> None:
    random.seed(SEED)
    torch.manual_seed(SEED)

    if not (PRE / "train").is_dir():
        print(f"ERROR: preprocessed not found: {PRE}", file=sys.stderr)
        sys.exit(1)

    WEIGHTS.mkdir(parents=True, exist_ok=True)

    train_ds = TensorFolder(PRE / "train")
    val_ds = TensorFolder(PRE / "val")
    n_train, n_val = len(train_ds), len(val_ds)
    print(f"train={n_train} val={n_val}")
    train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True,
                              num_workers=0, pin_memory=False)
    val_loader = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=0)

    model = build_model()
    criterion = nn.CrossEntropyLoss()

    if PTH_PATH.exists():
        model.load_state_dict(torch.load(PTH_PATH, weights_only=True, map_location="cpu"))
        print(f"LOAD .pth existing (skip training): {PTH_PATH}")
        history = []
        best_val = float("nan")
        t0 = time.time()
    else:
        optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
        history: list[dict] = []
        best_val = 0.0
        t0 = time.time()
        for epoch in range(1, EPOCHS + 1):
            model.train()
            run_loss = 0.0
            run_corr = 0
            run_tot = 0
            for x, y in train_loader:
                optimizer.zero_grad()
                out = model(x)
                loss = criterion(out, y)
                loss.backward()
                optimizer.step()
                run_loss += loss.item() * x.size(0)
                run_corr += (out.argmax(1) == y).sum().item()
                run_tot += x.size(0)
            tr_loss = run_loss / run_tot
            tr_acc = run_corr / run_tot
            va_loss, va_acc = evaluate(model, val_loader)
            history.append({
                "epoch": epoch,
                "train_loss": round(tr_loss, 4),
                "train_acc": round(tr_acc, 4),
                "val_loss": round(va_loss, 4),
                "val_acc": round(va_acc, 4),
            })
            print(
                f"epoch {epoch:2d}/{EPOCHS}  train_loss={tr_loss:.4f} train_acc={tr_acc:.4f} "
                f"val_loss={va_loss:.4f} val_acc={va_acc:.4f}  ({time.time()-t0:.0f}s)"
            )
            if va_acc >= best_val:
                best_val = va_acc
                torch.save(model.state_dict(), PTH_PATH)

    model.load_state_dict(torch.load(PTH_PATH, weights_only=True, map_location="cpu"))
    model.eval()

    # Freeze backbone for export (classifier only adjust is enough)
    model = _make_inference(model)

    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        model,
        dummy,
        str(ONNX_PATH),
        input_names=["input"],
        output_names=["logits"],
        opset_version=OPSET,
        dynamic_axes=None,
    )

    labels = {"classes": CLASSES, "model": "mobilenet_v2", "task": "hair_type"}
    LABEL_JSON.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "task": "hair_type",
        "backbone": "mobilenet_v2 (pretrained ImageNet)",
        "classes": CLASSES,
        "train_tensor": n_train,
        "val_tensor": n_val,
        "epochs": EPOCHS,
        "batch": BATCH,
        "lr": LR,
        "weight_decay": WEIGHT_DECAY,
        "history": history,
        "best_val_acc": round(best_val, 4),
        "onnx": str(ONNX_PATH),
        "opset": OPSET,
        "input": "input 1x3x224x224 float32 NCHW (RGB, ImageNet-normalized)",
        "output": "logits 1x4 (INDEX sesuai classes)",
        "duration_s": round(time.time() - t0, 1),
        "catatan": "hair_length ONNX belum tersedia (dataset labeled panjang rambut belum ada)",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSELESAI. ONNX -> {ONNX_PATH} (opset {OPSET}) | best_val_acc={best_val:.4f}")
    print(f"Label: {LABEL_JSON}")


def _make_inference(model: nn.Module) -> nn.Module:
    return model


if __name__ == "__main__":
    main()