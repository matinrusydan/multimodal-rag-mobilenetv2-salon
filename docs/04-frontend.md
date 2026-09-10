# 04 — Frontend (Next.js 16, SSR)

Dokumen ini menjelaskan arsitektur frontend `apps/web`: Next.js SSR, route group, konvensi global vs local component, mapping URL Bahasa Inggris, RBAC frontend, dan asal file UI.

> Status: **Rencana target**. UI awal disalin dari `TIEN-SALON-New` lalu diorganisir ulang.

---

## 1. Stack

| Aspek | Pilihan |
|---|---|
| Framework | Next.js 16 (App Router) |
| Render | **SSR** (Server Components) + client components bila perlu |
| Styling | Tailwind CSS + shadcn/ui (Radix) |
| Auth session | iron-session |
| State client | (opsional) Zustand / SWR |
| Test | Vitest (`jsdom`) + React Testing Library |

---

## 2. Routing

Semua halaman di bawah `src/app/`. URL menggunakan **Bahasa Inggris**; konten tetap Bahasa Indonesia.

```
src/app/
├── page.tsx                    “/”         splash screen
├── (marketing)/                route group publik
│   ├── home/page.tsx           /home
│   ├── services/page.tsx       /services
│   ├── services/[slug]/page.tsx /services/[slug]
│   ├── about/page.tsx          /about
│   ├── contact/page.tsx        /contact
│   └── auth/page.tsx           /auth         (login + daftar, 1 URL)
├── (app)/                      route group “wajib login”
│   ├── reservation/page.tsx            /reservation
│   ├── reservation/summary/page.tsx    /reservation/summary
│   ├── reservation/success/page.tsx    /reservation/success
│   ├── payment/page.tsx                /payment
│   ├── consult/page.tsx                /consult      (chatbot RAG, BARU)
│   └── admin/…                          /admin/*      (RBAC)
└── api/                        (opsional) route handler Next
```

---

## 3. Mapping URL — Bahasa Indonesia → Inggris

Folder `app/` asli (`TIEN-SALON-New`) diubah ke Bahasa Inggris:

| Asli (ID) | Baru (EN) | Halaman |
|---|---|---|
| `/` | `/` | Splash |
| `/home` | `/home` | Landing |
| `/layanan` | `/services` | Daftar layanan |
| `/layanan/[slug]` | `/services/[slug]` | Detail layanan |
| `/reservasi` | `/reservation` | Form reservasi |
| `/reservasi/ringkasan` | `/reservation/summary` | Ringkasan |
| `/reservasi/sukses` | `/reservation/success` | Sukses |
| `/payment` | `/payment` | Pembayaran (simulasi) |
| `/tentang` | `/about` | Tentang |
| `/kontak` | `/contact` | Kontak |
| `/auth` | `/auth` | Login + Daftar (merge, toggle via `?mode=register`) |
| _(baru)_ | `/consult` | Chatbot konsultasi RAG |

Semua `href`, `redirect`, dan `NAV_ITEMS` di `lib/constants.ts` mengikuti mapping ini. Konten teks di layar **tetap Bahasa Indonesia**.

---

## 4. Global vs Local Component

### Global component — `src/components/`

Dipakai lintas halaman/fitur. Berisi elemen umum & UI kit (dari `TIEN-SALON-New` + shadcn):

```
components/
├── ui/          button, badge, field, empty-state, loading-spinner, price-display, section, star-rating, stat-card, stepper
├── layout/      site-header, site-footer, marketing-shell, app-shell, page-transition-wrapper
├── sections/    hero, featured-services, why-choose-us, testimonials, cta-banner, stacked-services-scroll, featured-carousel
├── services/    service-card, service-grid, service-detail
├── reservation/ reservation-form, reservation-summary, success-page, guard-redirect
├── payment/     payment-method, payment-instructions, payment-page-content
├── auth/        auth-guard
├── consult/     photo-upload, chat-interface, result-card  (BARU untuk RAG)
└── brand/       brand-logo
```

### Local component — `src/features/`

Komponen **khusus satu fitur** yang tidak dipakai lintas fitur. Dibuat di `features/[nama]/` dengan sub-folder `{api, components, hooks}`.

```
features/
├── auth/        (login form spesifik, handler session)
├── reservation/
├── services/
├── consult/
└── admin/
```

> **Aturan**: pakai `components/` bila dipakai ≥ 2 fitur/halaman. Bila hanya untuk satu fitur → `features/[nama]/components`.

---

## 5. SSR & Data Fetching

- Halaman memakai **Server Components**; fetch data dari backend di server (menggunakan `BACKEND_URL`, bukan `NEXT_PUBLIC_*`) lalu render SSR.
- `lib/backend.ts` menyediakan helper fetch server-side (`backendRequest` + `ApiError`, membawa Bearer token).
- Client-side interaksi (upload foto, chat, form) memakai `"use client"` dan memanggil `NEXT_PUBLIC_API_URL`.

---

## 6. Auth di Frontend (iron-session)

- Session HTTP dikelola **iron-session** (cookie).
- `lib/session.ts` — helper read/write/clear.
- Guard halaman: redirect ke `/auth` bila belum login.
- Guard alur reservasi: cek sessionStorage (pola `TIEN-SALON-New`).
- Sync status via `GET /api/auth/session` + event `tien-auth-change`.

---

## 7. RBAC Frontend

- **`src/proxy.ts`** (Next.js 16 `proxy`, pengganti middleware) melindungi route: `/admin/*` wajib login + punya permission tertentu.
- Route group `(app)/admin` menampilkan halaman management (users, roles, permissions, routes, menus) dengan permission per aksi.
- **Menu dinamis** berdasarkan permission user (data dari `menus` + `role_menus`).
- Sidebar admin hanya menampilkan menu yang user berhak akses.

Halaman admin:
```
admin/
├── page.tsx          dashboard admin
├── users/            users.read / users.write
├── roles/            roles.read / roles.write
├── permissions/      permissions.read / permissions.write
├── routes/           routes.read / routes.write
└── menus/            menus.read / menus.write
```

---

## 8. Sumber File UI

Folder berikut **disalin dari `TIEN-SALON-New`** sebagai titik awal, lalu disesuaikan:

| Folder | Sumber |
|---|---|
| `app/` | `TIEN-SALON-New/app` (foldernya di-rename ke EN, lihat §3) |
| `components/` | `TIEN-SALON-New/components` |
| `data/` | `TIEN-SALON-New/data` |
| `lib/` | `TIEN-SALON-New/lib` |
| `public/` | `TIEN-SALON-New/public` |
| `styles/` | `TIEN-SALON-New/styles` |

File pendukung konfig dari referensi: `package.json` (versi deps), `tsconfig.json`, `next.config.mjs`, `postcss.config.mjs`, `components.json`.

---

## 9. Konvensi

- **Bahasa**: URL/path EN, konten UI ID, kode/komentar EN.
- File component: `kebab-case.tsx`.
- Komponen React: PascalCase.
- Semua gambar pakai `next/image` (CLS/alt text).

---

_Lanjut baca: [05-api.md](./05-api.md)_
