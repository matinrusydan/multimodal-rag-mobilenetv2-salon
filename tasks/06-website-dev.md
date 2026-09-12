# Task — Phase 06: Development Website (Frontend Selesai)

> Sebelumnya: Phase 04 (copy UI) + Phase 05 (endpoint API).
> Referensi: `docs/04-frontend.md`, `docs/05-api.md`.

**Tujuan**: Mengintegrasikan frontend Next.js dengan backend API, melengkapi seluruh alur user (marketing, auth, reservasi, payment), menambahkan halaman admin RBAC & halaman konsultasi, hingga website berfungsi end-to-end.

---

## 1. Integrasi SSR ke Backend

- [x] `src/lib/backend.ts` — fetch server-side memakai `BACKEND_URL` + Authorization Bearer (helper `backendRequest`, `ApiError`, RFC7807).
- [x] Halaman marketing ambil data real dari API (`/services`, `/services/[slug]` via `src/lib/catalog.ts`) dengan fallback ke `src/data/*` bila backend mati.
- [x] Sinkronkan `shared-types` sebagai tipe respons API (Service, Reservation, Payment, Chat, Analyze).

## 2. Auth Frontend (iron-session)

- [x] `src/lib/web-session.ts` — get/set/clear iron-session cookie `tien_session` (httpOnly, berisi JWT + user compact).
- [x] `/auth` (1 URL merge login+daftar) terhubung ke `POST /api/auth/login` / `register` (toggle `?mode=register`, animasi panel lintas arah).
- [x] `GET /api/auth/session` memulihkan status login + event `tien-auth-change` (use-auth refactor).
- [x] Guard: `src/proxy.ts` (cookie presence → redirect `/login`) + `AuthGuard`/`GuardRedirect` + `admin/layout.tsx` (permission).

## 3. Alur Reservasi + Payment

- [x] `/reservation` — form multi-layanan (`serviceIds[]`), validasi, POST ke `/api/reservations`.
- [x] `/reservation/summary` — ringkasan invoice `INV-...` + items (guard sessionStorage).
- [x] `/payment` — pilih metode (qris/transfer/cash), POST `/api/payments/simulate`.
- [x] `/reservation/success` — konfirmasi sukses + clear session.
- [x] State alur via sessionStorage (pola TIEN-SALON-New, shape mengikuti API).

## 4. Halaman Admin (RBAC)

- [x] `src/proxy.ts` — proteksi route `/admin/*` (cookie) + gating permission di `admin/layout.tsx` (server).
- [ ] Sidebar/menu dinamis dari `menus` + `role_menus` (nav admin statis — disederhanakan utk prototipe).
- [x] Halaman: `admin/users`, `admin/roles`, `admin/permissions`, `admin/routes`, `admin/menus` — CRUD via `/api/admin/[...path]` proxy (incl. assign role/permission).
- [ ] Sembunyikan tombol write/delete sesuai permission (prototipe: gating per-halaman di layout saja).

## 5. Halaman Konsultasi (chatbot UI)

- [x] `/consult` — UI lengkap: upload foto (CV) + chat interface + chip konteks hasil klasifikasi.
- [x] Integrasi ke `POST /api/analyze` & `POST /api/chat` (reply RAG + sources + contextId).

## 6. Polish & UX

- [x] Loading state, empty state, error state untuk semua fetch.
- [ ] Toast/notification pada aksi sukses/gagal (prototipe: pesan inline).
- [x] Responsive & a11y (alt text, label).
- [x] Validasi form konsisten (schemas backend di-proxy apa adanya).

## 7. Verifikasi

- [x] `pnpm --filter web build` sukses.
- [x] `pnpm lint` (biome web) lolos.
- [x] `pnpm test:web` — 2 unit test hijau.
- [x] Smoke test manual: marketing SSR (data API) → login admin → session → reservasi → payment → admin CRUD + assign → chat RAG; guard redirect 307 → `/login`.
- [ ] E2E (opsional): `reservation-flow` via Playwright.

> **Catatan**: RAG+CV hanya versi placeholder-ish dari Phase 05 di phase ini. Fungsionalitas CV penuh (model MobileNetV2→ONNX) dilakukan di **Phase 07** & RAG penuh (ChromaDB seeding) di **Phase 08**. Smoke test memakai OpenAI key lokal sehingga `/api/chat` sudah menjawab via RAG pipeline nyata.
