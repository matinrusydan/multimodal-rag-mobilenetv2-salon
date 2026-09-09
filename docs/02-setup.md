# 02 — Setup

Dokumen ini menjelaskan prasyarat, instalasi, dan perintah pengembangan untuk monorepo RAG-salon (pnpm + Turbo).

> Status: **Rencana target** — perintah berikut adalah konvensi yang akan diterapkan (pola `dashboard-ops`), bukan yang sudah dieksekusi.

---

## 1. Prasyarat

| Tool | Versi | Catatan |
|---|---|---|
| Node.js | 18+ (disarankan 20/22 LTS) | Wajib |
| pnpm | 9+ (dashboard-ops pakai 10.26.1) | Package manager |
| PostgreSQL | 14+ | Database RBAC & data |
| Python 3.10+ | opsional | Hanya untuk training/ekspor model CV |
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

### Untuk `apps/api`

```env
NODE_ENV=development
PORT=4000
HOST=127.0.0.1

DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/rag_salon
DB_CLIENT=postgres

JWT_SECRET=change-me
JWT_EXPIRES_IN=1d

OPENAI_API_KEY=sk-...
CHROMA_PERSIST_DIR=./chroma_db

MODEL_LENGTH_PATH=./cv/weights/hair_length.pth
MODEL_TYPE_PATH=./cv/weights/hair_type.pth
CONFIDENCE_THRESHOLD=0.5

SECURITY_ENFORCE_ENABLED=true
CORS_ORIGIN=http://localhost:3000
```

### Untuk `apps/web`

```env
BACKEND_URL=http://127.0.0.1:4000       # akses server-side ke API
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:4000  # akses client-side (jarang)
SESSION_SECRET=change-me-session-secret
NEXT_PUBLIC_API_URL=http://127.0.0.1:4000/api
```

> **Windows**: gunakan `127.0.0.1`, bukan `localhost` (mirip catatan dashboard-ops) untuk menghindari kendala bind IPv6.

---

## 5. Perintah Pengembangan

Semua dijalankan dari root repo.

| Tujuan | Perintah |
|---|---|
| Jalankan semua app (dev) | `pnpm local` |
| Migrasi DB | `pnpm migrate` |
| Seed (admin + RBAC) | `pnpm seed` |
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
pnpm migrate
pnpm seed
pnpm local
```

---

## 6. Urutan Wire-Up Disarankan untuk Eksekusi

1. Scaffold root (workspace + turbo + biome).
2. `apps/api` — Express app, Knex, migrasi + seed.
3. `packages/shared-types` — Zod schemas.
4. `apps/api` — RBAC middleware + routes.
5. `apps/web` — salin UI `TIEN-SALON-New`, sesuaikan URL EN.
6. `apps/web` — integrasi SSR ke API + halaman konsultasi.

---

## 7. Catatan Operasional

- **Jangan jalankan `pnpm lint` global secara sembarangan tanpa perlu** — lint hanya file yang disentuh (pola dashboard-ops).
- **Jangan auto-execute migrasi/seed** tanpa konfirmasi.
- API key OpenAI **hanya di `.env`** — jangan commit.
- Bioma konfigurasi: single quotes, trailing commas, 2-space indent, 100 line width.

---

_Lanjut baca: [03-backend.md](./03-backend.md)_
