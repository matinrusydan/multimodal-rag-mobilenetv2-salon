# Annotation Pipeline — Hierarchical Hair Classification

> **Status:** PILOT v1 SELESAI (A+B, 80 citra) → PILOT v2 SIAP (240 citra) — MENUNGGU ANOTASI v2
> **Scope:** Ground-truth annotation pipeline untuk hair type + conditional attribute (length/volume)
> **Repository:** `apps/api/cv/annotation/`

---

## 1. Tujuan Pipeline

Membangun **ground truth yang valid dan reproducible** untuk klasifikasi rambut hirarkis:

```
INPUT IMAGE
     │
     ▼
VIEWPOINT VALIDATION (back / back_left / back_right / side / front / unknown)
     │
     ├── invalid → ungradable (invalid_viewpoint)
     │
     ▼
HAIR TYPE (straight / wavy / curly / kinky)
     │
     ├── straight / wavy   → LENGTH (short / shoulder / mid_back / long)
     │
     ├── curly / kinky     → VISUAL VOLUME (low / medium / high) [PROVISIONAL]
     │
     └── ungradable → skip conditional
```

**Prioritas:** LABEL VALIDITY > MODEL ARCHITECTURE. Tidak melatih model sebelum GT tervalidasi.

---

## 2. Dataset Source

| Source | N | Used in Pilot? | Notes |
|---|---|---|---|
| **Figaro-1k** | 600 | ✅ Ya (pilot sample: 80) | Real back-view photos; GT hair mask tersedia di zip |
| Kaggle bald | 300 | ❌ Exclude | Botak → length/volume tidak terdefinisi |
| Hairstyle40 | 1470 | ❌ Exclude | Sketches (bukan foto); ujung tidak informatif |
| figaro-extra | 450 | ⚠️ Conditional | Perlu overlap check (`check_figaro_overlap.py`) sebelum dipakai |

Pilot sampling: **80 citra** (20 per hair_type) dari Figaro-1k only, seed=42.

---

## 3. Taxonomy (Pilot v1)

### Hair Type (Level 1)
| EN | ID (dataset) |
|---|---|
| straight | lurus |
| wavy | bergelombang |
| curly | keriting |
| kinky | sangat-keriting |

### Conditional Attribute (Level 2)
| Hair Type | Attribute | Classes | Status |
|---|---|---|---|
| straight / wavy | length | short / shoulder / mid_back / long | Pilot (anchor-based) |
| curly / kinky | visual_volume | low / medium / high | **PROVISIONAL** |

### Viewpoint
`back / back_left / back_right / side / front / unknown`

### Ungradable Reasons
`invalid_viewpoint / insufficient_visibility / severe_occlusion / ambiguous / other`

---

## 4. Roboflow Feasibility Result

**Decision: NOT NECESSARY.** Tkinter local tool dipilih. Alasan:
- Anotasi = classification + metadata nested (viewpoint, visibility, conditional_attribute) — Roboflow export tidak native mendukung schema nested.
- Tkinter sudah tersedia (nol dependensi baru).
- Reproducibility: deterministic seed + stratified sampling lebih mudah lokal.
- A/B isolation: tool lokal memastikan annotator tidak melihat label orang lain.

---

## 5. Annotation Procedure

### Step 1: Generate pilot manifest
```bash
cd C:\laragon\www\RAG-salon\apps\api\cv
& ".venv\Scripts\python.exe" annotation\sample_pilot.py
```
Output: `annotation/ground_truth/pilot_manifest.json` (80 image_id, seed 42).

**Pilot v2 (240 citra, superset 80 lama):**
```bash
& ".venv\Scripts\python.exe" annotation\sample_pilot.py --per-type 60 --seed 43 ^
    --carry-over annotation\ground_truth\pilot_manifest.json ^
    --out annotation\ground_truth\pilot_manifest_240.json
```
Output: `annotation/ground_truth/pilot_manifest_240.json` (240 image_id, 60/type, seed 43).

### Step 2: Run annotation tool (Annotator A)
```bash
& ".venv\Scripts\python.exe" -m annotation.annotation_tool.runner --annotator A
```

### Step 3: Run annotation tool (Annotator B — independent)
```bash
& ".venv\Scripts\python.exe" -m annotation.annotation_tool.runner --annotator B
```

**Untuk pilot v2 (240 citra):** tambahkan `--manifest`:
```bash
& ".venv\Scripts\python.exe" -m annotation.annotation_tool.runner --annotator A --manifest annotation\ground_truth\pilot_manifest_240.json
& ".venv\Scripts\python.exe" -m annotation.annotation_tool.runner --annotator B --manifest annotation\ground_truth\pilot_manifest_240.json
```
Output v2: `annotator_A_p240.json`, `annotator_B_p240.json` (tidak menimpa pilot v1).

**Independence:** Annotator A dan B tidak boleh melihat label satu sama lain. Tool tidak menampilkan pseudo-label/model prediction.

**Validasi & resume:** Tool mencegah menyimpan data tidak lengkap (jenis rambut wajib, alasan wajib jika ungradable, nilai kondisional wajib). Saat dibuka ulang, tool otomatis mengarah ke record yang belum lengkap untuk diperbaiki.

### Step 3b: QC kualitas anotasi (opsional tapi disarankan)
```bash
& ".venv\Scripts\python.exe" annotation\check_annotation_quality.py --annotator A
```
Melaporkan record tidak lengkap, distribusi, dan duplikat. Read-only (tidak mengubah file).

### Step 4: Agreement analysis
```bash
& ".venv\Scripts\python.exe" annotation\analyze_annotation_agreement.py
```
Output: `annotation/reports/annotation_agreement.json` + decision GREEN/YELLOW/RED.
### Step 5 (if GREEN): Geometry signal analysis
```bash
& ".venv\Scripts\python.exe" annotation\analyze_length_geometry_signal.py
& ".venv\Scripts\python.exe" annotation\analyze_volume_geometry_signal.py
& ".venv\Scripts\python.exe" annotation\analyze_hierarchical_signal.py
```

### Step 6 (parallel): Figaro-extra overlap check
```bash
& ".venv\Scripts\python.exe" annotation\check_figaro_overlap.py
```

### Step 7: Visual report (contact sheet A vs B)
```bash
& ".venv\Scripts\python.exe" annotation\make_visual_report.py
```
Output: `annotation/reports/figures/*.png` + `VISUAL_REPORT.md`.

### Step 8: Bandingkan agreement v1 vs v2 (frame identik)
Setelah pilot v2 selesai — menguji apakah revisi guideline v2 menurunkan disagreement pada frame yang sama:
```bash
& ".venv\Scripts\python.exe" annotation\compare_agreement_v1_v2.py
```
Output: `annotation/reports/agreement_v1_vs_v2.json` (+ tabel delta κ).

---

## 6. Sampling

- **N = 80** (20 per hair_type × 4)
- **Seed = 42** (configurable via `--seed`)
- **Source:** Figaro-1k only
- **Independence:** Sampling tidak berdasar pseudo-label (Gemini/geometric/style mapping)
- **Stratification:** per hair_type (lurus/bergelombang/keriting/sangat-keriting)
- **Deterministic:** `random.Random(seed).sample(frames, 20)` per tipe

---

## 7. Agreement Analysis

Menghitung **manual** (tanpa sklearn):
- Raw agreement
- Cohen's kappa (unweighted)
- Linear weighted kappa
- Quadratic weighted kappa
- Confusion matrix (5×5 termasuk ungradable)
- Per-class agreement
- Ungradable rate per annotator
- Confidence distribution
- Disagreement pairs + boundary frequencies

**Decision helper:** GREEN / YELLOW / RED (guideline, bukan scientific law).

---

## 8. Geometry Analysis (E0 Gate)

### Length (straight/wavy only)
- Join human GT ↔ `hair_geometry.json` by frame
- Per fitur: median, IQR, Kruskal-Wallis, effect size (ε²), pairwise Mann-Whitney + Holm
- Fitur: `bbox_aspect, bbox_h, bbox_w, span_ratio, face_ratio, area_ratio, fill_ratio, solidity`

### Volume (curly/kinky only)
- **Exploratory only** (taxonomy provisional)
- Feature distribution, tidak klaim classification

---

## 9. Output Files

```
annotation/
├── README.md                          ← file ini
├── ANNOTATION_GUIDELINE.md            ← guideline annotator
├── sample_pilot.py                    ← generate pilot_manifest.json
├── check_annotation_quality.py        ← QC: deteksi record tidak lengkap
├── make_visual_report.py              ← contact sheet A vs B (analisis kualitatif)
├── compare_agreement_v1_v2.py         ← bandingkan agreement v1 vs v2 (frame identik)
├── analyze_annotation_agreement.py    ← kappa + decision
├── analyze_hierarchical_signal.py     ← cross-level analysis
├── analyze_length_geometry_signal.py  ← E0 gate (length)
├── analyze_volume_geometry_signal.py  ← exploratory (volume)
├── check_figaro_overlap.py            ← dHash near-duplicate
├── annotation_tool/
│   ├── __init__.py
│   ├── app.py                         ← tkinter UI
│   └── runner.py                      ← CLI entry
├── ground_truth/
│   ├── pilot_manifest.json            ← 80 image_id (seed 42)
│   ├── annotator_A.json               ← diisi saat anotasi
│   └── annotator_B.json               ← diisi saat anotasi
└── reports/
    ├── annotation_agreement.json      ← diisi setelah agreement
    ├── hierarchical_signal.json       ← diisi setelah analisis
    ├── length_geometry_signal.json
    ├── volume_geometry_signal.json
    ├── figaro_subject_overlap.json
    └── figures/
```

---

## 10. Reproducibility

- Seed = 42 (configurable)
- Pilot manifest deterministic
- Schema versioned (`pilot-v1`)
- Guideline versioned (`pilot-v1`)
- Semua script punya `--help`
- Tidak ada dependensi baru (tkinter, numpy, PIL, scipy, matplotlib sudah di venv)

---

## 11. Safety Rules

- ❌ Jangan menghapus/overwrite file existing
- ❌ Jangan mengubah `scripts/`, `dataset/`, `preprocessed_*`, `weights/`, `reports/` (existing)
- ❌ Jangan memakai Gemini/geometric/pseudo-label sebagai GT
- ❌ Jangan melatih model sebelum GT tervalidasi
- ❌ Jangan klaim panjang dalam cm atau strand thickness fisik
- ✅ Semua output baru di `annotation/` (isolated)
- ✅ Adapter terpisah untuk integrasi dengan `build_length_dataset.py` (setelah pilot)

---

## 12. Limitations

- Pilot taxonomy (short/shoulder/mid_back/long) **belum tervalidasi** — butuh κ.
- Volume taxonomy (low/medium/high) **PROVISIONAL** — belum ada preseden literatur.
- Tidak ada subject ID → overlap detection via dHash (visual similarity, bukan bukti identitas).
- Figaro-1k 88% face detection rate → 12% image mungkin `ungradable` (face/head tidak terdeteksi → anchor hilang).
- Repo punya 20 file modified + 71 untracked yang belum di-commit — pipeline ini bekerja isolated di `annotation/`.

---

## 13. Next Research Gate

```
DATA AUDIT (DONE)
    ↓
ANNOTATION TOOL (READY)
    ↓
PILOT 80 ← WAITING FOR HUMAN A+B
    ↓
AGREEMENT (κ)
    ↓
┌───────────────┐
│ GREEN?        │
└───────┬───────┘
   YES  │  NO → revise taxonomy → pilot ulang
   ↓
E0 SIGNAL (geometry vs human GT)
   ↓
hierarchical + volume signal
   ↓
FINAL DATASET DESIGN
   ↓
MODEL EXPERIMENT (E1-E3, tahap terpisah)
```

**Status saat ini:** `PILOT SELESAI (A+B) — AGREEMENT & E0 TERHITUNG`

Hasil lengkap: lihat `annotation/reports/HASIL_ANALISIS_PILOT.md`.

**Ringkasan hasil pilot:**
- Length: κ=0.897 (quad 0.969) → YELLOW (mendekati GREEN)
- Volume: κ=0.725 (quad 0.839) → YELLOW (taxonomy provisional)
- Hair type: agreement 0.921
- E0 length: sinyal kuat (bbox_aspect p=8e-6, ε²=0.73)
- E0 volume: sinyal sedang (area_ratio p=0.004, span_ratio p=0.0009)
- **Temuan kritis:** ~27% foto Figaro-1k adalah front-view → perlu viewpoint gate

**Langkah berikutnya:** perbesar pilot, tegaskan guideline viewpoint, revisi taxonomy volume, lalu model experiment (E1).

---

## Revisi v2 (berbasis 17 disagreement pilot v1)

**Guideline:** `ANNOTATION_GUIDELINE_v2.md` (menggantikan v1; v1 tetap diarsipkan).

**Perubahan kunci v2 (ringkas):**
1. **Aturan keras ujung:** jika `hair_ends` tidak terlihat → WAJIB ungradable untuk length.
2. **Rambut diikat/dikuncir/sanggul → WAJIB ungradable** (severe_occlusion).
3. **Front-view:** INVALID untuk length; untuk volume boleh jika massa terlihat.
4. **Tie-break curly vs wavy** eksplisit (loop tertutup = curly).
5. **Volume operasional:** rasio lebar silhouette vs lebar kepala (≤1× low, 1–1.5× medium, >1.5× high).
6. **Boundary length** long↔mid_back dipertegas (pertengahan punggung sebagai batas).

**Manifest pilot v2:** `pilot_manifest_240.json` (240 citra, 60/type, seed 43, superset dari 80 v1).

**Output anotasi v2:** `annotator_A_p240.json`, `annotator_B_p240.json`.
