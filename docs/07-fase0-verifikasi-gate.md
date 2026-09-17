# 07 — FASE 0: Verifikasi Gate (Uji MediaPipe Pose pada Back-View)

> **Dokumen ini khusus untuk task Computer Vision (CV) proyek RAG-salon.**
>
> Fase 0 adalah **gerbang kritis** (go/no-go gate) sebelum membangun seluruh pipeline geometris klasifikasi rambut. Tujuannya: membuktikan secara empiris apakah **landmark anatomi (khususnya bahu) dapat dideteksi secara andal pada foto back-view**.
>
> Jika gate ini GAGAL, seluruh metode berbasis proporsi tubuh runtuh → harus pivot sebelum membuang waktu.
>
> **Status:** RENCANA — belum dieksekusi.
> **Prasyarat dokumen:** [06-kajian-matematis-referensi.md](./06-kajian-matematis-referensi.md)

---

## Daftar Isi

1. [Latar Belakang & Justifikasi](#1-latar-belakang--justifikasi)
2. [Pertanyaan Riset Fase 0](#2-pertanyaan-riset-fase-0)
3. [Hipotesis & Kriteria Lulus (Gate)](#3-hipotesis--kriteria-lulus-gate)
4. [Data yang Digunakan](#4-data-yang-digunakan)
5. [Implementasi Script](#5-implementasi-script)
6. [Metrik yang Diukur](#6-metrik-yang-diukur)
7. [Prosedur Eksperimen](#7-prosedur-eksperimen)
8. [Analisis & Ambang Keputusan](#8-analisis--ambang-keputusan)
9. [Skenario Hasil & Aksi](#9-skenario-hasil--aksi)
10. [Output & Deliverable](#10-output--deliverable)
11. [Risiko & Mitigasi](#11-risiko--mitigasi)
12. [Langkah Eksekusi (Checklist)](#12-langkah-eksekusi-checklist)
13. [Kaitan ke Fase Berikutnya](#13-kaitan-ke-fase-berikutnya)

---

## 1. Latar Belakang & Justifikasi

### 1.1 Mengapa Fase 0 Ada

Berdasarkan kajian literatur ([07](./06-kajian-matematis-referensi.md) §5):

> **Dill et al. (2023)** menemukan bahwa akurasi MediaPipe Pose **"highly dependent on the camera's viewing angle"** — akurasi menurun cepat pada kondisi kurang ideal.

**Back-view adalah kondisi "less favourable" yang BELUM diuji** (`[GAP]` di literatur). Tidak ada paper yang memvalidasi MediaPipe Pose pada foto tampak belakang.

### 1.2 Mengapa Bahu Krusial

Seluruh metode klasifikasi panjang rambut berencana memakai **garis bahu sebagai center point**:

```
y_shoulder = ( y(shoulder_L) + y(shoulder_R) ) / 2
```

Jika `y_shoulder` tidak dapat dideteksi → tidak ada acuan → klasifikasi panjang mustahil.

### 1.3 Prinsip

> **Ukur dulu, baru bangun.** Jangan bangun pipeline segmentasi/geometri sebelum terbukti landmark tersedia.

---

## 2. Pertanyaan Riset Fase 0

**RQ0.1** — Berapa proporsi foto back-view Figaro-1k yang berhasil dideteksi landmark bahu (kiri & kanan)?

**RQ0.2** — Berapa proporsi yang berhasil dideteksi landmark kepala (telinga/hidung) sebagai acuan unit tinggi kepala?

**RQ0.3** — Apakah skor `visibility` MediaPipe pada landmark bahu konsisten dengan penilaian manusia (valid/tidak)?

**RQ0.4** — Apakah ada perbedaan detection rate antara foto back-view vs front-view vs side-view?

**RQ0.5** — Apakah rasio `head:shoulder` yang terukur pada back-view masuk akal secara anatomis (stabil)?

---

## 3. Hipotesis & Kriteria Lulus (Gate)

### 3.1 Hipotesis

- **H0 (null):** Detection rate landmark bahu pada back-view ≤ 60% (MediaPipe tidak cocok untuk back-view).
- **H1 (alternatif):** Detection rate landmark bahu pada back-view ≥ 70% (MediaPipe layak).

### 3.2 Kriteria Lulus (GATE)

| Metrik | Ambang LULUS | Ambang PIVOT |
|---|---|---|
| Detection rate bahu (kiri **dan** kanan) | **≥ 70%** | < 70% |
| Detection rate minimal satu landmark kepala | **≥ 80%** | < 80% |
| Korelasi visibility vs penilaian manusia (Spearman) | **≥ 0.5** | < 0.5 |
| Stabilitas rasio head:shoulder (CV ≤ 0.30) | **ya** | tidak |

> **Catatan:** ambang ini adalah **rekomendasi praktis**, bukan hukum ilmiah. Harus dicatat sebagai keputusan desain.

### 3.3 Definisi "Berhasil Dideteksi"

Sebuah landmark dianggap **berhasil dideteksi** bila:
1. MediaPipe mengembalikan landmark, DAN
2. Skor `visibility ≥ v_min` (usulan awal `v_min = 0.5`), DAN
3. Landmark berada dalam batas gambar (0 ≤ x ≤ W, 0 ≤ y ≤ H).

---

## 4. Data yang Digunakan

### 4.1 Sumber

| Sumber | Jumlah | Kegunaan |
|---|---|---|
| Figaro-1k (back-view) | ~dari anotasi viewpoint | **target uji utama** |
| Figaro-1k (front/side) | ~dari anotasi viewpoint | pembanding |
| (Opsional) dataset back-view baru | — | validasi tambahan |

### 4.2 Cara Menentukan Label Viewpoint

Dua opsi:
- **Opsi A (disarankan):** pakai anotasi viewpoint yang sudah ada (arsip `_archive_annotator_A_p240_v2.json`) — kolom `viewpoint`.
- **Opsi B:** anotasi ulang cepat khusus viewpoint (Ya/Tidak/Ragu) bila anotasi lama tidak memadai.

### 4.3 Besaran Sampel

- **Minimum:** 30 foto back-view + 15 front + 15 side (total ~60).
- **Ideal:** 60 back-view + 30 front + 30 side (total ~120).
- **Alasan:** cukup untuk estimasi proporsi dengan margin error ±10%.

### 4.4 Catatan Kualitas

- Foto harus memiliki bahu minimal **sebagian terlihat** (bukan crop kepala saja).
- Catat resolusi gambar (berpengaruh ke deteksi).

---

## 5. Implementasi Script

### 5.1 Lokasi (Isolated)

```
apps/api/cv/geometry/          ← folder BARU, tidak menyentuh scripts/ lama
├── README.md
├── pose_feasibility.py        ← script utama Fase 0
├── reports/
│   ├── pose_feasibility.json
│   └── figures/
│       ├── pose_ok_*.png
│       └── pose_fail_*.png
└── weights/                   ← (kosong di Fase 0, dipakai Fase 2)
```

### 5.2 Spesifikasi `pose_feasibility.py`

**Input:**
- `--manifest` : path manifest/viewpoint (JSON) berisi daftar `{image_id, relpath, viewpoint}`
- `--per-view` : jumlah sampel per viewpoint (default 30)
- `--v-min` : ambang visibility landmark (default 0.5)
- `--out` : path output JSON

**Proses per gambar:**
```
1. Load image (PIL/OpenCV)
2. MediaPipe Pose → 33 landmark + visibility
3. Ambil landmark relevan:
   - SHOULDER_L (11), SHOULDER_R (12)
   - EAR_L (7), EAR_R (8), NOSE (0)
   - HIP_L (23), HIP_R (24)
4. Hitung:
   - shoulder_ok = (vis[11]>=v_min) AND (vis[12]>=v_min) AND dalam batas gambar
   - head_ok     = ada salah satu dari {7,8,0} dengan vis>=v_min
   - y_shoulder  = (y[11]+y[12])/2  (bila shoulder_ok)
   - H_head      = |y[ear] - y[shoulder]| atau dari face bbox (fallback)
   - R_head_shoulder = H_head / W_shoulder
5. Simpan landmark (opsional) + flag
```

**Output JSON (per gambar):**
```json
{
  "image_id": "figaro1k/lurus/00029.jpg",
  "viewpoint_annotated": "back",
  "resolve_wh": [418, 556],
  "landmarks": {
    "shoulder_L": {"x": 0.41, "y": 0.62, "visibility": 0.91},
    "shoulder_R": {"x": 0.59, "y": 0.61, "visibility": 0.88},
    "ear_L": {"x": 0.44, "y": 0.18, "visibility": 0.79},
    "nose": {"x": 0.50, "y": 0.15, "visibility": 0.40},
    "hip_L": null, "hip_R": null
  },
  "shoulder_ok": true,
  "head_ok": true,
  "y_shoulder_norm": 0.615,
  "H_head_norm": 0.44,
  "W_shoulder_norm": 0.18,
  "R_head_shoulder": 2.44
}
```

**Output ringkasan:**
```json
{
  "n_total": 120,
  "by_viewpoint": {
    "back":  {"n": 60, "shoulder_ok": 44, "shoulder_rate": 0.733, "head_ok": 55, "head_rate": 0.917},
    "front": {"n": 30, "shoulder_ok": 27, "shoulder_rate": 0.900, "head_ok": 29, "head_rate": 0.967},
    "side":  {"n": 30, "shoulder_ok": 24, "shoulder_rate": 0.800, "head_ok": 27, "head_rate": 0.900}
  },
  "gate": {"shoulder_back_rate": 0.733, "threshold": 0.70, "pass": true}
}
```

### 5.3 Dependensi

- `mediapipe` — **sudah terinstall** di venv CV
- `opencv-python-headless`, `Pillow`, `numpy` — sudah terinstall
- `matplotlib` — untuk visualisasi skeleton

**Tidak ada dependensi baru.**

---

## 6. Metrik yang Diukur

### 6.1 Detection Rate

```
                     jumlah gambar dengan shoulder_ok = True
DetectionRate_sh = ─────────────────────────────────────────────
                          jumlah total gambar (per viewpoint)
```

### 6.2 Detection Rate per Landmark

Untuk setiap landmark `i`, hitung fraksi `vis[i] ≥ v_min`.

### 6.3 Stabilitas Rasio Head:Shoulder

Untuk gambar yang lolos, hitung koefisien variasi:

```
CV = σ(R_head_shoulder) / μ(R_head_shoulder)
```

`CV ≤ 0.30` menandakan rasio cukup stabil (dapat dipakai normalisasi).

### 6.4 Korelasi Visibility vs Penilaian Manusia

- Ambil 20 gambar acak, annotator menilai "apakah bahu terlihat?" (Ya/Tidak)
- Hitung **Spearman ρ** antara `shoulder_ok` (MediaPipe) dan penilaian manusia.
- `ρ ≥ 0.5` = ada kesesuaian.

### 6.5 Perbandingan Antar-Viewpoint

Bandingkan `DetectionRate_sh` untuk back vs front vs side → apakah back-view signifikan lebih buruk (uji proporsi / McNemar bila berpasangan).

---

## 7. Prosedur Eksperimen

### Langkah:

1. **Siapkan manifest uji**
   - Ekstrak `{image_id, relpath, viewpoint}` dari anotasi viewpoint yang ada
   - Sampling per viewpoint (deterministik, seed tetap)

2. **Jalankan `pose_feasibility.py`**
   - MediaPipe Pose mode `static_image_mode=True`, `model_complexity=1` (Balanced)
   - Catat landmark + visibility tiap gambar

3. **Generate visualisasi**
   - Overlay skeleton pada sampel OK & FAIL
   - Contact sheet: back-view yang berhasil vs gagal deteksi bahu

4. **Human cross-check (kecil)**
   - 20 gambar, annotator nilai bahu terlihat/tidak
   - Hitung Spearman ρ

5. **Analisis statistik**
   - Detection rate per viewpoint
   - CV rasio head:shoulder
   - Keputusan gate

6. **Dokumentasikan hasil**

---

## 8. Analisis & Ambang Keputusan

### 8.1 Tabel Keputusan

| Kondisi | Keputusan |
|---|---|
| shoulder_rate(back) ≥ 0.70 **DAN** head_rate ≥ 0.80 | ✅ **LULUS** → lanjut Fase 1 |
| 0.50 ≤ shoulder_rate(back) < 0.70 | ⚠️ **KONDISIONAL** → uji model pose alternatif, evaluasi trade-off |
| shoulder_rate(back) < 0.50 | ❌ **PIVOT** → ubah pendekatan acuan |

### 8.2 Jika Kondisional/Pivot — Opsi Pivot

| Opsi | Deskripsi |
|---|---|
| P1 | MediaPipe Pose `model_complexity=2` (Heavy) — akurasi lebih tinggi |
| P2 | YOLO-Pose / BlazePose GHUM Full |
| P3 | Deteksi bahu via kontur (classical CV, bukan pose model) |
| P4 | Ganti acuan: pakai **tinggi kepala** saja (dari face detection) tanpa bahu |
| P5 | Kumpulkan dataset back-view baru dengan kualitas lebih baik |

---

## 9. Skenario Hasil & Aksi

### Skenario A — LULUS (≥70%)
- Lanjut Fase 1 (data cleaning) & Fase 2 (segmentasi)
- Dokumentasikan: MediaPipe **valid** untuk back-view pada dataset ini

### Skenario B — KONDISIONAL (50–70%)
- Uji pivot P1/P2
- Jika tetap < 70% → pertimbangkan P4 (acuan tinggi kepala saja)
- Catat sebagai limitasi paper

### Skenario C — GAGAL (<50%)
- Pivot total: hindari acuan anatomis, kembali ke klasifikasi CNN murni
- Atau kumpulkan dataset baru (P5)
- Dokumentasikan sebagai **negative result** yang valid (berguna untuk paper)

> **Penting:** Hasil negatif tetap valid secara ilmiah. Gate ini bukan "mencari pembenaran", tetapi **menguji kelayakan secara jujur**.

---

## 10. Output & Deliverable

| File | Isi |
|---|---|
| `geometry/pose_feasibility.py` | Script uji |
| `geometry/reports/pose_feasibility.json` | Hasil lengkap + ringkasan + keputusan gate |
| `geometry/reports/figures/pose_ok_*.png` | Contoh berhasil |
| `geometry/reports/figures/pose_fail_*.png` | Contoh gagal |
| `geometry/reports/figures/viewpoint_comparison.png` | Grafik detection rate per viewpoint |
| `docs/07-fase0-verifikasi-gate.md` (dokumen ini) | Rencana & hasil |

**Definition of Done (DoD):**
- [ ] Script berjalan tanpa error
- [ ] ≥60 gambar teruji
- [ ] JSON hasil lengkap dengan keputusan gate eksplisit
- [ ] Visualisasi tersedia
- [ ] Laporan keputusan (LULUS/KONDISIONAL/PIVOT) tertulis

---

## 11. Risiko & Mitigasi

| Risiko | Probabilitas | Dampak | Mitigasi |
|---|---|---|---|
| MediaPipe gagal deteksi bahu back-view | Sedang–Tinggi | Tinggi | Gate ketat + opsi pivot P1–P5 |
| Foto Figaro crop terlalu ketat (bahu tak ada) | Sedang | Sedang | Filter pra-syarat: minimal bahu sebagian terlihat |
| Landmark terdeteksi tapi posisi salah | Sedang | Tinggi | Cross-check manusia (Spearman) |
| Anotasi viewpoint tidak akurat | Rendah | Sedang | Verifikasi visual sampel |
| Sampel terlalu kecil | Sedang | Sedang | Perbesar ke 120+ |

---

## 12. Langkah Eksekusi (Checklist)

```
[ ] 1. Buat folder apps/api/cv/geometry/ + README.md
[ ] 2. Buat manifest uji viewpoint (dari anotasi yang ada)
[ ] 3. Implementasi pose_feasibility.py
[ ] 4. Uji --help + jalankan pada 5 gambar (smoke test)
[ ] 5. Jalankan pada ≥60 gambar (30 back + 15 front + 15 side)
[ ] 6. Analisis detection rate + CV rasio
[ ] 7. Cross-check manusia (20 gambar) → Spearman ρ
[ ] 8. Generate visualisasi
[ ] 9. Simpan pose_feasibility.json + keputusan gate
[ ] 10. Tulis hasil + keputusan (LULUS/KONDISIONAL/PIVOT)
[ ] 11. Update dokumen ini dengan hasil aktual
```

---

## 13. Kaitan ke Fase Berikutnya

```
FASE 0 (dokumen ini)
   │  Uji MediaPipe back-view
   │
   ├─ LULUS ──────────────┐
   │                      ↓
   │              FASE 1: Data Cleaning (viewpoint gate)
   │                      ↓
   │              FASE 2: Segmentasi (UNet dari GT Figaro)
   │                      ↓
   │              FASE 3: Geometric Pipeline (head-unit + pose)
   │                      ↓
   │              FASE 4: Klasifikasi Hirarkis
   │
   ├─ KONDISIONAL ────────→ Uji pivot P1/P2
   │
   └─ PIVOT ──────────────→ Ganti acuan / dataset baru
```

**Fase 0 HARUS selesai & lulus sebelum Fase 1 dimulai.** Ini mencegah pemborosan waktu pada metode yang tidak feasible.

---

> **Catatan implementasi:** Semua pekerjaan di `apps/api/cv/geometry/` (folder baru). **Tidak menyentuh** `scripts/`, `dataset/`, `weights/`, atau pipeline lama — sesuai prinsip isolasi proyek.

---

## Lampiran A — Spesifikasi Landmark MediaPipe Pose

| Indeks | Nama | Relevansi |
|---|---|---|
| 0 | nose | acuan kepala (fallback) |
| 7 | left_ear | acuan tinggi kepala |
| 8 | right_ear | acuan tinggi kepala |
| 11 | left_shoulder | **acuan utama** |
| 12 | right_shoulder | **acuan utama** |
| 23 | left_hip | proporsi torso (bila terlihat) |
| 24 | right_hip | proporsi torso (bila terlihat) |

## Lampiran B — Rumus yang Dipakai

```
y_shoulder_norm = (y[11] + y[12]) / 2
W_shoulder_norm = |x[11] - x[12]|
H_head_norm     = |y[ear] - y[nose]|  (atau dari face bbox)
R_head_shoulder = H_head_norm / W_shoulder_norm
CV(R) = std(R) / mean(R)
```
