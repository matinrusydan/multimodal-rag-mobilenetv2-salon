# Correção do evaluator e das operações de catálogo

Data: 20 Outubro 2026. Resolve os quatro casos de reprodução registrados em `docs/15-review-rag-2026-10-20.md`.

## Operações de catálogo

Listar todos os serviços, contar, filtrar por preço e ordenar por preço agora usam operações determinísticas sobre os records do catálogo, antes da clarificação de serviço e do retrieval BM25. Essas operações não chamam o modelo ou embedding e não ficam limitadas aos cinco resultados da busca documental.

No chat HTTP com `RAG_LIVE_SERVICES=true`, a origem continua sendo o catálogo ativo da API Express. Fora dessa opção, os mesmos operadores usam o snapshot configurado. Não há migração nem escrita no banco.

Exemplos suportados:

- `Sebutkan semua layanan yang tersedia di salon.`
- `Apa saja layanan dengan harga di bawah Rp300.000?`
- `Berapa jumlah layanan maksimal 300 ribu?`
- `Layanan antara Rp280.000 dan Rp325.000`
- `Layanan di atas Rp220.000 dan di bawah Rp300.000`
- `Apa layanan termurah?`
- `Urutkan semua layanan berdasarkan harga dari tertinggi`

`Di bawah/di atas` tidak menyertakan nilai batas; `maksimal/minimal` menyertakan nilai batas. Operasi membandingkan harga reguler tanpa menyimpulkan promo atau histori. Batas angka yang tidak didukung atau ambigu meminta penjelasan, bukan diam-diam mengembalikan seluruh katalog. Batas durasi tidak ditafsirkan sebagai rupiah. Permintaan campuran yang menyebut cara perawatan tetap menggunakan jalur RAG.

Daftar sampai 30 hasil ditampilkan utuh; jika lebih banyak, respons menyebut jumlah total dan bahwa hanya 30 ditampilkan. Respons menyertakan bukti ringkasan operasi, record terpilih, dan identitas sumber. Trace menyimpan semua record yang diperiksa untuk mereproduksi filter dan jumlah. Empty catalog dibedakan dari kegagalan API; kegagalan tidak mengambil kembali daftar snapshot.

Implementasi utama: `apps/ai/app/rag/catalog_operations.py`, dipanggil oleh `rag_service.py` sebelum `service_clarification()`.

## Evaluator v3

Default berubah menjadi `rag/eval/curated-development-v2/questions.json`. `rag/eval/testset.json` legacy, termasuk klaim promo lamanya, tetap disimpan sebagai arsip dan tidak diterima sebagai paket evaluasi tanpa manifest.

Sebelum inferensi, evaluator memeriksa hash manifest, korpus, pertanyaan, kebijakan, protokol, sumber, konsistensi ID, kelompok bukti dan jumlah data. Runtime menggunakan korpus dari paket yang dipilih, bukan korpus berbeda dari environment. Pemeriksaan hash diulang selama eksekusi; perubahan input membatalkan proses. Index vektor tanpa provenance yang cocok belum didukung jalur evaluator paket ini, sehingga mode evaluator ini dibatasi pada BM25 dan BM25 source-balanced.

`policy_clarification`, `catalog_lookup`, dan `policy_unavailable` diterima sebagai jenis respons yang dieksekusi dengan sah. Jenis respons bukan skor kebenaran. Klarifikasi dinilai relevansinya terhadap pertanyaan; kecocokan route dengan label klarifikasi dicatat terpisah, dan kebenaran semantiknya tetap memerlukan penilaian. Error model/offline tetap error pipeline dalam evaluasi.

Metrik yang tidak berlaku diberi `metric_applicability=false` dan alasan N/A. Misalnya, klarifikasi tanpa bukti tidak dipaksa memiliki skor faithfulness atau recall. Lookup katalog bukan ranking passage sehingga tidak diberi context precision/recall. Summary memisahkan valid, missing/error, zero yang sah, dan N/A. Retry hanya mengulang nilai missing yang berlaku; tidak mengulang zero atau N/A.

Laporan baru memakai protokol `custom_llm_judge_v3_not_ragas_library` dan default `custom_judge_v3_report.json/.md`. Laporan lama tidak ditimpa. Retry menolak protokol/model/provider/paket acuan yang berbeda. Ini tetap custom judge, bukan implementasi metrik library RAGAS.

Paket v2 tetap development: 21 item berstatus pemetaan/acuan baru menunggu peninjauan dan tiga berstatus perbaikan cakupan/label oleh asisten. Status tersebut dicatat apa adanya dalam laporan; tidak diubah menjadi persetujuan Matin atau hasil publikasi final.

## Pemeriksaan tanpa biaya inferensi

Dari `C:\laragon\www\RAG-salon\apps\ai`:

```powershell
& '.venv\Scripts\python.exe' -m app.rag.eval_rag --validate-only
```

Opsi ini memeriksa paket dan mencetak provenance tanpa generator/judge/API. Pengujian batch model tetap memerlukan `--allow-api`, model generator dan judge eksplisit, serta `--output` baru. Tidak ada batch model yang dijalankan pada perbaikan ini.

## Verifikasi

- 114 tes regresi lulus dalam 2,48 detik, termasuk tambahan 34 kasus terhadap suite sebelumnya.
- `--validate-only` lulus pada paket v2 dan melaporkan `publication_ready=false`.
- Checagem HTTP menggunakan proses Python baru dan GET API katalog lokal nyata: enam layanan terdaftar, dua di bawah Rp300.000, dan jumlah sesuai.
- Kasus klarifikasi diuji dengan judge tiruan, bukan dipublikasikan sebagai skor kualitas model.
- Pemeriksaan daftar/filter tidak memakai panggilan generator; total panggilan model pada smoke check adalah nol.
- Tidak ada migrasi, seed, perubahan data bisnis, perubahan CV, atau modifikasi proposal LaTeX.

Laporan HTTP: `apps/ai/rag/eval/online-smoke-chatgpt/catalog-evaluator-fix-check.json`. Skrip pemeriksaan: `tmp/verify_catalog_evaluator_fix.py`.

Restart proses `pnpm local` yang sedang berjalan agar port 5000 memakai kode baru, lalu muat ulang halaman konsultasi. Pemeriksaan HTTP di atas menggunakan proses baru dan tidak membuktikan proses lama sudah memuat perubahan.
- Checagem HTTP menggunakan proses Python baru dan GET API katalog lokal nyata: enam layanan terdaftar, dua di bawah Rp300.000, dan jumlah sesuai.
- Pemeriksaan HTTP menggunakan proses Python baru dan GET API katalog lokal nyata: enam layanan terdaftar, dua di bawah Rp300.000, dan jumlah sesuai.
