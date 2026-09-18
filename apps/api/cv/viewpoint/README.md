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
| `build_dataset.py` | Bangun dataset viewpoint dari label manusia (untuk CNN) |
| `train_cnn.py` | Latih CNN viewpoint (efficientnet_v2_s) |
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

## Catatan

- Heuristik saat ini **mentok ~80%** (batas MediaPipe). CNN target >85%.
- Model MediaPipe (`pose_landmarker_lite.task`, `blaze_face_short_range.tflite`, `face_landmarker.task`) ada di `../weights/`.
