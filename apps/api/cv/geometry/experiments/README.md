# Arsip eksperimen supplemental — 14 November 2026

Ringkasan dan laporan numerik dipertahankan di Git. Gambar, bobot model,
preview review, serta snapshot manifest berisi path lokal tidak disertakan
dalam commit dokumentasi ini. Referensi ke artefak tersebut di laporan adalah
jejak eksekusi lokal, bukan jaminan file tersedia setelah clone.

## Urutan hasil

1. `partner-20261114-seed42`: eksperimen supplemental empat kelas.
2. `partner-20261114-threeclass-seed42`: eksperimen tiga kelas awal;
   **terpengaruh dua near-duplicate lintas split yang kemudian dikonfirmasi**.
   Temuan dan keputusan pengguna ada di `leakage-audit-v1/FINDINGS.md`
   dan `USER-REVIEW.md`.
3. `partner-20261114-threeclass-corrected-seed42`: training baru dari ImageNet
   setelah dua salinan training dikecualikan; 536 train / 57 val / 59 test.
   Test 57/59, Macro-F1 0.9639. Lihat `RESULTS.md`,
   `reports/hair_type_eval.json`, dan `verification.json`.

Pernyataan "belum retraining" pada catatan review awal adalah status historis
saat catatan ditulis, bukan status akhir. Pengguna sudah meninjau 58 pasangan;
jangan meminta anotasi ulang. Dua duplikat dikecualikan dari training,
sembilan pasangan jelas berbeda, dan 47 pasangan dipertahankan tanpa
mengklaim identitas subjek/sesi independen.

## Batas penggunaan

- Model kandidat tidak dipromosikan; kontrak aktif tetap empat kelas.
- Perbaikan dua duplikat bukan bukti seluruh dataset bebas leakage subjek/sesi.
- Test lama sudah digunakan berulang; test eksternal baru tetap dianjurkan.
- Skrip persiapan supplemental mencatat persetujuan koleksi khusus eksperimen
  ini (269 gambar dan daftar pengecualian); bukan importer dataset umum.
- Skrip audit melakukan penyaringan heuristik, bukan penetapan identitas orang.
- Reproduksi training memerlukan dataset lokal, manifest snapshot, dependensi
  CV, bobot pretrained, serta GPU CUDA untuk wrapper eksperimen tiga kelas.
