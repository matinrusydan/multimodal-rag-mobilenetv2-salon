# 03 — Backend (Express + TypeScript) & Brain Engine (FastAPI)

Dokumen ini menjelaskan arsitektur backend `apps/api`: layering, auth, RBAC (diadopsi dari `dashboard-ops`), plus arsitektur `apps/ai` sebagai brain engine AI (CV, RAG, Crawl4AI) dan bagaimana Express menjadi proxy ke-nya.

> Status: **Sebagian dibangun** — `apps/api` sudah berjalan. `apps/ai` masih rencana.

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
├── utils/            # response, problemDetails
└── types/            # express.d.ts augmentasi
```

> `cv/` dan `rag/` **tidak lagi di Express** — runtime AI pindah ke `apps/ai` (Python). Express memanggil FastAPI melalui client HTTP (proxy).

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

## 8. Proxy ke Brain Engine (Express → FastAPI)

Express bertindak sebagai **kurir** untuk endpoint AI. AI endpoints (`/api/analyze`, `/api/chat`) melakukan forward ke FastAPI `apps/ai` (`:5000`).

```
POST /api/analyze ──► httpx/fetch ──► POST http://127.0.0.1:5000/ai/analyze
POST /api/chat    ──► httpx/fetch ──► POST http://127.0.0.1:5000/ai/chat
```

- **Rate-limit** (`postingLimiter`) dan **validasi Zod** tetap di Express (publik tidak boleh lihat FastAPI langsung).
- **Multipart** (`/api/analyze`) diteruskan apa adanya (`multer.memoryStorage` → buffer → forward).
- **Timeout** & retry terbatas (`AI_PROXY_TIMEOUT_MS`) supaya request bergantung FastAPI tidak menggantung.
- Global error handler menangkap kegagalan FastAPI (down) → Problem Details `502`.

---

## 9. Brain Engine — `apps/ai` (FastAPI + Python)

Runtime AI native Python. Terpisah dari Express agar bisa memakai ekosistem Python (onnxruntime, chromadb native, Crawl4AI) dan menempatkan seluruh AI stack kode Python di satu tempat.

Structure: `app/{main,config}.py`, `app/routers/`, `app/cv/`, `app/rag/`, `app/crawler/`, `tests/`. Port `5000`.

### 9.1 CV Pipeline (onnxruntime + MobileNetV2)

File: `app/cv/`

| Langkah | Detail |
|---|---|
| Preprocessing | resize 224×224, normalize ImageNet `mean=[0.485,0.456,0.406]`, `std=[0.229,0.224,0.225]` |
| Model | `hair_length.onnx` + `hair_type.onnx` (MobileNetV2), inference via **onnxruntime** |
| Output | softmax → label + confidence (format `HairFeaturesSchema` dari shared-types) |
| Label mapping | `cv/labels.py` (lihat label tetap) |
| Threshold | `< 0.5` → status "tidak yakin" |

Endpoint: `POST /ai/analyze` (multipart image) → `{ hairLength, hairType, analyzedAt }`.

### 9.2 RAG Pipeline (ChromaDB native + Gemini)

File: `app/rag/`

| Langkah | Detail |
|---|---|
| Embedding | Gemini `gemini-embedding-001` (**768d** via `outputDimensionality`), provider via `AI_EMBEDDING_PROVIDER=gemini` |
| Vector store | ChromaDB **native Python**; mode `persistent` (default) atau `http` |
| Search | cosine, `top_k = 5` |
| Chunking (ingest) | size 500–1000 token, overlap 100 |
| LLM | **Gemini** (`gemini-3.6-flash`), provider via `AI_LLM_PROVIDER=gemini`; temperature 0.7, max_tokens 1000 |
| Prompt | system + retrieved docs + `hair_context` (CV) + user query |
| Knowledge base | `rag/knowledge/*.md` (harga, layanan, gaya-rambut, tips, booking) + `crawled-*.md` |

**Ingest idempotent**: tiap chunk punya ID `file#hash#index` → upsert ke koleksi ChromaDB tidak membuat duplikat. `planIngest(files)` adalah fungsi murni (mudah di-test tanpa ChromaDB live).

Endpoint: `POST /ai/chat` → `{ reply, sources, contextId }`.

### 9.3 Crawler (Crawl4AI)

File: `app/crawler/`. Menghasilkan isi knowledge base. Dua skema:

| Skema | Sumber | Topic hasil |
|---|---|---|
| **Situs salon** | `CRAWL_BASE_URL` (default `http://127.0.0.1:3000`) | mapping URL → topic (`/services*`→`layanan`, `/reservation*`→`booking-info`, `/about`→`about`, default→`layanan`) |
| **Tips eksternal** | `CRAWL_TIPS_URL` (default `https://alodokter.com`) | semua → `tips-perawatan` |

Output: `rag/knowledge/crawled-*.md` dengan **YAML front-matter `topic`** (konten Bahasa Indonesia). Strategi `raw` (HTTP langsung, untuk halaman SSR/SSG) atau `browser` (Playwright, untuk SPA) via `CRAWL_USE_BROWSER`. Delay antar-request `CRAWL_DELAY_MS` (default 1500ms).

**Stealth mode** (`--stealth` / `pnpm crawl:site -- --stealth`): dipakai untuk situs anti-bot seperti alodokter.com. Berbasis `UndetectedAdapter` + `AsyncPlaywrightCrawlerStrategy` (`app/crawler/stealth.py`):

- `BrowserConfig(headless=False, enable_stealth=True, user_agent_mode="random", light_mode=True)` — anti-bot alodokter **butuh `headless=False`** (dikontrol env `CRAWL_HEADLESS`).
- `CrawlerRunConfig(delay_before_return_html=0.5, wait_until="domcontentloaded", cache_mode=CacheMode.BYPASS, page_timeout=30000, only_text=True)` — konten muncul di atribut `result.markdown` (bukan `raw_markdown`). `domcontentloaded` dipilih (bukan `load`) karena ~1.2s lebih cepat tanpa kehilangan konten pada halaman alodokter.
- **Anti-bot detector** (`app/crawler/antibot_detector.py`, adaptasi dari repo crawl4ai): hasil crawl yang terlihat seperti block page (Akamai/Cloudflare/PerimeterX/DataDome/403/429/empty-shell) ditolak sebelum ditulis ke KB atau dipakai RAG.

**Live web fallback di RAG** (`app/rag/web_fallback.py`): tiga mode sumber berdasarkan query:

| Query | Deteksi | Sumber jawaban |
|---|---|---|
| Kesehatan rambut murni (rontok, kebotakan, ketombe) | `detect_health_topic` | **Web-only** (live crawl alodokter, KB di-skip) |
| Layanan salon + kekhawatiran kondisi rambut ("apakah aman smoothing setelah bleaching?") | `detect_hair_concern` | **Mix** (KB salon + web alodokter) |
| Layanan salon biasa (harga, booking) | — | **KB lokal** saja |

Crawl pandu via `asyncio.to_thread(crawl_url_sync, ...)` agar spawn browser berada di **fresh Proactor loop** (uvicorn selector loop Windows tidak bisa spawn subprocess Playwright).

**Optimasi latensi** (dari ~15s → ~2–4s):

- **Cache hasil crawl** per-URL in-memory, TTL `WEB_CACHE_TTL_SECONDS` (default 3600s). Request berikutnya untuk URL sama → instan.
- **Cooldown model LLM**: model yang kena 429/quota ditandai cooldown (`AI_LLM_COOLDOWN_SECONDS`, default 120s; atau mengikuti `retryDelay` API) dan dilewati pada request berikutnya → tidak membuang waktu mencoba model yang sudah pasti gagal.
- **Fallback LLM berantai** `AI_LLM_FALLBACK_MODELS` (default `gemini-3.1-flash-lite,gemini-flash-lite-latest,gemini-3-flash-preview,gemini-flash-latest`).
- Prompt dipangkas (web 1100 char, KB 400 char, `max_output_tokens=900`, target ~180 kata).

Kontrol tambahan: env `WEB_FALLBACK_ENABLED` (default `true`), `WEB_FALLBACK_MAX_DOCS` (default `2`).

**Anti-halusinasi**: `prompt_builder.py` melarang LLM mengklaim kondisi rambut pelanggan (kering/rusak/bleaching) kecuali data tersebut diberikan eksplisit di KONTEKS/FITUR RAMBUT. Fitur CV (`app/cv/hair_features.py`) tidak lagi mengklaim `health: "kering"` — nilainya `"tidak-diketahui"` karena HSV+GLCM hanyalah heuristik, bukan klasifikasi kondisi terlatih. Yang dilaporkan hanya *indikasi* via `riskSigns.bleach` / `riskSigns.dry`.

```md
---
topic: tips-perawatan
source: https://alodokter.com/artikel-tips
type: crawled
---
# Judul Artikel
...
```

### 9.4 Framework & Tooling

- **FastAPI** + **Uvicorn**, validasi via **Pydantic** (mirip peran Zod di Express).
- Error respon memakai **RFC 7807 Problem Details** (Bahasa Indonesia) — selaras dengan Express.
- **Pytest** untuk unit test (tanpa ChromaDB/network untuk logic murni).

---

## 10. Konvensi

- **Bahasa**: kode & komentar Inggris; label klasifikasi Indonesia; error/UI user-facing Indonesia.
- **Tabel**: snake_case.
- **File**: `kebab-case.routes.ts` / `PascalController.ts` / `PascalService.ts`.
- **Jangan commit** `.env` / API key.

---

_Lanjut baca: [04-frontend.md](./04-frontend.md)_
