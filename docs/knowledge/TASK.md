# TASK — Status Fase dan Pekerjaan Terbuka

Audit statis: **6 November 2026**. Tabel ini membedakan keberadaan implementasi, hasil historis, dan validasi runtime. Tidak ada test, server, migrasi, seed, training, atau deployment yang dijalankan ulang dalam audit dokumentasi ini.

## Ringkasan

| Area | Status sekarang | Kesimpulan |
|---|---|---|
| Web + API | ✅ Implementasi tersedia | Next.js BFF, Express CRUD/auth/RBAC/proxy ditemukan; runtime belum diuji ulang. |
| RAG | ⚠️ Prototipe lokal + bukti evaluasi historis | Runtime BM25/katalog live/ChatGPT tersedia; human approval, independent test, dan deployment masih terbuka. |
| CV runtime publik | ⏳ Dinonaktifkan | Express `/api/analyze` sengaja mengembalikan 503; FastAPI aktif tidak memasang router CV. |
| CV penelitian | ⚠️ Banyak artefak, roadmap bertahap | Kelayakan pose untuk geometri belum dibuktikan lulus (Fase 0); Fase 1 kurasi data lolos teknis (385 citra); Fase 2 segmentasi MobileNetV2-UNet lolos gate numerik (val IoU 0.9305, ONNX CPU 28.79 ms); Fase 3 parsial (fitur bentuk mask eksploratif tanpa pose); panjang/volume dan Fase 4–5 belum dikerjakan. |
| Dataset tambahan | 🔄 Kandidat terisolasi | Koleksi interaktif maksimal 40 pin, QC, lisensi, label, dan deduplikasi belum selesai. |
| Deployment | ⏳ Belum terbukti | Konfigurasi/readiness docs tersedia, tetapi smoke test domain HTTPS belum tercatat lulus. |
| Publikasi | ⚠️ Draft/paket tersedia lokal | Blind-review dan beberapa konfirmasi penulis masih terbuka. |

## A. Platform web, backend, dan RBAC

| ID | Tugas | Fase | Status | Bukti | Berikutnya |
|---|---|---|---|---|---|
| APP-01 | Monorepo pnpm + Turbo | Fondasi | ✅ | `package.json`, `pnpm-workspace.yaml`, `turbo.json` | Pertahankan Node 22/pnpm 10.15.1. |
| APP-02 | Web Next.js App Router | Implementasi | ✅ | `apps/web/src/app`, `apps/web/src/components` | Jalankan test/build bila diminta. |
| APP-03 | BFF same-origin Web → Express | Implementasi | ✅ | `apps/web/src/app/api/*`, `src/lib/backend.ts` | Verifikasi end-to-end terhadap server aktif. |
| APP-04 | Express Route→Controller→Service→Repository | Implementasi | ✅ | `apps/api/src/{routes,controllers,services,repositories}` | Cegah akses DB langsung dari controller. |
| APP-05 | Auth JWT HttpOnly + web session | Implementasi | ✅ | `requireAuth.ts`, auth routes/service, `web-session.ts` | Uji expiry/logout/cookie pada environment target. |
| APP-06 | RBAC permission/menu/route | Implementasi | ✅ | middleware `securityEnforce`, service/repository dan tests | Jalankan `pnpm test:api` saat disetujui. |
| APP-07 | PostgreSQL migrations/seeds | Implementasi | ✅ file tersedia | `apps/api/src/db` | Migrasi/seed hanya dengan persetujuan dan DB terisolasi. |

## B. RAG

| ID | Tugas | Fase | Status | Bukti | Berikutnya |
|---|---|---|---|---|---|
| RAG-01 | Runtime RAG kanonikal | Operasional lokal | ✅ source | `app/main.py` mengimpor `rag_app`; router chat/agent/knowledge/health | Preflight dan smoke test belum dijalankan ulang. |
| RAG-02 | Retrieval BM25 + seleksi konteks | Implementasi | ✅ | `apps/ai/app/rag/*` | Bekukan versi corpus untuk evaluasi independen. |
| RAG-03 | Katalog layanan live | Implementasi | ✅ | `live_services.py`, Express `/api/services` | Uji failure path dan koneksi runtime. |
| RAG-04 | Penanganan ambiguitas | Evaluasi development | ⚠️ historis | `docs/22-*`, `rag/eval/ambiguity-v1` | Evaluasi ulang versi aktif pada test independen. |
| RAG-05 | Human approval ground truth | Validasi | ⏳ | `ir-protocol-v1/answer-review-status.json` tercatat pending | Reviewer manusia mengesahkan evidence dan jawaban acuan. |
| RAG-06 | Independent locked test | Validasi | ⏳ | Belum ada bukti test independen yang dikunci | Buat keluarga skenario baru tanpa leakage development. |
| RAG-07 | Baseline generatif berpasangan | Validasi | ⏳ | Dicatat terbuka di `project-memory.md` | Definisikan baseline dan judge terpisah. |
| RAG-08 | Cakupan sumber/SOP salon | Data | ⏳ | Batas sumber dicatat docs 19–22 | Tambahkan sumber berizin dan approval ahli. |
| RAG-09 | Deployment publik | Rilis | ⏳ | `docs/23` hanya readiness/config | Lulus gate Linux, DB, auth ChatGPT, dan smoke HTTPS. |

## C. Computer Vision — roadmap fase 0–5

| ID | Fase | Status | Bukti aktual | Gate / pekerjaan berikutnya |
|---|---|---|---|---|
| CV-00 | Kelayakan pose untuk geometri | ⚠️ Belum dibuktikan lulus | Uji lite: kohort 252 memiliki 141 keluaran bahu dan 143 kepala/proxy; kohort 137 memiliki 73 bahu dan 74 kepala/proxy. Historis 44 gambar disimpan di arsip dokumentasi. | Validasi anatomis manusia diperlukan sebelum memakai geometri pose; pose gagal tidak mengecualikan gambar dari hair type/segmentasi. |
| CV-01 | Kurasi data | ⚠️ Parsial/legacy | Implementasi dan artefak target `geometry/` belum lengkap. | Kurasi label/kualitas/lisensi, deduplikasi dan split bebas leakage; bukan klasifikasi orientasi foto. |
| CV-02 | Segmentasi rambut UNet | ⏳ Belum terverifikasi | Target `geometry/train_segmentation.py`, bobot dan `segmentation_eval.json` tidak ditemukan | Train/evaluasi dengan split group; gate IoU ≥0.75. |
| CV-03 | Geometri head-unit | ⏳ Belum final | Artefak lama ada di lokasi lain, target pipeline `geometry/` tidak ditemukan | Mask→pose→rasio relatif, tied-hair handling, validasi manusia. |
| CV-04 | Klasifikasi hierarkis/evaluasi | ⏳ Belum final | `geometry/classify_hierarchical.py` dan `classification_eval.json` tidak ditemukan | Laporkan macro-F1, per-class F1, confusion matrix, ECE. |
| CV-05 | Integrasi/deployment | ⏳ Dinonaktifkan | Express analyze 503; runtime FastAPI tidak memasang router analyze | Hanya integrasikan sesudah semua gate dan kontrak output lulus. |
| CV-BB | Eksperimen backbone hair length legacy | ⚠️ Hasil tersedia, bukan roadmap selesai | `hair_length/reports/backbone_decision.json` memilih EfficientNetV2-S dari eksperimen hold-out | Pisahkan dari klaim pipeline geometris dan validasi independen. |

**Koreksi lokasi artefak:** roadmap merujuk `geometry/reports/phase0_decision.json` dan `backbone_decision.json`, tetapi checkout menyimpan artefak historis di luar struktur target `geometry/`. Ini menunjukkan drift struktur yang harus dibereskan secara terkontrol, bukan dengan memindahkan artefak lama sembarangan.

## D. Dataset dan kurasi

| ID | Tugas | Status | Bukti | Berikutnya |
|---|---|---|---|---|
| DATA-01 | Base dataset Figaro1k terkurasi | ✅ 252 file teramati | `cv/dataset/figaro1k` | Jaga sebagai base; jangan overwrite. |
| DATA-02 | Arsip mentah `new_dataset` | ⚠️ lokal/legacy | `cv/dataset/new_dataset` | Read-only; banyak gambar kecil menurut audit sebelumnya. |
| DATA-03 | Recovery manual | 🔄 | `geometry/source_recovery/*` | Review lisensi, resolusi, label dan deduplikasi. |
| DATA-04 | Related Pinterest ≤40 | ⏳ Run interaktif belum terbukti | collector + tests tersedia | Login manual, jalankan koleksi, lalu QC; jangan masukkan token. |
| DATA-05 | Deduplikasi sebelum split | ⏳ | Belum ada artefak final split deduplicated di target geometry | Perceptual hash/group split sebelum train/val/test. |
| DATA-06 | Merge terkontrol | ⏳ | Kandidat masih terisolasi | Merge hanya setelah approval hak pakai, label, kualitas dan dedupe. |

## E. Publikasi dan supplementary (lokal, bukan produk runtime)

| ID | Tugas | Status | Berikutnya |
|---|---|---|---|
| PUB-01 | Naskah IEEE TAM hasil format | ✅ artefak lokal menurut checkpoint | Verifikasi visual akhir oleh penulis. |
| PUB-02 | Paket supplementary anonim | ✅ paket dan reproduksi historis | Pertahankan anonimitas dan checksum. |
| PUB-03 | Blind-review author anonymization | ⏳ | Konfirmasi aturan jurnal dan hilangkan identitas bila wajib. |
| PUB-04 | Pernyataan “not previously published” | ⏳ keputusan penulis | Penulis mengonfirmasi berdasarkan riwayat publikasi. |
| PUB-05 | Distribusi evidence/raw answer/judge notes | ⏳ keputusan izin | Jangan distribusikan sebelum izin jelas. |
| PUB-06 | Rekonsiliasi hitungan E3 | ⚠️ perlu konfirmasi | Tegaskan apakah 13 offline + 7 API = 20 pemeriksaan adalah definisi final. |

## Definition of done dokumentasi ini

- [x] Indeks dokumentasi dan aturan status.
- [x] Getting started dan commands.
- [x] Tracker lintas area dan fase.
- [x] Data fetching dan batas antarlayanan.
- [x] Modularisasi dan fungsi direktori.
- [x] Dokumentasi RAG, CV, dataset, test, dan troubleshooting.
- [ ] Validasi runtime/test suite (di luar perubahan dokumentasi; perlu persetujuan menjalankan test).
- [ ] Update otomatis setiap perubahan arsitektur (proses tim, belum ada automation).
