"""Tests for retriever using a fake ChromaDB store (no live ChromaDB needed)."""

import pytest

from app.rag.retriever import Retriever, RetrievedDoc


class FakeStore:
    """Minimal fake vector store implementing query()."""

    def __init__(self, hits_by_topic: dict | None = None) -> None:
        self.hits_by_topic = hits_by_topic or {}

    async def query(self, topic: str, embedding: list[float], top_k: int) -> list[dict]:
        return self.hits_by_topic.get(topic, [])[:top_k]


@pytest.mark.asyncio
async def test_retrieve_merges_results():
    fake = FakeStore(
        {
            "harga": [
                {"id": "harga#0", "text": "Harga potong", "distance": 0.2, "metadata": {"file": "harga.md", "section": "potong"}},
            ],
            "layanan": [
                {"id": "layanan#0", "text": "Layanan cat", "distance": 0.3, "metadata": {"file": "layanan.md", "section": "cat"}},
            ],
        }
    )
    r = Retriever(store=fake, topics=["harga", "layanan"])
    docs = await r.retrieve([0.1] * 768, top_k=3)

    assert len(docs) == 2
    assert docs[0].file == "harga.md"
    assert docs[1].file == "layanan.md"


@pytest.mark.asyncio
async def test_retrieve_empty():
    fake = FakeStore()
    r = Retriever(store=fake, topics=["harga"])
    docs = await r.retrieve([0.1] * 768, top_k=5)
    assert docs == []