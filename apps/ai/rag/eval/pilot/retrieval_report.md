# Pilot retrieval RAG salon

Status: pilot engineering pada snapshot PostgreSQL dan Markdown lama; anotasi dokumen belum divalidasi manusia/ahli. Bukan hasil publikasi final.

Snapshot: 2026-10-20T07:51:39.271Z; 6 layanan aktif; 51 evidence; 24 query.

Tidak ada panggilan API, neural dense embedding, generasi LLM, atau penilaian klinis. Hash proxy hanya kontrol leksikal. Semua metode menggunakan korpus dan query yang sama.

| Metode | Kelompok | N dinilai/total | Precision | Recall | F1 retrieval | Bukti lengkap |
|---|---|---|---|---|---|---|
| bm25 | all | 21/24 | 0.257 | 0.976 | 0.399 | 0.952 |
| bm25 | database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25 | document | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25 | mixed | 6/6 | 0.367 | 0.917 | 0.524 | 0.833 |
| bm25 | difficult | 3/6 | 0.267 | 1.000 | 0.413 | 1.000 |
| hash_proxy | all | 21/24 | 0.229 | 0.905 | 0.358 | 0.810 |
| hash_proxy | database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| hash_proxy | document | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| hash_proxy | mixed | 6/6 | 0.267 | 0.667 | 0.381 | 0.333 |
| hash_proxy | difficult | 3/6 | 0.267 | 1.000 | 0.413 | 1.000 |
| hybrid_rrf_hash_proxy | all | 21/24 | 0.229 | 0.905 | 0.358 | 0.810 |
| hybrid_rrf_hash_proxy | database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| hybrid_rrf_hash_proxy | document | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| hybrid_rrf_hash_proxy | mixed | 6/6 | 0.267 | 0.667 | 0.381 | 0.333 |
| hybrid_rrf_hash_proxy | difficult | 3/6 | 0.267 | 1.000 | 0.413 | 1.000 |

Recall memakai union label evidence draft; bukti alternatif yang belum dianotasi dapat dianggap negatif. Karena itu angka ini hanya diagnosis awal dan harus diaudit melalui annotation_sheet.json.
Query unanswerable/ambigu tidak masuk denominator retrieval; keluaran jawaban dan perilaku abstention belum diuji. Skor nol yang sah disertakan. Tidak ada skor faithfulness/correctness yang dibuat-buat.
Waktu assembly bukan latensi retrieval atau LLM. Jangan gunakan sebagai klaim kecepatan sistem. Tidak ada index produksi yang dibaca/ditulis.
