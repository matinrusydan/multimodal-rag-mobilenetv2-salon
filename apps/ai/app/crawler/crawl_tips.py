"""Crawl tips/perawatan from external source -> knowledge base.

Usage:
  python -m app.crawler.crawl_tips [--base-url URL]

Output: rag/knowledge/crawled-tips-*.md with YAML front-matter `topic: tips-perawatan`.

Default source: alodokter.com (configurable via CRAWL_TIPS_URL).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from app.config import settings

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "rag" / "knowledge"

MAX_PAGES = int(100)


async def _crawl_one_url(crawler, url: str) -> str | None:
    try:
        result = await crawler.arun(url=url, mode="markdown")
        md = getattr(result, "raw_markdown", None) or getattr(result, "markdown_v2", None)
        if not md:
            return None
        return md
    except Exception as exc:
        logger.warning("crawl tips gagal %s: %s", url, exc)
        return None


async def _crawl_one_url_stealth(crawler, url: str) -> str | None:
    """Crawl a tips page within an existing stealth crawler session."""
    from app.crawler.stealth import make_run_config
    from app.crawler.antibot_detector import is_blocked

    try:
        result = await crawler.arun(url=url, config=make_run_config())
        blocked, reason = is_blocked(
            getattr(result, "status_code", None), getattr(result, "html", None) or ""
        )
        if blocked:
            logger.warning("tips anti-bot %s: %s", url, reason)
            return None
        md = getattr(result, "markdown", None) or getattr(result, "raw_markdown", None)
        if not md:
            return None
        return md
    except Exception as exc:
        logger.warning("crawl tips stealth gagal %s: %s", url, exc)
        return None


def _slugify(url: str) -> str:
    slug = urlparse(url).path.strip("/").replace("/", "-")
    return slug[:80] or "index"


async def crawl_tips(base_url: str | None = None, use_stealth: bool | None = None) -> list[dict]:
    from crawl4ai import AsyncWebCrawler, BrowserConfig

    base = (base_url or settings.crawl_tips_url).rstrip("/")
    delay = settings.crawl_delay_ms / 1000.0
    stealth = use_stealth if use_stealth is not None else False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []

    if stealth:
        from app.crawler.stealth import _make_strategy

        strategy, browser_config = await _make_strategy()
        crawler_ctx = AsyncWebCrawler(crawler_strategy=strategy, config=browser_config)
        crawl_fn = _crawl_one_url_stealth
    else:
        browser_config = BrowserConfig(headless=True)
        crawler_ctx = AsyncWebCrawler(config=browser_config)
        crawl_fn = _crawl_one_url

    async with crawler_ctx as crawler:
        visited: set[str] = set()
        to_visit: list[str] = [base]
        count = 0

        while to_visit and count < MAX_PAGES:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            count += 1

            md = await crawl_fn(crawler, url)
            if md is None:
                continue

            slug = _slugify(url)
            filename = f"crawled-tips-{slug}.md"
            fm = f"---\ntopic: tips-perawatan\nsource: {url}\ntype: crawled\n---\n"
            (OUTPUT_DIR / filename).write_text(fm + md, encoding="utf-8")
            summaries.append({"url": url, "file": filename})
            logger.info("crawl tips %s -> %s", url, filename)

            # Extract internal links (same domain).
            links = re.findall(r"\[.*?\]\((.*?)\)", md)
            for link in links:
                full = urljoin(url, link)
                parsed = urlparse(full)
                if parsed.netloc == urlparse(base).netloc and full not in visited:
                    to_visit.append(full)

            if delay > 0:
                await asyncio.sleep(delay)

    print(f"\nSelesai. {len(summaries)} artikel tips di-crawl.")
    return summaries


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Crawl tips eksternal -> knowledge base")
    parser.add_argument("--base-url", default=None, help="Source URL (default: CRAWL_TIPS_URL)")
    parser.add_argument("--stealth", action="store_true", default=False, help="Gunakan stealth (bypass anti-bot)")
    args = parser.parse_args()
    asyncio.run(crawl_tips(base_url=args.base_url, use_stealth=args.stealth))


if __name__ == "__main__":
    main()