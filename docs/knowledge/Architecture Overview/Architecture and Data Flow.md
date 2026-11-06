# Arsitektur dan Alur Data

**Audit statis: 2026-11-06.** Catatan ini merangkum implementasi yang teramati pada source; bukan spesifikasi target. Jalur utama adalah Next.js `apps/web`, Express `apps/api`, dan runtime AI FastAPI. Sumber AI saat ini secara eksplisit menunjuk ke runtime RAG saja; modul riset CV bukan bagian runtime web.

## Batas aplikasi

- Web App Router mengembalikan halaman dan menangani interaksi UI. Route Handlers di `apps/web/src/app/api/` menjadi perantara browser ke API Express.
- API memetakan router `/api` lalu melakukan validasi, autentikasi/otorisasi, dan logika domain pada controller/service/repository.
- Integrasi AI memakai client/proxy di API; Chat dan Analyze route masing-masing memiliki batasan route. Runtime Python dimulai melalui `apps/ai/app/main.py`, yang mengekspor `app` dari `app.rag_app`.
- Data tampilan statis dapat berasal dari `apps/web/src/data/`; katalog layanan mencoba mengambil data API dan memiliki fallback lokal.

## Alur permintaan umum

1. Halaman atau komponen Next.js memanggil endpoint lokal `/api/...` atau fungsi katalog.
2. Route Handler web memanggil `backendRequest` untuk server-to-server ke `${BACKEND_URL}/api...`; permintaan memakai `cache: 'no-store'`.
3. Express mendaftarkan router di `apps/api/src/routes/index.ts`; route menjalankan middleware validasi/auth/RBAC yang ditetapkan sebelum controller.
4. Controller menggunakan service dan biasanya repository untuk akses data. Error diteruskan ke error handler API.
5. Respons backend dibungkus `{ ok, data }`; proxy web mempertahankan data sukses dan mengubah error menjadi Problem Details.

## Sesi dan alur reservasi

Auth web menggunakan cookie iron-session `tien_session` berisi token backend dan ringkasan user. Route web yang memerlukan autentikasi meneruskan token sebagai `Authorization: Bearer ...`. `apps/web/src/proxy.ts` hanya memeriksa keberadaan cookie untuk melindungi path `/admin`, `/reservation`, dan `/payment`; pemeriksaan autentikasi dan permission API berlangsung terpisah.

Data sementara alur reservasi/pembayaran di browser dapat disimpan melalui `sessionStorage` (`apps/web/src/lib/session.ts`); data ini bukan sumber otoritatif API. Rincian pemrosesan endpoint reservasi/payment berada di route dan controller masing-masing.

## Bukti sumber

- `apps/web/src/lib/backend.ts`, `catalog.ts`, `web-session.ts`, `proxy.ts`
- `apps/web/src/app/api/` Route Handlers
- `apps/api/src/app.ts`, `routes/index.ts`, `controllers/`, `services/`, `repositories/`, `middleware/`
- `apps/ai/app/main.py`, `apps/ai/app/rag_app.py`

Tidak disimpulkan perilaku yang tidak terlihat pada implementasi tersebut. Tidak membaca berkas konfigurasi rahasia atau menjalankan aplikasi.
