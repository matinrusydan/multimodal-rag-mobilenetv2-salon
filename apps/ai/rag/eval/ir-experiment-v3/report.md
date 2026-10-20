# Eksperimen komponen IR v1

Development, bukan hasil publikasi final. Tidak ada panggilan model atau database.

| Metode | P@k ketat | Recall@k | F1@k | MAP@k | MRR@k | nDCG@k biner | Bukti lengkap |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25_scan | 0.2400 | 0.9750 | 0.3756 | 0.9433 | 0.9750 | 0.9595 | 0.9500 |
| bm25_indexed | 0.2400 | 0.9750 | 0.3756 | 0.9433 | 0.9750 | 0.9595 | 0.9500 |
| bm25_allocated_no_decomposition | 0.2400 | 0.9750 | 0.3756 | 0.9433 | 0.9750 | 0.9595 | 0.9500 |
| bm25_source_balanced | 0.2500 | 1.0000 | 0.3899 | 0.9683 | 0.9750 | 0.9789 | 1.0000 |

## Pengukuran komputasi lokal sintetis

| Evidence | Bangun indeks ms | Scan median ms | Indexed median ms | Source-balanced median ms | Alokasi indeks Python KiB |
|---|---:|---:|---:|---:|---:|
| 13 | 0.293 | 0.291 | 0.018 | 0.064 | 61.1 |
| 130 | 2.005 | 4.252 | 0.210 | 0.627 | 225.1 |
| 1300 | 23.599 | 39.072 | 2.910 | 6.981 | 1959.9 |

## Batas interpretasi

- Development-only; no locked held-out test or independent graded judgments.
- Timing uses duplicated texts, preloaded corpus and warm process; not deployed app cold start or concurrency.
- RSS is a whole-process reading, not per-method peak memory; tracemalloc reports Python index allocations only.
- No database/network/generator calls; no generated answer, faithfulness or citation-entailment scores.
- Snippet strategies have identical retrieval labels; semantic evidence survival requires span annotation.
- Paired intervals describe this small selected development set, not general improvement or significance.
