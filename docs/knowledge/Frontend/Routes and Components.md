# Frontend: Routes dan Komponen

**Audit statis: 2026-11-06.** Route aktual ditentukan direktori `apps/web/src/app/`; jangan mengandalkan peta URL historis jika berbeda dari source.

## Halaman

App Router memuat halaman root dan area antara lain `/about`, `/admin` (serta halaman manajemen knowledge, menus, permissions, reports, reservations, role-menus, roles, routes, services, settings, users), `/auth`, `/consult`, `/contact`, `/home`, `/payment`, `/reservation`, dan `/services` termasuk detail slug. Terdapat pula route halaman lain di pohon app; direktori adalah sumber utama untuk daftar terbaru.

## Route Handlers

`app/api/` memuat endpoint lokal untuk services, reservations, chat, analyze, payments/simulate, admin catch-all, serta auth login/register/session/logout. Ini adalah server-side endpoint Next.js, bukan halaman. Implementasi Handler menjembatani API Express dan mengelola sesi sesuai area.

## Komponen

- `components/layout/`: shell/header/footer dan transisi halaman.
- `components/services/`: kartu, grid, detail layanan.
- `components/consult/`: antarmuka konsultasi dan markdown.
- `components/admin/`: navigasi dan pengelolaan area admin.
- `components/auth/`: tampilan autentikasi.
- `components/sections/`: bagian-bagian halaman pemasaran.
- `components/ui/`: elemen UI umum.
- `components/brand/`: elemen brand.

Beberapa fitur tetap menggunakan komponen lokal dalam page; klasifikasi folder tidak menjamin seluruh halaman memakai komponen global.

## Perlindungan route

`src/proxy.ts` memeriksa keberadaan cookie `tien_session` untuk `/admin`, `/reservation`, dan `/payment`. Tanpa cookie, redirect ke `/auth?redirect=<pathname>`. Pemeriksaan ini bukan otorisasi permission dan tidak membuktikan validitas token; endpoint API tetap harus melindungi operasi.

## Sumber

`apps/web/src/app/**/page.tsx`, `apps/web/src/app/api/**/route.ts`, `apps/web/src/components/`, `apps/web/src/proxy.ts`.
