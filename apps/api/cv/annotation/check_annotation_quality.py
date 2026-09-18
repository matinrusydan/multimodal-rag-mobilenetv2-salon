# -*- coding: utf-8 -*-
"""QC (Quality Control) untuk file anotasi — deteksi record tidak lengkap/tidak konsisten.

Tidak mengubah file anotasi. Hanya melaporkan masalah agar annotator bisa memperbaiki.

Cek yang dilakukan:
  1. Record tidak lengkap (hair_type kosong tanpa ungradable; ungradable tanpa alasan;
     non-ungradable tanpa nilai kondisional)
  2. Distribusi hair_type / viewpoint / confidence
  3. Jumlah ungradable + alasan
  4. Distribusi atribut kondisional per jenis
  5. Duplikat image_id
  6. image_id di luar manifest (jika manifest tersedia)

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" annotation\\check_annotation_quality.py --annotator A
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
GT_DIR = BASE / "annotation" / "ground_truth"
MANIFEST_PATH = GT_DIR / "pilot_manifest.json"


def is_incomplete(rec: dict) -> tuple[bool, str]:
    ht = rec.get("hair_type", "")
    ungradable = rec.get("ungradable", False)
    reason = rec.get("ungradable_reason")
    cond_value = (rec.get("conditional_attribute") or {}).get("value")

    if not ht and not ungradable:
        return True, "hair_type kosong tanpa ungradable"
    if ungradable and not reason:
        return True, "ungradable tanpa alasan"
    if not ungradable and ht and not cond_value:
        return True, "nilai kondisional kosong (tidak ungradable)"
    return False, ""


def main() -> None:
    ap = argparse.ArgumentParser(description="QC file anotasi (read-only).")
    ap.add_argument("--annotator", default="A", help="Annotator id (default: A)")
    args = ap.parse_args()

    path = GT_DIR / f"annotator_{args.annotator}.json"
    if not path.exists():
        print(f"ERROR: File anotasi tidak ditemukan: {path}")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"=== QC Anotasi: {path.name} ===")
    print(f"Total record: {len(data)}")

    # Duplikat
    ids = [r.get("image_id") for r in data]
    dups = [k for k, v in Counter(ids).items() if v > 1]
    if dups:
        print(f"[MASALAH] Duplikat image_id: {dups}")

    # Manifest cross-check
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        expected = {i["image_id"] for i in manifest["images"]}
        actual = set(ids)
        missing = expected - actual
        extra = actual - expected
        if missing:
            print(f"[INFO] Belum dianotasi: {len(missing)} image")
        if extra:
            print(f"[MASALAH] image_id di luar manifest: {sorted(extra)}")

    # Distribusi
    print(f"\nDistribusi hair_type: {dict(Counter(r.get('hair_type','') or '(kosong)' for r in data))}")
    print(f"Distribusi viewpoint: {dict(Counter(r.get('viewpoint','') for r in data))}")
    print(f"Distribusi confidence: {dict(Counter(r.get('confidence','') for r in data))}")

    n_ug = sum(1 for r in data if r.get("ungradable"))
    print(f"\nUngradable: {n_ug}/{len(data)}")
    print(f"  Alasan: {dict(Counter(r.get('ungradable_reason') or '(kosong)' for r in data if r.get('ungradable')))}")

    # Distribusi kondisional per jenis
    print("\nAtribut kondisional per jenis:")
    by_type = {}
    for r in data:
        if r.get("ungradable"):
            continue
        ht = r.get("hair_type", "")
        val = (r.get("conditional_attribute") or {}).get("value")
        by_type.setdefault(ht, Counter())[val or "(kosong)"] += 1
    for ht, dist in sorted(by_type.items()):
        print(f"  {ht or '(kosong)':8s}: {dict(dist)}")

    # Record tidak lengkap
    incomplete = []
    for r in data:
        bad, msg = is_incomplete(r)
        if bad:
            incomplete.append((r["image_id"], msg))
    print(f"\n=== Record tidak lengkap: {len(incomplete)} ===")
    for iid, msg in incomplete:
        print(f"  {iid:40s} -> {msg}")

    # Ringkasan status
    print("\n=== STATUS ===")
    if not incomplete and not dups:
        print("BERSIH: semua record lengkap.")
    else:
        print(f"PERLU DIPERBAIKI: {len(incomplete)} record tidak lengkap.")
        print("Buka tool anotasi lagi — akan otomatis ke record tidak lengkap.")


if __name__ == "__main__":
    main()
