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

OUTPUT_DIR = settings.rag_knowledge_dir

MAX_PAGES = int(100)


async def _crawl_one_url(crawler, url: str) -> str | None:
    try:
        from app.crawler.stealth import make_run_config

        result = await crawler.arun(url=url, config=make_run_config())
        md = getattr(result, "markdown", None) or getattr(result, "raw_markdown", None)
        if md and hasattr(md, "fit_markdown"):
            md = md.fit_markdown or md.raw_markdown
        if not md:
            return None
        return md if isinstance(md, str) else str(md)
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


async def crawl_tips(
    base_url: str | None = None,
    use_stealth: bool | None = None,
    targets: list[str] | None = None,
) -> list[dict]:
    from crawl4ai import AsyncWebCrawler, BrowserConfig

    # Prioritas sumber: targets eksplisit > base_url > setting runtime (DB) > env.
    if targets:
        sources = [t.rstrip("/") for t in targets if t.strip()]
    elif base_url:
        sources = [base_url.rstrip("/")]
    else:
        from app.settings_loader import crawl_targets

        dynamic = crawl_targets()
        sources = [u.rstrip("/") for u in (dynamic or [settings.crawl_tips_url]) if u.strip()]

    delay = settings.crawl_delay_ms / 1000.0
    stealth = use_stealth if use_stealth is not None else False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_summaries: list[dict] = []

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
        for src in sources:
            logger.info("[tips] sumber: %s", src)
            visited: set[str] = set()
            to_visit: list[str] = [src]
            count = 0
            src_parsed = urlparse(src)
            src_domain = src_parsed.netloc
            # Batasi BFS hanya pada prefix path sumber (mis. /rambut/) agar tidak
            # menyerap seluruh domain (komunitas, seks, nutrisi, dsb).
            src_prefix = src_parsed.path.rstrip("/") or "/"
            src_slug = src_domain.replace(".", "-")

            def _in_scope(u: str) -> bool:
                p = urlparse(u)
                if p.netloc != src_domain:
                    return False
                return p.path.startswith(src_prefix)

            while to_visit and count < MAX_PAGES:
                url = to_visit.pop(0)
                if url in visited:
                    continue
                visited.add(url)
                count += 1

                md = await crawl_fn(crawler, url)
                if md is None:
                    continue

                slug = f"{src_slug}-{_slugify(url)}"
                filename = f"crawled-tips-{slug}.md"
                fm = f"---\ntopic: tips-perawatan\nsource: {url}\ntype: crawled\n---\n"
                (OUTPUT_DIR / filename).write_text(fm + md, encoding="utf-8")
                all_summaries.append({"url": url, "file": filename})
                logger.info("crawl tips %s -> %s", url, filename)

                # Extract internal links (same domain & same path scope).
                links = re.findall(r"\[.*?\]\((.*?)\)", md)
                for link in links:
                    full = urljoin(url, link)
                    if _in_scope(full) and full not in visited:
                        to_visit.append(full)

                if delay > 0:
                    await asyncio.sleep(delay)

    print(f"\nSelesai. {len(all_summaries)} artikel tips di-crawl dari {len(sources)} sumber.")
    return all_summaries


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Crawl tips eksternal -> knowledge base")
    parser.add_argument("--base-url", default=None, help="Source URL (default: CRAWL_TIPS_URL)")
    parser.add_argument("--stealth", action="store_true", default=False, help="Gunakan stealth (bypass anti-bot)")
    args = parser.parse_args()
    asyncio.run(crawl_tips(base_url=args.base_url, use_stealth=args.stealth))


if __name__ == "__main__":
    main()