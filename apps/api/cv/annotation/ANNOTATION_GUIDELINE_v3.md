# ANNOTATION GUIDELINE — Hierarchical Hair Classification (Pilot v3)

> **Version:** pilot-v3
> **Date:** September 2026
> **Status:** PILOT taxonomy — NOT final.
> **Supersedes:** pilot-v1, pilot-v2.
> **Dasar revisi v3:** catatan annotator pada pilot v2 — alasan "terhalang berat" perlu dipisah (barang vs ikatan rambut), dan "sudut tidak valid" perlu sub-posisi orang.

---

## 0. Perubahan dari v2

| Masalah di v2 | Perubahan di v3 |
|---|---|
| "severe_occlusion" mencampur barang & ikatan | **Dipisah:** `occluded_object` (barang) vs `occluded_tied` (ikatan rambut) |
| "invalid_viewpoint" tidak mencatat posisi orang | **Sub-opsi posisi:** dari depan / samping / belakang-tidak-jelas / lain |
| Kesulitan membedakan rambut diikat | Rambut diikat = **`occluded_tied`**, bukan occluded_object |

---

## 1. Purpose

Klasifikasi hirarkis:
1. **Level 1 — Hair Type:** straight / wavy / curly / kinky
2. **Level 2 — Conditional:**
   - straight/wavy → **relative hair length** (short / shoulder / mid_back / long)
   - curly/kinky → **visual volume** (low / medium / high) [PROVISIONAL]

---

## 2. Hair Type (Level 1)

| EN | ID | Definisi |
|---|---|---|
| `straight` | `lurus` | Tidak ada kelengkungan; jatuh tegak |
| `wavy` | `bergelombang` | Lengkung lembut/berombak, tanpa loop tertutup |
| `curly` | `keriting` | Coil/spiral terdefinisi (loop terlihat) |
| `kinky` | `sangat-keriting` | Coil sangat rapat, tekstur tinggi, mengembang |

**Tie-break wavy vs curly:** ada loop tertutup jelas → `curly`; hanya lengkung terbuka → `wavy`. Jika 50:50 → pilih dominan, `confidence=low`, catat notes.

---

## 3. Viewpoint (Input Validity)

| Viewpoint | Valid untuk LENGTH? | Valid untuk VOLUME? |
|---|---|---|
| `back` | ✅ | ✅ |
| `back_left` | ✅ | ✅ |
| `back_right` | ✅ | ✅ |
| `side` | ⚠️ hanya jika ujung & anchor terlihat | ✅ |
| `front` | ❌ | ⚠️ hanya jika massa terlihat |
| `unknown` | ❌ | ❌ |

> **Temuan dataset:** Figaro-1k banyak berisi foto **samping/depan**. Untuk length, hanya `back/back_left/back_right` yang benar-benar valid.

---

## 4. Hair Length (straight/wavy only)

| Kelas | Anchor |
|---|---|
| `short` | Ujung di atas garis bahu (≤ dagu) |
| `shoulder` | Ujung sekitar level bahu |
| `mid_back` | Ujung dari bawah bahu sampai di atas pertengahan punggung |
| `long` | Ujung melewati pertengahan punggung |

**Aturan KERAS:**
1. `visibility.hair_ends == False` → WAJIB ungradable.
2. Rambut diikat/dikuncir → WAJIB ungradable (`occluded_tied`).
3. Foto `front` → WAJIB ungradable (`invalid_viewpoint` + sub-opsi posisi).

---

## 5. Visual Volume (curly/kinky only) [PROVISIONAL]

| Kelas | Rasio lebar silhouette vs lebar kepala |
|---|---|
| `low` | ≤ ~1× |
| `medium` | ~1–1.5× |
| `high` | > ~1.5× (atau sangat mengembang) |

**Aturan:** dinilai dari **massa/silhouette**, bukan ujung. Rambut diikat rapat → ungradable.

---

## 6. Ungradable — DIREVISI (v3)

| Reason | Kondisi |
|---|---|
| `invalid_viewpoint` | Foto dari sudut tidak valid (**WAJIB pilih sub-posisi**) |
| `occluded_object` | Terhalang **barang/benda/aksesori** (tangan, topi, syal, dsb.) |
| `occluded_tied` | Terhalang karena **rambut diikat/dikuncir** (pola rambut mengumpul di satu titik) |
| `insufficient_visibility` | Ujung (length) atau massa (volume) tidak terlihat |
| `ambiguous` | Benar-benar tidak bisa diputuskan |
| `other` | Lainnya (jelaskan di notes) |

### Sub-posisi untuk `invalid_viewpoint`:
| Sub-opsi | Kapan |
|---|---|
| `from_front` | Foto dari depan |
| `from_side` | Foto dari samping |
| `from_behind_unclear` | Dari belakang tapi sudut tidak jelas |
| `other_angle` | Sudut/posisi lain |

**Catatan penting tentang rambut diikat:**
> Rambut lurus/bergelombang yang **diikat** terlihat "mengumpul di satu titik" (bukan jatuh bebas). Ini **BUKAN** panjang alami → pilih `occluded_tied`. Jangan menilai length dari rambut yang diikat.

---

## 7. Confidence

| Level | Kondisi |
|---|---|
| `high` | Bukti jelas, mudah |
| `medium` | Boundary agak ambigu |
| `low` | Bukti lemah (mis. type 50:50, volume di batas) |
| — | Bukti tidak cukup → `ungradable`, bukan `low` |

---

## 8. Decision Flow

```
Lihat gambar
  ↓
1. VIEWPOINT?
   - front/side/unknown untuk length → UNGRADABLE (invalid_viewpoint) + sub-posisi
  ↓
2. HAIR TYPE?
   - tekstur tak terlihat → UNGRADABLE (insufficient_visibility)
   - ragu curly/wavy → tie-break, confidence=low
  ↓
3. ATRIBUT KONDISIONAL?
   - Ada ikatan rambut (mengumpul) → UNGRADABLE (occluded_tied)
   - Ada barang menutup → UNGRADABLE (occluded_object)
   - Ujung tidak terlihat (length) → UNGRADABLE (insufficient_visibility)
   - else → nilai length / volume
  ↓
4. CONFIDENCE + VISIBILITY + NOTES
```

---

## 9. Independence Rules

- A & B: gambar & urutan sama, guideline v3, tidak saling melihat.

---

## 10. Limitations

- Taxonomy masih PILOT.
- Volume PROVISIONAL.
- Tidak ada klaim cm / strand thickness fisik.
- Dataset Figaro banyak sudut samping/depan → validitas terbatas untuk length.
