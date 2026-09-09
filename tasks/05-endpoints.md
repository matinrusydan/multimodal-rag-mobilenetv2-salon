# Task — Phase 05: Membuat Endpoint API

> Sebelumnya: Phase 04 copy UI.
> Referensi: `docs/03-backend.md` (arsitektur + RBAC), `docs/05-api.md` (spesifikasi endpoint), `docs/00-struktur-direktori.md`.

**Tujuan**: Membangun seluruh endpoint REST API di `apps/api` (Express + TS) sesuai spesifikasi, lengkap dengan **RBAC** (`requireAuth` + `securityEnforce`) dan **Zod** validasi, lalu terhubung ke database (Phase 03).

---

## 1. Landasan (foundation)

- [x] Pastikan `src/app.ts` & `src/index.ts` berjalan (dari Phase 01).
- [x] Pastikan `src/config/db.ts` (Knex) terhubung DB (Phase 03).
- [x] Lengkapi `src/config/env.ts` (validasi Zod semua env).

## 2. Zod Schema (shared & api)

- [x] Lengkapi `packages/shared-types` sesuai spesifikasi: Login, Register, Session, Service, Reservation, Payment, Analyze, Chat, User, Role, Permission.
- [x] (Backend) Schema route di `src/schemas/*.schema.ts` meng-import & mengextend shared-types.
- [x] Terapkan `requestValidator` middleware pada tiap route.

## 3. RBAC Middleware (diadopsi dashboard-ops)

- [x] Buat tabel RBAC (migrasi) — lihat Phase "database migration" bila belum:
  - `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `routes`, `role_routes`, `menus`, `role_menus`
- [x] `src/middleware/requireAuth.ts` — validasi JWT → `req.user`.
- [x] `src/middleware/securityEnforce.ts` — cek permission, dukung wildcard `resource.*`/`resource.manage`/`*.own`.
- [x] Superadmin bypass: role `SUPER_ADMIN`/`SUPERADMIN` atau user `type = 0`.
- [x] Permission cache (in-memory, TTL).
- [x] Seed awal: role `customer`/`staff`/`admin` + permission (lihat `docs/05-api.md §9`).

## 4. Auth

- [x] `AuthService` + `AuthRepository`: register, login (argon2/bcrypt), logout, session.
- [x] Route: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/session`.
- [x] Terbitkan JWT pada login; `GET /session` mengembalikan user + permission.

## 5. Services (public)

- [x] `ServiceService`/`ServiceRepository`: list + detail by slug.
- [x] Route `GET /api/services`, `GET /api/services/:slug` (publik).
- [x] (Opsional) seed data layanan awal dari `data/services.ts`.

## 6. Reservations & Payments

- [x] `ReservationService`/`Repository`: create (generate invoice number via shared-utils), list, detail, cancel.
- [x] Route: `POST /api/reservations` (`reservations.create`), `GET /api/reservations` (`reservations.read`), dll.
- [x] `PaymentService`: simulate + status.
- [x] Route: `POST /api/payments/simulate` (`payments.write`), `GET /api/payments/:id` (`payments.read`).

## 7. Konsultasi — Analyze & Chat (stub dulu)

> RAG+CV penuh di **Phase 07**. Di phase ini buat **route + service skeleton** (placeholder respons) supaya frontend bisa dipasang.

- [x] `POST /api/analyze` — terima image (multer), kembalikan placeholder `{ hairLength, hairType, confidence }`.
- [x] `POST /api/chat` — terima `{ message, hairContext }`, kembalikan placeholder reply.
- [x] Rate-limit pada kedua endpoint (pino + express-rate-limit).

## 8. Admin RBAC CRUD

- [x] `userController`/`Role`/`Permission`/`Route`/`Menu` service+repository+route.
- [x] Penerapan permission per endpoint (lihat `docs/05-api.md §8`):
  - `users.read/write/delete/manage`
  - `roles.*`, `permissions.*`, `routes.*`, `menus.*`
- [x] `menus` + `role_menus` untuk menu dinamis frontend.

## 9. Error Handling & Response

- [x] `src/utils/response.ts` (`{ ok, data }`) dan `src/utils/problemDetails.ts` (RFC 7807, pesan Bahasa Indonesia).
- [x] `errorHandler` global memetakan error Zod/HTTP/RBAC ke format Problem Details.

## 10. Verifikasi

- [x] `pnpm test:api` — semua test hijau (auth, services, reservation, rbac, security).
- [x] Manual smoke test via curl/Postman untuk tiap endpoint (publik + protected).
- [x] Uji RBAC: endpoint terproteksi menolak tanpa token / tanpa permission.
- [x] `pnpm build` dan `pnpm lint` lolos.

> **Catatan**: RAG+CV hanya stub skeleton di phase ini — implementasi penuh di Phase 07. Jangan auto-`pnpm migrate`/`seed` tanpa konfirmasi (AGENTS.md).
