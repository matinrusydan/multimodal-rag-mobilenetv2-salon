# Fase 4 — Klasifikasi Jenis Rambut & Pipeline Inferensi Hirarkis

Dokumen implementasi dan evaluasi Fase 4 roadmap CV: pelatihan & validasi pengklasifikasi Stage 1 **Hair Type** (4 kelas kanonikal), seleksi arsitektur berbasis *validation Macro-F1*, evaluasi jujur pada *locked test split*, ekspor ONNX, dan orkestrasi inferensi hirarkis terisolasi di `apps/api/cv/geometry/`.

---

## 1. Arsitektur & Prinsip

### 1.1 Skema Klasifikasi Hirarkis
Mengikuti arsitektur roadmap section 10.1:
```
Foto Input (RGB)
   ↓
[Stage 1: Hair Type Classifier (CNN)]
   ├── lurus / bergelombang → target atribut: length
   ├── keriting             → target atribut: length + volume
   └── sangat-keriting      → target atribut: volume saja
   ↓
[Stage 2: Segmentasi Rambut (UNet ONNX) + Fitur Siluet]
   ├── Hair mask biner 256×256 → hair coverage ratio
   ├── Fitur bentuk siluet (circularity, solidity, bbox, border contact)
   ├── Deteksi ikatan rambut → berstatus "uncalibrated" (tied: null)
   └── Pose-dependent geometry → berstatus "blocked_phase0_gate" (Phase 0 belum lulus)
```

### 1.2 Prinsip Anti-Leakage & Evaluasi Jujur
- Seluruh model dilatih hanya pada 269 citra training split (`curated_manifest.json`, split == "train").
- Pemilihan arsitektur (MobileNetV2 vs EfficientNetV2-S) dilakukan **hanya berdasarkan validation Macro-F1** pada 57 citra validasi, tanpa pernah mengintip atau menyetel hyperparameter pada *locked test split*.
- Evaluasi pada 59 citra *locked test split* dilakukan sekali saja pada model pemenang untuk menghasilkan metrik uji objektif (Accuracy, Macro-F1, per-class F1, Confusion Matrix, ECE).
- Kode dan bobot diisolasi di `apps/api/cv/geometry/` tanpa mengubah arsip warisan `scripts/`, `dataset/`, atau `weights/`.

---

## 2. Pemilihan Arsitektur pada Validation Split (57 Citra)

Dua arsitektur pretrained ImageNet dievaluasi dengan *inverse-frequency class weighting* untuk mengatasi ketidakseimbangan kelas (*sangat-keriting*: 33/269 pada train):

| Metrik | MobileNetV2 | EfficientNetV2-S (Pemenang) | Selisih |
|---|---:|---:|---:|
| **Validation Accuracy** | 0.9649 (55/57) | **0.9825** (56/57) | +0.0176 |
| **Validation Macro-F1** | 0.9714 | **0.9857** | +0.0143 |
| **Validation Weighted-F1** | 0.9649 | **0.9825** | +0.0176 |
| **Validation ECE (Kalibrasi)** | 0.0968 | **0.0540** | -0.0428 (lebih terkalibrasi) |
| **Validation Loss** | 0.1864 | **0.0856** | -0.1008 |
| **Val Figaro-1k Acc / mF1** | 0.9730 / 0.9788 | **0.9730 / 0.9791** | +0.0003 |
| **Val New-Dataset Acc / mF1** | 0.9500 / 0.9530 | **1.0000 / 1.0000** | +0.0470 |
| **Jumlah Parameter** | 2.228.996 (2.2M) | 20.182.612 (20.2M) | — |
| **Ukuran Model ONNX** | 8.48 MB | 76.85 MB | — |
| **Latensi CPU Rata-rata** | 3.51 ms | 26.40 ms | (budget roadmap <500 ms) |

**Keputusan:** `efficientnet_v2_s` dipilih sebagai juara Stage 1 Hair Type karena mengungguli MobileNetV2 pada seluruh metrik klasifikasi dan kalibrasi probabilitas (ECE), konsisten dengan temuan benchmark roadmap section 14, dengan latensi CPU 26.40 ms yang sangat efisien.

---

## 3. Hasil Evaluasi Locked Test Split (59 Citra)

Evaluasi akhir pada *locked test split* (tanpa tuning) tersimpan di `reports/hair_type_eval.json`:

- **Test Accuracy**: **0.8814** (52 dari 59 citra benar)
- **Test Macro-F1**: **0.8740**
- **Test Weighted-F1**: **0.8829**
- **Test ECE**: **0.0654**
- **Loss**: 0.25371

### 3.1 Performa per Kelas pada Test Split

| Kelas | Precision | Recall | F1-Score | Support |
|---|---:|---:|---:|---:|
| `lurus` | 0.9412 | 0.8421 | 0.8889 | 19 |
| `bergelombang` | 0.8500 | 0.9444 | 0.8947 | 18 |
| `keriting` | 1.0000 | 0.8000 | 0.8889 | 15 |
| `sangat-keriting` | 0.7000 | 1.0000 | 0.8235 | 7 |

### 3.2 Confusion Matrix (Test Split)

```
                Predicted Label
True Label      lurus  bergelombang  keriting  sangat-keriting
lurus             16        3           0             0
bergelombang       1       17           0             0
keriting           0        0          12             3
sangat-keriting    0        0           0             7
```

**Analisis Error:**
1. Seluruh 7 citra *sangat-keriting* terprediksi benar (recall 100%).
2. Kesalahan klasifikasi hanya terjadi pada batas transisi kelas tetangga:
   - 3 citra *lurus* diprediksi *bergelombang* (ujung rambut sedikit bertekstur).
   - 1 citra *bergelombang* diprediksi *lurus*.
   - 3 citra *keriting* diprediksi *sangat-keriting* (pola spiral sangat rapat).
3. Tidak ada kesalahan silang ekstrem (misalnya *lurus* terprediksi *keriting* atau *sangat-keriting*).
4. Heatmap tersimpan di `reports/figures/hair_type_efficientnet_v2_s_test_confusion.png`.

### 3.3 Evaluasi per Subkelompok (Cohort)

| Cohort | Jumlah Citra | Test Accuracy | Test Macro-F1 | Catatan |
|---|---:|---:|---:|---|
| `new_dataset` | 22 | **0.9545** (21/22) | **0.9556** | Generalisasi sangat tinggi pada foto kontemporer |
| `figaro1k` | 37 | **0.8378** (31/37) | **0.6480** | Pada test split Figaro-1k, kelas *sangat-keriting* memiliki 0 support, sehingga rata-rata Macro-F1 4 kelas tertekan oleh F1=0 pada kelas tersebut |

---

## 4. Status Gate Fase 4

Berdasarkan kriteria gate roadmap section 10.5:
- **Kriteria Primer Hair Type Accuracy $\ge 0.85$**: **LULUS**
  - Aktual Validation Accuracy: **0.9825** ($\ge 0.85$)
  - Aktual Locked Test Accuracy: **0.8814** ($\ge 0.85$)
  - Aktual Validation Macro-F1: **0.9857**
  - Aktual Locked Test Macro-F1: **0.8740**

---

## 5. Pipeline Hirarkis & CLI (`classify_hierarchical.py`)

Modul `classify_hierarchical.py` menggabungkan model ONNX Stage 1 (`hair_type.onnx`) dan Stage 2 (`hair_segmentation.onnx`) dalam satu antarmuka inferensi terpadu.

### 5.1 Perilaku Dispatch & Penanganan Geometri
- **Deteksi Ikatan Rambut**: Menghasilkan fitur bentuk siluet objektif (`circularity`, `solidity`, `component_count`, `border_contact`, `waist_constriction_ratio`). Status keputusan terkalibrasi (`calibrated`) mengidentifikasi gaya rambut terurai (`loose`), kuncir kuda (`ponytail`), atau cepol (`bun`) dengan perlindungan tekstur rambut kribo.
- **Atribut Kondisional**:
  - `lurus` / `bergelombang`: `target_attributes = ["length"]`
  - `keriting`: `target_attributes = ["length", "volume"]`
  - `sangat-keriting`: `target_attributes = ["volume"]`
- **Estimasi Panjang & Volume Geometris (Unblocked via Dual-Mode)**:
  - Menggabungkan mode pose-guided (jika landmark bahu MediaPipe tersedia) dan pose-free silhouette (berdasarkan acuan kranial dan kanon antropometrik head-unit Domljan 2024 / Burton 2013).
  - Mode legacy tanpa estimasi geometris tetap dapat diaktifkan menggunakan flag `--no-geometry`.
  ```json
  "stage2_conditional_attributes": {
    "target_attributes": ["length"],
    "length": {
      "required": true,
      "status": "ok",
      "predicted_class": "panjang",
      "confidence": 0.8983,
      "relative_shoulder_ratio": 1.9538,
      "head_units": 2.5236,
      "method": "pose_free_silhouette"
    },
    "volume": {
      "required": false,
      "status": "not_required",
      "value": null
    }
  }
  ```

### 5.2 Penggunaan CLI

```powershell
# 1. Menampilkan bantuan CLI
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/classify_hierarchical.py --help

# 2. Inferensi citra tunggal dengan luaran JSON
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/classify_hierarchical.py `
  --image apps/api/cv/dataset/figaro1k/lurus/00001.jpg --json

# 3. Inferensi sekaligus menyimpan mask biner & visualisasi overlay di geometry/
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/classify_hierarchical.py `
  --image apps/api/cv/dataset/figaro1k/keriting/00319.jpg `
  --mask-out apps/api/cv/geometry/reports/figures/demo_mask.png `
  --overlay-out apps/api/cv/geometry/reports/figures/demo_overlay.jpg
```

---

## 6. Berkas & Artefak yang Dihasilkan

| Berkas | Ukuran | Deskripsi |
|---|---|---|
| `hair_type_model.py` | 2.5 KB | Builder PyTorch untuk MobileNetV2 dan EfficientNetV2-S serta eksportir ONNX |
| `train_hair_type.py` | 19.5 KB | Pipeline pelatihan Stage 1, evaluasi val/test, kalkulasi ECE, dan benchmark ONNX |
| `measure_length.py` | 8.8 KB | Estimasi panjang rambut geometris berbasis rasio bahu & head-unit |
| `measure_volume.py` | 4.8 KB | Estimasi ketebalan/volume rambut geometris ternormalisasi |
| `detect_tied_hair.py` | 6.8 KB | Ekstraksi geometri siluet dan deteksi ikatan rambut terkalibrasi |
| `classify_hierarchical.py` | 9.2 KB | Pipeline inferensi hirarkis terpadu (type + seg + geometry) & CLI |
| `test_hair_type.py` | 4.1 KB | Unit test model, loss inverse frequency, dan loader dataset anti-leakage |
| `test_classify_hierarchical.py` | 4.6 KB | Unit test logika dispatch atribut, softmax, dan inferensi terpadu |
| `test_geometry_estimation.py` | 4.7 KB | Unit test estimasi panjang, volume, dan deteksi ikatan rambut |
| `weights/hair_type.onnx` | 76.8 MB | Model ONNX champion (`efficientnet_v2_s`) untuk inferensi produksi CPU |
| `weights/hair_type_efficientnet_v2_s_best.pt` | 80.8 MB | Checkpoint PyTorch champion |
| `reports/hair_type_eval.json` | 9.8 KB | Laporan lengkap pelatihan, metrik validasi, metrik locked test, dan ECE |
| `reports/val_efficientnet_v2_s.json` | 8.2 KB | Laporan validasi arsitektur EfficientNetV2-S |
| `reports/val_mobilenet_v2.json` | 3.5 KB | Laporan validasi arsitektur MobileNetV2 |
| `reports/figures/hair_type_efficientnet_v2_s_test_confusion.png` | 41.5 KB | Visualisasi confusion matrix pada locked test split |

---

## 7. Status Pengujian Unit

Seluruh **62 test suite** di `apps/api/cv/geometry/` lulus:
```powershell
apps/api/cv/.venv/Scripts/python.exe -m unittest discover -s apps/api/cv/geometry -p "test_*.py"
# Ran 62 tests in ~1.7s (OK)
```
Mencakup pengujian integritas kurasi data, ekstraksi mask Figaro, segmentasi UNet, threshold biner & padding morfologi, deteksi bentuk siluet, model klasifikasi jenis rambut, dan pipeline inferensi hirarkis.
