# Implementasi dan eksperimen IR untuk RAG salon

Tanggal: 20 Oktober 2026. Pedoman: `docs/17-pedoman-ir-untuk-rag.md`, materi STBI, serta materi Penulisan Ilmiah. Status: implementasi dan eksperimen komponen development; belum hasil final publikasi.

## Perubahan yang dijalankan

| Kebutuhan | Implementasi | Batas interpretasi |
|---|---|---|
| Indeks sebelum query | `lexical_index.py`: DF, IDF, panjang, TF/postings dan normalisasi BM25 disiapkan sekali; cache maksimal dua versi konten | Parameter tetap k1=1,5 dan b=0,75; indeks bukan algoritma baru |
| Runtime terpisah dari pilot | `query_planning.py` dan `bm25_retrieval.py` memakai komponen runtime; baseline lama di pilot dipertahankan | Perilaku source-balanced lama dipertahankan untuk perbandingan |
| Pembaruan katalog | Konten harga/durasi yang berubah mengubah kunci indeks; timestamp pembacaan API saja dihapus dari teks ranking | Metadata dan teks sumber lengkap tetap tersedia. Ini tidak membuat database histori atau promo |
| Metrik ranking eksplisit | `ir_metrics.py`: P@k ketat, precision hasil aktual, Recall@k, F1, AP/MAP, RR/MRR, nDCG dan cakupan kelompok evidence | Label saat ini biner; gold kosong menghasilkan N/A. Tidak mengubah laporan historis |
| Cuplikan yang terlacak | `context_selection.py`: head atau query_window; offset dan hash teks penuh/teks yang digunakan tercatat di trace | Head tetap default. Query window masih pilihan eksperimen, bukan perbaikan kualitas yang sudah terbukti |
| Identitas konteks | `rag_service.py`: contextId ikut berubah bila cuplikan/strategi berubah | Adanya ID atau sitasi tidak otomatis membuktikan dukungan klaim |
| Audit jawaban | `answer_audit.py`: fakta terikat ke ID layanan+field, kelengkapan field wajib, penilaian klaim/sitasi/kebijakan manual | Tanpa reviewer, persetujuan dan jawaban aktual, tidak dihasilkan skor kualitas |
| Pemisahan data | `split_guard.py`: keluarga skenario tidak boleh menyeberang development/test; test harus disetujui dan dikunci | Kemiripan makna tetap diperiksa manusia; kandidat tambahan bukan test independen yang siap digunakan |

`RAG_CONTEXT_STRATEGY=head` ditambahkan ke `.env.example`. Pengaturan aplikasi berjalan tidak diubah untuk memaksakan strategi cuplikan baru. Tidak ada migrasi database, seed, perubahan CV atau panggilan LLM pada pekerjaan ini.

## Eksperimen yang sudah dieksekusi

Laporan terbaru: `apps/ai/rag/eval/ir-experiment-v2/report.json` dan `report.md`. Eksekusi v2 menyertakan hash delapan file implementasi, waktu UTC dan identitas lingkungan; hasil v1 tetap dipertahankan. Kedua eksekusi menghasilkan ranking dan metrik yang sama. Template cuplikan v1 tetap sesuai dengan konteks aktual yang sama pada v2.

Input versi `curated-development-v2`: 13 evidence dan 24 query. Dua puluh query memiliki gold retrieval; empat lainnya tidak diberi skor retrieval karena membutuhkan penilaian kebijakan/keterjawaban. Acuan revisi belum seluruhnya disetujui ulang oleh peneliti. Seluruh data tetap development dan tidak dipromosikan menjadi test set.

| Metode pada k=5 | P@5 ketat | Recall@5 | F1@5 | MAP@5 | MRR@5 | nDCG@5 biner | Kelompok bukti lengkap |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 scan | 0,2400 | 0,9750 | 0,3756 | 0,9433 | 0,9750 | 0,9595 | 19/20 |
| BM25 berindeks | 0,2400 | 0,9750 | 0,3756 | 0,9433 | 0,9750 | 0,9595 | 19/20 |
| Alokasi tanpa pemisahan kueri | 0,2400 | 0,9750 | 0,3756 | 0,9433 | 0,9750 | 0,9595 | 19/20 |
| Alokasi dengan pemisahan kueri | 0,2500 | 1,0000 | 0,3899 | 0,9683 | 0,9750 | 0,9789 | 20/20 |

Semua metode memakai korpus, tokenisasi, parameter, query, dan k yang sama. BM25 scan dan berindeks menghasilkan ranking identik pada semua query. Laporan juga menyimpan hasil per kategori, setiap query, kedua strategi cuplikan, dan interval bootstrap berpasangan seed 42. Interval tersebut hanya deskripsi development kecil yang sudah digunakan menyetel sistem; bukan bukti signifikansi atau generalisasi.

Recall tinggi bersama P@5 rendah bukan kontradiksi: gold per query sedikit, sementara sistem mengambil lima item. Cakupan kelompok gold 20/20 juga belum membuktikan bahwa semua teks pendukung bertahan setelah dipotong atau jawaban LLM benar.

### Pengukuran komponen lokal

| Evidence | Bangun indeks ms | Scan median ms | Indexed median ms | Alokasi+pemisahan median ms | Alokasi indeks Python KiB |
|---|---:|---:|---:|---:|---:|
| 13 | 1,052 | 1,095 | 0,066 | 0,226 | 60,3 |
| 130 | 15,736 | 10,892 | 0,476 | 1,421 | 225,1 |
| 1300 | 60,752 | 108,912 | 5,654 | 14,332 | 1959,9 |

Sepuluh ulangan waktu per metode; teks dimuat sebelumnya. Ukuran 130 dan 1300 berasal dari pengulangan sintetis 13 teks, bukan akuisisi dokumen baru. Waktu kueri mencakup pemeriksaan cache indeks pada jalur indexed. Bangun indeks dan pengukuran alokasi Python dilakukan terpisah dari ulangan waktu. RSS di JSON adalah pembacaan proses keseluruhan, bukan peak per metode. Hasil ini belum mengukur parsing input, jaringan, database, generasi, cold start atau concurrency dan belum membuktikan seluruh aplikasi ringan di Vercel/Railway.

## Protokol dan pekerjaan manusia yang tersisa

`apps/ai/rag/eval/ir-protocol-v1/` berisi protokol JSON, 24 template review jawaban/acuan dengan respons Matin sebelumnya sebagai lineage, 48 template pemeriksaan cuplikan, dan review pemisahan keluarga skenario. Dua belas pertanyaan tambahan masih kandidat draft dengan gold kosong; tidak langsung digunakan sebagai test.

Eksekusi audit template menghasilkan **24 pending, 0 jawaban dinilai**. Validasi split menghasilkan **not_ready** karena keluarga skenario belum ditetapkan. Ini status kesiapan data yang sebenarnya, bukan kegagalan model. Tidak ada nilai K/R/D/S/A atau persetujuan manusia yang dibuat otomatis.

Urutan berikutnya:

1. Peneliti meninjau acuan revisi dan bukti yang diusulkan, termasuk batas SOP perawatan/produk rahasia. Pilih field wajib sesuai pertanyaan, bukan seluruh field record.
2. Periksa teks pendukung pada cuplikan aktual; tandai klaim yang tidak terdukung, hilang setelah pemotongan, atau membutuhkan sumber tambahan.
3. Tetapkan keluarga skenario. Pertanyaan yang sudah digunakan mengembangkan sistem tetap development. Tambah kebutuhan baru yang cukup beragam, periksa overlap dan bukti, kemudian kunci test sebelum menjalankan perbandingan final.
4. Jalankan generasi dengan konfigurasi tetap dan anggaran yang tersedia; simpan jawaban aktual beserta konteks. Nilai fakta, kelengkapan, dukungan klaim, sitasi, dan fallback dari keluaran tersebut.
5. Laporkan trade-off, error, N/A dan missing secara terpisah. Jangan hanya memilih hasil non-zero atau mengubah test untuk memperbaiki skor.

Sumber proposal yang sudah terbuka di editor diperbarui pada `output/pdf/usulan-rag-salon/main.tex`: judul kerja menyebut BM25, baseline sesuai implementasi, definisi precision konsisten, RQ/RO mencakup pengujian komponen dan jawaban, dan hasil development diberi batas klaim. Perintah rotasi khusus pdfTeX diganti `pdflscape` agar kompatibel dengan compiler editor. Kompilasi bawaan berhasil; file `main.pdf` lama di folder tidak dianggap otomatis sebagai ekspor terbaru dari preview editor.

## Reproduksi

Dari `apps/ai`, gunakan nama folder/file hasil baru agar hasil lama tidak ditimpa:

```powershell
.\.venv\Scripts\python.exe -m app.rag.experiment_ir --out rag/eval/ir-experiment-v3 --repeats 10
.\.venv\Scripts\python.exe -m app.rag.split_guard --input rag/eval/ir-protocol-v1/split-review.template.json --require-locked-test
.\.venv\Scripts\python.exe -m app.rag.answer_audit --annotations rag/eval/ir-protocol-v1/answer-review.template.json --out rag/eval/ir-protocol-v1/answer-review-status-v2.json
```

CLI memvalidasi manifest input sebelum eksperimen dan memeriksa ulang hash setelah eksperimen. Semua paket acuan/hasil sebelumnya dipertahankan. Exit non-zero dari validasi template split adalah hasil yang diharapkan sampai peninjauan selesai.

## Verifikasi implementasi

Sebanyak 125 tes Python terkait RAG lulus: fondasi IR baru, operasi katalog, validasi paket evaluasi, layanan aktif, kebijakan jawaban, integrasi ChatGPT, baseline, pilot, ingest, retriever, dan antibot. Pemeriksaan terakhir pada fondasi IR setelah penambahan provenance juga lulus (11 tes). Tes mencakup kesetaraan skor/ranking indeks, invalidasi harga, perbedaan denominator precision, AP/MRR/nDCG, cuplikan yang sama antara prompt dan trace, identitas konteks, fakta yang terikat ke layanan, serta kebocoran keluarga skenario. Ini bukan klaim seluruh tes monorepo atau pengujian deployment telah dijalankan.

Hasil per-query, ranking dan cuplikan dari eksekusi v1/v2 dibandingkan dan identik; delapan hash implementasi di laporan v2 cocok dengan file yang dieksekusi. Kompilasi LaTeX bawaan berhasil setelah penyesuaian `pdflscape`.
