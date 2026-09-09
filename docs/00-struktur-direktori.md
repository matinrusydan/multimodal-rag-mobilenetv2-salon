# 00 — Struktur Direktori

Dokumen ini mendefinisikan **seluruh struktur folder dan file yang akan dibangun** untuk monorepo RAG-salon. Berfungsi sebagai peta implementasi — setiap file yang tertulis di sini adalah target yang akan dibuat.

> Status: **Rencana target** — kode belum ada. Referensi arsitektur dari `dashboard-ops` (monorepo pnpm+Turbo, Express layer) dan UI dari `TIEN-SALON-New`.

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
│   ├── api/                     # Backend Express + TypeScript
│   └── web/                     # Frontend Next.js 16
└── e2e/                         # (opsional) Playwright E2E
```

---

## 2. `apps/api` — Backend Express + TypeScript

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
│   │   ├── CvService.ts          # MobileNetV2 inference
│   │   ├── RagService.ts         # ChromaDB + OpenAI
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
│   ├── cv/                       # Computer Vision pipeline
│   │   ├── model.ts              # load + inference MobileNetV2
│   │   ├── preprocessing.ts      # resize 224x224 + normalisasi
│   │   └── labels.ts             # mapping label panjang & jenis rambut
│   ├── rag/                      # RAG pipeline
│   │   ├── embedding.ts          # text-embedding-3-small
│   │   ├── vectorStore.ts        # ChromaDB (persistent)
│   │   ├── promptBuilder.ts
│   │   └── knowledge/            # knowledge base markdown
│   │       ├── harga.md
│   │       ├── layanan.md
│   │       ├── gaya-rambut.md
│   │       ├── tips-perawatan.md
│   │       └── booking-info.md
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

---

## 3. `apps/web` — Frontend Next.js 16 (SSR)

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

## 4. `packages/shared-types`

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

## 5. `packages/shared-utils`

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

## 6. `e2e` (opsional)

```
e2e/
├── package.json
├── playwright.config.ts
└── tests/
    └── reservation-flow.spec.ts
```

---

## 7. Catatan Konvensi Penamaan

- **Folder route app/ (URL)**: Bahasa Inggris (`services`, `reservation`, `consult`, `admin`).
- **Tabel & kolom DB**: snake_case (persis dashboard-ops).
- **File backend**: `*.routes.ts`, `*Controller.ts`, `*Service.ts`, `*Repository.ts`, `*.schema.ts`.
- **File frontend**: kebab-case `kebab-case.tsx`.
- **Komponen React**: PascalCase; file `kebab-case.tsx`.
- **Permission**: `<resource>.<action>` (mis. `users.read`, `reservations.create`).

---

_Lanjut baca: [01-arsitektur.md](./01-arsitektur.md)_
