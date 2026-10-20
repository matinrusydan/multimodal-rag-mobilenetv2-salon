# Pemulihan gambar asli dari thumbnail

Audit riwayat unduhan Brave (profil Default, 19 Oktober 2026) tidak menemukan path unduhan yang langsung cocok dengan `dataset/new_dataset/`. Ada 137 catatan dengan **nama file** yang cocok, tetapi nama seperti `download.jpg` berulang di beberapa kelas; kecocokan nama **bukan bukti** file yang sama. URL chain mayoritas menunjuk thumbnail `encrypted-tbn*.gstatic.com`; tidak boleh dianggap URL gambar asli. Karena itu belum ada gambar yang dipulihkan otomatis, dan seluruh 137 thumbnail dimasukkan ke antrean manual. Riwayat browser tidak disalin ke folder ini.

## Cara mencari dan mengisi

1. Lihat gambar di `manual_reverse_search/<kelas>/`; cari versi asli melalui Google Lens/Bing Visual Search, lalu cek halaman sumber, izin pemakaian, dan resolusinya. Dahulukan `sangat-keriting` dan `keriting`.
2. Salin hasil ke `manual_recovered_originals/<kelas>/` dengan **ID yang sama** seperti thumbnail, mengganti akhiran `__thumbnail.jpg` menjadi `__original.jpg`. Jangan mengubah/menghapus file di `dataset/new_dataset/` atau `dataset/figaro1k/`.
3. Isi `source_page_url` dan `direct_image_url` pada `recovery_manifest.csv` bila diketahui. Jangan memasukkan URL bertoken autentikasi atau data pribadi.
4. Versi asli belum otomatis diterima sebagai data latih. Sebelum merge, periksa kecocokan visual dengan thumbnail, lisensi, ketajaman, label, resolusi (minimal sisi terpendek 224 px), dan duplikasi/near-duplicate terhadap kedua dataset. Simpan hanya gambar yang lolos ke dataset hasil merge **setelah** review.

`recovered_candidates/` disediakan untuk kandidat dari pemulihan otomatis di masa depan; saat ini kosong. Folder hasil manual juga kosong. Manifest mencatat satu baris per thumbnail, termasuk ID stabil berdasarkan path relatif, dimensi, SHA-256, dan dua pasangan dugaan duplikat yang perlu ditinjau. Tidak ada dataset sumber yang dipindah, ditimpa, atau digabung pada tahap ini.
