# Diagnosis baseline dan titik pemeriksaan label

Tanggal: 20 Oktober 2026. Acuan masih development dan belum dibekukan sebagai gold final.

## Temuan yang benar-benar terukur

BM25 top-5 mendapatkan setiap kelompok bukti wajib yang dianotasi pada 17/20 pertanyaan yang dinilai. Recall macro 0,908; precision macro 0,240; F1 retrieval macro 0,367. Empat pertanyaan tanpa gold retrieval tidak dinilai, bukan dianggap berhasil. Tidak ada generasi atau evaluasi perilaku chatbot.

## Tiga kasus yang memerlukan diagnosis

| Item | Yang terjadi | Keterbatasan diagnosis |
|---|---|---|
| r10: perawatan rambut rusak/bercabang | Bukti kondisioner dan pembatasan panas berada di urutan 11 dan 10, di luar top-5. | Passage terpilih adalah panduan umum. Perlu memeriksa apakah panduan itu cukup langsung untuk menjawab kondisi rusak/bercabang. Kemiripan topik saja bukan bukti penanganan kondisi tersebut. |
| r11: rambut kering/kusam | Kondisioner ditemukan di urutan 2; pembatasan panas di urutan 8. | Kewajiban mengambil keduanya mengikuti redaksi acuan kandidat. Pertanyaan tidak secara eksplisit meminta dua intervensi. Perlu menetapkan apakah pengurangan panas wajib atau hanya pelengkap. |
| r18: harga/durasi blowout dan rambut kering | Record blowout urutan 1; pembatasan panas urutan 5; kondisioner urutan 9. | Bukti harga dan sebagian edukasi sudah ditemukan. Status “tidak lengkap” mengikuti tiga kelompok wajib kandidat, bukan bukti bahwa semua jawaban yang mungkin dari konteks itu pasti salah. |

Kasus r11/r18 memperlihatkan perlunya memisahkan **kelengkapan terhadap jawaban acuan tertentu** dan **kecukupan untuk menjawab kebutuhan pertanyaan**. Keduanya tidak boleh disamakan tanpa rubric yang jelas. Ini bukan alasan mengganti gold setelah melihat skor untuk menaikkan hasil. Simpan label sekarang sebagai versi development, catat alasannya, lalu gunakan aturan penilaian yang sama saat menyusun gold berikutnya.

## Urutan penanganan

1. Audit langsung relevansi passage r10 terhadap kondisi yang ditanyakan. Jika dukungannya tidak cukup, tandai keterbatasan sumber atau gunakan pertanyaan yang cakupannya memang didukung. Jangan langsung menganggap hanya retriever yang salah.
2. Definisikan komponen jawaban inti dan tambahan untuk r11/r18. Jika dua saran diwajibkan, nyatakan kriteria tersebut sejak awal dan sediakan bukti langsung untuk keduanya. Jika satu saran relevan cukup, gunakan kelompok alternatif yang sah; jangan menuntut setiap alternatif sekaligus.
3. Pertahankan perbedaan rambut kering dan rambut keriting. Passage keriting tidak otomatis menjadi alternatif bagi pengguna yang tipenya belum diketahui.
4. Setelah label ditinjau, bekukan versi baru dan jalankan semua pembanding dengan korpus serta label yang identik. Gunakan kasus yang belum dilihat untuk uji final. Jangan mengubah algoritma dan label sekaligus lalu menyimpulkan peningkatan metode.

## Pemeriksaan implementasi

Tes terkait RAG: **55 lulus**, termasuk kontrol baru bahwa gold tidak memengaruhi ranking, missing group dihitung gagal, dan pertanyaan tanpa gold tidak masuk denominator. Ini verifikasi implementasi/protokol, bukan validasi ilmiah dataset.

Korpus, pertanyaan, sumber dan konteks kebijakan diverifikasi terhadap manifest sebelum baseline dijalankan. Input tidak berubah. Skor faithfulness, answer relevancy, akurasi fakta jawaban, efektivitas edukasi, dan kepatuhan kebijakan tidak dihitung karena generasi belum dijalankan.
