# Hasil training tiga kelas setelah koreksi dua duplikat

## Konfigurasi dan status

Training selesai; tidak deployment. EfficientNetV2-S dari ImageNet, seed42, batch8, LR0.0003, weighted loss, maksimum35epoch/patience10. Best epoch16, early stop26, durasi training695.23detik. Train536/val57/test59; dua salinan train duplikat diketahui dikecualikan. Keanggotaan/label evaluasi lama dipertahankan; file sumber tidak dihapus.

| Metrik | Sebelum koreksi (historis, terkontaminasi) | Setelah koreksi dua duplikat |
|---|---:|---:|
| Validation accuracy | 98.25% (56/57) | 96.49% (55/57) |
| Validation Macro-F1 | 0.9810 | 0.9616 |
| Validation ECE | 0.0665 | 0.0359 |
| Test accuracy | 96.61% (57/59) | 96.61% (57/59) |
| Test Macro-F1 | 0.9651 | 0.9639 |
| Test ECE | 0.0213 | 0.0292 |

Test F1: lurus0.9444 (19), bergelombang0.9474 (18), keriting1.0000 (22). Test confusion matrix (baris aktual, kolom prediksi; lurus/bergelombang/keriting): `[[17,2,0],[0,18,0],[0,0,22]]`. Kedua kesalahan: lurus diprediksi bergelombang. Validasi: dua bergelombang diprediksi lurus.

## Verifikasi

ONNX checker passed; parity PyTorch/ONNX batch1/2 passed (maks galat absolut4.77e-6), output batchx3. Seluruh652hash sumber diverifikasi; split evaluasi/label sama dengan eksperimen lama. Lima file model aktif SHA256 tidak berubah. Lihat verification.json. ONNX76.841MB; benchmark CPU lokal40.87ms (latensi bukan perbandingan terkontrol).

## Kesimpulan dan batas

Model tetap mencapai57/59 setelah dua salinan train yang bocor dikecualikan dan training dimulai ulang, tetapi itu tidak membuktikan leakage sebelumnya tidak berpengaruh. Pola kesalahan dan Macro-F1 berbeda. Ini satu seed dengan test kecil yang berulang digunakan, bukan test eksternal independen. Potensi subjek/sesi/sumber sama belum dipastikan; hanya dua near-duplicate yang diketahui diperbaiki. Tidak menyebut seluruh dataset bebas leakage. Model tetap kandidat tiga kelas, kontrak runtime aktif empat kelas belum diubah.

## Langkah berikutnya

Pertahankan konfigurasi; evaluasi pada test eksternal baru yang tidak dipakai tuning. Jika user ingin memakai kandidat ini pada aplikasi, minta persetujuan perubahan kontrak tiga kelas dan verifikasi integrasi terpisah sebelum deployment. Tidak meminta ulang58anotasi pengguna yang sudah selesai.
