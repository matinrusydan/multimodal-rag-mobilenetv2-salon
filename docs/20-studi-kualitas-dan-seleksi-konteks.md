# Studi kualitas dan seleksi konteks RAG

Pembaruan 21 Oktober 2026: lihat [dokumen 21](21-penguatan-seleksi-dan-evaluasi-lanjutan.md) untuk selector konservatif terbaru, 171 tes, dan penyelesaian penilaian 24/24 jawaban historis. Angka di bawah tetap merekam studi versi sebelumnya.

Tanggal: 20 Oktober 2026. Seluruh hasil di sini merupakan diagnostik development, bukan test independen atau hasil final publikasi.

## Pekerjaan yang dieksekusi

1. Memvalidasi manifest paket 24 pertanyaan dan 13 evidence. Semua ID gold dapat ditemukan; 15 pertanyaan mempunyai fakta bisnis yang cocok dengan record sumber. Pada 20 pertanyaan ber-gold tidak ada teks gold yang melebihi jendela 400 karakter. Pemeriksaan ini tidak mengesahkan makna acuan atau memberi persetujuan manusia baru.
2. Membandingkan BM25 dan alokasi sumber pada k=1, 2, 3, 4, 5.
3. Menguji seleksi konteks dari maksimal lima kandidat tanpa membaca label gold pada tahap pemilihan.
4. Menghasilkan jawaban aktual untuk seluruh 24 pertanyaan menggunakan snapshot yang sama, tanpa web atau data live yang berubah.
5. Menjalankan enam batch evaluator AI setelah pengguna memberikan izin spesifik pengiriman data. Empat batch selesai; dua batch timeout. Tidak ada retry eksternal tambahan melewati batas enam batch tersebut.
6. Memperbaiki sitasi klarifikasi, instruksi agar tidak mengganti jawaban yang tidak tersedia dengan tips lain, dan penggunaan ulang koneksi HTTP katalog.

## Perbandingan k

| k | Precision@k | Recall@k | F1@k | Kelompok gold lengkap |
|---|---:|---:|---:|---:|
| 1 | 0,9500 | 0,8417 | 0,8750 | 0,7500 |
| 2 | 0,5750 | 0,9583 | 0,6983 | 0,9000 |
| 3 | 0,4000 | 0,9833 | 0,5533 | 0,9500 |
| 4 | 0,3000 | 0,9833 | 0,4486 | 0,9500 |
| 5 | 0,2500 | 1,0000 | 0,3899 | 1,0000 |

Mengganti k menjadi 1 akan menaikkan precision sambil menghilangkan bukti. Karena itu k kandidat tetap 5; konteks akhir dipilih secara terpisah. Pada implementasi baseline yang diuji, reservasi sumber baru berlaku untuk k minimal 3.

## Seleksi konteks yang diaktifkan

`evidence_selection.py` mempertahankan record layanan yang disebut, membedakan kebutuhan bisnis/dokumen, dan memeriksa frasa berurutan pada kueri. Dokumen baru dipadatkan jika satu kandidat mempunyai frasa yang unik dan tidak menghilangkan kata kebutuhan yang hanya dicakup kandidat lain. Saat ragu, kandidat tetap dipertahankan. Nama layanan dikeluarkan dari analisis kebutuhan tambahan, sehingga kata `Styling` pada nama layanan tidak dianggap otomatis sebagai pertanyaan perawatan panas. Istilah conditioner, shampoo, panas dan pertanyaan campuran turut diuji.

Aturan ini merupakan heuristik transparan, bukan pembuktian entailment semantik. Parameter tidak mengambil gold atau jawaban referensi pada saat seleksi.

| Ukuran pada 20 query ber-gold | Semua kandidat | Setelah seleksi |
|---|---:|---:|
| Precision@5, penyebut tetap 5 | 0,2500 | 0,2500 |
| F1@5, memakai Precision@5 | 0,3899 | 0,3899 |
| Precision atas hasil aktual | 0,2500 | 0,7842 |
| F1 atas hasil aktual | 0,3899 | 0,8375 |
| Recall evidence | 1,0000 | 1,0000 |
| Kelompok gold lengkap | 20/20 | 20/20 |
| MAP@5 | 0,9683 | 0,9933 |
| MRR@5 | 0,9750 | 1,0000 |
| Rata-rata jumlah konteks | 5,00 | 2,05 |
| Rata-rata karakter konteks | 951,3 | 356,5 |

Teks konteks berkurang sekitar 62,5%. Ini pengukuran karakter, bukan angka token tagihan atau bukti seluruh aplikasi lebih cepat sebesar persentase yang sama. Tidak ada penurunan cakupan gold pada satu pun query development yang diuji. Precision 0,7842 dan F1 0,8375 **bukan** hasil Precision@5/F1@5 baru. Metode dan penyebut yang berbeda tidak disamakan.

Laporan offline terakhir: `apps/ai/rag/eval/quality-development-offline-v4/report.json` dan `report.md`. Versi antara disimpan untuk jejak pengujian. Hasil sama diuji kembali oleh regresi setelah pemadatan metadata evaluator.

## Jawaban aktual dan evaluator AI

Seluruh 24 pertanyaan menghasilkan jawaban: 7 katalog deterministik, 12 generasi ChatGPT berhasil, 4 batas informasi dan 1 klarifikasi. Median waktu pipeline generatif pada eksperimen snapshot sekitar 5,38 detik, p95 sekitar 9,92 detik dari 12 sampel. Pengukuran tersebut tidak mencakup database live, crawling, frontend, atau cold start cloud.

| Metrik diagnostik AI | Rata-rata | Dinilai | Belum dinilai | N/A |
|---|---:|---:|---:|---:|
| Dukungan klaim/faithfulness | 1,0000 | 16 | 8 | 0 |
| Relevansi jawaban | 0,9875 | 16 | 8 | 0 |
| Dukungan sitasi | 0,9333 | 15 | 8 | 1 |
| Kelengkapan unit acuan | 1,0000 | 16 | 8 | 0 |

Angka dihitung per pertanyaan dari penilaian klaim/unit oleh evaluator custom, bukan library RAGAS. Model generator dan judge sama sehingga berisiko bias. Acuan masih provisional. Tidak boleh menyebut hasil ini akurasi 100%, hasil seluruh 24 pertanyaan, atau penilaian manusia independen.

Batch r13–r16 dan r17–r20 timeout. Delapan nilai tersebut tetap missing, bukan nol/lulus, dan tidak dibuang diam-diam. `supplementary-ai-review.json` berisi ulasan kualitatif AI pendamping atas jawaban dan sumber tersimpan untuk delapan kasus itu; ulasan tersebut tidak digabung sebagai skor judge numerik dan tidak menjadi persetujuan manusia.

Kasus missing mencakup pertanyaan campuran dan jawaban yang lebih panjang. Karena itu, rata-rata 16 kasus yang berhasil dinilai dapat terlalu optimistis dan tidak mewakili distribusi lengkap 24 pertanyaan.

Temuan yang ditindaklanjuti:

- r21: opsi katalog benar tetapi tidak mempunyai sitasi inline. Setiap pilihan sekarang ditautkan `[1]` ke sumber katalog bernomor 1. Perbaikan format sudah diverifikasi pada respons HTTP nyata, tanpa mengubah skor historis 0,9333 menjadi 1 secara sepihak.
- r08: jawaban mengakui tidak ada petunjuk sampo setelah pewarnaan, tetapi menambahkan tips kondisioner yang tidak diminta. Instruksi generasi diperketat agar tidak mengganti kebutuhan utama yang belum didukung dengan tips lain. Belum dilakukan penilaian generatif ulang setelah perubahan instruksi ini.
- Evaluator berikutnya memakai kebijakan bersama satu kali per batch, menghapus metadata internal yang tidak diperlukan, dan tidak menduplikasi snippet pada daftar sitasi. Ini mengurangi payload; efek terhadap timeout belum diuji dengan panggilan eksternal baru.
- Klaim yang diekstrak judge harus benar-benar muncul pada jawaban tersimpan; dukungan ID, format nilai dan skor nol diperiksa. CLI berikutnya menghasilkan status/exit berbeda bila penilaian AI masih parsial.

Laporan utama: `apps/ai/rag/eval/quality-development-v1/report.json` dan `report.md`. Raw prompt, respons judge, jawaban aktual, error dan hash disimpan. Laporan ini merekam keluaran sebelum perbaikan sitasi/instruksi sesudah diagnosis; tidak ditimpa agar tampak lebih baik.

## Operasi dan pengukuran lokal

Konfigurasi lokal `RAG_CONTEXT_SELECTION=source_scoped` sudah diaktifkan. Untuk pembanding gunakan `all`; `RAG_TOP_K=5` dan `RAG_CONTEXT_STRATEGY=head` tetap. Server RAG direstart untuk membaca kode dan konfigurasi terbaru.

Pada profil `app.rag_app`, koneksi HTTP katalog dipakai ulang selama umur aplikasi dan ditutup saat shutdown. Data layanan tetap dibaca ulang pada setiap permintaan; tidak ada cache harga. Tes membuktikan harga baru terbaca pada permintaan berikutnya.

Pengujian lokal melalui Express memakai enam permintaan deterministik per tingkat concurrency, tanpa LLM:

| Concurrency | Sukses sebelum/sesudah | Median sebelum | Median sesudah | p95 sesudah |
|---|---|---:|---:|---:|
| 1 | 6/6 dan 6/6 | 0,315 s | 0,012 s | 0,116 s |
| 3 | 6/6 dan 6/6 | 0,828 s | 0,019 s | 0,024 s |

Sampel kecil dan urutan tidak diacak; hasil ini eksploratif, bukan jaminan kapasitas deployment. Concurrency generatif dan cold start cloud belum diuji. Tidak ada migrasi, seed, perubahan data salon atau perubahan CV dalam pekerjaan ini.

## Reproduksi

Dari `apps/ai`:

```powershell
# Tanpa pengiriman data/model:
.\.venv\Scripts\python.exe -m app.rag.quality_study --out rag/eval/quality-offline-baru

# Menggunakan kuota ChatGPT dan mengirim data sesuai lingkup evaluasi:
# Hanya jalankan bila memang ingin melakukan batch eksternal baru.
.\.venv\Scripts\python.exe -m app.rag.quality_study --out rag/eval/quality-ai-baru --allow-model
```

Dari root: `pnpm test:rag`. Verifikasi akhir: 165 tes RAG lulus. Dataset lama, anotasi Matin sebelumnya, dan hasil metrik historis tetap dipertahankan; persetujuan manusia atau test independen tidak dibuat otomatis.
