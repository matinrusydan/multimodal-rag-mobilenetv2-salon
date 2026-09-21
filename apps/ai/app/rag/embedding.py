"""Embedding provider: Gemini gemini-embedding-001 (768d via outputDimensionality)
with local deterministic fallback (offline/dev/tests, same dimension 768 so the
collection stays compatible).

Port of `apps/api/src/rag/embedding.ts` concepts, but provider Gemini + dim 768.
"""

from __future__ import annotations

import logging
import math
import re

from app.config import settings
from app.settings_loader import gemini_api_key

logger = logging.getLogger(__name__)

LOCAL_EMBEDDING_DIM = 768  # match Gemini gemini-embedding-001 dim (outputDimensionality=768)


def _fnv1a(text: str) -> int:
    h = 0x811C9DC5
    for ch in text:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def embed_local(texts: list[str]) -> list[list[float]]:
    """Deterministic feature-hash embedding (no network). 768d, L2-normalized."""
    vectors: list[list[float]] = []
    for text in texts:
        vec = [0.0] * LOCAL_EMBEDDING_DIM
        normalized = text.lower()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        words = re.findall(r"[a-z0-9]{2,}", normalized)
        features = set(words)
        for w in words:
            features.add(f"bi:{w[:2]}")
            features.add(f"tri:{w[:3]}")
        if len(normalized) > 4:
            for i in range(0, len(normalized) - 2):
                features.add(f"c3:{normalized[i:i+3]}")
        for f in features:
            h = _fnv1a(f)
            idx = h % LOCAL_EMBEDDING_DIM
            vec[idx] += 1 if h & 1 else -1
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        vectors.append([round(v / norm, 8) for v in vec])
    return vectors


def _gemini_client():
    try:
        from google import genai
    except ImportError:
        raise RuntimeError("google-genai tidak terpasang (pip install -r requirements.txt)")
    if not gemini_api_key():
        raise RuntimeError("GEMINI_API_KEY belum diisi")
    return genai.Client(api_key=gemini_api_key())


async def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts.

    - provider=gemini -> gemini-embedding-001 (768d via outputDimensionality), batched API call.
    - provider=local  -> deterministic feature-hash (offline/test).
    Falls back to local automatically if Gemini is unavailable (no key / error).
    """
    if settings.ai_embedding_provider != "gemini" or not gemini_api_key():
        logger.info("embedding lokal (offline, 768d)")
        return embed_local(texts)

    try:
        client = _gemini_client()
        response = await client.aio.models.embed_content(
            model=settings.embedding_model,
            contents=texts,
            config={"outputDimensionality": settings.embedding_dim},
        )
        return [list(e.values) for e in response.embeddings]
    except Exception as exc:  # no key / quota / network
        logger.warning("Gemini embedding gagal (%s); fallback lokal", exc)
        return embed_local(texts)


def embed_sync(texts: list[str]) -> list[list[float]]:
    """Sync wrapper for ingest CLI. Calls Gemini when key is available, local otherwise."""
    if settings.ai_embedding_provider != "gemini" or not gemini_api_key():
        return embed_local(texts)
    try:
        import asyncio
        return asyncio.run(embed(texts))
    except Exception as exc:
        logger.warning("Gemini embed_sync gagal (%s); fallback lokal", exc)
        return embed_local(texts)
