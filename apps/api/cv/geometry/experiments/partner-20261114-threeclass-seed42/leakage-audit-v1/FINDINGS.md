# Audit leakage — temuan terverifikasi visual

## Kesimpulan

**Ada near-duplicate leakage lintas split.** Tidak ada file/piksel identik, tetapi inspeksi visual menemukan dua pasangan foto sumber sama dengan crop/ukuran/encoding berbeda. Karena itu angka validasi98.25% dan test96.61% bukan estimasi bersih bebas duplikat.

## Cakupan

- 654 gambar: 538 train,57 val,59 test.
- 65,771 pasangan lintas split disaring full/mirror/center-crop pHash dan thumbnail correlation.
- 3,825 kandidat diperiksa SIFT + RANSAC homography;24 flag geometris.
-24 flag geometris ditinjau dalam contact sheets. Setidaknya dua pasangan dikonfirmasi sebagai foto sumber sama; flag lain tidak otomatis duplikat. Beberapa jelas berbagi watermark/latar; identitas subjek tidak ditentukan.

## Dua pasangan foto sumber sama

1. **Train–test**, `pair_000.jpg`: test `dataset/new_dataset/lurus/images (8).jpg` vs train supplemental `dataset/partner/lurus/fa938cdc805c4cde9806945b417dedf6.jpg`. Tampak rambut, pakaian, latar dan detail helai identik dengan crop berbeda.173 inlier,ratio0.966. Mempengaruhi eksperimen supplemental empat kelas dan tiga kelas yang berbagi split, bukan bukti leakage supplemental pada model baseline sebelum tambahan.
2. **Train–validasi**, `pair_001.jpg`: val `dataset/new_dataset/sangat keriting/download (1).jpg` vs train `dataset/new_dataset/sangat keriting/download (5).jpg`. Foto rambut/pola ikal/latar sama dengan crop/skala berbeda.61 inlier dari61 matches. Pasangan ini sudah ada dalam split dasar; pada eksperimen tiga kelas targetnya keriting.

## Interpretasi kandidat lain

Review pengguna atas58 pasangan tersedia di `USER-REVIEW.md`:2 duplikat dikonfirmasi (000/001),9 jelas berbeda,47 tidak otomatis duplikat. Tidak mengecualikan kandidat lain hanya berdasarkan sumber atau potensi orang sama. Identitas subjek tetap belum diketahui.

Pasangan dengan watermark JOHNNY RAMIREZ atau ANH CO TRAN memperlihatkan risiko domain/source overlap, tetapi watermark sama bukan bukti foto/subjek sama. Contoh `pair_010.jpg` (orang di latar laut vs foto studio) merupakan kecocokan geometris semu, bukan duplikat. Tidak menyatakan22 flag lain bersih secara identitas; hanya tidak dikonfirmasi foto identik.

## Tindakan yang belum dilakukan

Tidak memindahkan/menghapus gambar, tidak mengubah split atau model, tidak retrain. Jangan mengurangi skor sekadar satu/dua prediksi untuk memperkirakan skor bersih: bobot model sudah terpengaruh training dan pemilihan checkpoint.

Langkah koreksi yang disarankan: simpan manifest lama; kelompokkan foto sumber terkait; buat manifest bersih yang mengecualikan salinan train dari dua pasangan (setelah memeriksa seluruh komponen duplikat), lalu latih dari inisialisasi ImageNet baru dengan konfigurasi tetap. Split sumber/subjek yang lebih menyeluruh serta test eksternal baru tetap diperlukan untuk evaluasi independen. Test lama sudah digunakan berulang.

## Batas audit

Retrieval heuristik bukan pencocokan fitur lokal exhaustif semua pasangan. SIFT bukan flip invariant. Crop/rotasi/edit lain atau foto berbeda dari orang sama dapat lolos. Tidak tersedia subject-ID/URL sumber yang dapat dipercaya; tidak dapat menjamin seluruh leakage ditemukan.
