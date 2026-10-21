# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Aturan proyek dan sumber acuan

- Ikuti `AGENTS.md`. Untuk pekerjaan CV, **`docs/08-roadmap-cv-lengkap.md` adalah acuan tertinggi**; baca sebelum mengubah klasifikasi, pose, segmentasi, geometri, atau dataset.
- `README.md` dan `PRD.md` menjelaskan tujuan prototipe konsultasi salon multimodal, tetapi beberapa bagian masih rancangan lama. Bedakan rancangan dari implementasi dan konfigurasi yang benar-benar digunakan.
- Arsitektur umum: `docs/01-arsitektur.md`; setup: `docs/02-setup.md`. Profil operasional RAG: `docs/19-finalisasi-rag-dan-operasional.md`; perubahan seleksi bukti dan klarifikasi: `docs/21-penguatan-seleksi-dan-evaluasi-lanjutan.md` dan `docs/22-penanganan-ambiguitas-konsultasi.md`.
- Jangan menjalankan migrasi, seed, atau lint tanpa konfirmasi pengguna. `db:repair` juga perlu konfirmasi karena dapat menjalankan migrasi/seed.

## Perintah pengembangan dan pengujian

Jalankan dari root kecuali disebutkan lain. Gunakan pnpm **10.15.1** (pin `packageManager`), Node sesuai persyaratan Next.js 16 (README merekomendasikan Node 20+), PostgreSQL, dan Python. Contoh Python di bawah memakai PowerShell/Windows.

| Tujuan | Perintah |
|---|---|
| Instal dependensi workspace | `pnpm install` |
| Jalankan semua aplikasi | `pnpm dev` atau `pnpm local` |
| Jalankan satu aplikasi | `pnpm --filter web dev`, `pnpm --filter api dev`, `pnpm ai` |
| AI gabungan dengan reload | `pnpm --filter ai dev:reload` |
| AI RAG-only | `pnpm --filter ai start:rag` |
| Build / pemeriksaan tipe | `pnpm build` / `pnpm typecheck` |
| Semua tes / API / frontend | `pnpm test` / `pnpm test:api` / `pnpm test:web` |
| Regresi Python tanpa tes CV | `pnpm test:rag` |
| Preflight RAG dan katalog | `pnpm --filter ai rag:check` |
| Smoke RAG melalui proxy | `pnpm --filter ai rag:smoke` |
| Lint / lint dengan perbaikan | `pnpm lint` / `pnpm lint:fix` — perlu konfirmasi |
| Format / tulis format | `pnpm format` / `pnpm format:write` |
| Migrasi / seed / repair DB | `pnpm migrate` / `pnpm seed` / `pnpm db:repair` — perlu konfirmasi |
| Crawl offline / ingest Chroma | `pnpm crawl:site`, `pnpm crawl:tips`, `pnpm rag:ingest` |
| Sinkronisasi snapshot katalog | `pnpm --filter ai rag:sync-catalog` (tidak ada alias root) |

**Perhatian sebelum menjalankan:**

- `dev` setiap app memakai `scripts/freeport.mjs`, yang dapat menghentikan paksa proses di port 3000/4000/5000. `pnpm local` sudah mencakup AI; jangan sekaligus menjalankan `pnpm ai` atau profil RAG-only pada port 5000.
- **Tes API dapat menghapus dan membuat ulang tabel.** `apps/api/tests/helpers.ts::prepareDb()` memanggil migration `down()`, `up()`, lalu seed terhadap `DATABASE_URL` biasa; tidak ada pemisahan database tes otomatis. Siapkan database disposable dan minta konfirmasi sebelum menjalankan suite yang memakai helper ini, termasuk `pnpm test`/`pnpm test:api`.
- Turbo menjalankan dependensi build sebelum tes. `api` build hanyalah `tsc --noEmit`, bukan penghasil bundle produksi; `pnpm --filter api start` menjalankan TypeScript melalui `tsx`. AI tidak mempunyai task build.
- Script pnpm AI mengunci interpreter ke `apps/ai/.venv/Scripts/python.exe`; tidak otomatis memilih `.venv-rag` atau Python di PATH. Dari root, setup penuh: `python -m venv apps/ai/.venv`, lalu `apps/ai/.venv/Scripts/python.exe -m pip install -r apps/ai/requirements.txt`. Profil minimal/dependensi terkunci dijelaskan di dokumen 19; pytest perlu dipasang terpisah bila hanya memakai dependensi RAG minimal.
- Konfigurasi lokal: `apps/api/.env` (`DATABASE_URL`, `JWT_SECRET`, `AI_URL`), `apps/web/.env.local` (`BACKEND_URL`, `SESSION_SECRET`), dan `apps/ai/.env`. Port lazim web/API/AI adalah 3000/4000/5000; gunakan `127.0.0.1` untuk koneksi lokal Windows.

### Menjalankan satu file atau satu kasus tes

Gunakan runner langsung agar argumen file/kasus tidak tertelan wrapper Turbo:

```powershell
# API: Vitest, environment Node; health tetap memeriksa koneksi DB.
pnpm --filter api exec vitest run tests/health.test.ts
pnpm --filter api exec vitest run tests/health.test.ts -t "mengembalikan status ok"

# Frontend: Vitest + jsdom + React Testing Library.
pnpm --filter web exec vitest run src/lib/utils.test.ts
pnpm --filter web exec vitest run src/lib/utils.test.ts -t "menggabungkan kelas tailwind"

# Python: dari root; prefix pnpm memilih working directory apps/ai.
pnpm --filter ai exec .venv\Scripts\python.exe -m pytest tests/test_answer_policy.py -q
pnpm --filter ai exec .venv\Scripts\python.exe -m pytest tests/test_answer_policy.py::test_ambiguous_price_asks_and_lists_without_guessing -q
```

## Arsitektur lintas aplikasi

Monorepo pnpm + Turbo dengan tiga aplikasi. Alur konsultasi: browser → route handler Next.js → Express `/api/analyze` atau `/api/chat` → FastAPI `/ai/analyze` atau `/ai/chat`. Hasil CV menjadi konteks rambut untuk RAG; runtime AI bukan bagian dari proses Express.

- **`apps/web`**: Next.js 16 App Router, React 19, TypeScript, Tailwind 4. Route handler `src/app/api/` menjadi perantara server-side melalui `src/lib/backend.ts`. Halaman publik, reservasi, dan admin ada di `src/app/`; komponen saat ini di `src/components/`. `src/features/` adalah konvensi target untuk fitur baru, belum struktur yang sudah tersedia. State langkah reservasi memakai `sessionStorage` dan guard redirect. `src/lib/web-session.ts` menyimpan JWT backend + user dalam cookie iron-session `tien_session`, lalu mengirim JWT sebagai Bearer ke Express. `src/proxy.ts` memeriksa keberadaan cookie; layout admin melakukan pemeriksaan session/permission tambahan, dan backend tetap menegakkan otorisasi.
- **`apps/api`**: Express + TypeScript, alur Route → Controller → Service → Repository → PostgreSQL/Knex. `src/app.ts` membangun aplikasi untuk pengujian; `src/index.ts` melakukan bootstrap. Validasi Zod dan error RFC 7807; endpoint AI memvalidasi/rate-limit lalu meneruskan permintaan ke FastAPI. Otorisasi memakai `requireAuth` + `securityEnforce`, permission `<resource>.<action>`, wildcard/ownership, serta bypass superadmin.
- **`apps/ai`**: FastAPI/Python. `app.main:app` adalah aplikasi gabungan CV/RAG; `app.rag_app:app` adalah profil minimal chat/health **tanpa analisis foto**. Jangan menjalankan keduanya pada port yang sama.
- **`packages/shared-types`** menyediakan kontrak Zod bersama FE/BE; `packages/shared-utils` menyediakan helper bersama. Perubahan kontrak chat/CV perlu tetap konsisten dengan model Python dan UI, bukan hanya schema TypeScript.

## RAG: runtime dan penelitian

- Profil operasional yang didokumentasikan adalah **BM25 + katalog layanan live + ChatGPT**. Namun default kode `app/config.py` masih Gemini + Chroma dengan live services nonaktif. Template `.env.chatgpt.example` mengatur `AI_LLM_PROVIDER=chatgpt`, `RAG_RETRIEVAL_PROVIDER=bm25_source_balanced`, `RAG_LIVE_SERVICES=true`, bundle runtime, dan `RAG_CONTEXT_SELECTION=source_scoped`. `start:rag` hanya mengganti entrypoint, **tidak memilih profil konfigurasi atau interpreter minimal secara otomatis**. Periksa konfigurasi sebelum memilih jalur yang diubah.
- `app/rag/rag_service.py` mengorkestrasi jawaban; `catalog_operations.py`/`live_services.py` menangani fakta bisnis, `bm25_retrieval.py`/`lexical_index.py` menangani ranking, dan `evidence_selection.py`/`care_intent.py`/`answer_policy.py` menangani bukti serta klarifikasi. Integrasi ChatGPT memakai login/izin aplikasi sendiri, bukan kredensial Codex atau fallback API berbayar otomatis.
- Harga, durasi, daftar, hitung, filter, dan perbandingan layanan memakai operasi katalog deterministik dengan data `/api/services`. Jangan mengganti kegagalan API dengan harga snapshot. Edukasi perawatan memakai bukti terkurasi; pertanyaan campuran menggabungkan kedua jenis sumber.
- Bundle runtime `apps/ai/rag/runtime/` terpisah dari paket eksperimen beku `apps/ai/rag/eval/`. Ingest Chroma tidak otomatis memperbarui bundle BM25. Pertahankan byte paket/manifes sesuai `.gitattributes`; buat versi/output baru daripada menimpa hasil penelitian.
- Seleksi `source_scoped` dan klarifikasi adalah heuristik operasional; baseline `all` harus tetap dapat dibandingkan tanpa diam-diam memperoleh perluasan istilah baru. `contextId` mengidentifikasi bukti, **bukan memori percakapan**; jangan menganggap route menerima riwayat pesan yang tidak dikirim.
- Web fallback runtime memakai HTTP terbatas, allowlist HTTPS, robots.txt, dan pemeriksaan redirect. Jangan menyamakannya dengan crawler offline lama atau menjadikan artikel belum ditinjau sebagai SOP salon.
- Hasil development, metrik retrieval, audit rute, dan penilaian jawaban adalah pengukuran berbeda. Evaluator AI custom bukan RAGAS/persetujuan manusia; pertahankan nol, missing, dan N/A secara terpisah. Pertanyaan yang sudah dipakai menyetel aturan bukan test independen.

## Batas pekerjaan Computer Vision

- Implementasi CV baru hanya di `apps/api/cv/geometry/` atau `apps/api/cv/annotation/`. Jangan mengubah/menghapus/menimpa `scripts/`, dataset, `preprocessed_*`, bobot, atau label lama. Runtime inferensi yang sudah ada berada di `apps/ai`; roadmap geometris bukan bukti pipeline baru sudah terintegrasi.
- Tentukan fase dari roadmap; baca `docs/07-fase0-verifikasi-gate.md` untuk Fase 0 dan `docs/06-kajian-matematis-referensi.md` untuk dasar angka/rumus. Jangan membangun pipeline geometris sebelum gate MediaPipe back-view lulus. Status kondisional bukan kelulusan; verifikasi artefak keputusan sebelum melanjutkan.
- Gunakan rasio relatif dan head-unit canon 7.5–8, bukan golden ratio φ atau panjang absolut dalam cm. Pseudo-label Gemini/quartile geometris bukan ground truth final.
- Script eksperimen harus mempunyai seed tetap dan `--help`; split mencegah leakage/near-duplicate; laporkan macro-F1, bukan accuracy saja.
- Label kontrak tetap: panjang `pendek`, `pendek-menengah`, `menengah`, `panjang`; jenis `lurus`, `bergelombang`, `keriting`, `sangat-keriting`. Kelas geometris sebahu/sepunggung/dst. harus dipetakan ke kontrak ini, bukan menggantinya. Volume untuk curly/kinky memakai `tipis`/`sedang`/`tebal` sesuai roadmap.

## Konvensi khusus repo

URL/endpoint, kode, dan komentar berbahasa Inggris; UI, error, knowledge base, dan dokumentasi berbahasa Indonesia. Pertahankan URL seperti `/services`, `/reservation`, `/auth`, dan `/consult`, bukan padanan Indonesia dari proyek UI asal. Konfigurasi Biome memakai single quotes, indentasi dua spasi, trailing commas, dan lebar baris 100.
