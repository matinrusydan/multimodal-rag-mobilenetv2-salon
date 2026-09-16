"""Prompt builder for hair consultation — port of `apps/api/src/rag/promptBuilder.ts`.
Returns a list of {"role": "system"|"user", "content": str} messages (provider-agnostic).
"""

from __future__ import annotations

from typing import Optional

from app.rag.retriever import RetrievedDoc


def _format_docs(docs: list[RetrievedDoc]) -> str:
    parts: list[str] = []
    for i, d in enumerate(docs, start=1):
        is_web = d.file.startswith("web:")
        src = "Alodokter (web)" if is_web else (f"{d.file}#{d.section}" if d.section else d.file)
        # Konten web berisi artikel panjang → beri ruang lebih besar.
        limit = 1100 if is_web else 400
        snippet = (d.snippet or "")[:limit]
        parts.append(f"[{i}] {src}\n{snippet}".strip())
    return "\n\n---\n\n".join(parts)


def build_prompt(
    query: str,
    docs: list[RetrievedDoc],
    hair_context: Optional[dict] = None,
    hair_features: Optional[dict] = None,
    web_sources: list[dict] | None = None,
) -> list[dict]:
    system = (
        'Kamu adalah asisten konsultasi rambut "TIEN SALON", sebuah salon rambut di Indonesia. '
        "Jawab selalu dalam Bahasa Indonesia yang ramah, jelas, dan TERSTRUKTUR. "
        "ATURAN FORMAT: jawab langsung tanpa sapaan berulang (tidak perlu 'Halo'/'Terima kasih'). "
        "Gunakan poin-poin bersingkat (•) untuk daftar, maksimal ~180 kata. "
        "Pisahkan paragraf dengan baris kosong agar mudah dibaca. "
        "\n\nATURAN ANTI-HALUSINASI (SANGAT PENTING):\n"
        "- JANGAN mengklaim kondisi rambut pelanggan (mis. rambut kering, rusak, bleaching, berminyak) "
        "KECUALI data tersebut diberikan eksplisit di bagian 'KONTEKS RAMBUT' atau 'FITUR RAMBUT' di bawah.\n"
        "- Jika bagian KONTEKS/FITUR RAMBUT tidak ada, JANGAN membahas kondisi rambut pelanggan sama sekali. "
        "Jangan mengarang 'analisis kesehatan rambut' atau seolah-olah ada hasil pemeriksaan/analisis foto.\n"
        "- JANGAN menambahkan diagnosis atau istilah medis yang tidak ada di dokumen yang diberikan.\n"
        "- JANGAN mengasumsikan pelanggan melakukan bleaching/pewarnaan tertentu bila tidak disebutkan.\n"
        "- Sebutkan sumber hanya untuk informasi yang benar-benar diambil dari dokumen "
        "(mis. 'menurut Alodokter, ...' bila isinya memang dari konten Alodokter).\n\n"
        "Gunakan informasi dari dokumen yang diberikan. Dokumen bisa berasal dari knowledge base "
        "salon (layanan, harga, booking) DAN dari konten web Alodokter (kesehatan rambut). "
        "Pakai data salon untuk detail layanan/harga/booking, dan pakai konten Alodokter HANYA bila "
        "pertanyaan pelanggan memang menyangkut kesehatan rambut. "
        "Jangan menempelkan teks mentah dari sumber — rangkum dengan kalimatmu sendiri. "
        "Jangan menampilkan URL/link di dalam jawaban. "
        "Jika informasi tidak tersedia, katakan bahwa Anda perlu konfirmasi langsung ke salon. "
        "Jangan mengarang nomor telepon, alamat, harga, atau kebijakan yang tidak ada di dokumen."
    )

    parts: list[str] = []

    if hair_context:
        parts.append(
            "KONTEKS RAMBUT PELANGGAN (dari analisis foto yang DIUNGGAH pelanggan — ini SATU-SATUNYA "
            f"data kondisi rambut yang valid): panjang={hair_context.get('hairLength')}; jenis={hair_context.get('hairType')}."
        )

    if hair_features:
        feat_bits = []
        if hair_features.get("color"):
            feat_bits.append(f"warna={hair_features['color']}")
        if hair_features.get("texture"):
            feat_bits.append(f"tekstur={hair_features['texture']}")
        # 'health' hanya berarti bila bukan placeholder "tidak-diketahui".
        health = hair_features.get("health")
        if health and health not in ("tidak-diketahui", "normal"):
            feat_bits.append(f"kondisi={health}")
        if feat_bits:
            parts.append(
                "(Perkiraan kasar dari analisis foto, bukan diagnosis): "
                + "; ".join(feat_bits)
                + ". Sampaikan sebagai perkiraan, bukan kepastian."
            )
        risk = hair_features.get("riskSigns") or {}
        if risk.get("bleach") or risk.get("dry"):
            flags = []
            if risk.get("bleach"):
                flags.append("indikasi pewarnaan/bleaching keras")
            if risk.get("dry"):
                flags.append("indikasi rambut cenderung kering")
            parts.append(
                "PERINGATAN (INDIKASI dari analisis foto, bukan diagnosis): "
                + "; ".join(flags)
                + ". Bila pelanggan menanyakan smoothing/rebonding, berikan disclaimer bahwa "
                "hasil bisa bervariasi, risiko kerusakan lebih tinggi, serta sarankan konsultasi "
                "& uji keamanan langsung dengan stylist TIEN SALON."
            )

    parts.append(
        "INSTRUKSI FORMAT: jawab langsung tanpa sapaan berulang, gunakan poin bila perlu, maksimal ~180 kata."
    )

    formatted = _format_docs(docs)
    if formatted:
        parts.append(f"DOKUMEN (sumber jawaban — gabungan KB salon & konten web):\n\n{formatted}")
    else:
        parts.append("TIDAK ADA DOKUMEN yang terambil. Bila tidak ada dokumen, jawab seadanya dan sarankan menghubungi salon.")

    parts.append(f"PERTANYAAN PELANGGAN: {query}")

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(parts)},
    ]