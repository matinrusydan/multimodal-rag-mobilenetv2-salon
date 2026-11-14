# Eksperimen tiga kelas — 14 November 2026

> **Koreksi setelah audit leakage:** dua pasangan foto sumber sama dikonfirmasi visual lintas train–test dan train–validasi. Angka di bawah tetap hasil historis, **bukan evaluasi bebas near-duplicate leakage**. Lihat `leakage-audit-v1/FINDINGS.md`. Belum ada retraining/split correction.

Eksperimen terpisah atas permintaan user: `sangat-keriting` dipetakan ke `keriting`. Kelas output: lurus, bergelombang, keriting. Tidak mengubah label sumber, model aktif atau kontrak API/UI empat kelas.

## Konfigurasi

EfficientNetV2-S pretrained ImageNet, seed42, batch8, LR0.0003, inverse-frequency class weights, maksimum35 epoch, patience10. Early stopping epoch28; checkpoint terbaik epoch18 berdasarkan validation Macro-F1. Sumber sama dengan eksperimen supplemental empat kelas: 538 train / 57 val / 59 test. Seluruh path gambar, SHA256 dan keanggotaan split dipertahankan; hanya label target yang dipetakan.

| Metrik | Validasi | Test |
|---|---:|---:|
| Accuracy | 0.9825 (56/57) | 0.9661 (57/59) |
| Macro-F1 | 0.9810 | 0.9651 |
| ECE | 0.0665 | 0.0213 |

Test precision/recall/F1: lurus 1.0000/0.9474/0.9730 (19), bergelombang 0.9444/0.9444/0.9444 (18), keriting 0.9565/1.0000/0.9778 (22).

Confusion matrix test (baris aktual, kolom prediksi; urutan lurus/bergelombang/keriting): `[[18,1,0],[0,17,1],[0,0,22]]`.

## Perbandingan pada kategori sama

Prediksi argmax model supplemental empat kelas sebelumnya dan targetnya dipetakan ke tiga kategori. Hasil mapped test: 55/59 benar (0.9322), Macro-F1 0.9285; mapped validation Macro-F1 0.9438. Model yang benar-benar dilatih tiga kelas mencapai 57/59 dan Macro-F1 0.9651. Ini pemetaan argmax, bukan inferensi alternatif dengan menjumlahkan probabilitas kedua kelas keriting. Detail `fourclass_mapped_comparison.json`.

## Verifikasi dan batas

- Sembilan unit test hair-type lulus termasuk evaluasi tiga kelas tanpa mengubah konstanta kanonikal empat kelas.
- ONNX checker dan parity PyTorch/ONNX batch1/2 lulus (maks galat logit 1.91e-6); output masing-masing batch x3. Detail verification.json.
- Lima file model aktif SHA256 tidak berubah. ONNX kandidat berukuran76.841MB; benchmark CPU lokal33.90ms (bukan perbandingan latensi terkontrol).
- Hasil satu seed dan test kecil yang sudah berulang dibuka; tidak membuktikan signifikansi/generalitas. Penggabungan kelas mengubah tugas; angka mentah tiga/empat kelas tidak langsung sebanding. Independensi subjek dan hak sumber belum dibuktikan. Model belum dipromosikan; pipeline empat kelas tidak otomatis kompatibel dengan output tiga kelas.
