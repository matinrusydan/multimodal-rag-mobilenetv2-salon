# Studi kualitas RAG development

Hasil diagnostik development. Acuan manusia final dan test independen belum tersedia.

## Perbandingan k (BM25 source-balanced)

| k | P@k | Recall@k | F1@k | Kelompok bukti lengkap |
|---|---:|---:|---:|---:|
| 1 | 0.9500 | 0.8417 | 0.8750 | 0.7500 |
| 2 | 0.5750 | 0.9583 | 0.6983 | 0.9000 |
| 3 | 0.4000 | 0.9833 | 0.5533 | 0.9500 |
| 4 | 0.3000 | 0.9833 | 0.4486 | 0.9500 |
| 5 | 0.2500 | 1.0000 | 0.3899 | 1.0000 |

## Seleksi konteks dari maksimal lima kandidat

| Konteks | P@5 tetap | Precision hasil aktual | Recall | F1 hasil aktual | Karakter rata-rata |
|---|---:|---:|---:|---:|---:|
| all | 0.2500 | 0.2500 | 1.0000 | 0.3899 | 951.3000 |
| source_scoped | 0.2500 | 0.7592 | 1.0000 | 0.8208 | 363.0000 |

Precision@5 dan F1@5 tetap memakai penyebut k=5. Precision/F1 hasil aktual adalah metrik berbeda dengan jumlah konteks yang benar-benar digunakan. Tidak mengganti nama metrik untuk mengesankan peningkatan.

Audit struktural memeriksa resolusi ID, kesesuaian field database dan apakah teks gold muat dalam jendela. Ini bukan persetujuan semantik atau anotasi manusia.
