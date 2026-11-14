# Hasil review pengguna atas 58 pasangan audit

Sumber: review eksplisit pengguna dalam percakapan setelah audit. Nomor mengacu pada `pair_NNN.jpg` dalam folder ini, bukan semua pasangan dalam pairs.json.

## Duplikat dikonfirmasi pengguna — 2 pasangan

- `pair_000.jpg`: foto/pose dan orang sama; pasangan train–test.
- `pair_001.jpg`: foto/pose dan orang sama; pasangan train–validasi.

Kedua pasangan ini menjadi dasar usulan mengecualikan **salinan training** pada manifest eksperimen baru, bukan menghapus file sumber.

## Jelas berbeda menurut pengguna — 9 pasangan

`pair_010.jpg`, `pair_040.jpg`, `pair_046.jpg`, `pair_047.jpg`, `pair_048.jpg`, `pair_049.jpg`, `pair_054.jpg`, `pair_055.jpg`, `pair_057.jpg`.

## Tidak otomatis duplikat — 47 pasangan

- `pair_002.jpg`: sumber sama; mungkin orang sama, tetapi bukan bukti duplikat.
- `pair_003.jpg`–`pair_009.jpg`, `pair_011.jpg`–`pair_039.jpg`, `pair_041.jpg`–`pair_045.jpg`, `pair_050.jpg`–`pair_053.jpg`, `pair_056.jpg`: sumber sama dan mungkin orang sama, tetapi gaya/detail rambut dapat berbeda. Tidak diputuskan sebagai duplikat.

Kategori ini **bukan konfirmasi identitas berbeda**, dan bukan bukti subjek independen. Pertahankan gambar; jangan mengecualikan hanya karena watermark, latar atau kemungkinan orang sama.

## Status tindakan

58 pasangan terklasifikasi:2 duplikat +9 jelas berbeda +47 tidak otomatis duplikat. Hanya dokumentasi review ditambahkan. Dataset, manifest split, file sumber dan model tidak diubah; retraining koreksi belum dijalankan.
