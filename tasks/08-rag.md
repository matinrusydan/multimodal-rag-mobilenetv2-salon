# Task — Phase 08: Membangun RAG Pipeline (ChromaDB + OpenAI)

> Sebelumnya: Phase 06 website + Phase 07 CV selesai.
> Referensi: `docs/01-arsitektur.md §3`, `docs/03-backend.md §9`, `PRD.md`.
> Terpisah dari Case 07: fase ini hanya **RAG**; CV ada di **`tasks/07-cv.md`**, deployment di **`tasks/09-deployment.md`**.

**Tujuan**: Mengimplementasikan pipeline **Retrieval-Augmented Generation** (ChromaDB + OpenAI) menggantikan skeleton dari Phase 05, sehingga `POST /api/chat` menjawab berdasar knowledge base + konteks CV (multimodal). Halaman `/consult` (Phase 06) berfungsi penuh.

---

## 1. Embedding & Vector Store

- [ ] `rag/embedding.ts` — `text-embedding-3-small` (**1536d**), singleton client.
- [ ] `rag/vectorStore.ts` — ChromaDB **persistent** (`CHROMA_PERSIST_DIR=./chroma_db`, default `apps/api/chroma_db`).
- [ ] Inisialisasi collection per-topic: harga, layanan, gaya-rambut, tips-perawatan, booking-info.

## 2. Ingestion & Chunking Knowledge Base

- [ ] Sumber: `apps/api/rag/knowledge/*.md` (Bahasa Indonesia) — harga, layanan, gaya-rambut, tips-perawatan, booking-info.
- [ ] `rag/chunker.ts` — chunk size **500–1000 token**, overlap **100**; pemisahan rapi per bagian dokumen (jangan potong di tengah kalimat).
- [ ] `rag/ingest.ts` — jalankan sekali (script/CLI): parse markdown → chunk → embed → upsert ke ChromaDB dengan `metadata::{file, section}`.
- [ ] Idempotent: skip/replace embed bila dokumen sumber berubah (hash).

## 3. Retrieval & Prompt Building

- [ ] `rag/retriever.ts` — cosine similarity, **`top_k = 5`**.
- [ ] `rag/promptBuilder.ts` — compose: system prompt (TIEN SALON, Bahasa Indonesia, format jawaban) + `retrieved docs` (dengan source) + **`hair_context` dari CV** (length, type, hair_features incl. warna/kondisi) + user query.
- [ ] Peringatan risiko: bila `hair_features` menunjukkan tanda **bleaching/kering** → prompt menginstruksikan disclaimer rekomendasi smoothing/rebonding (sesuai keputusan warna=kunci).
- [ ] LLM callback: **GPT-4o-mini**, temperature **0.7**, `max_tokens` **1000**.

## 4. Integrasi Backend — `ChatService.ts`

- [ ] `POST /api/chat` menerima `{ message, hairContext?, image? }`; bila ada foto → panggil CV (Phase 07) untuk `hair_context`.
- [ ] Respons: `{ reply, sources[], contextId }` — `contextId` (hash query+context) untuk caching opsional.
- [ ] Ganti stub placeholder dengan pipeline nyata; rate-limit tetap (mencegah abuse biaya OpenAI).

## 5. Optimasi & Verifikasi

- [ ] Rate-limit `/api/chat` & `/api/analyze` efektif.
- [ ] Cache similarity untuk query berulang (opsional).
- [ ] Unit test: chunking (batas token + overlap), retrieval `top_k`, prompt build (order benar, no-sys-inject).
- [ ] Integration test: ingest docs → query → sumber relevan muncul di `sources`.
- [ ] Smoke: tanya chatbot → jawaban dari knowledge base + konteks rambut (hasil CV); verifikasi disclaimer bleaching.
- [ ] `pnpm test:api` hijau; `pnpm build` & `pnpm lint` lolos.

> **Catatan**: seed embedding memakai OpenAI (biaya kecil, 1536d). Jalankan `ingest` setelah knowledge base final. Bila nanti model berubah (embedding/LLM), re-embed collection.