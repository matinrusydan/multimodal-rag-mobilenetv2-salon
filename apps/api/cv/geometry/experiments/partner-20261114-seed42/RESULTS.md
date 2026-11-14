# Hasil retraining supplemental — 14 November 2026

- EfficientNetV2-S pretrained ImageNet; seed 42, batch 8, LR 0.0003, inverse-frequency loss; early stopping epoch 22, checkpoint terbaik epoch 12 berdasarkan Macro-F1 validasi.
- Dataset: 385 citra lama + 269 tambahan. Train 538, validasi 57, test 59. Validasi/test lama dipertahankan tanpa perubahan label atau SHA-256. Tambahan hanya masuk train.
- 35 koreksi label folder dikonfirmasi user. Satu accepted tanpa file (`e4e25a184c1b43f38f49fd1a78f3583e`) dikecualikan dengan persetujuan user. Snapshot tidak mengubah collector atau partner_dataset lama.

| Metrik | Sebelumnya | Eksperimen baru |
|---|---:|---:|
| Validation Macro-F1 | 0.9857 | 0.9553 |
| Test accuracy | 0.8814 (52/59) | 0.8983 (53/59) |
| Test Macro-F1 | 0.8740 | 0.8948 |
| Test ECE (lebih rendah lebih baik) | 0.0654 | 0.0916 |

Test F1 per kelas: lurus 0.9189; bergelombang 0.8889; keriting 0.8966; sangat-keriting 0.8750.

## Verifikasi

- Delapan unit test hair-type lulus, termasuk regresi dependensi torch pada ekspor.
- ONNX checker lulus; logits ONNX cocok dengan PyTorch pada batch 1 dan 2 (maks selisih absolut < 1e-6).
- Lima file model aktif tetap identik SHA-256 dengan sebelum eksperimen. Tidak deployment otomatis.
- Ekspor sempat gagal karena import torch hilang, lalu laporan gagal karena path relatif; keduanya diperbaiki. Evaluasi/ekspor dipulihkan dari checkpoint, tanpa retrain. Riwayat epoch direkonstruksi dari log dengan presisi tampilan; durasi training tidak tersedia, bukan nol.

## Batas dan keputusan

Kenaikan test hanya satu prediksi benar, bukan bukti signifikansi statistik. Batch berbeda dari baseline (8 vs 16), sehingga perubahan bukan ablation murni dataset. Test pernah dievaluasi sebelumnya, bukan test independen baru. Hash tidak menjamin independensi subjek/crop/flip; hak sumber tidak diverifikasi. Validasi turun dan ECE test memburuk. Model baru disimpan sebagai kandidat, model aktif dipertahankan.
