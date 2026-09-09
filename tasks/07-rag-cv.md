# Task — Phase 07: Membangun RAG + CV Pipeline

> Sebelumnya: Phase 06 website selesai (frontend terintegrasi; analyze/chat masih placeholder).
> Referensi: `docs/01-arsitektur.md §3`, `docs/03-backend.md §8-9`, `PRD.md`.

**Tujuan**: Mengimplementasikan pipeline **RAG** (ChromaDB + OpenAI) dan **CV** (MobileNetV2) yang sebenarnya, menggantikan skeleton dari Phase 05, sehingga halaman `/consult` (Phase 06) berfungsi nyata.

---

## 1. CV Pipeline (MobileNetV2 → ONNX, Node inference)

> **Keputusan final (Opsi A)**: model PyTorch `.pth` di-**export ke ONNX** sekali (proses offline di Python), lalu **Node (`onnxruntime-node`)** melakukan inference dari foto baru. **Tanpa service Python terpisah** — satu service Express (deploy Railway) handle CV + RAG + chat.

- [ ] Siapkan model MobileNetV2 (PyTorch `.pth`) di environment Python offline (catatan training, tidak di repo).
- [ ] Export ke ONNX (proses offline/once): jalankan script Python `export_to_onnx.py` → hasil `.onnx` di `apps/api/cv/weights/` (di-gitignore; pastikan artefak tidak ter-commit bila besar).
- [ ] Preprocessing (di Node): decode image → resize 224×224 → normalize `mean=[0.485,0.456,0.406]`, `std=[0.229,0.224,0.225]` (CHW uint8/float sesuai input model ONNX).
- [ ] Inference via `onnxruntime-node`: feed tensor → hasil logits → softmax → label + confidence.
- [ ] Label mapping tetap (dari PRD):
  - panjang: `pendek`, `pendek-menengah`, `menengah`, `panjang`
  - jenis: `lurus`, `bergelombang`, `keriting`, `sangat-keriting`
- [ ] Threshold `CONFIDENCE_THRESHOLD` (< 0.5 → `low_confidence`).
- [ ] `CvService` memanggil pipeline ONNX; `POST /api/analyze` mengembalikan hasil asli (ganti placeholder).
- [ ] Pastikan `onnxruntime-node` native binding bekerja di environment target (Railway = Linux); test inference lokal dulu.

## 2. RAG Pipeline (ChromaDB + OpenAI)

- [ ] `rag/embedding.ts` — `text-embedding-3-small` (1536d).
- [ ] `rag/vectorStore.ts` — ChromaDB persistent (`CHROMA_PERSIST_DIR`).
- [ ] Ingestion knowledge base `rag/knowledge/*.md` (harga, layanan, gaya-rambut, tips-perawatan, booking-info).
- [ ] Chunking: size 500–1000 token, overlap 100.
- [ ] Retrieval: cosine similarity, `top_k = 5`.
- [ ] `rag/promptBuilder.ts` — system + retrieved docs + `hair_context`(CV) + user query.
- [ ] LLM callback: GPT-4o-mini, temperature 0.7, max_tokens 1000.
- [ ] `ChatService` memanggil pipeline; `POST /api/chat` mengembalikan reply asli + `sources` + `contextId` (ganti placeholder).

## 3. Integrasi Multimodal

- [ ] Hasil CV (`hair_length` + `hair_type`) dimasukkan ke konteks chat (`hairContext`).
- [ ] Halaman `/consult`: setelah upload & analyze, hasil CV otomatis membekali jawaban chatbot berikutnya.
- [ ] Pastikan temperature & safety tidak melebihi token limit.

## 4. Optimasi & Rate-Limit

- [ ] Rate-limit pada `/api/analyze` & `/api/chat` efektif (mencegah abuse biaya OpenAI).
- [ ] Cache similarity (opsional) untuk query berulang.

## 5. Verifikasi

- [ ] Unit test CV: preprocessing + label mapping + confidence.
- [ ] Unit/integration test RAG: chunking, retrieval top_k, prompt build.
- [ ] Smoke test: upload foto → hasil klasifikasi nyata; tanya ke chatbot → jawaban sesuai knowledge base + konteks rambut.
- [ ] `pnpm test:api` hijau; `pnpm build` & `pnpm lint` lolos.

> **Catatan**: metode CV final = **ONNX + onnxruntime-node** (keputusan user). Divergence dari docs/03 (yang menulis PyTorch `.pth` langsung) — docs akan diperbarui bila perlu. Model `.onnx`/weights tidak di-commit bila ukuran besar (daftar di `.gitignore`, taruh artefak via env path).
