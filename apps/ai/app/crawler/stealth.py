"""Stealth crawler helpers — anti-bot bypass using UndetectedAdapter + stealth mode.

Provides:
- make_strategy(browser_config) → AsyncPlaywrightCrawlerStrategy with UndetectedAdapter
- crawl_url(url, ...) → raw markdown string or None
- build_headless() → resolves headless setting from env
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Optional

from app.config import settings
from app.crawler.antibot_detector import is_blocked

logger = logging.getLogger(__name__)


def _should_headless() -> bool:
    """Default: headless=True untuk production, False untuk bypass anti-bot."""
    v = os.getenv("CRAWL_HEADLESS", "").lower()
    if v == "true":
        return True
    if v == "false":
        return False
    return True  # default headless=True (lebih ringan)


async def _make_strategy(
    headless: Optional[bool] = None,
):
    from crawl4ai import BrowserConfig, UndetectedAdapter
    from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

    hl = headless if headless is not None else _should_headless()
    browser_config = BrowserConfig(
        headless=hl,
        enable_stealth=True,
        user_agent_mode="random",
        light_mode=True,
    )
    adapter = UndetectedAdapter()
    strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config=browser_config,
        browser_adapter=adapter,
    )
    return strategy, browser_config


def make_run_config(
    *,
    css_selector: Optional[str] = None,
    delay: float = 0.5,
    page_timeout: int = 30_000,
    only_text: bool = True,
):
    """Build a CrawlerRunConfig tuned for stealth crawling (fast path)."""
    from crawl4ai import CacheMode, CrawlerRunConfig

    return CrawlerRunConfig(
        delay_before_return_html=delay,
        # "domcontentloaded" jauh lebih cepat dari "load" tanpa kehilangan konten
        # pada halaman alodokter (konten statis SSR).
        wait_until="domcontentloaded",
        cache_mode=CacheMode.BYPASS,
        page_timeout=page_timeout,
        only_text=only_text,
        css_selector=css_selector,
    )


def _clean_markdown(raw: str) -> str:
    """Strip front-matter, excessive blank lines."""
    raw = re.sub(r"^---\n.*?\n---\n", "", raw, flags=re.DOTALL)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


async def crawl_url(
    url: str,
    *,
    headless: Optional[bool] = None,
    css_selector: Optional[str] = None,
    delay: float = 0.5,
    page_timeout: int = 30_000,
) -> tuple[Optional[str], Optional[str]]:
    """Crawl a single URL using stealth strategy.

    Returns:
        (markdown_text, error_or_None)
    """
    from crawl4ai import AsyncWebCrawler

    try:
        strategy, browser_config = await _make_strategy(headless)
        run_config = make_run_config(
            css_selector=css_selector,
            delay=delay,
            page_timeout=page_timeout,
        )
        async with AsyncWebCrawler(crawler_strategy=strategy, config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)

        if not getattr(result, "success", False):
            err = getattr(result, "error_message", "") or "unknown"
            return None, f"gagal: {err[:200]}"

        html = getattr(result, "html", None) or ""
        blocked, reason = is_blocked(getattr(result, "status_code", None), html)
        if blocked:
            logger.warning("anti-bot terdeteksi untuk %s: %s (html=%dB)", url, reason, len(html))
            return None, f"diblokir anti-bot: {reason[:160]}"

        md = getattr(result, "markdown", None) or ""
        if not md:
            md = getattr(result, "raw_markdown", None) or ""

        if not md:
            return None, "konten kosong"

        return _clean_markdown(md), None

    except Exception as exc:
        logger.warning("crawl_url error %s: %s", url, exc)
        return None, str(exc)[:200]


def crawl_url_sync(url: str, **kwargs) -> tuple[Optional[str], Optional[str]]:
    """Sync wrapper — safe to call from a thread; runs crawl in a fresh asyncio loop.

    This is needed on Windows where the caller's running loop (e.g. uvicorn's
    selector loop) cannot spawn the Playwright browser subprocess.
    """
    return asyncio.run(crawl_url(url, **kwargs))


# ─────────────────────────────────────────────────────────────────────────────
# Live web fallback: map keyword → alodokter article slug
# ─────────────────────────────────────────────────────────────────────────────

ALODOKTER_SLUG_MAP: dict[str, str] = {
    "rontok": "rambut-rontok",
    "rambut rontok": "rambut-rontok",
    "kebotakan": "rambut-rontok",
    "rambut rontok berlebih": "rambut-rontok",
    "botak": "rambut-rontok",
    "rambut rontok saat hamil": "rambut-rontok-hamil",
    "rambut rontok pria": "rambut-rontok",
    "rambut rontok wanita": "rambut-rontok",
    "rambut rontok anak": "rambut-rontok",
    "tumbuh kembali": "rambut-rontok",
    "dht": "rambut-rontok",
    "minoxidil": "rambut-rontok",
    "vitamin rambut": "rambut-rontok",
    "vitamin rambut rontok": "rambut-rontok",
    "telogen": "rambut-rontok",
    "rontok parah": "rambut-rontok",
    "rambut patah": "rambut-rontok",
    "rambut rontok musiman": "rambut-rontok",
    "rambut rontok anak remaja": "rambut-rontok",
    "rambut rontok penuaan": "rambut-rontok",
    "ketombe": "ketombe",
    "ketombe parah": "ketombe",
    "kulit kepala gatal": "ketombe",
    "jamur kulit kepala": "ketombe",
    "rambut kering": "rambut-kering",
    "rambut bercabang": "rambut-bercabang",
    "rambut kusam": "rambut-kusam",
    "rambut rontok perawatan": "rambut-rontok",
    "perawatan rambut rontok": "rambut-rontok",
    "obat rambut rontok": "rambut-rontok",
    "alat rambut rontok": "rambut-rontok",
    "shampoo rontok": "rambut-rontok",
    "rambut tipis": "rambut-rontok",
    "rambut rontok kronis": "rambut-rontok",
    "rambut rontok alopecia": "rambut-rontok",
    "alopecia": "rambut-rontok",
    "hormon rambut": "rambut-rontok",
    "nutrisi rambut": "rambut-rontok",
    "stres rambut rontok": "rambut-rontok",
    "pola rambut rontok": "rambut-rontok",
    "rontok": "rambut-rontok",
}

HEALTH_KEYWORDS = [
    "rontok", "botak", "kebotakan", "tumbuh kembali", "rambut rontok",
    "ketombe", "jamur kulit kepala", "kulit kepala gatal", "kulit kepala berketombe",
    "minoxidil", "dht", "alopecia",
    "vitamin rambut", "nutrisi rambut", "hormon rambut",
    "rambut patah", "rambut kering", "rambut bercabang",
    "rambut kusam", "rambut tipis", "perawatan rambut rontok",
    "shampoo rontok", "obat rambut", "stres rambut",
    "penyebab rambut", "gejala rambut", "mengatasi rambut rontok",
]

# Kata layanan salon — jika muncul, JANGAN pakai web mode meski ada kata kesehatan.
SALON_SERVICE_KEYWORDS = [
    "harga", "booking", "reservasi", "pesan", "jadwal", "durasi", "biaya",
    "potong", "cat", "pewarnaan", "smoothing", "rebonding", "keriting",
    "layanan", "treatment", "salon", "stylist", "promo", "diskon",
]

# Kata "kekhawatiran kondisi rambut" pada konteks layanan salon — memicu mode MIX
# (KB lokal + web crawl) karena menyentuh aspek kesehatan rambut.
# Catatan: sengaja berupa frasa spesifik agar tidak terlalu agresif; mis. kata
# "bleaching" saja TIDAK cukup (bisa sekadar info riwayat), harus ada keraguan/risiko.
HAIR_CONCERN_KEYWORDS = [
    "setelah bleaching", "habis bleaching", "baru bleaching",
    "aman tidak", "apakah aman", "aman gak", "aman ga", "boleh tidak", "boleh gak",
    "apakah boleh", "risiko", "bahaya", "rusak tidak", "makin rusak",
    "kerusakan rambut", "rambut rusak", "rambut rapuh", "rambut sensitif",
    "kondisi rambut saya", "kekuatan rambut", "rambut kering",
    "rambut patah", "rontok setelah", "frizz berlebih",
]


def detect_health_topic(query: str) -> bool:
    """True if query is about hair health/medical topics (not salon services)."""
    q = query.lower()
    # Pertanyaan layanan salon tidak pernah pakai web mode.
    if any(kw in q for kw in SALON_SERVICE_KEYWORDS):
        return False
    return any(kw in q for kw in HEALTH_KEYWORDS)


def detect_hair_concern(query: str) -> bool:
    """True if a salon query touches hair-health concerns (bleaching, rusak, dsb).

    Untuk query seperti ini, hasil jawaban di-mix: KB salon + konten web kesehatan.
    """
    q = query.lower()
    return any(kw in q for kw in HAIR_CONCERN_KEYWORDS)


def resolve_alodokter_slug(query: str) -> str:
    """Map query to alodokter article slug, default rambut-rontok."""
    q = query.lower()
    # exact phrase first
    for kw, slug in sorted(ALODOKTER_SLUG_MAP.items(), key=lambda x: -len(x[0])):
        if kw in q:
            return slug
    return "rambut-rontok"
