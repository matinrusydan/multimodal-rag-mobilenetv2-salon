# Strategi Pengujian

Audit statis: **6 November 2026**. Menjalankan pengujian memerlukan server, dependensi, database atau GPU yang relevan; perintah di bawah tidak dijalankan secara otomatis saat audit dokumentasi.

## Perintah per area

| Area | Perintah | Alat | Cakupan |
|---|---|---|---|
| Monorepo lint | `pnpm lint` | Biome | Root, `apps/api`, `apps/web` |
| Monorepo typecheck | `pnpm typecheck` | TypeScript | `web`, `api`, shared packages |
| Backend API | `pnpm test:api` | Vitest | Route, auth, RBAC, service, reservation, payment, isolated proxy/env |
| Frontend Web | `pnpm test:web` | Vitest + RTL | Session, backend helper, route handler, util |
| AI RAG | `pnpm test:rag` | pytest | RAG runtime, BM25, intent, prompt, catalog, policy (mengabaikan tes CV lama) |
| AI RAG smoke | `pnpm --filter ai rag:smoke` | Python | Uji proxy dan preflight RAG |
| AI CV offline | `pytest tests/test_cv_*.py` | pytest | Preprocessing, labels, ONNX model CPU loader (bukan tes runtime web) |
| CV collector | `pytest apps/api/cv/geometry/test_*.py` | pytest | Uji parsing/downloader offline tanpa login publik |

## Aturan keselamatan pengujian

1. Jangan jalankan `pnpm migrate`, `pnpm seed`, atau `pnpm db:repair` tanpa konfirmasi pengguna dan database yang terisolasi.
2. `test:api` membutuhkan konfigurasi test environment yang aman; jangan menunjuk ke database produksi.
3. `pnpm test:rag` menggunakan cache/mock untuk sebagian pengujian; hasil tes lulus membuktikan logika rute dan aturan, bukan kualitas jawaban klinis atau ketiadaan halusinasi.
4. Tes isolasi seperti `deployment-env-isolated.test.ts` membuktikan penanganan konfigurasi, bukan membuktikan container di cloud sudah berhasil dimulai.

## Evaluasi RAG dan evaluasi CV

- Evaluasi RAG dipisahkan antara retrieval metrics (P@k, Recall@k, MRR), seleksi bukti, dan evaluasi respons. Gunakan dataset terpisah untuk tuning versus evaluasi final.
- Evaluasi CV wajib melaporkan:
  - Macro-F1 dan per-class metrics untuk mengatasi imbalance.
  - Confusion matrix per label kontrak.
  - Evaluasi robustness per-subkelompok yang relevan bila metadata tersedia; jangan jadikan estimasi pose sebagai prasyarat task yang tidak bergantung pose.
  - Kalibrasi probabilitas / ECE.
- Dilarang melaporkan akurasi global saja untuk dataset kelas tidak seimbang.

Riwayat hasil pengujian tersimpan pada:
- `apps/ai/rag/eval/` (RAG artifacts)
- `apps/api/cv/hair_length/reports/` dan lokasi artefak CV historis lainnya (CV artifacts)
