# Panduan Anotasi Filtering Manual (Cleaning Dataset)

> Tool: `viewpoint/clean_annotation.py`
> Tujuan: memilih manual gambar harvest yang **LAYAK (KEEP)** vs **BUANG**.

## Konteks

Dataset harvest dari 3 sumber (total **~1400 gambar mentah**):
| Sumber | Jumlah | Isi |
|---|---|---|
| `back_view` | 245 | Wikimedia Commons (back-view) |
| `openverse` | 1067 | Openverse CC (Flickr dll) |
| `huggingface` | 74 | Dataset HF |
| `back_view_clean` | 46 | hasil gate otomatis (bisa ditinjau) |

Banyak gambar **tidak layak** (bukan rambut, objek, hewan, makanan, graphic).
Perlu **filtering manual** untuk memilih yang benar-benar dipakai.

## Cara Pakai

```powershell
cd C:\laragon\www\RAG-salon\apps\api\cv

# 1. Mulai anotasi (semua sumber)
& ".venv\Scripts\python.exe" viewpoint\clean_annotation.py --annotator A

# (opsi) satu sumber saja
& ".venv\Scripts\python.exe" viewpoint\clean_annotation.py --annotator A --source openverse

# (opsi) batasi jumlah dulu untuk uji coba
& ".venv\Scripts\python.exe" viewpoint\clean_annotation.py --annotator A --max 50
```

## Tombol

| Tombol | Fungsi |
|---|---|
| **K** | KEEP (layak dipakai) |
| **H** | BUANG (tidak dipakai) |
| **←/→** | Navigasi |
| Dropdown "Alasan" | Opsional (bukan_rambut, bukan_orang, depan_samping, blur, objek, duplikat) |

## Kriteria KEEP vs BUANG

### ✅ KEEP (layak)
- Foto orang / kepala / rambut
- Sudut **belakang** (atau 3/4 belakang) — fokus rambut
- Rambut terlihat jelas
- Tidak blur berat

### ❌ BUANG (tidak layak)
- **Bukan rambut**: objek (kursi, roti, sisir), hewan (kucing, kuda, burung),
  makanan, bangunan, tanaman
- **Graphic/diagram**: ilustrasi, step-by-step, png transparan
- **Bukan orang**: tempat, tattoo, painting tua
- **Salah sudut**: foto depan/samping jelas (bukan back-view)
- **Blur berat** / tidak jelas

## Simpan Otomatis

- Setiap keputusan langsung tersimpan ke:
  `viewpoint/ground_truth/clean_annotation_<annotator>.json`
- Bisa ditutup & dilanjutkan (resume otomatis)
- File **asli tidak dihapus**

## Setelah Selesai — Terapkan

```powershell
& ".venv\Scripts\python.exe" viewpoint\apply_clean.py --annotators A
```
→ menyalin gambar **KEEP** ke `apps/ai/app/crawler/harvest/manual_clean/`

## Tips

- Kerjakan **per sumber** (`--source openverse`, dst) agar fokus.
- Jika ragu → **BUANG** (kualitas > kuantitas; temuan kita: data kotor merusak model).
- Target: dataset bersih **berimbang** & **label akurat**.
