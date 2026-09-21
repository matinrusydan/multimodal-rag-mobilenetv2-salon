"""ChromaDB vector store — native Python (dual-mode persistent | http).

Port of `apps/api/src/rag/vectorStore.ts` to the Python chromadb client.
Collection one per topic (harga, layanan, gaya-rambut, tips-perawatan, booking-info).
"""

from __future__ import annotations

import logging
from typing import Optional

import chromadb
from chromadb.api.models.Collection import Collection

from app.config import settings

logger = logging.getLogger(__name__)

# Koleksi KB publik (chat pelanggan) — TANPA katalog admin.
RAG_TOPICS = [
    "harga",
    "layanan",
    "gaya-rambut",
    "tips-perawatan",
    "booking-info",
]

# Koleksi untuk agent admin (termasuk katalog hasil serialize DB).
AGENT_TOPICS = [*RAG_TOPICS, "katalog"]


def collection_name(topic: str) -> str:
    return f"rag-salon-{topic}"


class VectorStore:
    def __init__(self) -> None:
        self._client: Optional[chromadb.ClientAPI] = None
        self._collections: dict[str, Collection] = {}

    def _get_client(self):
        if self._client is None:
            if settings.chroma_mode == "http":
                self._client = chromadb.HttpClient(host=settings.chroma_url, port=8000)
            else:
                settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir))
            logger.info("ChromaDB client siap (mode=%s)", settings.chroma_mode)
        return self._client

    def _collection(self, topic: str) -> Collection:
        col = self._collections.get(topic)
        if col is None:
            col = self._get_client().get_or_create_collection(name=collection_name(topic))
            self._collections[topic] = col
        return col

    def upsert(
        self,
        topic: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        col = self._collection(topic)
        mds = metadatas or [{} for _ in ids]
        col.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=mds)
        logger.debug("upsert topic=%s n=%d", topic, len(ids))

    async def query(
        self,
        topic: str,
        embedding: list[float],
        top_k: int,
    ) -> list[dict]:
        """Return hits: [{"id", "text", "distance", "metadata"}, ...]."""
        col = self._collection(topic)
        res = col.query(query_embeddings=[embedding], n_results=top_k, include=["documents", "metadatas", "distances"])
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        dists = res.get("distances", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        out: list[dict] = []
        for i, doc_id in enumerate(ids or []):
            out.append(
                {
                    "id": str(doc_id),
                    "text": docs[i] or "" if i < len(docs) else "",
                    "distance": float(dists[i]) if i < len(dists) else 0.0,
                    "metadata": metas[i] or {} if i < len(metas) else {},
                }
            )
        return out

    def existing_ids(self, topic: str) -> list[str]:
        col = self._collection(topic)
        return col.get(include=[])["ids"]

    def delete_by_ids(self, topic: str, ids: list[str]) -> None:
        if not ids:
            return
        col = self._collection(topic)
        col.delete(ids=ids)

    def clear(self, topic: str) -> None:
        ids = self.existing_ids(topic)
        if ids:
            self.delete_by_ids(topic, ids)


vector_store = VectorStore()