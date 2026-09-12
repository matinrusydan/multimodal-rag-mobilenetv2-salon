# -*- coding: utf-8 -*-
"""Preprocess figaro1k (4 kelas salon) -> tensor NCHW float32.

Pipeline terstandar (disepakati, task 07-cv.md §2 & keputusan arsitektur):
  - Input: RGB 8-bit sRGB  (TANPA grayscale — warna = parameter kunci salon).
  - auto-orient EXIF (exif_transpose), resize keep-aspect (sisi pendek 256),
    center-crop 224, ToTensor, Normalize ImageNet  =>  tensor (1,3,224,224).
  - TRAIN augmentasi: RandomResizedCrop(0.875–1.0) + RandomHorizontalFlip(0.5)
    + RandomRotation(±10°). Setiap citra train disimpan (1 + AUG_REPEAT) versi.
  - VAL/INFERENCE: SAMA PERSIS train pipeline TANPA augmentasi (resize+crop
    identik) agar metrik valid konsisten dengan inferensi runtime.

Output layout (apps/api/cv/preprocessed/):
  train/<KELAS>/<stem>_r<rep>.pt
  val/<KELAS>/<stem>.pt
  _preprocess_report.json
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import torch
from PIL import Image, ImageOps
from torchvision import transforms as T
from torchvision.transforms import InterpolationMode

BASE = Path(__file__).resolve().parents[1]
DATASET = BASE / "dataset" / "figaro1k"
OUT = BASE / "preprocessed"
REPORT = OUT / "_preprocess_report.json"

CLASSES = ["lurus", "bergelombang", "keriting", "sangat-keriting"]

# Pipeline geometry
RESIZE_SIDE = 256
CROP = 224
MIN_SIDE = 224        # citra < 224px cannot be center-cropped -> skip & count

# Augmentasi train (hanya train; val/inference identik tanpa aug)
RRC_SCALE = (0.875, 1.0)
RRC_RATIO = (3.0 / 4.0, 4.0 / 3.0)
FLIP_P = 0.5
ROT_DEG = 10
AUG_REPEAT = 2        # tiap citra train -> (1 + AUG_REPEAT) versi

# Split
VAL_RATIO = 0.2       # 20% per kelas -> val
SEED = 42

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def _train_transforms() -> T.Compose:
    return T.Compose([
        T.RandomResizedCrop(
            CROP,
            scale=RRC_SCALE,
            ratio=RRC_RATIO,
            interpolation=InterpolationMode.BILINEAR,
            antialias=True,
        ),
        T.RandomHorizontalFlip(p=FLIP_P),
        T.RandomRotation(degrees=ROT_DEG, interpolation=InterpolationMode.BILINEAR),
    ])


def _val_transforms() -> T.Compose:
    return T.Compose([
        T.Resize(RESIZE_SIDE, interpolation=InterpolationMode.BILINEAR, antialias=True),
        T.CenterCrop(CROP),
    ])


def _to_nchw(img: Image.Image, basic: T.Compose) -> torch.Tensor:
    from torchvision import transforms as _T
    pipe = _T.Compose([
        basic,
        _T.ToTensor(),
        _T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
    return pipe(img).unsqueeze(0)   # (1,3,224,224)


def _load_rgb(path: Path) -> Image.Image | None:
    """Baca RGB 8-bit sRGB (tanpa grayscale), auto-orient EXIF, minimal 224px."""
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode != "RGB":
                return None
            if min(im.size) < MIN_SIDE:
                return None
            return im.convert("RGB")
    except Exception:
        return None


def main() -> None:
    random.seed(SEED)
    torch.manual_seed(SEED)

    if not DATASET.exists():
        print(f"ERROR: dataset tidak ditemukan: {DATASET}", file=sys.stderr)
        sys.exit(1)

    train_basic = _train_transforms()
    val_basic = _val_transforms()

    stats: dict[str, dict] = {}
    grand_total = 0
    total_skip = 0

    for cls in CLASSES:
        d = DATASET / cls
        files = sorted(d.glob("*.jpg"))
        n = len(files)
        if n == 0:
            print(f"  WARN: folder {cls} kosong", file=sys.stderr)
            continue

        rng = random.Random(SEED + len(cls.encode()))
        order = list(range(n))
        rng.shuffle(order)
        n_val = max(1, math.ceil(n * VAL_RATIO))
        val_idx = set(order[:n_val])
        train_idx = [i for i in order if i not in val_idx]

        tdir = OUT / "train" / cls
        vdir = OUT / "val" / cls
        tdir.mkdir(parents=True, exist_ok=True)
        vdir.mkdir(parents=True, exist_ok=True)

        n_train = 0
        n_val_ok = 0
        skip = 0

        for i in train_idx:
            img = _load_rgb(files[i])
            if img is None:
                skip += 1
                continue
            for rep in range(AUG_REPEAT + 1):
                t = _to_nchw(img, train_basic)
                torch.save(t, tdir / f"{files[i].stem}_r{rep}.pt")
                n_train += 1

        for i in sorted(val_idx):
            img = _load_rgb(files[i])
            if img is None:
                skip += 1
                continue
            t = _to_nchw(img, val_basic)
            torch.save(t, vdir / f"{files[i].stem}.pt")
            n_val_ok += 1

        stats[cls] = {
            "citra_asli": n,
            "train_citra": len(train_idx),
            "train_versi": n_train,     # (1+AUG_REPEAT) * train_citra
            "val": n_val_ok,
            "skip": skip,
        }
        grand_total += n_train + n_val_ok
        total_skip += skip
        print(
            f"{cls}: asli={n} train={len(train_idx)} (x{AUG_REPEAT+1}->{n_train}) "
            f"val={n_val_ok} skip={skip}"
        )

    report = {
        "dataset": "figaro1k (partisi salon 4 kelas)",
        "pipeline": "RGB 8-bit sRGB -> exif_transpose -> resize keep-aspect 256 -> "
        "center-crop 224 -> ToTensor -> Normalize ImageNet -> NCHW float32",
        "augmentasi": {
            "RandomResizedCrop_scale": list(RRC_SCALE),
            "RandomResizedCrop_ratio": list(RRC_RATIO),
            "RandomHorizontalFlip_p": FLIP_P,
            "RandomRotation_deg": ROT_DEG,
            "train_repeat_per_citra": AUG_REPEAT + 1,
            "train_aug_luas": "Ya, hanya train",
        },
        "val_inference_identik": "Ya, tanpa augmentasi (konsisten akurasi)",
        "normalisasi": {"mean": IMAGENET_MEAN, "std": IMAGENET_STD},
        "per_kelas": stats,
        "TOTAL_TENSOR": grand_total,
        "TOTAL_SKIP": total_skip,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSELESAI. Tensor NCHW -> {OUT}")
    print(f"Laporan: {REPORT}")
    print(f"TOTAL tensor: {grand_total} (skip: {total_skip})")


if __name__ == "__main__":
    main()
