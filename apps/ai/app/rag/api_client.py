"""HTTP client ke Express API (apps/api) untuk agent admin & serialisasi katalog.

Menyertakan header X-Internal-Token (AI_INTERNAL_TOKEN) supaya Express
mempercayai panggilan internal dari brain engine (tool-call data live).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ApiClientError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if settings.agent_internal_token:
        headers["X-Internal-Token"] = settings.agent_internal_token
    return headers


async def api_get(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    """GET ke Express API, return `data` dari envelope {ok,data}. Raise on error."""
    url = f"{settings.api_base_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(url, params=params, headers=_headers())
    except Exception as exc:
        raise ApiClientError(f"gagal menghubungi API {path}: {exc}") from exc

    if res.status_code >= 400:
        body = res.text[:300]
        raise ApiClientError(f"API {path} -> HTTP {res.status_code}: {body}")

    payload = res.json()
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def api_get_sync(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    """Sync wrapper (untuk CLI sync_catalog)."""
    import asyncio

    return asyncio.run(api_get(path, params))
