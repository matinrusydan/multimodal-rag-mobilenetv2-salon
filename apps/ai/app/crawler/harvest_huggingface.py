# -*- coding: utf-8 -*-
"""Harvest dataset gambar dari HuggingFace Hub (publik, tanpa token).

Menangani 3 format:
  1. Parquet dengan kolom gambar (mis. figaro)
  2. File gambar langsung di repo (mis. Kalva014 resized_imgs/, nrhone PNG root)
  3. pt (torch) — dilewati (tidak dipakai)

Output:
  apps/ai/app/crawler/harvest/huggingface/*.jpg
  apps/ai/app/crawler/harvest/_manifest_huggingface.json

Usage:
  & ".venv\\Scripts\\python.exe" -m app.crawler.harvest_huggingface --max-per 150
"""

from __future__ import annotations

import argparse
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("harvest_hf")

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "harvest"
IMG_DIR = OUT_DIR / "huggingface"
MANIFEST = OUT_DIR / "_manifest_huggingface.json"

DATASETS = [
    "Allison/figaro_hair_segmentation_1000",
    "Kalva014/male-asian-hairstyles",
    "nrhone/male-black-hairstyles",
]
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
MIN_SIDE = 224


def dhash(img, size=8):
    g = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    arr = np.asarray(g, dtype=int)
    diff = arr[:, 1:] > arr[:, :-1]
    return "".join("1" if b else "0" for b in diff.flatten())


def hamming(a, b):
    return sum(c1 != c2 for c1, c2 in zip(a, b))


def candidates_from_repo(ds_id: str):
    """Yield (key, PIL.Image) dari repo HF (parquet atau file gambar)."""
    from huggingface_hub import hf_hub_download, list_repo_files

    files = list_repo_files(ds_id, repo_type="dataset")

    # 1. parquet
    for f in [x for x in files if x.endswith(".parquet")]:
        try:
            import pyarrow.parquet as pq
            path = hf_hub_download(ds_id, f, repo_type="dataset")
            tbl = pq.read_table(path)
            img_col = next((c for c in tbl.column_names if c in ("image", "img", "images")), None)
            if not img_col:
                continue
            for i, cell in enumerate(tbl.column(img_col).to_pylist()):
                img = _cell_to_image(cell)
                if img is not None:
                    yield f"{f}:{i}", img
        except Exception as exc:
            logger.warning(f"  parquet {f} gagal: {str(exc)[:80]}")

    # 2. file gambar langsung
    for f in [x for x in files if x.lower().endswith(IMG_EXT)]:
        try:
            path = hf_hub_download(ds_id, f, repo_type="dataset")
            img = Image.open(path).convert("RGB")
            yield f, img
        except Exception:
            continue


def _cell_to_image(cell):
    try:
        if isinstance(cell, dict) and cell.get("bytes"):
            return Image.open(io.BytesIO(cell["bytes"])).convert("RGB")
        if isinstance(cell, (bytes, bytearray)):
            return Image.open(io.BytesIO(cell)).convert("RGB")
    except Exception:
        return None
    return None


def main():
    ap = argparse.ArgumentParser(description="Harvest dataset HF (parquet + file gambar).")
    ap.add_argument("--datasets", nargs="*", default=DATASETS)
    ap.add_argument("--max-per", type=int, default=150)
    ap.add_argument("--min-side", type=int, default=MIN_SIDE)
    args = ap.parse_args()

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    manifest, hashes = [], []
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            hashes = [m["dhash"] for m in manifest if m.get("dhash")]
        except Exception:
            manifest = []

    total = 0
    for ds_id in args.datasets:
        logger.info(f"[hf] {ds_id}")
        n = 0
        try:
            for key, img in candidates_from_repo(ds_id):
                if n >= args.max_per:
                    break
                if min(img.size) < args.min_side:
                    continue
                h = dhash(img)
                if any(hamming(h, eh) <= 4 for eh in hashes):
                    continue
                sha = key.replace("/", "_").replace(":", "_").replace(".", "_")[:50]
                fname = f"hf_{ds_id.split('/')[-1]}_{sha}.jpg"
                img.save(IMG_DIR / fname, "JPEG", quality=90)
                hashes.append(h)
                manifest.append({
                    "file": fname, "source": "huggingface", "dataset": ds_id,
                    "key": key, "width": img.size[0], "height": img.size[1],
                    "dhash": h, "downloaded_at": datetime.now(timezone.utc).isoformat(),
                    "pred_viewpoint": None,
                })
                n += 1
        except Exception as exc:
            logger.warning(f"  {ds_id} gagal: {str(exc)[:120]}")
        logger.info(f"  tersimpan: {n}")
        total += n
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== Harvest HuggingFace ===\n  tersimpan: {total} | manifest: {len(manifest)}\n  -> {IMG_DIR}")


if __name__ == "__main__":
    main()
