# Database Setup — PostgreSQL 17 + DBeaver

> Environment (terdeteksi, sudah diverifikasi via `SHOW server_version`):
> - Port **5432** → PostgreSQL **17.6** ← **dipakai** (berisi database `rag_salon`)
> - Port **5433** → instance lain (v16, password berbeda — tidak dipakai)
> - psql tersedia: `psql (PostgreSQL) 16.14`

**Database**: `rag_salon` · **User**: `postgres` · **Host**: `127.0.0.1` · **Port**: `5432`

> Kamu memilih **menjalankan sendiri** perintah psql. Semua langkah di bawah bisa kamu jalankan manual. Password tidak perlu ditampilkan di chat.

---

## 1. Buat Database (jalankan sendiri di PowerShell)

Buka PowerShell, lalu jalankan (isi `<password>` saat diminta):

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -c "CREATE DATABASE rag_salon;"
```

Verifikasi:

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -d rag_salon -c "SELECT version();"
```

> Jangan pakai `-w` (no-password) — itu membuat error `fe_sendauth: no password supplied`. Biarkan psql meminta password interaktif.

---

## 2. Kredensial untuk `apps/api`

Di `apps/api/.env`, set `DATABASE_URL` (ganti `<password>`):

```env
DATABASE_URL=postgresql://postgres:<password>@127.0.0.1:5432/rag_salon
PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=rag_salon
PGUSER=postgres
```

**(Opsional, lebih aman)** buat user khusus app:

```sql
CREATE USER rag_app WITH PASSWORD 'rag_secret';
GRANT ALL PRIVILEGES ON DATABASE rag_salon TO rag_app;
```

---

## 3. Koneksikan ke DBeaver (manual GUI)

1. Buka **DBeaver** → klik ikon **New Database Connection** (tanda `+`) / *Database > New Connection*.
2. Pilih **PostgreSQL** → **Next**.
3. Isi form koneksi:
   - **Host**: `127.0.0.1`
   - **Port**: `5432`
   - **Database**: `rag_salon`
   - **Username**: `postgres`
   - **Password**: *(password postgres kamu — diisi sendiri di GUI)*
4. Klik **Test Connection** → pastikan berhasil (DBeaver akan unduh driver PostgreSQL pertama kali).
5. Klik **Finish**.

Hasil: database `rag_salon` muncul di navigator DBeaver. (Belum ada tabel — kosong sampai migrasi/seed dijalankan.)

---

## 4. Checklist

- [ ] Database `rag_salon` berhasil dibuat (via §1).
- [ ] psql bisa `SELECT version()` di DB tersebut.
- [ ] DBeaver terhubung & menampilkan `rag_salon`.
- [ ] `apps/api/.env` berisi `DATABASE_URL` yang valid (belum di-connect kode, itu di Phase 03 bagian wire-up / Phase 05).

> Langkah lanjutan (migrasi & seed, wire-up Knex di `apps/api`) dilakukan di **Phase 03→05** — butuh konfirmasi user sebelum menjalankan.
