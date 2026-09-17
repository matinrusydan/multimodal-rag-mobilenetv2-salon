# 06 — Kajian Matematis Paper Referensi

> Dokumen ini berisi **kajian matematis** dari paper-paper referensi proyek RAG-salon (klasifikasi rambut berbasis Computer Vision + proporsi tubuh).
>
> Tujuan: menyediakan **dasar ilmiah terukur** (rumus, rasio, angka) yang dapat dikutip langsung di paper SINTA/skripsi, sekaligus menjadi acuan implementasi pipeline geometris.
>
> **Aturan kejujuran ilmiah:** setiap angka ditandai status verifikasinya. Angka yang tidak dapat diverifikasi ditulis eksplisit — **tidak dikarang**.
>
> **Status verifikasi:**
> - `[V]` = terverifikasi dari sumber primer (abstrak/full-text yang berhasil dibaca)
> - `[S]` = dari sumber sekunder / kutipan dalam paper lain
> - `[NS]` = belum terverifikasi / butuh akses penuh (berbayar)
> - `[GAP]` = belum ditemukan di literatur (celah riset)

---

## Daftar Isi

1. [Kerangka Matematis Umum](#1-kerangka-matematis-umum)
2. [Proporsi Tubuh Manusia (Head-Unit Canon)](#2-proporsi-tubuh-manusia-head-unit-canon)
3. [Rasio Kepala–Bahu dari Citra](#3-rasio-kepala-bahu-dari-citra)
4. [BlazePose / MediaPipe Pose](#4-blazepose--mediapipe-pose)
5. [Akurasi & Keterbatasan Pose Estimation](#5-akurasi--keterbatasan-pose-estimation)
6. [Segmentasi Rambut](#6-segmentasi-rambut)
7. [Deteksi Panjang Rambut dari Citra](#7-deteksi-panjang-rambut-dari-citra)
8. [Golden Ratio: Catatan Kritis](#8-golden-ratio-catatan-kritis)
9. [Formulasi Matematis yang Diusulkan untuk Proyek](#9-formulasi-matematis-yang-diusulkan-untuk-proyek)
10. [Rangkuman Angka Kunci](#10-rangkuman-angka-kunci)
11. [Bibliografi](#11-bibliografi)

---

## 1. Kerangka Matematis Umum

### 1.1 Masalah Normalisasi Skala

Klasifikasi dari citra menghadapi masalah skala: jarak kamera, crop, dan resolusi berbeda. Ukuran absolut piksel **tidak valid** sebagai pengukur panjang.

**Formulasi umum rasio tak-berdimensi (dimensionless ratio):**

```
            X_measure
R = ────────────────────────────
            X_reference
```

Di mana:
- `X_measure` = ukuran yang diukur (mis. panjang rambut dalam piksel)
- `X_reference` = ukuran acuan anatomis (mis. tinggi kepala atau lebar bahu dalam piksel)

Karena `R` tidak berdimensi, ia **invariant terhadap skala** (jarak kamera, resolusi) selama proyeksi bersifat ~affine (kamera jauh, distorsi rendah).

### 1.2 Persamaan Proyeksi Pinhole

Untuk memahami batas validitas rasio, model proyeksi kamera:

```
x_pixel = f · (X_world / Z) + cx
```

Di mana `f` = focal length, `Z` = jarak objek. Untuk dua titik pada **bidang yang sama** (mis. bidang frontal seseorang), rasio dua jarak vertikal:

```
            (y2 - y1)_pixel      (Y2 - Y1)_world
R = ────────────────────── = ──────────────────────
            (y3 - y4)_pixel      (Y3 - Y4)_world
```

`f` dan `Z` **tercancel** → rasio tetap valid. **Namun** jika titik berada pada kedalaman `Z` berbeda (mis. kepala lebih dekat kamera daripada punggung), rasio menjadi bias. Ini adalah **asumsi kunci** yang harus dinyatakan sebagai limitasi.

### 1.3 Normalisasi Berbasis Landmark

Alih-alih acuan tetap (mis. tinggi gambar), acuan yang lebih stabil adalah **jarak antar-landmark anatomi** yang proporsional terhadap tubuh:

```
R = d(P_measure) / d(P_a, P_b)
```

dengan `P_a, P_b` = landmark anatomi (mis. titik bahu kiri & kanan → `d` = lebar bahu).

---

## 2. Proporsi Tubuh Manusia (Head-Unit Canon)

### 2.1 Canon Head-Unit

**Temuan `[V]`:** Canon klasik proporsi tubuh manusia menyatakan tinggi badan setara **7.5 hingga 8 head lengths** (satuan tinggi kepala).

> Sumber: Domljan, Iliev & Jurčević Lulić (2024), *Applied Sciences* 14(16):7185. DOI: 10.3390/app14167185.

**Formulasi:**

```
H_body ≈ k · H_head,     k ∈ [7.5, 8.0]
```

Di mana:
- `H_body` = tinggi badan total
- `H_head` = tinggi kepala (vertex → mentum/dagu)
- `k` = jumlah head-unit

### 2.2 Variasi Terhadap Usia & Gender `[V]`

Domljan (2024) mengukur rasio head-length:body-height (HL/BH) pada 1.307 anak usia 2–16:

| Usia | HL/BH (kira-kira) |
|---|---|
| 2 tahun | 5.59 – 5.72 |
| 15 tahun | 7.50 – 7.60 |

**Implikasi matematis:** `k` **bukan konstanta universal** — ia berubah terhadap usia dan gender. Untuk populasi dewasa, `k ≈ 7.5–8`; untuk anak, jauh lebih kecil.

```
k(u, g) = fungsi usia (u) dan gender (g)
```

**Konsekuensi metodologis:** menggunakan `k` tunggal untuk semua subjek menimbulkan **error sistematis**. Harus dinyatakan sebagai limitasi atau dibatasi ke populasi dewasa.

### 2.3 Dublin / Cormic Index `[V]`

Indeks proporsi lain menyangkut rasio tinggi-duduk:

```
Cormic Index = (sitting height) / (stature) × 100
```

> Sumber: Bogin & Varela-Silva (2010), *Int. J. Environ. Res. Public Health* 7(3):1047–1075. DOI: 10.3390/ijerph7031047.

Relevansi terbatas: butuh tinggi duduk (seluruh tubuh), tidak cocok untuk foto back-view parsial.

### 2.4 Tinggi Kepala sebagai Unit Dasar `[V]`

Burton et al. (2013) menemukan leg length bervariasi proporsional terhadap (sitting height − kuantitas mendekati tinggi kepala):

```
leg_length ∝ (sitting_height − c·H_head)
```

> Sumber: Burton, R.F. et al. (2013), *Annals of Human Biology* 40(1):64–69. DOI: 10.3109/03014460.2012.739643.

**Kesimpulan:** tinggi kepala (`H_head`) adalah **kuantitas dasar yang relatif konsisten**, layak dipakai sebagai unit normalisasi.

---

## 3. Rasio Kepala–Bahu dari Citra

### 3.1 Rasio yang Terbukti Informatif `[V]`

**Temuan kunci:** Lucas & Henneberg (2017) menggunakan regresi atas **rasio anthropometrik yang diturunkan dari pengukuran kepala DAN tubuh dari citra** untuk estimasi usia anak.

Rasio yang dipakai **eksplisit** (dari abstrak):
1. `head_height : shoulder_width`
2. `head_height : hip_width`
3. `knee_width`
4. `leg_length`
5. `trunk_length`

> Sumber: Lucas, T. & Henneberg, M. (2017), *International Journal of Legal Medicine* 131(5):1385–1390. DOI: 10.1007/s00414-017-1561-2. PMID: 28233102.

**Model regresi berganda:** 4 rasio per gender; standard error 1.6–1.7 tahun pada n=1.603 laki-laki & 1.833 perempuan.

### 3.2 Formulasi Rasio Kepala–Bahu

```
            H_head              (tinggi kepala, px)
R_hs = ───────────────── = ─────────────────────────
            W_shoulder          (lebar bahu kiri–kanan, px)
```

**Catatan penting `[NS]`:** Nilai koefisien/mean rasio numerik ada di full-text Lucas & Henneberg (berbayar) dan **tidak dapat diverifikasi** dari abstrak. **Jangan mengutip angka rasio spesifik** dari paper ini tanpa akses full-text.

### 3.3 Apa yang Terverifikasi vs Tidak

| Item | Status |
|---|---|
| Rasio head:shoulder **berguna** untuk estimasi dari citra | `[V]` |
| Angka numerik rasio head:shoulder | `[NS]` — butuh full-text |
| Rasio "bahu ke tengah punggung" dalam head-unit (dewasa) | `[NS]` — tidak ditemukan |

---

## 4. BlazePose / MediaPipe Pose

### 4.1 Arsitektur & Landmark `[V]`

BlazePose menghasilkan **33 landmark** 3D, berjalan >30 FPS pada Pixel 2.

> Sumber: Bazarevsky, V. et al. (2020), *BlazePose: On-device Real-time Body Pose Tracking*, arXiv:2006.10204. DOI: 10.48550/arXiv.2006.10204.

**Indeks landmark relevan untuk proyek:**

| Landmark | Indeks | Kegunaan |
|---|---|---|
| Nose | 0 | referensi kepala |
| Left/Right Ear | 7, 8 | tinggi kepala / referensi |
| Left/Right Shoulder | 11, 12 | **acuan utama (bahu)** |
| Left/Right Hip | 23, 24 | proporsi torso (bila terlihat) |

### 4.2 "Visibility" Score

MediaPipe memberi skor `visibility ∈ [0,1]` per landmark. Landmark tak-terlihat (mis. bahu tertutup rambut) mendapat skor rendah.

```
v_i ∈ [0, 1],   i = indeks landmark
```

**Implikasi:** landmark bahu dengan `v < threshold` harus **di-discard** (tidak dipakai), bukan diinterpolasi buta.

### 4.3 Koordinat Image vs World `[V]`

Hazarika (2026) menunjukkan bahwa penggunaan **koordinat world** (bukan piksel) penting untuk generalisasi lintas subjek — ablasi menurunkan akurasi cross-player dari 83%→47% ketika memakai image-space.

> Sumber: Hazarika, J. (2026), arXiv:2606.15992. DOI: 10.48550/arXiv.2606.15992.

**Trade-off untuk proyek:** klasifikasi panjang rambut justru **bergantung pada skala gambar** (rasio), sehingga koordinat piksel **lebih sesuai** di sini — berbeda dari analisis biomekanik.

---

## 5. Akurasi & Keterbatasan Pose Estimation

### 5.1 Validasi Temporal `[V]`

Hii et al. (2023) memvalidasi MediaPipe vs Vicon (motion capture):

| Parameter | ICC(2,1) | MAE |
|---|---|---|
| Parameter gait (mayoritas) | 0.75 – 0.90+ | 20–50 ms |
| Double-support / swing time | 0.47 – 0.62 | — |

Deteksi event: heel-strike 97.2%/99.0%, toe-off 98.0%/95.2%.

> Sumber: Hii, C.S.T. et al. (2023), *Sensors* 23(14):6489. DOI: 10.3390/s23146489. PMC10384445.
> **Catatan:** pengambilan dari **side-view (sagittal)**, bukan back-view.

### 5.2 Ketergantungan Sudut (KRUSIAL) `[V]`

> **Temuan verbatim:** *"the pose estimation is **highly dependent on the camera's viewing angle** as well as the performed exercise. While high accuracy can be achieved under optimal conditions, the accuracy quickly decreases when the conditions are less favourable."*
>
> Sumber: Dill, S. et al. (2023), *Current Directions in Biomedical Engineering* 9(1):563–566. DOI: 10.1515/cdbme-2023-1141.

**Implikasi langsung:** back-view adalah kondisi "less favourable" → **akurasi landmark berisiko turun**. Ini **belum diuji** untuk back-view → menjadi Gate Fase 0 proyek.

### 5.3 Error Sudut & Koordinat `[V]`

- MediaPipe **overestimate sudut**, error ~**18.83°–19.68°** (Asaeda 2024, *Heliyon* 10(17):e36338, DOI: 10.1016/j.heliyon.2024.e36338).
- Error 3D monocular: **RMSE median 56.3** vs stereo-fused **30.1** (Dill 2024, *Sensors* 24(23):7772, DOI: 10.3390/s24237772).

**Konsekuensi matematis:** nilai sudut absolut MediaPipe **tidak reliabel**. Gunakan **rasio/perubahan relatif**, bukan sudut absolut:

```
Gunakan:  Δθ / θ_reference   (relatif)
Hindari:  θ_absolute         (absolut)
```

### 5.4 Landmark yang Lebih Terpercaya `[V]`

Lee et al. (2025) menunjukkan MediaPipe baik untuk landmark **torso/aksial** tetapi buruk untuk detail ekstremitas halus (kaki).

> Sumber: Lee, Y.Y. et al. (2025), *Gait & Posture* 121:64–69. DOI: 10.1016/j.gaitpost.2025.04.015.

**Implikasi:** landmark **bahu & kepala** (aksial) lebih dapat dipercaya daripada ekstremitas → mendukung desain proyek.

---

## 6. Segmentasi Rambut

### 6.1 Metrik Evaluasi Segmentasi

**IoU (Intersection over Union):**

```
           |M_pred ∩ M_gt|
IoU = ─────────────────────────
           |M_pred ∪ M_gt|
```

**Dice Coefficient (F1):**

```
           2 · |M_pred ∩ M_gt|
Dice = ─────────────────────────────
          |M_pred| + |M_gt|
```

### 6.2 Arsitektur UNet (Encoder–Decoder)

UNet memetakan input `X ∈ R^{H×W×C}` ke mask `M ∈ R^{H×W}` melalui jalur encoder (downsampling) + decoder (upsampling) + skip connections.

**Loss gabungan yang umum:**

```
L = α · L_BCE + (1−α) · L_Dice

L_Dice = 1 − (2·Σ p·g + ε) / (Σ p² + Σ g² + ε)
```

Di mana `p` = probabilitas prediksi, `g` = ground truth.

### 6.3 Dataset GT Mask Figaro-1k

Figaro-1k menyediakan **~1050 binary hair mask** (PBM P4, putih=rambut), dapat dipakai melatih segmentasi.

**Thresholding biner umum:**

```
M(x,y) = 1  jika I(x,y) ≥ τ
       = 0  jika I(x,y) < τ
```

Operasi morfologi (buang noise, tutup lubang):

```
M_clean = (M ⊖ B_n) ⊕ B_n        (opening: buang noise)
M_fill  = (M ⊕ B_n) ⊖ B_n        (closing: tutup lubang)
```

---

## 7. Deteksi Panjang Rambut dari Citra

### 7.1 Preseden `[V/S]`

- **Wang et al. (2014)** — *Human Hair Segmentation and Length Detection for Human Appearance Model* (ICPR). Melakukan segmentasi rambut + deteksi panjang. DOI: 10.1109/icpr.2014.86. **Angka konkret `[NS]`** (IEEE berbayar).
- **Tay et al. (2019)** — *AANet* (CVPR) memprediksi atribut termasuk "hair length" dari citra orang. DOI: arXiv:1912.09021.

### 7.2 CELAH RISET `[GAP]`

> **Tidak ditemukan** paper yang menghubungkan **panjang rambut dengan proporsi tubuh / landmark pose**. Pendekatan proyek (rasio tubuh → panjang rambut) adalah **novelty**, sekaligus **risiko** (tanpa preseden).

### 7.3 Fairness `[V]`

Balakrishnan et al. (2020) menemukan hair length sebagai salah satu driver **bias** pada algoritma analisis wajah.

> Sumber: Balakrishnan, G. et al. (2020), ECCV. arXiv:2007.06570.

**Implikasi:** klasifikasi panjang/volume rambut harus diuji fairness lintas hair type (jangan bias ke tipe tertentu).

---

## 8. Golden Ratio: Catatan Kritis

### 8.1 Definisi φ

```
φ = (1 + √5) / 2 ≈ 1.6180339887...
```

### 8.2 Status Bukti `[NS]`

**Temuan jujur:** tidak ditemukan paper akademik terverifikasi yang menetapkan **golden ratio φ sebagai rasio proporsi tubuh yang valid & terukur dari citra/landmark**.

Sebagian besar paper "golden ratio" yang ditemukan menyangkut **kardiologi/dental/estetika**, bukan proporsi tubuh untuk CV:
- Yalta et al. (2016), *Int J Cardiol* — golden ratio & jantung. DOI: 10.1016/j.ijcard.2016.03.166
- Jokar et al. (2025), *J Cosmet Dermatol* — pengukuran estetika vs golden ratio. DOI: 10.1111/jocd.16777

### 8.3 Rekomendasi

| Klaim | Layak? |
|---|---|
| "golden ratio φ = proporsi tubuh terukur" | ❌ **TIDAK didukung bukti** |
| "head-unit canon 7.5–8" | ✅ Terverifikasi (Domljan 2024) |

**Keputusan proyek:** gunakan **head-unit canon**, bukan φ. Jika ingin menyebut golden ratio, sebut sebagai *motivasi historis*, bukan dasar metode.

---

## 9. Formulasi Matematis yang Diusulkan untuk Proyek

> **Catatan:** formulasi ini adalah **usulan** berbasis proporsi terverifikasi. Ambang konkret harus **dikalibrasi** dengan data (anotasi manusia kecil), bukan ditetapkan arbitrer.

### 9.1 Unit Normalisasi

```
H_head = |y(ear_top) − y(chin)|   atau dari pose: H_head ≈ c · H_face
```

Bila wajah tak terdeteksi, gunakan tinggi kepala dari landmark MediaPipe (ear → nose → bahu).

### 9.2 Garis Bahu (Center Point)

```
y_shoulder = ( y(shoulder_L) + y(shoulder_R) ) / 2
```

Asumsi: bahu kiri & kanan terdeteksi (`v ≥ v_min`).

### 9.3 Ujung Rambut

```
y_end = max{ y | mask_hair(x, y) = 1 }     (titik terbawah mask rambut)
```

### 9.4 Rasio Panjang Rambut (ternormalisasi)

```
            y_end − y_head_top
R_len = ──────────────────────────
                  H_head
```

### 9.5 Klasifikasi Panjang (usulan ambang, HARUS dikalibrasi)

Definisi konseptual dari pengguna/domain:

```
- "pendek"           : ujung rambut tidak mencapai 50% jarak kepala→bahu
                       → (y_end − y_head_top) / (y_shoulder − y_head_top) ≤ 0.5
- "sebahu"           : ujung sekitar garis bahu
- "sepunggung"       : ujung mendekati titik punggung
- "melebihi punggung": ujung melampaui titik punggung
```

Ambang numerik (`0.5`, toleransi bahu, posisi punggung) **WAJIB dikalibrasi** dari distribusi data, bukan diasumsikan.

### 9.6 Deteksi Ikatan Rambut

**Hipotesis geometris:** rambut diikat → **gumpalan melingkar di satu titik** (bukan jatuh bebas).

**Fitur kandidat:**

```
circularity = 4π · A / P²      (A=area, P=perimeter; ≈1 untuk bulat)
solidity    = A / A_hull        (A_hull=luas convex hull)
```

Rambut diikat → `circularity` tinggi + gumpalan terkonsentrasi. **Ambang butuh validasi empiris** (`[GAP]`).

### 9.7 Volume/ketebalan (kribo)

```
R_vol = A_hair / H_head²        (area rambut ternormalisasi)
       atau
R_width = W_hair / W_head       (lebar silhouette vs lebar kepala)
```

---

## 10. Rangkuman Angka Kunci

| Besaran | Nilai | Status | Sumber |
|---|---|---|---|
| Head-unit canon (dewasa) | 7.5 – 8.0 | `[V]` | Domljan 2024 |
| HL/BH anak (2 thn) | 5.59 – 5.72 | `[V]` | Domljan 2024 |
| HL/BH anak (15 thn) | 7.50 – 7.60 | `[V]` | Domljan 2024 |
| Rasio head:shoulder (informatif) | ada, angka `[NS]` | `[V]/[NS]` | Lucas & Henneberg 2017 |
| MediaPipe ICC (side-view) | 0.75 – 0.90+ | `[V]` | Hii 2023 |
| MediaPipe MAE temporal | 20–50 ms | `[V]` | Hii 2023 |
| MediaPipe error sudut | 18.8°–19.7° | `[V]` | Asaeda 2024 |
| MediaPipe 3D monocular RMSE | ~56.3 | `[V]` | Dill 2024 |
| MediaPipe akurasi vs sudut | sangat bergantung | `[V]` | Dill 2023 |
| Golden ratio φ = proporsi tubuh | TIDAK terbukti | `[NS]` | — |
| MediaPipe back-view | belum diuji | `[GAP]` | — |
| Panjang rambut via proporsi tubuh | belum ada | `[GAP]` | — |
| Ambang deteksi ikatan | belum ada | `[GAP]` | — |

---

## 11. Bibliografi

**Proporsi tubuh & anthropometri:**
1. Domljan, D., Iliev, B., & Jurčević Lulić, T. (2024). Research on Children's Body Proportions: Determining the Canon of Head Length to Total Body Height. *Applied Sciences*, 14(16), 7185. https://doi.org/10.3390/app14167185 `[V]`
2. Mather, G. (2010). Head–Body Ratio as a Visual Cue for Stature. *Perception*, 39(10), 1390–1395. https://doi.org/10.1068/p6737 `[V]`
3. Bogin, B., & Varela-Silva, M.I. (2010). Leg Length, Body Proportion, and Health. *Int. J. Environ. Res. Public Health*, 7(3), 1047–1075. https://doi.org/10.3390/ijerph7031047 `[V]`
4. Burton, R.F. et al. (2013). Statistical approaches to relationships between sitting height and leg length in adults. *Annals of Human Biology*, 40(1), 64–69. https://doi.org/10.3109/03014460.2012.739643 `[V]`
5. Lucas, T., & Henneberg, M. (2017). Estimating a child's age from an image using whole body proportions. *International Journal of Legal Medicine*, 131(5), 1385–1390. https://doi.org/10.1007/s00414-017-1561-2 `[V]`
6. Utkualp, N., & Ercan, İ. (2015). Anthropometric Measurements Usage in Medical Sciences. *BioMed Research International*, 2015, 404261. https://doi.org/10.1155/2015/404261 `[V]`

**Pose estimation:**
7. Bazarevsky, V. et al. (2020). BlazePose: On-device Real-time Body Pose Tracking. arXiv:2006.10204. https://doi.org/10.48550/arXiv.2006.10204 `[V]`
8. Hii, C.S.T. et al. (2023). Automated Gait Analysis Based on a Marker-Free Pose Estimation Model. *Sensors*, 23(14), 6489. https://doi.org/10.3390/s23146489 `[V]`
9. Dill, S. et al. (2023). Accuracy Evaluation of 3D Pose Estimation with MediaPipe Pose for Physical Exercises. *Current Directions in Biomedical Engineering*, 9(1), 563–566. https://doi.org/10.1515/cdbme-2023-1141 `[V]`
10. Dill, S. et al. (2024). Evaluation of Accuracy and Angle Dependency of 3D Pose Estimation through Stereo Camera Information Fusion with MediaPipe Pose. *Sensors*, 24(23), 7772. https://doi.org/10.3390/s24237772 `[V]`
11. Asaeda, M. et al. (2024). Reliability and validity of knee valgus angle calculation using posture estimation (MediaPipe Pose). *Heliyon*, 10(17), e36338. https://doi.org/10.1016/j.heliyon.2024.e36338 `[V]`
12. Lee, Y.Y. et al. (2025). Validation of a video-based pose estimation algorithm for single limb stance test. *Gait & Posture*, 121, 64–69. https://doi.org/10.1016/j.gaitpost.2025.04.015 `[V]`
13. Hazarika, J. (2026). Multi-Task Tennis Stroke Biomechanics Analysis Using MediaPipe Pose. arXiv:2606.15992. https://doi.org/10.48550/arXiv.2606.15992 `[V]`

**Segmentasi rambut & atribut:**
14. Wang, Y., Zhou, Z., Teoh, E.K., & Su, B. (2014). Human Hair Segmentation and Length Detection for Human Appearance Model. *ICPR*. https://doi.org/10.1109/icpr.2014.86 `[NS]`
15. Muhammad, U.R., Svanera, M., Leonardi, R., & Benini, S. (2018). Hair detection, segmentation, and hairstyle classification in the wild. *Image and Vision Computing*, 71, 25–37. https://doi.org/10.1016/j.imavis.2018.02.001 `[V]`
16. Tay, C.-P., Roy, S., & Yap, K.-H. (2019). AANet: Attribute Attention Network for Person Re-Identifications. *CVPR*. arXiv:1912.09021 `[V]`
17. Balakrishnan, G. et al. (2020). Towards causal benchmarking of bias in face analysis algorithms. *ECCV*. arXiv:2007.06570 `[V]`

**Golden ratio (untuk konteks kritis):**
18. Yalta, K. et al. (2016). Golden Ratio and the heart. *Int J Cardiol*. https://doi.org/10.1016/j.ijcard.2016.03.166 `[V]`
19. Jokar, M. et al. (2025). Anthropometric and Angular Measurements in Healthy Persian Females in Comparison to the Golden Ratio. *J Cosmet Dermatol*. https://doi.org/10.1111/jocd.16777 `[V]`

---

> **Catatan penutup untuk penulis:** Jangan mengutip angka ber-tanda `[NS]` atau `[GAP]` sebagai fakta ilmiah. Gunakan dokumen ini sebagai peta: bagian `[V]` aman dikutip; bagian `[NS]/[GAP]` adalah **peluang riset** yang harus diisi lewat eksperimen sendiri.
