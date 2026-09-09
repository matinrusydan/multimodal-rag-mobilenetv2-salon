# Task — Phase 04: Copy-Paste UI dari Existing Project (TIEN-SALON-New)

> Sebelumnya: Phase 03 koneksi DB lokal.
> Referensi: `docs/00-struktur-direktori.md`, `docs/04-frontend.md` (mapping URL + komponen).

**Tujuan**: Menyalin seluruh UI dari `C:\laragon\www\TIEN-SALON-New` ke `apps/web/src`, lalu mengorganisir ulang ke struktur global vs local component dan mapping URL Bahasa Inggris (konten tetap Bahasa Indonesia).

---

## 1. Survei Sumber (TIEN-SALON-New)

- [ ] Inventarisasi folder asal yang akan disalin:
  - `app/` → halaman (akan di-rename ke EN)
  - `components/` → global components
  - `data/` → services.ts, salon-info.ts, testimonials.ts, spline-scenes.ts
  - `lib/` → constants.ts, format.ts, session.ts, use-auth.ts, utils.ts
  - `public/` → aset statis (gambar, ikon)
  - `styles/` → global css
- [ ] Catat dependency yang dipakai UI (icon library, spline, dsb) — pastikan terinstal (lihat Phase 02).
- [ ] Catat `package.json` sumber: versi Next/React/deps yang dipakai (untuk sinkron versi).

## 2. Mapping URL: Indonesia → English

Ikuti `docs/04-frontend.md §3`:

| Asli (ID) | Baru (EN) |
|---|---|
| `/layanan` | `/services` |
| `/layanan/[slug]` | `/services/[slug]` |
| `/reservasi` | `/reservation` |
| `/reservasi/ringkasan` | `/reservation/summary` |
| `/reservasi/sukses` | `/reservation/success` |
| `/payment` | `/payment` |
| `/tentang` | `/about` |
| `/kontak` | `/contact` |
| `/login` | `/login` |
| `/daftar` | `/register` |
| _(baru)_ | `/consult` |

- [ ] Salin folder `app/` → `src/app/` dengan penamaan folder EN.
- [ ] Update semua `href`, `redirect`, `NAV_ITEMS` di `lib/constants.ts` ke path EN.
- [ ] Pertahankan teks Bahasa Indonesia di elemen UI.

## 3. Organisasi Komponen

- [ ] Komponen lintas fitur → `src/components/`:
  - `ui/`, `layout/`, `sections/`, `services/`, `reservation/`, `payment/`, `auth/`, `brand/`
- [ ] Komponen khusus satu fitur → `src/features/[nama]/components/` (rename bila perlu).
- [ ] Pisahkan state/helper yang hanya dipakai satu fitur ke `features/[nama]/`.

## 4. Data & Lib

- [ ] Salin `data/*` → `src/data/*` (services.ts, salon-info.ts, testimonials.ts, constants.ts).
- [ ] Salin `lib/*` → `src/lib/*` (constants, format, session, use-auth, utils).
- [ ] Sinkron import relatif di semua file (path lama → baru).
- [ ] Pastikan `lib/constants.ts` berisi mapping URL EN + `SESSION_KEYS` (auth/reservation/payment).

## 5. Aset & Styling

- [ ] Salin `public/` → `apps/web/public/`.
- [ ] Salin `styles/` → `src/styles/` (atau `globals.css`).
- [ ] Semua gambar memakai `next/image` (alt text + dimensi).

## 6. Verifikasi

- [ ] `pnpm --filter web build` sukses (tanpa error import/sisip).
- [ ] `pnpm lint` lolos.
- [ ] Jalankan `pnpm --filter web dev` — semua halaman utama (home, services, about, reservation, dll) bisa diakses via path EN.
- [ ] Tidak ada link mati ke path ID lama di navigasi.

> **Catatan**: Halaman `consult` (chatbot RAG) belum diisi penuh di phase ini — baru placeholder/route. Backend endpoint (Phase 05) belum terintegrasi.
