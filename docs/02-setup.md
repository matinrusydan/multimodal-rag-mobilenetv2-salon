# 02 — Setup

Dokumen ini menjelaskan prasyarat, instalasi, dan perintah pengembangan untuk monorepo RAG-salon (pnpm + Turbo).

> Status: **Sebagian dibangun** — `apps/api` + `apps/web` sudah berjalan. `apps/ai` (Python) belum diimplementasikan; panduan env & perintah AI sudah final untuk eksekusi.

---

## 1. Prasyarat

| Tool | Versi | Catatan |
|---|---|---|
| Node.js | 18+ (disarankan 20/22 LTS) | Wajib |
| pnpm | 9+ | Package manager |
| PostgreSQL | 14+ | Database RBAC & data |
| **Python** | **3.10+** | **Wajib** — untuk `apps/ai` (FastAPI, onnxruntime, Crawl4AI) |
| Turbo | via devDependency | Dikelola pnpm |

---

## 2. Struktur Workspace

```yaml
# pnpm-workspace.yaml
packages:
  - apps/*
  - packages/*
  - e2e
```

---

## 3. Instalasi

```bash
# dari root repo
pnpm install
```

Ini akan menginstal seluruh workspace (web, api, shared packages).

---

## 4. Variabel Environment

### Untuk `apps/api` (Express)

```env
NODE_ENV=development
PORT=4000
HOST=127.0.0.1

DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/rag_salon
DB_CLIENT=postgres

JWT_SECRET=change-me
JWT_EXPIRES_IN=1d

SECURITY_ENFORCE_ENABLED=true
CORS_ORIGIN=http://localhost:3000
```

### Untuk `apps/ai` (FastAPI Brain Engine)

```env
AI_PORT=5000
AI_HOST=127.0.0.1

# Gemini (embed + LLM)
GEMINI_API_KEY=...

# Embedding & LLM provider
AI_EMBEDDING_PROVIDER=gemini      # "gemini" (gemini-embedding-001, 768d)

AI_LLM_PROVIDER=gemini            # "gemini" (gemini-3.6-flash)
# Fallback berantai saat model utama kena rate-limit/quota (429):
AI_LLM_FALLBACK_MODELS=gemini-3.1-flash-lite,gemini-flash-lite-latest,gemini-3-flash-preview,gemini-flash-latest
AI_LLM_COOLDOWN_SECONDS=120       # lama skip model yang kena 429 (detik)
# ChromaDB
AI_CHROMA_MODE=persistent          # "persistent" | "http"
CHROMA_URL=http://127.0.0.1:8000   # hanya utk mode http
CHROMA_PERSIST_DIR=./chroma_db

# CV models
MODEL_LENGTH_PATH=./cv/weights/hair_length.onnx
MODEL_TYPE_PATH=./cv/weights/hair_type.onnx
CONFIDENCE_THRESHOLD=0.5

# Crawl4AI
CRAWL_BASE_URL=http://127.0.0.1:3000   # situs salon lokal (Next.js dev)
CRAWL_USE_BROWSER=false                  # false=raw HTTP; true=Playwright (SPA)
CRAWL_DELAY_MS=1500
CRAWL_TIPS_URL=https://alodokter.com    # sumber tips eksternal
CRAWL_HEADLESS=false                  # false=bypass anti-bot; true=ringan
WEB_FALLBACK_ENABLED=true             # live crawl alodokter saat query kesehatan rambut
WEB_FALLBACK_MAX_DOCS=2
WEB_CACHE_TTL_SECONDS=3600            # cache hasil crawl (detik)
```

> **Catatan ChromaDB**: mode `persistent` (default) menggunakan ChromaDB embedded tanpa server terpisah — cocok untuk dev lokal. Mode `http` menghubungkan ke ChromaDB server di `CHROMA_URL`.

> **Windows + uvicorn**: `uvicorn --reload` di Windows menggunakan selector loop yang tidak bisa spawn subprocess Playwright. Aliran `web_fallback` otomatis menjalankan crawl di thread terpisah (`asyncio.to_thread`) dengan fresh Proactor loop — tidak perlu konfigurasi tambahan.

### Untuk `apps/web` (Next.js)

```env
BACKEND_URL=http://127.0.0.1:4000       # akses server-side ke API
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:4000  # akses client-side (jarang)
SESSION_SECRET=change-me-session-secret
NEXT_PUBLIC_API_URL=http://127.0.0.1:4000/api
```

> **Windows**: gunakan `127.0.0.1`, bukan `localhost` untuk menghindari kendala bind IPv6.

---

## 5. Perintah Pengembangan

Semua dijalankan dari root repo.

| Tujuan | Perintah |
|---|---|
| Jalankan semua app (dev) | `pnpm local` |
| Jalankan FastAPI brain engine (dev) | `pnpm ai` |
| Migrasi DB | `pnpm migrate` |
| Seed (admin + RBAC) | `pnpm seed` |
| Crawl situs salon → KB | `pnpm crawl:site` |
| Crawl tips eksternal → KB | `pnpm crawl:tips` |
| Ingest KB → ChromaDB | `pnpm rag:ingest` |
| Build semua | `pnpm build` |
| Lint | `pnpm lint` |
| Lint + fix | `pnpm lint:fix` |
| Format | `pnpm format` |
| Format + write | `pnpm format:write` |
| Test API saja | `pnpm test:api` |
| Test Web saja | `pnpm test:web` |
| Test semua | `pnpm test` |
| Tambah dep ke web | `pnpm --filter web add <pkg>` |
| Tambah dep ke api | `pnpm --filter api add <pkg>` |

**Alur setup awal:**

```bash
pnpm install
# setup venv Python di apps/ai
cd apps/ai && python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cd ../..
pnpm migrate
pnpm seed
pnpm local      # (terminal 1: Express + Next)
pnpm ai         # (terminal 2: FastAPI brain engine)
```

---

## 6. Urutan Wire-Up Disarankan untuk Eksekusi

1. Scaffold root (workspace + turbo + biome).
2. `apps/api` — Express app, Knex, migrasi + seed.
3. `packages/shared-types` — Zod schemas.
4. `apps/api` — RBAC middleware + routes.
5. `apps/web` — salin UI `TIEN-SALON-New`, sesuaikan URL EN.
6. `apps/web` — integrasi SSR ke API + halaman konsultasi.
7. `apps/ai` — FastAPI brain engine (CV + RAG + crawler). *(belum dieksekusi)*

---

## 7. Catatan Operasional

- **Jangan jalankan `pnpm lint` global secara sembarangan tanpa perlu** — lint hanya file yang disentuh (pola dashboard-ops).
- **Jangan auto-execute migrasi/seed** tanpa konfirmasi.
- API key Gemini **hanya di `.env`** — jangan commit.
- Model ONNX (`hair_length.onnx`, `hair_type.onnx`) diletakkan di `apps/ai/cv/weights/`.
- Bioma konfigurasi: single quotes, trailing commas, 2-space indent, 100 line width.

---

_Lanjut baca: [03-backend.md](./03-backend.md)_
