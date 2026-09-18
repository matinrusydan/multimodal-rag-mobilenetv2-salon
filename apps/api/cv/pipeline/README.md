# pipeline/ — Orkestrasi End-to-End

Menyatukan ketiga modul menjadi satu alur: **foto → gate → (type + length)**.

## Alur

```
Foto mentah
   ↓
[common/preprocessing]  resize + normalize
   ↓
[viewpoint]  gate posisi
   ├─ depan/samping → STOP (retake)
   └─ belakang → LANJUT
        ↓
[hair_type]   → lurus/bergelombang/keriting/sangat-keriting
[hair_length] → pendek/.../panjang
        ↓
hasil JSON → apps/ai (RAG)
```

## Isi

| File | Fungsi |
|---|---|
| `run.py` | Orkestrasi: gate → type → length untuk satu gambar |
| `adapters.py` | Adaptor path/output ke `apps/ai` |

## Alur

```powershell
cd C:\laragon\www\RAG-salon\apps\api\cv
& ".venv\Scripts\python.exe" pipeline\run.py --image path\to\foto.jpg
```

Output: `{viewpoint, valid, hair_type, hair_length, confidence}`
