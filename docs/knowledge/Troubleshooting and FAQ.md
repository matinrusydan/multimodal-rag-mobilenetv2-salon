# Troubleshooting dan FAQ

## Port 3000/4000/5000 sudah digunakan

Skrip dev memakai `scripts/freeport.mjs` untuk membebaskan port. Hentikan proses yang masih memiliki pekerjaan penting sebelum menjalankan ulang. Jangan membunuh semua proses Node/Python secara global.

## Web memperoleh error dari backend

1. Pastikan `BACKEND_URL` pada Web menunjuk origin Express tanpa `/api` di akhir.
2. Pastikan Express aktif pada port 4000.
3. Periksa Problem Details yang dikembalikan BFF; helper `backendRequest` menangani timeout dan respons error.
4. Untuk route terproteksi, cek session Web dan cookie JWT HttpOnly.

## Chat gagal atau timeout

Alur chat melewati Web BFF → Express → FastAPI. Periksa berurutan:

- `/api/health` Express;
- `/ai/health` / readiness FastAPI sesuai deployment;
- kesamaan `AI_INTERNAL_TOKEN` antara Express dan AI;
- `AI_URL` pada Express;
- `API_BASE_URL` pada AI untuk katalog live;
- corpus runtime, login/model ChatGPT dan izin inferensi.

Jangan mencetak token, cookie, URL berisi credential atau traceback locals ke log publik.

## Mengapa `/api/analyze` selalu 503?

Ini perilaku sengaja pada profil RAG-only saat ini. Express mengembalikan “Analisis foto belum tersedia”, dan runtime AI kanonikal tidak memasang router analyze. Modul CV tetap ada untuk riset offline. Jangan mengaktifkan route sebagai perbaikan cepat sebelum gate CV selesai.

## Harga layanan berbeda atau tidak muncul

Fakta bisnis harus berasal dari `/api/services` (layanan aktif). AI memakai katalog live dan tidak seharusnya menggantinya dengan snapshot corpus. Periksa koneksi AI → Express, database dan status aktif layanan. Hindari hardcode harga di prompt/UI.

## Migrasi atau seed gagal

- Verifikasi `DATABASE_URL` dan PostgreSQL.
- Jangan menjalankan repair/seed berulang pada produksi.
- Backup dan gunakan database terisolasi.
- `pnpm db:repair` dapat mengubah skema/data; selalu minta persetujuan.

## Status dokumen berbeda dengan source

Dokumen `docs/00`–`docs/23` mencakup desain dan hasil historis. Utamakan source dan artefak yang bisa direproduksi. Catat drift di `docs/knowledge/TASK.md`, jangan menghapus hasil lama untuk membuat struktur terlihat konsisten.

## Di mana mulai pekerjaan berikutnya?

- Status umum: [TASK](./TASK.md)
- Data/fetching: [Data Fetching](./Architecture%20Overview/Data%20Fetching.md)
- CV: baca `docs/08-roadmap-cv-lengkap.md`, lalu [CV Roadmap Status](./Computer%20Vision%20Research/CV%20Roadmap%20Status.md)
- Dataset: [Dataset and Curation Policy](./Computer%20Vision%20Research/Dataset%20and%20Curation%20Policy.md)
