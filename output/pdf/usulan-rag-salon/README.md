# Usulan penelitian RAG salon

- `main.pdf`: dokumen akhir enam halaman.
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

Alur PDF diadaptasi dari `C:\laragon\www\TUGAS Deep Learning\generate_docs\build_tex.ps1`. Hanya tahap LaTeX ke PDF yang diperlukan; tidak melakukan konversi ke Word. Kompilasi menggunakan paket MiKTeX yang telah tersedia dan menonaktifkan pemasangan paket otomatis. Halaman matriks menggunakan `lscape` dan atribut rotasi PDF sehingga tampil landscape.

## Sumber dan batas penggunaan

Struktur mengikuti contoh usulan yang diberikan pengguna. Isi penelitian mengikuti `artikel/merged-paper/mapping.md` dan panduan penulisan pada `C:\Users\lilol\Documents\Penelitian Ilmiah`. Klaim kebaruan dan masalah lokal masih harus dikonfirmasi melalui penelusuran terarah dan pilot. Tidak ada hasil eksperimen yang dikarang atau angka performa minimal yang dipaksakan.

NPM tidak dicantumkan karena nama file contoh dan identitas di isi contoh memuat angka yang berbeda. Nama pengusul mengikuti isi contoh.
