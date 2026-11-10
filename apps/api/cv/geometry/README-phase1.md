# Fase 1 — Audit kesiapan dataset

`curate_dataset.py` mengaudit kohort `figaro1k` dan `new_dataset` secara read-only. Folder backup resolusi rendah dan kandidat pemulihan tidak dimasukkan. Label folder `sangat keriting` dinormalisasi menjadi `sangat-keriting` hanya dalam laporan, tanpa merename sumber.

## Menjalankan

Dari root repositori:

```powershell
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/curate_dataset.py --help
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/curate_dataset.py
```

Output default: `apps/api/cv/geometry/reports/phase1/`:

- `dataset_curation.json`: hasil per citra dan ringkasan per kohort/kelas.
- `records.csv`: pemeriksaan teknis dan status review.
- `duplicate_candidates.csv`: pasangan eksak atau kandidat kemiripan untuk review manual.

Output yang sudah ada ditolak; `--overwrite` hanya mengganti tiga laporan tersebut. Dataset tidak disalin, dipindah, diubah, atau diberi split. Kedua direktori kohort harus tersedia. Seed default 42 dicatat untuk reproduksibilitas; audit penuh tidak melakukan sampling acak.

## Metode dan batasan

- Decode gambar, orientasi EXIF, resolusi sisi pendek minimum 224 px.
- SHA-256 berkas mentah dan piksel RGB beserta dimensi untuk konten eksak.
- dHash 64-bit (perbandingan kolom bertetangga setiap baris) dan pHash 64-bit (DCT 32×32, blok frekuensi rendah 8×8).
- Pasangan kandidat bila hash eksak cocok atau jarak Hamming dHash/pHash ≤6. Ambang ini heuristik, belum dikalibrasi untuk dataset rambut; dapat menghasilkan false positive dan melewatkan crop/flip/perubahan lain.
- Konflik label menandakan dua folder kelas berbeda, bukan keputusan kelas mana yang benar.
- Tidak membuktikan identitas subjek, hak penggunaan, kecocokan label, atau kelayakan training. Metadata review tetap belum disetujui; hasil audit teknis tidak boleh dianggap penolakan atas kurasi manusia yang sudah dilakukan.

## Hasil aktual — 10 November 2026

### 1. Audit Awal (389 citra)
| Kohort | Lurus | Bergelombang | Keriting | Sangat-keriting | Total | Decode gagal | Sisi pendek ≥224 |
|---|---:|---:|---:|---:|---:|---:|---:|
| figaro1k | 89 | 86 | 72 | 5 | 252 | 0 | 252 |
| new_dataset | 33 | 31 | 28 | 45 | 137 | 0 | 137 |
| **Total** | **122** | **117** | **100** | **50** | **389** | **0** | **389** |

### 2. Keputusan Review Duplikasi & Konflik Label
Berdasarkan tinjauan visual via UI anotasi dan konfirmasi:
- **Pasangan #1**: `figaro1k/keriting/00320.jpg` dan `new_dataset/bergelombang/download (6).jpg` adalah duplikat. Berkas B (`download (6).jpg`, resolusi 600×800) dipertahankan dengan label disetujui **`keriting`**; berkas A dikeluarkan.
- **Pasangan #2**: `figaro1k/lurus/00010.jpg` dan `new_dataset/keriting/download (4).jpg` berbeda (false-positive pHash/dHash). Keduanya dipertahankan dengan label masing-masing (**`lurus`** dan **`keriting`**).
- **Pasangan #3, #4, #5**: Tiga berkas identik/duplikat pada `new_dataset/sangat keriting` (`download (13).jpg`, `images (11).jpg`, `images (4).jpg`) **dikeluarkan ketiganya** dari dataset kurasi.

Artefak review: `duplicate_review_decisions.json`, `duplicate_review_decisions.csv`, dan `duplicate_review_resolution.json`.

### 3. Manifest Terkurasi & Split Train/Val/Test (`build_curated_split.py`)
Skrip `build_curated_split.py` membangun manifest kurasi deterministik (`seed=42`) dengan split stratified per-kelas:
- Total citra terkurasi: **385 citra** (389 dikurangi 4 berkas duplikat).
- Seluruh 385 citra memiliki sisi terpendek **≥ 224 px**.
- Berkas sumber asli di `dataset/` **tidak diubah, dihapus, atau dipindahkan**.

| Kelas | Total | Train (70%) | Val (15%) | Test (15%) |
|---|---:|---:|---:|---:|
| Lurus | 122 | 85 | 18 | 19 |
| Bergelombang | 116 | 81 | 17 | 18 |
| Keriting | 100 | 70 | 15 | 15 |
| Sangat-keriting | 47 | 33 | 7 | 7 |
| **Total** | **385** | **269 (69.9%)** | **57 (14.8%)** | **59 (15.3%)** |

### 4. Status Gate Fase 1
- **Kriteria**: Jumlah citra valid untuk task ≥ 150.
- **Aktual**: **385 citra** tervalidasi teknis dan lolos kurasi duplikasi.
- **Status Gate**: **LULUS** (`phase1_decision.json`).

Artefak yang dihasilkan:
- `curated_manifest.json` & `curated_manifest.csv`
- `phase1_decision.json`

## Langkah Berikut (Fase 2)

1. Persiapkan dataset segmentasi rambut (UNet): verifikasi ketersediaan mask ground-truth (Figaro-1k PBM/PNG masks).
2. Latih model segmentasi rambut (UNet) dengan split subjek tanpa kebocoran data.
3. Evaluasi metrik segmentasi (target IoU ≥ 0.75, Dice ≥ 0.85).
4. Export model ONNX `hair_segmentation.onnx` ke `geometry/weights/`.
