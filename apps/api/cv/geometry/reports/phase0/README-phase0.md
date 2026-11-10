# Laporan kelayakan pose — Fase 0

Model: `lite` (SHA-256 `59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`); seed: `42`; gambar dievaluasi: 504.

## Ringkasan kohort (hasil skrip ini)

| Kohort | N aktual | Min dimensi (px) | Semua dimensi ≥224 | Pose | Bahu | Kepala |
|---|---:|---:|---:|---:|---:|---:|
| figaro1k | 252 | sisi pendek minimum 227 | 252 | 0.567 | 0.560 | 0.567 |
| new_dataset | 137 | sisi pendek minimum 224 | 137 | 0.540 | 0.533 | 0.540 |
| new_dataset_backup_lowres | 115 | sisi pendek minimum 150 | 1 | 0.443 | 0.443 | 0.443 |

| Gate kanonik | N | Rate bahu | Rate kepala | Status |
|---|---:|---:|---:|---|
| Figaro + new_dataset | 389 | 0.5501285347043702 | 0.5578406169665809 | NOT_MET |

Angka ringkasan di atas dihasilkan dari eksekusi evaluator yang sama. Tabel detail per kelas dan interval Wilson 95% (unconditional serta conditional pada pose terdeteksi) tersedia di JSON.

## Batasan dan interpretasi

Skor visibility MediaPipe bukan validasi akurasi anatomi; evaluasi independen manusia belum dilakukan, sehingga gate ini belum tervalidasi penuh.
Pemulihan backup dapat mengubah crop atau adegan, bukan semata resolusi; pasangan berdasarkan nama berkas bukan bukti adegan sama. Backup rendah resolusi terpisah dan tidak termasuk gate kanonik. Tidak ada downsampling sintetis sebagai pengganti backup.

Artefak: `pose_feasibility.json`, `pose_feasibility.csv`, lembar kontak dan overlay per gambar.