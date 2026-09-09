# AGENTS.md — Panduan untuk Agent

## Status Repository

Saat ini repo hanya berisi `PRD.md` dan `.gitignore`. Kode belum ada — arsitektur berikut adalah rencana yang belum diimplementasi.

## Sumber Kebenaran

Baca `docs/PRD.md` (atau root `PRD.md` saat ini) untuk memahami keseluruhan sistem. Setiap keputusan arsitektur, label klasifikasi, dan spesifikasi ada di sana.

## Arsitektur yang Direncanakan

Monorepo dengan dua paket utama:

- `backend/` — FastAPI (Python 3.10+), MobileNetV2 CV pipeline, RAG pipeline (ChromaDB + GPT-4o-mini)
- `frontend/` — React 18 + Vite 5 + Tailwind CSS 3

## Label Klasifikasi Tetap

**Panjang rambut** (4 kelas): pendek, pendek-menengah, menengah, panjang

**Jenis rambut** (4 kelas): lurus, bergelombang, keriting, sangat-keriting

Label ini berulang di seluruh pipeline — CV, RAG prompt, dan UI. Nama kelas tidak boleh diubah sembarangan.

## API Endpoints

| Endpoint | Metode | Fungsi |
|---|---|---|
| `/api/analyze` | POST | Upload foto → hasil klasifikasi CV |
| `/api/chat` | POST | Kirim pesan → respons chatbot RAG |
| `/api/health` | GET | Health check |

## Environment Variables

### Backend
```
OPENAI_API_KEY=sk-...
CHROMA_PERSIST_DIR=./chroma_db
MODEL_LENGTH_PATH=./cv/weights/hair_length.pth
MODEL_TYPE_PATH=./cv/weights/hair_type.pth
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### Frontend
```
VITE_API_URL=http://localhost:8000
```

## Keputusan Arsitektur Kunci

- CV: PyTorch + MobileNetV2, input 224×224, normalisasi ImageNet
- RAG: ChromaDB (persistent), embedding `text-embedding-3-small` (OpenAI, 1536d), top_k=5
- LLM: GPT-4o-mini, temperature 0.7, max_tokens 1000
- Chunk size: 500-1000 token, overlap 100 token

## Konvensi

- **Bahasa**: user-facing content (UI, knowledge base, error message) wajib Bahasa Indonesia. Kode dan komentar dalam Bahasa Inggris.
- **Keamanan**: API key OpenAI hanya di `.env`. Jangan commit.
- **Scale**: ini adalah prototip/skripsi. Jangan over-engineer.

## Referensi

- `docs/PRD.md` — Product Requirements Document lengkap
- `docs/proposal-skripsi.md` — Proposal skripsi (jika ada)
