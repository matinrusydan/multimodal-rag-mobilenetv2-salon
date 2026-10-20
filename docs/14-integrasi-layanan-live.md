# Integrasi katalog layanan aktif untuk konsultasi

Tanggal pemeriksaan: 20 Oktober 2026.

## Perilaku aplikasi

Route FastAPI `/ai/chat` memakai `RAG_LIVE_SERVICES=true` dari konfigurasi lokal. Pada setiap permintaan, brain engine membaca `GET /api/services` di Express melalui `API_BASE_URL`. Endpoint ini mengambil record `services` dengan `is_active=true` di PostgreSQL. Tidak ada cache katalog di brain engine dan tidak ada migrasi atau perubahan data dalam implementasi ini.

Katalog aktif menggantikan seluruh record database snapshot di korpus sementara untuk permintaan tersebut. Dokumen edukasi terkurasi tetap dipakai. BM25 atau BM25 dengan pembagian sumber berjalan atas korpus sementara itu. Harga dan durasi tidak memerlukan ingest ulang ketika data berubah. Pembacaan tersebut mencerminkan waktu permintaan, bukan penguncian harga untuk reservasi berikutnya.

Jika layanan pada pertanyaan belum jelas, sistem meminta nama layanan dan menawarkan pilihan dari katalog aktif tanpa memanggil LLM. Label sumber layanan menjadi `Data layanan: ... (database aktif)`. `services.live.json` merupakan identitas bukti sementara dalam respons; ini bukan file snapshot yang ditulis ke disk. Trace menyimpan waktu pembacaan, hash isi record, serta potongan bukti yang dipakai.

Jika API gagal, respons atau struktur data tidak valid, record harga snapshot tidak dimasukkan sebagai pengganti. Instruksi generasi menjelaskan bahwa data layanan aktif tidak dapat diperiksa. Pada mode tanpa generasi, pesan kegagalan tersebut ditambahkan secara eksplisit. Sistem tetap dapat mengambil sumber edukasi. Timeout pembacaan katalog adalah delapan detik.

Diskon, masa berlaku promo, histori harga, dan instruksi khusus setelah layanan belum tersedia di endpoint katalog. Sistem tidak boleh menyimpulkannya dari harga reguler. Perubahan skema untuk diskon atau histori menjadi pekerjaan terpisah.

## Pemisahan dari eksperimen penelitian

`RagService.answer()` tetap memakai snapshot secara default. Route HTTP mengaktifkan opsi `live_services` secara eksplisit sesuai konfigurasi server. Pemanggilan evaluasi Python yang ada tidak mengaktifkan opsi ini, sehingga korpus dan jawaban acuan penelitian tidak ikut berubah mengikuti database operasional.

Jika suatu eksperimen kelak menguji perubahan harga, peneliti perlu membuat skenario dan versi data tersendiri serta menyimpan keadaan sebelum dan sesudah perubahan. Hasil eksperimen snapshot sebelumnya tidak berubah menjadi hasil evaluasi data live.

## Verifikasi

- 80 tes lokal lulus, termasuk tujuh kasus baru untuk integrasi katalog: perubahan harga pada permintaan berikutnya; layanan nonaktif; API gagal; angka tidak valid; klarifikasi dari katalog aktif; pemisahan evaluasi snapshot; pengaktifan opsi pada route.
- Tes perubahan harga dan status memakai API tiruan. Database salon tidak diubah.
- API lokal yang sedang berjalan berhasil mengembalikan enam layanan aktif.
- Satu generasi ChatGPT dengan data API lokal menjawab Volume Blowout Styling Rp280.000 dan 55 menit dengan sitasi layanan aktif.
- Route HTTP diuji di proses Python baru untuk klarifikasi katalog aktif. Proses aplikasi lama pada port 5000 memerlukan restart untuk membaca perubahan kode dan `.env`.
- Sitasi masih merupakan atribusi model; entailment belum diperiksa oleh penilai independen. Pemeriksaan ini bukan evaluasi akurasi menyeluruh.

Laporan pemeriksaan: `apps/ai/rag/eval/online-smoke-chatgpt/live-catalog-check.json`.

## Menjalankan perubahan

Restart proses pengembangan yang sedang menjalankan brain engine. Jika memakai `pnpm local`, hentikan proses itu dan jalankan lagi dari root proyek, kemudian muat ulang halaman konsultasi.

Untuk mengembalikan route HTTP ke snapshot penelitian, ubah `RAG_LIVE_SERVICES=false` dan restart. Mode live saat ini memerlukan `RAG_RETRIEVAL_PROVIDER=bm25` atau `bm25_source_balanced`.
