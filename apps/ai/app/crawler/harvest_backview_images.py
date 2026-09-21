# -*- coding: utf-8 -*-
"""Harvest foto BACK-VIEW dari Wikimedia Commons (lisensi bebas/CC).

Tujuan: memperkaya dataset viewpoint (khusus kelas "belakang") dari sumber
legal (Wikimedia Commons API, bukan scraping kasar).

Alur:
  1. Query Wikimedia Commons API per kategori/pencarian (mis. "hairstyle back",
     "long hair", "back of head").
  2. Ambil URL file gambar (via API, hormati lisensi).
  3. Download dengan rate-limit + User-Agent jelas.
  4. Filter: resolusi >= min, format valid, dedup (dHash).
  5. (Opsional) Label otomatis via gate heuristik.

Output:
  apps/ai/app/crawler/harvest/back_view/*.jpg
  apps/ai/app/crawler/harvest/_manifest.json
  apps/ai/app/crawler/harvest/_download.log

Usage (dari apps/ai):
  & ".venv\\Scripts\\python.exe" -m app.crawler.harvest_backview_images --help
  & ".venv\\Scripts\\python.exe" -m app.crawler.harvest_backview_images --max 30
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image
import io

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("harvest")

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "harvest"
IMG_DIR = OUT_DIR / "back_view"
MANIFEST = OUT_DIR / "_manifest.json"
LOG = OUT_DIR / "_download.log"

# Wikimedia Commons API
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia mewajibkan User-Agent deskriptif + kontak (kebijakan UA Wikimedia).
USER_AGENT = "RAGSalonCVResearch/1.0 (academic hair-classification research; https://github.com/matinrusydan/multimodal-rag-mobilenetv2-salon)"
UA_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}

# Query kategori/pencarian terkait rambut dari belakang
SEARCH_TERMS = [
    "hairstyle back",
    "hair back view",
    "long hair back",
    "braid back",
    "ponytail back",
    "hair bun back",
    "back of head hair",
]

MIN_SIDE = 224
DELAY = 1.0  # detik antar request (hormati server)


def api_get(client: httpx.Client, params: dict) -> dict:
    params = {**params, "format": "json"}
    r = client.get(COMMONS_API, params=params, headers=UA_HEADERS)
    r.raise_for_status()
    return r.json()


def search_images(client: httpx.Client, term: str, limit: int) -> list[dict]:
    """Cari file gambar di Commons untuk satu term."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{term} filetype:bitmap",
        "gsrnamespace": "6",          # namespace File
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata|mime",
        "iiurlwidth": "800",
    }
    data = api_get(client, params)
    pages = (data.get("query") or {}).get("pages") or {}
    out = []
    for _, page in pages.items():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "unknown")
        artist = (meta.get("Artist") or {}).get("value", "")
        if isinstance(artist, str) and "<" in artist:
            # strip html kasar
            import re
            artist = re.sub(r"<[^>]+>", "", artist)
        out.append({
            "title": page.get("title"),
            "url": url,
            "width": info.get("width"),
            "height": info.get("height"),
            "mime": info.get("mime"),
            "license": lic,
            "artist": artist.strip()[:120],
            "page": page.get("title"),
        })
    return out


def dhash(img: Image.Image, size: int = 8) -> str:
    g = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    import numpy as np
    arr = np.asarray(g, dtype=int)
    diff = arr[:, 1:] > arr[:, :-1]
    return "".join("1" if b else "0" for b in diff.flatten())


def hamming(a: str, b: str) -> int:
    return sum(c1 != c2 for c1, c2 in zip(a, b))


def main():
    ap = argparse.ArgumentParser(description="Harvest back-view images dari Wikimedia Commons.")
    ap.add_argument("--max", type=int, default=30, help="Maks gambar per term (default 30)")
    ap.add_argument("--terms", nargs="*", default=SEARCH_TERMS)
    ap.add_argument("--min-side", type=int, default=MIN_SIDE)
    ap.add_argument("--delay", type=float, default=DELAY)
    ap.add_argument("--no-dedup", action="store_true")
    args = ap.parse_args()

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # muat manifest lama (resume)
    manifest = []
    existing_hashes = []
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            existing_hashes = [m.get("dhash") for m in manifest if m.get("dhash")]
        except Exception:
            manifest = []

    log_lines = []
    n_ok = n_skip = n_dup = n_err = 0

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for term in args.terms:
            logger.info(f"[search] {term}")
            try:
                candidates = search_images(client, term, args.max)
            except Exception as exc:
                logger.warning(f"  gagal search: {exc}")
                continue
            logger.info(f"  kandidat: {len(candidates)}")

            for c in candidates:
                url = c["url"]
                try:
                    time.sleep(args.delay)
                    r = client.get(url, headers=UA_HEADERS)
                    r.raise_for_status()
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                except Exception as exc:
                    n_err += 1
                    log_lines.append(f"ERR {url}: {exc}")
                    continue

                if min(img.size) < args.min_side:
                    n_skip += 1
                    continue

                # dedup
                if not args.no_dedup:
                    h = dhash(img)
                    if any(hamming(h, eh) <= 4 for eh in existing_hashes):
                        n_dup += 1
                        continue

                # simpan
                sha = hashlib.md5(url.encode()).hexdigest()[:10]
                fname = f"wikimedia_{sha}.jpg"
                img.save(IMG_DIR / fname, "JPEG", quality=90)
                existing_hashes.append(h)
                manifest.append({
                    "file": fname,
                    "source": "wikimedia_commons",
                    "term": term,
                    "title": c.get("title"),
                    "url": url,
                    "license": c.get("license"),
                    "artist": c.get("artist"),
                    "width": img.size[0],
                    "height": img.size[1],
                    "dhash": h,
                    "downloaded_at": datetime.now(timezone.utc).isoformat(),
                    "pred_viewpoint": None,   # diisi tahap gate (opsional)
                })
                n_ok += 1
                if n_ok % 10 == 0:
                    logger.info(f"  tersimpan: {n_ok}")
                    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "_download.log").write_text("\n".join(log_lines), encoding="utf-8")

    print("\n=== Hasil Harvest Wikimedia ===")
    print(f"  tersimpan : {n_ok}")
    print(f"  dilewati (kecil): {n_skip}")
    print(f"  duplikat  : {n_dup}")
    print(f"  error     : {n_err}")
    print(f"  total manifest: {len(manifest)}")
    print(f"\nGambar -> {IMG_DIR}")
    print(f"Manifest -> {MANIFEST}")


if __name__ == "__main__":
    main()
