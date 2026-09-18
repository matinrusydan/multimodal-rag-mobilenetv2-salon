# hair_type/ — Klasifikasi Jenis Rambut (TAHAP 1)

Modul klasifikasi **jenis rambut** (4 kelas) dari foto back-view.

## Kelas

`lurus` · `bergelombang` · `keriting` · `sangat-keriting`

(Nama tetap — konsisten dengan RAG prompt & UI.)

## Isi

| File | Fungsi |
|---|---|
| `train.py` | Latih CNN jenis rambut (MobileNetV2) |
| `evaluate.py` | Evaluasi model (accuracy, F1, confusion) |
| `labels.py` | Definisi label tetap |

## Model

- Backbone: **MobileNetV2** (val acc ~85.8%, sudah bagus — tidak perlu ganti)
- Input: 224×224, ImageNet normalization
- Output: `hair_type/weights/hair_type.onnx`

## Alur

```powershell
cd C:\laragon\www\RAG-salon\apps\api\cv
& ".venv\Scripts\python.exe" hair_type\train.py
& ".venv\Scripts\python.exe" hair_type\evaluate.py
```

## Catatan

- Training data **hanya foto back-view** (hasil filter `viewpoint/`).
- Model existing ada di `../weights/hair_type.onnx` (dipakai runtime).
