# Pengambilan Data

**Audit statis: 2026-11-06.**

## Klien backend pada web

`apps/web/src/lib/backend.ts` menyediakan `backendRequest<T>(path, init)`:

- Base URL dari `BACKEND_URL`, default `http://127.0.0.1:4000`, ditambah `/api` dan path yang diberikan.
- Header menerima `application/json`; body non-null memicu `content-type: application/json`; token opsional menjadi `Authorization: Bearer ...`.
- Cache selalu `no-store`. Timeout hanya diterapkan jika `timeoutMs` diberi pemanggil, menggunakan `AbortSignal.timeout` dan menggabungkan signal pemanggil bila tersedia.
- Mengharapkan respons JSON dengan `data`; sukses mengembalikan `body?.data`. JSON tak terbaca menjadi `null`; HTTP non-2xx menghasilkan `ApiError` berisi status/title/detail (title fallback Indonesia).
- Abort/timeout dinormalisasi ke status 504. `routeError` mengembalikan `application/problem+json`; error tak dikenal menjadi respons generik 500.

## Katalog layanan

`apps/web/src/lib/catalog.ts` mengambil `GET /services` via klien tersebut. Jika data bukan array atau array kosong, atau pemanggilan melempar error, hasilnya katalog lokal `apps/web/src/data/services.ts`. Data API dipetakan ke bentuk UI dengan sejumlah atribut lokal/fallback. `getServiceBySlug` mencari daftar hasil tersebut, lalu fallback ke katalog lokal. Jadi API tidak selalu menjadi sumber tampilan tunggal.

## Route Handlers sebagai lapisan perantara

Endpoint browser ada di `apps/web/src/app/api/`. Contoh route admin dapat meneruskan path dan token sesi ke backend; auth login/register/session/logout mengelola sesi web. Jangan menyamakan endpoint internal Next.js ini dengan endpoint Express walau beberapa path semantik sama.

## Sesi browser berbeda dari sesi login

- `apps/web/src/lib/web-session.ts`: iron-session di cookie `tien_session`; `httpOnly`, `sameSite=lax`, `secure` pada production; API menyediakan get/set/clear. Di production secret harus memenuhi pemeriksaan minimal 32 karakter dan bukan nilai bawaan/contoh.
- `apps/web/src/lib/session.ts`: utilitas `sessionStorage` untuk data reservasi/payment sementara; hanya berjalan di browser, JSON rusak dihapus saat dibaca, dan clear flow menghapus dua key.
- Proxy Next.js mengecek cookie keberadaan untuk redirect route terlindungi. Ini bukan validasi token backend.

## AI Brain Engine — Konsumsi Data

- **Live Catalog Sync:** `apps/ai/app/rag/live_services.py` menggunakan HTTP client async untuk memanggil Express `GET /api/services`. Data dibaca untuk jawaban katalog deterministik. Periksa perilaku koneksi/cache di kode saat mengubah lifecycle; startup `rag_app` memanggil `start_catalog_client()` dan menutup client saat shutdown.
- **Corpus Pengetahuan RAG:** `apps/ai/app/rag/corpus_loader.py` memuat dokumen pengetahuan terkurasi dari sumber/runtime yang dikonfigurasi; detail path dan fallback berada di loader, jangan diasumsikan seluruh `rag/knowledge` selalu diindeks langsung.
- **Internal API Token:** Pemanggilan agent/admin AI oleh Express memakai header `X-Internal-Token` yang diverifikasi melalui `apps/api/src/middleware/internalAuth.ts`. Jalur live catalog biasa bukan internal-auth header.

## Tidak diasumsikan

Tidak ada cache HTTP positif pada `backendRequest`; ia eksplisit no-store. Fallback katalog menangkap error, sehingga pemanggil katalog tidak menerima error backend. Detail cache DB dan API mengikuti implementasi tiap repository/service.

## Sumber

`apps/web/src/lib/backend.ts`, `catalog.ts`, `session.ts`, `web-session.ts`, `proxy.ts`; `apps/web/src/app/api/**/route.ts`; `apps/api/src/routes/`.
