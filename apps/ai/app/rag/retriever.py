"""Retriever: cosine-similarity across all topic collections, merged, top_k.
Port of `apps/api/src/rag/retriever.ts`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.rag.vector_store import RAG_TOPICS, VectorStore, vector_store


@dataclass
class RetrievedDoc:
    file: str
    section: Optional[str] = None
    snippet: Optional[str] = None
    distance: Optional[float] = None


class StoreLike:
    """Protocol for a fake store in tests."""

    async def query(self, topic: str, embedding: list[float], top_k: int) -> list[dict]:
        raise NotImplementedError


class Retriever:
    def __init__(self, store: VectorStore | StoreLike = vector_store, topics: Optional[list[str]] = None) -> None:
        self.store = store
        self.topics = topics if topics is not None else list(RAG_TOPICS)

    async def retrieve(
        self,
        embedding: list[float],
        top_k: int = 5,
    ) -> list[RetrievedDoc]:
        per_topic = max(1, (top_k + len(self.topics) - 1) // len(self.topics)) if top_k else 1

        results: list[list[dict]] = []
        for topic in self.topics:
            try:
                hits = await self.store.query(topic, embedding, per_topic)
                results.append(hits)
            except NotImplementedError:
                raise
            except Exception:
                results.append([])

        merged: list[dict] = []
        for hits in results:
            for h in hits:
                if h.get("text"):
                    merged.append(h)
        merged.sort(key=lambda h: h.get("distance", 0.0))

        taken = merged[:top_k] if top_k > 0 else merged

        docs: list[RetrievedDoc] = []
        for h in taken:
            meta = h.get("metadata") or {}
            file = meta.get("file") or str(h.get("id", "")).split("#")[0] or "rag"
            docs.append(
                RetrievedDoc(
                    file=str(file),
                    section=meta.get("section") if isinstance(meta.get("section"), str) else None,
                    snippet=h.get("text"),
                    distance=h.get("distance"),
                )
            )
        return docs


retriever = Retriever()