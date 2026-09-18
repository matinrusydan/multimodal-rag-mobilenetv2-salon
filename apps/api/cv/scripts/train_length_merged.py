# -*- coding: utf-8 -*-
"""Training MobileNetV2 hair_length dengan dataset GABUNGAN (Fase 3.3 lanjutan).

Membaca apps/api/cv/preprocessed_length_merged/index_merged.json
(Figaro + Figaro-extra + bald + Hairstyle40).

Jalankan (Python GLOBAL: torch + torchvision):
  $env:PYTHONIOENCODING='utf-8'
  python apps\\api\\cv\\scripts\\train_length_merged.py

Output:
  apps/api/cv/weights/hair_length_merged.onnx
  apps/api/cv/weights/hair_length_labels.json   (GLOBAL, dipakai produksi)
  apps/api/cv/weights/_train_report_length_merged.json
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models

BASE = Path(__file__).resolve().parents[1]
WEIGHTS = BASE / "weights"
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]
EPOCHS = 20
BATCH = 32
LR = 5e-4
WEIGHT_DECAY = 5e-4
DROPOUT = 0.4
LABEL_SMOOTH = 0.1
SEED = 42
OPSET = 14


class MergedDataset(Dataset):
    def __init__(self, base: Path, entries: list[dict]):
        self.items = []
        self.cls_to_idx = {c: i for i, c in enumerate(LENGTH_CLASSES)}
        for e in entries:
            if e["kelas"] in self.cls_to_idx:
                self.items.append((base / e["pt"], self.cls_to_idx[e["kelas"]]))

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        path, label = self.items[idx]
        t = torch.load(path, weights_only=True, map_location="cpu").squeeze(0)
        return t, label


def build_model() -> nn.Module:
    m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    # Regularisasi: dropout sebelum classifier akhir (atasi overfit train 99% vs val 71%).
    m.classifier = nn.Sequential(
        nn.Dropout(p=DROPOUT),
        nn.Linear(m.last_channel, len(LENGTH_CLASSES)),
    )
    return m


def evaluate(model, loader) -> tuple[float, float, list[list[int]]]:
    model.eval()
    crit = nn.CrossEntropyLoss()
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
    if total == 0:
        return 0.0, 0.0, cm
    return loss_sum / total, correct / total, cm


def main() -> None:
    random.seed(SEED)
    torch.manual_seed(SEED)

    if not INDEX.exists():
        raise SystemExit(f"index tidak ada: {INDEX} (jalankan build_length_dataset.py)")

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    train_ds = MergedDataset(BASE, idx["index"]["train"])
    val_ds = MergedDataset(BASE, idx["index"]["val"])
    print(f"device={DEVICE} | train={len(train_ds)} val={len(val_ds)} | label_source={idx.get('label_source')}")

    pin = DEVICE.type == "cuda"
    train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True, num_workers=0, pin_memory=pin)
    val_loader = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=0, pin_memory=pin)

    model = build_model().to(DEVICE)
    crit = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTH)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)

    WEIGHTS.mkdir(parents=True, exist_ok=True)
    pth = WEIGHTS / "hair_length_merged_mobilenetv2.pth"
    onnx_path = WEIGHTS / "hair_length_merged.onnx"

    history = []
    best_acc = 0.0
    best_cm = None
    t0 = time.time()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        run_loss = run_corr = run_tot = 0
        for x, y in train_loader:
            x, y = x.to(DEVICE, non_blocking=pin), y.to(DEVICE, non_blocking=pin)
            opt.zero_grad()
            out = model(x)
            loss = crit(out, y)
            loss.backward()
            opt.step()
            run_loss += loss.item() * x.size(0)
            run_corr += (out.argmax(1) == y).sum().item()
            run_tot += x.size(0)
        sched.step()
        tr_acc = run_corr / max(run_tot, 1)
        va_loss, va_acc, cm = evaluate(model, val_loader)
        history.append({"epoch": epoch, "train_acc": round(tr_acc, 4), "val_acc": round(va_acc, 4), "val_loss": round(va_loss, 4)})
        print(f"epoch {epoch:2d}/{EPOCHS} train_acc={tr_acc:.4f} val_acc={va_acc:.4f} ({time.time()-t0:.0f}s)")
        if va_acc >= best_acc:
            best_acc = va_acc
            best_cm = cm
            torch.save(model.state_dict(), pth)

    model.load_state_dict(torch.load(pth, weights_only=True, map_location="cpu"))
    model.to("cpu")
    model.eval()
    # Export SINGLE-FILE (embed bobot) agar bisa dipakai readFileSync di produksi.
    for _f in (onnx_path, onnx_path.with_suffix(".onnx.data")):
        _f.unlink(missing_ok=True)
    torch.onnx.export(
        model,
        torch.randn(1, 3, 224, 224),
        str(onnx_path),
        input_names=["input"],
        output_names=["logits"],
        opset_version=OPSET,
        dynamo=False,
        external_data=False,
    )

    labels_path = WEIGHTS / "hair_length_labels.json"
    labels_path.write_text(json.dumps({"classes": LENGTH_CLASSES, "model": "mobilenet_v2", "task": "hair_length"}, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "task": "hair_length",
        "dataset": "merged (figaro + figaro-extra + bald + hairstyle40)",
        "label_source_figaro": idx.get("label_source"),
        "classes": LENGTH_CLASSES,
        "train_tensor": len(train_ds),
        "val_tensor": len(val_ds),
        "epochs": EPOCHS,
        "batch": BATCH,
        "lr": LR,
        "history": history,
        "best_val_acc": round(best_acc, 4),
        "confusion_matrix": best_cm,
        "onnx": str(onnx_path),
        "opset": OPSET,
        "duration_s": round(time.time() - t0, 1),
    }
    (WEIGHTS / "_train_report_length_merged.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nSELESAI best_val_acc={best_acc:.4f} -> {onnx_path}")
    print(f"labels -> {labels_path}")


if __name__ == "__main__":
    main()
