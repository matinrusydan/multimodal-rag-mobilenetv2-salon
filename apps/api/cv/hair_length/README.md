# hair_length/ — Klasifikasi Panjang Rambut (TAHAP 2)

Modul klasifikasi **panjang rambut** (4 kelas) dari foto back-view.

## Kelas

`pendek` · `pendek-menengah` · `menengah` · `panjang`

(Nama tetap — konsisten dengan RAG prompt & UI.)

## Isi

| File | Fungsi |
|---|---|
| `train.py` | Latih CNN panjang rambut (efficientnet_v2_s / ConvNeXt-Tiny) |
| `bench_backbones.py` | Bandingkan backbone (15 arsitektur) |
| `compare_backbones.py` | Validasi multi-seed backbone final |
| `build_dataset.py` | Bangun dataset panjang dari label |
| `evaluate.py` | Evaluasi model |
| `labels.py` | Definisi label tetap |

## Backbone Champion

- **efficientnet_v2_s** (0.8293 ± 0.0086, 3-seed, juara benchmark)
- Alternatif: ConvNeXt-Tiny (0.8177 ± 0.0163)
- Output: `hair_length/weights/hair_length.onnx`

## Alur

```powershell
cd C:\laragon\www\RAG-salon\apps\api\cv
& ".venv\Scripts\python.exe" hair_length\bench_backbones.py
& ".venv\Scripts\python.exe" hair_length\train.py
& ".venv\Scripts\python.exe" hair_length\evaluate.py
```

## Catatan

- Training data **hanya foto back-view** (hasil filter `viewpoint/`).
- Benchmark & model existing ada di `../weights/`.
