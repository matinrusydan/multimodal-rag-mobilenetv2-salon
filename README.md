# RAG-Salon — TIEN Salon

Prototipe konsultasi layanan/perawatan rambut berbasis **Retrieval-Augmented Generation**.
Monorepo pnpm + Turbo: Next.js, Express, FastAPI, dan PostgreSQL.

## Profil aplikasi saat ini

- Konsultasi teks: **BM25 + seleksi bukti + katalog layanan live + ChatGPT** melalui izin aplikasi sendiri.
- Harga/durasi berasal dari API layanan aktif; kegagalan katalog tidak diganti harga snapshot.
- Tombol **Analisis Foto** menampilkan **“Fitur belum tersedia”**. Endpoint analisis mengembalikan HTTP 503, bukan memproses foto.
- Implementasi/dataset/bobot CV dan artefak penelitian tetap disimpan untuk tahap berikutnya, tetapi tidak menjadi dependensi runtime produksi.
- Draf paper dan hasil development bukan bukti kualitas produksi atau hasil uji independen.

**Panduan deployment:** [docs/23-deployment-rag-only.md](docs/23-deployment-rag-only.md).
Target: **Vercel (web) + Railway (API, AI, PostgreSQL)**; image backend juga dapat digunakan di Render.
Persiapan konfigurasi tidak berarti layanan sudah dideploy atau izin inferensi cloud sudah terverifikasi.

## Arsitektur

```text
Browser → Next.js /api/* → Express /api/* → FastAPI /ai/*
                                ↓               ↓
                           PostgreSQL     katalog live dari Express
                                         + bundle bukti runtime
                                         + ChatGPT application grant
```

| App | Teknologi | Port lokal |
|---|---|---|
| `apps/web` | Next.js 16, React, TypeScript | 3000 |
| `apps/api` | Express, Knex, PostgreSQL, JWT/RBAC | 4000 |
| `apps/ai` | FastAPI, BM25, ChatGPT | 5000 |

`app.rag_app:app` merupakan komposisi AI ringan; `app.main:app` adalah entrypoint kompatibilitas.
Keduanya tidak memuat model CV. Agent admin dan knowledge CRUD dipertahankan; crawler/reingest
legacy tidak tersedia pada profil BM25 minimal. Mengedit knowledge legacy tidak otomatis
mengubah bundle BM25 yang terversi.

## Setup lokal

Prasyarat: **Node.js 22.x**, **pnpm 10.15.1**, PostgreSQL, dan Python 3.13 untuk profil minimal.
Konfigurasi development dan produksi berbeda; jangan mengandalkan default Gemini/Chroma pada
kode untuk menjalankan profil ChatGPT.

1. Pasang workspace dengan `pnpm install`.
2. Siapkan konfigurasi lokal dari contoh masing-masing app, tanpa meng-commit secret.
3. Ikuti [setup RAG minimal](docs/19-finalisasi-rag-dan-operasional.md) untuk venv,
   provider, model yang diizinkan akun, dan corpus runtime.
4. Siapkan database/migrasi/RBAC setelah memastikan target database benar. Jangan menjalankan
   demo seed pada produksi.

```powershell
# Dari root; scripts development saat ini memakai venv Windows.
pnpm local

# Atau jalankan satu app; jangan duplikasi AI pada port 5000.
pnpm --filter web dev
pnpm --filter api dev
pnpm --filter ai start:rag
```

**Perhatian:** `pnpm local` sudah menjalankan AI. Script dev memakai `freeport.mjs`, yang dapat
menghentikan proses lain pada port aplikasi. Gunakan Docker/production commands pada hosting,
bukan script dev tersebut.

## Pemeriksaan dan pengujian

```powershell
pnpm --filter api typecheck
pnpm --filter web typecheck
pnpm --filter web test
pnpm --filter web build
pnpm test:rag
```

**Jangan menjalankan `pnpm test`, `pnpm test:api`, migrasi, atau seed terhadap database produksi.**
Sebagian tes API memanggil `prepareDb()` yang menghapus dan membuat ulang tabel menggunakan
`DATABASE_URL` biasa. Gunakan database disposable dan persetujuan operator.

`pnpm lint`/`pnpm lint:fix`, migrasi, dan seed perlu konfirmasi sesuai aturan proyek.
Tidak ada migrate/seed/repair otomatis pada startup image.

## Data dan operasi

- **Liveness:** `/api/health`, `/ai/health`.
- **Readiness:** `/api/ready`, `/ai/ready`; readiness tidak melakukan generasi berbayar/berkuota.
- **Session ChatGPT:** volume privat writable Linux melalui `XDG_DATA_HOME=/data`; satu replica AI.
- **Corpus runtime:** `apps/ai/rag/runtime/`, dibundel immutable bersama manifest/checksum.
- **Knowledge legacy:** direktori persistent terpisah; bukan corpus runtime aktif.
- **Database:** PostgreSQL terkelola dengan backup dan TLS sesuai provider.

Tidak menyalin file kredensial DPAPI Windows ke Linux. Initial login/re-auth ChatGPT pada cloud
memerlukan langkah operator dan transport loopback yang aman; detail dan gate-nya ada pada runbook.
Tidak ada fallback otomatis ke API berbayar atau kredensial aplikasi lain.

## Referensi

- [Deployment RAG-only](docs/23-deployment-rag-only.md)
- [Arsitektur](docs/01-arsitektur.md)
- [Setup development dan profil lama](docs/02-setup.md)
- [Operasional RAG minimal](docs/19-finalisasi-rag-dan-operasional.md)
- [Seleksi bukti dan evaluasi](docs/21-penguatan-seleksi-dan-evaluasi-lanjutan.md)
- [Penanganan ambiguitas](docs/22-penanganan-ambiguitas-konsultasi.md)
- [Roadmap CV — acuan tertinggi pekerjaan CV](docs/08-roadmap-cv-lengkap.md)
