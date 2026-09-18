# common/ — Utilitas Bersama

Kode yang dipakai bersama oleh `viewpoint/`, `hair_type/`, `hair_length/`.

## Isi

| File | Fungsi |
|---|---|
| `constants.py` | Label tetap semua task + path config |
| `preprocessing.py` | Pipeline gambar (resize, normalize ImageNet, CLAHE opsional) |
| `io_utils.py` | Helper load image, baca/tulis JSON, list dataset |

## Prinsip

- **Label tetap** — nama kelas tidak boleh berubah sembarangan (dipakai di CV, RAG, UI).
- **Preprocessing konsisten** — semua modul pakai pipeline yang sama agar inference cocok.
- Normalisasi ImageNet: `mean=[0.485,0.456,0.406]`, `std=[0.229,0.224,0.225]`.
