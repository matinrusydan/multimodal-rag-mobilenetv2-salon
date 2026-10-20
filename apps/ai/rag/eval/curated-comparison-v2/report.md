# Perbandingan retrieval setelah perbaikan acuan v2

Status: eksplorasi development, bukan hasil publikasi final. Korpus 13 evidence dan 24 pertanyaan sama untuk kedua metode; 20 memiliki gold retrieval. Empat kasus lainnya tidak dinilai sebagai berhasil. Top-5 dan batas cuplikan 400 karakter sama.

| Metode | Bukti lengkap | Recall macro | F1 retrieval macro |
|---|---:|---:|---:|
| BM25 | 19/20 | 0,975 | 0,376 |
| BM25 + seleksi bersumber | 20/20 | 1,000 | 0,390 |

r18 memperoleh record layanan dan passage kondisioner dengan seleksi bersumber. Untuk kebutuhan campuran yang terdeteksi oleh aturan, cadangkan slot data layanan dan dua slot dokumen; ranking dokumen memakai kueri yang dipisahkan dari nama layanan/kata bisnis. Metode tidak menerima label acuan sebagai input. Source code: `app/rag/bm25_retrieval.py`, fungsi `balanced_order`.

Aturan ini dirancang setelah melihat error r18; hasil mengandung bias development. Belum ada uji pada pertanyaan baru atau korpus lebih luas. Menemukan seluruh ID gold tidak membuktikan seluruh jawaban benar, sumber klinis tervalidasi, kebijakan dipatuhi, atau semua kebutuhan pada kasus partial terjawab.

Jangan mengatribusikan selisih dengan v1 pada algoritma: r10 berubah cakupan dan r11/r18 berubah label wajib. Perbandingan metode yang dicatat di tabel hanya memakai v2 yang sama. Semua keluaran retrieval, konteks, kelompok yang terlewat dan kategori tersimpan di `report.json`.

Konfigurasi aplikasi lokal sekarang menggunakan `AI_LLM_PROVIDER=chatgpt` dan `RAG_RETRIEVAL_PROVIDER=bm25_source_balanced`. Tidak ada API embedding. ChatGPT-plan login serta pilihan model masih harus diselesaikan pengguna sebelum pengujian generasi online. Tidak menggunakan API key berbayar atau kredensial Codex. Nilai layanan runtime profil penelitian ini tetap snapshot 20 Oktober 2026, bukan data live.

Tes terkait: 67 lulus menggunakan mock dan smoke test retrieval/offline lulus. Tidak ada metrik generasi yang dihitung.
