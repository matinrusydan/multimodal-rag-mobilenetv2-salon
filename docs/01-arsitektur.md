# 01 — Arsitektur Sistem

Dokumen ini menjelaskan arsitektur keseluruhan RAG-salon: **website salon** (layanan, reservasi, pembayaran) yang digabung dengan **chatbot konsultasi rambut berbasis Multimodal RAG** (Computer Vision + LLM).

> Status: **Sebagian dibangun** — `apps/api` + `apps/web` ada; `apps/ai` (FastAPI brain engine) masih rencana. Definisi label & kebutuhan produk diambil dari `PRD.md`.

---

## 1. Komponen Sistem

| Komponen | Teknologi | Peran |
|---|---|---|
| **Frontend** | Next.js 16 (App Router, SSR) + TypeScript + Tailwind | Halaman publik salon, reservasi, payment, admin RBAC, dan halaman konsultasi |
| **Backend** | Express + TypeScript | REST API, RBAC, service reservation/payment; **proxy AI** ke FastAPI |
| **Brain Engine** | FastAPI + Python | Runtime AI (CV, RAG, crawler) — `apps/ai`, port `5000` |
| **CV Pipeline** | onnxruntime (Python) + MobileNetV2 ONNX | Klasifikasi panjang & jenis rambut dari foto |
| **RAG Pipeline** | ChromaDB native (Python) + Gemini (embed & LLM) | Chatbot konsultasi berbasis knowledge base |
| **Crawler** | Crawl4AI (Python) | Isi knowledge base: situs TIEN + tips eksternal |
| **Database** | PostgreSQL + Knex | User, role, permission, service, reservation |
| **Auth** | iron-session (FE) + JWT (BE) | Session autentikasi + RBAC |

---

## 2. Arsitektur Monorepo

```
rag-salon/
├── apps/web       → Next.js 16 (frontend, UI dari TIEN-SALON-New + konsultasi)
├── apps/api       → Express + TS (backend, RBAC, proxy AI)
├── apps/ai        → FastAPI + Python (brain engine: CV, RAG, Crawl4AI)
├── packages/shared-types → Zod schemas FE↔BE
└── packages/shared-utils → helper util dibagi
```

- Package manager: **pnpm** workspace.
- Task pipeline: **Turbo** (build/test/lint/local).
- Lint & format: **Biome**.

**Dua-tier AI**: Express hanya meneruskan (proxy) request AI ke FastAPI `:5000`. Publik tidak menyentuh FastAPI langsung.

---

## 3. Data Flow — Konsultasi Multimodal (Chatbot RAG)

```
User upload foto rambut
        │
        ▼
[1] POST /api/analyze (foto)                ← Express (rate-limit + validasi)
        │
        ▼  (proxy)
[2] FastAPI /ai/analyze (apps/ai)
        │  CV Pipeline (onnxruntime + MobileNetV2 ONNX)
        │  preprocessing 224x224 + normalisasi ImageNet
        ▼  (kembali ke Express)
[3] Hasil klasifikasi:
        │  hairLength: pendek/pendek-menengah/menengah/panjang
        │  hairType:   lurus/bergelombang/keriting/sangat-keriting
        │  + confidence
        ▼
[4] POST /api/chat (pesan + hair_context dari CV)   ← Express
        │
        ▼  (proxy)
[5] FastAPI /ai/chat (apps/ai) — RAG Pipeline:
        │  embed query (Gemini 768d) → ChromaDB similarity search (top_k=5)
        │  → prompt builder (system + retrieved docs + hair_context + query)
        ▼
[6] Gemini LLM → respons konsultasi (Bahasa Indonesia)
```

**Integrasi multimodal**: hasil CV (`hair_context`) menjadi bagian dari konteks prompt RAG, sehingga jawaban chatbot relevan dengan kondisi rambut pengguna.

**Crawling & ingest (offline)**:

```
Crawl4AI script (apps/ai/crawler/) : situs TIEN lokal + alodokter.com
        │
        ▼  tulis markdown + front-matter topic
apps/ai/rag/knowledge/crawled-*.md
        │
        ▼  pnpm rag:ingest (Chunker → Gemini embed → ChromaDB)
ChromaDB (persistent | http)
```

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
