# 02 — Setup

Panduan development monorepo pnpm + Turbo. Produksi memakai prosedur terpisah di
[23-deployment-rag-only.md](./23-deployment-rag-only.md).

## 1. Prasyarat

| Tool | Versi | Catatan |
|---|---|---|
| Node.js | 22.x | Sama dengan konfigurasi hosting |
| pnpm | 10.15.1 | Pin `packageManager` root |
| PostgreSQL | 14+ | Database aplikasi/RBAC |
| Python | 3.13 | Profil RAG minimal; snapshot dependensi berasal dari 3.13.3 |
| Turbo | devDependency | Tidak perlu instal global |

Workspace berisi `apps/*` dan `packages/*`. Jalankan perintah dari root kecuali dinyatakan lain.
Pada Windows gunakan `127.0.0.1` untuk koneksi lokal.

## 2. Instalasi JavaScript

```powershell
pnpm install
```

Konfigurasi Biome: single quotes, indentasi 2 spasi, trailing commas, lebar 100 karakter.
Jangan menjalankan lint, migrasi, seed, atau db:repair tanpa konfirmasi.

## 3. Konfigurasi lokal

Siapkan sendiri file berikut dari contoh yang sesuai; jangan commit secret:

| File lokal | Nilai penting |
|---|---|
| `apps/api/.env` | DATABASE_URL, JWT_SECRET, AI_URL, AI_INTERNAL_TOKEN, CORS_ORIGIN |
| `apps/web/.env.local` | BACKEND_URL, SESSION_SECRET |
| `apps/ai/.env` | Provider/model ChatGPT, profil BM25, corpus runtime, katalog live, internal token |

Contoh koneksi lokal: `BACKEND_URL=http://127.0.0.1:4000`,
`AI_URL=http://127.0.0.1:5000`, `API_BASE_URL=http://127.0.0.1:4000`.
Internal token Express dan AI harus sama. BACKEND_URL dan SESSION_SECRET **server-side only**;
browser memakai route handler same-origin Next.js, bukan NEXT_PUBLIC_API_URL.

Profil operasional yang dipilih:

```dotenv
AI_LLM_PROVIDER=chatgpt
# Isi slug model yang diizinkan grant aplikasi.
AI_CHATGPT_MODEL=
RAG_RETRIEVAL_PROVIDER=bm25_source_balanced
RAG_LIVE_SERVICES=true
RAG_CONTEXT_SELECTION=source_scoped
RAG_RUNTIME_CORPUS_FILE=./rag/runtime/curated-care-v1/corpus.json
```

Path corpus relatif di atas diasumsikan dari `apps/ai`. Ikuti
[19-finalisasi-rag-dan-operasional.md](./19-finalisasi-rag-dan-operasional.md) untuk profil
minimal, setup izin ChatGPT, dan preflight. Default kode Gemini/Chroma tidak otomatis memilih
profil tersebut. `start:rag` hanya memilih entrypoint.

`app.rag_app:app` adalah runtime ringan; `app.main:app` alias kompatibilitas ke aplikasi sama.
Analisis foto unavailable. Tidak perlu model ONNX/Playwright untuk menjalankan profil minimal.
Implementasi CV dan skrip eksperimen tetap tersimpan, bukan dihapus atau dilatih ulang.

## 4. Python dan interpreter

Contoh Windows untuk environment RAG minimal:

```powershell
python -m venv apps/ai/.venv
apps/ai/.venv/Scripts/python.exe -m pip install -r apps/ai/requirements-rag.lock.txt
# pytest tidak termasuk dependency runtime minimal; pasang terpisah untuk pengujian.
```

Script pnpm AI memakai `apps/ai/.venv/Scripts/python.exe`, bukan `.venv-rag` atau interpreter
PATH secara otomatis. Dependensi penuh/eksperimen terdapat pada `requirements.txt` dan
instruksi penelitian terkait. Snapshot minimal Windows bukan bukti dependensi Linux teruji.

## 5. Database

Siapkan PostgreSQL dan pastikan DATABASE_URL menunjuk database development yang benar.
Migrasi/seed adalah langkah manual setelah konfirmasi operator:

```powershell
# Hanya setelah target database dan konsekuensinya disetujui.
pnpm migrate
pnpm seed
```

Seed demo memiliki akun/password hardcoded: **jangan gunakan unchanged pada produksi**.
Tidak ada seed atau migrasi otomatis saat startup. `db:repair` juga bukan pemeriksaan read-only.
Lihat runbook deployment untuk gate bootstrap RBAC/admin/katalog produksi.

## 6. Menjalankan aplikasi

```powershell
# Seluruh aplikasi, termasuk AI.
pnpm local

# Alternatif: jalankan masing-masing pada terminal terpisah, bukan bersamaan dengan local.
pnpm --filter web dev
pnpm --filter api dev
pnpm --filter ai start:rag
```

Port lokal lazim web/API/AI: 3000/4000/5000. Script dev menggunakan `freeport.mjs`, yang bisa
menghentikan proses lain pada port tersebut. Jangan sekaligus menjalankan `pnpm local` dan
`pnpm ai`, atau dua entrypoint AI pada port sama. Hosting memakai production start/Docker,
bukan freeport atau venv Windows.

## 7. Pemeriksaan aman dan tes

```powershell
pnpm --filter api typecheck
pnpm --filter web typecheck
pnpm --filter web test
pnpm --filter web build
pnpm test:rag
```

Tes API terisolasi yang baru tidak memakai DB dan harus dipanggil eksplisit:

```powershell
pnpm --filter api exec vitest run tests/deployment-env-isolated.test.ts tests/deployment-routes-isolated.test.ts tests/deployment-proxy-isolated.test.ts
```

**Jangan menjalankan root `pnpm test` atau `pnpm test:api` sembarangan.** Helper prepareDb()
memakai DATABASE_URL biasa untuk migration down/up/seed. Suite terkait memerlukan database
disposable dan konfirmasi. Health liveness `/api/health` tidak memeriksa DB;
`/api/ready` yang memeriksa koneksinya. `/ai/ready` memeriksa konfigurasi/corpus/session lokal
dan katalog, tanpa generasi model; tidak membuktikan inferensi berhasil.

## 8. Profil legacy/eksperimen

Gemini/Chroma, Crawl4AI offline, dan skrip penelitian masih tersedia untuk kebutuhan terdahulu,
bukan syarat runtime RAG minimal. Jangan menjalankan crawl/reingest untuk memperbarui BM25:
corpus BM25 harus dibuat sebagai bundle baru dengan manifest/checksum yang valid. Knowledge CRUD
legacy juga tidak mengubah bundle runtime aktif.

Web fallback operasional memakai HTTP terbatas/allowlist, bukan browser Playwright atau bypass
anti-bot. Jangan mencampur konfigurasinya dengan crawler offline lama. Pada runtime BM25 minimal,
endpoint crawl/reingest legacy mengembalikan unavailable terkontrol.

Lihat [arsitektur](./01-arsitektur.md), [operasional RAG](./19-finalisasi-rag-dan-operasional.md),
dan [deployment](./23-deployment-rag-only.md). Untuk pekerjaan penelitian CV, roadmap
[08-roadmap-cv-lengkap.md](./08-roadmap-cv-lengkap.md) tetap acuan tertinggi.
