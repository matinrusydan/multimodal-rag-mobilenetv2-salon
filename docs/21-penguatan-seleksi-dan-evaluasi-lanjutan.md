# Penguatan seleksi bukti dan evaluasi lanjutan

Pembaruan: [dokumen 22](22-penanganan-ambiguitas-konsultasi.md) mencatat perbaikan ambiguitas kondisioner, rujukan yang belum jelas, dan pengujian endpoint terbaru. Angka dalam dokumen ini tetap merekam studi sebelumnya.

Tanggal lokal: 21 Oktober 2026. Dokumen ini memperbarui status pada dokumen 20; laporan historis tidak diubah.

## Perubahan program

Seleksi `source_scoped_v2` mempertahankan kutipan yang mempunyai kalimat pengecualian atau kondisi berbeda dari kandidat dengan frasa paling cocok. Contohnya: kutipan umum tentang penggunaan kondisioner tidak boleh menghilangkan larangan pada akar atau petunjuk khusus rambut lurus hanya karena kecocokan frasanya lebih tinggi. Penjagaan mengenali penanda leksikal seperti `jangan`, `hindari`, `jika`, `kecuali`, `untuk rambut`, dan beberapa padanan Inggris. Kalimat identik tetap dapat dipadatkan.

Ini perlindungan konservatif, bukan pengenal semua kondisi atau pembuktian entailment semantik. Tidak ada gold atau jawaban referensi yang dibaca selector. Server RAG lokal telah direstart menggunakan perubahan ini; endpoint `/ai/health` kembali sukses. Tidak ada migrasi, seed, perubahan CV, atau push Git.

## Pengukuran ulang pada development

Dataset tetap 24 pertanyaan, dengan 20 pertanyaan ber-gold retrieval. Angka berikut membandingkan selector sebelum dan setelah penjagaan kondisi, bukan membandingkan dua generator.

| Ukuran | Versi sebelumnya | Versi dengan penjagaan kondisi |
|---|---:|---:|
| Precision hasil aktual | 0,7842 | 0,7175 |
| F1 hasil aktual | 0,8375 | 0,7942 |
| Recall evidence | 1,0000 | 1,0000 |
| Kelompok bukti lengkap | 20/20 | 20/20 |
| Precision@5, penyebut tetap 5 | 0,2500 | 0,2500 |
| F1@5 | 0,3899 | 0,3899 |
| Rata-rata karakter konteks | 356,50 | 377,95 |
| Rata-rata jumlah konteks | 2,05 | 2,20 |

Precision turun karena sebagian kutipan tambahan yang mengandung kondisi dipertahankan, sementara label relevansi lama tetap sama. Ini tidak membuktikan kutipan tambahan relevan maupun tidak relevan secara semantik. Pengesahan alternatif bukti masih memerlukan anotasi. Dibanding memakai lima kandidat seluruhnya (951,3 karakter), konteks versi terbaru sekitar 60,3% lebih pendek. Jangan menyamakan persentase karakter dengan pengurangan token, biaya, atau latensi aplikasi.

Laporan: `apps/ai/rag/eval/quality-development-offline-v5/report.json` dan `report.md`.

## Penilaian delapan jawaban yang sebelumnya timeout

Empat batch baru berisi masing-masing dua jawaban tersimpan berhasil. Tidak ada regenerasi jawaban atau pengulangan 16 penilaian yang sudah selesai. Model tetap sama, memakai izin aplikasi ChatGPT yang sudah ada tanpa fallback API berbayar. Hash paket acuan dan laporan asal diverifikasi. Rubrik sama; metadata diminimalkan dan ukuran batch berubah. Efek perubahan komposisi batch terhadap judge belum dikontrol.

| Metrik evaluator AI custom | Rata-rata gabungan | Dinilai | Missing | N/A |
|---|---:|---:|---:|---:|
| Faithfulness | 0,9965 | 24 | 0 | 0 |
| Relevansi jawaban | 0,9875 | 24 | 0 | 0 |
| Dukungan sitasi | 0,9565 | 23 | 0 | 1 |
| Kelengkapan unit acuan | 1,0000 | 24 | 0 | 0 |

Angka ini menilai **jawaban historis**, bukan jawaban yang dihasilkan ulang setelah perbaikan prompt, sitasi, dan selector. Ini bukan RAGAS, akurasi 100%, anotasi manusia, atau hasil test independen. Generator dan judge memakai model sama; acuan tetap provisional.

Satu klaim pada r16 dinilai tidak didukung: kata `penelitian` dalam kalimat tentang snapshot 20 Oktober 2026. Judge mengakui tanggalnya didukung tetapi menafsirkan label tersebut tidak tersedia dalam kebijakan yang diberikan. Ini kandidat ketidaksepakatan anotasi/metadata; perlu pemeriksaan manusia. Nilainya tidak diubah sepihak untuk menaikkan faithfulness. Nilai nol sitasi historis r21 tetap dihitung, walaupun format sitasinya sudah diperbaiki pada program.

Laporan lengkap dan raw respons: `apps/ai/rag/eval/quality-resume-v1/report.json`. Laporan asal `quality-development-v1/report.json` tetap utuh. CLI `app.rag.resume_quality` hanya memilih penilaian missing, menolak laporan dengan ID duplikat, dan tidak mengganti jawaban tersimpan.

## Pertanyaan baru dan batas temuan

`apps/ai/rag/eval/quality-development-offline-v5/new-question-probes.json` menyimpan 12 variasi pertanyaan beserta kandidat, hasil seleksi, dan keluaran katalog deterministik bila tersedia. Pencocokan nama/alias, kapitalisasi/spasi, dua layanan, nama tak dikenal, typo, dan substring semuanya memenuhi 12/12 invariant pencocokan yang ditetapkan pengembang. Tidak ada panggilan model pada probe ini.

Angka 12/12 **hanya** untuk pencocokan layanan, bukan keberhasilan jawaban, recall dokumen, atau ketepatan edukasi. Semua label semantik dan jawaban acuan probe masih kosong serta berstatus pending; pertanyaan buatan AI ini sudah dilihat selama pengembangan sehingga tidak boleh disebut test independen.

Temuan terbuka: kueri `Harga Signature Hair Spa dan cara memakai conditioner?` memilih kutipan leave-in, sementara instruksi kondisioner bilas merupakan kebutuhan berbeda yang mungkin dimaksud. Pencocokan lintas istilah Inggris/Indonesia dan klarifikasi bilas/leave-in perlu eksperimen tersendiri. Jangan mengesahkan kutipan tersebut hanya karena mengandung kata conditioner. Pertanyaan nama tidak dikenal/typo juga memerlukan verifikasi jalur klarifikasi end-to-end, bukan kesimpulan dari selector saja.

## Verifikasi dan langkah penelitian berikutnya

171 tes RAG lulus. Pemeriksaan operasi lokal: 17/17 lulus tanpa generasi LLM; sebagian proxy diperiksa sebelum restart, health diperiksa setelah restart. Uji baru memeriksa pengecualian/kondisi, pemadatan kalimat identik, serta bahwa resume tidak mengubah laporan asal dan tidak menghilangkan skor nol atau N/A. `git diff --check` lulus.

Prioritas berikutnya adalah mengesahkan acuan dan alternatif bukti secara manual, menetapkan cara menangani istilah ambigu (misalnya kondisioner bilas versus leave-in), lalu mengunci protokol dan memperoleh pertanyaan test dari pemeriksa manusia yang tidak digunakan untuk menyetel aturan. Penambahan sinonim perlu pembanding eksplisit terhadap BM25 asli; jangan mengubah baseline lama diam-diam. Pengetahuan setelah pewarnaan/ujung bercabang masih perlu sumber yang sesuai; produk internal tetap rahasia dan aturan keratin universal tidak ditambahkan.
