# RAG-Salon — Multimodal RAG + Computer Vision (Salon)

Project penelitian/skripsi: sistem **multimodal** yang menggabungkan **Computer Vision (CV)** untuk
analisis foto rambut dan **Retrieval-Augmented Generation (RAG)** untuk konsultasi berbasis
pengetahuan salon. Fokus penelitian ada di **CV & RAG**; aplikasi web/admin berfungsi sebagai
wadah demo & integrasi end-to-end.

> Dokumen analisis CV & RAG untuk bimbingan TA: **[`docs/09-analisis-cv-rag.md`](docs/09-analisis-cv-rag.md)**
> Diagram arsitektur: **[`docs/diagrams/`](docs/diagrams/)**

---

## 1. Arsitektur Singkat

Monorepo **pnpm + Turbo** dengan 3 app:

| App | Stack | Port | Peran |
|---|---|---|---|
| `apps/web` | Next.js 16 (App Router) | 3000 | Landing page, reservasi, panel admin |
| `apps/api` | Express + TypeScript + Knex/PostgreSQL | 4000 | REST API, RBAC, proxy ke brain engine |
| `apps/ai` | FastAPI (Python) | 5000 | **Brain engine**: CV (ONNX) + RAG (ChromaDB + Gemini) + Crawler |

```
Next.js (3000) ──▶ Express (4000) ──▶ FastAPI (5000)
                       │                    ├── CV   : MobileNetV2 ONNX + MediaPipe (viewpoint gate)
                       │                    └── RAG  : ChromaDB + Gemini embed/LLM
                       └── PostgreSQL (5432)
```

---

## 2. Prasyarat

- **Node.js ≥ 20** + **pnpm 10** (`npm i -g pnpm`)
- **Python 3.12/3.13** (venv di `apps/ai/.venv`)
- **PostgreSQL 17** berjalan di `127.0.0.1:5432` (database `rag_salon`)
- (Opsional) **Graphviz** untuk regenerasi diagram — lihat `docs/diagrams/README`.

---

## 3. Menjalankan Website

```bash
# dari root
pnpm install

# jalankan semua app (web :3000, api :4000, ai :5000) via Turbo
pnpm dev          # = pnpm local

# atau jalankan FastAPI brain engine saja
pnpm ai
```

> `pnpm ai` (dan `pnpm dev`) otomatis **membebaskan port** yang dipakai sebelum start
> (via `scripts/freeport.mjs`), jadi tidak lagi error `WinError 10048` kalau ada instance
> lama yang masih jalan.

Kalau ingin terpisah (disarankan saat debug):

```bash
# Terminal 1 — backend API
cd apps/api && pnpm dev            # http://127.0.0.1:4000

# Terminal 2 — web
cd apps/web && pnpm dev            # http://127.0.0.1:3000
```

**Akun demo** (seed): `admin@rag-salon.id` / `Password123!` (superadmin).

---

## 4. Menjalankan FastAPI (Brain Engine) — CV & RAG

```bash
cd apps/ai

# pastikan venv & dependency
.venv\Scripts\python.exe -m pip install -r requirements.txt

# jalankan server
.venv\Scripts\python.exe -m uvicorn app.main:app --port 5000 --host 127.0.0.1
# atau dari root: pnpm ai
```

Endpoint utama:

| Endpoint | Fungsi |
|---|---|
| `GET /ai/health` | Health check |
| `POST /ai/analyze` | **CV**: analisis foto rambut (viewpoint → type → length) |
| `POST /ai/chat` | **RAG**: konsultasi pelanggan (ChromaDB + Gemini) |
| `POST /ai/agent` | Agent admin (RAG katalog + tool-call data live) |
| `GET /ai/knowledge` | Kelola dokumen knowledge base `.md` |

Environment penting di `apps/ai/.env`: `GEMINI_API_KEY`, `API_BASE_URL`, `AI_INTERNAL_TOKEN`,
`CHROMA_PERSIST_DIR`, `CRAWL_TIPS_URLS`.

**Ingest / crawl knowledge base RAG:**

```bash
pnpm rag:ingest        # ingest app/rag/knowledge/*.md -> ChromaDB
pnpm crawl:tips        # crawl sumber tips (alodokter dll) -> knowledge
pnpm rag:sync-catalog  # serialize katalog layanan DB -> ChromaDB (agent admin)
```

---

## 5. Database: migrate, seed, dan REPAIR (menu kembali ke awal)

```bash
pnpm migrate    # jalankan migrasi skema
pnpm seed       # isi data awal (RBAC, menu, layanan, user demo)
```

### ⚠️ Kalau data/menu "hilang" atau kembali ke daftar awal

Gejala: kolom hilang walau migrasi tercatat "applied", `pnpm seed` gagal dengan error
`column "status" does not exist`, sehingga **menu tidak ikut ter-update**.

Perbaikan satu perintah:

```bash
pnpm db:repair
```

`db:repair` akan: (1) hapus record migrasi "reensure" yang bermasalah, (2) jalankan ulang
migrasi untuk memastikan **semua kolom ada**, lalu (3) `seed` ulang. Setelah itu menu/admin
kembali ke struktur yang benar.

Perintah seed granular (bila perlu):

```bash
cd apps/api
pnpm migrate            # migrate:latest
pnpm seed               # semua seed
pnpm db:repair          # repair + migrate + seed
```

> Penyebab umum: `knex_migrations` sinkron tetapi skema DB ter-rollback/restore dari dump lama,
> jadi migrasi tidak dijalankan ulang padahal kolomnya hilang.

---

## 6. Lihat juga

- **Analisis CV & RAG (bahan bimbingan):** [`docs/09-analisis-cv-rag.md`](docs/09-analisis-cv-rag.md)
- **Roadmap CV lengkap:** [`docs/08-roadmap-cv-lengkap.md`](docs/08-roadmap-cv-lengkap.md)
- **Kajian matematis rujukan:** [`docs/06-kajian-matematis-referensi.md`](docs/06-kajian-matematis-referensi.md)
- **Diagram (flowchart & sequence):** [`docs/diagrams/`](docs/diagrams/)
- **README CV modular:** [`apps/api/cv/README.md`](apps/api/cv/README.md)
