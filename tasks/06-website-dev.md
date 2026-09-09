# Task — Phase 06: Development Website (Frontend Selesai)

> Sebelumnya: Phase 04 (copy UI) + Phase 05 (endpoint API).
> Referensi: `docs/04-frontend.md`, `docs/05-api.md`.

**Tujuan**: Mengintegrasikan frontend Next.js dengan backend API, melengkapi seluruh alur user (marketing, auth, reservasi, payment), menambahkan halaman admin RBAC & halaman konsultasi, hingga website berfungsi end-to-end.

---

## 1. Integrasi SSR ke Backend

- [ ] `src/lib/api.ts` — fetch server-side memakai `BACKEND_URL` + cookie/session.
- [ ] Halaman-halaman marketing ambil data real dari API (services list, detail) dengan fallback ke `src/data/*`.
- [ ] Sinkronkan `shared-types` sebagai tipe respons API.

## 2. Auth Frontend (iron-session)

- [ ] `src/lib/session.ts` — read/write/clear iron-session cookie.
- [ ] Halaman login/register terhubung ke `POST /api/auth/login` / `register`.
- [ ] `GET /api/auth/session` untuk memulihkan status login (SSR) + event `tien-auth-change`.
- [ ] Guard: redirect ke `/login` bila halaman protected tanpa session.

## 3. Alur Reservasi + Payment

- [ ] `/reservation` — form lengkap, validasi, POST ke `POST /api/reservations`.
- [ ] `/reservation/summary` — tampil ringkasan (guard sessionStorage).
- [ ] `/payment` — pilih metode, `POST /api/payments/simulate`.
- [ ] `/reservation/success` — konfirmasi sukses + clear session.
- [ ] State alur via sessionStorage (pola TIEN-SALON-New).

## 4. Halaman Admin (RBAC)

- [ ] `src/middleware.ts` — proteksi route `/admin/*` (login + permission).
- [ ] Sidebar/menu dinamis dari `menus` + `role_menus`.
- [ ] Halaman: `admin/users`, `admin/roles`, `admin/permissions`, `admin/routes`, `admin/menus` — CRUD ke API terproteksi.
- [ ] Hanya tampilkan aksi sesuai permission user (hide tombol write/delete bila tak punya hak).

## 5. Halaman Konsultasi (chatbot UI)

- [ ] `/consult` — UI lengkap: upload foto (CV) + chat interface + hasil klasifikasi (result card).
- [ ] Integrasi ke `POST /api/analyze` & `POST /api/chat` (reply RAG).

## 6. Polish & UX

- [ ] Loading state, empty state, error state untuk semua fetch.
- [ ] Toast/notification pada aksi sukses/gagal.
- [ ] Responsive & a11y (alt text, label, focus).
- [ ] Validasi form konsisten (shared-types).

## 7. Verifikasi

- [ ] `pnpm --filter web build` sukses.
- [ ] `pnpm lint` lolos.
- [ ] `pnpm test:web` — unit/component test hijau.
- [ ] Smoke test manual: seluruh alur marketing → auth → reservasi → payment → success; admin CRUD; konsultasi.
- [ ] E2E (opsional): `reservation-flow` via Playwright.

> **Catatan**: RAG+CV hanya versi placeholder (dari Phase 05) di phase ini. Fungsionalitas CV & RAG penuh dilakukan di **Phase 07**.
