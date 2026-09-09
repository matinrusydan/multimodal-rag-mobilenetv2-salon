# Task — Phase 03: Koneksi Database Lokal (PostgreSQL Laragon) + DBeaver

> Sebelumnya: Phase 02 instalasi library.
> Lingkungan: PostgreSQL sudah terinstal via **Laragon** (dua service aktif: `postgresql-x64-16` di port **5432**, `postgresql-x64-17` di port **5433**). User ingin database dikoneksikan ke **DBeaver**.

**Tujuan**: Memastikan server PostgreSQL lokal berjalan, membuat database `rag_salon`, dan menghubungkannya ke DBeaver + `apps/api`.

---

## 1. Status Server PostgreSQL

- [x] Instance dipilih: **port 5432 = PostgreSQL 17** (terverifikasi via `SHOW server_version`), berisi DB `rag_salon`.
- [ ] Pastikan server `Running`.

> Lingkungan terdeteksi:
> - `5432` → PostgreSQL **17.6** ✔ (dipakai, berisi `rag_salon`)
> - `5433` → instance lain (v16, password beda — tidak dipakai)
>
> Panduan praktis langkah demi langkah → lihat **[`db-notes.md`](./db-notes.md)**.

## 2. Kredensial & Pengguna

- [ ] User superuser `postgres` + password (hanya di sisi user — lihat `db-notes.md §1-2`).
- [ ] Buat database `rag_salon` (user sudah setuju jalanin sendiri via psql).
- [ ] (Opsional, lebih aman) Buat user khusus app, mis. `rag_app`.

## 3. Buat Database & Koneksi DBeaver

- [ ] Buat database `rag_salon` & verifikasi koneksi psql (langkah praktis + perintah → lihat **[`db-notes.md`](./db-notes.md) §1**).
- [ ] Koneksikan ke DBeaver (GUI manual → **[`db-notes.md`](./db-notes.md) §3**): Host `127.0.0.1`, Port `5432`, DB `rag_salon`, user `postgres`.
- [ ] Dapatkan `DATABASE_URL`:
  ```
  postgresql://postgres:<pass>@127.0.0.1:5432/rag_salon
  ```

## 5. Wire ke `apps/api`

- [ ] Di `apps/api/.env`: set `DATABASE_URL` sesuai §3.
- [ ] Update `src/config/env.ts` agar membaca `DATABASE_URL` & memvalidasi dengan Zod.
- [ ] Update `src/config/db.ts` (Knex) agar terhubung ke DB ini.
- [ ] (Verifikasi ringan) Jalankan script koneksi & pastikan `SELECT 1` berhasil dari Node/Knex.

## 6. Verifikasi

- [ ] Database `rag_salon` berhasil dibuat & bisa di-`SELECT 1` via psql (dijalankan user).
- [ ] DBeaver berhasil terhubung & melihat `rag_salon`.
- [ ] `apps/api` dapat membaca `DATABASE_URL` & konek ke Postgres tanpa error.
- [ ] `.env` tidak ter-commit (di-gitignore).

> **Poin tanya ke user**: (2) password user `postgres` dirahasiakan — user jalanin sendiri via psql (lihat `db-notes.md`). (3) buat user khusus (`rag_app`) atau pakai `postgres` langsung — konfirmasi saat wire-up.
>
> **TIDAK dilakukan di phase ini**: migrasi/seed (khusus Phase 03 lanjutan / fase DB-migration), endpoint, copy UI.
