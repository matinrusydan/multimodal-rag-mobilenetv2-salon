# 01 — Arsitektur Sistem

Dokumen ini menjelaskan arsitektur keseluruhan RAG-salon: **website salon** (layanan, reservasi, pembayaran) yang digabung dengan **chatbot konsultasi rambut berbasis Multimodal RAG** (Computer Vision + LLM).

> Status: **Rencana target** — kode belum ada. Definisi label & kebutuhan produk diambil dari `PRD.md`.

---

## 1. Komponen Sistem

| Komponen | Teknologi | Peran |
|---|---|---|
| **Frontend** | Next.js 16 (App Router, SSR) + TypeScript + Tailwind | Halaman publik salon, reservasi, payment, admin RBAC, dan halaman konsultasi |
| **Backend** | Express + TypeScript | REST API, RBAC, service reservation/payment |
| **CV Pipeline** | PyTorch + MobileNetV2 | Klasifikasi panjang & jenis rambut dari foto |
| **RAG Pipeline** | ChromaDB + OpenAI (GPT-4o-mini, text-embedding-3-small) | Chatbot konsultasi berbasis knowledge base |
| **Database** | PostgreSQL + Knex | User, role, permission, service, reservation |
| **Auth** | iron-session (FE) + JWT (BE) | Session autentikasi + RBAC |

---

## 2. Arsitektur Monorepo

```
rag-salon/
├── apps/web       → Next.js 16 (frontend, UI dari TIEN-SALON-New + konsultasi)
├── apps/api       → Express + TS (backend, RBAC, CV & RAG)
├── packages/shared-types → Zod schemas FE↔BE
└── packages/shared-utils → helper util dibagi
```

- Package manager: **pnpm** workspace.
- Task pipeline: **Turbo** (build/test/lint/local).
- Lint & format: **Biome**.

---

## 3. Data Flow — Konsultasi Multimodal (Chatbot RAG)

```
User upload foto rambut
        │
        ▼
[1] POST /api/analyze (foto)
        │
        ▼
[2] CV Pipeline (MobileNetV2)
        │  preprocessing 224x224 + normalisasi ImageNet
        ▼
[3] Hasil klasifikasi:
        │  hairLength: pendek/pendek-menengah/menengah/panjang
        │  hairType:   lurus/bergelombang/keriting/sangat-keriting
        │  + confidence
        ▼
[4] POST /api/chat (pesan + hair_context dari CV)
        │
        ▼
[5] RAG Pipeline:
        │  embed query → ChromaDB similarity search (top_k=5)
        │  → prompt builder (system + retrieved docs + hair_context + query)
        ▼
[6] GPT-4o-mini → respons konsultasi (Bahasa Indonesia)
```

**Integrasi multimodal**: hasil CV (`hair_context`) menjadi bagian dari konteks prompt RAG, sehingga jawaban chatbot relevan dengan kondisi rambut pengguna.

---

## 4. Data Flow — Reservasi Salon

```
User (login)
   │
   ▼
/services → pilih layanan → /reservation (form)
   │
   ▼
POST /api/reservations (simpan + generate invoice)
   │
   ▼
/reservation/summary → /payment
   │
   ▼
POST /api/payments/simulate
   │
   ▼
/reservation/success (session di-clear)
```

State alur reservasi disimpan di **sessionStorage** (pola `TIEN-SALON-New`), dengan guard redirect di tiap langkah.

---

## 5. RBAC (Role-Based Access Control)

Diadopsi penuh dari `dashboard-ops`, diimplementasikan di **Express** sebagai middleware.

- **Permission naming**: `<resource>.<action>` (contoh `users.read`, `reservations.create`, `menus.write`).
- **Wildcard**: `resource.*` / `resource.manage`; varian kepemilikan `*.own`.
- **Superadmin bypass**: role `SUPER_ADMIN` / `SUPERADMIN` atau user `type = 0`.
- **Enforcement**: `requireAuth` (JWT) + `securityEnforce(permission)`.
- **Tabel**: `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `routes`, `role_routes`, `menus`, `role_menus`.
- **Cache**: permission cache dengan TTL agar lookup cepat.

Detail lengkap: [03-backend.md](./03-backend.md) & [05-api.md](./05-api.md).

---

## 6. Label Klasifikasi Tetap

Label ini **berulang** di seluruh pipeline — CV, RAG prompt, dan UI. Jangan diubah sembarangan.

**Panjang rambut** (4 kelas):
`pendek`, `pendek-menengah`, `menengah`, `panjang`

**Jenis rambut** (4 kelas):
`lurus`, `bergelombang`, `keriting`, `sangat-keriting`

---

## 7. Bahasa

| Lapisan | Bahasa |
|---|---|
| URL path & endpoint API | **Inggris** |
| Konten user-facing (UI, knowledge base, error) | **Indonesia** |
| Kode & komentar | **Inggris** |
| Nama label klasifikasi | **Indonesia** |
| Dokumentasi | **Indonesia** |

---

## 8. Kaitan dengan Referensi

| Aspek | Referensi |
|---|---|
| Monorepo pnpm+Turbo, layer backend, RBAC, env files | `dashboard-ops` |
| UI salon (app/, components/, data/, lib/, public/) | `TIEN-SALON-New` |
| Requirement & label klasifikasi CV/RAG | `PRD.md` |

---

_Lanjut baca: [02-setup.md](./02-setup.md)_
