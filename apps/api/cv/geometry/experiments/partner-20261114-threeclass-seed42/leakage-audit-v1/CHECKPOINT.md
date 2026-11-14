# Checkpoint — keputusan audit dan langkah berikutnya

## Kesimpulan

Eksperimen tiga kelas (lurus, bergelombang, keriting gabungan) selesai dengan val98.25%, test96.61%, test Macro-F1 0.9651, tetapi dua near-duplicate lintas split ditemukan setelahnya. Angka ini hasil historis yang terkontaminasi duplikat diketahui, bukan skor bersih.

## Keputusan pengguna yang tidak perlu ditanyakan ulang

- Pengguna sudah mereview seluruh58 pasangan melalui percakapan:000/001 duplikat dikonfirmasi;010/040/046/047/048/049/054/055/057 jelas berbeda;47 pasangan lainnya tidak otomatis duplikat dan tetap dipertahankan. Kemungkinan orang/sesi sama bukan konfirmasi identitas.
- Jangan meminta anotasi yang sama dua kali. HTML berfungsi untuk melihat/menyesuaikan keputusan, bukan mewajibkan review ulang. Default lama uncertain telah dimigrasikan menjadi retain+reviewed tanpa menimpa edit browser bertimestamp.
- Pengguna menyerahkan pemilihan salinan/split kepada agent. Keputusan: pertahankan gambar evaluasi lama dan kecualikan salinan training dari dua duplikat, bukan menghapus gambar sumber.

## Artefak koreksi terverifikasi

- `curated_manifest_corrected.json`:652 records, **536 train /57 val /59 test**. Dua record train dikecualikan:
  - Supplemental lurus `fa938cdc805c4cde9806945b417dedf6.jpg` (duplikat test `images (8).jpg`).
  - `new_dataset/sangat keriting/download (5).jpg` (duplikat val `download (1).jpg`).
- Manifest lama dan file gambar tidak diubah. Model aktif tetap. Belum training dari manifest koreksi.
- `annotation.html`: Live Server; preview individual tersedia dalam `previews/` (62 JPEG). Keputusan browser disimpan localStorage per origin/port; jangan mengklaim membaca keputusan browser yang belum diekspor.
- Dokumen terkait: FINDINGS.md, USER-REVIEW.md; hasil eksperimen lama ../RESULTS.md dan ../reports/hair_type_eval.json.

## Langkah berikutnya

1. Verifikasi hash/label/split manifest koreksi terhadap manifest sumber, cek byte/pixel duplicate antar-split; jangan mengasumsikan perubahan browser sudah diterapkan pada manifest.
2. Jalankan eksperimen baru **3 kelas**, EfficientNetV2-S pretrained ImageNet, seed42,batch8,35epoch,patience10,LR0.0003; gunakan direktori output baru. Jangan resume checkpoint terkontaminasi. Gunakan `train_and_evaluate(... class_names=['lurus','bergelombang','keriting'])`; CLI trainer default tetap empat kelas. Wrapper train_three_class_experiment.py mengambil input snapshot dan hanya menerima output baru; periksa kompatibilitasnya sebelum memilih jalur.
3. Laporkan Macro-F1/accuracy/per-class/ECE, pilih checkpoint dari val, verifikasi ONNX checker/parity dan hash model aktif. Tidak deployment otomatis.
4. Sebut sebagai perbaikan dua duplikat diketahui, bukan jaminan subject/source independence. Test lama sudah berulang dibuka; test eksternal baru tetap dianjurkan.

## Preferensi memori

Pengguna meminta setiap sesi chat memiliki kesimpulan/checkpoint di Obsidian agar konteks bisa dipulihkan. Utamakan vault + ringkasan repo untuk pekerjaan penting; baca project note/handoff saat melanjutkan, simpan hanya fakta/keputusan/batas terverifikasi, tanpa rahasia.
