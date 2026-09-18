# -*- coding: utf-8 -*-
"""Validasi backbone final: ConvNeXt-Tiny vs EfficientNetV2-S (multi-seed).

Hold-out FIXED (anti-leakage): SPLIT dibuat sekali; hanya init/seed training
yang divariasikan. Tujuan: memastikan keunggulan bukan kebetulan satu seed.

Usage (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\geometry\\compare_final_backbones.py
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
import torch

HERE = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(HERE))

# impor dari bench_backbones_v2
import bench_backbones_v2 as B  # noqa: E402

CLS = B.CLS
DEVICE = B.DEVICE


def run_backbone(name: str, tr, va, seeds: list[int], epochs: int) -> dict:
    """Latih satu backbone untuk beberapa seed pada split yang SAMA."""
    per_seed = []
    batch = B.BATCH_PER_BACKBONE.get(name, B.BATCH)
    for sd in seeds:
        B.EPOCHS = epochs
        B.INIT_SEED = sd
        # cari batch aman (fallback OOM)
        attempt = [batch] + [b for b in B.BATCH_FALLBACK if b < batch]
        done = False
        for b in attempt:
            try:
                torch.cuda.empty_cache()
                res = B.train_one(name, tr, va, b)
                res["seed"] = sd
                res["batch"] = b
                per_seed.append(res)
                done = True
                break
            except RuntimeError as exc:
                if "out of memory" in str(exc).lower():
                    continue
                raise
        if not done:
            per_seed.append({"seed": sd, "error": "OOM"})

    accs = [r["acc"] for r in per_seed if "acc" in r]
    f1s = [r["macro_f1"] for r in per_seed if "macro_f1" in r]
    return {
        "backbone": name,
        "per_seed": per_seed,
        "acc_mean": round(float(np.mean(accs)), 4) if accs else None,
        "acc_std": round(float(np.std(accs, ddof=1)), 4) if len(accs) > 1 else 0.0,
        "f1_mean": round(float(np.mean(f1s)), 4) if f1s else None,
        "f1_std": round(float(np.std(f1s, ddof=1)), 4) if len(f1s) > 1 else 0.0,
        "n_seeds": len(accs),
    }


def main():
    ap = argparse.ArgumentParser(description="Validasi ConvNeXt-Tiny vs EfficientNetV2-S (multi-seed).")
    ap.add_argument("--backbones", nargs="*", default=["convnext_tiny", "efficientnet_v2_s"])
    ap.add_argument("--seeds", nargs="*", type=int, default=[42, 7, 123])
    ap.add_argument("--epochs", type=int, default=18)
    ap.add_argument("--out", default=str(B.REPORTS / "backbone_final.json"))
    args = ap.parse_args()

    B.REPORTS.mkdir(parents=True, exist_ok=True)
    print(f"=== Validasi backbone final (multi-seed) ===\ndevice={DEVICE}", flush=True)
    print(f"backbones: {args.backbones} | seeds: {args.seeds} | epochs: {args.epochs}", flush=True)

    idx = json.loads(B.INDEX.read_text(encoding="utf-8"))
    entries = [e for e in (idx["index"]["train"] + idx["index"]["val"]) if e["sumber"] != "figaro"]
    tr, va = B.fixed_split(entries, B.VAL_RATIO, args.seeds[0])  # split tetap pakai seed pertama
    print(f"train={len(tr)} val={len(va)} (hold-out FIXED)", flush=True)
    print(f"val kelas: {dict(Counter(e['kelas'] for e in va))}\n", flush=True)

    results = {}
    for name in args.backbones:
        print(f"--- {name} ---", flush=True)
        results[name] = run_backbone(name, tr, va, args.seeds, args.epochs)

    print("\n=== RINGKASAN (mean ± std) ===", flush=True)
    for name, r in sorted(results.items(), key=lambda kv: -(kv[1]["acc_mean"] or 0)):
        print(f"  {name:20s} acc={r['acc_mean']}±{r['acc_std']} "
              f"macroF1={r['f1_mean']}±{r['f1_std']} (n_seeds={r['n_seeds']})", flush=True)

    best = max(results.items(), key=lambda kv: (kv[1]["acc_mean"] or 0))
    report = {
        "analysis": "backbone_final",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": str(DEVICE),
        "split": {"val_ratio": B.VAL_RATIO, "n_train": len(tr), "n_val": len(va)},
        "seeds": args.seeds,
        "epochs": args.epochs,
        "results": results,
        "best_backbone": best[0],
        "best_acc_mean": best[1]["acc_mean"],
    }
    out = Path(args.out)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n>>> TERBAIK: {best[0]} (acc {best[1]['acc_mean']}±{best[1]['acc_std']})", flush=True)
    print(f"Report -> {out}", flush=True)


if __name__ == "__main__":
    main()
