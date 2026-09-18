# -*- coding: utf-8 -*-
"""hair_type/train.py — Latih CNN jenis rambut (MobileNetV2).

Data: dataset back-view (hasil filter viewpoint). Input 224x224 ImageNet-norm.
Output: hair_type/weights/hair_type.onnx + reports.

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\hair_type\\train.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import HAIR_TYPE_CLASSES, IMAGENET_MEAN, IMAGENET_STD, INPUT_SIZE, SEED

HERE = Path(__file__).resolve().parent
CV_DIR = HERE.parent
WEIGHTS = HERE / "weights"
REPORTS = HERE / "reports"
# dataset tensor hasil preprocess lama (kompatibel)
INDEX_CANDIDATES = [
    CV_DIR / "preprocessed" / "index.json",
]

EPOCHS = 12
BATCH = 32
LR = 1e-3
WD = 1e-4
VAL_RATIO = 0.15


def main():
    ap = argparse.ArgumentParser(description="Latih hair_type (MobileNetV2).")
    ap.add_argument("--index", default=None, help="Path index.json (image_id, kelas/relpath)")
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset
    from torchvision import models
    from PIL import Image

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}")

    index_path = Path(args.index) if args.index else next((p for p in INDEX_CANDIDATES if p.exists()), None)
    if not index_path or not index_path.exists():
        print("ERROR: index dataset tidak ditemukan. Sediakan --index (lihat README).")
        return
    data = json.loads(index_path.read_text(encoding="utf-8"))
    records = data.get("records") if isinstance(data, dict) else data
    ci = {c: i for i, c in enumerate(HAIR_TYPE_CLASSES)}

    rng = random.Random(args.seed)
    by = defaultdict(list)
    for r in records:
        by[r.get("kelas") or r.get("label")].append(r)
    tr, va = [], []
    for _, ents in by.items():
        rng.shuffle(ents)
        n = max(1, int(len(ents) * VAL_RATIO))
        va.extend(ents[:n]); tr.extend(ents[n:])
    print(f"train={len(tr)} val={len(va)}")

    def load(r):
        rel = r.get("relpath") or r.get("pt")
        t = torch.load(CV_DIR / rel, weights_only=True).squeeze(0)
        return t

    class DS(Dataset):
        def __init__(self, items, train):
            self.items, self.train = items, train
        def __len__(self):
            return len(self.items)
        def __getitem__(self, i):
            r = self.items[i]
            t = load(r)
            if self.train and random.random() < 0.5:
                t = torch.flip(t, dims=[2])
            return t, ci[r.get("kelas") or r.get("label")]

    tl = DataLoader(DS(tr, True), batch_size=BATCH, shuffle=True)
    vl = DataLoader(DS(va, False), batch_size=BATCH, shuffle=False)

    m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    m.classifier = nn.Sequential(nn.Dropout(0.5), nn.Linear(m.last_channel, len(HAIR_TYPE_CLASSES)))
    m = m.to(device)
    opt = torch.optim.Adam(m.parameters(), lr=LR, weight_decay=WD)
    crit = nn.CrossEntropyLoss()

    WEIGHTS.mkdir(parents=True, exist_ok=True)
    pth = WEIGHTS / "hair_type_mobilenetv2.pth"
    best = 0.0
    t0 = time.time()
    for ep in range(1, args.epochs + 1):
        m.train()
        for x, y in tl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(); loss = crit(m(x), y); loss.backward(); opt.step()
        m.eval(); cor = tot = 0
        with torch.no_grad():
            for x, y in vl:
                x, y = x.to(device), y.to(device)
                cor += (m(x).argmax(1) == y).sum().item(); tot += x.size(0)
        acc = cor / max(tot, 1)
        print(f"epoch {ep:2d} val={acc:.4f} ({time.time()-t0:.0f}s)", flush=True)
        if acc > best:
            best = acc; torch.save(m.state_dict(), pth)

    # export ONNX
    onnx_path = WEIGHTS / "hair_type.onnx"
    m.load_state_dict(torch.load(pth, map_location="cpu", weights_only=True))
    m.to("cpu").eval()
    torch.onnx.export(m, torch.randn(1, 3, INPUT_SIZE, INPUT_SIZE), str(onnx_path),
                      input_names=["input"], output_names=["logits"], opset_version=17, dynamo=False)
    rep = {"task": "hair_type", "backbone": "mobilenet_v2", "classes": HAIR_TYPE_CLASSES,
           "timestamp": datetime.now(timezone.utc).isoformat(),
           "train": len(tr), "val": len(va), "best_val_acc": round(best, 4), "onnx": str(onnx_path)}
    (REPORTS / "hair_type_train.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nbest val={best:.4f}\nONNX -> {onnx_path}")


if __name__ == "__main__":
    main()
