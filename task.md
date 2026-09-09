# Task.md — Roadmap Eksekusi RAG-salon

Daftar **phase eksekusi** proyek. Setiap phase punya file task sendiri di folder `tasks/`.

Urutan & alur (berdasarkan diskusi dengan user):
**Scaffold root dulu**, lalu instalasi library → DB → copy UI → endpoint → website selesai → RAG+CV → deployment.

| Phase | Judul | File Task |
|---|---|---|
| 01 | Scaffold Monorepo Root | [`tasks/01-scaffold-root.md`](./tasks/01-scaffold-root.md) |
| 02 | Instalasi Library (dependencies) | [`tasks/02-libraries.md`](./tasks/02-libraries.md) |
| 03 | Koneksi Database Lokal (PostgreSQL Laragon) + DBeaver | [`tasks/03-database.md`](./tasks/03-database.md) |
| 04 | Copy-Paste UI dari TIEN-SALON-New | [`tasks/04-copy-ui.md`](./tasks/04-copy-ui.md) |
| 05 | Membuat Endpoint API (Express + RBAC + Zod) | [`tasks/05-endpoints.md`](./tasks/05-endpoints.md) |
| 06 | Development Website (Frontend selesai) | [`tasks/06-website-dev.md`](./tasks/06-website-dev.md) |
| 07 | Membangun RAG + CV Pipeline | [`tasks/07-rag-cv.md`](./tasks/07-rag-cv.md) |
| 08 | Deployment | [`tasks/08-deployment.md`](./tasks/08-deployment.md) |

---

## Status

| Phase | Status |
|---|---|
| 01 | ✅ Selesai (scaffold monorepo) |
| 02 | ✅ Selesai (install 481 pkgs, build/lint/test hijau) |
| 03 | ✅ Selesai (health db:up, PostgreSQL 17.6 port 5432) |
| 04 | ✅ Selesai (UI disalin, path EN, build + lint + test hijau) |
| 05 | ✅ Selesai (endpoint API + RBAC + Zod, migrate+seed, 32 test API hijau) |
| 06 | ⬜ Belum mulai |
| 07 | ⬜ Belum mulai |
| 08 | ⬜ Belum mulai |

## Catatan Eksekusi

- Jangan auto-execute langkah besar (`pnpm migrate`, `pnpm seed`, `pnpm lint`, instalasi besar) tanpa konfirmasi user (lihat `AGENTS.md`).
- Setiap fase diakhiri dengan **verifikasi** (build/test/lint) sebelum lanjut.
- Fase 07 (RAG+CV) menggunakan **runtime Node** (PyTorch→ONNX export offline + `onnxruntime-node`), bukan microservice Python terpisah.
- Fase 08 (deployment) membutuhkan keputusan platform — konfirmasi user.
