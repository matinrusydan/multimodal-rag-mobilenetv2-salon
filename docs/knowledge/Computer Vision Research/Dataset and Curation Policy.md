# Dataset dan Kebijakan Kurasi

Audit statis: **6 November 2026**. Seluruh sumber tetap dipertahankan; penulisan dokumentasi tidak mengubah dataset, label, atau model.

## Lokasi dan status

| Direktori | Peran | Status |
|---|---|---|
| `apps/api/cv/dataset/figaro1k/` | Dataset dasar terkurasi | 252 file teramati saat audit; tetap base, bukan diganti Pinterest. |
| `apps/api/cv/dataset/new_dataset/` | Arsip mentah koleksi awal | Read-only; perlu recovery/resolusi dan QC. |
| `apps/api/cv/geometry/source_recovery/` | Manifest recovery dan kandidat terisolasi | Belum menjadi ground truth atau split final. |
| `source_recovery/manual_reverse_search/` | Thumbnail pencarian ulang manual | Bukan data siap training. |
| `source_recovery/manual_recovered_originals/` | Hasil recovery manual | Perlu review sumber, label dan dedupe. |
| `source_recovery/pinterest_candidates/` | Kandidat Pinterest | Belum boleh auto-merge. |
| `source_recovery/recovered_candidates/` | Kandidat hasil recovery lain | Status kandidat sampai approval. |

Jumlah kelas dari memory sebelumnya tidak dihitung ulang dalam audit ini; 252 adalah hitungan file, bukan penilaian mutu/lisensi.

## Alur koleksi terkontrol

1. Pertahankan Figaro1k sebagai base dan data lama tetap utuh.
2. Untuk Pinterest, gunakan `download_public_pin.py` atau `collect_related_pins.py` di `geometry/`; panduan pada `README-pinterest.md` dan `README-related-pins.md`.
3. Login manual di browser/profil khusus. **Jangan memasukkan token/cookie ke script atau percakapan.**
4. Batas persetujuan koleksi terkait adalah **maksimal 40 gambar**. Keberadaan script tidak membuktikan run interaktif sudah dilakukan.
5. Simpan kandidat terpisah beserta provenance sumber.
6. Periksa hak penggunaan, resolusi, label hair type, bagian rambut yang diperlukan task, ikatan, watermark dan kualitas.
7. Lakukan exact/near-duplicate check lintas seluruh sumber **sebelum** split.
8. Group subject/duplicate family, baru buat train/val/test dengan seed tetap.
9. Merge hanya melalui manifest keputusan yang dapat diaudit, bukan menyalin kandidat langsung ke base.

## Hal yang belum selesai

- Run interaktif collector ≤40 belum terverifikasi.
- Approval kandidat recovery/Pinterest belum selesai.
- Hak distribusi setiap gambar belum terbukti hanya karena bisa diunduh.
- Manifest deduped dan split final pipeline geometris belum ditemukan di target roadmap.

Dataset lokal diabaikan Git sesuai kebijakan repository saat ini. Keberadaan data lokal bukan jaminan checkout baru dapat mereproduksi eksperimen; dokumentasikan sumber/prosedur dan sediakan data hanya bila izin jelas.
