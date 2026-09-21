# -*- coding: utf-8 -*-
"""viewpoint/apply_clean.py — Terapkan hasil anotasi KEEP/BUANG.

Membaca clean_annotation_<annotator>.json lalu menyalin gambar dengan
keputusan "keep" ke folder dataset bersih. Gambar asli TIDAK dihapus.

Output: apps/ai/app/crawler/harvest/manual_clean/

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\apply_clean.py --annotator A
  & ".venv\\Scripts\\python.exe" viewpoint\\apply_clean.py --annotators A B  # gabung
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground_truth"
HARVEST = HERE.parents[2] / "ai" / "app" / "crawler" / "harvest"
OUT_DIR = HARVEST / "manual_clean"


def main():
    ap = argparse.ArgumentParser(description="Terapkan anotasi cleaning (KEEP -> folder bersih).")
    ap.add_argument("--annotators", nargs="*", default=["A"])
    args = ap.parse_args()

    keep, delete = {}, {}
    for a in args.annotators:
        p = GT_DIR / f"clean_annotation_{a}.json"
        if not p.exists():
            print(f"WARN: {p.name} tidak ada"); continue
        recs = json.loads(p.read_text(encoding="utf-8")).get("records", {})
        for path, rec in recs.items():
            if rec["decision"] == "keep":
                keep[path] = rec
            else:
                delete[path] = rec

    if not keep and not delete:
        print("ERROR: tidak ada anotasi. Jalankan clean_annotation.py dulu.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_ok = n_miss = 0
    manifest = []
    for path, rec in keep.items():
        src = Path(path)
        if not src.exists():
            n_miss += 1; continue
        dst = OUT_DIR / src.name
        # hindari tabrakan nama
        if dst.exists() and dst.stat().st_size != src.stat().st_size:
            dst = OUT_DIR / f"{src.stem}_{rec.get('source','')}{src.suffix}"
        try:
            shutil.copy2(src, dst)
            manifest.append({"file": dst.name, "source": rec.get("source"), "orig": path})
            n_ok += 1
        except Exception:
            n_miss += 1

    (OUT_DIR / "_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("=== Terapkan Cleaning ===")
    print(f"  KEEP  : {len(keep)} (disalin: {n_ok}, gagal: {n_miss})")
    print(f"  BUANG : {len(delete)}")
    print(f"  per sumber (keep): {dict(Counter(r.get('source') for r in keep.values()))}")
    print(f"  -> {OUT_DIR}")


if __name__ == "__main__":
    main()
