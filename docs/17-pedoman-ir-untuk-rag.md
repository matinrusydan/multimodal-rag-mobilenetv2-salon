# Pedoman IR untuk RAG layanan salon

Tanggal kajian: 20 Oktober 2026. Sumber materi: `C:/laragon/www/Persiapan UTS STBI`.

## Cakupan pembacaan

Folder berisi enam PDF perkuliahan, satu PDF ringkasan, dua PDF referensi, ringkasan Markdown, latihan soal, serta sumber LaTeX/HTML. Sembilan PDF berjumlah 191 halaman. Teks diekstrak dari semua PDF; pembacaan difokuskan pada konsep, pemodelan, pengindeksan, tolerant retrieval, dan evaluasi yang relevan dengan RAG. Sebanyak 23 halaman terpilih diperiksa secara visual untuk membaca rumus, tabel, dan diagram yang berupa gambar. Ini bukan pernyataan bahwa setiap ilustrasi pada seluruh halaman sudah diverifikasi.

Hash file, teks per halaman, dan render terpilih tersimpan di `tmp/ir-material-review/`. Ringkasan dan latihan dipakai sebagai navigasi; rujukan utama kajian adalah PDF materi dan bagian relevan referensinya. Tidak ada perubahan kode produksi, korpus penelitian, atau sumber materi dalam kajian ini.

| PDF | Halaman | Bagian yang relevan |
|---|---:|---|
| 1 STBI - Pengantar SistemTemu Balik Informasi (IR System) | 10 | Hal. 6–9: kebutuhan informasi, perbedaan IR/database, komponen sistem |
| 2 STBI - Konsep Dasar | 27 | Hal. 3–7, 10–14: efektivitas, efisiensi, query, preprocessing |
| 3 STBI - Pemodelan IR | 32 | Hal. 3–19: Boolean, VSM, TF-IDF, BM25; hal. 20–30: embedding dan pencarian semantik |
| 5 STBI - Search Egine | 19 | Hal. 7–13: crawling, alur indeks dan ranking; hal. 18–19: evaluasi dan contoh |
| 6 STBI - Dictionaries and Tolerant Retrieval | 13 | Hal. 2–12: dictionary, postings, k-gram, edit distance, saran ejaan |
| 7 STBI - Evaluasi pada IR | 41 | Hal. 2–4, 9–24: rancangan evaluasi; hal. 25–40: contoh metrik ranking |
| Materi STBI | 6 | Ringkasan; bukan sumber independen untuk membuktikan klaim penelitian |
| Referensi Distioneri and Toleran REtrival | 18 | Cuplikan bab 3 edisi daring Cambridge 2009; dictionary dan tolerant retrieval |
| Referensi Evaluasi | 25 | Cuplikan bab 8 edisi daring Cambridge 2009; test collection, relevance judgment, ranked evaluation, snippet |

Nomor di dokumen ini adalah nomor halaman PDF mulai dari satu, bukan nomor slide atau halaman buku. Dua referensi buku bertahun 2009: keduanya dapat menjelaskan teori klasik, tetapi tidak dihitung sebagai paper terbit 2021–2026 atau bukti research gap terbaru. Buku tersebut berada di luar pembatasan tahun koleksi paper sebelumnya dan tidak ditambahkan diam-diam ke koleksi itu.

## 1. Materi sangat relevan, terutama untuk komponen retrieval

RAG memiliki pengambilan konteks eksternal dan pembentukan jawaban. Materi IR menyediakan dasar untuk pengolahan dokumen, pengindeksan, pencocokan kueri, ranking, dan evaluasi retrieval. Evaluasi jawaban generatif tetap membutuhkan pemeriksaan tambahan: ketepatan harga, kelengkapan jawaban, dukungan klaim/sitasi, serta perilaku ketika sumber tidak tersedia.

Materi pengantar hal. 7 dan konsep dasar hal. 5 membedakan pencarian relevansi dengan pengambilan data terstruktur. Ini mendukung keputusan arsitektur sekarang:

- Harga, durasi, status aktif, daftar, dan filter layanan menggunakan katalog/database melalui operasi terstruktur.
- Penjelasan perawatan nonklinis menggunakan pencarian passage dokumen yang mempunyai sumber.
- Pertanyaan campuran membutuhkan bukti kedua jalur; satu bukti yang relevan belum berarti semua kebutuhan terjawab.
- LLM menyusun jawaban dari bukti yang disediakan dan kebijakan yang dicatat. LLM tidak menjadi sumber harga atau pengganti data yang tidak tersedia.

Pemisahan ini sudah sesuai dengan jalur `catalog_operations.py` dan penggabungan katalog aktif dengan dokumen pada `rag_service.py`. Ini dasar desain, bukan bukti bahwa arsitektur tersebut baru dalam literatur.

## 2. Pemetaan materi terhadap codebase

| Pedoman materi | Kondisi program saat ini | Tindak lanjut yang layak |
|---|---|---|
| Pengantar hal. 8: query analysis, indexer, ranking adalah komponen berbeda | Komponen tersedia secara fungsi, tetapi BM25 mengambil implementasi scoring dari modul pilot | Pisahkan komponen runtime dan pengukuran tanpa mengubah baseline beku atau hasil lama |
| Pemodelan hal. 13–17: BM25 memakai TF, DF/IDF, panjang dokumen dan rata-ratanya | `pilot.bm25_scores()` mengikuti varian IDF `ln(1 + (N-df+0.5)/(df+0.5))`; k1=1,5 dan b=0,75 | Pertahankan parameter awal; perubahan parameter hanya dipilih di development dan dicatat |
| Search Engine hal. 8, 12: indeks disiapkan sebelum pencarian | Token, DF, panjang rata-rata, dan frekuensi dihitung ulang di setiap pemanggilan BM25; source-balanced melakukan beberapa scoring | Kandidat optimasi: persiapkan statistik indeks/postings dan gunakan kembali berdasarkan versi korpus. Jangan menghilangkan pembaruan katalog aktif |
| Konsep Dasar hal. 12–14: preprocessing query dan dokumen | Tokenisasi runtime berupa case folding dan pemisahan `\w+`; belum ada studi preprocessing domain | Uji normalisasi, alias yang terverifikasi, stopword atau stemming secara terpisah; jangan menganggap semuanya pasti meningkatkan skor |
| Dictionaries hal. 8–11: ejaan, k-gram, edit distance | Alias layanan masih terbatas; belum ada tolerant retrieval yang dievaluasi untuk bahasa pelanggan | Uji varian penulisan dan typo pada development; jika calon layanan ambigu, minta konfirmasi |
| Evaluasi hal. 9–10, 22: corpus, kebutuhan informasi, dan relevance judgment | Ada korpus 13 evidence dan 24 pertanyaan pengembangan; acuan revisi belum seluruhnya ditinjau kembali | Perluas kebutuhan informasi, tinjau bukti alternatif, pisahkan keluarga skenario development/test, kemudian bekukan acuan |
| Evaluasi hal. 18–20, 26–40: posisi bukti relevan ikut dinilai | Evaluator retrieval utama memakai precision, recall, F1, dan kelompok bukti lengkap; belum melaporkan AP/MRR/nDCG | Tambahkan metrik ranking sesuai label yang tersedia, tanpa mengarang relevansi bertingkat |
| Evaluasi hal. 24; referensi evaluasi hal. 21–23: cuplikan bisa bergantung pada query | `context_snippets()` memotong passage non-web pada 400 karakter pertama | Periksa apakah bukti wajib masih ada setelah pemotongan; bandingkan cuplikan tetap dengan pemilihan kalimat berbasis query dalam budget yang sama |
| Evaluasi hal. 2–3, 23: efektivitas dan efisiensi harus diukur | Ada diagnosis waktu lokal sintetis; belum ada profil memori/concurrency/deployment yang memadai | Ukur biaya indeks, retrieval, database, generasi dan cold/warm secara terpisah |

BM25 tidak memerlukan pembelajaran embedding. Hal tersebut tidak otomatis membuktikan seluruh aplikasi ringan, karena masih ada parsing dokumen, dependensi runtime, akses database, konteks dan generasi eksternal.

## 3. Preprocessing harus mempertahankan makna domain

Contoh pembuangan angka pada materi hal. 13 merupakan ilustrasi umum, bukan aturan yang diterapkan pada semua input salon. Untuk proyek ini:

- Pertahankan harga, tanggal, durasi, satuan, nama layanan dan negasi seperti `tidak` atau `belum`.
- Normalisasi `Rp300.000` dan `300 ribu` menjadi nilai harga terstruktur hanya pada jalur parsing yang mendukungnya.
- Simpan pertanyaan asli, versi normalisasi, dan alasan perubahan agar dapat diaudit.
- Alias seperti `conditioner`/`kondisioner` dapat diuji. Pemetaan nama layanan yang berbeda tidak disahkan hanya karena kata-katanya mirip.
- Typo seperti `kratin` dapat menghasilkan kandidat `keratin`; bila ada beberapa kandidat layanan yang masuk akal, jangan diam-diam memilih harga salah satu.
- Jangan menjalankan koreksi ejaan atau stemming atas angka harga, ID, merek, atau nama layanan tanpa aturan yang sesuai.

Keuntungan stemming/lemmatisasi bergantung pada bahasa, implementasi dan korpus. Jangan memindahkan penyederhanaan bahwa lemmatisasi selalu lebih akurat ke klaim penelitian. Uji sebagai ablation bila masalah variasi kata memang muncul.

## 4. Protokol evaluasi retrieval yang disarankan

Dasar eksperimen adalah tiga komponen pada materi evaluasi hal. 9:

1. **D:** korpus/record/passage yang dicari, dengan versi dan identitas jelas.
2. **Q:** kebutuhan informasi serta representasi pertanyaannya.
3. **R:** relevance judgments pada unit evidence yang sama dengan hasil retrieval.

Pertanyaan tidak cukup dibuat dengan menyalin judul dokumen atau nama layanan. Sertakan bahasa pengguna, sinonim, typo yang wajar, kebutuhan campuran, filter katalog, dan sumber yang tidak tersedia. Pisahkan kategori katalog deterministik dari ranking dokumen; keduanya tidak dipaksa memiliki denominator retrieval yang sama.

Penilaian relevansi dilakukan terhadap kebutuhan informasi, bukan sekadar kecocokan kata. Catat semua bukti alternatif yang benar-benar mendukung fakta. Korpus kecil dapat ditinjau lebih menyeluruh; jika memakai pooling beberapa retriever, dokumen yang belum dinilai tidak otomatis terbukti tidak relevan. Recall kemudian harus dijelaskan sebagai recall terhadap acuan yang diketahui.

Materi hal. 22 menyebut 50 query sebagai aturan praktis, bukan jaminan kecukupan statistik atau standar wajib untuk setiap domain. Jumlah akhir ditentukan oleh keragaman kebutuhan dan kemampuan anotasi; puluhan paraphrase dari satu kasus tidak menggantikan kebutuhan informasi yang independen. Data pengembangan 24 query sekarang tetap untuk diagnosis, bukan diganti namanya menjadi test final.

### Rumus dan penggunaan metrik

Dengan E himpunan ID bukti relevan dan Rk daftar hasil sampai k:

| Ukuran | Definisi operasional | Pemakaian |
|---|---|---|
| Precision hasil aktual | `|set(Rk) ∩ E| / |Rk|` | Proporsi hasil yang benar-benar dikembalikan yang relevan; ini konvensi implementasi retrieval sekarang |
| Precision@k ketat | `|set(Rk) ∩ E| / k` | Sesuai materi hal. 18. Jika hasil kurang dari k, penyebut tetap k. Nyatakan kebijakan ketika korpus lebih kecil daripada k |
| Recall@k | `|set(Rk) ∩ E| / |E|` | Cakupan bukti relevan yang diketahui; query tanpa acuan dinilai N/A |
| F1 retrieval | `2PR/(P+R)` | Gunakan definisi P yang dipilih secara konsisten; bukan F1 token jawaban atau akurasi harga |
| AP / MAP | `AP(q)=sum(P@i × rel(i))/|E|`; MAP adalah rata-rata AP antar-query | Menilai beberapa bukti relevan beserta urutannya. Jika ranking dipotong pada k, beri label AP@k/MAP@k dan tetapkan penyebut |
| RR / MRR | RR adalah `1/rank` bukti relevan pertama per-query; MRR rata-rata RR antar-query | Tambahan untuk bukti pertama; tidak cukup untuk query campuran yang memerlukan dua sumber |
| nDCG@k | `DCG@k/IDCG@k` dengan gain dan diskon eksplisit | Memerlukan label graded bila ingin membedakan tingkat relevansi. Label biner juga dapat dipakai, tetapi tidak menjadi validasi graded |
| Cakupan bukti lengkap | Setiap kelompok kebutuhan memiliki sekurangnya satu bukti pendukung | Ukuran utama pertanyaan campuran; mencegah sukses hanya karena satu kebutuhan terjawab |

Perbedaan precision hasil aktual dan Precision@k penting ketika hasil lebih sedikit daripada k: satu hasil benar menghasilkan precision aktual 1, sedangkan P@5 ketat 0,2. Laporan lama tidak diubah diam-diam. Sebelum implementasi metrik baru, tetapkan nama dan formula dalam protokol baru serta simpan lineage hasil.

Saat gold mengandung beberapa passage alternatif untuk kebutuhan yang sama, recall terhadap union semua alternatif dan cakupan kelompok menjawab pertanyaan berbeda. Laporkan definisinya agar sistem tidak dihukum seolah harus mengambil semua passage yang sebenarnya dapat saling menggantikan.

MRR dapat bernilai 1 meskipun bukti harga saja yang ditemukan dan penjelasan perawatan tidak ditemukan. Karena itu MAP/MRR/nDCG tidak menggantikan cakupan kebutuhan dan pemeriksaan jawaban akhir.

## 5. Catatan verifikasi angka pada materi

Pemeriksaan numerik mandiri tersimpan di `tmp/ir-material-review/formula-checks.json`; angka ini adalah contoh matematika, bukan hasil model salon.

- BM25 D1 pada asumsi slide menghasilkan sekitar 1,56542, sejalan dengan contoh 1,565 pada materi pemodelan.
- Contoh ranking biner R,R,R,N,R dengan empat bukti relevan menghasilkan AP=0,95, sesuai materi evaluasi hal. 25.
- DCG linear untuk nilai `[3,2,3,0,1]` adalah sekitar 6,14871; IDCG sekitar 6,32347; nDCG sekitar 0,97236. Penyajian slide membulatkan angka di tahap berbeda, tetapi kesimpulan nDCG≈0,972 tetap sesuai.
- Hal. 27–28 evaluasi menampilkan satu tabel query, lalu rata-rata dua nilai RR. Agar tidak ambigu: untuk satu query dengan bukti relevan pertama di peringkat satu, RR=1. Nilai MRR=0,75 benar jika ada **dua query** dengan peringkat relevan pertama masing-masing satu dan dua. Bukan rata-rata reciprocal rank beberapa dokumen dalam satu query.
- Slide dictionaries hal. 8 mencontohkan 3-gram `data` dengan potongan `data` dan `ata`. Untuk panjang tiga karakter, potongan tanpa penanda batas adalah `dat` dan `ata`. Indeks k-gram dengan penanda awal/akhir menghasilkan daftar berbeda; definisinya harus eksplisit.
- Contoh cosine 0–1 pada vektor term nonnegatif tidak boleh digeneralisasikan sebagai rentang semua embedding; vektor bertanda dapat memiliki cosine negatif.

Konsep utama materi dapat diikuti, sementara contoh dan konvensi numeriknya tetap diperiksa sebelum menjadi kode evaluator atau rumus dalam naskah.

## 6. Rancangan eksperimen yang mengikuti materi

Pertahankan paket development/test terpisah. Pada korpus dan kueri yang sama, rancangan bertahap dapat membandingkan:

1. Baseline TF-IDF + cosine sebagai pembanding IR klasik bila diperlukan untuk menguji pemilihan BM25.
2. BM25 standar sebagai baseline utama yang sudah tersedia.
3. BM25 dengan normalisasi domain/toleransi ejaan, hanya bila diagnosis menunjukkan kebutuhan tersebut.
4. BM25 dengan alokasi sumber seperti implementasi sekarang; lakukan ablation normalisasi, pemisahan kueri, dan alokasi bila komponen-komponen itu menjadi klaim metode.

Tidak semua variasi wajib dibuat. Pilih satu intervensi utama dan kontrol yang cukup untuk mengisolasi efeknya. Jangan menambahkan algoritma hanya agar judul terlihat kompleks. Indeks/statistik yang dipersiapkan sebelum query dapat diterapkan sebagai optimasi setara pada kedua pembanding; jika menjadi objek eksperimen, ukur pengaruhnya terpisah dari perubahan ranking.

Untuk keadilan, gunakan generator/model yang sama, korpus dan snapshot yang sama, batas konteks yang sama, serta perlakuan pembaruan fakta bisnis yang setara. Akses katalog aktif bukan keuntungan informasi yang hanya boleh diberikan ke metode usulan. Uji cold/warm dan beberapa ukuran korpus; batasi perubahan parameter pada development. Status N/A, error teknis, dan skor nol yang sah tetap dibedakan.

## 7. Urutan pekerjaan berikutnya

1. Kunci unit relevansi serta konvensi precision, AP@k, MRR@k dan gain nDCG; pertahankan cakupan kelompok bukti untuk pertanyaan campuran.
2. Perluas kebutuhan informasi dan tinjau bukti alternatif sebelum membekukan test. Pertahankan anotasi naratif Matin sebagai lineage; jangan mengarang label graded atau persetujuan baru.
3. Siapkan indeks/statistik BM25 yang dapat digunakan kembali dan invalidasi berdasarkan versi korpus, sambil menjaga katalog layanan tetap mutakhir.
4. Jalankan ablation preprocessing dan seleksi konteks yang dibutuhkan pola error. Simpan konteks yang benar-benar diberikan kepada generator, bukan hanya ID passage.
5. Ukur retrieval dan biaya komputasi, kemudian nilai jawaban, fakta layanan, dukungan klaim dan abstention.

Materi IR memperkuat rancangan metode dan evaluasi kita. Ia belum membuktikan kebaruan, tidak menetapkan ambang industri universal, dan tidak menggantikan pembanding paper terbit yang sudah dipetakan. Judul serta klaim efisiensi tetap mengikuti masalah dan hasil eksperimen yang benar-benar diperoleh.
