"""Tests for plan_ingest pure logic and topic resolution.

Verifies:
  - legacy filename -> topic mapping
  - front-matter topic parsing
  - idempotent chunk id generation
  - no live ChromaDB required (fake store pattern)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.crawler.topic_mapping import resolve_topic_from_url
from app.rag.chunker import chunk_markdown, estimate_tokens
from app.rag.ingest import LEGACY_TOPIC_MAP, _sha16, plan_ingest, resolve_topic


class TestTopicResolution:
    def test_legacy_filename_map(self):
        assert resolve_topic("harga.md", "") == "harga"
        assert resolve_topic("layanan.md", "") == "layanan"
        assert resolve_topic("gaya-rambut.md", "") == "gaya-rambut"
        assert resolve_topic("tips-perawatan.md", "") == "tips-perawatan"
        assert resolve_topic("booking-info.md", "") == "booking-info"

    def test_front_matter_overrides_legacy(self):
        content = "---\ntopic: harga\n---\nSome content"
        assert resolve_topic("tips-perawatan.md", content) == "harga"

    def test_unknown_filename_no_fm_returns_none(self):
        assert resolve_topic("random.md", "Just some text") is None

    def test_front_matter_only(self):
        content = "---\ntopic: gaya-rambut\n---\nBody"
        assert resolve_topic("crawled-site-home.md", content) == "gaya-rambut"


class TestSiteTopicMapping:
    def test_services(self):
        assert resolve_topic_from_url("http://localhost/services") == "layanan"
        assert resolve_topic_from_url("http://localhost/services/haircut") == "layanan"

    def test_reservation(self):
        assert resolve_topic_from_url("http://localhost/reservation") == "booking-info"

    def test_root(self):
        assert resolve_topic_from_url("http://localhost/") == "layanan"

    def test_unknown(self):
        assert resolve_topic_from_url("http://localhost/blabla/xyz") == "layanan"


class TestChunker:
    def test_estimate_tokens(self):
        assert estimate_tokens("1234") == 1
        assert estimate_tokens("12345678") == 2

    def test_chunk_with_sections(self):
        md = "## Sesi 1\nHello world. This is a test.\n\n## Sesi 2\nAnother section here."
        chunks = chunk_markdown(md)
        assert len(chunks) >= 2
        sections = {c.section for c in chunks}
        assert "Sesi 1" in sections
        assert "Sesi 2" in sections

    def test_chunk_without_headers(self):
        md = "Just text. " * 500
        chunks = chunk_markdown(md)
        assert len(chunks) >= 1
        assert all(c.section == "Dokumen" for c in chunks)

    def test_small_doc(self):
        md = "## Title\nShort."
        chunks = chunk_markdown(md)
        assert len(chunks) == 1


class TestPlanIngest:
    @patch("app.rag.ingest.vector_store")
    def test_empty_dir(self, mock_store):
        summaries = plan_ingest(Path("/nonexistent/path"))
        assert summaries == []

    def test_idempotent_hash(self):
        content_a = "Hello world"
        content_b = "Hello world"
        assert _sha16(content_a) == _sha16(content_b)