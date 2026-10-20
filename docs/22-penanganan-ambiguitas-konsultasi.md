# Penanganan ambiguitas konsultasi RAG

Tanggal lokal: 21 Oktober 2026. Memperbarui temuan terbuka pada dokumen 21.

## Perilaku yang diperbaiki

1. Jenis kondisioner yang belum disebutkan tidak dipilih berdasarkan peringkat dokumen. Sistem meminta pilihan bilas atau leave-in/tanpa bilas sebelum memberi petunjuk pemakaian.
2. Kalimat tanya seperti “Apakah conditioner tidak perlu dibilas?” tidak dianggap sebagai penetapan jenis leave-in. Negasi tipe yang dikenali juga meminta penjelasan alih-alih disimpulkan otomatis sebagai tipe sebaliknya.
3. Pertanyaan yang menyebut jenis secara eksplisit mengambil keluarga bukti yang sesuai. Normalisasi operasional menyetarakan conditioner/kondisioner dan tanpa bilas/leave-in. Ini perluasan leksikal transparan, bukan embedding baru.
4. Kutipan khusus leave-in tidak dimasukkan sebagai dasar pemakaian kondisioner bilas. Penyaringan berlaku untuk dokumen lokal dan hasil web yang mempunyai penanda jenis eksplisit. Kutipan umum kondisioner juga tidak dijadikan instruksi leave-in tanpa dukungan yang sesuai.
5. Pertanyaan perbedaan/jenis produk boleh mengambil kedua sumber; prompt mengharuskan penjelasan terpisah, bukan mencampur petunjuknya.
6. Harga layanan yang namanya jelas tetap dijawab saat jenis kondisioner masih perlu diklarifikasi. Keterbatasan promo dan histori harga tetap disebutkan bila ditanyakan bersama.
7. Nama layanan tidak dikenal pada pertanyaan campuran meminta pilihan layanan tanpa harga tebakan. Alias yang ambigu tidak dipilih sembarang.
8. “Produk ini”, “krim itu”, dan “treatment itu” tanpa rujukan yang dapat dikenali meminta penjelasan. Durasi mendiamkan kondisioner dibedakan dari durasi layanan salon.

Contoh respons pertanyaan “Berapa harga Signature Hair Spa dan cara memakai conditioner?” memuat harga reguler dari sumber layanan yang dibaca, kemudian meminta jenis kondisioner. Contoh jenis berikutnya ditulis sebagai pertanyaan lengkap agar pengguna dapat melanjutkan tanpa mengandalkan rujukan yang belum diketahui sistem.

## Batas konteks percakapan

Endpoint saat ini menerima pesan, konteks rambut, fitur rambut, dan contextId. contextId mengidentifikasi konteks bukti; bukan penyimpanan riwayat percakapan. Karena itu sistem tidak boleh menganggap “itu” merujuk pesan sebelumnya yang tidak disertakan. Implementasi ini meminta nama/jenis secara eksplisit. Penyimpanan percakapan lintas permintaan belum ditambahkan.

## Validasi

- Regresi lengkap final: 198 tes lulus. Tes khusus ambiguitas: 27/27 lulus, termasuk bahwa kueri perbandingan mengambil kedua sumber dan baseline tetap asli. Laporan JUnit akhir: `apps/ai/rag/eval/ambiguity-v1/python-tests-final.xml`.
- Audit mandiri tanpa model: 13/13 pemeriksaan rute/konteks lulus.
- Audit gabungan: 20/20 pemeriksaan lulus, terdiri dari 13 pemeriksaan lokal dan tujuh permintaan nyata melalui Express ke RAG yang sudah direstart.
- Tidak ada panggilan ChatGPT, API berbayar, atau crawling eksternal pada audit ini. Jalur generasi diuji dengan model tiruan untuk memastikan sumber yang benar masuk prompt; ini tidak menilai makna jawaban generatif.
- Normalisasi dan penyaringan jenis produk hanya pada profil operasional `RAG_CONTEXT_SELECTION=source_scoped`. Profil `all` mempertahankan ranking BM25 sebelumnya sebagai pembanding. Klarifikasi adalah kebijakan aplikasi terpisah dari ranking.

Artefak:

- `apps/ai/rag/eval/ambiguity-v1/offline-audit.json`
- `apps/ai/rag/eval/ambiguity-v1/live-api-audit.json`
- `apps/ai/rag/eval/ambiguity-v1/python-tests.xml`
- `apps/ai/tests/test_care_ambiguity.py`

Audit menguji perilaku rute dan sumber pada kasus development yang terbatas. Tidak ada label test independen atau pengesahan manusia yang dibuat otomatis. Tidak ada klaim bahwa seluruh bahasa alami kini bebas ambiguitas. Kasus yang tercakup sekarang mempunyai perilaku eksplisit: jawab dengan bukti yang sesuai, atau minta klarifikasi. Penanda bahasa yang belum dikenali, sumber dengan judul tidak informatif, serta entailment jawaban generatif masih memerlukan penilaian lebih lanjut.

## Dampak terhadap hasil penelitian

Metrik pada dokumen 20 dan 21 tetap milik konfigurasi/jawaban historis. Angkanya tidak diwariskan sebagai hasil versi penanganan ambiguitas ini. Pertanyaan yang kini meminta klarifikasi tidak boleh dipaksa mendapat skor retrieval seolah-olah sudah mengungkap jenis produk. Evaluasi berikutnya perlu memberi label kebutuhan klarifikasi dan menilai ketepatan keputusan klarifikasi terpisah dari kecocokan bukti pada pertanyaan yang sudah jelas.

Tidak dilakukan migrasi, seed, perubahan CV, atau push Git. Corpus dan anotasi beku tetap utuh; perubahan pencocokan berada pada kode operasional.
