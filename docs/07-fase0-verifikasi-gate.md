# 07 — Fase 0: Kelayakan Landmark untuk Geometri

> Dokumen ini menguji kelayakan landmark MediaPipe Pose sebagai prasyarat **geometri yang bergantung pose** (misalnya panjang relatif terhadap bahu). Hasilnya bukan gate bagi klasifikasi jenis rambut atau segmentasi, yang dapat berjalan tanpa landmark pose.
>
> Detail tahapan proyek ada di [roadmap CV](./08-roadmap-cv-lengkap.md). Catatan eksekusi terdahulu tersimpan utuh dalam `docs/archive/cv-2026-11-10/07-fase0-verifikasi-gate.md`.

## Tujuan dan batasan

Ukur apakah bahu dan landmark kepala cukup tersedia untuk membangun fitur geometri pada kohort yang sedang dipertimbangkan. Kegagalan pose tidak membatalkan kegunaan gambar untuk klasifikasi rambut atau segmentasi. Tidak menyimpulkan bahwa landmark pengembalian model adalah anatomi yang benar tanpa validasi manusia.

## Rencana uji ringkas

1. Jalankan pose estimator deterministik pada setiap gambar kohort yang diusulkan; simpan identitas citra, status keluaran, visibility, dan koordinat ternormalisasi.
2. Laporkan jumlah seluruh citra, jumlah pose terdeteksi, keberhasilan kedua landmark bahu, dan keberhasilan landmark kepala secara terpisah; gunakan denominator seluruh kohort dan nyatakan denominator dengan jelas.
3. Pilih sampel berstrata hasil sukses/gagal untuk pemeriksaan visual manusia. Nilai posisi anatomis landmark secara eksplisit; jangan memakai visibility model sebagai ground truth.
4. Ukur kestabilan rasio hanya pada subset pose yang lolos, dan nyatakan bahwa estimasi tinggi kepala dari landmark wajah/proxy adalah diagnostik, bukan ukuran anatomi tervalidasi.
5. Putuskan hanya apakah geometri bergantung-pose layak diuji berikutnya. Hasil gagal/bersyarat menghentikan atau mengubah geometri, bukan menghapus gambar dari alur type/segmentasi.

## Hasil yang tersedia (seluruh kohort)

Hasil lite aktual mencakup 252 gambar Figaro-1k terkurasi dan 137 gambar kohort pemulihan, total **389**:

| Kohort | Gambar | Kedua bahu tersedia | Landmark kepala/proxy tersedia |
|---|---:|---:|---:|
| Figaro-1k terkurasi | 252 | 141 | 143 |
| Kohort pemulihan | 137 | 73 | 74 |
| **Total** | **389** | **214** | **217** |

Ini adalah hitungan ketersediaan keluaran pada uji lite, bukan hasil validasi akurasi anatomis dan bukan bukti bahwa gate historis telah lulus. Hasil per kohort tetap dilaporkan terpisah; agregat tidak menggantikan evaluasi kualitas landmark.

## Keputusan dan langkah lanjut

Kelayakan geometri pose **belum dibuktikan sebagai lulus** berdasarkan hitungan ini. Sebelum memakai fitur pose untuk prediksi panjang/volume, lakukan validasi landmark manusia, tinjau kegagalan dan hitung metrik dengan definisi/denominator yang ditetapkan sebelumnya. Bila tidak memadai, tunda atau ganti hanya tahap geometri tersebut. Hair type CNN dan segmentasi tetap dapat dievaluasi secara independen pada gambar yang sesuai.

## Catatan cakupan

Hasil back-view berukuran 44 gambar beserta keputusan dan rencana gate versi sebelumnya merupakan catatan historis dan dipertahankan di arsip, bukan status aktif. Dokumen ini tidak menyatakan gate lama lulus.
