# -*- coding: utf-8 -*-
"""viewpoint/train_cnn.py — Latih CNN viewpoint 3-kelas (efficientnet_v2_s).

Menangani imbalance via class weight + augmentasi. Split stratified + hold-out tetap.
Output: viewpoint/weights/viewpoint_cnn.pth + viewpoint_cnn.onnx + reports.

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\viewpoint\\train_cnn.py

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\train_cnn.py
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
from common.constants import IMAGENET_MEAN, IMAGENET_STD, INPUT_SIZE, SEED, VIEWPOINT_CLASSES

HERE = Path(__file__).resolve().parent
CV_DIR = HERE.parent
INDEX = HERE / "dataset" / "index.json"
WEIGHTS_DIR = HERE / "weights"
REPORTS = HERE / "reports"

# Hyperparameter
EPOCHS = 30
BATCH = 16
LR_HEAD = 1.5e-3
LR_FULL = 2e-4
WD = 5e-2
DROPOUT = 0.3
LS = 0.08
WARMUP = 3
PATIENCE = 8
VAL_RATIO = 0.25
SPLIT_SEED = 42


def load_tensor(relpath: str):
    from PIL import Image
    import torch
    apps_dir = CV_DIR.parents[1]
    # cek dua format: relatif CV_DIR, atau relatif apps/
    p = CV_DIR / relpath
    if not p.exists():
        p = apps_dir / relpath
    im = Image.open(p).convert("RGB")
    im = im.resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR)
    f = np.asarray(im, dtype=np.float32) / 255.0
    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std = np.array(IMAGENET_STD, dtype=np.float32)
    t = ((f - mean) / std).transpose(2, 0, 1)
    return torch.from_numpy(np.ascontiguousarray(t))


def main():
    ap = argparse.ArgumentParser(description="Latih CNN viewpoint.")
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--seed", type=int, default=SPLIT_SEED)
    ap.add_argument("--backbone", default="efficientnet_v2_s")
    ap.add_argument("--index", default=str(INDEX), help="Path index dataset (default: dataset/index.json)")
    ap.add_argument("--tag", default="", help="Tag nama output model (mis. veronly)")
    args = ap.parse_args()

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset
    from torchvision import models

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}")

    data = json.loads(Path(args.index).read_text(encoding="utf-8"))
    records = data["records"]
    print(f"index: {args.index} | n={len(records)}")
    ci = {c: i for i, c in enumerate(VIEWPOINT_CLASSES)}

    # split stratified (hold-out tetap)
    rng = random.Random(args.seed)
    by = defaultdict(list)
    for r in records:
        by[r["label"]].append(r)
    tr, va = [], []
    for _, ents in by.items():
        ents = sorted(ents, key=lambda e: e["image_id"]); rng.shuffle(ents)
        n = max(1, int(len(ents) * VAL_RATIO))
        va.extend(ents[:n]); tr.extend(ents[n:])
    print(f"train={len(tr)} val={len(va)}")
    print(f"  val dist: {dict(Counter(r['label'] for r in va))}")

    class DS(Dataset):
        def __init__(self, items, train):
            self.items, self.train = items, train
        def __len__(self):
            return len(self.items)
        def __getitem__(self, i):
            r = self.items[i]
            t = load_tensor(r["relpath"])
            if self.train:
                if random.random() < 0.5:
                    t = torch.flip(t, dims=[2])
                if random.random() < 0.6:
                    t = t * random.uniform(0.9, 1.1) + random.uniform(-0.1, 0.1)
            return t, ci[r["label"]]

    tl = DataLoader(DS(tr, True), batch_size=BATCH, shuffle=True, num_workers=0)
    vl = DataLoader(DS(va, False), batch_size=BATCH, shuffle=False, num_workers=0)

    cnt = np.array([sum(1 for r in tr if r["label"] == c) for c in VIEWPOINT_CLASSES], float)
    w = cnt.sum() / (len(VIEWPOINT_CLASSES) * np.maximum(cnt, 1))
    crit = nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32).to(device), label_smoothing=LS)

    # model
    def build():
        m = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.DEFAULT)
        m.classifier[1] = nn.Sequential(nn.Dropout(DROPOUT), nn.Linear(m.classifier[1].in_features, len(VIEWPOINT_CLASSES)))
        return m

    def set_grad(m, en):
        for p in m.features.parameters():
            p.requires_grad = en

    model = build().to(device)
    set_grad(model, False)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR_HEAD, weight_decay=WD)

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    _tag = f"_{args.tag}" if args.tag else ""
    pth = WEIGHTS_DIR / f"viewpoint_cnn{_tag}.pth"
    best, noimp = 0.0, 0

    def evaluate():
        model.eval()
        n = len(VIEWPOINT_CLASSES); cm = np.zeros((n, n), int); cor = tot = 0
        with torch.no_grad():
            for x, y in vl:
                x, y = x.to(device), y.to(device)
                p = model(x).argmax(1)
                for t, pp in zip(y.tolist(), p.tolist()):
                    cm[t][pp] += 1
                cor += (p == y).sum().item(); tot += x.size(0)
        acc = cor / max(tot, 1)
        f1s = []
        for c in range(n):
            tp = cm[c, c]; fp = cm[:, c].sum() - tp; fn = cm[c, :].sum() - tp
            pr = tp / (tp + fp) if (tp + fp) else 0.0
            rc = tp / (tp + fn) if (tp + fn) else 0.0
            f1s.append(2 * pr * rc / (pr + rc) if (pr + rc) else 0.0)
        return acc, float(np.mean(f1s)), cm.tolist()

    t0 = time.time()
    for ep in range(1, args.epochs + 1):
        if ep == WARMUP + 1:
            set_grad(model, True)
            opt = torch.optim.AdamW(model.parameters(), lr=LR_FULL, weight_decay=WD)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs - WARMUP)
        model.train()
        for x, y in tl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = crit(model(x), y)
            loss.backward(); opt.step()
        if ep > WARMUP:
            sched.step()
        acc, f1, cm = evaluate()
        print(f"epoch {ep:2d} val={acc:.4f} macroF1={f1:.4f} ({time.time()-t0:.0f}s)", flush=True)
        if acc > best:
            best, best_f1, best_cm, bep, noimp = acc, f1, cm, ep, 0
            torch.save(model.state_dict(), pth)
        else:
            noimp += 1
            if ep > WARMUP and noimp >= PATIENCE:
                break

    report = {
        "task": "viewpoint", "backbone": args.backbone, "classes": VIEWPOINT_CLASSES,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "train": len(tr), "val": len(va), "val_distribution": dict(Counter(r["label"] for r in va)),
        "best_val_acc": round(best, 4), "best_macro_f1": round(best_f1, 4), "best_epoch": bep,
        "confusion_matrix": best_cm,
    }
    (REPORTS / f"viewpoint_cnn_train{_tag}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nbest acc={best:.4f} macroF1={best_f1:.4f} @ep{bep}")
    print(f"model -> {pth}")


if __name__ == "__main__":
    main()
