# Korpus edukasi umum dan acuan evaluasi kandidat

Status: siap untuk peninjauan dan development offline, belum menjadi gold final/publikasi atau knowledge base aktif.

Korpus: 13 evidence, terdiri atas enam record layanan dari snapshot lama dan tujuh parafrasa edukasi umum. Sumber edukasi: lima panduan resmi bertanggal dan satu artikel review jurnal terbit, semuanya bertanggal 2022–2025. Tidak ada merek internal salon.

Acuan: 24 pertanyaan; 20 memiliki kelompok bukti retrieval. r07 memiliki pertanyaan baru yang memperjelas cakupan kondisioner. Seluruh ID berubah agar versi lama dan baru tidak tertukar.

## Berkas

- `corpus.json`: candidate evidence beserta ID, URL, tanggal, locator, hash teks parafrasa, dan batas konteks.
- `education/`: tujuh dokumen Markdown, disimpan di area evaluasi, di luar knowledge base produksi.
- `questions.json` dan `acuan-evaluasi.md`: acuan baru, keterjawaban, lineage, kelompok bukti dan tindakan yang diharapkan.
- `evaluation-context.json`: kebijakan yang sama bagi semua konfigurasi dan batas data snapshot. Kebijakan bukan passage ilmiah hasil retrieval.
- `source-register.json`: enam sumber terpilih, tiga sumber tidak dimasukkan, serta catatan robots dari audit.
- `protocol.json` dan `manifest.json`: ruang lingkup dan integritas versi.

## Batas evaluasi

Kelompok bukti retrieval hanya mengukur kebutuhan faktual yang memang memiliki bukti. Untuk pertanyaan partial, keberhasilan mengambil harga tidak berarti seluruh pertanyaan terjawab. Kelengkapan jawaban, kepatuhan kebijakan, abstention, dan ketepatan angka perlu metrik terpisah. r08/r20/r21/r22 tidak mempunyai gold retrieval; tidak dihitung sukses otomatis.

Pada r21, pilihan enam layanan diambil sebagai lookup katalog. Tidak diwajibkan mengambil enam passage pada top-5. Pada r16, sumber reaksi pewarna bersifat kondisional; jangan menggunakannya untuk menetapkan semua penyebab kulit kepala perih.

Sampo spesifik, waktu larangan keramas setelah keratin, diskon, histori harga, dan alasan kebijakan perubahan harga belum direka sebagai fakta. Rekomendasi resep/dosis tetap di luar cakupan.

Korpus ini kecil dan diseleksi berdasarkan masalah development; hasilnya nanti tidak dapat langsung dibandingkan dengan skor pilot lama untuk membuktikan peningkatan algoritma. Tidak ada pemisahan test final, model yang dijalankan, crawling baru, ingest, atau perubahan database.

## Langkah selanjutnya

Tinjau redaksi kandidat dan relasi klaim–bukti, lalu tentukan versi yang dibekukan. Setelah itu jalankan baseline pada versi yang sama, perluas cakupan korpus/pertanyaan, pisahkan keluarga pertanyaan development/test, dan ukur perilaku sesuai jenis tugas. Hash parafrasa bukan hash halaman web asli.
