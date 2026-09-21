"""Ingest knowledge base -> ChromaDB.

Port of `apps/api/src/rag/ingest.ts`. Two topic sources:
  - Legacy static mapping (filename -> topic) for existing hand-written KB files.
  - YAML front-matter `topic` for crawled files (crawled-*.md from Crawl4AI).

Idempotent: chunk id = <filename>#<sha16_hash>#<index>. Run with --force to wipe first.

CLI:
  python -m app.rag.ingest           # incremental
  python -m app.rag.ingest --force   # wipe then ingest
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
from pathlib import Path

from app.config import settings
from app.rag.chunker import chunk_markdown
from app.rag.embedding import embed_sync
from app.rag.vector_store import RAG_TOPICS, vector_store

logger = logging.getLogger(__name__)

# Legacy filename -> topic mapping (still used for the 5 hand-written files).
LEGACY_TOPIC_MAP: dict[str, str] = {
    "harga.md": "harga",
    "layanan.md": "layanan",
    "gaya-rambut.md": "gaya-rambut",
    "tips-perawatan.md": "tips-perawatan",
    "booking-info.md": "booking-info",
}


def _sha16(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _parse_front_matter(content: str) -> tuple[dict, str]:
    """Extract YAML front-matter and remaining markdown content.

    Supports the format:
        ---
        topic: tips-perawatan
        source: https://example.com
        ---
        # Markdown content ...
    """
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, flags=re.DOTALL)
    if not fm_match:
        return {}, content

    meta_block, body = fm_match.groups()
    meta: dict[str, str] = {}
    for line in meta_block.strip().split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip().strip("'\"")
    return meta, body


def resolve_topic(filename: str, content: str) -> str | None:
    """Resolve topic from filename/front-matter. Returns None -> skip."""
    meta, _ = _parse_front_matter(content)
    fm_topic = meta.get("topic", "").strip()
    if fm_topic:
        return fm_topic
    return LEGACY_TOPIC_MAP.get(filename)


def plan_ingest(
    kb_dir: Path | str,
    force: bool = False,
    min_tokens: int | None = None,
    max_tokens: int | None = None,
    overlap: int | None = None,
) -> list[dict]:
    """Pure function: ingest one KB directory -> list of operation summaries.

    Side-effect: upserts into chromadb via vector_store.
    """
    kb_path = Path(kb_dir)
    if not kb_path.exists():
        logger.warning("Knowledge base directory tidak ada: %s", kb_path)
        return []

    summaries: list[dict] = []

    if force:
        for topic in RAG_TOPICS:
            vector_store.clear(topic)
            logger.info("collection cleared: %s", topic)
    md_files = sorted(kb_path.glob("*.md"))
    if not md_files:
        logger.warning("Knowledge base kosong: %s", kb_path)
        return []

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        topic = resolve_topic(md_file.name, content)
        if not topic:
            logger.info("skip (no topic): %s", md_file.name)
            continue

        body = _parse_front_matter(content)[1]
        chunks = chunk_markdown(body, {
            "minTokens": min_tokens or settings.rag_min_chunk_tokens,
            "maxTokens": max_tokens or settings.rag_max_chunk_tokens,
            "overlapTokens": overlap or settings.rag_chunk_overlap,
        })
        if not chunks:
            logger.info("skip (no chunks): %s", md_file.name)
            continue

        content_hash = _sha16(content)
        ids = [f"{md_file.name}#{content_hash}#{i}" for i in range(len(chunks))]

        existing_ids = set(vector_store.existing_ids(topic))
        to_insert = [j for j, cid in enumerate(ids) if cid not in existing_ids]
        to_delete = [cid for cid in existing_ids if cid not in ids]

        if to_insert:
            texts = [chunks[j].text for j in to_insert]
            embeddings = embed_sync(texts)
            vector_store.upsert(
                topic,
                ids=[ids[j] for j in to_insert],
                texts=texts,
                embeddings=embeddings,
                metadatas=[
                    {"file": md_file.name, "section": chunks[j].section, "topic": topic, "hash": content_hash}
                    for j in to_insert
                ],
            )
        if to_delete:
            vector_store.delete_by_ids(topic, to_delete)

        summary = {
            "file": md_file.name,
            "topic": topic,
            "total_chunks": len(chunks),
            "inserted": len(to_insert),
            "deleted": len(to_delete),
        }
        summaries.append(summary)
        logger.info("ingest file=%s topic=%s chunks=%d inserted=%d deleted=%d",
                     md_file.name, topic, len(chunks), len(to_insert), len(to_delete))
    return summaries


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base -> ChromaDB")
    parser.add_argument("--force", action="store_true", help="Wipe collections before ingesting")
    args = parser.parse_args()

    summaries = plan_ingest(settings.rag_knowledge_dir, force=args.force)
    print(f"\nSelesai. {len(summaries)} file di-ingest.")
    for s in summaries:
        print(f"  {s['file']:30s} topic={s['topic']:20s} inserted={s['inserted']:3d} deleted={s['deleted']:3d}")


if __name__ == "__main__":
    main()