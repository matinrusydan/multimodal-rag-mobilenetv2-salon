# CV — Modularisasi Pipeline Computer Vision

> Pipeline Computer Vision untuk klasifikasi rambut salon, dipecah menjadi **modul terpisah** agar jelas batas tanggung jawab tiap tahap.

## Arsitektur Modul

```
Foto user (mentah)
      ↓
[ common/ ]        utilitas bersama (preprocessing, constants, io)
      ↓
[ viewpoint/ ]     TAHAP 0 — GATE: vonis posisi (depan/samping/belakang)
      │             hanya "belakang" yang lolos
      ├─ depan/samping → STOP ("mohon foto ulang dari belakang")
      └─ belakang → LANJUT
              ↓
[ hair_type/ ]     TAHAP 1 — jenis rambut (lurus/bergelombang/keriting/sangat-keriting)
[ hair_length/ ]   TAHAP 2 — panjang rambut (pendek/pendek-menengah/menengah/panjang)
              ↓
[ pipeline/ ]      orkestrasi end-to-end + adaptor ke apps/ai
```

## Prinsip

1. **Viewpoint sebagai filter** — dataset training hair_type/length **hanya** foto back-view.
2. **Isolasi modul** — tiap folder mandiri (script + weights + reports sendiri).
3. **Tulis ulang** — modul baru ditulis bersih, bukan copy mentah `scripts/` lama.
4. **Label tetap** — nama kelas konsisten dengan `apps/ai` & UI (lihat `common/constants.py`).

## Modul

| Folder | Peran | Status |
|---|---|---|
| `viewpoint/` | Gate posisi (heuristik + CNN), verifikasi, pengukuran | aktif |
| `hair_type/` | Klasifikasi jenis rambut (CNN) | aktif |
| `hair_length/` | Klasifikasi panjang rambut (CNN) | aktif |
| `common/` | Utilitas dibagi (preprocessing, constants, io) | aktif |
| `pipeline/` | Orkestrasi end-to-end | aktif |

## Model & Path

- Weights ONNX besar tetap di `../weights/` (di-gitignore) atau disalin ke folder modul sesuai kebutuhan deploy.
- Dataset besar (`../dataset/`, `../preprocessed_*`) tetap di lokasi lama.
- `apps/ai` mengonsumsi model via adaptor (`pipeline/adapters.py`).

## Referensi

- Roadmap: `docs/08-roadmap-cv-lengkap.md`
- Kajian matematis: `docs/06-kajian-matematis-referensi.md`
