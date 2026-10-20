# Usulan penelitian RAG salon

- `main.pdf`: ekspor lama; belum diekspor ulang setelah revisi IR. Lihat preview editor untuk hasil sumber terbaru.
- `main.tex`: sumber LaTeX yang dapat diedit.
- `build.ps1`: kompilasi PDF dengan MiKTeX, dua putaran untuk menyelesaikan sitasi.

## Isi

1. Rencana judul dan masalah utama.
2. Matriks tiga pasangan RP–RQ–RO.
3. Rancangan sumber, metode, baseline, dan ablation.
4. Definisi parameter evaluasi, termasuk F1 retrieval.
5. Langkah berikutnya dan gate keputusan pilot.
6. Referensi utama yang dipilih dari mapping 25 paper.

## Kompilasi ulang

Jalankan dari folder ini melalui PowerShell:

```powershell
.\build.ps1
```

Alur awal diadaptasi dari `C:\laragon\www\TUGAS Deep Learning\generate_docs\build_tex.ps1`. Sumber sekarang juga berhasil dikompilasi dengan compiler bawaan editor Codex. Halaman matriks menggunakan `pdflscape` agar kompatibel dengan XeTeX dan pdfTeX. Kompilasi editor memperbarui preview; ini tidak berarti ekspor `main.pdf` lama ikut diganti.

Revisi IR 20 Oktober 2026: judul kerja menyebut BM25, pembanding mengikuti metode yang tersedia, Precision@k memakai penyebut k, dan hasil development dipisahkan dari pengujian final. Rincian pada `docs/18-implementasi-dan-eksperimen-ir.md` dari root proyek.

## Sumber dan batas penggunaan

Struktur mengikuti contoh usulan yang diberikan pengguna. Isi penelitian mengikuti `artikel/merged-paper/mapping.md` dan panduan penulisan pada `C:\Users\lilol\Documents\Penelitian Ilmiah`. Klaim kebaruan dan masalah lokal masih harus dikonfirmasi melalui penelusuran terarah dan pilot. Tidak ada hasil eksperimen yang dikarang atau angka performa minimal yang dipaksakan.

NPM tidak dicantumkan karena nama file contoh dan identitas di isi contoh memuat angka yang berbeda. Nama pengusul mengikuti isi contoh.
