# -*- coding: utf-8 -*-
"""Bangun dataset panjang rambut gabungan (Figaro + dataset extra) -> tensor .pt.

Menggabungkan:
  1. Figaro-1k (600 citra) dengan label panjang dari SALAH SATU:
     - ground_truth_length.json (validasi manual, PRIORITAS tertinggi bila ada)
     - hair_length_geometris.json (metode geometris) — fallback
  2. Dataset extra (dataset/extra/<kelas>/*.jpg) dengan label eksplisit:
     - Figaro kelas tambahan (short-men/braids/dreadlocks)
     - kaggle-bald (pendek)
     - FaceSketches-HairStyle40 (40 gaya, label panjang eksplisit)

Semua citra dipreprocess dengan pipeline yang SAMA (resize 256 -> crop 224 ->
ImageNet norm -> NCHW) lalu disimpan sebagai .pt.

Output:
  apps/api/cv/preprocessed_length_merged/{train,val}/<kelas>/*.pt
  apps/api/cv/preprocessed_length_merged/index_merged.json

Jalankan (venv CV: PIL + numpy + torch TIDAK diperlukan untuk simpan .pt? -> pakai torch global):
  gunakan Python GLOBAL (torch) karena menyimpan torch tensor:
  $env:PYTHONIOENCODING='utf-8'
  python apps\\api\\cv\\scripts\\build_length_dataset.py --val-ratio 0.15
"""

from __future__ import annotations

import argparse
import json
import random
import zipfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

BASE = Path(__file__).resolve().parents[1]
ZIP_PATH = BASE / "dataset" / "figaro-1k.zip"
EXTRA = BASE / "dataset" / "extra"
REPORTS = BASE / "reports"
GT_JSON = REPORTS / "ground_truth_length.json"
GEO_JSON = REPORTS / "hair_length_geometris.json"
OUT = BASE / "preprocessed_length_merged"

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]

RESIZE_SIDE = 256
CROP = 224
MIN_SIDE = 64  # izinkan upscale citra kecil (mis. bald thumbnail) agar tidak terbuang
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
SEED = 42


def crop224(img: Image.Image) -> np.ndarray | None:
    if img.mode != "RGB":
        img = img.convert("RGB")
    if min(img.size) < MIN_SIDE:
        return None
    w, h = img.size
    scale = RESIZE_SIDE / min(h, w)
    rw = max(CROP, round(w * scale))
    rh = max(CROP, round(h * scale))
    resized = img.resize((rw, rh), Image.Resampling.BILINEAR)
    left = (rw - CROP) // 2
    top = (rh - CROP) // 2
    return np.asarray(resized.crop((left, top, left + CROP, top + CROP)), dtype=np.uint8)


def to_tensor(rgb: np.ndarray) -> torch.Tensor:
    f = rgb.astype(np.float32) / 255.0
    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std = np.array(IMAGENET_STD, dtype=np.float32)
    norm = (f - mean) / std
    t = np.transpose(norm, (2, 0, 1))[np.newaxis, ...]
    return torch.from_numpy(np.ascontiguousarray(t))


def figaro_label_map() -> tuple[dict[str, str], str]:
    """Prioritas: ground truth manual > geometris."""
    if GT_JSON.exists():
        data = json.loads(GT_JSON.read_text(encoding="utf-8"))
        recs = data.get("records", {})
        if recs:
            return {k: v["label"] for k, v in recs.items()}, "ground_truth"
    if GEO_JSON.exists():
        data = json.loads(GEO_JSON.read_text(encoding="utf-8"))
        return {f"{r['frame']:05d}": r["panjang_label"] for r in data.get("records", [])}, "geometric"
    return {}, "none"


def collect_items() -> list[tuple[str, str, str, str]]:
    """Kumpulkan (sumber, kelas, asal, payload). payload = 'zip:<frame>' atau 'file:<path>'."""
    items: list[tuple[str, str, str, str]] = []

    # 1. Figaro utama (zip) dengan label panjang
    lmap, src = figaro_label_map()
    if lmap:
        for frame in range(1, 601):
            key = f"{frame:05d}"
            if key in lmap:
                items.append(("figaro", lmap[key], "figaro-main", f"zip:{frame}"))
    # 2. dataset extra (file langsung)
    for kelas_dir in EXTRA.iterdir():
        if not kelas_dir.is_dir() or kelas_dir.name not in LENGTH_CLASSES:
            continue
        for jpg in kelas_dir.glob("*.jpg"):
            prefix = jpg.stem.split("_")[0]
            items.append((prefix, kelas_dir.name, jpg.stem, f"file:{jpg}"))
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--val-ratio", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    random.seed(args.seed)
    lmap, src = figaro_label_map()
    print(f"Label Figaro: {src} ({len(lmap)} frame)")

    items = collect_items()
    if not items:
        raise SystemExit("tidak ada citra — jalankan enrich_dataset.py / import_hairstyle40.py dulu")

    # simpan .pt
    for split in ("train", "val"):
        for c in LENGTH_CLASSES:
            (OUT / split / c).mkdir(parents=True, exist_ok=True)

    index: dict[str, list[dict]] = {"train": [], "val": []}
    dist: dict[str, dict[str, int]] = {s: {c: 0 for c in LENGTH_CLASSES} for s in ("train", "val")}
    skipped = 0

    z = zipfile.ZipFile(ZIP_PATH)
    zip_names = z.namelist()

    # dedup + split per (sumber, kelas)
    counter: dict[tuple[str, str], int] = {}
    for sumber, kelas, asal, payload in items:
        try:
            if payload.startswith("zip:"):
                frame = int(payload.split(":")[1])
                cands = [n for n in zip_names if f"Frame{frame:05d}-org.jpg" in n]
                if not cands:
                    skipped += 1
                    continue
                img = Image.open(__import__("io").BytesIO(z.read(cands[0])))
            else:
                img = Image.open(payload.split("file:", 1)[1])
            img = ImageOps.exif_transpose(img)
            rgb = crop224(img)
            if rgb is None:
                skipped += 1
                continue
        except Exception:
            skipped += 1
            continue

        key = (sumber, kelas)
        idx = counter.get(key, 0)
        counter[key] = idx + 1
        split = "val" if (idx % max(1, int(1 / args.val_ratio)) == 0) else "train"
        fname = f"{sumber}_{kelas}_{idx:05d}.pt"
        torch.save(to_tensor(rgb), OUT / split / kelas / fname)
        index[split].append({"pt": str((OUT / split / kelas / fname).relative_to(BASE)).replace("\\", "/"), "kelas": kelas, "sumber": sumber, "asal": asal})
        dist[split][kelas] += 1

    z.close()

    (OUT / "index_merged.json").write_text(
        json.dumps({"length_classes": LENGTH_CLASSES, "label_source": src, "index": index}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nSelesai. skipped={skipped}")
    for split in ("train", "val"):
        print(f"{split}: {len(index[split])} tensor | {dist[split]}")
    print(f"Index -> {OUT / 'index_merged.json'}")


if __name__ == "__main__":
    main()
