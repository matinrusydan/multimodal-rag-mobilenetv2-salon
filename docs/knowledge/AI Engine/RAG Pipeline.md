# AI Engine — RAG Pipeline

Audit statis: **6 November 2026**. Runtime kanonikal `app.main:app` saat ini sama dengan `app.rag_app:app` dan memasang health, chat, agent, serta knowledge; CV tidak dipasang.

## Alur konsultasi

```text
POST /api/chat (Express)
  → validasi + rate limit
  → POST /ai/chat (FastAPI, internal token)
  → RagService.answer()
      ├─ operasi katalog deterministik bila pertanyaan harga/durasi/daftar
      ├─ load runtime corpus
      ├─ retrieval BM25 atau provider terkonfigurasi
      ├─ evidence/context selection
      ├─ kebijakan ambiguitas dan scope
      ├─ generasi ChatGPT/Gemini sesuai konfigurasi
      └─ fallback kutipan bila generasi gagal
  → reply + sources + contextId
```

`contextId` adalah hash query, identitas dokumen dan konteks rambut. Ia bukan conversation history. Route chat tidak menerima/meneruskan seluruh histori percakapan.

## Komponen penting

| Lokasi | Fungsi |
|---|---|
| `app/routers/chat.py` | Kontrak request/response chat dan penanganan corpus unavailable. |
| `app/rag/rag_service.py` | Orkestrasi retrieval, katalog, prompt, model dan fallback. |
| `app/rag/corpus_loader.py` | Memuat dan memvalidasi corpus runtime. |
| `app/rag/retriever.py` | Abstraksi retrieval aktif. |
| `app/rag/bm25_retrieval.py`, `lexical_index.py` | Retrieval leksikal BM25 dan indeks/cache. |
| `app/rag/live_services.py` | Client katalog aktif dari Express `/api/services`. |
| `catalog_operations.py` | Daftar, filter, harga, durasi dan perbandingan deterministik. |
| `evidence_selection.py`, `context_selection.py` | Seleksi sumber dan span konteks. |
| `care_intent.py`, `answer_policy.py`, `scope_policy.py` | Klarifikasi, batas klaim dan aturan jawaban. |
| `prompt_builder.py` | Prompt dari evidence terpilih. |
| `chatgpt_plan.py` | Integrasi ChatGPT melalui login aplikasi sendiri. |
| `web_fallback.py`, `web_fetch.py` | Fallback web terbatas; default environment menonaktifkannya. |

## Pemisahan fakta bisnis dan edukasi

Harga/durasi/daftar layanan yang didukung harus berasal dari katalog live, bukan similarity search atau snapshot corpus. Konten edukasi mengambil bukti corpus terkurasi. Jika katalog gagal, sistem tidak boleh mengarang harga dari dokumen lama.

## Profil dan konfigurasi

- Default contoh: `AI_LLM_PROVIDER=chatgpt`, `RAG_RETRIEVAL_PROVIDER=bm25_source_balanced`, `RAG_LIVE_SERVICES=true`.
- Cabang Gemini/vector masih ada untuk kompatibilitas/eksperimen, tetapi keberadaannya tidak berarti semua provider aktif bersamaan.
- Corpus runtime berada di `apps/ai/rag/runtime/`; artefak evaluasi ada di `apps/ai/rag/eval/`.
- Login, model access, quota dan inference permission harus diperiksa di target environment; subscription bukan bukti izin deployment.

## Bukti evaluasi dan batasnya

Artefak `quality-development-offline-v5`, `quality-resume-v1`, dan `ambiguity-v1` adalah hasil historis versi tertentu. Ia tidak membuktikan versi source saat ini lulus. Test ambiguitas/rute tidak menggantikan evaluasi semantik independen.

Pekerjaan terbuka:

1. Pengesahan manusia untuk evidence dan jawaban acuan development.
2. Test independen terkunci yang tidak dipakai menyetel aturan.
3. Baseline generatif berpasangan dan judge yang tidak identik dengan generator bila memungkinkan.
4. Penambahan sumber/SOP salon berizin.
5. Evaluasi ulang source aktif dan smoke test deployment.

Lihat [TASK](../TASK.md) dan dokumen historis `docs/18`–`docs/23`.
