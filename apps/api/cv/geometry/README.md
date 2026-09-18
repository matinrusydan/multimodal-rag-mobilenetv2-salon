# geometry/ — Pipeline Computer Vision (Fase 0 → 5)

Folder ini berisi seluruh implementasi **Computer Vision baru** untuk proyek RAG-salon: klasifikasi rambut hirarkis berbasis segmentasi + geometri proporsi tubuh.

> **Peta lengkap:** lihat `docs/08-roadmap-cv-lengkap.md`.
> **Prinsip:** folder ini **terisolasi** — tidak mengubah `scripts/`, `dataset/`, `preprocessed_*`, `weights/` lama.

## Struktur

```
geometry/
├── README.md
├── pose_feasibility.py        # Fase 0: uji MediaPipe Pose back-view (GATE)
├── filter_viewpoint.py        # Fase 1 (akan datang)
├── train_segmentation.py      # Fase 2 (akan datang)
├── segment_infer.py           # Fase 2
├── threshold_binary.py        # Fase 3
├── detect_tied_hair.py        # Fase 3
├── pose_landmarks.py          # Fase 3
├── measure_length.py          # Fase 3
├── measure_volume.py          # Fase 3
├── classify_hierarchical.py   # Fase 4
├── evaluate_cv.py             # Fase 4
├── weights/                   # model (pose, segmentation)
└── reports/                   # output JSON + figures
```

## Fase 0 — Verifikasi Gate

**Tujuan:** membuktikan MediaPipe Pose dapat mendeteksi landmark **bahu** pada foto back-view.

```powershell
cd C:\laragon\www\RAG-salon\apps\api\cv
& ".venv\Scripts\python.exe" geometry\pose_feasibility.py --help
& ".venv\Scripts\python.exe" geometry\pose_feasibility.py --per-view 30
```

**Output:**
- `reports/pose_feasibility.json` — hasil lengkap + keputusan gate
- `reports/figures/pose_ok.png`, `pose_fail.png`, `viewpoint_comparison.png`

**Gate:** shoulder detection rate (back-view) ≥ 0.70 DAN head rate ≥ 0.80 → **LULUS**.

## TAHAP 1 — Cleaning Dataset (Gate Viewpoint)

**Tujuan:** membersihkan dataset (buang foto depan/samping) via:
model prediksi viewpoint (paksa pilih 4 kelas) → verifikasi manusia → ukur akurasi.

**Alur (3 script):**

```powershell
# 1. Model prediksi viewpoint (paksa pilih: depan/samping/belakang/belakang_nyerong)
& ".venv\Scripts\python.exe" geometry\viewpoint_gate.py --source figaro --all
#    -> reports/viewpoint_predictions.json

# 2. Verifikasi manusia (human-in-the-loop, MODE PENGUKURAN, sampling cerdas)
& ".venv\Scripts\python.exe" geometry\verify_viewpoint.py --annotator A --n 60
#    -> ground_truth/viewpoint_verification_A.json
#    Anotator menjawab: Benar? [Ya/Tidak/Ragu]. Koreksi OPSIONAL.

# 3. Ukur akurasi model AS-IS (Mode Pengukuran)
& ".venv\Scripts\python.exe" geometry\analyze_viewpoint_accuracy.py --annotators A
#    -> reports/viewpoint_accuracy.json
```

**Filosofi:** ukur dulu kemampuan model apa adanya ("Don't fix what you haven't measured").
Koreksi manusia opsional. Output: dataset bersih + laporan metrik.

**Sinyal gate (v2):** Face Landmarker (fitur wajah asli) + geometri pose (relatif, bukan
visibility mentah) + BlazeFace (pendukung). Model terdeteksi **berhalusinasi** visibility
hidung pada foto belakang — karena itu sinyal geometris dipakai.

## Dependensi

Semua sudah tersedia di venv CV: `mediapipe`, `opencv-python-headless`, `Pillow`, `numpy`, `matplotlib`.

Model yang diunduh otomatis/disediakan:
- `weights/pose_landmarker_lite.task` (+ heavy)
- `weights/blaze_face_short_range.tflite`
- `weights/face_landmarker.task`
