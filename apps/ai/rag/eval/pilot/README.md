# Pilot penelitian RAG salon

Paket ini menjalankan tahap audit dan pilot awal dari usulan RP–RQ–RO. Semua query adalah draft berbantuan asisten untuk ditinjau peneliti pada tahap development; belum ada data pelanggan nyata dan bukan test final yang dikunci.

## Berkas

| Berkas | Kegunaan |
|---|---|
| `services.snapshot.json` | Ekspor PostgreSQL aktual enam layanan aktif dalam transaksi read-only; tidak berasal dari seed atau Markdown. |
| `inventory.json` | Enam dokumen lokal, hash, jumlah chunk, topik, dan status sumber. |
| `corpus.json` | 51 unit evidence: enam record layanan dan 45 chunk dokumen. |
| `questions.md` / `questions.json` | 24 pertanyaan, jawaban acuan draft, field bisnis, evidence, serta answerability. |
| `annotation_sheet.json` | Lembar verifikasi manual. Nilai kualitas jawaban masih null karena belum ada generasi jawaban. |
| `retrieval_report.md` / `.json` | Hasil retrieval dan konteks aktual per query/metode. |

## Cara menjalankan ulang

Dari root repository, ekspor ulang snapshot hanya bila memang ingin membuat versi data baru:

```powershell
node apps/api/tools/export_rag_pilot.mjs
```

Ekspor hanya membaca field publik tabel services. Tidak menjalankan server, migrasi atau seed. Tidak mengambil users, reservasi, token, maupun kredensial. Snapshot menyatakan isi database lokal, bukan konfirmasi bahwa pemilik salon telah menyetujui seluruh nilainya.

Dari `apps/ai`, jalankan pilot gratis:

```powershell
.venv\Scripts\python.exe -m app.rag.pilot --help
.venv\Scripts\python.exe -m app.rag.pilot
```

Jika data berubah, buat versi keluaran baru dengan `--out rag/eval/pilot-versi-baru`. Lembar anotasi yang sudah ada dipertahankan; input yang tidak cocok akan ditolak agar verifikasi manusia tidak tertimpa.

## Yang sudah dan belum diukur

- BM25 adalah baseline leksikal yang dijalankan nyata pada korpus lokal.
- `hash_proxy` dan `hybrid_rrf_hash_proxy` memakai feature hashing leksikal deterministik, **bukan neural dense retrieval**. Hasilnya kontrol engineering, bukan pembanding state-of-the-art.
- Seluruh metode menerima 51 evidence yang sama dan top-k 5. Tidak menggunakan routing usulan agar baseline tidak disamarkan sebagai intervensi.
- Retrieval dinilai atas label evidence draft. Tiga query ambigu/tidak terjawab tidak mempunyai gold evidence, sehingga denominator retrieval 21/24; ini tidak berarti tiga query tersebut berhasil dijawab.
- Precision memakai jumlah hasil aktual; recall memakai union label relevan; bukti lengkap memakai kelompok kebutuhan. Label alternatif yang belum ditambahkan dapat mengubah hasil.
- Tidak ada generasi LLM, faithfulness, kebenaran jawaban, sitasi, atau latensi end-to-end yang sudah diukur. Kolom terkait tetap null/not_run.
- Dokumen perawatan masih Markdown manual tanpa bibliografi primer. Jangan menjadikannya gold klinis atau dasar rekomendasi pengobatan. Pilot ini hanya mengecek apakah teks sumber ditemukan.

## Perbaikan evaluator

`app/rag/eval_rag.py` sekarang menggunakan trace dari satu proses jawaban: konteks yang telah dipotong sesuai prompt, tanpa retrieval kedua. Rubrik disebut **custom LLM judge**, bukan implementasi library RAGAS. Nol sah tetap dihitung; kegagalan menjadi null; retry hanya memproses null dan menolak pergantian model dalam report yang sama. Report lama `ragas_report*` tidak ditimpa.

Evaluator API bersifat opt-in dan belum dijalankan. `--help` tersedia tanpa panggilan model. Eksekusi memerlukan `--allow-api`, `--generation-model`, dan `--judge-model` eksplisit. Model harus diverifikasi ketersediaannya sendiri; tidak ada asumsi nama model tertentu valid. Web dinonaktifkan; embedding strict menolak fallback lokal. Sebelum eksperimen final, index juga harus dibangun dalam direktori terpisah dengan model embedding yang diketahui dan dicatat. Strict query saja tidak memvalidasi embedding index lama.

## Gate berikutnya

1. Tinjau 24 item melalui `questions.md`, lalu koreksi label/bukti dalam dataset berversi; catat reviewer dan alasan pada lembar anotasi.
2. Konfirmasi field harga dan kebijakan promo dengan sumber bisnis yang berwenang. Harga promo di Markdown tidak otomatis menjadi field harga DB.
3. Ganti/tambahkan sumber pengetahuan perawatan yang terkurasi dan memiliki provenance; bila crawl digunakan, verifikasi robots.txt sebelum akses. Pilot ini tidak melakukan crawl.
4. Baru jalankan baseline neural dense dan hybrid dengan embedding tetap, lalu generasi dengan model tetap bila sumber daya tersedia. Jangan menamai kontrol hashing sebagai dense neural.
5. Putuskan intervensi source routing dari kegagalan yang nyata; jangan menyatakan gap atau peningkatan metode sudah terbukti oleh skor draft ini.
