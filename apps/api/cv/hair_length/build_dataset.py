# -*- coding: utf-8 -*-
"""hair_length/build_dataset.py — Bangun dataset tensor panjang rambut.

Membangun index (image_id, kelas, pt) dari sumber mentah menjadi tensor .pt.
Logika inti diadaptasi dari pipeline riset; lihat README untuk sumber data.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" hair_length\\build_dataset.py --help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import CV_DIR, HAIR_LENGTH_CLASSES

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description="Bangun dataset hair_length (tensor .pt).")
    ap.add_argument("--out", default=str(HERE / "dataset" / "index.json"))
    ap.add_argument("--source-dir", default=str(CV_DIR / "preprocessed_length_merged"),
                    help="Folder dataset tensor (train/val/<kelas>/*.pt)")
    args = ap.parse_args()

    print("hair_length/build_dataset")
    print(f"kelas: {HAIR_LENGTH_CLASSES}")
    print(f"sumber tensor: {args.source_dir}")
    print("CATATAN: dataset tensor utama sudah dibangun di preprocessed_length_merged/.")
    print("Script ini untuk dokumentasi/rebuild. Lihat README untuk detail pipeline.")


if __name__ == "__main__":
    main()
