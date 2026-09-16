# 00 — Struktur Direktori

Dokumen ini mendefinisikan **struktur folder dan file** untuk monorepo RAG-salon. Berfungsi sebagai peta implementasi — beberapa bagian sudah dibangun (`apps/api`, `apps/web`, `packages/*`), sisanya adalah target (terutama `apps/ai`).

> Status: **Sebagian dibangun** — `apps/api` (Express + RBAC), `apps/web` (Next.js), dan `packages/*` sudah ada. `apps/ai` (FastAPI brain engine) masih rencana. Referensi arsitektur dari `dashboard-ops` (monorepo pnpm+Turbo, Express layer) dan UI dari `TIEN-SALON-New`.

---

## 1. Struktur Root

```
rag-salon/
├── pnpm-workspace.yaml          # workspace: apps/*, packages/*
├── turbo.json                   # pipeline build/test/lint/local tugas
├── package.json                 # root: scripts turbo + biome
├── biome.json                   # lint & format (konsisten dashboard-ops)
├── .gitignore
├── .env.example                 # env template
├── AGENTS.md                    # panduan agent
├── docs/                        # dokumentasi proyek (folder ini)
│   ├── 00-struktur-direktori.md
│   ├── 01-arsitektur.md
│   ├── 02-setup.md
│   ├── 03-backend.md
│   ├── 04-frontend.md
│   └── 05-api.md
├── packages/
│   ├── shared-types/            # Zod schemas dibagi FE↔BE
│   └── shared-utils/            # helper util dibagi
├── apps/
│   ├── api/                     # Backend Express + TypeScript (proxy AI ke FastAPI)
│   ├── ai/                      # Brain Engine FastAPI + Python (CV, RAG, Crawl4AI)
│   └── web/                     # Frontend Next.js 16
└── e2e/                         # (opsional) Playwright E2E
```

---

## 2. `apps/api` — Backend Express + TypeScript

Backend utama: REST API, auth, RBAC, service reservation/payment. Endpoint AI (`/api/analyze`, `/api/chat`) jadi **proxy** ke `apps/ai` (FastAPI). Lapisan Route→Controller→Service→Repository.

```
apps/api/
├── package.json
├── tsconfig.json
├── vitest.config.ts
├── knexfile.ts                  # konfigurasi Knex (PostgreSQL)
├── src/
│   ├── index.ts                 # ENTRY: bootstrap server (baca env, listen)
│   ├── app.ts                   # Express app (dipisah untuk testability)
│   ├── config/
│   │   ├── env.ts               # validasi env Zod
│   │   ├── db.ts                # koneksi Knex / data source
│   │   ├── jwt.ts               # config JWT
│   │   ├── cors.ts              # whitelist CORS
│   │   ├── helmet.ts            # security headers
│   │   └── logger.ts            # logging (pino)
│   ├── db/
│   │   ├── migrations/          # migrasi Knex (users, roles, permissions, dll)
│   │   └── seeds/               # seed data (admin, RBAC, permission)
│   ├── routes/
│   │   ├── index.ts             # register semua route + prefix /api
│   │   ├── auth.routes.ts
│   │   ├── services.routes.ts
│   │   ├── reservations.routes.ts
│   │   ├── payments.routes.ts
│   │   ├── analyze.routes.ts
│   │   ├── chat.routes.ts
│   │   ├── users.routes.ts
│   │   ├── roles.routes.ts
│   │   ├── permissions.routes.ts
│   │   ├── routes.routes.ts
│   │   ├── menus.routes.ts
│   │   └── health.routes.ts
│   ├── controllers/
│   │   ├── authController.ts
│   │   ├── serviceController.ts
│   │   ├── reservationController.ts
│   │   ├── paymentController.ts
│   │   ├── analyzeController.ts
│   │   ├── chatController.ts
│   │   ├── userController.ts
│   │   ├── roleController.ts
│   │   ├── permissionController.ts
│   │   ├── routeController.ts
│   │   └── menuController.ts
│   ├── services/
│   │   ├── AuthService.ts
│   │   ├── ServiceService.ts
│   │   ├── ReservationService.ts
│   │   ├── PaymentService.ts
│   │   ├── CvService.ts          # PROXY → FastAPI /ai/analyze (ai client)
│   │   ├── RagService.ts         # PROXY → FastAPI /ai/chat (ai client)
│   │   ├── ChatService.ts
│   │   ├── UserService.ts
│   │   ├── RoleService.ts
│   │   ├── PermissionService.ts
│   │   ├── RouteService.ts
│   │   ├── MenuService.ts
│   │   └── BaseService.ts
│   ├── repositories/
│   │   ├── AuthRepository.ts
│   │   ├── ServiceRepository.ts
│   │   ├── ReservationRepository.ts
│   │   ├── UserRepository.ts
│   │   ├── RoleRepository.ts
│   │   ├── PermissionRepository.ts
│   │   ├── RouteRepository.ts
│   │   ├── MenuRepository.ts
│   │   └── BaseRepository.ts
│   ├── middleware/
│   │   ├── requireAuth.ts        # auth JWT → req.user
│   │   ├── securityEnforce.ts    # RBAC: requirePermission(...)
│   │   ├── errorHandler.ts
│   │   └── requestValidator.ts   # validasi Zod per route
│   ├── schemas/                  # Zod schema per resource
│   │   ├── auth.schema.ts
│   │   ├── service.schema.ts
│   │   ├── reservation.schema.ts
│   │   ├── payment.schema.ts
│   │   ├── analyze.schema.ts
│   │   ├── chat.schema.ts
│   │   ├── user.schema.ts
│   │   ├── role.schema.ts
│   │   ├── permission.schema.ts
│   │   ├── route.schema.ts
│   │   └── menu.schema.ts
│   ├── cv/                       # (dipindah → apps/ai/cv/) CV pipeline Python[^1]
│   ├── rag/                      # (dipindah → apps/ai/rag/) RAG pipeline Python[^1]
│   ├── utils/
│   │   ├── response.ts
│   │   └── problemDetails.ts
│   └── types/
│       └── express.d.ts          # augmentasi Request (req.user, req.permission)
└── tests/
    ├── auth.test.ts
    ├── service.test.ts
    ├── reservation.test.ts
    ├── rbac.test.ts
    └── security.test.ts
```

> [^1]: Saat restrukturisasi ke FastAPI tuntas, kode lamanya diarsipkan (bukan dihapus) di `apps/api/src/archive/`.

---

## 3. `apps/ai` — Brain Engine (FastAPI + Python)

Runtime AI **native Python**: CV inference, RAG, dan crawler. Diakses Express sebagai proxy (publik tidak menyentuh `5000` langsung). Knowledge base markdown berada di sini.

```
apps/ai/
├── package.json                  # skrip dev + turbo (jalankan uvicorn)
├── pyproject.toml                # (opsional) metadata Python
├── requirements.txt              # deps Python (fastapi, onnxruntime, chromadb, dll)
├── .venv/                        # virtualenv lokal (tidak di-commit)
├── app/
│   ├── main.py                   # ENTRY: FastAPI app + lifespan
│   ├── config.py                 # baca env (AI_*, CHROMA_*, CRAWL_*, dll)
│   ├── routers/
│   │   ├── health.py             # GET /ai/health
│   │   ├── analyze.py            # POST /ai/analyze (multipart → klasifikasi CV)
│   │   └── chat.py               # POST /ai/chat (RAG Gemini)
│   ├── cv/
│   │   ├── model.py              # load + inference MobileNetV2 (onnxruntime)
│   │   ├── preprocessing.py      # resize 224x224 + normalisasi ImageNet
│   │   └── labels.py             # mapping label panjang & jenis rambut
│   ├── rag/
│   │   ├── embedding.py          # Gemini text-embedding-004 (768d)
│   │   ├── vectorStore.py        # ChromaDB (persistent | http)
│   │   ├── chunker.py            # chunk 500-1000 token, overlap 100
│   │   ├── retriever.py          # cosine similarity, top_k=5
│   │   ├── promptBuilder.py      # system + retrieved docs + hair_context
│   │   ├── ingest.py             # ingest knowledge → ChromaDB (idempotent)
│   │   └── knowledge/            # knowledge base markdown
│   │       ├── harga.md
│   │       ├── layanan.md
│   │       ├── gaya-rambut.md
│   │       ├── tips-perawatan.md
│   │       ├── booking-info.md
│   │       └── crawled-*.md      # (BARU) hasil Crawl4AI + front-matter topic
│   └── crawler/
│       ├── crawl_site.py         # skema situs TIEN (CRAWL_BASE_URL)
│       ├── crawl_tips.py         # skema tips eksternal (CRAWL_TIPS_URL)
│       └── topic_mapping.py      # URL pattern → topic
└── tests/
    ├── test_cv.py                # inference harapan (fake image)
    ├── test_ingest.py            # planIngest pure fn (fake store)
    ├── test_retriever.py         # retriever (fake store)
    └── test_topics.py            # topic mapping
```

---

## 4. `apps/web` — Frontend Next.js 16 (SSR)

UI disalin dari `TIEN-SALON-New`, diorganisir ulang ke route group + FSD-ringan (global vs local component).

```
apps/web/
├── package.json
├── tsconfig.json
├── next.config.ts
├── postcss.config.mjs
├── components.json              # shadcn/ui config
└── src/
    ├── middleware.ts            # RBAC route protection (Next middleware)
    ├── proxy.ts                 # (opsional) alias login/proxy middleware
    ├── app/
    │   ├── layout.tsx           # root layout (font, AppShell)
    │   ├── globals.css
    │   ├── not-found.tsx
    │   ├── error.tsx
    │   ├── page.tsx             # splash screen (“/”)
    │   ├── (marketing)/         # route group publik
    │   │   ├── layout.tsx       # marketing shell (header + footer)
    │   │   ├── home/page.tsx
    │   │   ├── services/page.tsx
    │   │   ├── services/[slug]/page.tsx
    │   │   ├── about/page.tsx
    │   │   ├── contact/page.tsx
    │   │   ├── login/page.tsx
    │   │   └── register/page.tsx
    │   ├── (app)/               # route group autentikasi (login wajib)
    │   │   ├── layout.tsx       # app shell
    │   │   ├── reservation/page.tsx
    │   │   ├── reservation/summary/page.tsx
    │   │   ├── reservation/success/page.tsx
    │   │   ├── payment/page.tsx
    │   │   ├── consult/page.tsx # chatbot konsultasi RAG (BARU)
    │   │   └── admin/           # halaman admin RBAC
    │   │       ├── layout.tsx
    │   │       ├── page.tsx
    │   │       ├── users/page.tsx
    │   │       ├── roles/page.tsx
    │   │       ├── permissions/page.tsx
    │   │       ├── routes/page.tsx
    │   │       └── menus/page.tsx
    │   └── api/                 # (opsional) route API Next
    ├── components/              # GLOBAL components (lintas halaman)
    │   ├── ui/                  # button, badge, field, dsb (dari shadcn/TIEN)
    │   ├── layout/              # site-header, site-footer, shell
    │   ├── sections/            # hero, featured-services, testimonials
    │   ├── services/
    │   ├── reservation/
    │   ├── payment/
    │   ├── auth/
    │   ├── consult/             # PhotoUpload, ChatInterface, ResultCard
    │   └── brand/
    ├── features/                # LOCAL component per fitur
    │   ├── auth/
    │   ├── reservation/
    │   ├── consult/
    │   ├── services/
    │   └── admin/
    ├── data/                    # data statis profil & fallback
    │   ├── services.ts
    │   ├── salon-info.ts
    │   ├── testimonials.ts
    │   └── constants.ts
    ├── lib/
    │   ├── session.ts           # iron-session
    │   ├── api.ts               # API client (server-side fetch)
    │   ├── format.ts
    │   ├── utils.ts
    │   └── constants.ts         # NAV_ITEMS, SESSION_KEYS
    ├── store/                   # (opsional) state client (Zustand)
    └── styles/
```

> **Catatan penamaan folder app/route**: folder URL menggunakan **Bahasa Inggris** (`services`, `reservation`, `about`, `contact`, `register`, `consult`). Konten/teks di halaman tetap Bahasa Indonesia.

---

## 5. `packages/shared-types`

```
packages/shared-types/
├── package.json                 # @rag-salon/shared-types
└── src/
    ├── index.ts
    ├── auth.ts                  # Zod: login, register, session
    ├── service.ts               # Zod: Service
    ├── reservation.ts           # Zod: Reservation
    ├── payment.ts               # Zod: Payment
    ├── analyze.ts               # Zod: hasil klasifikasi CV
    ├── chat.ts                  # Zod: chat request/response
    ├── user.ts
    ├── role.ts
    ├── permission.ts
    └── common.ts
```

---

## 6. `packages/shared-utils`

```
packages/shared-utils/
├── package.json                 # @rag-salon/shared-utils
└── src/
    ├── index.ts
    ├── format.ts                # formatRupiah, formatDate
    ├── invoice.ts               # generate invoice number
    └── permission.ts            # helper wildcard permission match
```

---

## 7. `e2e` (opsional)

```
e2e/
├── package.json
├── playwright.config.ts
└── tests/
    └── reservation-flow.spec.ts
```

---

## 8. Catatan Konvensi Penamaan

- **Folder route app/ (URL)**: Bahasa Inggris (`services`, `reservation`, `consult`, `admin`).
- **Tabel & kolom DB**: snake_case (persis dashboard-ops).
- **File backend**: `*.routes.ts`, `*Controller.ts`, `*Service.ts`, `*Repository.ts`, `*.schema.ts`.
- **File frontend**: kebab-case `kebab-case.tsx`.
- **Komponen React**: PascalCase; file `kebab-case.tsx`.
- **Permission**: `<resource>.<action>` (mis. `users.read`, `reservations.create`).

---

_Lanjut baca: [01-arsitektur.md](./01-arsitektur.md)_
