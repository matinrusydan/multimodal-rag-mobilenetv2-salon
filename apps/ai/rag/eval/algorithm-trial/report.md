# Eksplorasi algoritma retrieval

Data development: 24 pertanyaan draft, 51 evidence; belum divalidasi manusia. Bukan hasil pengujian akhir.

| Metode | Kelompok | N dinilai/total | Precision | Recall | F1 retrieval | Bukti lengkap |
|---|---|---|---|---|---|---|
| bm25 | all | 21/24 | 0.257 | 0.976 | 0.399 | 0.952 |
| bm25 | database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25 | document | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25 | mixed | 6/6 | 0.367 | 0.917 | 0.524 | 0.833 |
| bm25 | difficult | 3/6 | 0.267 | 1.000 | 0.413 | 1.000 |
| bm25_clean | all | 21/24 | 0.257 | 0.976 | 0.399 | 0.952 |
| bm25_clean | database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_clean | document | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_clean | mixed | 6/6 | 0.367 | 0.917 | 0.524 | 0.833 |
| bm25_clean | difficult | 3/6 | 0.267 | 1.000 | 0.413 | 1.000 |
| bm25_mmr | all | 21/24 | 0.257 | 0.976 | 0.399 | 0.952 |
| bm25_mmr | database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_mmr | document | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_mmr | mixed | 6/6 | 0.367 | 0.917 | 0.524 | 0.833 |
| bm25_mmr | difficult | 3/6 | 0.267 | 1.000 | 0.413 | 1.000 |
| bm25_decomposed_rrf | all | 21/24 | 0.248 | 0.952 | 0.385 | 0.952 |
| bm25_decomposed_rrf | database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_decomposed_rrf | document | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_decomposed_rrf | mixed | 6/6 | 0.333 | 0.833 | 0.476 | 0.833 |
| bm25_decomposed_rrf | difficult | 3/6 | 0.267 | 1.000 | 0.413 | 1.000 |
| bm25_routed | all | 21/24 | 0.257 | 0.976 | 0.399 | 0.952 |
| bm25_routed | database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_routed | document | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_routed | mixed | 6/6 | 0.367 | 0.917 | 0.524 | 0.833 |
| bm25_routed | difficult | 3/6 | 0.267 | 1.000 | 0.413 | 1.000 |
| bm25_routed_decomposed | all | 21/24 | 0.257 | 0.976 | 0.399 | 0.952 |
| bm25_routed_decomposed | database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_routed_decomposed | document | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| bm25_routed_decomposed | mixed | 6/6 | 0.367 | 0.917 | 0.524 | 0.833 |
| bm25_routed_decomposed | difficult | 3/6 | 0.267 | 1.000 | 0.413 | 1.000 |

Semua metode top-5, cuplikan maksimal 400 karakter per evidence. Metrik menghitung ID evidence draft, bukan kualitas jawaban atau dukungan klaim setelah pemotongan.
Query ambigu/tanpa bukti (3/24) tidak memiliki skor retrieval; tidak dianggap berhasil. Aturan diusulkan setelah inspeksi kegagalan baseline, sehingga kenaikan pada data ini rentan bias seleksi.
BM25 MMR memakai kemiripan leksikal TF-IDF. Decomposed RRF menggabungkan dua ranking BM25, bukan BM25 + neural dense. Routing berbasis aturan, bukan classifier terlatih.
Tidak ada API, generasi jawaban, perubahan database atau index produksi. Lihat report.json untuk parameter, hash input, rencana routing, dan seluruh konteks.
