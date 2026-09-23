"""Ambil konfigurasi runtime dari Express API (mis. Gemini API key yang diset admin).

Sumber utama tetap env (GEMINI_API_KEY). Bila admin menyetel key di dashboard
(tabel site_settings), nilai itu dipakai (menimpa env), dengan cache singkat.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, str | None]] = {}
_TTL = 60.0  # detik


def _fetch_gemini_key() -> str | None:
    url = f"{settings.api_base_url.rstrip('/')}/api/settings/gemini-key"
    headers: dict[str, str] = {"Accept": "application/json"}
    if settings.agent_internal_token:
        headers["X-Internal-Token"] = settings.agent_internal_token
    try:
        res = httpx.get(url, headers=headers, timeout=8)
        if res.status_code >= 400:
            return None
        data = res.json().get("data") or {}
        key = data.get("key")
        return key if isinstance(key, str) and key else None
    except Exception as exc:
        logger.debug("gagal ambil gemini key dari API: %s", exc)
        return None


def gemini_api_key() -> str | None:
    """Return Gemini API key efektif: DB (jika ada) > env."""
    now = time.monotonic()
    cached = _CACHE.get("gemini")
    if cached and now - cached[0] < _TTL:
        return cached[1]

    key = _fetch_gemini_key() or os.getenv("GEMINI_API_KEY") or settings.gemini_api_key or None
    _CACHE["gemini"] = (now, key)
    return key


def _fetch_setting(key: str) -> object | None:
    url = f"{settings.api_base_url.rstrip('/')}/api/settings/internal/{key}"
    headers: dict[str, str] = {"Accept": "application/json"}
    if settings.agent_internal_token:
        headers["X-Internal-Token"] = settings.agent_internal_token
    try:
        res = httpx.get(url, headers=headers, timeout=8)
        if res.status_code >= 400:
            return None
        data = res.json().get("data") or {}
        return data.get("value")
    except Exception as exc:
        logger.debug("gagal ambil setting %s dari API: %s", key, exc)
        return None


def crawl_targets() -> list[str]:
    """Daftar URL target crawler (dari DB), fallback env CRAWL_TIPS_URLS."""
    now = time.monotonic()
    cached = _CACHE.get("crawl_targets")
    if cached and now - cached[0] < _TTL:
        return list(cached[1] or [])

    value = _fetch_setting("crawl_targets")
    targets: list[str] = []
    if isinstance(value, list):
        targets = [str(u).strip() for u in value if str(u).strip()]
    if not targets:
        targets = list(settings.crawl_tips_urls)
    _CACHE["crawl_targets"] = (now, targets)  # type: ignore[assignment]
    return targets


def invalidate() -> None:
    _CACHE.pop("gemini", None)
    _CACHE.pop("crawl_targets", None)
