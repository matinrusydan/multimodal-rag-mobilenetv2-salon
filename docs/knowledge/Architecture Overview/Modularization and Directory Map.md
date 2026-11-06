# Modularisasi dan Peta Direktori

**Audit statis: 2026-11-06.** Peta berikut ringkas dan berbasis direktori yang ada.

## Web — `apps/web/src`

- `app/`: Next.js App Router, halaman dan Route Handlers pada `app/api/`.
- `components/`: komponen bersama, dikelompokkan antara lain `admin/`, `auth/`, `consult/`, `layout/`, `sections/`, `services/`, `ui/`.
- `data/`: data UI lokal seperti layanan, testimoni, dan informasi salon.
- `lib/`: klien backend, katalog, sesi, auth hooks, konstanta dan utilitas.
- `proxy.ts`: redirect pemeriksaan keberadaan cookie untuk subset route.

## API — `apps/api/src`

- `routes/`: registrasi endpoint Express per area.
- `controllers/`: adaptor HTTP dan pengendali request.
- `services/`: logika use-case/domain serta klien AI/cache permission.
- `repositories/`: akses persistence.
- `middleware/`: auth, RBAC, validasi, autentikasi internal, dan penanganan error.
- `schemas/`: skema validasi; `utils/`: response, pagination, Problem Details.
- `config/`: konfigurasi aplikasi.

## AI — `apps/ai/app`

- `main.py`: compatibility entrypoint yang mengekspor instance FastAPI dari `rag_app.py`.
- `rag_app.py`: konfigurasi runtime kanonikal (RAG-only) dengan router health, chat, agent, dan knowledge.
- `routers/`: endpoint HTTP FastAPI (`chat.py`, `agent.py`, `health.py`, `knowledge.py`, serta `analyze.py` offline).
- `rag/`: pipeline RAG lengkap (`rag_service.py`, `bm25_retrieval.py`, `live_services.py`, `catalog_operations.py`, `chatgpt_plan.py`, `retriever.py`, dll).
- `cv/`: modul inferensi Computer Vision offline (`model.py`, `labels.py`, `preprocessing.py`, `hair_features.py`).
- `crawler/`: utilitas perayap data pengetahuan lokal dan tips eksternal (`crawl_site.py`, `crawl_tips.py`).
- `config.py`: pembacaan variabel environment terpusat dengan schema default.

## Packages — `packages/`

- `packages/shared-types`: skema validasi Zod dan tipe TypeScript bersama antara frontend dan backend (`common.ts`, `service.ts`, `reservation.ts`, `payment.ts`, `rbac.ts`, `auth.ts`, `analyze.ts`, `chat.ts`).
- `packages/shared-utils`: fungsi utilitas bersama (`format.ts`, `invoice.ts`, `permission.ts`).

## Computer Vision Research — `apps/api/cv/`

- `geometry/`: direktori isolasi implementasi target roadmap CV baru (Fase 0–5), pengunduh pin, dan pemulihan dataset (`source_recovery/`).
- `dataset/`: penyimpanan dataset lokal (`figaro1k/` 252 citra terkurasi, `new_dataset/` arsip mentah).
- `weights/`: berkas bobot model ONNX dan PyTorch historis/warisan.
- `reports/`, `viewpoint/`, `hair_length/`, `hair_type/`: skrip dan artefak eksperimen legacy terdahulu.

## Arah dependensi (pola umum)

Web page/component → web Route Handler atau helper `lib` → API route → controller → service → repository. Ini bukan aturan absolut untuk setiap route: beberapa controller menggunakan client AI atau operasi khusus. Periksa endpoint terkait sebelum menambah alur.

## Bukti

Peta disusun dari daftar source di `apps/web/src/`, `apps/api/src/`, dan `apps/ai/app/main.py`; struktur dapat bertambah. Tidak mendokumentasikan folder arsip/dataset karena di luar cakupan arsitektur runtime ini.
