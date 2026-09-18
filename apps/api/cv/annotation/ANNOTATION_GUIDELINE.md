# ANNOTATION GUIDELINE — Hierarchical Hair Classification (Pilot v1)

> **Version:** pilot-v1
> **Date:** September 2026
> **Status:** PILOT taxonomy — NOT final. Validated only after inter-annotator agreement analysis.

---

## 1. Purpose

Mengklasifikasi atribut rambut dari static image secara hirarkis:

1. **Level 1 — Hair Type** (4 kelas): straight / wavy / curly / kinky
2. **Level 2 — Conditional Attribute** (tergantung Level 1):
   - straight/wavy → **relative hair length** (4 kelas: short / shoulder / mid_back / long)
   - curly/kinky → **visual volume / apparent thickness** (3 kelas PROVISIONAL: low / medium / high)

**PENTING:**
- Hair length adalah **relative visual hair-length classification**, BUKAN pengukuran dalam centimeter.
- Visual volume adalah **apparent hair mass/silhouette**, BUKAN physical strand thickness.
- Jangan mengarang threshold. Jangan menebak jika informasi tidak cukup.

---

## 2. Hair Type (Level 1)

Label EN (pilot) dipetakan ke label ID (dataset existing):

| EN (annotasi) | ID (dataset)  | Definisi operasional |
|---|---|---|
| `straight`  | `lurus`            | Rambut lurus, tidak ada kelengkungan signifikan. Pola jatuh tegak/kondu. |
| `wavy`      | `bergelombang`    | Rambut bergelombang — lengkung lembut, tidak coil ketat. |
| `curly`     | `keriting`        | Rambut keriting — coil/curl terdefinisi, pola spiral atau loop jelas. |
| `kinky`     | `sangat-keriting` | Rambut kribo/afro — coil sangat rapat, tekstur tinggi, sering mengembang. |

**Aturan:**
- Pilih SATU kelas yang paling dominan.
- Jika rambut jelas campuran dua kategori → pilih yang lebih menonjol secara visual, catat di notes.
- Jika tidak dapat ditentukan → `ungradable=true`, `ungradable_reason=ambiguous`.

---

## 3. Viewpoint (Input Validity)

Setiap image diberi label viewpoint. Ini **bukan** kelas target, tetapi **validity condition**.

| Viewpoint | Deskripsi | Valid? |
|---|---|---|
| `back`        | Foto tegak lurus dari belakang | ✅ |
| `back_left`   | Dari belakang, sedikit miring ke kiri | ✅ |
| `back_right`  | Dari belakang, sedikit miring ke kanan | ✅ |
| `side`        | Dari samping | ⚠️ Hanya valid jika silhouette rambut jelas & anchor terlihat |
| `front`       | Dari depan | ❌ INVALID untuk length/volume |
| `unknown`     | Tidak dapat ditentukan | ❌ INVALID |

**Aturan validitas side/back_left/back_right:**
- Diterima jika: sebagian besar rambut terlihat, silhouette cukup jelas, ujung rambut dapat diamati, reference body/head masih terlihat, tidak ada occlusion berat.
- Jika viewpoint=front/unknown → `ungradable=true`, `ungradable_reason=invalid_viewpoint`.

---

## 4. Hair Length (Level 2 — straight/wavy only)

**Hanya dianotasi jika hair_type = straight atau wavy.**

Taxonomy pilot (anchor-based, mengadopsi Hairmony-style):

| Kelas | Anchor (ujung rambut relatif terhadap) | UI Display |
|---|---|---|
| `short`     | Di atas garis bahu (≤ level dagu) | "Pendek" |
| `shoulder`  | Sekitar level bahu | "Sekitar Bahu" |
| `mid_back`  | Bahu → belum lewat tengah punggung | "Punggung Tengah" |
| `long`      | Melewati tengah punggung | "Panjang" |

**Aturan:**
- Tentukan berdasarkan posisi **ujung rambut** relatif terhadap **anatomical anchor** (bahu/punggung).
- Jika ujung rambut tidak terlihat (terpotong frame, tertutup) → `ungradable=true`.
- Jika anchor (bahu/punggung) tidak terlihat → `ungradable=true`.
- Jangan menggunakan persepsi "rambut terlihat pendek" tanpa anchor.

**Borderline cases:**
- Ujung tepat menyentuh bahu → `shoulder`.
- Ujung sedikit di bawah bahu (masih dalam toleransi visual setara lebar wajah) → `shoulder`.
- Ujung jelas di bawah bahu → `mid_back`.
- Ujung tepat di tengah punggung → `mid_back` (bukan `long`).

---

## 5. Visual Volume / Apparent Thickness (Level 2 — curly/kinky only)

**Hanya dianotasi jika hair_type = curly atau kinky.**

**⚠️ PROVISIONAL TAXONOMY — BELUM TERVALIDASI.**

| Kelas | Deskripsi (PROVISIONAL) | UI Display |
|---|---|---|
| `low`    | Massa/silhouette rambut kecil, tipis | "Tipis" |
| `medium` | Massa/silhouette sedang | "Sedang" |
| `high`   | Massa/silhouette besar, mengembang, padat visual | "Tebal/Mengembang" |

**Definisi:**
> Seberapa besar massa/silhouette rambut terlihat pada static image.

**DILARANG:**
- Jangan klaim ini mengukur **physical strand thickness** atau **physical hair density**.
- Jangan klaim ini mengukur jumlah helai rambut.

**Aturan:**
- Evaluasi berdasarkan visual area/spread rambut relatif terhadap kepala/wajah.
- Jika rambut tertutup/terpotong sehingga massa tidak dapat dinilai → `ungradable=true`.
- Catat ketidakpastian di notes.

---

## 6. Ungradable

Image ditandai `ungradable=true` jika salah satu kondisi:

| Reason | Kondisi |
|---|---|
| `invalid_viewpoint`         | Foto dari depan/unknown; informasi visual tidak cukup untuk length/volume |
| `insufficient_visibility`   | Ujung rambut tidak terlihat, atau anchor (bahu/punggung) tidak terlihat |
| `severe_occlusion`          | Rambut tertutup signifikan oleh tangan/aksesori/orang lain |
| `ambiguous`                 | Annotator tidak dapat memutuskan kelas dengan keyakinan |
| `other`                     | Alasan lain (jelaskan di notes) |

**Aturan:**
- Jika `ungradable=true`, `conditional_attribute.value` harus `null`.
- Jangan menebak kelas ketika image ungradable.
- Tandai `ungradable_reason` dengan salah satu nilai di atas.

---

## 7. Confidence

| Level | Kondisi |
|---|---|
| `high`   | Endpoint dan anatomical anchor terlihat jelas; keputusan mudah |
| `medium` | Masih dapat dikategorikan tetapi boundary agak ambigu |
| `low`    | Keputusan dibuat tetapi visual evidence lemah |
| —        | Jika evidence terlalu lemah → gunakan `ungradable`, BUKAN `low` |

**Aturan:** Jangan menggunakan `low` sebagai pengganti `ungradable`.

---

## 8. Visibility Checklist

Untuk setiap image, annotator menandai visibility:

| Field | Ya jika terlihat |
|---|---|
| `hair_ends`  | Ujung rambut terlihat jelas (tidak terpotong) |
| `shoulder`   | Garis bahu terlihat (tidak tertutup rambut/pakaian) |
| `upper_back` | Punggung atas terlihat |
| `mid_back`   | Punggung tengah terlihat |

**Aturan:** Jika semua False → kemungkinan `ungradable=true` (insufficient_visibility).

---

## 9. Independence Rules (Anotator A & B)

- Annotator A dan B melihat gambar yang SAMA, urutan yang SAMA.
- Annotator TIDAK boleh melihat label annotator lain.
- Annotator TIDAK boleh melihat Gemini/geometric/pseudo-label/model prediction.
- Annotator menggunakan guideline yang SAMA (pilot-v1).

---

## 10. Schema

Lihat `README.md` untuk schema JSON lengkap.

---

## 11. Limitations

- Taxonomy ini adalah **PILOT**, bukan final.
- Validitas ditentukan oleh inter-annotator agreement (κ).
- Jika κ rendah → revisi taxonomy/guideline → pilot ulang.
- Volume taxonomy (`low/medium/high`) bersifat **PROVISIONAL** — belum ada preseden literatur kuat.
- Tidak ada klaim panjang dalam cm atau strand thickness fisik.
