# Perbaikan acuan dan integrasi ChatGPT plan

Tanggal: 20 Oktober 2026.

## Hasil pekerjaan

Versi acuan baru ada di `apps/ai/rag/eval/curated-development-v2/`. V1 dan hasil pilot terdahulu tetap utuh.

- r10 diubah menjadi pertanyaan pencegahan kerusakan saat memakai alat panas. Sumber umum sebelumnya tidak cukup langsung untuk menjawab penanganan rambut rusak/bercabang. Pertanyaan lama dipertahankan pada v1; kasus tidak disembunyikan sebagai perbaikan algoritma.
- r11 dan r18 menjadikan bukti kondisioner sebagai inti edukasi rambut kering. Pembatasan panas merupakan informasi tambahan, bukan kewajiban mengambil seluruh saran dalam satu jawaban acuan.
- Label baru disusun asisten atas permintaan perbaikan; bukan anotasi baru dari Matin atau persetujuan dokter. Versi ini masih development.

| Pengujian | Kelengkapan bukti pada item yang dinilai | Interpretasi |
|---|---|---|
| BM25 pada v1 | 17/20 | Diagnosis lama, dengan cakupan/label yang perlu diperbaiki |
| BM25 pada v2 | 19/20 | Perubahan ini merupakan efek perbaikan acuan, bukan metode baru |
| BM25 + seleksi bersumber pada v2 | 20/20 | Perbandingan metode pada input v2 yang sama; tetap eksplorasi development |

Metode seleksi bersumber menggunakan BM25 yang sama (k1=1,5; b=0,75), top-5, dan cuplikan 400 karakter/evidence. Bila aturan mendeteksi pertanyaan campuran, cadangkan satu slot DB (hingga dua jika dua nama layanan dikenali) dan dua slot dokumen. Ranking dokumen memakai kueri setelah nama layanan/kata bisnis dipisahkan; sisa posisi diisi ranking BM25 asli. Korpus, label dan jawaban acuan tidak dibaca oleh aturan pemilihan, selain data katalog yang memang merupakan input.

Ini bukan neural dense retrieval atau metode baru yang telah terbukti secara umum. Dua slot dokumen dipilih setelah inspeksi r18. Korpus hanya 13 evidence, query development berulang, dan belum ada held-out test. Kelengkapan 20/20 mengacu pada kebutuhan faktual yang didukung, termasuk hanya harga untuk sejumlah pertanyaan partial; tidak berarti seluruh jawaban atau perilaku chatbot benar. Empat item tanpa gold retrieval tetap di luar denominator.

## Jalur online yang disiapkan

Pengguna memilih langganan ChatGPT yang sudah ada, tanpa biaya tambahan API. Implementasi menggunakan alur resmi **Sign in with ChatGPT untuk penggunaan paket**. Ini login khusus aplikasi RAG Salon, bukan membaca kredensial yang dipakai Codex. Izin, kelayakan akun/model dan kuota harus diperiksa melalui alur tersebut. Tidak ada fallback ke API key berbayar.

Rujukan OpenAI Docs:

- [Registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in): registrasi dinamis, PKCE, state/nonce, verifikasi ID token dan scope penggunaan paket.
- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference): katalog model akun dan Responses API melalui OAuth.
- [Preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations): stream wajib, store=false, batas parameter/tool.
- [Accounts and sessions](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions): perlindungan token, refresh dan logout. Penggunaan tetap memakai batas paket yang dibagikan antar aplikasi; bukan jaminan kuota tidak terbatas atau akses untuk semua akun.

Implementasi prototipe ini memakai satu akun aplikasi lokal, bukan pengelolaan akun pelanggan publik. Aplikasi tidak mendukung pergantian banyak akun melalui UI. Identitas lain ditolak saat login ulang ke registrasi tersimpan, sehingga token akun berbeda tidak tercampur. Untuk deployment atau banyak akun diperlukan desain akun/otorisasi tersendiri.

Konfigurasi lokal `apps/ai/.env` telah diarahkan ke:

```dotenv
AI_LLM_PROVIDER=chatgpt
RAG_RETRIEVAL_PROVIDER=bm25_source_balanced
AI_CHATGPT_MODEL=
WEB_FALLBACK_ENABLED=false
```

Model sengaja belum dipilih sebelum melihat katalog akun. Embedding Gemini dan koleksi Chroma lama tidak dipakai oleh jalur BM25 ini; tidak ada re-embedding berbayar atau percampuran ruang embedding. Kode Gemini tetap tersedia sebagai kompatibilitas konfigurasi lama, tetapi bukan jalur aktif profil ini. Secret Gemini yang sudah ada tidak dicetak atau dihapus.

Konsultasi publik menggunakan korpus snapshot development v2. Harga/durasi **belum merupakan pembacaan database live**; tanggal dan batas snapshot dimasukkan sebagai konteks. Agent admin mempertahankan tool ringkasan operasional melalui Express. Integrasi publik ke DB live, diskon/histori, SOP pelanggan dan sumber web tambahan tetap pekerjaan tersendiri. Live crawling dinonaktifkan untuk menjaga sumber tetap dapat direproduksi; tidak mengaktifkan crawler lama yang kepatuhan robots-nya belum diperbaiki.

## Menyelesaikan login sebelum tes online

Jalankan dari direktori `C:\laragon\www\RAG-salon\apps\ai`:

```powershell
& '.venv\Scripts\python.exe' -m app.chatgpt_auth login
& '.venv\Scripts\python.exe' -m app.chatgpt_auth models
```

Perintah pertama membuka browser untuk **Continue with ChatGPT**. Pengguna sendiri masuk, memilih akun/workspace dan menyetujui izin aplikasi. Jangan mengirim token atau kata sandi di chat. Callback loopback memakai state, nonce dan PKCE; tanda tangan RS256, issuer, audience, expiry dan identitas ID token diperiksa sebelum sesi aktif. Algoritma tanda tangan selain RS256 ditolak; jika akun memerlukan alur berbeda, adaptasi perlu diverifikasi sebelum akses dinyatakan berhasil.

Setelah daftar model muncul, isi `AI_CHATGPT_MODEL` pada `.env` dengan `slug` yang tersedia untuk akun, lalu restart proses aplikasi. Katalog bukan bukti inferensi berhasil: uji satu permintaan dahulu. Jika izin/model tidak tersedia atau kuota habis, implementasi tidak beralih ke layanan berbayar. Sebelum login, aplikasi menampilkan mode offline; setelah login, kegagalan generasi tetap ditandai dalam trace dan tidak dianggap hasil evaluasi berhasil.

Status tanpa mencetak token:

```powershell
& '.venv\Scripts\python.exe' -m app.chatgpt_auth status
```

Logout:

```powershell
& '.venv\Scripts\python.exe' -m app.chatgpt_auth logout
```

Credential khusus aplikasi disimpan di `%LOCALAPPDATA%\RAGSalon\chatgpt-plan.credentials`, dienkripsi menggunakan Windows DPAPI. Tidak disimpan di browser, repository atau log. Refresh diserialisasi melalui lock file agar rotating token tidak dipakai bersamaan. Login dan status tidak menyalin file auth Codex. Logout mencoba mencabut sesi di origin resmi; bila gagal, status tersebut dijelaskan dan pengguna dapat memutus akses di pengaturan ChatGPT.

## Perubahan program dan pengujian

- `app/chatgpt_auth.py`: login CLI, validasi identitas/scope, penyimpanan terlindungi, refresh, katalog model dan logout.
- `app/rag/chatgpt_plan.py`: transport Responses SSE; hasil hanya sukses setelah response.completed. Role system diubah menjadi developer, parameter preview yang tidak didukung tidak dikirim, dan function tools dikelompokkan dalam namespace. Tidak memakai endpoint backend-api ChatGPT. max_tokens pada caller bukan batas token yang dijamin, karena parameter max_output_tokens tidak didukung jalur preview ini.
- `app/rag/bm25_retrieval.py`: seleksi BM25 lokal dan konteks snapshot/kebijakan.
- `rag_service.py`, `agent_service.py`, `eval_rag.py`: provider ChatGPT dan pemisahan pemilihan LLM dari embedding; trace mencatat provider/model. Retry evaluator menolak perubahan provider/konfigurasi retrieval.
- `prompt_builder.py`: pernyataan kondisi pengguna dapat dipakai tanpa harus berasal dari CV; batas diagnosis/resep, kerahasiaan dan konteks tipe rambut ditegaskan. Tidak mengubah pipeline CV.

Tes terkait terbaru: **68 lulus**. Mencakup autentikasi ditolak jika issuer/audience/nonce/expiry salah, scope tidak diasumsikan dari login identitas, roundtrip DPAPI dengan token uji, refresh yang merotasi token, streaming incomplete ditolak, teks delta tetap terbaca saat envelope penutup kosong, siklus tool admin, dan BM25 tidak memanggil embedding API. Tes memakai mock; bukti akses online dicatat terpisah di bawah.

Pembaruan setelah login pengguna, 20 Oktober 2026: izin paket terverifikasi dan model lokal dikonfigurasi `gpt-6.1-sol` dari katalog akun. Uji pertama menemukan bug pembacaan streaming: teks dikirim melalui delta tetapi tidak diulang dalam output envelope penutup. Program diperbaiki untuk merangkai delta/item, dan tetap mensyaratkan status completed sebelum menganggapnya berhasil. Hasil gagal pertama tidak ditimpa.

Uji RAG online terakhir berhasil (`llm_success`) dalam sekitar 3,88 detik untuk satu pertanyaan harga/durasi Volume Blowout Styling. Jawaban menyebut Rp280.000 dan 55 menit serta menjelaskan bahwa data merupakan snapshot, bukan konfirmasi harga terkini. Laporan: `apps/ai/rag/eval/online-smoke-chatgpt/smoke-20261020-175247040944.json`. Pemeriksaan angka hanya kehadiran literal, bukan penilaian semantik penuh atau skor faithfulness. Ini membuktikan satu permintaan generasi pada saat uji, bukan seluruh agent/evaluator atau jaminan akses model selamanya.

Tidak ada pembelian, fallback API key berbayar, evaluasi massal, migrasi/seed, atau pengubahan index lama. Permintaan online memakai kuota paket ChatGPT yang sudah diizinkan pengguna; bukan berarti tidak mengonsumsi batas penggunaan paket.

## Perbaikan sesi pada proses Turbo

Setelah website dijalankan ulang, endpoint server sempat tetap offline meskipun CLI terhubung. Fallback lokasi sesi sebelumnya menggunakan `.local/share` ketika LOCALAPPDATA tidak tersedia; lokasi ini salah untuk sesi Windows yang disimpan di AppData/Local. Kondisi direproduksi dengan menghapus LOCALAPPDATA pada proses pemeriksaan. Turbo menggunakan penyaringan environment dan konfigurasi task AI sebelumnya tidak meneruskan variabel tersebut.

Lokasi sesi kini ditentukan melalui Windows known-folder API, sehingga konsisten walaupun LOCALAPPDATA/APPDATA/USERPROFILE disaring. Task `ai#dev` juga meneruskan ketiga variabel tersebut secara eksplisit. File kredensial tidak dipindahkan atau disalin; login ulang tidak diperlukan.

Tes terkait terbaru: **69 lulus**. Uji HTTP route `/ai/chat` melalui ASGI pada proses dengan ketiga variabel pengguna dihapus juga berhasil menghasilkan jawaban online, HTTP 200 dan offline_fallback=false. Hasil disimpan di `apps/ai/rag/eval/online-smoke-chatgpt/filtered-environment-route-check.json`. Proses server yang sudah berjalan tanpa autoreload masih memerlukan restart agar memuat kode perbaikan; uji ASGI bukan klaim proses port 5000 yang lama sudah memuatnya.
