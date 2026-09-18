# -*- coding: utf-8 -*-
"""Fase 0+ — Benchmark backbone hair_length (JUJUR, ANTI-LEAKAGE, diperluas).

Mengapa script ini ada:
  - `scripts/bench_backbones.py` menguji 5 backbone (hasil valid, 1 split).
  - Perlu uji arsitektur MODERN yang belum dicoba: ConvNeXt-Small/Base,
    EfficientNet-B1/B2, EfficientNetV2-S, Swin-T, RegNet, MaxViT, dll.
  - Memakai SATU hold-out FIXED (anti-leakage) + macro-F1 (bukan hanya accuracy).

Prinsip (sesuai docs/08-roadmap-cv-lengkap.md):
  - Split tetap, sama untuk semua backbone (adil).
  - Laporkan accuracy + macro-F1 + per-class.
  - Dataset: preprocessed_length_merged (label geometris existing).

Jalankan (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\geometry\\bench_backbones_v2.py

Isolated: menulis hanya ke geometry/reports/. Tidak menyentuh scripts/ lama.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models

BASE = Path(__file__).resolve().parents[1]          # apps/api/cv
GEO = Path(__file__).resolve().parents[0]
WEIGHTS = BASE / "weights"
REPORTS = GEO / "reports"
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"

CLS = ["pendek", "pendek-menengah", "menengah", "panjang"]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Hyperparameter (sama untuk semua backbone -> adil)
EPOCHS = 18
BATCH = 32
LR_HEAD = 1.5e-3
LR_FULL = 2.5e-4
WD = 2e-4
DROPOUT = 0.35
LS = 0.08
WARMUP = 3
PATIENCE = 6
VAL_RATIO = 0.25
SPLIT_SEED = 42
INIT_SEED = 42

# Batch size adaptif per backbone (VRAM RTX 3050 = ~4GB).
# Backbone besar/attention-heavy pakai batch lebih kecil agar tidak OOM.
BATCH_PER_BACKBONE = {
    "mobilenet_v2": 32,
    "mobilenet_v3_large": 32,
    "shufflenet_v2_x2_0": 32,
    "efficientnet_b0": 32,
    "efficientnet_b1": 24,
    "efficientnet_b2": 20,
    "efficientnet_v2_s": 20,
    "resnet50": 24,
    "regnet_y_800mf": 32,
    "regnet_y_1_6gf": 20,
    "convnext_tiny": 24,
    "convnext_small": 16,
    "convnext_base": 8,
    "swin_t": 12,
    "maxvit_t": 6,
}
# Urutan fallback bila OOM (batch diturunkan bertahap)
BATCH_FALLBACK = [32, 24, 16, 12, 8, 6, 4, 2]


# ------------------------------------------------------------------
# Model factory — (name, constructor, backbone_attr, in_features_fn)
# ------------------------------------------------------------------
def build_model(name: str):
    """Kembalikan (model, backbone_attr) untuk backbone yang diminta."""
    if name == "mobilenet_v2":
        m = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        m.classifier = nn.Sequential(nn.Dropout(DROPOUT), nn.Linear(m.last_channel, len(CLS)))
        return m, "features"
    if name == "mobilenet_v3_large":
        m = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, len(CLS))
        return m, "features"
    if name == "efficientnet_b0":
        m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(CLS))
        return m, "features"
    if name == "efficientnet_b1":
        m = models.efficientnet_b1(weights=models.EfficientNet_B1_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(CLS))
        return m, "features"
    if name == "efficientnet_b2":
        m = models.efficientnet_b2(weights=models.EfficientNet_B2_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(CLS))
        return m, "features"
    if name == "efficientnet_v2_s":
        m = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, len(CLS))
        return m, "features"
    if name == "resnet50":
        m = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, len(CLS))
        return m, "nobn"
    if name == "convnext_tiny":
        m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, len(CLS))
        return m, "features"
    if name == "convnext_small":
        m = models.convnext_small(weights=models.ConvNeXt_Small_Weights.DEFAULT)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, len(CLS))
        return m, "features"
    if name == "convnext_base":
        m = models.convnext_base(weights=models.ConvNeXt_Base_Weights.DEFAULT)
        m.classifier[2] = nn.Linear(m.classifier[2].in_features, len(CLS))
        return m, "features"
    if name == "swin_t":
        m = models.swin_t(weights=models.Swin_T_Weights.DEFAULT)
        m.head = nn.Linear(m.head.in_features, len(CLS))
        return m, "features"
    if name == "regnet_y_800mf":
        m = models.regnet_y_800mf(weights=models.RegNet_Y_800MF_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, len(CLS))
        return m, "nobn"
    if name == "regnet_y_1_6gf":
        m = models.regnet_y_1_6gf(weights=models.RegNet_Y_1_6GF_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, len(CLS))
        return m, "nobn"
    if name == "maxvit_t":
        m = models.maxvit_t(weights=models.MaxVit_T_Weights.DEFAULT)
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, len(CLS))
        return m, "features"
    if name == "shufflenet_v2_x2_0":
        m = models.shufflenet_v2_x2_0(weights=models.ShuffleNet_V2_X2_0_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, len(CLS))
        return m, "nobn"
    raise ValueError(f"backbone tak dikenal: {name}")


def set_grad(model, backbone_attr, enabled, name):
    if name.startswith("resnet") or name.startswith("regnet") or name.startswith("shufflenet"):
        for p in model.parameters():
            p.requires_grad = enabled
        if not enabled:
            # buka head (fc) saja
            for m_name in ("fc",):
                if hasattr(model, m_name):
                    for p in getattr(model, m_name).parameters():
                        p.requires_grad = True
    else:
        for p in getattr(model, backbone_attr).parameters():
            p.requires_grad = enabled


# ------------------------------------------------------------------
# Dataset
# ------------------------------------------------------------------
class AugDataset(Dataset):
    def __init__(self, base, items, train):
        self.base, self.items, self.train = base, items, train

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        pt, label = self.items[i]
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
            t[:, y0:y0 + eh, x0:x0 + ew] = 0.0
        return t, label


def fixed_split(entries, ratio, seed):
    """Split HOLD-OUT tetap (anti-leakage): sama untuk semua backbone."""
    rng = random.Random(seed)
    by = defaultdict(list)
    for e in entries:
        by[e["kelas"]].append(e)
    tr, va = [], []
    for _, ents in by.items():
        ents = sorted(ents, key=lambda e: e["pt"])
        rng.shuffle(ents)
        n = max(1, int(len(ents) * ratio))
        va.extend(ents[:n])
        tr.extend(ents[n:])
    return tr, va


# ------------------------------------------------------------------
# Train / eval
# ------------------------------------------------------------------
def evaluate(model, loader):
    model.eval()
    n_cls = len(CLS)
    cm = np.zeros((n_cls, n_cls), dtype=int)
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            pred = model(x).argmax(1)
            for t, p in zip(y.tolist(), pred.tolist()):
                cm[t][p] += 1
    total = cm.sum()
    acc = np.trace(cm) / total if total else 0.0
    # macro-F1
    f1s = []
    for c in range(n_cls):
        tp = cm[c, c]
        fp = cm[:, c].sum() - tp
        fn = cm[c, :].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        f1s.append(f1)
    macro_f1 = float(np.mean(f1s))
    return float(acc), macro_f1, cm.tolist()


def train_one(name, train_e, val_e, batch):
    torch.manual_seed(INIT_SEED)
    random.seed(INIT_SEED)
    np.random.seed(INIT_SEED)

    ci = {c: i for i, c in enumerate(CLS)}
    tl = DataLoader(AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in train_e], True),
                    batch_size=batch, shuffle=True, num_workers=0, pin_memory=True, drop_last=True)
    vl = DataLoader(AugDataset(BASE, [(e["pt"], ci[e["kelas"]]) for e in val_e], False),
                    batch_size=min(batch, 32), shuffle=False, num_workers=0, pin_memory=True)

    cnt = np.array([sum(1 for e in train_e if e["kelas"] == c) for c in CLS], float)
    w = cnt.sum() / (len(CLS) * np.maximum(cnt, 1))
    crit = nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32).to(DEVICE), label_smoothing=LS)

    model, bb = build_model(name)
    model = model.to(DEVICE)
    n_params = sum(p.numel() for p in model.parameters())
    set_grad(model, bb, False, name)
    head = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(head, lr=LR_HEAD, weight_decay=WD)

    best_acc, best_f1, best_cm, bep, noimp = 0.0, 0.0, None, 0, 0
    t0 = time.time()
    for ep in range(1, EPOCHS + 1):
        if ep == WARMUP + 1:
            set_grad(model, bb, True, name)
            opt = torch.optim.AdamW(model.parameters(), lr=LR_FULL, weight_decay=WD)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS - WARMUP)
        model.train()
        for x, y in tl:
            x, y = x.to(DEVICE, non_blocking=True), y.to(DEVICE, non_blocking=True)
            opt.zero_grad()
            loss = crit(model(x), y)
            loss.backward()
            opt.step()
        if ep > WARMUP:
            sched.step()
        acc, macro_f1, cm = evaluate(model, vl)
        if acc > best_acc:
            best_acc, best_f1, best_cm, bep, noimp = acc, macro_f1, cm, ep, 0
        else:
            noimp += 1
            if ep > WARMUP and noimp >= PATIENCE:
                break

    dur = time.time() - t0
    print(f"  {name:22s} acc={best_acc:.4f} macroF1={best_f1:.4f} @ep{bep} "
          f"params={n_params/1e6:.1f}M batch={batch} ({dur:.0f}s)", flush=True)
    return {
        "acc": round(best_acc, 4),
        "macro_f1": round(best_f1, 4),
        "best_epoch": bep,
        "params_m": round(n_params / 1e6, 1),
        "duration_s": round(dur),
        "confusion_matrix": best_cm,
    }


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
DEFAULT_BACKBONES = [
    # baseline lama (pembanding)
    "mobilenet_v2", "mobilenet_v3_large", "efficientnet_b0", "resnet50", "convnext_tiny",
    # kandidat baru
    "efficientnet_b1", "efficientnet_b2", "efficientnet_v2_s",
    "convnext_small", "convnext_base", "swin_t", "regnet_y_800mf", "regnet_y_1_6gf",
    "maxvit_t", "shufflenet_v2_x2_0",
]


def main():
    global EPOCHS
    ap = argparse.ArgumentParser(description="Benchmark backbone hair_length (jujur, anti-leakage).")
    ap.add_argument("--backbones", nargs="*", default=DEFAULT_BACKBONES, help="Daftar backbone")
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--seed", type=int, default=SPLIT_SEED)
    ap.add_argument("--out", default=str(REPORTS / "bench_backbones_v2.json"))
    args = ap.parse_args()

    EPOCHS = args.epochs

    REPORTS.mkdir(parents=True, exist_ok=True)
    print(f"=== Benchmark backbone v2 (JUJUR) ===\ndevice={DEVICE}", flush=True)

    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    # buang 'figaro' (label geometris utk figaro) -> konsisten dgn bench lama
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    tr, va = fixed_split(entries, VAL_RATIO, args.seed)
    from collections import Counter
    print(f"train={len(tr)} val={len(va)} (hold-out FIXED, seed={args.seed})", flush=True)
    print(f"val kelas: {dict(Counter(e['kelas'] for e in va))}", flush=True)
    print(f"backbone: {args.backbones}", flush=True)
    print(flush=True)

    results = {}
    for name in args.backbones:
        batch = BATCH_PER_BACKBONE.get(name, BATCH)
        # Coba batch default, turunkan bila OOM
        attempt_batches = [batch] + [b for b in BATCH_FALLBACK if b < batch]
        done = False
        for b in attempt_batches:
            try:
                torch.cuda.empty_cache()
                res = train_one(name, tr, va, b)
                res["batch"] = b
                results[name] = res
                done = True
                break
            except RuntimeError as exc:
                if "out of memory" in str(exc).lower():
                    print(f"  {name:22s} OOM @batch={b}, turun...")
                    torch.cuda.empty_cache()
                    continue
                print(f"  {name:22s} GAGAL: {str(exc)[:120]}")
                results[name] = {"error": str(exc)[:200]}
                done = True
                break
            except Exception as exc:
                print(f"  {name:22s} GAGAL: {str(exc)[:120]}")
                results[name] = {"error": str(exc)[:200]}
                done = True
                break
        if not done:
            print(f"  {name:22s} GAGAL: OOM di semua batch {attempt_batches}")
            results[name] = {"error": "OOM all batches"}

    # Ranking
    ok = {k: v for k, v in results.items() if "acc" in v}
    print("\n=== RANKING (by accuracy) ===")
    for k, v in sorted(ok.items(), key=lambda kv: -kv[1]["acc"]):
        print(f"  {k:22s} acc={v['acc']:.4f} macroF1={v['macro_f1']:.4f} params={v['params_m']}M")

    report = {
        "phase": "bench_backbones_v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": str(DEVICE),
        "split": {"val_ratio": VAL_RATIO, "seed": args.seed, "n_train": len(tr), "n_val": len(va)},
        "val_distribution": dict(Counter(e["kelas"] for e in va)),
        "results": results,
        "ranking_by_acc": sorted(ok, key=lambda k: -ok[k]["acc"]),
        "ranking_by_macro_f1": sorted(ok, key=lambda k: -ok[k]["macro_f1"]),
    }
    out = Path(args.out)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport -> {out}")


if __name__ == "__main__":
    main()
