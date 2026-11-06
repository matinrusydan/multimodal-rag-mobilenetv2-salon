# Getting Started

Panduan penyiapan lingkungan kerja, konfigurasi, dan perintah eksekusi untuk repositori **RAG-salon**.

Dokumen ini disusun dari audit statis tanggal **6 November 2026**. Instruksi di bawah adalah referensi untuk operator/pengembang; sistem agen tidak diizinkan menjalankan migrasi, seed, atau lint secara otomatis tanpa konfirmasi pengguna.

---

## 1. Prasyarat Sistem

| Komponen | Versi Minimal / Rekomendasi | Catatan |
|---|---|---|
| **Node.js** | `22.x` (LTS) | Diperlukan oleh `apps/web`, `apps/api`, Turbo |
| **pnpm** | `10.15.1` (Package Manager resmi) | Dikonfigurasi pada `package.json` root |
| **Python** | Sesuaikan dengan lock/dependensi dan Dockerfile AI | Diperlukan oleh `apps/ai` (`.venv/`); kompatibilitas lokal belum diuji ulang |
| **PostgreSQL** | `16.x` | Database utama untuk `apps/api` (Knex migration) |
| **Turbo** | `^2.3.3` | Pengelola build monorepo |

---

## 2. Struktur Monorepo dan Port Layanan

Repositori ini adalah monorepo pnpm + Turbo dengan tiga aplikasi dan dua shared package:

| Aplikasi / Paket | Lokasi | Port Default | Peran Utama |
|---|---|---|---|
| **`web`** | `apps/web` | `3000` | Frontend Next.js 16 (App Router), BFF API routes, konsultasi chat UI |
| **`api`** | `apps/api` | `4000` | Backend Express 5 + Knex + PostgreSQL, auth JWT, RBAC, proxy ke AI |
| **`ai`** | `apps/ai` | `5000` | FastAPI brain engine: RAG (BM25 + ChatGPT + live catalog sync) |
| **`shared-types`** | `packages/shared-types` | - | Skema kontrak Zod dan TypeScript types bersama (BE↔FE) |
| **`shared-utils`** | `packages/shared-utils` | - | Helper utilitas format, invoice, permissions |

> **Catatan Pencegahan Port Collision (Windows):** Skrip dev monorepo membungkus pemanggilan port dengan `node ../../scripts/freeport.mjs <port>` untuk mencegah error `WinError 10048` (port terkunci) pada sistem operasi Windows.

---

## 3. Konfigurasi Environment (`.env`)

Template konfigurasi awal tersedia di file root `.env.example` serta berkas example per-aplikasi:
- `apps/web/.env.example`
- `apps/api/.env.example`
- `apps/ai/.env.example`

### Variabel Utama per Aplikasi:

#### a. Backend (`apps/api`)
```ini
PORT=4000
HOST=127.0.0.1
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/rag_salon
JWT_SECRET=change-me-secret-minimum-32-chars
SECURITY_ENFORCE_ENABLED=true
TRUST_PROXY=false
AI_URL=http://127.0.0.1:5000
AI_INTERNAL_TOKEN=change-me-internal-token
CORS_ORIGIN=http://127.0.0.1:3000,http://localhost:3000
```

#### b. AI Brain Engine (`apps/ai`)
```ini
AI_PORT=5000
AI_HOST=127.0.0.1
AI_ENV=development
AI_LLM_PROVIDER=chatgpt          # atau gemini
AI_EMBEDDING_PROVIDER=gemini     # jika vector pipeline diaktifkan
AI_INTERNAL_TOKEN=change-me-internal-token
API_BASE_URL=http://127.0.0.1:4000
RAG_LIVE_SERVICES=true           # sinkronisasi katalog live via API backend
CHROMA_PERSIST_DIR=./chroma_db
```

#### c. Frontend (`apps/web`)
```ini
BACKEND_URL=http://127.0.0.1:4000
SESSION_SECRET=change-me-session-secret-min-32-chars
```

---

## 4. Langkah Instalasi dan Menjalankan Proyek

### 1. Instalasi Dependensi Node.js
```bash
pnpm install
```

### 2. Setup Virtual Environment Python (`apps/ai`)
Pastikan python venv terpasang di `apps/ai/.venv`:
```powershell
cd apps/ai
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ../..
```

### 3. Setup Database (Migrasi & Seed)
> **Peringatan Kebijakan:** Jangan jalankan perintah ini secara otomatis. Pastikan PostgreSQL lokal sudah menyala dan database `rag_salon` telah dibuat.
```bash
pnpm migrate      # Menjalankan migrasi Knex (apps/api)
pnpm seed         # Mengisi data awal (admin, permission, layanan)
# pnpm db:repair  # Skrip perbaikan skema (hanya jika ada desinkronisasi kolom)
```

### 4. Menjalankan Server Pengembangan

- **Menjalankan Seluruh Sistem (Web + API + AI):**
  ```bash
  pnpm local
  # atau
  pnpm dev
  ```
- **Menjalankan AI Brain Engine Saja:**
  ```bash
  pnpm ai
  ```
- **Menjalankan Web Saja:**
  ```bash
  pnpm --filter web dev
  ```
- **Menjalankan Backend API Saja:**
  ```bash
  pnpm --filter api dev
  ```

---

## 5. Profil Runtime AI (`main.py` vs `rag_app.py`)

Berdasarkan audit source kode per **6 November 2026**:
- `apps/ai/app/main.py` secara langsung mengekspor `app` dari `app.rag_app`:
  ```python
  from app.rag_app import app
  __all__ = ['app']
  ```
- Ini berarti runtime kanonikal yang berjalan adalah **RAG-only pipeline**:
  - Router terdaftar: `/ai/health`, `/ai/chat`, `/ai/agent`, `/ai/knowledge`.
  - Router `/ai/analyze` (CV inference) **tidak dipasang** pada web server aktif.
  - Sisi Express (`apps/api/src/routes/analyze.routes.ts`) mengembalikan respons **`503 Service Unavailable`** ("Fitur belum tersedia: Analisis foto belum tersedia").
  - Modul inferensi CV dan bobot ONNX tersimpan secara offline untuk riset lanjutan.

---

## 6. Daftar Perintah Kerja (Root `package.json`)

| Perintah | Deskripsi |
|---|---|
| `pnpm dev` / `pnpm local` | Menjalankan seluruh workspace via Turbo |
| `pnpm ai` | Menjalankan server AI FastAPI saja (port 5000) |
| `pnpm build` | Membangun seluruh paket (web, api, shared) |
| `pnpm lint` | Pengecekan kode menggunakan Biome |
| `pnpm lint:fix` | Perbaikan otomatis Biome |
| `pnpm typecheck` | Pengecekan tipe TypeScript (`tsc --noEmit`) |
| `pnpm test` | Menjalankan seluruh test workspace |
| `pnpm test:api` | Menjalankan test Vitest pada `apps/api` |
| `pnpm test:rag` | Menjalankan test pytest RAG pada `apps/ai` |
| `pnpm test:web` | Menjalankan test Vitest pada `apps/web` |
| `pnpm crawl:site` | Menjalankan crawler lokal untuk knowledge base TIEN Salon |
| `pnpm crawl:tips` | Menjalankan crawler artikel tips perawatan rambut |
| `pnpm rag:ingest` | Melakukan ingest dokumen pengetahuan ke vector store / index |
