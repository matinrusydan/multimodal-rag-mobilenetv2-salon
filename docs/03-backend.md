# 03 — Backend (Express + TypeScript)

Dokumen ini menjelaskan arsitektur backend `apps/api`: layering, auth, RBAC (diadopsi dari `dashboard-ops`), CV & RAG pipeline, dan konvensi.

> Status: **Rencana target** — kode belum ada.

---

## 1. Stack

| Aspek | Pilihan |
|---|---|
| Runtime | Node.js + TypeScript |
| Framework | Express 5 |
| Validasi | Zod (+ `zod-express`/custom validator middleware) |
| DB | PostgreSQL + Knex query builder |
| Logging | Pino (bukan `console.log`) |
| Test | Vitest (`node` env) |

---

## 2. Arsitektur Layer

Aliran pemanggilan, **satu arah**:

```
Route → Controller → Service → Repository → DB
```

- **Route** — definisi endpoint + validasi schema + middleware auth/RBAC.
- **Controller** — menerima `req/res`, memanggil service, menyusun respons.
- **Service** — logika bisnis, orkestrasi, transaksi.
- **Repository** — akses DB, extend `BaseRepository`.
- **Schema (Zod)** — validasi input/output, dibagi lewat `shared-types`.

`app.ts` (create app) dipisah dari `index.ts` (bootstrap) demi **testability**.

---

## 3. Struktur `apps/api`

```
apps/api/src/
├── index.ts          # bootstrap (env, listen)
├── app.ts            # Express app (dipisah utk test)
├── config/           # env.ts (Zod), db.ts (Knex), jwt.ts, cors.ts, logger.ts
├── db/               # migrations/ + seeds/
├── routes/           # *.routes.ts (prefix /api)
├── controllers/
├── services/         # + BaseService
├── repositories/     # + BaseRepository
├── middleware/       # requireAuth, securityEnforce, errorHandler, requestValidator
├── schemas/          # Zod schema per resource
├── cv/               # MobileNetV2 pipeline
├── rag/              # ChromaDB + OpenAI
├── utils/            # response, problemDetails
└── types/            # express.d.ts augmentasi
```

---

## 4. Auth: iron-session (FE) + JWT (BE)

Pola `dashboard-ops`:

1. Frontend (Next.js SSR) memakai **iron-session** untuk session HTTP.
2. Backend Express menerbitkan **JWT** via `POST /api/auth/login` / `/register`.
3. `GET /api/auth/session` menyinkronkan status login ke frontend.
4. Protected request membawa JWT; middleware `requireAuth` memvalidasi & menaruh `req.user`.
5. Logout: `POST /api/auth/logout` + clear cookie.

**Password hashing**: `argon2` (idempotent-recommended) atau `bcrypt`.

---

## 5. RBAC

Diadopsi penuh dari `dashboard-ops`, diimplementasikan sebagai middleware Express.

### 5.1 Tabel RBAC

| Tabel | Fungsi |
|---|---|
| `users` | Akun pengguna (kolom `type`: 0 = superadmin, 1 = biasa) |
| `roles` | Definisi role + hierarki (`parent_id`) |
| `permissions` | Daftar permission (`name`) |
| `user_roles` | Relasi user ↔ role (+ `scope_type`, `scope_value`) |
| `role_permissions` | Relasi role ↔ permission |
| `routes` | Definisi route/fitur aplikasi |
| `role_routes` | Otorisasi route per role |
| `menus` | Menu/sidebar dinamis |
| `role_menus` | Menu yang tampil per role |

### 5.2 Naming Convention Permission

```
<resource>.<action>
contoh: users.read, users.write, reservations.create, menus.write
```

Aturan matching (berurutan):
1. Exact match: `users.read`.
2. Wildcard: `users.*` atau `users.manage`.
3. Kepemilikan: `users.read.own` (untuk resource milik sendiri).

### 5.3 Superadmin Bypass

- Role `SUPER_ADMIN` / `SUPERADMIN`, **atau**
- user `type = 0` (system admin).

### 5.4 Middleware

```ts
// requireAuth: validasi JWT → req.user
// securityEnforce: cek permission → req.permission

router.get(
  '/users',
  requireAuth,
  securityEnforce('users.read'),
  userController.list,
)
```

`securityEnforce` menerima opsi `getResourceOwnerId` untuk pengecekan kepemilikan (`*.own`).

### 5.5 Cache

- Permission di-cache (in-memory, TTL ±60s; opsional Redis).
- Refresh non-blocking.

---

## 6. Validasi (Zod)

- Schema berada di `src/schemas/*.schema.ts` dan sebagian di-export via `shared-types`.
- Middleware `requestValidator` memvalidasi `body/params/query` sebelum controller.
- **Env divalidasi** dengan Zod di `config/env.ts` (gagal cepat saat boot bila salah).

---

## 7. Error Handling

- **RFC 7807 Problem Details** via `utils/problemDetails.ts`.
- `middleware/errorHandler.ts` menangkap error terpusat.
- Logging via Pino (`req.log`), bukan `console.log`.

---

## 8. CV Pipeline (MobileNetV2)

File: `src/cv/`

| Langkah | Detail |
|---|---|
| Preprocessing | resize 224×224, normalize ImageNet `mean=[0.485,0.456,0.406]`, `std=[0.229,0.224,0.225]` |
| Model | MobileNetV2 (PyTorch, `.pth`), dua head: panjang & jenis |
| Output | softmax → label + confidence |
| Label mapping | `cv/labels.ts` (lihat label tetap) |
| Threshold | `< 0.5` → status "tidak yakin" |

---

## 9. RAG Pipeline

File: `src/rag/`

| Langkah | Detail |
|---|---|
| Embedding | `text-embedding-3-small` (1536d) |
| Vector store | ChromaDB persist (`CHROMA_PERSIST_DIR`) |
| Search | cosine, `top_k = 5` |
| Chunking (ingest) | size 500–1000 token, overlap 100 |
| LLM | GPT-4o-mini, temperature 0.7, max_tokens 1000 |
| Prompt | system + retrieved docs + `hair_context` (CV) + user query |
| Knowledge base | `rag/knowledge/*.md` (harga, layanan, gaya-rambut, tips, booking) |

---

## 10. Konvensi

- **Bahasa**: kode & komentar Inggris; label klasifikasi Indonesia; error/UI user-facing Indonesia.
- **Tabel**: snake_case.
- **File**: `kebab-case.routes.ts` / `PascalController.ts` / `PascalService.ts`.
- **Jangan commit** `.env` / API key.

---

_Lanjut baca: [04-frontend.md](./04-frontend.md)_
