# Finalisasi implementasi RAG salon

Tanggal: 20 Oktober 2026. Status: prototipe RAG siap digunakan dan diuji secara lokal. Validasi akhir penelitian dan deployment publik merupakan tahap berbeda.

Pembaruan selanjutnya: seleksi konteks, studi k=1–5, evaluasi jawaban aktual dan optimasi koneksi terdapat pada `docs/20-studi-kualitas-dan-seleksi-konteks.md`. Angka verifikasi di bawah merekam tahap finalisasi sebelumnya, bukan menggantikan laporan studi terbaru.

## Perilaku yang tersedia

- Harga/durasi layanan yang disebut jelas, daftar lengkap, jumlah, filter harga, urutan harga dan perbandingan dijawab langsung dari API katalog. Operasi ini tidak membutuhkan LLM atau embedding.
- Pertanyaan layanan ambigu meminta klarifikasi dan menawarkan pilihan dari katalog yang terbaca. Alias hanya dipakai jika cocok secara tidak ambigu; tidak menebak harga layanan lain.
- Konsultasi perawatan mencari bukti lokal lebih dahulu melalui BM25. Pertanyaan campuran memakai katalog aktif dan dokumen terkurasi. ChatGPT menyusun penjelasan dari bukti tersebut.
- Permintaan dosis/resep, produk internal, dan aturan keramas khusus yang belum tersedia memiliki jawaban kebijakan deterministik. Promo/histori yang belum ada pada API tidak dikarang; harga reguler dapat ditampilkan terpisah. Angka pengguna tidak otomatis disebut salah.
- Tidak ada bukti yang cocok: sistem menyatakan keterbatasan. Kegagalan API tidak mengembalikan harga snapshot. Kegagalan/timeout generasi memberikan kutipan sumber dengan pemberitahuan yang jelas.
- Sitasi yang ditampilkan sesuai atribusi jawaban; potongan sumber sesuai cuplikan di prompt. Kehadiran sitasi belum merupakan verifikasi semantik independen.

## Pemisahan data runtime dan penelitian

Profil lokal memakai `RAG_RUNTIME_CORPUS_FILE=.../rag/runtime/curated-care-v1/corpus.json`, berisi tujuh dokumen edukasi, tanpa record harga snapshot. Bundle mempunyai manifest dan source register yang diperiksa hash-nya sebelum digunakan. Bundle rusak/tidak lengkap menghasilkan 503 yang aman, tanpa membuka path lokal.

`RAG_CORPUS_FILE` tetap menunjuk paket penelitian beku untuk eksperimen Python. Route chat live memakai bundle runtime dan membaca katalog aktif pada setiap permintaan. Kebijakan eksperimen tidak disisipkan sebagai konfigurasi produksi. Paket dan laporan lama dipertahankan.

Untuk menyiapkan bundle versi baru dari paket sumber yang sudah diverifikasi:

```powershell
# Dari apps/ai; gunakan nama versi baru.
.\.venv\Scripts\python.exe -m app.rag.build_runtime_corpus --source rag/eval/curated-development-v2 --out rag/runtime/curated-care-v2
```

Pembuatan bundle tidak memberi persetujuan manusia baru terhadap sumber. Jangan memasukkan seluruh paper algoritma sebagai nasihat pelanggan. Endpoint administrasi ingest Chroma lama tidak otomatis memperbarui bundle BM25; pembaruan bundle dilakukan melalui alur versi ini.

## Fallback web

Fallback runtime sekarang memakai HTTP, tanpa Playwright/Crawl4AI, stealth atau bypass challenge. Hanya host HTTPS dalam allowlist yang dapat diakses. robots.txt diperiksa sebelum artikel; kegagalan membaca aturan menghentikan pengambilan, kecuali 404/410 yang diperlakukan sebagai tidak ada aturan. Redirect artikel diperiksa ulang terhadap allowlist dan robots tujuan.

Ada pembatasan byte, timeout total 12 detik, interval crawl, cache maksimal 32 URL selama satu jam, dan maksimal dua cuplikan web. Pemicu fallback adalah heuristik cakupan kata topik yang belum ada pada bukti lokal, bukan penilaian semantik sempurna atas keterjawaban. Tidak ada artikel default yang tidak sesuai topik. Artikel eksternal diberi status belum ditinjau dan tidak otomatis dipromosikan menjadi dokumen terkurasi atau SOP salon.

Probe eksternal berhasil mengambil satu artikel ketombe sesudah pemeriksaan robots, dengan hash aturan, isi dan waktu akses. Tidak ada artikel yang dimasukkan otomatis ke bundle dalam pengujian ini. Crawling massal lama tetap terpisah dan tidak diperlukan oleh profil runtime minimal.

## Menjalankan

Saat finalisasi, frontend port 3000, Express port 4000 dan layanan RAG port 5000 berhasil dijalankan. Halaman `http://127.0.0.1:3000/consult` dan POST `/api/chat` pada Next.js mengembalikan 200 melalui Express sampai katalog aktif.

Profil RAG saja tersedia di `app.rag_app:app`. Profil ini tidak menyediakan endpoint analisis foto. Aplikasi gabungan yang sudah ada tetap memakai `app.main:app`; kode CV, dataset, bobot dan label tidak diubah.

Lingkungan `.venv-rag` sudah dibuat dan diuji, terpisah dari `.venv` lama:

```powershell
# Dari apps/ai, untuk instalasi baru lingkungan minimal:
python -m venv .venv-rag
.\.venv-rag\Scripts\python.exe -m pip install -r requirements-rag.lock.txt
.\.venv-rag\Scripts\python.exe -m app.rag.preflight --check-catalog
.\.venv-rag\Scripts\python.exe -m uvicorn app.rag_app:app --host 127.0.0.1 --port 5000
```

`requirements-rag.lock.txt` merekam 20 dependensi runtime yang diuji pada Windows/Python 3.13.3. Lingkungan minimal tidak memasang ChromaDB, NumPy, ONNX Runtime, Playwright atau Crawl4AI; `pip check` lulus. Kompatibilitas instalasi di host/Linux tujuan tetap harus diuji pada platform tersebut.

Profil `.env.chatgpt.example` memuat pengaturan nonrahasia yang dibutuhkan. Model memakai izin ChatGPT aplikasi yang sudah diberikan, tanpa fallback API berbayar atau pemakaian kredensial Codex. Deadline generasi total 50 detik. Kehadiran sesi pada preflight dibedakan dari keberhasilan inferensi sebenarnya.

Jalankan API dan frontend dari root pada terminal terpisah:

```powershell
pnpm --filter api start
pnpm --filter web exec next dev --hostname 127.0.0.1 --port 3000
```

Jangan menjalankan dua proses pada port yang sama. Untuk kembali ke seluruh brain engine gunakan perintah aplikasi gabungan yang ada setelah menghentikan profil RAG saja.

## Hasil verifikasi

Laporan berada di `apps/ai/rag/eval/runtime-final-v1/`:

| Pemeriksaan | Hasil |
|---|---|
| Regresi Python RAG | 149 tes lulus; kode CV tidak termasuk cakupan ini |
| Smoke awal dengan model | 16/16 pemeriksaan lulus; dua generasi ChatGPT berhasil |
| Smoke final lingkungan minimal | 17/17 pemeriksaan lulus; tidak ada generasi tambahan |
| Next.js → Express → RAG → katalog | Halaman konsultasi dan POST chat 200; jawaban Blowout Rp280.000/55 menit dengan satu sumber aktif |
| Preflight final | Konfigurasi dan sesi tersedia, tujuh dokumen runtime, enam layanan aktif |
| Dependensi minimal | 20 dependensi runtime; pip check lulus; paket CV/Chroma/browser tidak terpasang |
| HTTP eksternal | Satu artikel berhasil diambil dengan pemeriksaan robots dan provenance |

Perintah regresi dari root: `pnpm test:rag`. Perintah preflight dari root: `pnpm --filter ai rag:check`. Untuk smoke baru:

```powershell
# Dari apps/ai; nama output baru wajib agar hasil lama tidak ditimpa.
.\.venv-rag\Scripts\python.exe -m app.rag.smoke_runtime --check-proxy --out rag/eval/runtime-check-baru.json
# Tambahkan --allow-model hanya bila ingin menjalankan dua generasi menggunakan kuota ChatGPT.
```

Smoke memeriksa route, field literal, filter, dan atribusi sumber; ini bukan skor faithfulness/citation entailment independen atau bukti akurasi seluruh pertanyaan pelanggan. Jumlah 16 dan 17 berasal dari dua eksekusi dengan cakupan berbeda, bukan satu benchmark yang diperbesar diam-diam. Satu probe Next.js melengkapi verifikasi ketiga lapisan aplikasi.

## Batas penelitian yang tetap dicatat

Laporan IR terkini `ir-experiment-v3` mempertahankan hasil komponen sebelumnya: baseline menemukan seluruh kelompok bukti pada 19/20 query ber-gold, alokasi dengan pemisahan kueri pada 20/20. Semua 24 query masih development; acuan revisi, span bukti dan test set independen belum memperoleh persetujuan manusia final. Hasil tersebut tidak dinyatakan sebagai hasil akhir paper.

Harga historis, promo terjadwal dan SOP khusus produk belum tersedia pada sumber API; implementasi merespons keterbatasannya dengan benar. Tidak ada migrasi/seed/perubahan data salon pada finalisasi ini. Tidak dilakukan deployment publik atau klaim bahwa paket gratis suatu host pasti mencukupi. Skor nol, N/A, kegagalan eksekusi dan anotasi yang belum dinilai tetap dipisahkan.
