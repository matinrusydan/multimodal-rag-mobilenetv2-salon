# Perbaikan klarifikasi layanan dan sitasi konsultasi

Tanggal: 20 Oktober 2026. Dasar: empat hasil pengujian website yang dikirim pengguna.

## Masalah dan perbaikan

Pertanyaan “Berapa biaya treatment itu?” sebelumnya tetap ditebak sebagai Keratin. Konteks percakapan penuh belum dikirim ke backend; contextId sendiri bukan riwayat layanan yang sudah dipilih. Kecocokan hasil retrieval tidak membuktikan layanan yang dimaksud pengguna.

Pada jalur BM25, permintaan harga layanan yang belum teridentifikasi kini ditangani sebagai klarifikasi sebelum pemanggilan model: tanyakan layanan yang dimaksud dan tampilkan opsi katalog snapshot. Tidak menyebut harga atau memilih satu layanan tebakan. Nama penuh dan alias layanan yang dikenali tetap dapat masuk jalur jawaban normal. Aturan ini masih heuristik; bukan kemampuan resolusi referensi percakapan yang sudah lengkap. Katalog yang ditampilkan tetap snapshot, bukan database live.

Daftar sumber sebelumnya merupakan seluruh hasil retrieval, sehingga beberapa record layanan tampil sebagai nama file yang sama dan panduan tak terpakai ikut ditampilkan. Sekarang model diminta memberikan nomor sitasi per pernyataan faktual. Backend menampilkan hanya evidence yang memiliki nomor sitasi valid, menyatukan duplikasi evidence dan menghapus nomor tidak valid. Record layanan diberi judul nama layanan; dokumen edukasi diberi judul bagian dan tautan sumber jika tersedia. Tidak adanya sitasi valid menghasilkan daftar sumber kosong, bukan seluruh hasil retrieval.

**Batas:** sitasi menunjukkan atribusi oleh model, bukan bukti entailment yang diverifikasi independen. Trace tetap menyimpan seluruh konteks aktual agar kualitas sitasi dapat dievaluasi tersendiri. Jawaban kebijakan atau batas informasi tidak dipaksakan memiliki sitasi ilmiah. Mode offline menampilkan sumber cuplikan yang memang ditunjukkan, dengan metadata penggunaan yang berbeda.

## Hasil pemeriksaan route HTTP terbaru

Uji dilakukan melalui ASGI pada kode terbaru; bukan klaim bahwa proses port 5000 yang lama otomatis memuat kode baru.

| Pertanyaan | Hasil |
|---|---|
| Harga dan durasi Volume Blowout Styling | Rp280.000, 55 menit, menyebut snapshot. Satu sumber: record layanan yang benar, sitasi [1]. |
| Harga Hair Spa dan kondisioner rambut kering | Rp325.000 dan edukasi sepanjang batang rambut. Dua sumber: record Hair Spa dan panduan kondisioner, sitasi [1] dan [2]. |
| Biaya treatment itu | Bertanya layanan yang dimaksud dan menampilkan enam opsi; tanpa harga tebakan, tanpa pemanggilan model. Satu sumber katalog opsi. |
| Waktu keramas setelah keratin | Menyatakan instruksi khusus belum tersedia dan meminta konfirmasi staf; tidak menetapkan aturan 48/72 jam. Tanpa daftar sumber retrieval yang tidak dipakai. |

Hasil lengkap: `apps/ai/rag/eval/online-smoke-chatgpt/consult-followups-check.json`. Tiga kasus memakai generasi melalui paket ChatGPT; satu kasus klarifikasi memakai kebijakan deterministik.

Pengujian: **73 tes backend terkait lulus**, termasuk kontrol tanpa tebakan harga, sitasi valid/invalid, deduplikasi, dan pemisahan sumber yang hanya diambil dari sumber yang disitasi. `pnpm --filter web typecheck` juga lulus. Tidak menjalankan lint, migrasi, seed, atau mengubah pipeline CV.

Backend dev yang berjalan tanpa autoreload perlu restart untuk memuat perubahan; frontend perlu refresh agar percakapan baru memakai label sumber terbaru. Pesan lama pada riwayat tampilan tidak ditulis ulang.
