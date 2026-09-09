# Task — Phase 08: Deployment

> Sebelumnya: Phase 07 RAG + CV selesai, seluruh fitur berfungsi lokal.
> Referensi: `docs/02-setup.md`, env vars di `AGENTS.md`.

**Tujuan**: Menjadikan RAG-salon dapat diakses publik — meliputi build produksi, database produksi, layanan CV/RAG/LLM, dan hosting web.

> ⚠️ Detail platform (VPS, Vercel, Railway, Docker, dll) **belum dipilih** — konfirmasi ke user sebelum memulai.

---

## 1. Keputusan Arsitektur Deployment (diskusi dulu)

- [ ] Tentukan platform untuk tiap bagian:
  - **Frontend Next.js** (mis. Vercel / VPS + PM2 / Docker)
  - **Backend Express** (VPS / Railway / Docker)
  - **Database PostgreSQL** (managed / VPS)
  - **ChromaDB** (persisted, satu node)
  - **OpenAI** (cloud, via API key)
  - **CV service** (bila Phase 07 pakai microservice Python)
- [ ] Pilih strategi: monorepo build di CI vs pre-build image.
- [ ] Konfirmasi domain & HTTPS (SSL).

## 2. Persiapkan Build Produksi

- [ ] `pnpm build` dari root sukses untuk web & api.
- [ ] Env produksi (per-deployment): `NODE_ENV=production`, `BACKEND_URL` publik, DB URL produksi, `JWT_SECRET`/`SESSION_SECRET` kuat, `OPENAI_API_KEY`, `CHROMA_PERSIST_DIR`, model path, `SECURITY_ENFORCE_ENABLED=true`.
- [ ] Siapkan run command: api `node dist/index.js`, web `next start` (atau standalone).
- [ ] Pastikan migrasi & seed bisa dijalankan pada DB produksi.

## 3. Database & Migrasi Produksi

- [ ] Provision PostgreSQL produksi.
- [ ] Jalankan `pnpm migrate` + `pnpm seed` (perlu konfirmasi user sebelum eksekusi).
- [ ] Seed admin awal untuk RBAC.

## 4. CV & RAG di Produksi

- [ ] Salin model weights & knowledge base ke environment produksi.
- [ ] Pastikan ChromaDB persist dir tersedia & writable.
- [ ] Verifikasi pipeline CV/RAG berjalan di server prod (bukan cuma dev).

## 5. Reverse Proxy & HTTPS

- [ ] Nginx/Caddy (bila VPS) atau platform-managed TLS.
- [ ] Route `/services` → web, `/api` → api (atau sebaliknya sesuai setup).
- [ ] CORS origin update ke domain produksi.

## 6. CI/CD (opsional)

- [ ] Pipeline build + test + deploy otomatis (GitHub Actions / platform-native).
- [ ] Env dirahasiakan (secrets, bukan di repo).

## 7. Verifikasi Peluncuran

- [ ] `GET /health` publik OK.
- [ ] Halaman web publik bisa diakses via domain.
- [ ] Login/registrasi, reservasi, payment, konsultasi (oh CV + RAG) berfungsi di prod.
- [ ] Admin RBAC berfungsi.
- [ ] Periksa keamanan: secrets tidak terbocor, rate-limit aktif, penyimpanan model/DB aman.

## 8. Dokumentasi Operasional

- [ ] Catat alamat domain, endpoint API, env vars produksi (di tempat aman, bukan repo).
- [ ] Ringkas cara menjalankan/re-deploy.

> **Catatan**: Deployment sangat bergantung pada platform yang dipilih. Berhenti & tanya user untuk keputusan platform sebelum melanjutkan (lihat AGENTS.md).
