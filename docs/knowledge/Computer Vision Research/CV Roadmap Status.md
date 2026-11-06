# Status Roadmap Computer Vision

Audit statis: **6 November 2026**. Dokumen otoritatif pekerjaan CV: `docs/08-roadmap-cv-lengkap.md`; gate Fase 0: `docs/07-fase0-verifikasi-gate.md`; angka/rumus: `docs/06-kajian-matematis-referensi.md`. Halaman ini adalah peta status, bukan pengganti gate.

## Temuan lokasi artefak

Dokumen 08 menyebut output `apps/api/cv/geometry/reports/phase0_decision.json` dan `backbone_decision.json`. Checkout saat audit **tidak memiliki** kedua berkas di lokasi target. Namun hasil tersebut **ada di lokasi legacy lain**:

- `apps/api/cv/viewpoint/reports/phase0_decision.json`: status `KONDISIONAL_FINAL`, 57 sampel keseluruhan (44 back, 8 front, 5 side); back pose detected 28/44, shoulder OK 27/44, head OK 28/44.
- `apps/api/cv/hair_length/reports/backbone_decision.json`: keputusan eksperimen backbone `efficientnet_v2_s` pada hold-out tertentu. Ini bukan kelulusan gate geometri.

Jangan menyebut kedua keputusan itu "tidak ada" secara umum atau memindahkannya ke `geometry/` tanpa provenance.

## Fase dan gate

| Fase | Output target | Status checkout | Syarat lanjut |
|---|---|---|---|
| **0 — Pose feasibility** | Pose/head/shoulder back-view + keputusan | **Kondisional**: shoulder 61.4% dan head 63.6% pada seluruh sampel back; conditional on detected pose lebih tinggi | Gate ≥70% shoulder dan ≥80% head pada back-view belum terbukti lulus; evaluasi sesudah cleaning atau pivot harus dicatat. |
| **1 — Data cleaning/viewpoint** | back-view valid, dedupe, split group | **Parsial**: modul legacy `cv/viewpoint/`; laporan filter target `geometry/reports/viewpoint_filter.json` belum ditemukan | ≥150 citra back-view valid + validasi manusia dan leakage prevention. |
| **2 — Segmentasi UNet** | mask ONNX dan evaluasi | **Belum terbukti** di target `geometry/` | IoU validasi ≥0.75, Dice dan latensi sesuai roadmap. |
| **3 — Geometri head-unit** | fitur panjang/volume dan tied-hair detection | **Belum final**; ada hasil lama di folder CV lain | Ukur rasio relatif tanpa cm absolut, validasi landmark/mask. |
| **4 — Hirarkis/evaluasi** | keluaran 4 kelas + volume dan report | **Belum final** di target `geometry/` | Macro-F1, per-class F1, confusion matrix, ECE, kalibrasi dan audit kasus gagal. |
| **5 — Integrasi** | route aman dan UI | **Belum dimulai di runtime publik** | `/api/analyze` masih 503; baru aktif sesudah gate seluruh fase dan evaluasi lulus. |

## Prinsip evaluasi dan data

- Empat kelas jenis: `lurus`, `bergelombang`, `keriting`, `sangat-keriting`.
- Empat kelas panjang: `pendek`, `pendek-menengah`, `menengah`, `panjang`; definisi geometris internal harus dipetakan ke label kontrak.
- Untuk keriting/kribo: atribut volume `tipis`, `sedang`, `tebal` menurut roadmap.
- Jangan memakai pseudo-label Gemini/quartile sebagai ground truth final.
- Split train/val/test sesudah deduplikasi dan grouping subjek; gunakan seed tetap dan dokumentasikan `--help` script.
- Hasil negatif adalah temuan valid, bukan alasan melewati gate.

Lihat [TASK](../TASK.md) untuk pekerjaan lintas fase dan [Dataset and Curation Policy](./Dataset%20and%20Curation%20Policy.md) untuk batas sumber tambahan.
