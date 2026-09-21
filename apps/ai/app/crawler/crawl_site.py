"""Crawl site TIEN salon -> knowledge base markdown files.

Usage:
  python -m app.crawler.crawl_site [--base-url URL] [--browser]

Output: rag/knowledge/crawled-site-*.md with YAML front-matter `topic`.

Requires `crawl4ai` and optionally Playwright (for SPA with --browser flag).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from app.config import settings
from app.crawler.topic_mapping import resolve_topic_from_url

logger = logging.getLogger(__name__)

OUTPUT_DIR = settings.rag_knowledge_dir

# Max pages safety limit.
MAX_PAGES = int(200)


async def _crawl_one_url(crawler, url: str) -> tuple[str, str] | None:
    """Fetch one URL, return (url, raw_markdown) or None."""
    try:
        from app.crawler.stealth import make_run_config

        result = await crawler.arun(url=url, config=make_run_config())
        md = getattr(result, "markdown", None) or getattr(result, "raw_markdown", None)
        if md and hasattr(md, "fit_markdown"):
            md = md.fit_markdown or md.raw_markdown
        if not md:
            return None
        return (url, md if isinstance(md, str) else str(md))
    except Exception as exc:
        logger.warning("crawl gagal %s: %s", url, exc)
        return None


async def _crawl_one_url_stealth(crawler, url: str) -> tuple[str, str] | None:
    """Fetch one URL within an existing stealth crawler session."""
    from app.crawler.stealth import make_run_config
    from app.crawler.antibot_detector import is_blocked

    try:
        result = await crawler.arun(url=url, config=make_run_config())
        blocked, reason = is_blocked(
            getattr(result, "status_code", None), getattr(result, "html", None) or ""
        )
        if blocked:
            logger.warning("anti-bot terdeteksi %s: %s", url, reason)
            return None
        md = getattr(result, "markdown", None) or getattr(result, "raw_markdown", None)
        if not md:
            return None
        return (url, md)
    except Exception as exc:
        logger.warning("crawl stealth gagal %s: %s", url, exc)
        return None


def _slugify(url: str) -> str:
    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("/", "_")
    return slug or "home"


async def crawl_site(
    base_url: str | None = None,
    use_browser: bool | None = None,
    use_stealth: bool | None = None,
) -> list[dict]:
    from crawl4ai import AsyncWebCrawler, BrowserConfig

    base = (base_url or settings.crawl_base_url).rstrip("/")
    browser = use_browser if use_browser is not None else settings.crawl_use_browser
    stealth = use_stealth if use_stealth is not None else False
    delay = settings.crawl_delay_ms / 1000.0

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
        to_visit: list[str] = [base + "/"]
        count = 0

        while to_visit and count < MAX_PAGES:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            count += 1

            result = await crawl_fn(crawler, url)
            if result is None:
                continue

            _, md = result
            topic = resolve_topic_from_url(url)
            slug = _slugify(url)
            filename = f"crawled-site-{slug}.md"

            fm = f"---\ntopic: {topic}\nsource: {url}\ntype: crawled\n---\n"
            (OUTPUT_DIR / filename).write_text(fm + md, encoding="utf-8")
            summaries.append({"url": url, "topic": topic, "file": filename})
            logger.info("crawl  %s -> %s (topic=%s)", url, filename, topic)

            # Extract internal links for BFS.
            links = re.findall(r"\[.*?\]\((.*?)\)", md)
            for link in links:
                full = urljoin(url, link)
                parsed = urlparse(full)
                if parsed.netloc == urlparse(base).netloc and full not in visited:
                    to_visit.append(full)

            if delay > 0:
                await asyncio.sleep(delay)

    print(f"\nSelesai. {len(summaries)} halaman di-crawl.")
    return summaries


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Crawl situs salon -> knowledge base")
    parser.add_argument("--base-url", default=None, help="Base URL salon (default: CRAWL_BASE_URL)")
    parser.add_argument("--browser", action="store_true", default=False, help="Gunakan Playwright (SPA)")
    parser.add_argument("--stealth", action="store_true", default=False, help="Gunakan stealth (bypass anti-bot)")
    args = parser.parse_args()
    asyncio.run(crawl_site(base_url=args.base_url, use_browser=args.browser, use_stealth=args.stealth))


if __name__ == "__main__":
    main()