# -*- coding: utf-8 -*-
"""hair_length/train.py — Latih CNN panjang rambut (efficientnet_v2_s champion).

Anti-leakage: hold-out tetap. Output ONNX ke hair_length/weights/hair_length.onnx.

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\hair_length\\train.py
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
from common.constants import HAIR_LENGTH_CLASSES, SEED

HERE = Path(__file__).resolve().parent
CV_DIR = HERE.parent
WEIGHTS = HERE / "weights"
REPORTS = HERE / "reports"
INDEX = CV_DIR / "preprocessed_length_merged" / "index_merged.json"

CLS = HAIR_LENGTH_CLASSES
EPOCHS = 40
BATCH = 20
LR_HEAD = 1.5e-3
LR_FULL = 2e-4
WD = 5e-2
DROPOUT = 0.3
WARMUP = 3
PATIENCE = 10
VAL_RATIO = 0.25
SPLIT_SEED = 42
BACKBONE = "efficientnet_v2_s"


def build(name, n_cls):
    from torchvision import models
    import torch.nn as nn
    if name == "efficientnet_v2_s":
        m = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.DEFAULT)
        m.classifier[1] = nn.Sequential(nn.Dropout(DROPOUT), nn.Linear(m.classifier[1].in_features, n_cls))
        return m, "features"
    if name == "convnext_tiny":
        m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
        m.classifier[2] = nn.Sequential(nn.Dropout(DROPOUT), nn.Linear(m.classifier[2].in_features, n_cls))
        return m, "features"
    raise ValueError(name)


def main():
    ap = argparse.ArgumentParser(description="Latih hair_length.")
    ap.add_argument("--backbone", default=BACKBONE, choices=["efficientnet_v2_s", "convnext_tiny"])
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--seed", type=int, default=SPLIT_SEED)
    args = ap.parse_args()

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device} backbone={args.backbone}")

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    rng = random.Random(args.seed)
    by = defaultdict(list)
    for e in entries:
        by[e["kelas"]].append(e)
    tr, va = [], []
    for _, ents in by.items():
        ents = sorted(ents, key=lambda e: e["pt"]); rng.shuffle(ents)
        n = max(1, int(len(ents) * VAL_RATIO)); va.extend(ents[:n]); tr.extend(ents[n:])
    print(f"train={len(tr)} val={len(va)}")
    ci = {c: i for i, c in enumerate(CLS)}

    class DS(Dataset):
        def __init__(self, items, train):
            self.items, self.train = items, train
        def __len__(self):
            return len(self.items)
        def __getitem__(self, i):
            e = self.items[i]
            t = torch.load(CV_DIR / e["pt"], weights_only=True).squeeze(0)
            if self.train:
                if random.random() < 0.5:
                    t = torch.flip(t, dims=[2])
                if random.random() < 0.6:
                    t = t * random.uniform(0.9, 1.1) + random.uniform(-0.1, 0.1)
            return t, ci[e["kelas"]]

    tl = DataLoader(DS(tr, True), batch_size=BATCH, shuffle=True, drop_last=True)
    vl = DataLoader(DS(va, False), batch_size=BATCH, shuffle=False)

    model, bb = build(args.backbone, len(CLS))
    model = model.to(device)
    for p in getattr(model, bb).parameters():
        p.requires_grad = False
    cnt = np.array([sum(1 for e in tr if e["kelas"] == c) for c in CLS], float)
    w = cnt.sum() / (len(CLS) * np.maximum(cnt, 1))
    crit = nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32).to(device), label_smoothing=0.08)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR_HEAD, weight_decay=WD)

    WEIGHTS.mkdir(parents=True, exist_ok=True)
    pth = WEIGHTS / f"hair_length_{args.backbone}.pth"
    best, noimp, best_cm = 0.0, 0, None

    def eval_m():
        model.eval(); n = len(CLS); cm = np.zeros((n, n), int)
        with torch.no_grad():
            for x, y in vl:
                x, y = x.to(device), y.to(device)
                p = model(x).argmax(1)
                for t, pp in zip(y.tolist(), p.tolist()):
                    cm[t][pp] += 1
        return np.trace(cm) / max(cm.sum(), 1), cm.tolist()

    t0 = time.time()
    for ep in range(1, args.epochs + 1):
        if ep == WARMUP + 1:
            for p in getattr(model, bb).parameters():
                p.requires_grad = True
            opt = torch.optim.AdamW(model.parameters(), lr=LR_FULL, weight_decay=WD)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs - WARMUP)
        model.train()
        for x, y in tl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(); loss = crit(model(x), y); loss.backward(); opt.step()
        if ep > WARMUP:
            sched.step()
        acc, cm = eval_m()
        print(f"epoch {ep:2d} val={acc:.4f} ({time.time()-t0:.0f}s)", flush=True)
        if acc > best:
            best, best_cm, bep, noimp = acc, cm, ep, 0
            torch.save(model.state_dict(), pth)
        else:
            noimp += 1
            if ep > WARMUP and noimp >= PATIENCE:
                break

    onnx_path = WEIGHTS / "hair_length.onnx"
    model.load_state_dict(torch.load(pth, map_location="cpu", weights_only=True))
    model.to("cpu").eval()
    import torch as _t
    _t.onnx.export(model, _t.randn(1, 3, 224, 224), str(onnx_path),
                   input_names=["input"], output_names=["logits"], opset_version=14, dynamo=False)
    (REPORTS / "hair_length_train.json").write_text(json.dumps({
        "task": "hair_length", "arch": args.backbone, "classes": CLS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "train": len(tr), "val": len(va), "best_val_acc": round(best, 4), "best_epoch": bep,
        "confusion_matrix": best_cm, "onnx": str(onnx_path),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nbest val={best:.4f} @ep{bep}\nONNX -> {onnx_path}")


if __name__ == "__main__":
    main()
