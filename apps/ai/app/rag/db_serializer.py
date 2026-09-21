"""Serialisasi data DB (via Express API) -> dokumen teks untuk vector DB.

Ini yang dimaksud "docs": bukan file manual, melainkan representasi semantik
dari data operasional salon (layanan, harga, kategori) agar agent admin bisa
menjawab pertanyaan seperti "layanan apa saja yang tersedia?" via RAG.

Dipanggil oleh sync_catalog.py; idempotent (id = doc key).
"""

from __future__ import annotations

import logging
from typing import Any

from app.rag.api_client import api_get

logger = logging.getLogger(__name__)


def _format_rupiah(value: int | float | None) -> str:
    if value is None:
        return "-"
    return f"Rp{int(value):,}".replace(",", ".")


def serialize_services(services: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Ubah daftar layanan jadi dokumen teks kaya-konteks (1 doc per layanan)."""
    docs: list[dict[str, str]] = []
    for s in services:
        name = s.get("name", "-")
        category = s.get("category") or "umum"
        price = _format_rupiah(s.get("price"))
        duration = s.get("durationMin")
        desc = (s.get("description") or "").strip()
        lines = [
            f"# Layanan: {name}",
            f"Kategori: {category}",
            f"Harga: {price}",
            f"Durasi: {duration} menit" if duration else "",
            f"Deskripsi: {desc}" if desc else "",
        ]
        text = "\n".join(line for line in lines if line)
        docs.append({
            "id": f"service:{s.get('slug') or s.get('id')}",
            "section": name,
            "file": f"katalog-service-{s.get('slug') or s.get('id')}.md",
            "text": text,
        })
    return docs


def serialize_catalog_overview(
    stats: dict[str, Any],
    by_category: list[dict[str, Any]],
) -> dict[str, str]:
    """Ringkasan katalog (jumlah layanan, rentang harga, per-kategori)."""
    lines = [
        "# Ringkasan Katalog Layanan Salon",
        f"Total layanan aktif: {stats.get('active', 0)} dari {stats.get('total', 0)}.",
        (
            f"Rentang harga: {_format_rupiah(stats.get('minPrice'))} - "
            f"{_format_rupiah(stats.get('maxPrice'))}."
        ),
        "",
        "## Jumlah layanan per kategori",
    ]
    for c in by_category:
        cat = c.get("category") or "umum"
        lines.append(
            f"- {cat}: {c.get('count', 0)} layanan "
            f"({_format_rupiah(c.get('minPrice'))} - {_format_rupiah(c.get('maxPrice'))}, "
            f"rata-rata {c.get('avgDurationMin', 0)} menit)."
        )
    return {
        "id": "catalog:overview",
        "section": "Ringkasan Katalog",
        "file": "katalog-overview.md",
        "text": "\n".join(lines),
    }


async def build_catalog_docs() -> list[dict[str, str]]:
    """Tarik data dari Express API lalu serialize jadi dokumen teks."""
    summary = await api_get("/api/services/summary")
    services = summary.get("services", []) if isinstance(summary, dict) else []
    stats = summary.get("stats", {}) if isinstance(summary, dict) else {}
    by_category = summary.get("byCategory", []) if isinstance(summary, dict) else []

    docs: list[dict[str, str]] = [serialize_catalog_overview(stats, by_category)]
    docs.extend(serialize_services(services))
    logger.info("serialize katalog: %d dokumen (1 overview + %d layanan)", len(docs), len(services))
    return docs
