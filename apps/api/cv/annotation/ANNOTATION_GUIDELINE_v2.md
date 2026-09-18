# ANNOTATION GUIDELINE — Hierarchical Hair Classification (Pilot v2)

> **Version:** pilot-v2
> **Date:** September 2026
> **Status:** PILOT taxonomy — NOT final.
> **Supersedes:** pilot-v1 (`ANNOTATION_GUIDELINE.md`).
> **Dasar revisi:** 17 disagreement A vs B pada pilot 80 citra (lihat `reports/figures/VISUAL_REPORT.md`).

---

## 0. Ringkasan Perubahan dari v1

Revisi ini menutup celah yang menyebabkan disagreement:

| # | Masalah di v1 | Perubahan di v2 |
|---|---|---|
| 1 | Aturan "ujung tidak terlihat → ungradable" tidak tegas; A menilai meski visibilitas 0/4 | **Aturan keras:** jika `hair_ends` tidak terlihat (visibility.hair_ends = False) → **WAJIB ungradable**, tanpa kecuali |
| 2 | Rambut diikat/terhalang dinilai sebagian annotator | **Rambut diikat/dikuncir/terhalang → WAJIB ungradable** (`severe_occlusion`) |
| 3 | Viewpoint `front` dianggap selalu invalid, tapi annotator tetap menilai volume | **Pemisahan aturan:** `front` = INVALID untuk **length**; `front` = **butuh ujung terlihat** untuk **volume** (lihat §3) |
| 4 | Boundary `curly ↔ wavy` ambigu (B catat "50:50") | **Aturan tie-break eksplisit** untuk curly vs wavy (§2) |
| 5 | Volume `low/medium/high` terlalu subjektif | **Definisi operasional volume v2** berbasis lebar-silhouette relatif (§5) |
| 6 | Boundary length `long ↔ mid_back` tidak tegas | **Aturan pembatas tegas** (§4) |

---

## 1. Purpose

Klasifikasi atribut rambut dari static image secara hirarkis:

1. **Level 1 — Hair Type** (4 kelas): straight / wavy / curly / kinky
2. **Level 2 — Conditional Attribute**:
   - straight/wavy → **relative hair length** (short / shoulder / mid_back / long)
   - curly/kinky → **visual volume / apparent thickness** (low / medium / high) [PROVISIONAL]

**PENTING:**
- Hair length = **relative visual hair-length classification**, BUKAN centimeter.
- Visual volume = **apparent hair mass/silhouette**, BUKAN physical strand thickness.
- **Jangan menebak.** Jika informasi tidak cukup → `ungradable`.

---

## 2. Hair Type (Level 1)

| EN (annotasi) | ID (dataset)  | Definisi operasional |
|---|---|---|
| `straight`  | `lurus`            | Tidak ada kelengkungan signifikan; jatuh tegak. |
| `wavy`      | `bergelombang`    | Lengkung lembut/berombak, **tanpa coil/loop tertutup**. |
| `curly`     | `keriting`        | Coil/spiral **terdefinisi** — terlihat loop atau gelombang berulang rapat. |
| `kinky`     | `sangat-keriting` | Coil sangat rapat (zig-zag/afro), tekstur tinggi, mengembang. |

### Aturan tie-break (BARU di v2):
- **wavy vs curly (paling sering ambigu):**
  - Jika rambut membentuk **lengkung terbuka** yang bisa diluruskan dengan tangan (tidak ada loop tertutup) → `wavy`.
  - Jika terdapat **setidaknya beberapa loop/coil tertutup** yang jelas → `curly`.
  - Jika benar-benar **50:50** dan tidak bisa diputuskan → pilih yang lebih dominan, tulis di notes, set `confidence=low`. **JANGAN** ungradable hanya karena type ambigu — type tetap dapat dinilai selama tekstur terlihat.
- **curly vs kinky:**
  - Coil longgar/terpisah → `curly`. Coil sangat rapat, hampir zig-zag, sering mengembang → `kinky`.
- Jika tekstur **tidak terlihat sama sekali** (blur/terhalang) → `ungradable`, reason `insufficient_visibility`.

---

## 3. Viewpoint (Input Validity) — DIREVISI

| Viewpoint | Deskripsi | Valid untuk LENGTH? | Valid untuk VOLUME? |
|---|---|---|---|
| `back`        | Tegak lurus dari belakang | ✅ | ✅ |
| `back_left`   | Belakang, miring kiri | ✅ | ✅ |
| `back_right`  | Belakang, miring kanan | ✅ | ✅ |
| `side`        | Dari samping | ⚠️ Hanya jika ujung & anchor terlihat | ✅ (silhouette samping justru informatif) |
| `front`       | Dari depan | ❌ **INVALID** (anchor punggung tidak ada) | ⚠️ **Hanya jika ujung/massa terlihat** (§3.1) |
| `unknown`     | Tidak jelas | ❌ INVALID | ❌ INVALID |

### 3.1 Aturan front-view (BARU di v2):
- Untuk **length** (straight/wavy): `front` → `ungradable` (`invalid_viewpoint`). Anchor punggung tidak dapat diamati dari depan.
- Untuk **volume** (curly/kinky): `front` BISA dinilai hanya jika **massa/silhouette rambut terlihat cukup** (mis. afro/kribo besar terlihat dari depan). Jika massa terlihat jelas → boleh nilai volume, catat `viewpoint=front` + confidence. Jika hanya sebagian kecil terlihat → `ungradable` (`insufficient_visibility`).

### 3.2 Aturan side-view:
- Diterima jika sebagian besar rambut terlihat, ujung/anchors terlihat, tanpa occlusion berat.

---

## 4. Hair Length (Level 2 — straight/wavy only) — DIREVISI

Hanya dianotasi jika hair_type = straight atau wavy.

| Kelas | Anchor | UI Display |
|---|---|---|
| `short`     | Ujung di atas garis bahu (≤ level dagu) | "Pendek" |
| `shoulder`  | Ujung sekitar level bahu | "Sekitar Bahu" |
| `mid_back`  | Ujung dari bawah bahu sampai **di atas** pertengahan punggung | "Punggung Tengah" |
| `long`      | Ujung **melewati** pertengahan punggung | "Panjang" |

### Aturan KERAS (BARU di v2):
1. **Jika `visibility.hair_ends == False` → WAJIB `ungradable`** (`insufficient_visibility`). Tidak ada pengecualian.
2. **Jika `visibility.shoulder == False` DAN ujung tidak jelas relatif bahu → WAJIB `ungradable`.** (Kecuali ujung jelas terlalu pendek, mis. di atas telinga.)
3. **Rambut diikat/dikuncir/sanggul → WAJIB `ungradable`** (`severe_occlusion`), karena panjang alami tidak terukur.
4. **Foto `front` → WAJIB `ungradable`** (`invalid_viewpoint`).

### Borderline (tie-break tegas):
- Ujung tepat menyentuh atau sedikit di bawah bahu (dalam ±1 lebar wajah) → `shoulder`.
- Ujung jelas berada di antara bahu dan tengah punggung → `mid_back`.
- Ujung tepat di pertengahan punggung → `mid_back` (belum `long`).
- Ujung **jelas melewati** pertengahan punggung (menuju punggung bawah/pinggang) → `long`.

> **Catatan:** `long` hanya untuk rambut yang ujungnya **benar-benar terlihat** melewati tengah punggung. Jika ujung menjuntai keluar frame → `ungradable` (bukan `long`).

---

## 5. Visual Volume / Apparent Thickness (Level 2 — curly/kinky only) — DIREVISI

Hanya dianotasi jika hair_type = curly atau kinky.

**PROVISIONAL TAXONOMY v2 — belum tervalidasi.**

**Definisi:** seberapa besar **massa/silhouette** rambut terlihat pada static image.

### Definisi operasional v2 (BARU — mengurangi subjektivitas):

Ukur **lebar silhouette rambut relatif terhadap lebar kepala/wajah** pada titik terlebar:

| Kelas | Aturan relatif | UI Display |
|---|---|---|
| `low`    | Lebar silhouette rambut **≤ ~1×** lebar kepala | "Tipis" |
| `medium` | Lebar silhouette **~1–1.5×** lebar kepala | "Sedang" |
| `high`   | Lebar silhouette **> ~1.5×** lebar kepala, atau massa sangat mengembang/penuh | "Tebal" |

> Rasio ini adalah **panduan visual**, bukan pengukuran presisi. Tujuannya menyeragamkan ambang antara annotator. Perhatikan **jarak kamera** mempengaruhi — bandingkan selalu terhadap kepala dalam gambar yang sama.

### Aturan KERAS (BARU):
1. Volume dinilai dari **massa/silhouette**, BUKAN panjang ujung. (Ujung tidak terlihat TIDAK otomatis ungradable untuk volume — beda dari length.)
2. Namun jika **massa rambut sendiri tidak terlihat** (terhalang, tertutup, hanya sebagian kecil) → `ungradable` (`insufficient_visibility`).
3. **Rambut diikat rapat** (massa tertekan/diubah) → `ungradable` (`severe_occlusion`).
4. Jika ragu antara dua kelas yang **bersebelahan** dan tidak bisa diputuskan → pilih yang lebih mungkin + `confidence=low` + notes. **JANGAN** ungradable selama massa terlihat.

### DILARANG:
- Klaim physical strand thickness / hair density / jumlah helai.

---

## 6. Ungradable — DIREVISI

`ungradable=true` WAJIB dipilih jika salah satu kondisi:

| Reason | Kondisi (v2, dipertegas) |
|---|---|
| `invalid_viewpoint`         | Foto `front` untuk **length**, atau `unknown` |
| `insufficient_visibility`   | `hair_ends` tidak terlihat (untuk length); atau massa rambut tidak terlihat (untuk volume) |
| `severe_occlusion`          | Rambut **diikat/dikuncir/sanggul**, atau tertutup tangan/aksesori/orang lain |
| `ambiguous`                 | Hanya jika benar-benar tidak dapat memutuskan **meski semua informasi terlihat** |
| `other`                     | Alasan lain (jelaskan di notes) |

**Aturan:**
- `ungradable=true` → `conditional_attribute.value = null`.
- **`ambiguous` HANYA untuk kasus ekstrem.** Jangan pakai `ambiguous` menggantikan usaha memutuskan kelas type.

---

## 7. Confidence — DIREVISI

| Level | Kondisi |
|---|---|
| `high`   | Ujung/anchors (length) atau massa (volume) terlihat jelas; keputusan mudah |
| `medium` | Dapat dikategorikan, boundary agak ambigu |
| `low`    | Keputusan dibuat, visual evidence lemah (mis. type 50:50, volume di batas) |
| —        | Jika evidence **tidak cukup sama sekali** → `ungradable`, BUKAN `low` |

---

## 8. Visibility Checklist

| Field | Ya jika terlihat |
|---|---|
| `hair_ends`  | Ujung rambut terlihat jelas (tidak terpotong) |
| `shoulder`   | Garis bahu terlihat |
| `upper_back` | Punggung atas terlihat |
| `mid_back`   | Punggung tengah terlihat |

**Aturan penting (BARU):** Untuk **length**, `hair_ends` WAJIB True agar dapat dinilai (lihat §4). Checklist ini bukan formalitas — nilainya menentukan apakah length boleh dinilai.

---

## 9. Decision Flow (BARU)

```
Lihat gambar
  │
  ├─ Sumber/URL jelas? Jika tidak → tandai asal dataset
  │
  ▼
1. Tentukan VIEWPOINT
   - front & task=length → UNGRADABLE (invalid_viewpoint)
   - unknown → UNGRADABLE
   │
   ▼
2. Tentukan HAIR TYPE (straight/wavy/curly/kinky)
   - tekstur tidak terlihat → UNGRADABLE (insufficient_visibility)
   - ragu curly/wavy → tie-break §2, confidence=low
   │
   ▼
3a. Jika straight/wavy → LENGTH
    - rambut diikat → UNGRADABLE
    - hair_ends tidak terlihat → UNGRADABLE
    - front → UNGRADABLE
    - else → pilih short/shoulder/mid_back/long
   │
3b. Jika curly/kinky → VOLUME
    - rambut diikat rapat → UNGRADABLE
    - massa tidak terlihat → UNGRADABLE
    - else → pilih low/medium/high (rasio lebar vs kepala)
   │
   ▼
4. Set CONFIDENCE + VISIBILITY + NOTES
```

---

## 10. Independence Rules (Anotator A & B)

- Gambar & urutan SAMA untuk A dan B.
- Tidak melihat label satu sama lain / pseudo-label / prediksi model.
- Keduanya memakai guideline **pilot-v2** ini.

---

## 11. Limitations

- Taxonomy masih PILOT; validitas via κ.
- Volume taxonomy PROVISIONAL — ambang rasio bersifat panduan.
- Tidak ada klaim cm / strand thickness fisik.
- Pilot v2 akan dijalankan pada 240 citra; jika κ naik → taxonomy makin diterima.
