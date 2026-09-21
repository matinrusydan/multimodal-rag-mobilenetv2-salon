"""Sync katalog dari DB (via Express API) -> ChromaDB collection 'katalog'.

Dipakai agent admin untuk menjawab pertanyaan semantik tentang layanan/harga.

CLI:
  python -m app.rag.sync_catalog            # sync (idempotent, upsert)
  python -m app.rag.sync_catalog --clear    # kosongkan lalu sync
"""

from __future__ import annotations

import argparse
import logging

from app.config import settings
from app.rag.db_serializer import build_catalog_docs
from app.rag.embedding import embed_sync
from app.rag.vector_store import vector_store

logger = logging.getLogger(__name__)


def sync_catalog(clear: bool = False) -> dict:
    import asyncio

    topic = settings.rag_catalog_topic
    if clear:
        vector_store.clear(topic)
        logger.info("collection katalog dibersihkan")

    docs = asyncio.run(build_catalog_docs())
    if not docs:
        logger.warning("tidak ada dokumen katalog")
        return {"topic": topic, "inserted": 0}

    ids = [d["id"] for d in docs]
    texts = [d["text"] for d in docs]
    embeddings = embed_sync(texts)
    metadatas = [
        {"file": d.get("file", ""), "section": d.get("section", ""), "topic": topic, "source": "db"}
        for d in docs
    ]
    vector_store.upsert(topic, ids=ids, texts=texts, embeddings=embeddings, metadatas=metadatas)
    logger.info("sync katalog: %d dokumen -> collection %s", len(docs), topic)
    return {"topic": topic, "inserted": len(docs)}


def main():
    parser = argparse.ArgumentParser(description="Sync katalog DB -> ChromaDB")
    parser.add_argument("--clear", action="store_true", help="Kosongkan collection sebelum sync")
    args = parser.parse_args()

    result = sync_catalog(clear=args.clear)
    print(f"\nSelesai. topic={result['topic']} inserted={result['inserted']}")


if __name__ == "__main__":
    main()
