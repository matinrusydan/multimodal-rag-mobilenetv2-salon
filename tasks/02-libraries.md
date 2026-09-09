# Task — Phase 02: Instalasi Library (Dependencies)

> Sebelumnya: Phase 01 scaffold monorepo root (`tasks/01-scaffold-root.md`).

**Tujuan**: Menginstal seluruh library yang dibutuhkan di tiap workspace dengan benar. Phase ini memastikan semua dependency terpasang di `apps/web`, `apps/api`, dan `packages/*` — siap untuk fase berikutnya (DB, copy UI, endpoint).

---

## 1. Dependencies `apps/web` (Next.js 16)

- [ ] Dependencies produksi (via `pnpm --filter web add`):
  - Framework: `next`, `react`, `react-dom`
  - Styling: `tailwindcss`, `tailwindcss-animate`, `class-variance-authority`, `clsx`, `tailwind-merge`
  - Ikon: `lucide-react`
  - UI primitive: `@radix-ui/*` (button, dialog, dropdown-menu, tabs, select, label, slot, dll — sesuai kebutuhan UI yang akan disalin)
  - Session: `iron-session`
  - Validasi/shared: `@rag-salon/shared-types`, `@rag-salon/shared-utils`, `zod`
  - Client state: `zustand` (opsional)
- [ ] Dev dependencies: `typescript`, `@types/react`, `@types/react-dom`, `@types/node`, `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`, `@vitejs/plugin-react`
- [ ] Script `test` → `vitest run`; `dev` → `next dev`; `build` → `next build`.

## 2. Dependencies `apps/api` (Express + TypeScript)

- [ ] Dependencies produksi (via `pnpm --filter api add`):
  - Server: `express`
  - Validasi/shared: `zod`, `@rag-salon/shared-types`, `@rag-salon/shared-utils`
  - DB: `knex`, `pg`
  - Auth: `jsonwebtoken`, `argon2` (atau `bcrypt`), `cookie-parser`
  - Security: `helmet`, `cors`, `express-rate-limit`
  - Logging: `pino`, `pino-http`
  - Multer (upload foto CV): `multer`
  - **CV inference**: `onnxruntime-node` (baca model ONNX hasil export dari `.pth`) ← keputusan: Opsi A/ONNX
  - RAG: `chromadb`, `openai`
- [ ] Dev dependencies: `typescript`, `tsx`, `vitest`, `supertest`, `@types/express`, `@types/jsonwebtoken`, `@types/cors`, `@types/multer`, `@types/cookie-parser`, `@types/supertest`
- [ ] Script `dev` → `tsx watch src/index.ts`; `build` → `tsc`; `test` → `vitest run`.

## 3. Dependencies `packages/*`

- [ ] `shared-types`: pastikan `zod` sebagai dependency (bukan devDependency karena dipakai runtime).
- [ ] `shared-utils`: tidak butuh dependency runtime; dev: `typescript`.

## 4. Root

- [ ] Root devDependencies terpasang: `turbo`, `typescript`, `@biomejs/biome`.
- [ ] `packageManager` terisi (mis. `pnpm@10.26.1`).

## 5. Verifikasi

- [ ] `pnpm install` dari root sukses tanpa error peer dependency.
- [ ] `pnpm build` dari root sukses (semua package & app).
- [ ] `pnpm lint` lolos (Biome).
- [ ] `pnpm test:api` hijau (health test masih lolos).
- [ ] Tidak ada warning konflik versi pada package yang sama.

> **Catatan**: Jika suatu library ternyata tidak tersedia/disetujui, catat alternatif & tanya user sebelum lanjut. Jangan auto-`pnpm install` tanpa sepengetahuan pengguna pada langkah besar (lihat AGENTS.md).
