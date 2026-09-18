# -*- coding: utf-8 -*-
"""hair_length/bench_backbones.py — Benchmark backbone (jujur, anti-leakage).

Pilih backbone terbaik untuk panjang rambut. Juara: efficientnet_v2_s.

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\hair_length\\bench_backbones.py

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" hair_length\\bench_backbones.py --backbones convnext_tiny efficientnet_v2_s
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
EPOCHS = 18
VAL_RATIO = 0.25
SPLIT_SEED = 42
BATCH_PER_BACKBONE = {
    "mobilenet_v2": 32, "mobilenet_v3_large": 32, "efficientnet_b0": 32,
    "efficientnet_b1": 24, "efficientnet_b2": 20, "efficientnet_v2_s": 20,
    "resnet50": 24, "convnext_tiny": 24, "convnext_small": 16, "convnext_base": 8,
    "swin_t": 12, "regnet_y_800mf": 32, "regnet_y_1_6gf": 20,
}
BATCH_FALLBACK = [32, 24, 16, 12, 8, 6, 4, 2]

DEFAULT = ["convnext_tiny", "efficientnet_v2_s"]


def build_model(name, n_cls):
    from torchvision import models
    import torch.nn as nn
    if name == "mobilenet_v2":
        m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        m.classifier = nn.Sequential(nn.Dropout(0.35), nn.Linear(m.last_channel, n_cls))
        return m, "features"
    if name == "mobilenet_v3_large":
        m = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, n_cls); return m, "features"
    if name == "efficientnet_b0":
        m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, n_cls); return m, "features"
    if name == "efficientnet_b1":
        m = models.efficientnet_b1(weights=models.EfficientNet_B1_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, n_cls); return m, "features"
    if name == "efficientnet_b2":
        m = models.efficientnet_b2(weights=models.EfficientNet_B2_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, n_cls); return m, "features"
    if name == "efficientnet_v2_s":
        m = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, n_cls); return m, "features"
    if name == "resnet50":
        m = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, n_cls); return m, "nobn"
    if name == "convnext_tiny":
        m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, n_cls); return m, "features"
    if name == "convnext_small":
        m = models.convnext_small(weights=models.ConvNeXt_Small_Weights.DEFAULT)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, n_cls); return m, "features"
    if name == "convnext_base":
        m = models.convnext_base(weights=models.ConvNeXt_Base_Weights.DEFAULT)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, n_cls); return m, "features"
    if name == "swin_t":
        m = models.swin_t(weights=models.Swin_T_Weights.DEFAULT)
        m.head = nn.Linear(m.head.in_features, n_cls); return m, "features"
    if name == "regnet_y_800mf":
        m = models.regnet_y_800mf(weights=models.RegNet_Y_800MF_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, n_cls); return m, "nobn"
    if name == "regnet_y_1_6gf":
        m = models.regnet_y_1_6gf(weights=models.RegNet_Y_1_6GF_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, n_cls); return m, "nobn"
    raise ValueError(name)


def main():
    ap = argparse.ArgumentParser(description="Benchmark backbone hair_length.")
    ap.add_argument("--backbones", nargs="*", default=DEFAULT)
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--seed", type=int, default=SPLIT_SEED)
    ap.add_argument("--out", default=str(REPORTS / "bench_backbones.json"))
    args = ap.parse_args()

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    REPORTS.mkdir(parents=True, exist_ok=True)
    print(f"device={device}")

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
    CVV = CV_DIR

    class DS(Dataset):
        def __init__(self, items, train):
            self.items, self.train = items, train
        def __len__(self):
            return len(self.items)
        def __getitem__(self, i):
            e = self.items[i]
            t = torch.load(CVV / e["pt"], weights_only=True).squeeze(0)
            if self.train:
                if random.random() < 0.5:
                    t = torch.flip(t, dims=[2])
                if random.random() < 0.6:
                    t = t * random.uniform(0.92, 1.08) + random.uniform(-0.08, 0.08)
            return t, ci[e["kelas"]]

    def evaluate(model, loader):
        model.eval(); n = len(CLS); cm = np.zeros((n, n), int)
        with torch.no_grad():
            for x, y in loader:
                x, y = x.to(device), y.to(device)
                p = model(x).argmax(1)
                for t, pp in zip(y.tolist(), p.tolist()):
                    cm[t][pp] += 1
        acc = np.trace(cm) / max(cm.sum(), 1)
        f1s = []
        for c in range(n):
            tp = cm[c, c]; fp = cm[:, c].sum() - tp; fn = cm[c, :].sum() - tp
            pr = tp / (tp + fp) if (tp + fp) else 0.0; rc = tp / (tp + fn) if (tp + fn) else 0.0
            f1s.append(2 * pr * rc / (pr + rc) if (pr + rc) else 0.0)
        return float(acc), float(np.mean(f1s))

    results = {}
    for name in args.backbones:
        batch = BATCH_PER_BACKBONE.get(name, 32)
        att = [batch] + [b for b in BATCH_FALLBACK if b < batch]
        done = False
        for b in att:
            try:
                torch.cuda.empty_cache()
                torch.manual_seed(args.seed)
                tl = DataLoader(DS(tr, True), batch_size=b, shuffle=True, drop_last=True)
                vl = DataLoader(DS(va, False), batch_size=b, shuffle=False)
                model, bb = build_model(name, len(CLS)); model = model.to(device)
                if bb == "nobn":
                    for p in model.parameters(): p.requires_grad = True
                else:
                    for p in getattr(model, bb).parameters(): p.requires_grad = False
                    for p in getattr(model, "classifier" if hasattr(model, "classifier") else "fc").parameters(): p.requires_grad = True
                head = [p for p in model.parameters() if p.requires_grad]
                opt = torch.optim.AdamW(head, lr=1.5e-3)
                cnt = np.array([sum(1 for e in tr if e["kelas"] == c) for c in CLS], float)
                w = cnt.sum() / (len(CLS) * np.maximum(cnt, 1))
                crit = nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32).to(device), label_smoothing=0.08)
                best, bep, noimp = 0.0, 0, 0
                t0 = time.time()
                for ep in range(1, args.epochs + 1):
                    if ep == 4 and bb != "nobn":
                        for p in getattr(model, bb).parameters(): p.requires_grad = True
                        opt = torch.optim.AdamW(model.parameters(), lr=2.5e-4)
                    model.train()
                    for x, y in tl:
                        x, y = x.to(device), y.to(device)
                        opt.zero_grad(); loss = crit(model(x), y); loss.backward(); opt.step()
                    acc, f1 = evaluate(model, vl)
                    if acc > best:
                        best, best_f1, bep, noimp = acc, f1, ep, 0
                    else:
                        noimp += 1
                        if ep > 4 and noimp >= 6:
                            break
                print(f"  {name:20s} acc={best:.4f} macroF1={best_f1:.4f} @ep{bep} batch={b} ({time.time()-t0:.0f}s)", flush=True)
                results[name] = {"acc": round(best, 4), "macro_f1": round(best_f1, 4), "batch": b}
                done = True
                break
            except RuntimeError as exc:
                if "out of memory" in str(exc).lower():
                    continue
                results[name] = {"error": str(exc)[:150]}; done = True; break
        if not done:
            results[name] = {"error": "OOM"}

    ok = {k: v for k, v in results.items() if "acc" in v}
    ranking = sorted(ok, key=lambda k: -ok[k]["acc"])
    json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "results": results,
               "ranking_by_acc": ranking}, (Path(args.out)).open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n=== Ranking ===")
    for k in ranking:
        print(f"  {k:20s} acc={ok[k]['acc']:.4f} macroF1={ok[k]['macro_f1']:.4f}")
    print(f"\nReport -> {args.out}")


if __name__ == "__main__":
    main()
