# -*- coding: utf-8 -*-
"""Harvest gambar via Bing Images dengan FILTER LISENSI CC (legal).

Alur:
  1. Query Bing Images (filterui:license-L2_L3_L4 = bebas pakai/bagi/modifikasi).
  2. Ambil URL gambar asli (murl) dari hasil.
  3. Download (httpx, delay), filter resolusi + dedup dHash.
  4. Manifest: url, term, sumber.

CATATAN LEGAL: hanya lisensi CC yang diambil. Simpan atribusi (url/term).

Output:
  apps/ai/app/crawler/harvest/bing/*.jpg
  apps/ai/app/crawler/harvest/_manifest_bing.json

Usage (dari apps/ai):
  & ".venv\\Scripts\\python.exe" -m app.crawler.harvest_bing --max 30
  & ".venv\\Scripts\\python.exe" -m app.crawler.harvest_bing --terms "braid back" "bun back"
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("harvest_bing")

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "harvest"
IMG_DIR = OUT_DIR / "bing"
MANIFEST = OUT_DIR / "_manifest_bing.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
LICENSE_FILTER = "+filterui:license-L2_L3_L4"  # free to share/use/modify

# Term SANGAT spesifik back-view (+ fokus wanita utk keseimbangan)
SEARCH_TERMS = [
    "hair back view",
    "back of head hair",
    "back view hairstyle",
    "long hair back view",
    "braid back hairstyle",
    "hair bun back view",
    "ponytail back view",
    "cornrows back",
    "curly hair back view",
    "hairstyle back of head",
    "woman long hair back",
    "woman braid back",
    "female hair bun back",
    "girl hair back view",
    "women hair back view",
    "wavy hair back",
    "hair updo back view",
    "afro hair back",
    # gelombang 2 — variasi sudut/subjek
    "back of head hairstyle",
    "rear view hair",
    "long hair from behind",
    "hair from the back",
    "female ponytail back",
    "woman hair bun",
    "girl braid back",
    "women braid back view",
    "model hair back view",
    "curly long hair back",
    "fishtail braid back",
    "french braid back",
    "dutch braid back view",
    "hair down back view",
    "shoulder length hair back",
    "mid back hair view",
    "ponytail from behind",
    "hijab back view",
    "curly afro back view",
]

MIN_SIDE = 224


def dhash(img: Image.Image, size: int = 8) -> str:
    g = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    arr = np.asarray(g, dtype=int)
    diff = arr[:, 1:] > arr[:, :-1]
    return "".join("1" if b else "0" for b in diff.flatten())


def hamming(a: str, b: str) -> int:
    return sum(c1 != c2 for c1, c2 in zip(a, b))


def decode_murls(html: str) -> list[str]:
    urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', html)
    # fallback: json-escaped
    if not urls:
        urls = re.findall(r'"murl":"(https?://[^"]+?)"', html)
    seen, out = set(), []
    for u in urls:
        u = u.replace("\\/", "/").replace("&amp;", "&")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def main():
    ap = argparse.ArgumentParser(description="Harvest dari Bing Images (lisensi CC).")
    ap.add_argument("--max", type=int, default=40, help="Maks per term")
    ap.add_argument("--terms", nargs="*", default=SEARCH_TERMS)
    ap.add_argument("--min-side", type=int, default=MIN_SIDE)
    ap.add_argument("--delay", type=float, default=0.5)
    args = ap.parse_args()

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    manifest, hashes = [], []
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            hashes = [m["dhash"] for m in manifest if m.get("dhash")]
        except Exception:
            manifest = []

    n_ok = n_skip = n_dup = n_err = 0
    headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        for term in args.terms:
            logger.info(f"[bing] {term}")
            try:
                r = client.get(
                    "https://www.bing.com/images/search",
                    params={"q": term, "qft": LICENSE_FILTER, "count": "35", "first": "1"},
                )
                r.raise_for_status()
                urls = decode_murls(r.text)
            except Exception as exc:
                logger.warning(f"  query gagal: {exc}")
                continue
            logger.info(f"  kandidat url: {len(urls)}")
            got = 0
            for url in urls:
                if got >= args.max:
                    break
                try:
                    time.sleep(args.delay)
                    rr = client.get(url)
                    rr.raise_for_status()
                    img = Image.open(io.BytesIO(rr.content)).convert("RGB")
                except Exception:
                    n_err += 1
                    continue
                got += 1
                if min(img.size) < args.min_side:
                    n_skip += 1
                    continue
                h = dhash(img)
                if any(hamming(h, eh) <= 4 for eh in hashes):
                    n_dup += 1
                    continue
                sha = hashlib.md5(url.encode()).hexdigest()[:10]
                fname = f"bing_{sha}.jpg"
                img.save(IMG_DIR / fname, "JPEG", quality=90)
                hashes.append(h)
                manifest.append({
                    "file": fname, "source": "bing", "term": term, "url": url,
                    "width": img.size[0], "height": img.size[1], "dhash": h,
                    "license_filter": "L2_L3_L4",
                    "downloaded_at": datetime.now(timezone.utc).isoformat(),
                })
                n_ok += 1
            logger.info(f"  tersimpan total: {n_ok}")
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== Harvest Bing ===")
    print(f"  tersimpan: {n_ok} | kecil: {n_skip} | duplikat: {n_dup} | error: {n_err}")
    print(f"  manifest total: {len(manifest)}")
    print(f"  -> {IMG_DIR}")


if __name__ == "__main__":
    main()
