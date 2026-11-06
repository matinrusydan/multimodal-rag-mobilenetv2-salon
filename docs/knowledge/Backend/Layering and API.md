# Backend: Lapisan dan API

**Audit statis: 2026-11-06.** API Express menginisialisasi middleware umum, JSON body parser (batas 5 MB), cookie parser, router, lalu error handler (`apps/api/src/app.ts`). Router pusat ada di `apps/api/src/routes/index.ts`, dengan prefix `/api` untuk health dan area seperti auth, services, reservations, payments, analyze, chat, knowledge, users, roles, permissions, routes, menus, settings, dan agent.

## Lapisan

- **Route** menentukan method/path dan urutan middleware/controller.
- **Controller** menerima request dan membentuk respons atau meneruskan error.
- **Service** memuat logika domain/use-case dan koordinasi.
- **Repository** mengisolasi operasi persistence; pola dasar ada di `repositories/BaseRepository.ts`.
- **Schema/middleware** memvalidasi masukan dan menerapkan auth/RBAC sebelum controller bila route memasangnya.

Tidak setiap route dijamin memakai semua lapisan; baca route/controller bersangkutan untuk perilaku tepat.

## Contoh kontrak rute yang teramati

- `/api/health` dan `/api/ready`: GET.
- `/api/auth/register`, `/login`: POST dengan limiter dan schema; `/logout` POST dan `/session` GET memerlukan auth.
- `/api/services`: GET publik; `admin/all` dan operasi tulis dibatasi; `/:slug` divalidasi.
- `/api/chat` dan `/api/analyze`: POST memakai posting limiter (chat juga validasi schema). Keberadaan route tidak membuktikan layanan AI sehat.
- Area administrasi memasang `requireAuth` dan `securityEnforce` sesuai aksi; detail endpoint aktual ada di berkas route.

## Error dan validasi

Validasi dilakukan melalui middleware `requestValidator` dengan schema route. `errorHandler`/utilitas Problem Details menentukan bentuk kegagalan. Web proxy memiliki kontrak responsnya sendiri; jangan mengasumsikan semua format respons identik tanpa menelusuri controller terkait.

## AI runtime

API memiliki `services/aiClient.ts`. Runtime Python entrypoint `apps/ai/app/main.py` mengimpor `app.rag_app.app` (RAG-only menurut docstring); ini bukan pipeline CV inference.

## Sumber kode

`apps/api/src/app.ts`, `routes/index.ts`, `routes/*.routes.ts`, `controllers/`, `services/`, `repositories/`, `schemas/`, `middleware/`, `utils/`; `apps/ai/app/main.py`.
