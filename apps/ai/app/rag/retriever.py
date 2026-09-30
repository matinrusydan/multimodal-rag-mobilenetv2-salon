"""Retriever: cosine-similarity across all topic collections, merged, top_k.
Port of `apps/api/src/rag/retriever.ts`.

Menambahkan *query routing* ringan: pertanyaan pelanggan diklasifikasikan ke satu
topik dominan (berbasis kata kunci) agar retrieval hanya menyentuh koleksi yang
relevan. Ini menaikkan context precision karena mengurangi dokumen dari topik lain
yang tidak berkaitan (noise lintas koleksi).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from app.rag.vector_store import RAG_TOPICS, VectorStore, vector_store


@dataclass
class RetrievedDoc:
    file: str
    section: Optional[str] = None
    snippet: Optional[str] = None
    distance: Optional[float] = None


# ── Query routing (keyword/intent-based) ────────────────────────────────────
# Indikator kuat: bila salah satu kata ini muncul, topik langsung ditetapkan.
STRONG_INDICATORS: dict[str, list[str]] = {
    "harga": ["harga", "biaya", "tarif", "price", "cost", "promo", "diskon"],
    "booking-info": ["booking", "reservasi", "reservation", "invoice", "pembatalan"],
}

# Setiap topik punya daftar kata kunci. Skor = jumlah kecocokan kata kunci.
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "harga": [
        "berapa harga", "berapakah", "berapa biaya", "rp", "murah", "mahal", "bayar",
        "pembayaran", "harga",
    ],
    "layanan": [
        "layanan", "service", "treatment", "spa", "hair spa", "haircut",
        "potong", "keratin", "smoothing", "color gloss", "scalp", "detox", "blowout",
        "styling", "manfaat", "durasi", "berfungsi", "layanan apa", "tersedia",
    ],
    "gaya-rambut": [
        "gaya", "model rambut", "potongan", "bentuk wajah", "layer", "poni",
        "bergelombang", "keriting", "ikal", "tekstur", "gaya rambut",
        "rekomendasi gaya", "karakteristik rambut", "kategori panjang",
        "kategori rambut", "panjang rambut", "ciri rambut", "rambut lurus",
        "rambut keriting", "rambut bergelombang",
    ],
    "tips-perawatan": [
        "tips", "cara merawat", "merawat rambut", "perawatan setelah", "pasca",
        "setelah smoothing", "setelah keratin", "setelah treatment", "perawatan pasca",
        "home care", "conditioner", "kondisioner", "ketombe",
        "rontok", "bercabang", "gatal", "perhatian profesional", "perawatan dasar",
        "kesehatan rambut", "perawatan di rumah", "tips perawatan",
    ],
    "booking-info": [
        "reservasi", "pesan", "memesan", "jadwal", "persiapan", "formulir", "konfirmasi",
        "dikonfirmasi", "sebelum datang", "cara melakukan",
    ],
}


def classify_topic(query: str) -> Optional[str]:
    """Klasifikasikan pertanyaan ke satu topik dominan, atau None bila ambigu."""
    q = query.lower()
    q = re.sub(r"\s+", " ", q).strip()

    # 1. Indikator kuat lebih dulu (prioritas tinggi).
    for topic, kws in STRONG_INDICATORS.items():
        for kw in kws:
            if kw in q:
                return topic

    # 2. Skor kata kunci umum.
    scores: dict[str, int] = {}
    for topic, kws in TOPIC_KEYWORDS.items():
        s = 0
        for kw in kws:
            if kw in q:
                s += 2 if " " in kw else 1
        scores[topic] = s
    best_topic, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score == 0:
        return None
    # bila seri antar topik teratas -> anggap ambigu (fallback cross-collection)
    ordered = sorted(scores.values(), reverse=True)
    if len(ordered) > 1 and ordered[0] == ordered[1]:
        return None
    return best_topic


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
        query: Optional[str] = None,
    ) -> list[RetrievedDoc]:
        # ── Query routing: bila query diberikan, fokus ke topik yang terdeteksi ──
        active_topics = self.topics
        if query:
            routed = classify_topic(query)
            if routed and routed in self.topics:
                active_topics = [routed]

        if len(active_topics) == 1:
            # Retrieval terarah: ambil langsung top_k dari koleksi relevan.
            per_topic = top_k if top_k else 1
        else:
            per_topic = max(1, (top_k + len(active_topics) - 1) // len(active_topics)) if top_k else 1

        results: list[list[dict]] = []
        for topic in active_topics:
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

        # Filter berdasarkan jarak: buang dokumen yang terlalu jauh dari dokumen
        # terbaik (noise). Threshold = distance_terbaik + margin, dibatasi top_k.
        if merged and top_k > 0:
            best = merged[0].get("distance", 0.0) or 0.0
            margin = float(os.getenv("RAG_MAX_DISTANCE_MARGIN", "0.25"))
            merged = [h for h in merged if (h.get("distance", 1.0) - best) <= margin]

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