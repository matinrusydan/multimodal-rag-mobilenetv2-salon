# -*- coding: utf-8 -*-
"""Harvest gambar dari Openverse API (agregator konten CC, tanpa API key).

Tujuan: memperkaya dataset dari sumber legal (Flickr CC, Wikimedia, dll via
Openverse) TANPA kredensial.

Alur:
  1. Query Openverse /v1/images/ per term.
  2. Filter lisensi bebas (boleh dipakai; NC/ND disimpan tapi ditandai).
  3. Download (httpx, rate-limit), filter resolusi + dedup dHash.
  4. Manifest: url, license, creator, source, term.

Output:
  apps/ai/app/crawler/harvest/openverse/*.jpg
  apps/ai/app/crawler/harvest/_manifest_openverse.json

Usage (dari apps/ai):
  & ".venv\\Scripts\\python.exe" -m app.crawler.harvest_openverse --max 40
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("harvest_openverse")

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "harvest"
IMG_DIR = OUT_DIR / "openverse"
MANIFEST = OUT_DIR / "_manifest_openverse.json"

API = "https://api.openverse.org/v1/images/"
UA = {"User-Agent": "RAGSalonCVResearch/1.0 (academic hair research)"}

# Term luas — back-view + tekstur + variasi sudut
SEARCH_TERMS = [
    "hair back view", "hair from behind", "hairstyle back", "braid back",
    "ponytail back", "hair bun back", "long hair back", "curly hair back",
    "afro back", "hair texture", "hairstyle side", "hairstyle front",
    "hair portrait", "woman hair", "man hair", "blonde hair back",
    "black hair back", "wavy hair", "straight hair", "hair braid",
    "hair updo back", "hijab hair", "hair roots scalp",
    # tambahan (margin 1000+)
    "african hair", "asian hair", "kinky hair", "coily hair", "curly afro",
    "hair back profile", "woman from behind", "girl hair back", "bun updo",
    "french braid", "dutch braid", "fishtail braid", "hair ribbons",
    "red hair back", "brown hair back", "short hair back", "medium hair",
    "waist length hair", "shoulder length hair", "pixie cut back",
    "hair salon", "haircut", "hair styling", "barber",
    # FOKUS WANITA (menyeimbangkan gender; sudah divalidasi ada hasil di Openverse)
    "woman hair back", "female hairstyle back", "women long hair back",
    "girl hair back view", "female braid back", "women back of head hair",
    "female long hair from behind", "woman ponytail back",
]

MIN_SIDE = 224


def dhash(img: Image.Image, size: int = 8) -> str:
    g = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    arr = np.asarray(g, dtype=int)
    diff = arr[:, 1:] > arr[:, :-1]
    return "".join("1" if b else "0" for b in diff.flatten())


def hamming(a: str, b: str) -> int:
    return sum(c1 != c2 for c1, c2 in zip(a, b))


def main():
    ap = argparse.ArgumentParser(description="Harvest dari Openverse API.")
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
    with httpx.Client(timeout=30, follow_redirects=True, headers=UA) as client:
        for term in args.terms:
            logger.info(f"[openverse] {term}")
            # Openverse: max page_size=20; ambil 2 halaman
            got = 0
            for page in (1, 2):
                try:
                    r = client.get(API, params={"q": term, "page_size": 20, "page": page})
                    r.raise_for_status()
                    results = r.json().get("results", [])
                except Exception as exc:
                    logger.warning(f"  query gagal: {exc}")
                    break
                if not results:
                    break
                for it in results:
                    if got >= args.max:
                        break
                    url = it.get("url")
                    if not url:
                        continue
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
                    fname = f"openverse_{sha}.jpg"
                    img.save(IMG_DIR / fname, "JPEG", quality=90)
                    hashes.append(h)
                    manifest.append({
                        "file": fname, "source": "openverse", "term": term,
                        "title": it.get("title"), "url": url,
                        "license": f"{it.get('license')} {it.get('license_version')}",
                        "creator": it.get("creator"),
                        "provider": it.get("source"),
                        "width": img.size[0], "height": img.size[1],
                        "dhash": h,
                        "downloaded_at": datetime.now(timezone.utc).isoformat(),
                        "pred_viewpoint": None,
                    })
                    n_ok += 1
            logger.info(f"  total tersimpan: {n_ok}")
            MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== Harvest Openverse ===")
    print(f"  tersimpan: {n_ok} | kecil: {n_skip} | duplikat: {n_dup} | error: {n_err}")
    print(f"  manifest total: {len(manifest)}")
    print(f"  -> {IMG_DIR}")


if __name__ == "__main__":
    main()
