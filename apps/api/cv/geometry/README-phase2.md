# Fase 2 — Segmentasi Rambut (UNet)

Fase 2 mengimplementasikan model segmentasi rambut berbasis arsitektur **UNet** untuk menghasilkan hair mask biner (rambut vs latar) beresolusi 256×256 secara presisi, ringan, dan mandiri tanpa ketergantungan model deteksi pose.

## Arsitektur & Pipeline

```
Citra Input (RGB) -> Resize (256x256) -> ImageNet Normalization
   ↓
MobileNetV2-UNet (encoder pretrained ImageNet + Skip Connections + Bilinear Upsample)
   ↓
Logits (1, H, W) -> Sigmoid -> Threshold 0.5 -> Binary Hair Mask
   ↓
Resize kembali ke resolusi asli -> Mask biner (0 / 255) + Hair Coverage Ratio
```

- **Loss function**: `L = 0.5 * BCEWithLogits + 0.5 * SoftDice`
- **Data Ground-Truth**: 251 pasang citra & mask biner ground-truth Figaro-1k (`data/figaro1k_gt/*.png`) yang diekstrak langsung dari arsip kanonikal `Figaro-1k.zip` menggunakan HTTP Range request.
- **Split**: Mengikuti partisi terstrata deterministik Fase 1 setelah review duplikat (`curated_manifest.json`, `seed=42`). Identitas subjek belum diverifikasi; deduplikasi citra tidak membuktikan split bebas kebocoran antar-subjek:

  - Train: 177 citra
  - Val: 37 citra
  - Test: 37 citra

## Berkas & Modul

| Berkas | Deskripsi |
|---|---|
| `unet_model.py` | Definisi arsitektur PyTorch `MobileNetV2UNet`, `ResNet34UNet`, `HairUNet` (scratch), builder `build_hair_segmentation_model`, dan `BCEDiceLoss`. |
| `extract_figaro_masks.py` | CLI & helper ekstraksi/verifikasi 251 mask PBM kanonikal Figaro-1k via HTTP Range request ke binary PNG. Mendukung `--verify-only`. |
| `train_segmentation.py` | Skrip training, evaluasi val/test, early stopping, export ONNX, benchmark latensi CPU, dan pencatatan gate. |
| `segment_infer.py` | CLI & class `HairSegmenter` untuk inferensi mandiri memakai `hair_segmentation.onnx` pada citra sembarang. |
| `test_extract_figaro_masks.py` | Unit test parser central directory ZIP, konversi PBM, dan verifikasi coverage mask. |
| `test_segmentation_helpers.py` | Unit test preprocessing NCHW, sigmoid, penyimpanan overlay, dan forward/loss UNet (MobileNetV2, ResNet34, scratch). |

## Menjalankan

Dari root repositori:

```powershell
# 1. Verifikasi integritas 251 mask ground truth
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/extract_figaro_masks.py --verify-only

# 2. Training MobileNetV2-UNet (wajib CUDA; gagal jika GPU tidak tersedia)
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/train_segmentation.py --arch mobilenet_v2 --epochs 45 --batch-size 16 --device cuda
# Alternatif arsitektur: --arch resnet34 atau --arch scratch
# Encoder ImageNet diunduh saat pertama dipakai; --no-pretrained menonaktifkannya.

# 3. Inferensi citra tunggal via ONNX
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/segment_infer.py `
  --image apps/api/cv/dataset/figaro1k/lurus/00010.jpg `
  --mask-out apps/api/cv/geometry/reports/figures/test_mask.png `
  --overlay-out apps/api/cv/geometry/reports/figures/test_overlay.jpg
```

## Kriteria Gate Fase 2

| Metrik | Target Gate |
|---|---|
| Validation Mean IoU | $\ge 0.75$ |
| Validation Mean Dice ($F_1$) | $\ge 0.85$ |
| CPU Inference Latency (256×256) | $< 200$ ms |

## Hasil aktual — 10 November 2026

**Gate numerik LULUS** pada split eksperimen ini (`reports/segmentation_eval.json`). Model MobileNetV2-UNet pretrained ImageNet, 6.626.481 parameter, dilatih di RTX 3050 Laptop GPU dengan seed 42, batch 16. Early stopping pada epoch 24; checkpoint terbaik dipilih hanya dari IoU validasi pada epoch 12. Durasi training 164,6 detik.

| Metrik | Validasi (37 citra) | Test (37 citra) |
|---|---:|---:|
| Mean IoU per citra | 0.9305 | 0.9441 |
| Mean Dice per citra | 0.9635 | 0.9711 |

- ONNX: `weights/hair_segmentation.onnx`, 25,249 MiB; input 256×256, batch dinamis.
- Benchmark ONNX CPU (20 run setelah 3 warmup): mean **28,79 ms**, p95 **34,25 ms**. Ini latensi model, bukan keseluruhan layanan.
- Smoke CLI pada `figaro1k/lurus/00010.jpg`: output mask dan overlay 428×571, coverage 0,4921; latensi preprocessing/inferensi/postprocessing 36,24 ms. Smoke ini bukan evaluasi independen.
- Tes geometry: **30 lulus, tanpa skip**; tes API: **86 lulus**.
- Inspeksi enam contoh `reports/figures/segmentation_test_grid.jpg`: siluet utama tertangkap; celah antarhelai cenderung terisi dan ujung rambut lebih halus dibanding GT. Inspeksi ini bukan validasi seluruh test.

### Batasan dan kelanjutan

- Identitas subjek belum diverifikasi. Split terstrata setelah review duplikat tidak membuktikan independensi subjek/sumber.
- Test hanya berisi lurus (14), bergelombang (13), dan keriting (10); tidak ada sangat-keriting. Belum ada evaluasi segmentasi pada `new_dataset` karena mask GT tidak tersedia.
- Hasil ini tidak membuktikan generalisasi pada foto pelanggan, akurasi panjang/volume, atau kesiapan deployment.
- Tidak melakukan tuning lanjutan berdasarkan hasil test yang sudah dibuka.
- Gate Fase 0 untuk geometri pose tetap belum terbukti lulus. Kelulusan segmentasi tidak mengizinkan klaim geometri pose tervalidasi.

