# -*- coding: utf-8 -*-
"""Impor FaceSketches-HairStyle40 (Apache-2.0) -> dataset panjang rambut.

Sumber: yikaiwang/FaceSketches-HairStyle40 (Hairstyle30k subset)
Setiap citra di image/<StyleName>/*.jpg. Nama gaya memetakan ke kelas panjang
rambut salon secara eksplisit, mis. Bald/CrewCut -> pendek, WaistLenHair -> panjang.

Output: apps/api/cv/dataset/extra/<kelas>/hs40_<style>_<n>.jpg + manifest.

Jalankan (Python global: tanpa dependensi khusus selain stdlib):
  $env:PYTHONIOENCODING='utf-8'
  python apps\\api\\cv\\scripts\\import_hairstyle40.py --max-per-style 30
"""

from __future__ import annotations

import argparse
import csv
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
EXTRA = BASE / "dataset" / "extra"
MANIFEST = EXTRA / "_manifest.csv"
ZIP_URL = "https://huggingface.co/datasets/yikaiwang/FaceSketches-HairStyle40/resolve/main/FaceSketches-HairStyle40.zip"
CACHE = BASE / "dataset" / "_hairstyle40.zip"

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]

# Mapping gaya -> kelas panjang (berbasis definisi panjang referensi gaya).
# Sumber: klasifikasi panjang konvensional (bald/pixie=pendek, bob=pendek-menengah,
# shoulder/layered=menengah, waist/ponytail panjang=panjang).
STYLE_TO_LENGTH = {
    # pendek
    "Bald": "pendek",
    "CrewCut": "pendek",
    "PixieCut": "pendek",
    "BowlCut": "pendek",
    "Flattop": "pendek",
    "Crop": "pendek",
    "HorseShoeFlattop": "pendek",
    "HiTopFade": "pendek",
    "Fauxhawk": "pendek",
    "LibertySpikes": "pendek",
    "SpikyHair": "pendek",
    "Mohawk": "pendek",
    "UndercutCurly": "pendek",
    "UndercutSlickback": "pendek",
    "UndercutPompadour": "pendek",
    "undercutSidepart": "pendek",
    "CombOver": "pendek",
    "RazorCut": "pendek",
    # pendek-menengah
    "BobHair": "pendek-menengah",
    "MopTop": "pendek-menengah",
    "Mullet": "pendek-menengah",
    "EmoHair": "pendek-menengah",
    "shag": "pendek-menengah",
    "Perm": "pendek-menengah",
    "Afro": "pendek-menengah",
    "CornRows": "pendek-menengah",
    "DreadLocks": "pendek-menengah",
    # menengah
    "MedLenHair": "menengah",
    "ShoulderLenHair": "menengah",
    "LayeredHair": "menengah",
    "UndercutLong": "menengah",
    "WaveHair": "menengah",
    # panjang
    "WaistLenHair": "panjang",
    "PonyTail": "panjang",
    "Ringlet": "panjang",
    "HimeCut": "panjang",
    "Bun": "panjang",
    "Odango": "panjang",
    "FrenchTwist": "panjang",
    "CurtainedHair": "panjang",
}


def ensure_dirs() -> None:
    for c in LENGTH_CLASSES:
        (EXTRA / c).mkdir(parents=True, exist_ok=True)


def download() -> None:
    if CACHE.exists() and CACHE.stat().st_size > 1_000_000:
        print(f"  pakai cache: {CACHE.name} ({CACHE.stat().st_size/1e6:.1f} MB)")
        return
    print(f"  unduh {ZIP_URL.split('/')[-1]} (~223 MB)...")
    urllib.request.urlretrieve(ZIP_URL, CACHE)
    print(f"  selesai: {CACHE.stat().st_size/1e6:.1f} MB")


def style_of(name: str) -> str | None:
    # FaceSketches-HairStyle40/image/<Style>/<file>.jpg
    parts = name.split("/")
    if len(parts) >= 4 and parts[0] == "FaceSketches-HairStyle40" and parts[1] == "image":
        return parts[2]
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-style", type=int, default=30)
    args = ap.parse_args()

    ensure_dirs()
    download()

    z = zipfile.ZipFile(CACHE)
    rows = []
    per_style: dict[str, int] = {}
    unmapped = set()
    for info in z.infolist():
        if info.is_dir():
            continue
        style = style_of(info.filename)
        if not style:
            continue
        kelas = STYLE_TO_LENGTH.get(style)
        if not kelas:
            unmapped.add(style)
            continue
        if per_style.get(style, 0) >= args.max_per_style:
            continue
        data = z.read(info.filename)
        n = per_style.get(style, 0)
        out = EXTRA / kelas / f"hs40_{style}_{n:02d}.jpg"
        out.write_bytes(data)
        rows.append({"file": str(out.relative_to(BASE)).replace("\\", "/"), "kelas_panjang": kelas, "sumber": "hairstyle40", "asal": style})
        per_style[style] = n + 1
    z.close()

    exists = MANIFEST.exists()
    with MANIFEST.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "kelas_panjang", "sumber", "asal"])
        if not exists:
            w.writeheader()
        w.writerows(rows)

    print(f"\nDitambahkan {len(rows)} citra FaceSketches-HairStyle40")
    if unmapped:
        print(f"  gaya tak terpetakan (dilewati): {sorted(unmapped)}")
    # distribusi
    import collections

    cc = collections.Counter(r["kelas_panjang"] for r in rows)
    for c in LENGTH_CLASSES:
        print(f"  {c:16s} {cc.get(c, 0)}")
    print("\n=== Total dataset extra ===")
    for c in LENGTH_CLASSES:
        n = len(list((EXTRA / c).glob("*.jpg")))
        print(f"  {c:16s} {n} citra")


if __name__ == "__main__":
    main()
