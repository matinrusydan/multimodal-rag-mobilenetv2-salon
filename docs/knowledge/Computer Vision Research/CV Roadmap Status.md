# Status Roadmap Computer Vision

Audit statis: **6 November 2026**. Dokumen otoritatif pekerjaan CV: `docs/08-roadmap-cv-lengkap.md`; gate Fase 0: `docs/07-fase0-verifikasi-gate.md`; angka/rumus: `docs/06-kajian-matematis-referensi.md`. Halaman ini adalah peta status, bukan pengganti gate.

## Temuan lokasi artefak

Dokumen 08 menyebut output `apps/api/cv/geometry/reports/phase0_decision.json` dan `backbone_decision.json`. Checkout saat audit **tidak memiliki** kedua berkas di lokasi target. Namun hasil tersebut **ada di lokasi legacy lain**:

- Uji lite terbaru: kohort 252 menghasilkan 141 keluaran bahu dan 143 kepala/proxy; kohort 137 menghasilkan 73 bahu dan 74 kepala/proxy. Ini ketersediaan keluaran, bukan validasi anatomis. Laporan uji lama 44 gambar dipertahankan di arsip dokumentasi `docs/archive/cv-2026-11-10/`.
- `apps/api/cv/hair_length/reports/backbone_decision.json`: keputusan eksperimen backbone `efficientnet_v2_s` pada hold-out tertentu. Ini bukan kelulusan gate geometri.

Jangan menyebut kedua keputusan itu "tidak ada" secara umum atau memindahkannya ke `geometry/` tanpa provenance.

## Fase dan gate

| Fase | Output target | Status checkout | Syarat lanjut |
|---|---|---|---|
| **0 — Kelayakan pose untuk geometri** | Keluaran landmark dan validasi manusia | **Belum dibuktikan lulus**; hasil lite hanya hitungan ketersediaan | Validasi anatomis sebelum memakai geometri pose; tidak membatasi hair type/segmentasi. |
| **1 — Kurasi data** | data sesuai task, dedupe, split group | **Parsial**; artefak final target `geometry/` belum ditemukan | ≥150 citra valid untuk task, validasi label/kualitas dan leakage prevention. |
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
