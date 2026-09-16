"""Live web fallback for the RAG pipeline.

Saat query bertopik kesehatan rambut (rambut rontok, kebotakan, ketombe, dll.)
dan knowledge base lokal tidak menjawab, sistem melakukan live-crawl
alodokter.com via Crawl4AI (stealth mode) lalu menjawab dari konten hasil crawl.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Optional

from app.config import settings
from app.crawler.stealth import crawl_url_sync, resolve_alodokter_slug
from app.rag.retriever import RetrievedDoc

logger = logging.getLogger(__name__)

ALODOKTER_BASE = "https://www.alodokter.com"

# Cache hasil crawl per-URL (TTL detik) — hindari buka browser berulang.
_CRAWL_CACHE: dict[str, tuple[float, str]] = {}
_CACHE_TTL = float(os.getenv("WEB_CACHE_TTL_SECONDS", "3600"))  # 1 jam


def _crawl_target(query: str) -> str:
    """Pilih URL artikel alodokter berdasar query."""
    slug = resolve_alodokter_slug(query)
    return f"{ALODOKTER_BASE}/{slug}"


def _cache_get(url: str) -> Optional[str]:
    entry = _CRAWL_CACHE.get(url)
    if entry is None:
        return None
    expires_at, md = entry
    if time.monotonic() >= expires_at:
        _CRAWL_CACHE.pop(url, None)
        return None
    return md


def _cache_put(url: str, md: str) -> None:
    _CRAWL_CACHE[url] = (time.monotonic() + _CACHE_TTL, md)


def slug_of(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).path.strip("/") or "alodokter"


def _clean_markdown(raw: str) -> str:
    """Bersihkan markdown hasil crawl agar siap dipakai LLM & ditampilkan.

    - Hapus baris navigasi/link menu berlebih ([ Pengertian ](...), ![...](...))
    - Hapus URL mentah di markdown link, sisakan teks
    - Rapikan whitespace
    """
    # Hapus image markdown ![alt](url)
    raw = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", raw)
    # Ubah [text](url) -> text
    raw = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", raw)
    # Hapus baris yang hanya berisi kata menu navigasi (Pengertian, Penyebab, dll.)
    nav_words = r"(?:Pengertian|Penyebab|Gejala|Pengobatan|Komplikasi|Pencegahan|Diagnosis)"
    raw = re.sub(rf"(?m)^\s*{nav_words}(?:\s+{nav_words})*\s*$", "", raw)
    # Hapus baris "Artikel Terkait" / "Dokter Terkait" dan setelahnya
    raw = re.sub(r"(?ms)^Artikel Terkait.*$", "", raw)
    raw = re.sub(r"(?ms)^## Dokter Terkait.*$", "", raw)
    # Hapus baris "Terakhir diperbarui: ..."
    raw = re.sub(r"(?m)^Terakhir diperbarui:.*$", "", raw)
    # Hapus baris "Chat Bersama Dokter" promo
    raw = re.sub(r"(?m)^.*Chat Bersama Dokter.*$", "", raw)
    # Hapus baris "Booking" promo link
    raw = re.sub(r"(?m)^.*booking.*$", "", raw, flags=re.IGNORECASE)
    # Rapikan whitespace
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
    return raw


def _short_summary(md: str, max_chars: int = 200) -> str:
    """Ambil kalimat pertama yang substantif sebagai ringkasan singkat."""
    lines = md.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if len(stripped) < 40:
            continue
        clean = " ".join(stripped.split())
        return clean[:max_chars] + ("…" if len(clean) > max_chars else "")
    return " ".join(md.split())[:max_chars] + "…"


def _chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """Potong teks panjang jadi beberapa chunk ~max_chars (overlap kecil)."""
    chunks: list[str] = []
    step = max_chars
    i = 0
    while i < len(text):
        chunks.append(text[i : i + step])
        i += step - 100  # overlap 100
    return chunks or [text]


async def live_crawl_docs(
    query: str,
    *,
    max_pages: int = 3,
    delay: float = 0.5,
) -> tuple[list[RetrievedDoc], list[dict]]:
    """Crawl halaman alodokter relevan dan kembalikan dokumen + sources.

    Hasil crawl di-cache per-URL (TTL) agar request berikutnya instan.

    Returns:
        (docs, sources) — docs untuk prompt Gemini (panjang), sources ringkas
        untuk API ({"file", "url", "snippet"} unik per URL).
    """
    target = _crawl_target(query)
    slug = slug_of(target)

    md = _cache_get(target)
    if md is not None:
        logger.info("live web fallback: CACHE HIT %s (query=%r)", target, query)
    else:
        logger.info("live web fallback: crawl %s (query=%r)", target, query)
        # Run in a worker thread so a fresh Proactor loop spawns the browser.
        md, err = await asyncio.to_thread(crawl_url_sync, target, delay=delay)
        if md is None:
            logger.warning("live crawl gagal %s: %s", target, err)
            return [], []
        _cache_put(target, md)

    # Bersihkan markdown untuk prompt (full konten) dan untuk ringkasan source.
    clean_md = _clean_markdown(md)

    docs: list[RetrievedDoc] = []
    # Batasi jumlah chunk yang dipakai (prompt lebih kecil → LLM lebih cepat).
    max_chunks = max(1, max_pages)
    for chunk in _chunk_text(clean_md, max_chars=2500)[:max_chunks]:
        docs.append(
            RetrievedDoc(
                file=f"web:{slug}",
                section="web",
                snippet=chunk,
                distance=None,
            )
        )

    # SATU source unik per URL — file tetap "web:{slug}" tapi frontend pakai
    # key kombinasi file+index agar tidak ganda.
    sources = [
        {
            "file": f"web:{slug}",
            "url": target,
            "snippet": _short_summary(clean_md, max_chars=180),
        }
    ]
    return docs, sources


async def answer_from_web(
    query: str,
    top_k: int = 2,
) -> tuple[str, list[dict]]:
    """Jawaban cepat dari hasil crawl web (tanpa ChromaDB)."""
    docs, sources = await live_crawl_docs(query)
    if not docs:
        return (
            "Maaf, kami tidak dapat mengambil informasi dari sumber web saat ini. "
            "Silakan konsultasi langsung ke salon TIEN SALON.",
            [],
        )

    lines = []
    for i, d in enumerate(docs[:top_k], start=1):
        snippet = " ".join((d.snippet or "").split())[:260]
        lines.append(f"{i}. {snippet}")
    reply = (
        "Berdasarkan artikel kesehatan yang kami ambil langsung dari Alodokter"
        " (alodokter.com), berikut informasinya:\n\n" + "\n".join(lines)
    )
    return reply, sources