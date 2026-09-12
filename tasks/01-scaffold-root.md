# Task.md — Roadmap Eksekusi RAG-salon

Daftar **phase eksekusi** proyek. Setiap phase punya file task sendiri di folder `tasks/`.

Urutan & alur (berdasarkan diskusi dengan user):
**Scaffold root dulu**, lalu instalasi library → DB → copy UI → endpoint → website selesai → CV → RAG → deployment.

| Phase | Judul | File Task |
|---|---|---|
| 01 | Scaffold Monorepo Root | [`tasks/01-scaffold-root.md`](./tasks/01-scaffold-root.md) |
| 02 | Instalasi Library (dependencies) | [`tasks/02-libraries.md`](./tasks/02-libraries.md) |
| 03 | Koneksi Database Lokal (PostgreSQL Laragon) + DBeaver | [`tasks/03-database.md`](./tasks/03-database.md) |
| 04 | Copy-Paste UI dari TIEN-SALON-New | [`tasks/04-copy-ui.md`](./tasks/04-copy-ui.md) |
| 05 | Membuat Endpoint API (Express + RBAC + Zod) | [`tasks/05-endpoints.md`](./tasks/05-endpoints.md) |
| 06 | Development Website (Frontend selesai) | [`tasks/06-website-dev.md`](./tasks/06-website-dev.md) |
| 07 | Membangun CV Pipeline (MobileNetV2 → ONNX) | [`tasks/07-cv.md`](./tasks/07-cv.md) |
| 08 | Membangun RAG Pipeline (ChromaDB + OpenAI) | [`tasks/08-rag.md`](./tasks/08-rag.md) |
| 09 | Deployment | [`tasks/09-deployment.md`](./tasks/09-deployment.md) |

---

## Status

| Phase | Status |
|---|---|
| 01 | ⬜ Belum mulai |
| 02 | ⬜ Belum mulai |
| 03 | ⬜ Belum mulai |
| 04 | ⬜ Belum mulai |
| 05 | ⬜ Belum mulai |
| 06 | ⬜ Belum mulai |
| 07 | ⬜ Belum mulai |
| 08 | ⬜ Belum mulai |

## Catatan Eksekusi

- Jangan auto-execute langkah besar (`pnpm migrate`, `pnpm seed`, `pnpm lint`, instalasi besar) tanpa konfirmasi user (lihat `AGENTS.md`).
- Setiap fase diakhiri dengan **verifikasi** (build/test/lint) sebelum lanjut.
- Fase 07 (RAG+CV) membutuhkan keputusan runtime CV (Python vs Node) — konfirmasi user.
- Fase 08 (deployment) membutuhkan keputusan platform — konfirmasi user.
