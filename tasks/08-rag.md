# Task — Phase 08: Membangun RAG Pipeline (ChromaDB + OpenAI)

> Sebelumnya: Phase 06 website + Phase 07 CV selesai.
> Referensi: `docs/01-arsitektur.md §3`, `docs/03-backend.md §9`, `PRD.md`.
> Terpisah dari Case 07: fase ini hanya **RAG**; CV ada di **`tasks/07-cv.md`**, deployment di **`tasks/09-deployment.md`**.

**Tujuan**: Mengimplementasikan pipeline **Retrieval-Augmented Generation** (ChromaDB + OpenAI) menggantikan skeleton dari Phase 05, sehingga `POST /api/chat` menjawab berdasar knowledge base + konteks CV (multimodal). Halaman `/consult` (Phase 06) berfungsi penuh.

---

## 1. Embedding & Vector Store

- [x] `rag/embedding.ts` — `text-embedding-3-small` (**1536d**), singleton client.
- [x] `rag/vectorStore.ts` — ChromaDB **persistent** (server via `CHROMA_URL=127.0.0.1:8000`; persist dir sisi server `CHROMA_PERSIST_DIR=./chroma_db`).
- [x] Inisialisasi collection per-topic: harga, layanan, gaya-rambut, tips-perawatan, booking-info.

## 2. Ingestion & Chunking Knowledge Base

- [x] Sumber: `apps/api/rag/knowledge/*.md` (Bahasa Indonesia) — harga, layanan, gaya-rambut, tips-perawatan, booking-info.
- [x] `rag/chunker.ts` — chunk size **500–1000 token**, overlap **100**; pemisahan rapi per bagian dokumen (jangan potong di tengah kalimat).
- [x] `rag/ingest.ts` — jalankan sekali: `pnpm rag:ingest` (parse markdown → chunk → embed → upsert ke ChromaDB dengan `metadata::{file, section, topic, hash}`).
- [x] Idempotent: skip/replace embed bila dokumen sumber berubah (hash konten di id chunk `file#hash#index`).

## 3. Retrieval & Prompt Building

- [x] `rag/retriever.ts` — cosine similarity antar semua topic digabung, **`top_k = 5`** (distance naik).
- [x] `rag/promptBuilder.ts` — compose: system prompt (TIEN SALON, Bahasa Indonesia, format jawaban) + `retrieved docs` (dengan source) + **`hair_context` dari CV** (length, type; hair_features siap disambungkan) + user query.
- [x] Peringatan risiko: bila `hairFeatures.riskSigns` menunjukkan tanda **bleaching/kering** → prompt menginstruksikan disclaimer rekomendasi smoothing/rebonding (sesuai keputusan warna=kunci).
- [x] LLM callback: **GPT-4o-mini**, temperature **0.7**, `max_tokens` **1000**.

## 4. Integrasi Backend — `ChatService.ts`

- [x] `POST /api/chat` menerima `{ message, hairContext?, contextId? }`; foto dianalisis via `POST /api/analyze` (CV Phase 07) → `hair_context` dikirim sebagai `hairContext`.
- [x] Respons: `{ reply, sources[], contextId }` — `contextId` (hash query+konteks) untuk caching opsional.
- [x] Ganti stub placeholder dengan pipeline nyata; rate-limit tetap (mencegah abuse biaya OpenAI).

## 5. Optimasi & Verifikasi

- [x] Rate-limit `/api/chat` & `/api/analyze` efektif (terlihat di header `ratelimit`; smoke terbukti).
- [ ] Cache similarity untuk query berulang (opsional).
- [x] Unit test: chunking (batas token + overlap), retrieval `top_k`, prompt build (order benar, no-sys-inject, disclaimer).
- [x] Integration: `pnpm rag:ingest` → 37 chunk terembed (idempotent: run-2 `upsert=0`) → query muncul di `sources`.
- [x] Smoke: `POST /api/chat` → jawaban dari knowledge base + 5 sumber + `contextId`; status 200; rate-limit aktif.
- [ ] Smoke penuh dengan OpenAI asli saat kredit tersedia (`RAG_EMBEDDING_PROVIDER=openai`): konteks rambut CV benar-benar dipakai + disclaimer bleaching.
- [x] `pnpm test:api` hijau (47/47); `pnpm build` & `pnpm lint` lolos.

> **Catatan**: seed embedding memakai OpenAI (biaya kecil, 1536d). Jalankan `ingest` setelah knowledge base final — jalankan `pnpm rag:ingest` saat server ChromaDB aktif (`chroma run --path ./chroma_db`). Bila nanti model berubah (embedding/LLM), re-embed collection (`rag:ingest --force`).