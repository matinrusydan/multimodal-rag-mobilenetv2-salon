# Backend: RBAC dan Autentikasi

**Audit statis: 2026-11-06.**

## Autentikasi API

`requireAuth` membaca header `Authorization: Bearer ...`, memverifikasi JWT, mengambil user aktif dari repository, dan memasang data auth pada request. Token hilang/tidak valid atau user nonaktif menghasilkan 401. Permission diambil melalui `PermissionCache` bila tersedia; role user diambil dan disertakan sebagai kode role.

`requireAuth` dan `requireAuthOrInternal` adalah mekanisme berbeda; route seperti payment tertentu memilih middleware alternatif. Jalur tepat ditentukan route.

## Otorisasi

`securityEnforce(permission, options)`:

- Jika `SECURITY_ENFORCE_ENABLED` false, middleware melewati pemeriksaan.
- Jika tidak ada `req.auth`, menghasilkan 401.
- Bypass superadmin jika `type === 0`, permission mencakup `*`, atau role `SUPER_ADMIN`/`SUPERADMIN`.
- Selain itu memanggil `hasPermission` dengan permission dan opsi `own`; gagal menghasilkan 403.

Konvensi permission dan wildcard mengikuti helper shared `@rag-salon/shared-utils`; route merupakan bukti permission spesifik. Beberapa endpoint auth/public tidak menerapkan RBAC.

## Sesi web bukan sesi backend

Web memakai iron-session cookie `tien_session` yang menyimpan token backend dan ringkasan user (`apps/web/src/lib/web-session.ts`). Cookie httpOnly, sameSite lax, dan secure pada production. Fungsi pemetaan role menyimpan kode role. `apps/web/src/proxy.ts` hanya memeriksa cookie untuk redirect; otorisasi sumber tetap API.

Login/logout/session web ditangani melalui Next.js Route Handlers di `apps/web/src/app/api/auth/`. Karena browser tidak perlu mengelola JWT langsung, route server dapat mengirim token ke API melalui backend client.

## Bukti

`apps/api/src/middleware/requireAuth.ts`, `securityEnforce.ts`, `internalAuth.ts`, `services/PermissionCache.ts`, `routes/*.routes.ts`; `apps/web/src/lib/web-session.ts`, `proxy.ts`, `app/api/auth/`.
