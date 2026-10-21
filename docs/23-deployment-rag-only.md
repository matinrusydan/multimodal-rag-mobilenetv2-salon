# 23 — Deployment RAG-only

## 1. Ruang lingkup dan gate rilis

Target: **Vercel untuk web**, **Railway untuk API + AI + PostgreSQL**. Dockerfile backend
juga dapat digunakan pada Render. Ini bukan deployment seluruh monorepo ke Vercel Functions.

Profil publik memakai BM25, katalog live, seleksi `source_scoped`, dan **ChatGPT melalui izin
aplikasi sendiri**. Tidak ada perpindahan otomatis ke Gemini/API berbayar. CV sementara
unavailable: tombol membuka popup, endpoint analisis mengembalikan 503 tanpa memproses foto.

Bedakan lima status berikut:

1. Tes/typecheck/build source lokal lulus.
2. Image dan dependensi Linux berhasil dibangun/dijalankan.
3. Database, environment, volume, dan jaringan hosting siap.
4. Login ChatGPT di Linux, refresh, dan persistensi session berhasil.
5. Smoke test aplikasi melalui domain HTTPS berhasil.

Source/configuration readiness tidak membuktikan semua gate tersebut lulus. Khusus ChatGPT,
keberadaan kredensial tidak membuktikan akun/model mengizinkan inferensi. Jangan menyatakan
sudah deploy bila hanya build lokal yang selesai.

## 2. Service dan koneksi

```text
Browser ─HTTPS→ Vercel Next.js ─HTTPS→ Express
                                        ├─private→ PostgreSQL
                                        └─private→ FastAPI RAG
                                                     └─private→ Express /api/services
```

| Service | Root build context | Konfigurasi | Liveness | Readiness |
|---|---|---|---|---|
| Web | Workspace, project root `apps/web` | `apps/web/vercel.json` | Halaman aplikasi | Uji alur aplikasi |
| Express | Root repository | `apps/api/Dockerfile`, `apps/api/railway.json` | `/api/health` | `/api/ready` |
| FastAPI | Root repository | `apps/ai/Dockerfile`, `apps/ai/railway.json` | `/ai/health` | `/ai/ready` |
| PostgreSQL | Layanan terkelola | Sesuai provider | Sesuai provider | Koneksi API |

Health platform memakai liveness agar container bisa dimulai sebelum login ChatGPT manual.
**Operator tetap harus memeriksa readiness sebelum menerima trafik publik.** Health tidak
memanggil generasi model. Readiness session hanya pemeriksaan lokal, bukan verifikasi izin
inferensi remote. Jangan mempublikasikan detail readiness internal di dashboard publik.

Gunakan satu replica API dan AI pada tahap awal. Limiter API masih memory-local; session
ChatGPT memakai file locking dan rotating refresh token pada satu filesystem.

## 3. Environment wajib

Contoh kosong tersedia di:

- `apps/web/.env.production.example`
- `apps/api/.env.production.example`
- `apps/ai/.env.production.example`

Isi nilai melalui dashboard/secret manager hosting, bukan commit file `.env`. Jangan membuat
variabel rahasia berawalan `NEXT_PUBLIC_`.

### Web

- `BACKEND_URL`: origin HTTPS Express yang dapat diakses Vercel, tanpa `/api` di akhir.
- `SESSION_SECRET`: random, unik, stabil, minimal 32 karakter. Rotasi memutus sesi pengguna.
- Node.js **22.x**, pnpm **10.15.1**.

Browser tetap memanggil BFF Next.js same-origin. JWT tetap dalam cookie HttpOnly server-side,
bukan localStorage. Tidak perlu cross-domain cookie atau `SameSite=None`.

### Express

- `NODE_ENV=production`, `HOST=0.0.0.0`; gunakan `PORT` yang disuntikkan platform.
- `DATABASE_URL`: connection string PostgreSQL provider, termasuk pengaturan TLS yang diwajibkan.
  Jangan menonaktifkan verifikasi sertifikat sebagai jalan pintas.
- `JWT_SECRET` dan `AI_INTERNAL_TOKEN`: secret berbeda, random, minimal 32 karakter;
  internal token harus sama dengan konfigurasi AI. Default development ditolak di produksi.
- `AI_URL`: origin FastAPI pada jaringan privat, termasuk skema `http://` atau `https://`.
- `CORS_ORIGIN`: origin web yang tepat. CORS bukan autentikasi server-to-server.
- `SECURITY_ENFORCE_ENABLED=true`.
- `TRUST_PROXY=false` secara default; hanya gunakan jumlah hop **1..5** setelah rantai ingress
  platform dipastikan tetap. Jangan gunakan `true` atau mempercayai X-Forwarded-For sembarang.

**Batas atribusi pengguna:** request lewat BFF dapat memakai identitas egress yang sama, sehingga
berbagi bucket rate limit. `trust proxy` saja tidak mengembalikan IP browser melewati semua lapisan.
Tidak ada klaim rate limit per pengguna yang terdistribusi. Untuk trafik publik lebih besar,
gunakan perlindungan ingress/edge yang sesuai atau mekanisme identitas terverifikasi sebelum
mengubah key limiter. Jangan mempercayai header IP kiriman klien tanpa autentikasi.

### FastAPI

- `AI_ENV=production`, `AI_HOST=0.0.0.0`, `PORT` platform.
- `AI_LLM_PROVIDER=chatgpt`.
- `AI_CHATGPT_MODEL`: slug model yang benar-benar tersedia bagi grant aplikasi/akun.
- `AI_INTERNAL_TOKEN`: sama dengan Express; jangan menyediakan service AI secara publik tanpa
  pembatasan ingress. Token internal bukan izin untuk browser memanggil tool admin langsung.
- `API_BASE_URL`: origin Express yang dapat dicapai AI, termasuk skema.
- `RAG_RETRIEVAL_PROVIDER=bm25_source_balanced`.
- `RAG_LIVE_SERVICES=true`.
- `RAG_CONTEXT_SELECTION=source_scoped`.
- `RAG_RUNTIME_CORPUS_FILE=./rag/runtime/curated-care-v1/corpus.json`.
- `XDG_DATA_HOME=/data`, `RAG_KNOWLEDGE_DIR=/data/knowledge`.

Jika jaringan privat hosting mensyaratkan bind IPv6, atur host listener yang sesuai (`::`)
dan periksa koneksi antarlayanan. Jangan menganggap bind IPv4 selalu cocok dengan semua private DNS.

## 4. Build dan filesystem

Dockerfile memakai Node 22 dan Python 3.13; dependency lock dipakai saat instalasi.
`requirements-rag.lock.txt` berasal dari snapshot Windows/Python 3.13.3: keberadaannya **bukan**
bukti build Linux berhasil. Build image berikut adalah gate verifikasi terpisah:

```sh
# Dari root repository, hanya jika Docker tersedia dan instalasi dependency diizinkan.
docker build -f apps/api/Dockerfile -t rag-salon-api .
docker build -f apps/ai/Dockerfile -t rag-salon-ai .
```

API menjalankan TypeScript lewat `tsx` runtime dan membawa source shared packages. API build
adalah pemeriksaan tipe, bukan folder dist. AI Docker langsung menjalankan uvicorn dengan
PORT platform; tidak memakai interpreter Windows atau `freeport` development.

`.dockerignore` mengizinkan hanya input backend yang diperlukan. Dataset/bobot CV, PDF,
output penelitian, .env, dan kredensial tidak masuk context image. Corpus runtime beserta
manifest/source register harus ikut secara utuh; jangan menormalisasi atau mengubah byte paket.

### Volume AI

Mount persistent disk pada `/data`, writable oleh **UID/GID 10001** (runtime user `salon`).
Pastikan permission setelah mount; mount provider dapat menggantikan ownership direktori image.
Jika perlu, operator melakukan penyiapan ownership volume melalui prosedur administrasi provider
sebelum login. Jangan mengatasi masalah permission dengan menaruh token dalam image.

| Lokasi | Sifat |
|---|---|
| `/data/RAGSalon/chatgpt-plan.credentials` | Secret session, writable, mode 0600 |
| `/data/RAGSalon/chatgpt-plan.lock` | Koordinasi refresh pada filesystem yang sama |
| `/data/knowledge` | Knowledge legacy mutable; tidak berisi session |
| `/app/rag/runtime` | Bundle BM25 immutable dari image |
| Cache BM25/web | Memory; boleh hilang ketika restart |

Linux tidak memakai DPAPI: lindungi volume, backups, dan akses shell. Jangan mengunduh isi
credential store untuk debugging, menaruhnya dalam log, atau membagikannya lewat chat.

## 5. Vercel

1. Pilih repository dan **Root Directory `apps/web`**.
2. Aktifkan akses file di luar root project untuk workspace/shared packages.
3. Node 22.x; gunakan `apps/web/vercel.json`: install workspace terfilter dan build langsung Next.js.
4. Isi BACKEND_URL dan SESSION_SECRET pada environment production, serta preview bila diperlukan.
5. Jangan memakai root `pnpm build` untuk frontend bila tidak perlu; Turbo strict env/cache
   membutuhkan konfigurasi tambahan bila dipakai untuk build produksi.
6. Pastikan execution duration plan mendukung route chat/agent. Periksa `maxDuration` pada route
   dan deadline upstream, bukan hanya timeout model.

Rantai request memiliki budget generasi 50 detik, katalog hingga 8 detik, web fallback hingga
12 detik, serta timeout proxy API 90 detik. BFF harus memiliki margin di luar timeout API.
Tidak ada jaminan semua paket hosting gratis mendukung budget ini. Bila platform membatasi
lebih pendek, sesuaikan budget secara konsisten dan uji respons timeout, bukan sekadar menaikkan
satu angka. Jangan membuat request retry generasi otomatis yang menggandakan penggunaan akun.

## 6. Railway

1. Buat service API dan AI dari repository yang sama, **root build context repository**, bukan
   subfolder app. Pilih config file `/apps/api/railway.json` dan `/apps/ai/railway.json` pada
   masing-masing service. Keduanya menunjuk Dockerfile yang berbeda.
2. Tambahkan PostgreSQL terkelola; hubungkan API lewat connection string yang benar.
3. Isi environment wajib. API_BASE_URL/AI_URL harus memakai skema dan port service yang benar;
   internal hostname saja bukan URL lengkap.
4. AI tidak diberi public domain. API memakai public HTTPS origin untuk Vercel.
5. Pasang volume `/data` pada AI, atur ownership dan satu replica. Pastikan offering mendukung
   persistence/private networking; jangan menganggap free tier mencukupi.
6. Lakukan migrasi dan bootstrap yang disetujui, lalu initial ChatGPT authorization manual.
7. Periksa readiness dan uji restart/redeploy sebelum menerima trafik.

Konfigurasi tidak otomatis membuat project, volume, akun, secret, atau database. Memasang
service cloud dapat menimbulkan biaya dan harus dilakukan operator dengan persetujuan.

## 7. Render sebagai alternatif

- Buat Docker **Web Service** untuk Express dan Docker **Private Service** untuk AI.
- Docker context root repository; Dockerfile masing-masing `apps/api/Dockerfile` dan
  `apps/ai/Dockerfile`; jangan menjalankan pnpm dev.
- Tambahkan PostgreSQL, persistent disk `/data` pada AI, dan environment yang sama.
- Tetapkan health path `/api/health` dan `/ai/health`, lalu gunakan readiness sebagai gate operator.
- Periksa dukungan private service/disk, timeout ingress, shell dan tunnel pada offering yang
  dipilih. Seluruh backend stateful tidak dijanjikan berjalan pada layanan gratis/ephemeral.

Tidak disediakan blueprint yang otomatis membuat layanan berbayar. Dockerfile yang sama dapat
dipakai, tetapi perilaku jaringan, volume, dan autentikasi tetap harus diuji pada provider terpilih.

## 8. Login ChatGPT headless dan re-authentication

Tetap memakai grant aplikasi RAG Salon, bukan kredensial Codex/browser aplikasi lain dan bukan
OPENAI_API_KEY. **Jangan menyalin file DPAPI Windows ke Linux.**

Untuk host dengan shell interaktif dan tunnel loopback yang didukung:

1. Siapkan tunnel aman dari port loopback operator ke loopback service AI, misalnya port 8765.
   Kedua ujung harus memakai port yang sama dengan redirect. Ikuti mekanisme akses resmi host;
   jangan membuka callback OAuth ke internet atau bind ke 0.0.0.0.
2. Jalankan dari `/app`, sebagai user runtime dengan XDG_DATA_HOME yang sama:

   ```sh
   python -m app.chatgpt_auth login --no-browser --callback-port 8765
   ```

3. Buka URL otorisasi yang ditampilkan pada browser operator dan setujui grant aplikasi.
   Listener tetap `127.0.0.1`; PKCE/state/nonce dan identitas OIDC diverifikasi. Token ditulis
   langsung ke volume target, bukan diekspor melalui terminal.
4. Periksa status/model melalui CLI hanya atas izin operator; lakukan satu inferensi nyata
   terkontrol untuk membuktikan model/grant bekerja.
5. Uji refresh dan restart agar rotated refresh token tetap tersimpan. Jangan memakai credential
   copy terpisah di beberapa replica.

**Gate penting:** web shell biasa atau remote exec saja belum tentu mendukung port forwarding.
Jika Railway/Render pada offering Anda tidak mendukung transport tersebut, bootstrap ini belum
siap. Jangan melewati gate dengan mempublikasikan callback atau menyalin token ke log. Pilih
lingkungan/tunnel resmi yang kompatibel sebelum menyatakan generasi cloud siap.

Login default desktop tetap tersedia. Re-auth ketika refresh dicabut/kedaluwarsa tetap tindakan
operator; aplikasi tidak mengganti provider atau beralih ke paid API otomatis.

## 9. Database dan admin

- Validasi seluruh migrasi pada database disposable, kemudian jalankan migrasi produksi sekali
  sebagai release operation yang disetujui, dari working directory `apps/api`.
- Backup data sebelum perubahan skema. Gunakan konfigurasi TLS provider.
- **Jangan menjalankan demo seed unchanged:** seed sekarang memiliki akun demo/superadmin
  dengan password hardcoded. Siapkan RBAC, administrator dengan password unik, dan katalog
  salon yang disahkan melalui bootstrap terpisah. Tidak ada bootstrap akun otomatis pada image.
- Jangan menjalankan `db:repair` sebagai startup/release default; perintah itu dapat mengubah
  migration history, menjalankan migrasi, dan seed.
- Jangan memindahkan data pelanggan lokal ke cloud tanpa persetujuan dan prosedur privasi.

Registrasi/login/katalog tidak dianggap siap hanya karena proses API hidup: verifikasi tabel,
role/permission, akun yang sah, dan data bisnis sebelum publikasi.

## 10. Capability dan verifikasi akhir

### Verifikasi lokal — 21 Oktober 2026

- Node 22.16.0, pnpm 10.15.1; Python 3.13 pada Windows.
- API typecheck dan 47 tes terisolasi lulus; tidak memakai database.
- Frontend typecheck, 49 tes, dan `pnpm --filter web build` lulus.
- Regresi Python terpilih: 103 lulus, 1 deselected (`auth_location`, agar tidak menyentuh lokasi
  kredensial pengguna). HTTP, browser, session store, dan provider dimock pada tes terkait.
- Lockfile diperbarui via pnpm dan pemeriksaan `--frozen-lockfile --lockfile-only` lulus.
- `git diff --check` lulus; file penelitian/corpus runtime/evaluasi tracked tidak berubah.
- Docker tidak tersedia di mesin verifikasi: image Linux belum dibangun/dijalankan.
- Belum melakukan login provider, migrasi/seed, deployment, atau smoke test cloud.

### Capability

- Chat publik: BM25 + bukti runtime + katalog aktif + ChatGPT.
- Agent admin: cabang ChatGPT/tools yang ada, tetap melalui otorisasi Express/internal token.
- Knowledge CRUD legacy: persistent tetapi **tidak** memperbarui bundle BM25 aktif.
- Crawl/reingest legacy: unavailable pada profil minimal BM25; bukan kegagalan import tersembunyi.
- CV: 503 dan popup **Fitur belum tersedia**; tidak ada upload/model inference.

Checklist operator setelah izin operasional diberikan:

- [ ] Typecheck/test murni/build lokal.
- [ ] Build dan startup image Linux, termasuk production-only dependencies.
- [ ] Corpus checksum valid dan CV dependencies tidak diimpor.
- [ ] Database/migrasi/bootstrap disahkan; readiness DB lulus.
- [ ] Volume privat writable, session model/grant terverifikasi, refresh/restart lulus.
- [ ] HTTPS login/logout dan RBAC benar; secret tidak masuk bundle browser.
- [ ] Chat harga membaca katalog terbaru; outage tidak memunculkan harga snapshot.
- [ ] Chat perawatan dan sitasi berhasil; timeout memberi error terkontrol.
- [ ] Popup dan endpoint CV tidak mengunggah foto.
- [ ] Readiness failure terlihat, liveness tidak memakai kuota.

Tes API umum menggunakan `prepareDb()` yang menjalankan down/up/seed pada DATABASE_URL biasa.
Jangan menjalankan `pnpm test:api` atau root `pnpm test` pada produksi. Lint, migrasi, seed,
autentikasi nyata, dan deploy memerlukan konfirmasi terpisah.

Smoke script lama memakai contoh katalog demo dan memerlukan `--out`. Jangan menganggap alias
`rag:smoke` tanpa output path atau harga demo sebagai acceptance test produksi. Gunakan output
baru dan kasus yang disesuaikan dengan katalog yang disahkan; jangan menimpa laporan penelitian.
