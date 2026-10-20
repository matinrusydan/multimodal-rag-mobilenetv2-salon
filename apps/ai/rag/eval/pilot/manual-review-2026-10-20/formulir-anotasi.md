# Paket anotasi manual 24 pertanyaan pilot

Status: seluruh jawaban masih menunggu peneliti.

Anotator: diisi pengguna. Tanggal penilaian: diisi saat menjawab. Snapshot DB: 20 Oktober 2026, bukan harga yang dijamin berlaku selamanya.

## Cara mengisi

Isi per item: K=jelas/perlu revisi; R=masuk akal/tidak/belum tahu sebagai pertanyaan calon pengguna (bukan bukti pernah ditanyakan pelanggan); D=penuh/sebagian/tidak/tidak dapat dinilai untuk dukungan jawaban oleh bukti; S=layak/perlu verifikasi/tidak layak untuk kelayakan sumber sebagai acuan penelitian; A=dapat dijawab/sebagian/perlu klarifikasi/tidak dapat dijawab dari korpus ini; Putusan=terima/revisi/tunda/tolak. Tambahkan koreksi, alasan, sumber atau bukti alternatif jika ada. Jangan menebak jika belum tahu. Penilaian R dan S adalah opini peneliti tunggal, bukan validasi pelanggan atau ahli.

Penilaian dukungan teks dipisahkan dari kelayakan sumber. Jawaban dapat cocok dengan Markdown, sementara Markdown belum layak sebagai referensi ilmiah. Dokumen lama belum memiliki rujukan primer terverifikasi. Ini pemeriksaan gold retrieval/jawaban acuan, bukan penilaian keluaran chatbot.

Untuk pertanyaan ambigu/tidak terjawab, K menilai apakah skenarionya dapat dipahami, bukan apakah informasinya lengkap. Bukti kosong tidak cukup membuktikan ketiadaan informasi; periksa batas snapshot/korpus. Persetujuan atas kebijakan fallback dicatat sebagai keputusan ruang lingkup, bukan passage hasil retrieval.

## Informasi anotator dan data

Nama/alias anotator: ____; tanggal: ____; data layanan nyata/simulasi/belum pasti: ____; apakah snapshot cocok dengan data yang ingin diuji: ____.

## p01

**Pertanyaan:** Berapa harga reguler dan durasi Signature Hair Spa yang tercatat?

**Jawaban acuan draft:** Signature Hair Spa: harga reguler Rp325,000, durasi 90 menit, sesuai snapshot. Promo tidak diasumsikan.

**Bukti yang harus diperiksa:**

### db:services:1

Sumber: services.snapshot.json / Signature Hair Spa (db).

> Layanan: Signature Hair Spa
> Harga reguler: Rp325,000
> Durasi: 90 menit
> Deskripsi: Ritual hair spa khas TIEN SALON dengan pijatan relaksasi kulit kepala, masker rambut bernutrisi, dan finishing lembut untuk mengembalikan kelembapan rambut.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p02

**Pertanyaan:** Berapa harga reguler dan durasi Precision Haircut yang tercatat?

**Jawaban acuan draft:** Precision Haircut: harga reguler Rp220,000, durasi 60 menit, sesuai snapshot. Promo tidak diasumsikan.

**Bukti yang harus diperiksa:**

### db:services:2

Sumber: services.snapshot.json / Precision Haircut (db).

> Layanan: Precision Haircut
> Harga reguler: Rp220,000
> Durasi: 60 menit
> Deskripsi: Layanan haircut dengan konsultasi singkat, shaping presisi, dan styling akhir agar potongan rambut terasa rapi, ringan, dan mudah diatur.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p03

**Pertanyaan:** Berapa harga reguler dan durasi Keratin Smooth Treatment yang tercatat?

**Jawaban acuan draft:** Keratin Smooth Treatment: harga reguler Rp780,000, durasi 150 menit, sesuai snapshot. Promo tidak diasumsikan.

**Bukti yang harus diperiksa:**

### db:services:3

Sumber: services.snapshot.json / Keratin Smooth Treatment (db).

> Layanan: Keratin Smooth Treatment
> Harga reguler: Rp780,000
> Durasi: 150 menit
> Deskripsi: Perawatan keratin untuk membantu mengurangi tampilan frizz dan membuat rambut terasa lebih halus tanpa menghilangkan karakter natural rambut.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p04

**Pertanyaan:** Berapa harga reguler dan durasi Color Gloss Refresh yang tercatat?

**Jawaban acuan draft:** Color Gloss Refresh: harga reguler Rp620,000, durasi 130 menit, sesuai snapshot. Promo tidak diasumsikan.

**Bukti yang harus diperiksa:**

### db:services:4

Sumber: services.snapshot.json / Color Gloss Refresh (db).

> Layanan: Color Gloss Refresh
> Harga reguler: Rp620,000
> Durasi: 130 menit
> Deskripsi: Layanan pewarnaan rambut untuk menyegarkan tone, menambah kilau, dan membuat warna rambut terlihat lebih hidup dengan hasil tetap elegan.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p05

**Pertanyaan:** Berapa harga reguler dan durasi Scalp Detox Therapy yang tercatat?

**Jawaban acuan draft:** Scalp Detox Therapy: harga reguler Rp360,000, durasi 75 menit, sesuai snapshot. Promo tidak diasumsikan.

**Bukti yang harus diperiksa:**

### db:services:5

Sumber: services.snapshot.json / Scalp Detox Therapy (db).

> Layanan: Scalp Detox Therapy
> Harga reguler: Rp360,000
> Durasi: 75 menit
> Deskripsi: Ritual detox kulit kepala dengan cleansing, massage, dan tonic care untuk membantu rambut terasa lebih ringan dari akar.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p06

**Pertanyaan:** Berapa harga reguler dan durasi Volume Blowout Styling yang tercatat?

**Jawaban acuan draft:** Volume Blowout Styling: harga reguler Rp280,000, durasi 55 menit, sesuai snapshot. Promo tidak diasumsikan.

**Bukti yang harus diperiksa:**

### db:services:6

Sumber: services.snapshot.json / Volume Blowout Styling (db).

> Layanan: Volume Blowout Styling
> Harga reguler: Rp280,000
> Durasi: 55 menit
> Deskripsi: Styling rambut dengan blowout natural untuk memberi volume, movement, dan hasil akhir yang rapi tanpa terlihat berlebihan.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p07

**Pertanyaan:** Menurut panduan, kondisioner digunakan di bagian rambut mana?

**Jawaban acuan draft:** Bagian tengah hingga ujung; hindari akar.

**Bukti yang harus diperiksa:**

### md:tips-perawatan.md:a54925e92feb:0

Sumber: tips-perawatan.md / Perawatan Dasar (manual_legacy).

> - Cuci rambut sesuai kebutuhan; tidak terlalu sering agar minyak alami tidak hilang. - Gunakan sampo yang sesuai jenis kulit kepala dan rambut. - Gunakan kondisioner dari bagian tengah hingga ujung, hindari akar. - Keringkan dengan handuk lembut atau biarkan alami; hindari menggosok rambut keras. - Batasi penggunaan alat panas bersuhu tinggi.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p08

**Pertanyaan:** Menurut panduan, sampo seperti apa yang digunakan setelah pewarnaan?

**Jawaban acuan draft:** Sampo khusus warna; ikuti instruksi stylist.

**Bukti yang harus diperiksa:**

### md:tips-perawatan.md:a54925e92feb:5

Sumber: tips-perawatan.md / Perawatan Setelah Treatment di Salon (manual_legacy).

> - Ikuti instruksi dari stylist mengenai larangan keramas atau pemakaian produk tertentu. - Untuk smoothing/keratin: hindari air dan ikat rambut pada 48 jam pertama. - Untuk pewarnaan: gunakan sampo khusus warna untuk menjaga warna tetap awet.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p09

**Pertanyaan:** Apa catatan panduan mengenai menyisir rambut keriting saat kering?

**Jawaban acuan draft:** Panduan menyatakan jangan menyisir rambut keriting dalam keadaan kering.

**Bukti yang harus diperiksa:**

### md:tips-perawatan.md:a54925e92feb:3

Sumber: tips-perawatan.md / Rambut Keriting (manual_legacy).

> Utamakan kelembapan. Gunakan conditioner tanpa bilas dan jangan menyisir rambut kering.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p10

**Pertanyaan:** Apa isi panduan perawatan untuk rambut rusak dan bercabang?

**Jawaban acuan draft:** Panduan menyebut deep conditioning, mengurangi alat panas, pemangkasan ujung, dan menghindari bleaching ulang sebelum pulih.

**Bukti yang harus diperiksa:**

### md:panduan-layanan.md:58aa4b98724d:1

Sumber: panduan-layanan.md / Rambut Rusak / Bercabang (manual_legacy).

> Disarankan deep conditioning rutin, mengurangi alat panas, dan pemangkasan ujung berkala. Hindari bleaching ulang sebelum rambut pulih.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p11

**Pertanyaan:** Apa isi panduan untuk rambut kering atau kusam?

**Jawaban acuan draft:** Utamakan kelembapan, kondisioner dan hair mask; hindari keramas air panas.

**Bukti yang harus diperiksa:**

### md:panduan-layanan.md:58aa4b98724d:4

Sumber: panduan-layanan.md / Rambut Kering / Kusam (manual_legacy).

> Utamakan kelembapan: kondisioner, hair mask, dan hindari keramas air panas.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p12

**Pertanyaan:** Menurut panduan, apa tindak lanjut bila kerontokan berlebihan menetap?

**Jawaban acuan draft:** Konsultasi ke dokter atau ahli dermatologi; bukan diagnosis oleh chatbot.

**Bukti yang harus diperiksa:**

### md:panduan-layanan.md:58aa4b98724d:2

Sumber: panduan-layanan.md / Rambut Rontok (manual_legacy).

> Perhatikan pola makan, kelola stres, dan gunakan sampo lembut. Bila rontok berlebihan dan menetap, disarankan konsultasi ke dokter/ahli dermatologi.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p13

**Pertanyaan:** Berapa harga Signature Hair Spa dan di bagian mana kondisioner dipakai menurut panduan?

**Jawaban acuan draft:** Harga mengikuti snapshot; kondisioner di tengah hingga ujung, hindari akar.

**Bukti yang harus diperiksa:**

### db:services:1

Sumber: services.snapshot.json / Signature Hair Spa (db).

> Layanan: Signature Hair Spa
> Harga reguler: Rp325,000
> Durasi: 90 menit
> Deskripsi: Ritual hair spa khas TIEN SALON dengan pijatan relaksasi kulit kepala, masker rambut bernutrisi, dan finishing lembut untuk mengembalikan kelembapan rambut.

### md:tips-perawatan.md:a54925e92feb:0

Sumber: tips-perawatan.md / Perawatan Dasar (manual_legacy).

> - Cuci rambut sesuai kebutuhan; tidak terlalu sering agar minyak alami tidak hilang. - Gunakan sampo yang sesuai jenis kulit kepala dan rambut. - Gunakan kondisioner dari bagian tengah hingga ujung, hindari akar. - Keringkan dengan handuk lembut atau biarkan alami; hindari menggosok rambut keras. - Batasi penggunaan alat panas bersuhu tinggi.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p14

**Pertanyaan:** Berapa harga reguler Keratin Smooth Treatment dan siapa yang memberi instruksi perawatan setelahnya?

**Jawaban acuan draft:** Harga mengikuti snapshot; ikuti instruksi stylist, jangan menganggap aturan waktu universal.

**Bukti yang harus diperiksa:**

### db:services:3

Sumber: services.snapshot.json / Keratin Smooth Treatment (db).

> Layanan: Keratin Smooth Treatment
> Harga reguler: Rp780,000
> Durasi: 150 menit
> Deskripsi: Perawatan keratin untuk membantu mengurangi tampilan frizz dan membuat rambut terasa lebih halus tanpa menghilangkan karakter natural rambut.

### md:tips-perawatan.md:a54925e92feb:5

Sumber: tips-perawatan.md / Perawatan Setelah Treatment di Salon (manual_legacy).

> - Ikuti instruksi dari stylist mengenai larangan keramas atau pemakaian produk tertentu. - Untuk smoothing/keratin: hindari air dan ikat rambut pada 48 jam pertama. - Untuk pewarnaan: gunakan sampo khusus warna untuk menjaga warna tetap awet.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p15

**Pertanyaan:** Berapa harga Color Gloss Refresh dan sampo apa yang disebut panduan setelah pewarnaan?

**Jawaban acuan draft:** Harga mengikuti snapshot; panduan menyebut sampo khusus warna.

**Bukti yang harus diperiksa:**

### db:services:4

Sumber: services.snapshot.json / Color Gloss Refresh (db).

> Layanan: Color Gloss Refresh
> Harga reguler: Rp620,000
> Durasi: 130 menit
> Deskripsi: Layanan pewarnaan rambut untuk menyegarkan tone, menambah kilau, dan membuat warna rambut terlihat lebih hidup dengan hasil tetap elegan.

### md:tips-perawatan.md:a54925e92feb:5

Sumber: tips-perawatan.md / Perawatan Setelah Treatment di Salon (manual_legacy).

> - Ikuti instruksi dari stylist mengenai larangan keramas atau pemakaian produk tertentu. - Untuk smoothing/keratin: hindari air dan ikat rambut pada 48 jam pertama. - Untuk pewarnaan: gunakan sampo khusus warna untuk menjaga warna tetap awet.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p16

**Pertanyaan:** Berapa harga Scalp Detox Therapy dan apa tindak lanjut panduan bila kulit kepala perih?

**Jawaban acuan draft:** Harga mengikuti snapshot; konsultasi profesional, tanpa menjanjikan layanan menyembuhkan keluhan.

**Bukti yang harus diperiksa:**

### db:services:5

Sumber: services.snapshot.json / Scalp Detox Therapy (db).

> Layanan: Scalp Detox Therapy
> Harga reguler: Rp360,000
> Durasi: 75 menit
> Deskripsi: Ritual detox kulit kepala dengan cleansing, massage, dan tonic care untuk membantu rambut terasa lebih ringan dari akar.

### md:tips-perawatan.md:a54925e92feb:6

Sumber: tips-perawatan.md / Tanda Rambut Perlu Perhatian (manual_legacy).

> - Rambut terasa sangat kering, kusut berlebihan, atau banyak bercabang. - Kulit kepala gatal, berketombe, atau terasa perih. - Rambut rontok dalam jumlah tidak wajar. Bila mengalami tanda tersebut, sebaiknya berkonsultasi dengan profesional. TIEN SALON menyediakan konsultasi dan perawatan yang sesuai dengan kondisi rambut Anda.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p17

**Pertanyaan:** Berapa biaya Precision Haircut dan apa isi panduan mengenai ujung bercabang?

**Jawaban acuan draft:** Harga mengikuti snapshot; panduan menyebut pemangkasan ujung berkala dan perawatan, bukan jaminan terapi.

**Bukti yang harus diperiksa:**

### db:services:2

Sumber: services.snapshot.json / Precision Haircut (db).

> Layanan: Precision Haircut
> Harga reguler: Rp220,000
> Durasi: 60 menit
> Deskripsi: Layanan haircut dengan konsultasi singkat, shaping presisi, dan styling akhir agar potongan rambut terasa rapi, ringan, dan mudah diatur.

### md:panduan-layanan.md:58aa4b98724d:1

Sumber: panduan-layanan.md / Rambut Rusak / Bercabang (manual_legacy).

> Disarankan deep conditioning rutin, mengurangi alat panas, dan pemangkasan ujung berkala. Hindari bleaching ulang sebelum rambut pulih.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p18

**Pertanyaan:** Berapa harga serta durasi Volume Blowout Styling dan isi panduan untuk rambut kering?

**Jawaban acuan draft:** Harga/durasi mengikuti snapshot; penjelasan perawatan mengikuti passage rambut kering.

**Bukti yang harus diperiksa:**

### db:services:6

Sumber: services.snapshot.json / Volume Blowout Styling (db).

> Layanan: Volume Blowout Styling
> Harga reguler: Rp280,000
> Durasi: 55 menit
> Deskripsi: Styling rambut dengan blowout natural untuk memberi volume, movement, dan hasil akhir yang rapi tanpa terlihat berlebihan.

### md:panduan-layanan.md:58aa4b98724d:4

Sumber: panduan-layanan.md / Rambut Kering / Kusam (manual_legacy).

> Utamakan kelembapan: kondisioner, hair mask, dan hindari keramas air panas.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p19

**Pertanyaan:** Markdown menyebut Hair Spa promo Rp285.000. Berapa harga reguler pada database dan apakah promo itu bisa dipastikan?

**Jawaban acuan draft:** Harga reguler snapshot Rp325.000; snapshot tidak memiliki field promo, promo tidak dapat dipastikan.

**Bukti yang harus diperiksa:**

### db:services:1

Sumber: services.snapshot.json / Signature Hair Spa (db).

> Layanan: Signature Hair Spa
> Harga reguler: Rp325,000
> Durasi: 90 menit
> Deskripsi: Ritual hair spa khas TIEN SALON dengan pijatan relaksasi kulit kepala, masker rambut bernutrisi, dan finishing lembut untuk mengembalikan kelembapan rambut.

Catatan: bukti DB mendukung harga reguler. Pernyataan tidak dapat memastikan promo memerlukan pemeriksaan cakupan field dan sumber promo; angka promo dalam pertanyaan bukan bukti keberlakuannya.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p20

**Pertanyaan:** Berapa harga Keratin kemarin sebelum berubah hari ini?

**Jawaban acuan draft:** Snapshot tidak memuat riwayat harga; harga kemarin dan perubahan hari ini tidak dapat dipastikan.

**Bukti yang harus diperiksa:**

Tidak ada passage gold. Periksa ketersediaan informasi atau kebijakan klarifikasi/fallback; jangan menandai dukungan passage sebagai penuh.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p21

**Pertanyaan:** Berapa biaya treatment itu?

**Jawaban acuan draft:** Minta nama layanan yang dimaksud sebelum memberi harga.

**Bukti yang harus diperiksa:**

Tidak ada passage gold. Periksa ketersediaan informasi atau kebijakan klarifikasi/fallback; jangan menandai dukungan passage sebagai penuh.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p22

**Pertanyaan:** Berapa dosis obat resep yang harus saya minum untuk ketombe?

**Jawaban acuan draft:** Dosis obat resep tidak tersedia dalam korpus dan memerlukan penilaian tenaga kesehatan; jangan mengarang.

**Bukti yang harus diperiksa:**

Tidak ada passage gold. Periksa ketersediaan informasi atau kebijakan klarifikasi/fallback; jangan menandai dukungan passage sebagai penuh.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p23

**Pertanyaan:** Apa perbedaan harga reguler dan durasi Signature Hair Spa dibanding Scalp Detox Therapy?

**Jawaban acuan draft:** Bandingkan dua record snapshot, jangan menukar harga atau durasinya.

**Bukti yang harus diperiksa:**

### db:services:1

Sumber: services.snapshot.json / Signature Hair Spa (db).

> Layanan: Signature Hair Spa
> Harga reguler: Rp325,000
> Durasi: 90 menit
> Deskripsi: Ritual hair spa khas TIEN SALON dengan pijatan relaksasi kulit kepala, masker rambut bernutrisi, dan finishing lembut untuk mengembalikan kelembapan rambut.

### db:services:5

Sumber: services.snapshot.json / Scalp Detox Therapy (db).

> Layanan: Scalp Detox Therapy
> Harga reguler: Rp360,000
> Durasi: 75 menit
> Deskripsi: Ritual detox kulit kepala dengan cleansing, massage, dan tonic care untuk membantu rambut terasa lebih ringan dari akar.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

## p24

**Pertanyaan:** Apakah Keratin Smooth Treatment masih Rp690.000? Berapa harga reguler yang tercatat?

**Jawaban acuan draft:** Harga reguler snapshot Rp780.000; keberlakuan promo Rp690.000 tidak dapat dipastikan.

**Bukti yang harus diperiksa:**

### db:services:3

Sumber: services.snapshot.json / Keratin Smooth Treatment (db).

> Layanan: Keratin Smooth Treatment
> Harga reguler: Rp780,000
> Durasi: 150 menit
> Deskripsi: Perawatan keratin untuk membantu mengurangi tampilan frizz dan membuat rambut terasa lebih halus tanpa menghilangkan karakter natural rambut.

Catatan: bukti DB mendukung harga reguler. Pernyataan tidak dapat memastikan promo memerlukan pemeriksaan cakupan field dan sumber promo; angka promo dalam pertanyaan bukan bukti keberlakuannya.

**Anotasi Anda:** K=____; R=____; D=____; S=____; A=____; Putusan=____.

Alasan/koreksi: ____

Bukti alternatif (file/URL, halaman/bagian, kutipan): ____

