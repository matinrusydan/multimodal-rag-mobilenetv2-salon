# Perbandingan kandidat algoritma RAG dan keputusan eksplorasi

Tanggal: 20 Oktober 2026. Status: **eksplorasi development; belum hasil penelitian final**.

## 1. Keputusan yang dapat diambil sekarang

BM25 dipertahankan sebagai baseline yang dapat direproduksi tanpa API. MMR, RRF, dan perutean berbasis aturan sudah dibuat sebagai variasi eksperimen terisolasi. Pada pilot saat ini **belum ada variasi yang mengungguli baseline dalam kelengkapan bukti**. Karena itu belum ada dasar menetapkan salah satunya sebagai metode peningkatan, mengubah sistem produksi, atau menulis abstrak dengan klaim keberhasilan.

Judul kerja yang menyebut metode, tujuan, dan objek secara eksplisit:

> **Evaluasi Diversifikasi MMR dan Fusi RRF pada BM25 untuk Pengambilan Bukti Konsultasi Salon**

Ini judul untuk arah penelitian evaluatif, bukan keputusan bahwa MMR dan RRF harus dipakai bersama. Eksperimen membandingkan variasinya secara terpisah. Fokus operasionalnya adalah pertanyaan yang membutuhkan fakta layanan dari database sekaligus panduan perawatan nonklinis dari dokumen. Judul akhir dapat dipersempit setelah korpus, label, dan eksperimen final siap. RAG merupakan kerangka aplikasi; BM25, MMR, dan RRF merupakan mekanisme yang diuji. Evaluasi ini sendiri belum membuktikan kebaruan yang cukup untuk jurnal tujuan.

## 2. Pemeriksaan penelitian terdekat dari sumber asli

| Penelitian terbit | Metode yang benar-benar dibahas | Implikasi untuk proyek | Status pemeriksaan |
|---|---|---|---|
| Cruz dkk., 2025, *Lisa: a touristic chatbot for Lisbon*, Information Technology & Tourism, DOI 10.1007/s40558-025-00339-x | BM25, dense retrieval, dan hybrid dengan RRF; preprocessing korpus web diuji | Menggabungkan BM25 dengan dense/RRF saja sudah ada. Pembersihan korpus merupakan faktor pembanding penting. | Bagian retrieval dan preprocessing pada laman penerbit diperiksa kembali; mapping P03 sudah membaca PDF. [Penerbit](https://link.springer.com/article/10.1007/s40558-025-00339-x) |
| Khasanova Zafar kizi & Suh, 2025, *Design and Performance Evaluation of LLM-Based RAG Pipelines for Chatbot Services in International Student Admissions*, Electronics, DOI 10.3390/electronics14153095 | Perbandingan retriever termasuk MMR/hybrid dan variasi chunking pada informasi layanan | MMR bukan kebaruan dengan sendirinya. Perlu menyatakan bentuk kemiripan dan kesetaraan konteks bila melakukan perbandingan. | PDF lokal telah dipetakan P04, halaman 3–6 dan 18–19. Akses web ulang gagal HTTP 429; fallback ke mapping PDF lokal, bukan mengaku berhasil mengakses ulang. [Penerbit](https://www.mdpi.com/2079-9292/14/15/3095) |
| Liu dkk., 2024, *SUQL: Conversational Search over Structured and Unstructured Data with Large Language Models*, Findings NAACL, DOI 10.18653/v1/2024.findings-naacl.283 | SQL diperluas dengan operasi teks SUMMARY/ANSWER; semantic parsing berbasis LLM menggabungkan akses data terstruktur dan teks | Pertanyaan lintas sumber dan integrasi SQL–teks sudah diteliti. Proyek salon tidak boleh mengklaim sebagai yang pertama menggabungkan database dan dokumen. | Metadata, abstrak, pendahuluan dan rancangan metode pada PDF primer diperiksa; bukan replikasi keseluruhan studi. Prosiding terbit, **bukan jurnal**. [Penerbit dan PDF](https://aclanthology.org/2024.findings-naacl.283/) |
| Glenn dkk., 2024, *BlendSQL: A Scalable Dialect for Unifying Hybrid Question Answering in Relational Algebra*, Findings ACL, DOI 10.18653/v1/2024.findings-acl.25 | Dialek turunan SQLite mengorkestrasi operasi SQL dan LLM; rencana dekomposisi direpresentasikan dalam kueri | Dekomposisi dan reasoning lintas sumber juga sudah ada. Heuristik tanpa LLM pada pilot ini bukan implementasi BlendSQL. | Metadata, abstrak, pendahuluan dan overview metode pada PDF primer diperiksa; belum replikasi. Prosiding terbit, **bukan jurnal**. [Penerbit dan PDF](https://aclanthology.org/2024.findings-acl.25/) |

Semua sumber pembanding di tabel terbit pada rentang 2021–2026. Dua artikel jurnal pertama berasal dari mapping sebelumnya; dua prosiding terakhir merupakan penajaman penelusuran metode terdekat. Koleksi 25 PDF dan nama filenya tidak diubah. Sumber prosiding tambahan belum diunduh ke koleksi. Pernyataan implikasi merupakan interpretasi untuk desain proyek kita, bukan klaim kelemahan universal penelitian tersebut.

**Calon celah yang masih harus dibuktikan:** pemilihan bukti untuk setiap kebutuhan dalam pertanyaan campuran, dengan batas konteks tetap dan prioritas fakta operasional dari sumber yang berwenang. Adanya kegagalan lokal mendukung masalah teknis, tetapi belum membuktikan bahwa celah ini belum diselesaikan pada literatur lain atau bahwa pertanyaan tersebut sering muncul pada pelanggan TIEN.

## 3. Eksperimen yang sudah dijalankan

Implementasi: `apps/ai/app/rag/algorithm_trial.py`. Input dibaca dari pilot beku, output terpisah di `apps/ai/rag/eval/algorithm-trial/`. Tidak memakai API, model neural, database langsung, atau index produksi. Seluruh jalur mendapat korpus yang sama: 6 record snapshot layanan dan 45 potongan Markdown lama, total 51 evidence; 24 pertanyaan draft.

| Metode di laporan | Operasi | Parameter/kontrol |
|---|---|---|
| `bm25` | Ranking BM25 atas pertanyaan asli, top-5 | k1=1,5; b=0,75; sama dengan baseline pilot sebelumnya |
| `bm25_clean` | BM25 setelah penghapusan daftar stopword eksplisit | Kontrol apakah perubahan hanya akibat pembersihan pertanyaan |
| `bm25_mmr` | Pemilihan MMR atas relevansi BM25 dan redundansi cosine TF-IDF | lambda=0,7; seluruh 51 kandidat; **kemiripan leksikal, bukan neural** |
| `bm25_decomposed_rrf` | RRF ranking pertanyaan asli dengan ranking kueri dokumen hasil penghilangan nama layanan/kata bisnis, bila kebutuhan dokumen terdeteksi | konstanta RRF=60; dua ranking **BM25**, bukan hybrid BM25+dense |
| `bm25_routed` | Cadangkan satu posisi DB untuk kebutuhan bisnis dan satu posisi non-DB untuk kebutuhan dokumen; sisanya ranking asli | Kebutuhan dideteksi aturan kata, bukan kategori gold |
| `bm25_routed_decomposed` | Cadangan sumber yang sama, ranking dokumen memakai kueri yang dipisahkan | Ablation untuk melihat pengaruh pemisahan kebutuhan dan reservasi sumber |

Pemilihan kandidat tidak menerima ID pertanyaan, kategori evaluasi, jawaban acuan, atau label evidence. Nama layanan berasal dari katalog input. Label hanya dipakai sesudah pemilihan untuk menghitung metrik. Seluruh metode maksimal lima potongan, masing-masing cuplikan 400 karakter. Anggaran keluaran setara, tetapi biaya komputasinya tidak dianggap sama: beberapa variasi memerlukan dua kali ranking BM25. Latensi belum diukur sebagai hasil penelitian.

Rumus MMR yang dipakai: pilih kandidat yang memaksimalkan `0,7 × BM25_normalized − 0,3 × max(cosine_TFIDF(candidate, selected))`. Normalisasi membagi skor BM25 dengan skor maksimum kueri tersebut. Pilihan pertama memakai penalti redundansi nol. RRF menjumlahkan `1 / (60 + rank)` dari ranking masukan. Ikatan skor dipecahkan secara deterministik menggunakan ID evidence. Perutean mendahulukan slot bisnis bila budget hanya satu. Aturan lengkap dan parameter tersimpan dalam `report.json` dan source code.

Aturan diusulkan setelah kegagalan baseline diperiksa. Data ini merupakan development set, **bukan held-out test**; tidak ada pencarian parameter, tetapi bias pemilihan rancangan tetap mungkin. Parameter tidak diubah lagi untuk mengejar angka pada pertanyaan yang sama.

## 4. Hasil aktual pada pertanyaan campuran

Enam pertanyaan campuran memiliki dua kelompok bukti wajib: record layanan dan passage perawatan.

| Metode | Precision@5 | Recall@5 | F1 retrieval@5 | Seluruh kelompok bukti ditemukan |
|---|---:|---:|---:|---:|
| BM25 | 0,367 | 0,917 | 0,524 | 5/6 |
| BM25 + cleaning | 0,367 | 0,917 | 0,524 | 5/6 |
| BM25 + MMR leksikal | 0,367 | 0,917 | 0,524 | 5/6 |
| BM25 + dekomposisi + RRF | 0,333 | 0,833 | 0,476 | 5/6 |
| BM25 + reservasi sumber | 0,367 | 0,917 | 0,524 | 5/6 |
| BM25 + reservasi sumber + dekomposisi | 0,367 | 0,917 | 0,524 | 5/6 |

Untuk seluruh pertanyaan yang memiliki label evidence, baseline mendapatkan bukti lengkap pada 20/21. Tiga pertanyaan tanpa jawaban/ambigu tidak memiliki gold passage dan tidak masuk denominator retrieval, **bukan dianggap benar**. Pertanyaan dokumen 6/6 dan database 6/6 sudah mencapai batas atas kelengkapan pada set kecil ini. Dataset ini terlalu mudah/kecil untuk menyimpulkan keunggulan atau kesetaraan metode secara umum.

Precision = jumlah ID evidence relevan terambil / jumlah evidence terambil. Recall = jumlah ID relevan terambil / jumlah ID gold relevan. F1 retrieval = harmonic mean precision dan recall, dihitung per kueri lalu dirata-ratakan. Kelengkapan = 1 bila sekurangnya satu bukti dari **setiap kelompok wajib** terambil, selainnya 0. Pada data sekarang setiap kelompok hanya berisi satu ID; bila nanti ada beberapa passage alternatif, gunakan group coverage sebagai ukuran utama atau revisi definisi recall agar tidak menuntut semua alternatif sekaligus.

ID relevansi draft belum memperhitungkan semua kemungkinan bukti alternatif. Metrik ini menilai pengambilan passage, bukan ketepatan harga yang diucapkan chatbot, kualitas jawaban, faithfulness, maupun dukungan semua klaim setelah cuplikan dipotong. Skor precision rendah sebagian dipengaruhi pengambilan lima passage ketika gold hanya satu atau dua; jangan menjadikan nilai itu sendirian bukti mutu sistem yang buruk.

## 5. Diagnosis kegagalan yang tetap ada

Pertanyaan p18: “Berapa harga serta durasi Volume Blowout Styling dan isi panduan untuk rambut kering?”

- BM25 mengambil tiga representasi layanan Volume Blowout Styling, satu passage Rambut Lurus, dan satu harga Precision Haircut. Record layanan benar ada, tetapi passage gold Rambut Kering / Kusam tidak ada.
- Pada pertanyaan asli, passage gold perawatan berada di urutan 23. Setelah nama layanan dan kata bisnis dibuang, kueri dokumen menjadi `rambut kering`; passage gold naik ke urutan 3, tetapi dua passage Rambut Keriting masih mendahuluinya karena juga memuat istilah yang cocok.
- Reservasi satu slot dokumen mengambil passage Rambut Keriting, sehingga keberadaan dua jenis sumber belum menjamin dua kebutuhan terjawab.
- RRF pada pertanyaan ini justru mengeluarkan kedua ID gold dari top-5. Kelengkapan tetap nol, tetapi recall turun dari 0,5 menjadi 0; ini menjelaskan mengapa kelengkapan agregat sama sementara recall berbeda.

Ini mendukung kebutuhan memeriksa pencocokan isi dan redundansi, bukan sekadar menambah nama algoritma. Namun passage alternatif Rambut Keriting masih harus ditinjau manusia sebelum dianggap pasti tidak relevan. Belum ada generasi jawaban, sehingga kegagalan retrieval ini tidak boleh disebut halusinasi jawaban yang sudah terukur.

## 6. Langkah berikut yang paling bernilai

1. **Validasi 24 pertanyaan dan gold evidence** pada `apps/ai/rag/eval/pilot/annotation_sheet.json`. Periksa kebenaran, bukti alternatif, dan apakah dua subkebutuhan memang membutuhkan dua sumber. Semua status tetap pending sampai benar-benar ditinjau peneliti; asisten tidak menandatangani atas nama peneliti.
2. **Kurasi pengetahuan perawatan yang benar-benar akan digunakan chatbot.** Simpan sumber primer/pedoman produk yang sesuai, halaman/URL, tanggal, hash dan batas klaim. Markdown lama belum cukup sebagai acuan ilmiah. Paper algoritma RAG merupakan literatur metode, bukan pengetahuan perawatan pelanggan. Instruksi smoothing “tiga hari” tidak dijadikan aturan universal. Crawling hanya setelah pemeriksaan robots.txt dan aturan akses.
3. **Perluas pertanyaan berdasarkan cakupan, bukan angka target akurasi.** Sertakan variasi nama layanan, paraphrase, dua layanan, keterkaitan kondisi–perawatan, promo tanpa sumber, konflik dokumen–DB, pertanyaan ambigu dan out-of-scope. Pisahkan keluarga pertanyaan/skenario ke development dan test agar paraphrase dari satu kasus tidak bocor ke keduanya. Jumlah akhir ditetapkan berdasarkan variasi kasus dan kemampuan anotasi, lalu ketidakpastian skor tetap dilaporkan.
4. **Bekukan protokol sebelum uji final.** Pilih satu perubahan utama, tetapkan parameter di development, serta bandingkan BM25 dengan baseline sederhana termasuk cleaning/deduplikasi. Jika memasukkan neural dense, gunakan embedding neural yang benar dan model/index konsisten; hash proxy dari pilot lama tidak boleh dilabel dense. Uji ablation agar efek komponen dapat dipisahkan.
5. **Uji jawaban setelah retrieval layak.** Harga/durasi diuji dengan exact match field atau akurasi fakta terhadap snapshot; kelengkapan jawaban dengan cakupan subkebutuhan; dukungan klaim/sitasi dinilai manual dengan rubric. Faithfulness dan relevansi jawaban dapat menjadi tambahan, bukan pengganti kebenaran terhadap DB. Jika memakai judge, kalibrasi dengan anotasi manual, pertahankan skor nol yang sah, dan pisahkan kegagalan API sebagai missing. Abstention dinilai tersendiri dengan label answerability. RAGAS opsional sesuai kuota, bukan syarat untuk evaluasi sah.

Gate keputusan metode: setelah kurasi dan validasi development, pilih intervensi yang sesuai pola error. Setelah itu barulah uji final pada test terpisah dan laporkan hasil apa adanya. Jika tidak ada peningkatan yang konsisten, pertahankan metode sederhana dan evaluasi kelayakan kontribusi dengan dosen; jangan mengganti metrik untuk menyamarkan hasil negatif.

## 7. Jejak eksekusi dan verifikasi

- Eksplorasi dijalankan: 24 kueri × 6 metode = **144 keluaran retrieval**, tersimpan dalam `report.json`; cuplikan, rencana routing, parameter dan hash input dapat diaudit.
- Baseline baru terbukti menghasilkan ID yang identik dengan baseline pilot beku pada seluruh 24 pertanyaan.
- Tes baru menguji label tidak memengaruhi pemilihan, pemisahan nama layanan dari intent, reservasi sumber/budget, determinisme RRF, dan penalti duplikasi MMR.
- Pengujian RAG terkait: **52 passed** (7 tes eksplorasi ditambah 45 tes terkait sebelumnya). Ini validasi implementasi, bukan bukti keberhasilan ilmiah.
- Akses ulang MDPI mengalami HTTP 429; fallback memakai hasil baca PDF lokal yang tercatat pada mapping. Tidak memakai mirror pihak ketiga atau Playwright.
- Tidak ada biaya API, migrasi/seed, perubahan layanan/promo, ingest index produksi, atau penulisan ulang proposal LaTeX.

Perintah reproduksi dari `apps/ai`:

```powershell
& '.venv\Scripts\python.exe' -m app.rag.algorithm_trial --help
& '.venv\Scripts\python.exe' -m app.rag.algorithm_trial
& '.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_rag_algorithm_trial.py tests/test_rag_pilot_protocol.py tests/test_ingest.py tests/test_retriever.py tests/test_antibot.py
```
