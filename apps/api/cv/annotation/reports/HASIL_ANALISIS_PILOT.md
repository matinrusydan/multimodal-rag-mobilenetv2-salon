# Hasil Pilot Anotasi & Analisis Sinyal Geometris

> **Tanggal:** September 2026
> **Dataset pilot:** Figaro-1k, 80 citra (20 per hair type), seed=42
> **Anotator:** A (internal) + B (independen)
> **Taxonomy:** pilot-v1

---

## 1. Kelengkapan Anotasi

| Anotator | Total | Lengkap | Tidak Lengkap |
|---|---|---|---|
| A | 80 | 74 (setelah sebelumnya) | 6 (diperbaiki/dibiarkan) |
| B | 80 | **80** | 0 |

**Catatan A:** 6 record tidak lengkap (4 ungradable tanpa alasan, 2 length kosong). Tool sudah diperbaiki dengan validasi agar tidak terulang. Data A tetap dipakai apa adanya (tidak diubah, sesuai prinsip data integrity).

---

## 2. Inter-Annotator Agreement (A vs B)

### Kesepakatan umum
- **Raw agreement (semua label): 0.7875**
- Viewpoint sama persis: **67/80 (0.84)**
- Hair type agreement (comparable): **58/63 (0.921)**
- Kesepakatan ungradable: keduanya=10, hanya A=1, hanya B=6, keduanya dinilai=63

### LENGTH (straight/wavy) — n=44
| Metrik | Nilai |
|---|---|
| Raw agreement (ordinal) | **0.9355** |
| Cohen's κ | **0.897** |
| Linear weighted κ | **0.9399** |
| Quadratic weighted κ | **0.9687** |
| Ungradable rate (A) | 20.4% |
| Ungradable rate (B) | 27.3% |
| Per-class recall | short 1.00, shoulder 0.75, mid_back 1.00, long 0.50 |
| Disagreement boundaries | long↔mid_back (1), shoulder↔ungradable (2), mid_back↔shoulder (1) |
| **Decision** | **YELLOW** |

### VISUAL VOLUME (curly/kinky) [PROVISIONAL] — n=34
| Metrik | Nilai |
|---|---|
| Raw agreement (ordinal) | **0.8276** |
| Cohen's κ | **0.7254** |
| Quadratic weighted κ | **0.8394** |
| Disagreement boundaries | high↔medium (3), low↔medium (2), high↔ungradable (2) |
| **Decision** | **YELLOW** |

### Interpretasi
- **Length: YELLOW→mendekati GREEN.** κ=0.897 (unweighted) dan quad κ=0.969 sangat baik. YELLOW dipicu oleh: (a) ungradable rate B > 15%, (b) kelas `long` hanya recall 0.50 (n kecil), (c) sedikit disagreement `long↔mid_back`.
- **Volume: YELLOW.** κ=0.725 lebih rendah; boundary `high↔medium` dan `low↔medium` adalah titik lemah. Ini konsisten dengan status taxonomy volume yang **PROVISIONAL**.
- **Hair type sangat baik** (0.921) — kecuali pasangan `curly↔wavy` (3 disagreement) dan `straight↔wavy` (1).

### Titik lemah teridentifikasi
1. **Ungradable rate berbeda** antara A (20%) dan B (27%) — ambang kapan "tidak bisa dinilai" tidak seragam.
2. **Banyak foto front-view** (A:22, B:20 dari 80) — ini memengaruhi validitas (lihat §4).
3. **Boundary `long`** sulit (hanya 1-3 sampel; recall rendah).
4. **Boundary volume `high↔medium`** — paling ambigu.

---

## 3. E0 Gate: Sinyal Geometris vs Human GT

> ⚠️ Ini **hipotesis-generating**, bukan konfirmasi. Sampel pilot kecil (n=33 length, n=34 volume) dan tidak seimbang.

### LENGTH (straight/wavy), n=33
| Fitur | Kruskal-Wallis H | p-value | Effect size ε² | Signifikan? |
|---|---|---|---|---|
| **bbox_aspect** | 26.42 | **0.000008** | **0.732** | ✅ besar |
| **face_ratio** | 18.52 | **0.000343** | 0.554 | ✅ besar |
| **span_ratio** | 18.65 | **0.000323** | 0.489 | ✅ besar |
| **bbox_h** | 18.36 | **0.000370** | 0.480 | ✅ besar |
| bbox_w | 8.76 | 0.0326 | 0.180 | ✅ kecil |
| area_ratio | 8.87 | 0.0311 | 0.183 | ✅ kecil |
| fill_ratio | 0.99 | 0.803 | −0.063 | ❌ |
| solidity | 1.90 | 0.594 | −0.034 | ❌ |

**Temuan:** Fitur **ekstensi vertikal + aspek** (bbox_aspect, face_ratio, span_ratio, bbox_h) membawa sinyal kuat untuk length. Fitur **massa** (solidity, fill_ratio) **tidak** — bahkan sedikit negatif. Ini mendukung hipotesis bahwa "panjang ≈ ekstensi vertikal relatif", bukan "massa".

### VOLUME (curly/kinky), n=34
| Fitur | H | p-value | ε² | Signifikan? |
|---|---|---|---|---|
| **span_ratio** | 14.07 | **0.000879** | 0.366 | ✅ sedang |
| **area_ratio** | 10.95 | **0.004182** | 0.271 | ✅ sedang |
| **face_ratio** | 6.64 | 0.0361 | 0.160 | ✅ kecil |
| thickness_index | 4.07 | 0.131 | 0.063 | ❌ |
| fill_ratio | 3.20 | 0.202 | 0.036 | ❌ |
| solidity | 1.34 | 0.512 | −0.020 | ❌ |
| bbox_aspect | 1.37 | 0.505 | −0.019 | ❌ |

**Temuan:** Fitur **massa/luasan + sebaran** (area_ratio, span_ratio) membawa sinyal untuk volume. `solidity` & `bbox_aspect` **tidak** (baik — artinya volume bukan sekadar ulangan length).

> **PERINGATAN CONFOUND:** `span_ratio` signifikan di KEDUA task. Karena length dan volume adalah task berbeda (sample berbeda: straight/wavy vs curly/kinky), ini **bukan konfirmasi** — bisa jadi span_ratio memang generik. Perlu uji pada sampel lebih besar.
> **Uji konsensus (A==B):** hanya 30 (length) & 23 (volume) sampel — terlalu kecil untuk kesimpulan kuat. Hasil konsisten (bbox_aspect p=0.00009 length; area_ratio p=0.043 volume).

---

## 4. MASALAH KRITIS: Viewpoint

| Viewpoint | A | B |
|---|---|---|
| back | 36 | 46 |
| back_left | 2 | 0 |
| back_right | 7 | 3 |
| side | 13 | 11 |
| **front** | **22** | **20** |
| unknown | 0 | 0 |

**~27% foto Figaro-1k dinilai FRONT-view** oleh kedua annotator. Ini penting:
- Figaro-1k **tidak sepenuhnya back-view** sebagaimana diasumsikan.
- Foto front → tidak valid untuk length/volume (anchor tubuh tidak terlihat).
- Ini menjelaskan **ungradable rate tinggi** dan sebagian disagreement (`XNUMX|ungradable`).

**Implikasi:** Dataset primer perlu **viewpoint gate**. Untuk training length/volume, hanya gambar back/back_left/back_right/side yang valid.

---

## 5. Kesimpulan Gate Keputusan

```
Anotasi A+B selesai
    ↓
AGREEMENT: LENGTH = YELLOW (mendekati GREEN), VOLUME = YELLOW
    ↓
E0 SIGNAL: LENGTH → SINYAL KUAT ✅ (bbox_aspect, face_ratio, span_ratio)
           VOLUME → SINYAL SEDANG ✅ (area_ratio, span_ratio)
    ↓
REKOMENDASI: LANJUT, TAPI perbaiki dulu:
    1. Ungradable bukan masalah label — perbaiki definisi front-view
    2. Skala pilot terlalu kecil (n=33) → anotasi lebih besar
    3. Boundary `long` & volume `high↔medium` perlu guideline lebih tegas
```

### Keputusan
- **GREEN-ish untuk length:** κ tinggi → taxonomy length **layak**, perlu **pilot ulang dengan sampel lebih besar** untuk konfirmasi boundary `long`.
- **YELLOW untuk volume:** taxonomy volume **belum matang**, perlu revisi definisi `high↔medium`.
- **E0 lolos:** sinyal geometris terhadap human GT **ADA** → jalur geometri/hybrid **layak dilanjutkan** (tidak boleh dianggap pasti lebih baik dari CNN; harus eksperimen terkontrol).

---

## 6. Catatan Metodologis

- Human annotation = reference (bukan pseudo-label).
- Gemini/geometric pseudo-label TIDAK dipakai sebagai GT.
- dHash overlap: 0 likely_duplicate, 52 possible_same_subject (perlu review manual sebelum split).
- Tidak ada klaim centimeter atau strand thickness fisik.
- Semua angka dari `annotation/reports/*.json` (reproducible).

---

## 7. Langkah Berikutnya (Rekomendasi)

1. **Perbaiki 6 record A** (opsional, agar konsisten dengan B).
2. **Perbesar pilot** (mis. 200–300 citra) untuk stabilkan estimasi boundary & κ.
3. **Tegaskan guideline viewpoint** — definisi `front` vs `side` (batas sudut).
4. **Revisi taxonomy volume** — definisi `high↔medium` yang lebih operasional.
5. **Baru** jalankan eksperimen model (E1 CNN baseline) pada subset valid (back-view only).
