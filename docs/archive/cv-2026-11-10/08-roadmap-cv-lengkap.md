# 08 — Roadmap Lengkap Computer Vision (Fase 0 → Selesai)

> **Dokumen induk** untuk seluruh pekerjaan Computer Vision (CV) proyek RAG-salon, dari awal hingga selesai.
>
> Fokus: klasifikasi **hair type** & **hair length/volume** dari foto **back-view** berbasis segmentasi + geometri proporsi tubuh.
>
> **Status:** MASTER PLAN — eksekusi bertahap.
> **Prasyarat:** [06-kajian-matematis-referensi.md](./06-kajian-matematis-referensi.md) · [07-fase0-verifikasi-gate.md](./07-fase0-verifikasi-gate.md)

---

## ⚡ STATUS EKSEKUSI (diperbarui)

| Item | Status | Temuan |
|---|---|---|
| **Fase 0** (gate MediaPipe back-view) | ⚠️ **KONDISIONAL — selesai dianalisis** | Pose terdeteksi 64% (back). Di antara yang terdeteksi, shoulder **96%** & head **100%** OK → masalah = pose detection rate, bukan pemilihan landmark. 16/44 `no_pose`. Model heavy tidak membantu (0.568 < 0.614). |
| **TAHAP 1 (cleaning dataset)** | ✅ **Diimplementasikan** | 3 script: `viewpoint_gate.py` (prediksi paksa pilih 4 kelas), `verify_viewpoint.py` (verifikasi manusia/model pengukuran, koreksi opsional), `analyze_viewpoint_accuracy.py` (ukur akurasi as-is + confusion). Temuan: MediaPipe **berhalusinasi** visibility hidung di foto belakang → sinyal diganti geometris + Face Landmarker. Prediksi Figaro: depan 338 / samping 119 / belakang 143 (belum diverifikasi manusia). |
| **Deployment runtime** | ✅ Sudah ConvNeXt-Tiny | `apps/ai/cv/weights/hair_length.onnx` = `hair_length_final.onnx` (md5 identik), ConvNeXt-Tiny 111MB. Metadata label sempat salah (`mobilenet_v2`) — **sudah diperbaiki**. |
| **Backbone benchmark v2** | ✅ Selesai (15 backbone) | Juara awal: `efficientnet_v2_s` (84.18%). |
| **Validasi backbone 3-seed** | ✅ Selesai | `efficientnet_v2_s` (0.8293±0.0086) > `convnext_tiny` (0.8177±0.0163). Menang + stabil + lebih kecil. |
| **Fase 1–5** | ❌ Belum dieksekusi | — |

**Keputusan backbone final:** `efficientnet_v2_s` (lihat `geometry/reports/backbone_decision.json`).
**Keputusan Fase 0:** KONDISIONAL → wajib lanjut **Fase 1 data cleaning** (buang `no_pose`), lalu gate diharapkan lulus (conditional 96–100%). Lihat `geometry/reports/phase0_decision.json`.

---

## Daftar Isi

1. [Visi & Target Akhir](#1-visi--target-akhir)
2. [Arsitektur Konseptual](#2-arsitektur-konseptual)
3. [Peta Fase & Timeline](#3-peta-fase--timeline)
4. [Struktur Folder](#4-struktur-folder)
5. [Prinsip Kerja Wajib](#5-prinsip-kerja-wajib)
6. [FASE 0 — Verifikasi Gate](#6-fase-0--verifikasi-gate)
7. [FASE 1 — Data Cleaning & Viewpoint Filter](#7-fase-1--data-cleaning--viewpoint-filter)
8. [FASE 2 — Segmentasi Rambut (UNet)](#8-fase-2--segmentasi-rambut-unet)
9. [FASE 3 — Pipeline Geometris](#9-fase-3--pipeline-geometris)
10. [FASE 4 — Klasifikasi Hirarkis & Validasi](#10-fase-4--klasifikasi-hirarkis--validasi)
11. [FASE 5 — Integrasi, Dataset Baru & Publikasi](#11-fase-5--integrasi-dataset-baru--publikasi)
12. [Definition of Done Global](#12-definition-of-done-global)
13. [Risk Register Global](#13-risk-register-global)
14. [Referensi Silang](#14-referensi-silang)

---

## 1. Visi & Target Akhir

### 1.1 Masalah

Pemilik salon sering tidak responsif menjawab konsultasi pelanggan. Pelanggan ingin tahu **harga pasti** (berbasis panjang & jenis rambut) tanpa harus datang. Solusi: foto rambut (dari **belakang**) → sistem klasifikasi otomatis → rekomendasi + estimasi harga via RAG.

### 1.2 Target Output Sistem

```
INPUT: Foto rambut dari BELAKANG (user TIDAK memperlihatkan wajah)
   ↓
STAGE 0: Validasi input (viewpoint, kualitas)
   ↓
STAGE 1: HAIR TYPE (straight / wavy / curly / kinky)
   ↓
STAGE 2: Atribut kondisional
   ├── straight/wavy → PANJANG (pendek / sebahu / sepunggung / melebihi punggung)
   ├── curly         → PANJANG + SEGMENTASI KETEBALAN
   └── kinky         → KETEBALAN/VOLUME saja
```

### 1.3 Spesifikasi Kelas (final untuk proyek)

**Hair Type (4):** straight (lurus), wavy (bergelombang), curly (keriting), kinky (kribo)

**Hair Length** — acuan geometris berbasis **bahu sebagai center point**:
| Kelas | Definisi Geometris |
|---|---|
| pendek | ujung rambut tidak mencapai 50% jarak ujung-atas-kepala → bahu |
| sebahu | ujung rambut di sekitar garis bahu |
| sepunggung | ujung rambut mendekati titik punggung |
| melebihi punggung | ujung rambut melampaui titik punggung |

**Volume/Ketebalan (untuk curly/kinky):** tipis / sedang / tebal — berbasis rasio lebar silhouette vs lebar kepala.

### 1.4 Hasil Akhir yang Diharapkan

- Pipeline CV end-to-end yang dapat dipanggil dari `apps/ai` (brain engine)
- Model ONNX (hair type + segmentasi) ringan, inference < 500ms
- Dokumentasi ilmiah (paper SINTA + skripsi)
- Ground truth tervalidasi untuk evaluasi

---

## 2. Arsitektur Konseptual

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT: FOTO BACK-VIEW                     │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 0 — INPUT VALIDATION                                   │
│  • Viewpoint check (back / back_left / back_right)           │
│  • Kualitas (resolusi, blur)                                 │
│  • Deteksi ikatan rambut (gumpalan) → "foto ulang"           │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1 — HAIR TYPE CLASSIFIER (CNN)                         │
│  • efficientnet_v2_s / ConvNeXt-Tiny → straight/wavy/curly/kinky │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2 — SEGMENTASI + GEOMETRI                             │
│  • UNet → hair mask                                          │
│  • MediaPipe Pose → landmark bahu + kepala                   │
│  • Normalisasi head-unit → rasio geometris                   │
│                                                              │
│  straight/wavy → measure_length()   → 4 kelas panjang        │
│  curly        → measure_length() + measure_volume()          │
│  kinky        → measure_volume()    → 3 kelas ketebalan      │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ OUTPUT: hair_type + length/volume + confidence               │
│  → diteruskan ke RAG (konteks konsultasi + harga)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Peta Fase & Timeline

| Fase | Nama | Durasi | Gate → Lanjut? |
|---|---|---|---|
| **0** | Verifikasi Gate (MediaPipe back-view) | 3–5 hari | ✅ LULUS wajib |
| **1** | Data Cleaning & Viewpoint Filter | 1 minggu | ✅ data valid ≥ target |
| **2** | Segmentasi Rambut (UNet) | 1 minggu | ✅ IoU ≥ target |
| **3** | Pipeline Geometris | 1,5 minggu | ✅ fitur terbentuk |
| **4** | Klasifikasi Hirarkis & Validasi | 2 minggu | ✅ metrik ≥ target |
| **5** | Integrasi, Dataset Baru, Publikasi | 2 minggu | — |

**Total: ~12 minggu (3 bulan).**

---

## 4. Struktur Folder

Seluruh pekerjaan CV baru di folder **isolated** `apps/api/cv/geometry/` (tidak menyentuh `scripts/`, `dataset/`, `weights/` lama):

```
apps/api/cv/
├── annotation/              ← (sudah ada) anotasi & QC
├── scripts/                 ← (lama, JANGAN diubah)
├── dataset/                 ← (lama)
├── preprocessed*/           ← (lama)
├── weights/                 ← (lama)
│
└── geometry/                ← BARU (seluruh Fase 0–5)
    ├── README.md
    │
    ├── pose_feasibility.py          # Fase 0
    ├── filter_viewpoint.py          # Fase 1
    ├── train_segmentation.py        # Fase 2
    ├── segment_infer.py             # Fase 2
    ├── threshold_binary.py          # Fase 3
    ├── detect_tied_hair.py          # Fase 3
    ├── pose_landmarks.py            # Fase 3
    ├── measure_length.py            # Fase 3
    ├── measure_volume.py            # Fase 3
    ├── classify_hierarchical.py     # Fase 4
    ├── evaluate_cv.py               # Fase 4
    │
    ├── weights/                     # Fase 2 (hair_segmentation.onnx)
    └── reports/
        ├── pose_feasibility.json
        ├── viewpoint_filter.json
        ├── segmentation_eval.json
        ├── geometric_features.json
        ├── classification_eval.json
        └── figures/
```

---

## 5. Prinsip Kerja Wajib

| # | Prinsip |
|---|---|
| 1 | **Data integrity** — jangan hapus/overwrite dataset & label lama |
| 2 | **Ground-truth validity** — jangan pakai pseudo-label sebagai GT final |
| 3 | **Reproducibility** — seed tetap, script punya `--help` |
| 4 | **Leakage prevention** — split by group, cek near-duplicate |
| 5 | **Correct evaluation** — laporkan macro-F1, bukan hanya accuracy |
| 6 | **Isolasi** — semua CV baru di `geometry/` |
| 7 | **No absolute cm** — gunakan rasio relatif |
| 8 | **Negative results valid** — gate boleh gagal & tetap dilaporkan |

---

## 6. FASE 0 — Verifikasi Gate

> **Detail lengkap:** [07-fase0-verifikasi-gate.md](./07-fase0-verifikasi-gate.md)

**Tujuan:** membuktikan MediaPipe Pose dapat mendeteksi landmark **bahu** pada foto back-view.

**Aktivitas:**
1. Buat `geometry/pose_feasibility.py`
2. Uji pada ≥60 foto (30 back + 15 front + 15 side)
3. Ukur detection rate bahu & kepala, stabilitas rasio head:shoulder
4. Cross-check manusia (Spearman ρ) pada 20 gambar

**Gate:** shoulder detection rate (back) **≥ 70%** DAN head **≥ 80%**.

**Jika LULUS** → Fase 1. **Jika KONDISIONAL** → uji pivot (P1–P3). **Jika PIVOT** → ganti acuan/dataset (P4–P5).

**Output:** `geometry/reports/pose_feasibility.json` + visualisasi.

### Hasil Aktual (selesai dieksekusi)

| Metrik | Nilai (back-view) |
|---|---|
| Pose terdeteksi | **64%** (28/44) |
| Shoulder OK | 61% (27/44) |
| Head OK | 64% (28/44) |
| **Conditional (pose terdeteksi)** | **shoulder 96%, head 100%** |

**Keputusan: KONDISIONAL.** Akar masalah = **pose detection rate** (16 `no_pose`), BUKAN pemilihan landmark. Ketika pose terdeteksi, MediaPipe andal (96–100%).
**Pivot yang diuji:** P1 (model heavy) **gagal** (0.568 < 0.614); P4 (acuan kepala) tidak menyelesaikan karena `no_pose` juga menghilangkan kepala.
**Rekomendasi:** lanjut **Fase 1 data cleaning** (buang citra `no_pose`), lalu gate diharapkan lulus. Detail: `geometry/reports/phase0_decision.json`.

---

## 7. FASE 1 — Data Cleaning & Viewpoint Filter

**Tujuan:** memastikan dataset training hanya berisi foto back-view valid.

> **STATUS: TAHAP 1 DIIMPLEMENTASIKAN** (fokus: hapus foto depan/samping).
> Lihat `apps/api/cv/geometry/README.md` untuk cara jalan.

### 7.0 Alur Tahap 1 (implementasi aktual)

```
Dataset kotor
    ↓
[1] Model gate prediksi viewpoint (paksa pilih 4 kelas: depan/samping/belakang/belakang_nyerong)
    → geometry/viewpoint_gate.py → reports/viewpoint_predictions.json
    ↓
[2] Verifikasi manusia (MODE PENGUKURAN, sampling cerdas, koreksi OPSIONAL)
    → geometry/verify_viewpoint.py → ground_truth/viewpoint_verification_<id>.json
    Anotator menjawab: "Benar? [Ya/Tidak/Ragu]"
    ↓
[3] Ukur akurasi model AS-IS (baseline jujur)
    → geometry/analyze_viewpoint_accuracy.py → reports/viewpoint_accuracy.json
    ↓
Dataset bersih + laporan: berapa % tebakan model SALAH (tanpa bantuan)
```

**Prinsip:** "Don't fix what you haven't measured." Ukur kemampuan model apa adanya dulu,
baru putuskan perlu koreksi atau tidak. Koreksi manusia = opsional.

**Sinyal gate (v2):** Face Landmarker (fitur wajah asli) + geometri pose relatif + BlazeFace.
Catatan kritis: MediaPipe Pose **berhalusinasi** visibility hidung tinggi di foto belakang
(nose_vis 0.86 padahal tidak terlihat) → sinyal visibility mentah diganti geometri posisi.

### 7.1 Aktivitas

1. **Manifest viewpoint** — kumpulkan label viewpoint dari anotasi yang ada
   - Sumber: `annotation/ground_truth/_archive_annotator_A_p240_v2.json` (kolom `viewpoint`)
2. **Verifikasi viewpoint** (bila perlu) — anotasi cepat Ya/Tidak/Ragu
3. **`geometry/filter_viewpoint.py`** — filter hanya `back`, `back_left`, `back_right`
4. **(Paralel) Cari dataset back-view baru** di Kaggle / HuggingFace:
   - Kata kunci: "hair back view", "hair length dataset", "hairstyle back"
   - Kriteria: foto asli, back-view, ujung rambut terlihat
5. **Deduplikasi** — near-duplicate check (dHash) sebelum split

### 7.2 Schema Filter

```json
{
  "image_id": "figaro1k/lurus/00029.jpg",
  "viewpoint": "back",
  "valid_for_training": true,
  "reason": null
}
```

### 7.3 Gate

- Jumlah citra back-view valid **≥ 150** (minimum viable untuk training)
- Jika < 150 → **wajib** tambah dataset baru sebelum lanjut

### 7.4 Output

- `geometry/reports/viewpoint_filter.json`
- Daftar citra valid siap pakai (path + split assignment)

---

## 8. FASE 2 — Segmentasi Rambut (UNet)

**Tujuan:** model segmentasi yang dapat menghasilkan hair mask untuk citra apa pun.

### 8.1 Data

- **GT mask:** ~1050 binary mask Figaro-1k (`figaro-1k.zip` → `GT/*.pbm`)
- Split: train/val/test dengan **grouping subjek** (hindari leakage)

### 8.2 Arsitektur

- **UNet** (encoder ResNet/MobileNet pretrained ImageNet)
- Output: binary mask 224×224 atau 256×256
- Loss: `L = α·BCE + (1−α)·Dice` (α≈0.5)

### 8.3 Training

- GPU venv ComfyUI
- Augmentasi: flip horizontal (aman untuk rambut), brightness, small rotate
- Early stopping, cosine LR
- Epoch: ~30–40

### 8.4 Metrik

| Metrik | Target |
|---|---|
| IoU | ≥ 0.75 |
| Dice (F1) | ≥ 0.85 |
| Inference time | < 200ms (CPU) |

### 8.5 Export & Inferensi

- Export ONNX → `geometry/weights/hair_segmentation.onnx`
- `geometry/segment_infer.py` — inferensi mask untuk dataset mana pun

### 8.6 Gate

- IoU val **≥ 0.75** → lanjut
- Jika < 0.75 → augmentasi / arsitektur lebih kuat / lebih banyak data

### 8.7 Output

- `geometry/weights/hair_segmentation.onnx`
- `geometry/reports/segmentation_eval.json` (IoU, Dice, confusion, contoh)

---

## 9. FASE 3 — Pipeline Geometris

**Tujuan:** ekstraksi fitur geometris dari mask + pose, normalisasi head-unit.

### 9.1 Modul

**a. `threshold_binary.py`**
```
mask_pred → threshold → morphology (opening/closing) → mask bersih
```

**b. `detect_tied_hair.py`** — deteksi ikatan
```
Fitur: circularity = 4πA/P², solidity = A/A_hull
Hipotesis: rambut diikat → gumpalan melingkar terkonsentrasi
Output: {tied: bool, confidence} → flag "foto ulang"
```
> ⚠️ Ambang deteksi ikatan `[GAP]` — **harus dikalibrasi** dengan data (bukan diasumsikan).

**c. `pose_landmarks.py`** — MediaPipe Pose
```
Output: {shoulder_L, shoulder_R, ear_L, ear_R, nose, hip_L, hip_R} + visibility
```

**d. `measure_length.py`** — klasifikasi panjang (straight/wavy/curly)
```
y_shoulder = (y[sh_L] + y[sh_R]) / 2
y_end      = max{y | mask(x,y)=1}
H_head     = |y[ear] - y[nose]|  (atau face bbox)
y_head_top = min{y | mask(x,y)=1}

# rasio relatif bahu
r = (y_end - y_head_top) / (y_shoulder - y_head_top)

kelas = "pendek"            jika r <= 0.5
        "sebahu"            jika r ≈ 1.0 (±toleransi)
        "sepunggung"        jika ujung mendekati titik punggung
        "melebihi punggung" jika melampaui titik punggung
```
> Ambang (`0.5`, toleransi, titik punggung) **dikalibrasi** dari distribusi data.

**e. `measure_volume.py`** — ketebalan (curly/kinky)
```
R_width = W_hair / W_head       (lebar silhouette vs lebar kepala)
R_area  = A_hair / H_head²
kelas   = tipis / sedang / tebal
```

### 9.2 Fitur yang Diekstrak

| Fitur | Rumus | Untuk |
|---|---|---|
| `y_shoulder_norm` | `(y11+y12)/2` | acuan panjang |
| `H_head_norm` | `|y_ear − y_nose|` | unit normalisasi |
| `W_shoulder_norm` | `|x11 − x12|` | acuan lebar |
| `R_len` | `(y_end − y_top)/(y_shoulder − y_top)` | panjang |
| `R_width` | `W_hair / W_head` | volume |
| `circularity` | `4πA/P²` | deteksi ikatan |
| `solidity` | `A/A_hull` | deteksi ikatan |

### 9.3 Gate

- Fitur terbentuk untuk **≥ 90%** citra valid
- `R_len` berkorelasi dengan penilaian manusia (uji pada subset)

### 9.4 Output

- `geometry/reports/geometric_features.json`
- Visualisasi overlay (mask + garis bahu + endpoint)

---

## 10. FASE 4 — Klasifikasi Hirarkis & Validasi

**Tujuan:** skema klasifikasi hirarkis lengkap + evaluasi jujur.

### 10.1 Pipeline `classify_hierarchical.py`

```
Stage 0: viewpoint filter + ikatan detection → valid?
Stage 1: hair type (CNN)
Stage 2: 
   straight/wavy → measure_length()
   curly         → measure_length() + measure_volume()
   kinky         → measure_volume()
```

### 10.2 Eksperimen Perbandingan (wajib)

| Eksperimen | Input | Metode | Tujuan |
|---|---|---|---|
| E1 | Image | CNN-only | baseline |
| E2 | Mask GT | Geometry-only | uji sinyal geometris |
| E3 | Image + geometri | Hybrid | uji nilai tambah |

Untuk **tiap task** (type, length, volume) — bandingkan fair.

### 10.3 Metrik

| Metrik | Kegunaan |
|---|---|
| Accuracy | info umum |
| **Macro-F1** | metrik utama (imbalance) |
| Precision, Recall per kelas | detail |
| Confusion matrix | analisis error |
| Per-viewpoint | robustness |
| Per-hair-type | fairness |

### 10.4 Metrik Tambahan (geometris)

- Korelasi `R_len` vs annotasi manusia (Spearman)
- Sensitivity terhadap error segmentasi
- Distribusi fitur per kelas

### 10.5 Gate

- Macro-F1 ≥ 0.70 (length/volume)
- Hair type accuracy ≥ 0.85
- Hybrid tidak lebih buruk dari CNN-only (untuk length)

### 10.6 Output

- `geometry/reports/classification_eval.json`
- Model ONNX final (type + segmentation)

---

## 11. FASE 5 — Integrasi, Dataset Baru & Publikasi

### 11.1 Integrasi ke Production

- Adapter `apps/ai` → panggil pipeline CV
- Endpoint memakai model ONNX baru
- Fallback bila landmark gagal (skip length, minta foto ulang)

### 11.2 Dataset Baru & Validasi

- Integrasikan dataset back-view tambahan
- Uji generalisasi lintas dataset
- Uji robustness (viewpoint, cahaya, resolusi)

### 11.3 Publikasi

- **Paper SINTA** — novelty: proporsi tubuh → panjang rambut (celah riset `[GAP]`)
- **Skripsi** — CV + RAG + web lengkap
- Tabel & figur: benchmark arsitektur, analisis per-viewpoint, confusion matrix

### 11.4 Dokumentasi

- Update `docs/06`, `docs/07`, dan dokumen ini dengan hasil aktual
- README `geometry/`
- Reproducibility: seed, versi model, path

---

## 12. Definition of Done Global

Proyek CV dinyatakan **selesai** bila:

- [ ] Fase 0 lulus gate (MediaPipe back-view valid)
- [ ] Dataset back-view valid ≥ 150 citra
- [ ] Model segmentasi IoU ≥ 0.75
- [ ] Pipeline geometris berjalan end-to-end
- [ ] Klasifikasi hirarkis (type → length/volume) menghasilkan output stabil
- [ ] Evaluasi jujur: CNN vs geometry vs hybrid terlaporkan
- [ ] Model ONNX terintegrasi ke `apps/ai`
- [ ] Dokumentasi lengkap (paper + skripsi)
- [ ] Semua script reproducible (seed, `--help`)

---

## 13. Risk Register Global

| Risiko | Prob | Dampak | Mitigasi |
|---|---|---|---|
| MediaPipe gagal back-view | Sedang–Tinggi | Tinggi | Gate Fase 0, pivot P1–P5 |
| Dataset valid sedikit | Sedang | Tinggi | Cari dataset baru (Fase 1 paralel) |
| Segmentasi IoU rendah | Sedang | Sedang | Arsitektur kuat, augmentasi |
| Ambang geometris tidak akurat | Sedang | Tinggi | Kalibrasi dengan human GT kecil |
| Deteksi ikatan tidak reliabel | Tinggi | Sedang | Kalibrasi; bila gagal → manual/absen |
| Kelas sulit dibedakan (κ rendah) | Sedang | Sedang | Gabung kelas jika terbukti tak reliably |
| Waktu 3 bulan kurang | Rendah–Sedang | Sedang | Fokus CV saja (backend sudah jadi) |
| Bias fairness (tipe rambut) | Sedang | Sedang | Uji per-hair-type (Balakrishnan 2020) |

---

## 14. Referensi Silang

| Dokumen | Isi |
|---|---|
| [06-kajian-matematis-referensi.md](./06-kajian-matematis-referensi.md) | Angka rasio terverifikasi (head-unit 7.5–8), rumus, bibliografi |
| [07-fase0-verifikasi-gate.md](./07-fase0-verifikasi-gate.md) | Detail rencana & eksekusi Fase 0 |
| `apps/api/cv/annotation/` | Pipeline anotasi (viewpoint, QC, agreement) |
| `apps/api/cv/geometry/` | Implementasi seluruh Fase 0–5 |

### Angka kunci dari kajian (dikutip aman)
- Head-unit canon: **7.5–8** (Domljan 2024) `[V]`
- Rasio head:shoulder informatif (Lucas & Henneberg 2017) `[V]`
- MediaPipe akurasi **bergantung sudut** (Dill 2023) `[V]`
- Golden ratio φ proporsi tubuh: **TIDAK terbukti** — jangan diklaim `[NS]`

### Benchmark backbone (hasil aktual, `geometry/reports/`)

**Benchmark v2 (15 backbone, 1 seed, hold-out fixed):**
| Backbone | Acc |
|---|---|
| **efficientnet_v2_s** | **0.8418** |
| convnext_small | 0.8204 |
| efficientnet_b2 | 0.8177 |
| convnext_base | 0.8150 |
| convnext_tiny | 0.8070 |
| mobilenet_v2 | 0.7614 |

**Validasi 3-seed (final):** `efficientnet_v2_s` 0.8293±0.0086 > `convnext_tiny` 0.8177±0.0163.
→ **Keputusan: efficientnet_v2_s** (menang + stabil + lebih kecil). Lihat `backbone_decision.json`.

> **Catatan:** backbone lama di runtime (`hair_length.onnx`) = ConvNeXt-Tiny. Untuk switch ke `efficientnet_v2_s` perlu retrain penuh + export ONNX.

---

## Lampiran — Aturan Kelas Geometris (Konseptual)

```
Straight / Wavy:
  bahu = center point
  pendek            : endpoint di atas 50% (kepala→bahu)
  sebahu            : endpoint ≈ garis bahu
  sepunggung        : endpoint mendekati titik punggung
  melebihi punggung : endpoint melampaui titik punggung

Curly:
  panjang (sama seperti straight/wavy) + ketebalan
  (karena curl menambah massa → butuh fitur volume tambahan)

Kinky:
  hanya ketebalan/volume (panjang visual menipu karena coil rapat)

Aturan ikatan:
  rambut mengumpul di satu titik (gumpalan melingkar) → BUKAN panjang alami
  → flag "foto ulang" (produksi) atau exclude (training)
```

> **Catatan:** semua ambang numerik di atas **WAJIB dikalibrasi** dengan data & anotasi manusia. Angka contoh bukan final.

---

> **Status dokumen:** MASTER PLAN. Akan diperbarui seiring eksekusi tiap fase.
