# -*- coding: utf-8 -*-
"""Perkaya dataset: impor kelas Figaro yang belum dipakai + dataset bald Apache-2.0.

Sumber 1 (GRATIS, dari zip yang sudah ada): Figaro-1k frame 601-1050
  - short-men  (901-1050) -> rambut pendek pria  -> kelas "pendek"
  - braids     (601-750)  -> variasi gaya        -> kelas "pendek-menengah" (kepang menempel)
  - dreadlocks (751-900)  -> variasi gaya        -> kelas "pendek-menengah"

Sumber 2 (Apache-2.0): ideepankarsharma2003/kaggle-bald-dataset
  - kelas bald/notbald -> ambil subset "bald" -> kelas "pendek"

Output: apps/api/cv/dataset/extra/<kelas_panjang>/<sumber>_<id>.jpg
        + apps/api/cv/dataset/extra/_manifest.csv

Jalankan (Python global: pyarrow + PIL):
  $env:PYTHONIOENCODING='utf-8'
  python apps\\api\\cv\\scripts\\enrich_dataset.py --figaro-extra --max-per-group 150
  python apps\\api\\cv\\scripts\\enrich_dataset.py --bald --max-bald 300
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ZIP_PATH = BASE / "dataset" / "figaro-1k.zip"
EXTRA = BASE / "dataset" / "extra"
MANIFEST = EXTRA / "_manifest.csv"

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]

# Figaro kelas tambahan -> kelas panjang (heuristik konservatif)
FIGARO_EXTRA_GROUPS = [
    ("short-men", 901, 1050, "pendek"),
    ("braids", 601, 750, "pendek-menengah"),
    ("dreadlocks", 751, 900, "pendek-menengah"),
]

BALD_PARQUET = [
    "https://huggingface.co/datasets/ideepankarsharma2003/kaggle-bald-dataset/resolve/main/data/train-00000-of-00002.parquet",
    "https://huggingface.co/datasets/ideepankarsharma2003/kaggle-bald-dataset/resolve/main/data/train-00001-of-00002.parquet",
]


def ensure_dirs() -> None:
    for c in LENGTH_CLASSES:
        (EXTRA / c).mkdir(parents=True, exist_ok=True)


def append_manifest(rows: list[dict]) -> None:
    exists = MANIFEST.exists()
    with MANIFEST.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "kelas_panjang", "sumber", "asal"])
        if not exists:
            w.writeheader()
        w.writerows(rows)


def import_figaro(max_per_group: int) -> None:
    ensure_dirs()
    z = zipfile.ZipFile(ZIP_PATH)
    names = z.namelist()
    rows = []
    for group, lo, hi, kelas in FIGARO_EXTRA_GROUPS:
        count = 0
        for frame in range(lo, hi + 1):
            if count >= max_per_group:
                break
            cands = [n for n in names if f"Frame{frame:05d}-org.jpg" in n]
            if not cands:
                continue
            data = z.read(cands[0])
            out = EXTRA / kelas / f"figaro_{group}_{frame:05d}.jpg"
            out.write_bytes(data)
            rows.append({"file": str(out.relative_to(BASE)).replace("\\", "/"), "kelas_panjang": kelas, "sumber": "figaro-extra", "asal": group})
            count += 1
        print(f"  {group} -> {kelas}: {count} citra")
    z.close()
    append_manifest(rows)
    print(f"ditambahkan {len(rows)} citra Figaro tambahan")


def import_bald(max_bald: int) -> None:
    ensure_dirs()
    try:
        import pyarrow.parquet as pq
    except Exception as exc:
        raise SystemExit(f"pyarrow tidak tersedia: {exc}") from exc

    rows = []
    got = 0
    for url in BALD_PARQUET:
        if got >= max_bald:
            break
        tmp = EXTRA / "_tmp.parquet"
        print(f"  unduh {url.split('/')[-1]} ...")
        try:
            urllib.request.urlretrieve(url, tmp)
        except Exception as exc:
            print(f"  GAGAL unduh: {exc}")
            continue
        pf = pq.ParquetFile(tmp)
        cols = pf.schema_arrow.names
        img_col = "image" if "image" in cols else cols[0]
        lbl_col = "label" if "label" in cols else (cols[1] if len(cols) > 1 else None)
        for batch in pf.iter_batches(batch_size=64):
            d = batch.to_pydict()
            imgs = d[img_col]
            lbls = d[lbl_col] if lbl_col else [None] * len(imgs)
            for img, lbl in zip(imgs, lbls, strict=False):
                if got >= max_bald:
                    break
                # dataset ini label 0/1 (bald/not) — ambil yang positif saja
                lbl_s = str(lbl).lower()
                if lbl_col and not any(k in lbl_s for k in ("1", "bald", "true")):
                    continue
                raw = img.get("bytes") if isinstance(img, dict) else img
                if not raw:
                    continue
                out = EXTRA / "pendek" / f"bald_{got:05d}.jpg"
                out.write_bytes(raw)
                rows.append({"file": str(out.relative_to(BASE)).replace("\\", "/"), "kelas_panjang": "pendek", "sumber": "kaggle-bald", "asal": "bald"})
                got += 1
        del pf  # lepas handle file sebelum unlink (Windows)
        tmp.unlink(missing_ok=True)
    append_manifest(rows)
    print(f"ditambahkan {len(rows)} citra bald -> kelas pendek")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figaro-extra", action="store_true")
    ap.add_argument("--bald", action="store_true")
    ap.add_argument("--max-per-group", type=int, default=150)
    ap.add_argument("--max-bald", type=int, default=300)
    args = ap.parse_args()

    if not args.figaro_extra and not args.bald:
        ap.error("pilih minimal satu: --figaro-extra atau --bald")

    if args.figaro_extra:
        print("Impor kelas Figaro tambahan...")
        import_figaro(args.max_per_group)
    if args.bald:
        print("Impor dataset bald...")
        import_bald(args.max_bald)

    # ringkasan
    print("\n=== Ringkasan dataset extra ===")
    for c in LENGTH_CLASSES:
        n = len(list((EXTRA / c).glob("*.jpg")))
        print(f"  {c:16s} {n} citra")


if __name__ == "__main__":
    main()
