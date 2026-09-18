# -*- coding: utf-8 -*-
"""Training MobileNetV2 hair_length (4 kelas panjang) -> ONNX (Fase 3.3).

Membaca tensor NCHW (.pt) via index dari prepare_length_dataset.py (method
geometric atau gemini). Struktur identik export_to_onnx.py hair_type.

Jalankan (Python GLOBAL: torch + torchvision):
  python apps\\api\\cv\\scripts\\export_to_onnx_length.py --method geometric --tag geom
  python apps\\api\\cv\\scripts\\export_to_onnx_length.py --method gemini    --tag gemini

Output:
  apps/api/cv/weights/hair_length_<tag>.onnx
  apps/api/cv/weights/hair_length_<tag>_labels.json
  apps/api/cv/weights/_train_report_length_<tag>.json
"""

from __future__ import annotations

import argparse
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
INDEX_DIR = BASE / "preprocessed_length"
LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]

EPOCHS = 12
BATCH = 32
LR = 1e-3
WEIGHT_DECAY = 1e-4
SEED = 42
OPSET = 17


class IndexedTensorDataset(Dataset):
    """Dataset dari index JSON: tiap entry menunjuk file .pt + label."""

    def __init__(self, base: Path, entries: list[dict]):
        self.base = base
        self.classes = LENGTH_CLASSES
        self.cls_to_idx = {c: i for i, c in enumerate(self.classes)}
        self.items = [(base / e["pt"], self.cls_to_idx[e["label"]]) for e in entries if e["label"] in self.cls_to_idx]

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        path, label = self.items[idx]
        t = torch.load(path, weights_only=True, map_location="cpu")
        t = t.squeeze(0)
        return t, label


def build_model() -> nn.Module:
    m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    m.classifier[1] = nn.Linear(m.last_channel, len(LENGTH_CLASSES))
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
    if total == 0:
        return 0.0, 0.0
    return loss_sum / total, correct / total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["geometric", "gemini"], required=True)
    ap.add_argument("--tag", required=True, help="suffix nama model, mis. geom / gemini")
    args = ap.parse_args()

    random.seed(SEED)
    torch.manual_seed(SEED)

    index_path = INDEX_DIR / f"index_{args.method}.json"
    if not index_path.exists():
        raise SystemExit(f"index tidak ada: {index_path} (jalankan prepare_length_dataset.py --method {args.method})")

    idx = json.loads(index_path.read_text(encoding="utf-8"))
    if idx.get("method") != args.method:
        print(f"WARN: index method={idx.get('method')} != requested {args.method}; regenerate dulu.")
        raise SystemExit(1)

    train_ds = IndexedTensorDataset(BASE, idx["index"]["train"])
    val_ds = IndexedTensorDataset(BASE, idx["index"]["val"])
    n_train, n_val = len(train_ds), len(val_ds)
    print(f"[{args.tag}] train={n_train} val={n_val}")
    if n_train == 0 or n_val == 0:
        raise SystemExit("dataset kosong — label mungkin belum cukup")

    train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=0)

    model = build_model()
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    WEIGHTS.mkdir(parents=True, exist_ok=True)
    pth_path = WEIGHTS / f"hair_length_{args.tag}_mobilenetv2.pth"
    onnx_path = WEIGHTS / f"hair_length_{args.tag}.onnx"
    labels_json = WEIGHTS / f"hair_length_{args.tag}_labels.json"
    report_path = WEIGHTS / f"_train_report_length_{args.tag}.json"

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
        tr_loss = run_loss / max(run_tot, 1)
        tr_acc = run_corr / max(run_tot, 1)
        va_loss, va_acc = evaluate(model, val_loader)
        history.append(
            {
                "epoch": epoch,
                "train_loss": round(tr_loss, 4),
                "train_acc": round(tr_acc, 4),
                "val_loss": round(va_loss, 4),
                "val_acc": round(va_acc, 4),
            }
        )
        print(f"[{args.tag}] epoch {epoch:2d}/{EPOCHS} train_acc={tr_acc:.4f} val_acc={va_acc:.4f} ({time.time()-t0:.0f}s)")
        if va_acc >= best_val:
            best_val = va_acc
            torch.save(model.state_dict(), pth_path)

    if pth_path.exists():
        model.load_state_dict(torch.load(pth_path, weights_only=True, map_location="cpu"))
    model.eval()

    dummy = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        model,
        dummy,
        str(onnx_path),
        input_names=["input"],
        output_names=["logits"],
        opset_version=OPSET,
        dynamic_axes=None,
    )

    labels_json.write_text(
        json.dumps({"classes": LENGTH_CLASSES, "model": "mobilenet_v2", "task": "hair_length"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report = {
        "task": "hair_length",
        "method": args.method,
        "tag": args.tag,
        "backbone": "mobilenet_v2 (pretrained ImageNet)",
        "classes": LENGTH_CLASSES,
        "train_tensor": n_train,
        "val_tensor": n_val,
        "epochs": EPOCHS,
        "batch": BATCH,
        "lr": LR,
        "weight_decay": WEIGHT_DECAY,
        "history": history,
        "best_val_acc": round(best_val, 4),
        "onnx": str(onnx_path),
        "opset": OPSET,
        "duration_s": round(time.time() - t0, 1),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[{args.tag}] SELESAI best_val_acc={best_val:.4f} -> {onnx_path}")


if __name__ == "__main__":
    main()
