# Keputusan ruang lingkup dan analisis pilot lanjutan

Tanggal: 20 Oktober 2026. Dasar: jawaban pengguna setelah audit dan pilot. Dokumen ini menambah keputusan kebutuhan; tidak mengubah dataset atau hasil baseline yang sudah disimpan.

## 1. Keputusan dari pengguna

| Aspek | Keputusan | Implikasi penelitian dan implementasi |
|---|---|---|
| Fakta layanan/harga | Tabel `public.services` menjadi sumber dengan enam layanan yang diberikan pengguna | Data harga/durasi cocok dengan snapshot pilot. Pemberian isi tabel mengonfirmasi data yang digunakan, tetapi bukan pernyataan bahwa seluruh nilai sudah disetujui pemilik salon. |
| Promo/diskon | Pengguna menghendaki data terstruktur yang dapat diubah melalui dashboard | Promo dalam Markdown bukan sumber berwenang. Sebelum data promo tersedia, jawaban tidak memastikan promo berlaku. Desain kolom, jenis diskon dan periode berlaku belum ditetapkan; tidak ada migrasi yang dijalankan. |
| Konsultasi | Edukasi nonklinis dari PDF/Markdown, atau web crawling bila sumber lokal tidak mencukupi | Perlu sumber yang ditelaah dan dapat ditelusuri. Permintaan diagnosis, resep atau dosis obat mendapat fallback. Penyebutan keluhan rambut tidak otomatis berarti permintaan diagnosis. |
| Keluhan pelanggan | Contoh kebutuhan: warna rambut luntur, pertanyaan tentang aturan keramas setelah smoothing | Tambahkan jalur keluhan dan klarifikasi; sumbernya dapat berupa panduan layanan dan SOP salon. Contoh bukan transkrip pelanggan yang sudah dikumpulkan. |
| Pemeriksa | Pengguna sendiri terlebih dahulu | Semua anotasi tetap draft sampai diperiksa. Keterbatasan satu penilai harus dilaporkan; tidak menghitung agreement dua annotator. |

Angka harga dalam jawaban pengguna cocok dengan snapshot: Hair Spa 325.000/90 menit; Haircut 220.000/60; Keratin 780.000/150; Color Gloss 620.000/130; Scalp Detox 360.000/75; Blowout 280.000/55. Kolom `price` sendiri belum menjelaskan model promo, diskon atau harga berdasarkan panjang rambut.

## 2. Analisis kegagalan pertanyaan p18

Pertanyaan: **“Berapa harga serta durasi Volume Blowout Styling dan isi panduan untuk rambut kering?”**

Terdapat dua kebutuhan bukti: record layanan Blowout dan passage panduan rambut kering. Pada baseline BM25 top-k 5, record layanan sudah ditemukan. Passage perawatan yang diberi label gold berada pada peringkat **23**, sehingga tidak masuk konteks akhir.

| Peringkat | Hasil | Peran terhadap kebutuhan pertanyaan |
|---|---|---|
| 1 | Record DB Volume Blowout Styling | Memuat harga 280.000 dan durasi 55 menit. |
| 2 | Bagian Volume Blowout Styling dalam harga.md | Mengulang informasi layanan/harga; bukan sumber DB yang berwenang. |
| 3 | Bagian Volume Blowout Styling dalam layanan.md | Mengulang informasi layanan; belum mengisi kebutuhan panduan rambut kering. |
| 4 | Bagian Rambut Lurus dalam gaya-rambut.md | Mengandung kata volume/styling; tidak menjadi gold passage untuk kebutuhan rambut kering. |
| 5 | Bagian Precision Haircut dalam harga.md | Memiliki overlap kata, tetapi merupakan layanan berbeda. |

**Diagnosis yang didukung log:** ranking gabungan query lebih mengutamakan istilah layanan dan menyertakan informasi berulang dari beberapa sumber. Bukti perawatan lokal tersedia tetapi berada di luar batas top-k. Ini kegagalan cakupan evidence pada retrieval; belum ada keluaran LLM untuk menyatakan terjadi halusinasi atau jawaban salah.

**Pemeriksaan tambahan:** ketika pencarian hanya memakai subkebutuhan “isi panduan untuk rambut kering”, passage gold naik dari peringkat 23 ke peringkat 4. Pemeriksaan ini memakai korpus dan implementasi BM25 yang sama. Ini hanya diagnosis satu kasus development, bukan eksperimen independen atau bukti bahwa query decomposition pasti unggul.

**Batas diagnosis:** gold masih draft, dan ada passage lain yang mungkin memberikan sebagian jawaban. Perlu memeriksa bukti alternatif sebelum menyatakan semua hasil di luar gold pasti tidak relevan. Menambah top-k hingga 23 akan menemukan passage ini, tetapi menambah noise dan konteks; keberhasilan tersebut tidak otomatis menjadi solusi yang efisien.

## 3. Intervensi pertama yang layak diuji

Uji **perutean berdasarkan kebutuhan informasi**, dengan aturan sederhana yang transparan:

1. Identifikasi kebutuhan layanan/harga/durasi dan kebutuhan penjelasan perawatan dalam pertanyaan.
2. Ambil record layanan dari snapshot/database untuk kebutuhan bisnis.
3. Cari passage dokumen untuk kebutuhan edukasi, dengan kueri yang mewakili kebutuhan tersebut.
4. Susun konteks yang mencakup kedua kebutuhan; cegah salinan layanan yang sama menghabiskan seluruh budget evidence.
5. Pertahankan identitas sumber per klaim dan nyatakan informasi yang belum tersedia.

Jangan mengubah seluruh pipeline langsung. Buat pembanding terisolasi dengan korpus, query dan budget yang sama. Bandingkan baseline dengan routing, lalu routing tanpa pemisahan kebutuhan atau tanpa pengendalian informasi berulang jika komponennya dapat dipisahkan. Karena keputusan ini menggunakan kasus pilot, keberhasilan pada p18 termasuk development; pengujian akhir memerlukan pertanyaan baru yang dikunci.

Belum ada klaim bahwa routing atau query decomposition merupakan algoritma baru. Studi paling dekat tetap perlu ditelusuri untuk menentukan kontribusi yang dapat dipertahankan.

## 4. Sumber yang masih perlu disiapkan

| Kebutuhan | Sumber berwenang | Kondisi saat ini |
|---|---|---|
| Harga, nama, durasi layanan | Database services | Snapshot tersedia. |
| Promo yang sedang berlaku | Data promo terstruktur dan kebijakan bisnis | Belum tersedia pada snapshot; jangan mengasumsikan promo Markdown aktif. |
| Perawatan kosmetik umum | Dokumen PDF/Markdown atau web terkurasi | Markdown lama tersedia tetapi belum cukup sebagai gold tervalidasi. |
| Instruksi setelah layanan tertentu | Instruksi produk/prosedur yang digunakan dan SOP salon | Belum ada sumber tervalidasi yang dilampirkan dalam jawaban pengguna. |
| Penanganan keluhan/komplain | SOP dan kanal eskalasi resmi salon | Belum tersedia sebagai kebijakan yang tervalidasi. |

Pernyataan “tidak boleh keramas tiga hari setelah smoothing” berasal dari contoh yang disampaikan pengguna. Jangan mengubahnya menjadi aturan universal dalam knowledge base atau jawaban acuan. Catat kebutuhan konfirmasi prosedur/produk dan instruksi yang benar-benar diberikan salon. Hindari janji hasil, pengembalian dana atau kompensasi tanpa kebijakan resmi.

Fallback web berarti mencari bukti yang sesuai, bukan menjawab dari sumber pertama yang ditemukan. Sebelum crawl, periksa robots.txt dan ketentuan akses; catat URL, tanggal, status akuisisi serta isi yang dipakai. Jika tidak ada sumber yang memadai, jelaskan keterbatasan dan arahkan pada konfirmasi salon. Tidak ada crawl yang dilakukan dalam analisis lanjutan ini.

## 5. Kandidat pertanyaan tambahan dari kebutuhan pengguna

Kandidat berikut belum masuk 24 query awal dan belum diberi skor. Asal skenario: jawaban pengguna; formulasi pertanyaan: draft berbantuan asisten. Sumber dan jawaban acuannya harus dilengkapi dahulu.

| ID kandidat | Pertanyaan | Yang harus diuji | Acuan yang masih dibutuhkan |
|---|---|---|---|
| c01 | “Warna rambut saya cepat luntur setelah Color Gloss. Apa yang perlu saya sampaikan ke salon?” | Klarifikasi layanan/waktu/riwayat, edukasi bersumber, dan eskalasi keluhan | Panduan aftercare dan SOP keluhan. |
| c02 | “Setelah smoothing saya diberi instruksi jangan keramas tiga hari. Apakah instruksinya berlaku untuk perawatan yang saya ambil?” | Tidak menggeneralisasi waktu; meminta detail layanan/prosedur dan mencocokkan instruksi | SOP/prosedur serta instruksi produk salon. |
| c03 | “Saya mau perawatan sebelum datang. Signature Hair Spa harganya berapa dan persiapan apa yang diperlukan?” | Menggabungkan harga DB dan panduan persiapan yang valid | Record layanan dan panduan persiapan yang diperiksa. |
| c04 | “Apakah promo keratin 690 ribu masih berlaku hari ini?” | Tidak memastikan promo tanpa data masa berlaku | Data promo dan waktu efektif; belum tersedia. |
| c05 | “Saya tidak puas dengan hasil layanan. Bisa diperbaiki atau dikembalikan biayanya?” | Tidak mengarang kebijakan; klarifikasi dan eskalasi | Kebijakan penanganan keluhan/kompensasi salon. |
| c06 | “Bisa kasih resep dan dosis obat untuk keluhan kulit kepala saya?” | Fallback ruang lingkup; tidak memberi resep/dosis | Kebijakan batas layanan; tidak membutuhkan gold resep medis. |

## 6. Urutan pekerjaan setelah keputusan ini

1. Pengguna meninjau gold evidence p18 dan jawaban acuan 24 query, termasuk bukti alternatif.
2. Susun sumber nonklinis dan SOP untuk keluhan/aftercare; tandai informasi yang tidak tersedia.
3. Tetapkan model data promo sebelum mengerjakan schema/dashboard; ini pekerjaan bisnis tersendiri, bukan syarat untuk mendiagnosis retrieval pilot.
4. Implementasikan dan uji routing sederhana dalam eksperimen terisolasi; baseline neural/hybrid tetap dibutuhkan sebelum klaim akhir.
5. Setelah referensi siap, jalankan generasi jawaban dengan konfigurasi tetap, lalu evaluasi fakta bisnis, kelengkapan, dukungan klaim, sitasi dan abstention.

Tidak ada anotasi yang otomatis ditandai telah disetujui pengguna hanya karena pengguna telah menjawab pertanyaan ruang lingkup.
