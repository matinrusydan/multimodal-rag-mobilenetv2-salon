# viewpoint/ — Gate Posisi (TAHAP 0)

Modul **filterisasi posisi kamera**. Menentukan apakah foto layak dianalisis:
hanya **belakang** yang lolos; depan/samping → minta foto ulang.

## Filosofi

- **Vonis keras** — sistem selalu memilih 1 dari 3 kelas (depan/samping/belakang).
- User **bisa klarifikasi** bila sistem salah vonis (diteruskan ke RAG).
- **Heuristik dulu** (NON-model, berbasis MediaPipe). CNN menyusul untuk akurasi lebih tinggi.

## Isi

| File | Fungsi |
|---|---|
| `gate.py` | Heuristik: sinyal face+pose → vonis 3 kelas |
| `verify.py` | Tool GUI verifikasi manusia (human-in-the-loop) |
| `measure.py` | Ukur akurasi gate vs verifikasi manusia |
| `pose_check.py` | Uji awal MediaPipe Pose pada foto back-view (Fase 0) |
| `clean_annotation.py` | **Tool GUI cleaning dataset harvested (KEEP/BUANG)** |
| `apply_clean.py` | **Terapkan anotasi KEEP → folder bersih** |
| `build_dataset.py` | Bangun dataset viewpoint dari label manusia (untuk CNN) |
| `train_cnn.py` | Latih CNN viewpoint (efficientnet_v2_s) — **eksperimen** |
| `evaluate.py` | Bandingkan CNN vs heuristik |

## Alur Kerja

```powershell
cd C:\laragon\www\RAG-salon\apps\api\cv

# 1. Jalankan gate heuristik pada dataset
& ".venv\Scripts\python.exe" viewpoint\gate.py --source figaro --all
#    -> viewpoint/reports/viewpoint_predictions.json

# 2. Verifikasi manusia (GUI, ja/benar - tidak - ragu)
& ".venv\Scripts\python.exe" viewpoint\verify.py --annotator A --n 150
#    -> viewpoint/ground_truth/viewpoint_verification_A.json

# 3. Ukur akurasi
& ".venv\Scripts\python.exe" viewpoint\measure.py --annotators A

# 4. (CNN) bangun dataset + latih + evaluasi
& ".venv\Scripts\python.exe" viewpoint\build_dataset.py
& ".venv\Scripts\python.exe" viewpoint\train_cnn.py
& ".venv\Scripts\python.exe" viewpoint\evaluate.py
```

## Kelas

`depan` · `samping` · `belakang` (belakang_nyerong digabung ke belakang)

## Cleaning Dataset Harvested (KEEP/BUANG)

Setelah harvest gambar (Wikimedia/Openverse/HF), gunakan tool ini untuk memilih
manual gambar yang **layak dipakai** (KEEP) vs **dibuang** (BUANG).

```powershell
cd C:\laragon\www\RAG-salon\apps\api\cv

# 1. Anotasi KEEP/BUANG (GUI)
& ".venv\Scripts\python.exe" viewpoint\clean_annotation.py --annotator A
#    -> ground_truth/clean_annotation_A.json

# 2. Terapkan: salin KEEP -> folder bersih
& ".venv\Scripts\python.exe" viewpoint\apply_clean.py --annotators A
#    -> apps/ai/app/crawler/harvest/manual_clean/
```

Shortcut: `K`=KEEP, `H`=BUANG, `←/→`=navigasi. File asli tidak dihapus.

## Catatan

- Heuristik saat ini ~80% (batas MediaPipe). CNN viewpoint **kalah** (~70%) → **heuristik = metode produksi**.
- Model MediaPipe (`pose_landmarker_lite.task`, `blaze_face_short_range.tflite`, `face_landmarker.task`) ada di `../weights/`.
