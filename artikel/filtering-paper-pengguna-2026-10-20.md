# Filtering awal paper pengguna untuk penelitian RAG salon

Tanggal: 20 Oktober 2026. Cakupan: 10 PDF langsung dalam folder artikel; 19 PDF unduhan baru belum menjalani penilaian kualitas penuh dalam laporan ini.
Kriteria: tahun 2021–2026; fokus RAG konsultasi layanan/harga dari database dan perawatan dari dokumen. Seleksi berdasarkan abstrak, bagian metode/hasil yang relevan, serta simpulan bila tersedia.
**Hasil: 6 kandidat pendukung (3 prioritas konteks, 3 opsional), 4 di luar seleksi utama. Tidak ada kandidat metode RAG langsung yang sekaligus memenuhi batas tahun pada 10 PDF pengguna.**
Kandidat adalah hasil screening awal, bukan jaminan dimasukkan ke naskah final. Semua PDF asli dipertahankan; belum dipindahkan atau digabung secara fisik.

## Hasil per paper

### U01 — An analysis of strategic planning of the development of beauty industry in Indonesia (2026)

- Sumber: [2.+19257+Afrizal+Firman+(1).pdf](<2.+19257+Afrizal+Firman+(1).pdf>)
- Keputusan: candidate_optional; Pelengkap.
- Peran: Konteks industri.
- Halaman PDF rujukan screening: 1, 13.
- Alasan: Kajian strategis dengan data sekunder dan Porter/SWOT/TOWS; konteks industri kecantikan lebih luas daripada konsultasi salon.
- Batas pemakaian: Bukan bukti kebutuhan chatbot atau kelemahan retrieval. Telusuri sumber primer sebelum mengutip angka industri.

### U02 — Pengaruh kualitas layanan, kualitas produk dan harga terhadap kepuasan pelanggan salon di Tanjung Tabalong Kalimantan Selatan (2025)

- Sumber: [588-597+JAEMB_IKE.pdf](<588-597+JAEMB_IKE.pdf>)
- Keputusan: candidate_priority; Utama untuk konteks.
- Peran: Latar belakang objek salon.
- Halaman PDF rujukan screening: 1, 5, 9.
- Alasan: Survei 100 pelanggan salon dengan regresi; mendukung pentingnya aspek layanan, produk, dan harga dalam konteks salon.
- Batas pemakaian: Tidak menguji chatbot, ketepatan informasi harga, atau kepuasan pengguna RAG. Temuan salon tertentu tidak langsung berlaku bagi TIEN.

### U03 — Profil pengetahuan, ketepatan tindakan, dan pemilihan produk dalam mengatasi ketombe pada mahasiswi berhijab di Universitas Airlangga (2024)

- Sumber: [1.+Diva+Daeng+Prayogo+et+al.pdf](<1.+Diva+Daeng+Prayogo+et+al.pdf>)
- Keputusan: candidate_priority; Utama untuk konteks.
- Peran: Bukti kebutuhan edukasi/perawatan.
- Halaman PDF rujukan screening: 1, 3, 5, 6.
- Alasan: Survei deskriptif 161 responden; pembahasan tindakan dan pemilihan produk pada 139 responden yang pernah berketombe dapat mendukung kebutuhan informasi.
- Batas pemakaian: Populasi khusus; bukan prevalensi nasional. Periksa konsistensi label tabel dan denominator sebelum memakai angka. Tidak membuktikan RAG memperbaiki tindakan; belum otomatis layak menjadi ground truth saran medis.

### U04 — Faktor-faktor yang berhubungan dengan kejadian pityriasis capitis pada mahasiswi Fakultas Kedokteran Universitas Muslim Indonesia angkatan 2021 (2026)

- Sumber: [10301-29624-3-PB.pdf](<10301-29624-3-PB.pdf>)
- Keputusan: candidate_optional; Pelengkap bersyarat.
- Peran: Konteks perawatan kulit kepala.
- Halaman PDF rujukan screening: 1, 10.
- Alasan: Studi potong lintang 199 mahasiswi tentang faktor yang berhubungan dengan ketombe dan kebutuhan edukasi.
- Batas pemakaian: Hubungan observasional bukan kausalitas. Masukkan hanya bila ketombe termasuk cakupan pertanyaan; bukan panduan diagnosis atau terapi dan bukan bukti gap RAG.

### U05 — Perancangan bangun sistem informasi jasa kecantikan berbasis web pada Annisavy (2026)

- Sumber: [DEA+AMELIA+PUTRI+EDIT+INTERCOMS+DONE+2026.pdf](<DEA+AMELIA+PUTRI+EDIT+INTERCOMS+DONE+2026.pdf>)
- Keputusan: candidate_priority; Utama untuk konteks.
- Peran: Penelitian terkait aplikasi jasa kecantikan.
- Halaman PDF rujukan screening: 1, 3, 7, 8.
- Alasan: Sistem informasi web dengan Waterfall, wawancara/observasi, pengelolaan layanan dan transaksi, serta pengujian fungsi.
- Batas pemakaian: Objek mencakup nail art, eyelash, dan MUA; bukan khusus perawatan rambut. Waterfall/black-box bukan pembanding algoritma retrieval. Ketiadaan RAG dalam paper tidak membuktikan ketiadaan RAG secara global.

### U06 — Klasifikasi jenis rambut berbasis citra menggunakan convolutional neural network dengan arsitektur MobileNetV2 (2026)

- Sumber: [2091-2100+-+Klasifikasi+Jenis+Rambut+Berbasis+Citra+Menggunakan+Convolutional+Neural+Network+dengan+Arsitektur+MobileNetV2.pdf](<2091-2100+-+Klasifikasi+Jenis+Rambut+Berbasis+Citra+Menggunakan+Convolutional+Neural+Network+dengan+Arsitektur+MobileNetV2.pdf>)
- Keputusan: exclude_current_scope; Di luar mapping utama.
- Peran: Arsip CV.
- Halaman PDF rujukan screening: 1.
- Alasan: Klasifikasi citra rambut; fokus CV, bukan retrieval atau generation.
- Batas pemakaian: Simpan untuk penelitian CV berikutnya; jangan campurkan metrik klasifikasi citra dengan evaluasi RAG.

### U07 — Hairmony: Fairness-aware hairstyle classification (2024)

- Sumber: [2410.11528v1.pdf](<2410.11528v1.pdf>)
- Keputusan: exclude_current_scope; Di luar mapping utama.
- Peran: Arsip CV.
- Halaman PDF rujukan screening: 1, 9.
- Alasan: Taksonomi dan klasifikasi gaya rambut; bukan penelitian RAG.
- Batas pemakaian: Berkas lokal merupakan versi arXiv v1; versi terbit perlu diverifikasi bila kelak dipakai.

### U08 — 3D hair style recommendation and salon scheduling (2025)

- Sumber: [3D-Hair-Style-Recommendation-And-Salon-Scheduling.pdf](<3D-Hair-Style-Recommendation-And-Salon-Scheduling.pdf>)
- Keputusan: candidate_optional; Pelengkap.
- Peran: Penelitian terkait aplikasi salon.
- Halaman PDF rujukan screening: 1, 3, 5.
- Alasan: Menggabungkan reservasi salon dengan rekomendasi/visualisasi gaya rambut; dekat secara aplikasi.
- Batas pemakaian: Paper prosiding, bukan jurnal. Bukan pembanding metode RAG; klaim efektivitas perlu ditinjau terhadap rincian pengujiannya sebelum digunakan.

### U09 — MobileNetV2: Inverted residuals and linear bottlenecks (2018)

- Sumber: [1801.04381v4.pdf](<1801.04381v4.pdf>)
- Keputusan: exclude_year_and_scope; Di luar mapping utama.
- Peran: Arsip dasar CV.
- Halaman PDF rujukan screening: 1, 8.
- Alasan: Di luar batas tahun 2021–2026 dan fokus CV.
- Batas pemakaian: Tidak dihapus; tidak disertakan dalam korpus seleksi utama saat ini.

### U10 — Retrieval-augmented generation for knowledge-intensive NLP tasks (2020)

- Sumber: [NeurIPS-2020-retrieval-augmented-generation-for-knowledge-intensive-nlp-tasks-Paper.pdf](<NeurIPS-2020-retrieval-augmented-generation-for-knowledge-intensive-nlp-tasks-Paper.pdf>)
- Keputusan: exclude_year; Di luar batas tahun.
- Peran: Referensi fondasional RAG.
- Halaman PDF rujukan screening: 1.
- Alasan: Relevan langsung dengan RAG, tetapi terbit 2020 sehingga tidak memenuhi batas tahun pengguna.
- Batas pemakaian: Tetap disimpan. Memasukkannya sebagai pengecualian referensi fondasional memerlukan perubahan kriteria; jangan mengubah tahunnya menjadi 2021.

## Penggabungan untuk mapping berikutnya

Gabungkan secara logis ID U01–U05 dan U08 dengan daftar 19 PDF berhasil diunduh dalam subfolder unduhan-rag-2021-2026-2026-10-20: total 25 kandidat untuk ditelaah lebih lanjut, bukan 25 paper metode atau 25 paper yang telah lolos penilaian kualitas.
Gunakan peran yang eksplisit pada setiap baris mapping: metode/evaluasi RAG, konteks aplikasi salon, atau kebutuhan informasi perawatan. Kolom minimum: ID, judul, tahun, jenis publikasi, masalah, metode, data, hasil, keterbatasan, peran untuk penelitian, bukti halaman, keputusan.
Paper pendukung domain tidak menjadi bukti kebaruan algoritma. Bug implementasi dan ketiadaan fitur dalam satu aplikasi tidak otomatis menjadi gap literatur.
Pengetahuan perawatan yang akan menjadi knowledge base memerlukan kurasi tersendiri; hasil survei kebutuhan informasi tidak otomatis menjadi jawaban referensi terapi.
Untuk pendahuluan, gunakan hubungan klaim–bukti–cakupan populasi; jangan menulis masalah pelanggan TIEN sebagai fakta sebelum ada bukti lokal.
