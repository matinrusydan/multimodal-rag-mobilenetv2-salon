# -*- coding: utf-8 -*-
"""harvest_all.py — Orkestrasi harvest multi-sumber (target 1000+).

Menjalankan berurutan:
  1. Wikimedia Commons (back-view rambut)
  2. Openverse API (agregator CC)
  3. HuggingFace Hub (dataset hair)

Semua gambar masuk ke harvest/<sumber>/ + manifest masing-masing.

Usage (dari apps/ai):
  & ".venv\\Scripts\\python.exe" -m app.crawler.harvest_all
  & ".venv\\Scripts\\python.exe" -m app.crawler.harvest_all --max-openverse 60
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARVEST = HERE / "harvest"


def count(d: str) -> int:
    p = HARVEST / d
    return len(list(p.glob("*.jpg"))) + len(list(p.glob("*.png"))) if p.exists() else 0


def run(mod: str, args: list[str]) -> bool:
    cmd = [sys.executable, "-m", f"app.crawler.{mod}", *args]
    print(f"\n>>> {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=str(HERE.parents[1]))
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description="Harvest multi-sumber (Wikimedia+Openverse+HF).")
    ap.add_argument("--max-openverse", type=int, default=40)
    ap.add_argument("--max-wikimedia", type=int, default=40)
    ap.add_argument("--max-hf", type=int, default=200)
    ap.add_argument("--skip", nargs="*", default=[], help="Sumber yang dilewati (openverse/wikimedia/huggingface)")
    args = ap.parse_args()

    print("=== HARVEST ALL (Wikimedia + Openverse + HuggingFace) ===")
    if "wikimedia" not in args.skip:
        run("harvest_backview_images", ["--max", str(args.max_wikimedia), "--delay", "0.6"])
    if "openverse" not in args.skip:
        run("harvest_openverse", ["--max", str(args.max_openverse), "--delay", "0.4"])
    if "huggingface" not in args.skip:
        run("harvest_huggingface", ["--max-per", str(args.max_hf)])

    print("\n=== RINGKASAN ===")
    total = 0
    for d in ["back_view", "openverse", "huggingface"]:
        n = count(d)
        total += n
        print(f"  {d:14s}: {n}")
    print(f"  {'TOTAL':14s}: {total}")


if __name__ == "__main__":
    main()
