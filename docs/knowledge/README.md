# Basis Pengetahuan Proyek RAG-salon

Dokumentasi ini adalah peta operasional codebase RAG-salon. Dokumen disusun dari pemeriksaan statis source dan artefak pada **6 November 2026**; bukan bukti bahwa server, database, model, atau deployment sedang aktif.

## Mulai dari sini

1. [Getting Started](./Getting%20Started.md) — kebutuhan lokal, instalasi, dan perintah kerja.
2. [TASK](./TASK.md) — status fase, gate, bukti, dan pekerjaan yang belum selesai.
3. [Architecture and Data Flow](./Architecture%20Overview/Architecture%20and%20Data%20Flow.md) — batas Web, API, AI, dan database.
4. [Data Fetching](./Architecture%20Overview/Data%20Fetching.md) — aliran fetch dan pemilik data.
5. [Modularization and Directory Map](./Architecture%20Overview/Modularization%20and%20Directory%20Map.md) — fungsi direktori dan aturan dependensi.
6. [CV Roadmap Status](./Computer%20Vision%20Research/CV%20Roadmap%20Status.md) — status penelitian CV beserta gate.

## Indeks topik

### Arsitektur

- [Architecture and Data Flow](./Architecture%20Overview/Architecture%20and%20Data%20Flow.md)
- [Data Fetching](./Architecture%20Overview/Data%20Fetching.md)
- [Modularization and Directory Map](./Architecture%20Overview/Modularization%20and%20Directory%20Map.md)

### Implementasi

- [Backend: Layering and API](./Backend/Layering%20and%20API.md)
- [Backend: RBAC and Auth](./Backend/RBAC%20and%20Auth.md)
- [Frontend: Routes and Components](./Frontend/Routes%20and%20Components.md)
- [AI Engine: RAG Pipeline](./AI%20Engine/RAG%20Pipeline.md)
- [AI Engine: CV Existing](./AI%20Engine/CV%20Existing.md)

### Penelitian dan operasi

- [CV Roadmap Status](./Computer%20Vision%20Research/CV%20Roadmap%20Status.md)
- [Dataset and Curation Policy](./Computer%20Vision%20Research/Dataset%20and%20Curation%20Policy.md)
- [Testing Strategy](./Testing%20Strategy.md)
- [Troubleshooting and FAQ](./Troubleshooting%20and%20FAQ.md)

## Arti status

| Simbol | Arti |
|---|---|
| ✅ | Implementasi atau artefak ditemukan; jika menyebut tes lulus, ada bukti hasil historis atau tes baru. |
| 🔄 | Sedang berjalan atau masih memerlukan kelanjutan. |
| ⏳ | Belum dikerjakan atau belum memenuhi gate. |
| ⚠️ | Kondisional, parsial, atau memiliki batas penting. |
| ❓ | Belum dapat diverifikasi dari checkout saat audit. |

Keberadaan file tidak otomatis membuktikan kualitas runtime. Angka evaluasi bertanggal diperlakukan sebagai bukti historis, kecuali pengujian dijalankan ulang dan dicatat.

## Hubungan dengan dokumen lama

- `docs/00`–`docs/08` menjelaskan desain awal dan roadmap CV; `docs/08-roadmap-cv-lengkap.md` tetap sumber tertinggi untuk pekerjaan CV.
- `docs/09`–`docs/23` merekam studi dan keputusan RAG pada tahap tertentu.
- Beberapa bagian dokumen lama tidak lagi sesuai source. Contoh: `apps/ai/app/main.py` saat ini hanya mengimpor aplikasi dari `app.rag_app`; runtime publik tidak memasang router CV `/ai/analyze`.
- `docs/project-memory.md` adalah snapshot pemeriksaan 21 Oktober 2026, bukan status berjalan.

Jika dokumen ini dan source berbeda, source dan artefak yang bisa direproduksi menjadi sumber kebenaran, lalu dokumentasi harus diperbarui.
