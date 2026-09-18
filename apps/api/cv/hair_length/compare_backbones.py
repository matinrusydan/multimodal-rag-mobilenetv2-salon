# -*- coding: utf-8 -*-
"""hair_length/compare_backbones.py — Validasi multi-seed backbone final.

Bandingkan efficientnet_v2_s vs convnext_tiny dengan beberapa seed pada
hold-out yang sama, untuk memastikan keunggulan bukan kebetulan.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" hair_length\\compare_backbones.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import HAIR_LENGTH_CLASSES

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"


def main():
    ap = argparse.ArgumentParser(description="Validasi multi-seed backbone hair_length.")
    ap.add_argument("--backbones", nargs="*", default=["efficientnet_v2_s", "convnext_tiny"])
    ap.add_argument("--seeds", nargs="*", type=int, default=[42, 7, 123])
    ap.add_argument("--out", default=str(REPORTS / "backbone_multiseed.json"))
    args = ap.parse_args()

    print("=== Validasi multi-seed backbone ===")
    print(f"backbones: {args.backbones} | seeds: {args.seeds}")
    print("Jalankan bench_backbones.py per-seed (--seed) untuk mengisi hasil.")
    print(f"(Hasil final: {REPORTS / 'backbone_final.json'} bila tersedia)")


if __name__ == "__main__":
    main()
