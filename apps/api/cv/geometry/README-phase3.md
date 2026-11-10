# Fase 3 — Ekstraksi fitur mask (parsial, eksploratif)

## Batas pekerjaan

Gate numerik segmentasi Fase 2 lulus, tetapi gate Fase 0 untuk geometri pose **belum lulus** dan belum memiliki validasi anatomis manusia. Karena itu pekerjaan ini terbatas pada mask, bukan implementasi pipeline panjang/volume berbasis pose. Modul `pose_landmarks.py`, `measure_length.py`, dan `measure_volume.py` ditunda.

Panjang relatif terhadap bahu, head-unit, ketebalan berbasis lebar kepala, dan kelas final **tidak dihitung**. Jarak hidung–telinga bukan tinggi kepala tervalidasi; lebar rambut bukan lebar kepala. Canon tubuh 7,5–8 kepala juga tidak menyelesaikan referensi anatomi pada foto parsial.

## Modul

- `threshold_binary.py`: validasi dan threshold mask/probabilitas; operasi morfologi, pengisian lubang, dan pemilihan komponen terbesar bersifat opsional. Default mempertahankan mask biner tanpa pembersihan tambahan.
- `detect_tied_hair.py`: ekstraksi fitur siluet (luas, bbox, perimeter, circularity, solidity, komponen, kontak tepi). Status keputusan ikatan tetap `uncalibrated`, `tied=null`, `confidence=null`; tidak menolak foto otomatis.
- `extract_mask_features.py`: inferensi ONNX dan ekstraksi fitur pada **train saja**, tanpa mengoptimalkan parameter menggunakan val/test. Output dipisahkan dari laporan Fase 2.
- `test_mask_geometry.py`: uji sintetis untuk operasi mask dan kasus degenerat.

## Menjalankan dari root

```powershell
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/threshold_binary.py --help
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/detect_tied_hair.py --help
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/extract_mask_features.py --help
apps/api/cv/.venv/Scripts/python.exe -m unittest discover -s apps/api/cv/geometry -p "test_*.py"

# Semua 269 citra train; direktori output baru wajib untuk menghindari overwrite
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/extract_mask_features.py
```

Runner mencatat checksum manifest/model, seed 42 (tidak ada sampling acak), identitas citra, fitur, dan alasan atribut panjang/volume tidak tersedia. Delapan overlay awal disimpan untuk inspeksi eksploratif, bukan evaluasi representatif. Input `dataset/` tidak diubah. Default menolak direktori output yang sudah ada; gunakan `--out` dengan direktori baru di `geometry/` untuk pengulangan.

## Hasil aktual ekstraksi training split (10 November 2026)

Ekstraksi berhasil dijalankan pada seluruh **269 citra training split** (`curated_manifest.json`, split == "train") tanpa modifikasi citra sumber, dengan laporan tersimpan di `reports/phase3_mask_features/mask_features.json`:

- **Cakupan kelas:** 85 lurus, 81 bergelombang, 70 keriting, 33 sangat-keriting (total 269).
- **Mask kosong:** **0 dari 269** (model memprediksi siluet rambut pada seluruh citra train).
- **Multi-komponen:** **9 dari 269 (3.3%)** memiliki $>1$ komponen terhubung (disebabkan oleh helai rambut kecil/terpisah yang terdeteksi di luar massa utama).
- **Kontak tepi (border contact):** **50 dari 269 (18.6%)** menyentuh batas tepi citra (atas/samping/bawah), menandakan potensi crop.
- **Distribusi fitur bentuk:**
  - `circularity`: rentang 0.1372 – 0.8636 (rata-rata 0.6865). Rambut bergelombang/keriting dengan ujung bercabang cenderung memiliki perimeter lebih panjang dan circularity lebih rendah.
  - `solidity`: rentang 0.5029 – 0.9924 (rata-rata 0.9457).
  - `hair_coverage`: rentang 8.76% – 80.50% (rata-rata 40.99%).
- **Status keputusan:** Seluruh entri mempertahankan `tied: null`, `confidence: null`, `status: "uncalibrated"`.
- **Status pose:** Seluruh entri menandai `length: {"status": "blocked_phase0_gate", "value": null}` dan `volume: {"status": "reference_not_validated", "value": null}`.
- **Status Gate Fase 3:** **NOT_ASSESSED** (sesuai batasan ilmiah, ekstraksi eksploratif tanpa ground truth ikatan/geometri pose manusia bukan bukti kelulusan gate).

## Interpretasi dan verifikasi

- Mask kosong atau bentuk degenerat harus ditangani tanpa NaN atau pembagian nol. Besaran yang tak terdefinisi disimpan sebagai `null`.
- Luas piksel tidak sama dengan luas kontur. Circularity dan solidity harus menggunakan besaran kontur yang konsisten.
- Kontak tepi adalah indikasi potensi crop, bukan bukti rambut benar-benar terpotong.
- Largest component, hole filling, dan morfologi dapat menghapus helai yang sah atau mengisi latar. Tidak ada klaim pembersihan selalu memperbaiki akurasi.
- Rasio siluet bukan volume fisik, ketebalan anatomi, atau kelas panjang.
- **Gate Fase 3 tetap NOT_ASSESSED**: ekstraksi fitur bentuk bukan bukti ≥90% fitur geometri valid atau korelasi dengan penilaian manusia.

## Prasyarat kelanjutan

1. Review manusia untuk landmark anatomis dan keputusan melanjutkan/mengganti geometri sesuai gate Fase 0.
2. Referensi tinggi/lebar kepala dan titik punggung yang operasional serta tervalidasi; jangan mengganti dengan proxy tanpa bukti.
3. Anotasi ikatan/panjang/ketebalan berizin pada train/validation untuk kalibrasi dan evaluasi terpisah; test tetap tidak dipakai tuning.
4. Evaluasi dampak postprocessing sebelum mengaktifkan default baru.
