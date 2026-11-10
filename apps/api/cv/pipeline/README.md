# pipeline/ — Orkestrasi End-to-End

Menjalankan preprocessing dan dua klasifikasi rambut secara berurutan.

## Alur

```
Foto mentah
   ↓
[common/preprocessing]  resize + normalize
   ↓
[hair_type]   → lurus/bergelombang/keriting/sangat-keriting
[hair_length] → pendek/.../panjang
   ↓
hasil JSON → apps/ai (RAG)
```

## Isi

| File | Fungsi |
|---|---|
| `run.py` | Orkestrasi preprocessing, type, dan length untuk satu gambar |
| `adapters.py` | Adaptor path/output ke `apps/ai` |

## Alur

```powershell
cd C:\laragon\www\RAG-salon\apps\api\cv
& ".venv\Scripts\python.exe" pipeline\run.py --image path\to\foto.jpg
```

Output: `{decision, hair_type, hair_length, confidence}`
