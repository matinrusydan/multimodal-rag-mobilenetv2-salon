"""Markdown chunking for the knowledge base.

Port of `apps/api/src/rag/chunker.ts` — chunk size 500-1000 estimated tokens
with 100-token overlap (chars/4 heuristic). Splits follow markdown sections
(##) and avoids cutting mid-sentence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

DEFAULT_OPTIONS = {"maxTokens": 1000, "overlapTokens": 100, "minTokens": 500}


@dataclass
class RAGChunk:
    text: str
    section: str


def estimate_tokens(text: str) -> int:
    """Approximate tokens via ~4 chars per token (enough for chunk bounds)."""
    return (len(text) + 3) // 4


def split_sections(markdown: str) -> list[dict]:
    """Split markdown into level-2 (##) sections."""
    sections: list[dict] = []
    for line in markdown.split("\n"):
        m = re.match(r"^#{2,}\s+(.*)$", line)
        if m:
            sections.append({"header": m.group(1).strip(), "body": []})
        elif sections:
            sections[-1]["body"].append(line)
    return [{"header": s["header"], "body": "\n".join(s["body"]).strip()} for s in sections]


def split_sentences(text: str) -> list[str]:
    """Split text into sentence-ish units, never cutting mid-sentence."""
    parts: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        for seg in re.split(r"(?<=[.!?])\s+", line):
            seg = seg.strip()
            if seg:
                parts.append(seg)
    return parts


def chunk_markdown(markdown: str, options: Optional[dict] = None) -> list[RAGChunk]:
    """Chunk a whole markdown document. Each chunk stays within maxTokens and
    carries ~overlapTokens from the previous chunk. Sections stay separate."""
    opts = {**DEFAULT_OPTIONS, **(options or {})}
    max_tokens = opts["maxTokens"]
    overlap_tokens = opts["overlapTokens"]
    min_tokens = opts["minTokens"]
    chunks: list[RAGChunk] = []

    def flush_body(
        header: str,
        current: list[str],
        overlap_parts: list[str],
    ) -> tuple[list[RAGChunk], list[str]]:
        text = " ".join([*overlap_parts, *current]).strip()
        added: list[RAGChunk] = []
        if text:
            full = len(text)
            added.append(RAGChunk(text=text, section=header))
            # carry overlap (measured in estimated tokens)
            carry = ""
            for i in range(full - 1, -1, -1):
                if estimate_tokens(carry) >= overlap_tokens:
                    break
                carry = text[i] + carry
            next_overlap = carry.strip().split(" ") if carry.strip() else []
            return added, next_overlap
        return added, []

    for section in split_sections(markdown):
        header = section["header"]
        if not header.strip():
            continue
        sentences = split_sentences(section["body"])
        if not sentences:
            continue

        current: list[str] = []
        overlap_parts: list[str] = []

        def cur_text() -> str:
            return " ".join([*overlap_parts, *current])

        for sentence in sentences:
            candidate = " ".join([*overlap_parts, *current, sentence])
            if (
                current
                and estimate_tokens(candidate) > max_tokens
                and estimate_tokens(cur_text()) >= min_tokens
            ):
                emitted, overlap_parts = flush_body(header, current, overlap_parts)
                chunks.extend(emitted)
                current = []
            current.append(sentence)
            if estimate_tokens(cur_text()) >= max_tokens:
                emitted, overlap_parts = flush_body(header, current, overlap_parts)
                chunks.extend(emitted)
                current = []
        emitted, _ = flush_body(header, current, overlap_parts)
        chunks.extend(emitted)

    # Fallback for markdown without any ## section.
    if not chunks:
        sentences = split_sentences(markdown)
        buff: list[str] = []
        for sentence in sentences:
            buff.append(sentence)
            if estimate_tokens(" ".join(buff)) >= min_tokens:
                chunks.append(RAGChunk(text=" ".join(buff), section="Dokumen"))
                buff = []
        if buff:
            chunks.append(RAGChunk(text=" ".join(buff), section="Dokumen"))

    return chunks