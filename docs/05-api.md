# 05 — API Endpoint

Spesifikasi endpoint REST API. Semua path & field nama dalam **Bahasa Inggris**; konten pesan error/user-facing tetap **Bahasa Indonesia**.

Base URL: `http://127.0.0.1:4000/api`

> Status: **Rencana target** — endpoint berikut adalah spesifikasi yang akan diimplementasikan.

---

## Konvensi Umum

- **Prefix**: semua route dibawah `/api`.
- **Auth**: protected route memakai `Authorization: Bearer <JWT>` (via `requireAuth`).
- **RBAC**: permission `<resource>.<action>` via `securityEnforce`.
- **Format respons sukses**:
  ```json
  { "ok": true, "data": { ... } }
  ```
- **Format error**: RFC 7807 Problem Details:
  ```json
  { "type": "...", "title": "...", "status": 400, "detail": "Pesan Bahasa Indonesia" }
  ```
- Kolom tanggal pakai ISO 8601 (`YYYY-MM-DD`, `HH:mm`).

---

## 1. Health

| Method | Path | RBAC | Fungsi |
|---|---|---|---|
| GET | `/api/health` | publik | Status server + DB |

```json
200 { "ok": true, "data": { "status": "ok", "uptime": 123.4, "db": "up" } }
```

---

## 2. Auth

| Method | Path | RBAC | Fungsi |
|---|---|---|---|
| POST | `/api/auth/register` | publik | Buat akun customer |
| POST | `/api/auth/login` | publik | Login → set session + JWT |
| POST | `/api/auth/logout` | auth | Hapus session |
| GET | `/api/auth/session` | auth | Ambil status session user |

**POST /api/auth/login**
```json
{ "email": "user@example.com", "password": "secret" }
```
```json
200 { "ok": true, "data": { "token": "JWT", "user": { "id": 1, "name": "...", "email": "...", "type": 1, "roles": ["customer"] } } }
```
`GET /api/auth/session` mengembalikan permission list user untuk RBAC frontend.

---

## 3. Services

| Method | Path | RBAC | Fungsi |
|---|---|---|---|
| GET | `/api/services` | publik | Daftar layanan |
| GET | `/api/services/:slug` | publik | Detail layanan |

```json
200 { "ok": true, "data": [{ "id": 1, "name": "Haircut", "slug": "haircut", "price": 75000, "durationMin": 60, "description": "Potong rambut profesional" }] }
```

---

## 4. Reservations

| Method | Path | RBAC | Fungsi |
|---|---|---|---|
| POST | `/api/reservations` | `reservations.create` | Buat reservasi + invoice |
| GET | `/api/reservations` | `reservations.read` | List reservasi (own/admin) |
| GET | `/api/reservations/:id` | `reservations.read` | Detail reservasi |
| PUT | `/api/reservations/:id/cancel` | `reservations.write` | Batalkan reservasi |

**POST /api/reservations**
```json
{
  "serviceIds": [1, 3],
  "date": "2026-09-20",
  "time": "14:00",
  "notes": "Minta stylist ramah"
}
```
```json
201 { "ok": true, "data": { "id": "INV-20260920-001", "total": 175000, "status": "pending", "expiresAt": "..." } }
```

---

## 5. Payments

| Method | Path | RBAC | Fungsi |
|---|---|---|---|
| POST | `/api/payments/simulate` | `payments.write` | Simulasi pembayaran (prototip) |
| GET | `/api/payments/:id` | `payments.read` | Status pembayaran |

**POST /api/payments/simulate**
```json
{ "reservationId": "INV-...", "method": "qris" }
```
```json
200 { "ok": true, "data": { "status": "paid", "paymentId": "PAY-..." } }
```

---

## 6. Konsultasi — CV (Analyze)

| Method | Path | RBAC | Fungsi |
|---|---|---|---|
| POST | `/api/analyze` | publik (rate-limited) | Klasifikasi rambut dari foto |

Multipart `image/*` (PNG/JPG/WebP).

```json
200
{
  "ok": true,
  "data": {
    "hairLength": { "label": "menengah", "confidence": 0.93 },
    "hairType":   { "label": "bergelombang", "confidence": 0.88 },
    "analyzedAt": "2026-09-09T12:00:00Z"
  }
}
```
Jika confidence `< CONFIDENCE_THRESHOLD`: `status: "low_confidence"`.

---

## 7. Konsultasi — Chat (RAG)

| Method | Path | RBAC | Fungsi |
|---|---|---|---|
| POST | `/api/chat` | publik (rate-limited) | Chatbot konsultasi rambut |

```json
{
  "message": "Rekomendasi gaya untuk rambut tipis?",
  "hairContext": { "hairLength": "menengah", "hairType": "bergelombang" }
}
```
```json
200 { "ok": true, "data": { "reply": "Untuk rambut menengah bergelombang, Anda bisa mencoba …", "sources": ["gaya-rambut.md"], "contextId": "..." } }
```

---

## 8. Admin — RBAC Management

Semua endpoint admin dilindungi `securityEnforce`.

### Users
| Method | Path | RBAC |
|---|---|---|
| GET | `/api/users` | `users.read` |
| GET | `/api/users/:id` | `users.read` |
| POST | `/api/users` | `users.write` |
| PUT | `/api/users/:id` | `users.write` |
| DELETE | `/api/users/:id` | `users.delete` |
| PUT | `/api/users/:id/roles` | `users.manage` |

### Roles
| Method | Path | RBAC |
|---|---|---|
| GET | `/api/roles` | `roles.read` |
| POST | `/api/roles` | `roles.write` |
| PUT | `/api/roles/:id` | `roles.write` |
| DELETE | `/api/roles/:id` | `roles.delete` |
| PUT | `/api/roles/:id/permissions` | `roles.manage` |

### Permissions
| Method | Path | RBAC |
|---|---|---|
| GET | `/api/permissions` | `permissions.read` |
| POST | `/api/permissions` | `permissions.write` |
| PUT | `/api/permissions/:id` | `permissions.write` |
| DELETE | `/api/permissions/:id` | `permissions.delete` |

### Routes & Menus
| Method | Path | RBAC |
|---|---|---|
| GET | `/api/routes` | `routes.read` |
| POST | `/api/routes` | `routes.write` |
| PUT | `/api/routes/:id` | `routes.write` |
| DELETE | `/api/routes/:id` | `routes.delete` |
| GET | `/api/menus` | `menus.read` |
| POST | `/api/menus` | `menus.write` |
| PUT | `/api/menus/:id` | `menus.write` |
| DELETE | `/api/menus/:id` | `menus.delete` |
| PUT | `/api/menus/:id/roles` | `menus.manage` |

---

## 9. Ringkasan Hak Akses Role Awal (Seed)

| Permission | customer | staff | admin |
|---|:---:|:---:|:---:|
| `reservations.create` | ✔ | ✔ | ✔ |
| `reservations.read` | ✔ (own) | ✔ | ✔ |
| `payments.write` | ✔ | ✔ | ✔ |
| `services.read` | ✔ | ✔ | ✔ |
| `users.read/write/delete` | – | – | ✔ |
| `roles.*` / `permissions.*` / `routes.*` / `menus.*` | – | – | ✔ |

Superadmin (`type = 0` / role `SUPER_ADMIN`) melewati semua pengecekan.

---

## 10. Catatan

- Rate-limit diterapkan pada `/api/analyze` & `/api/chat` (mis. per-IP) untuk mencegah abuse biaya OpenAI.
- Semua input divalidasi Zod; error disajikan sebagai Problem Details Bahasa Indonesia.

---

_Lanjut baca: kembali ke [00-struktur-direktori.md](./00-struktur-direktori.md)_
