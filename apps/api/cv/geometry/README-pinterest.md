# Ambil satu gambar pin Pinterest publik

Skrip `download_public_pin.py` mengambil **gambar utama dari satu URL pin publik** melalui metadata `og:image`. Tidak mengambil board, rekomendasi, seluruh hasil pencarian, maupun gambar lain di halaman. Tidak memakai cookie atau token; jika pin meminta login atau akses ditolak, skrip berhenti.

Referensi konsep: [gallery-dl](https://github.com/mikf/gallery-dl) (URL pin dan CDN gambar) serta [pinterest-dl](https://github.com/sean1832/pinterest-dl) (metadata halaman). Implementasi ini tidak menyalin kode keduanya.

Jalankan dari root proyek (perlu Python + Pillow):

```powershell
python apps/api/cv/geometry/download_public_pin.py --help
python apps/api/cv/geometry/download_public_pin.py "https://mx.pinterest.com/pin/273241902380992811/"
python apps/api/cv/geometry/download_public_pin.py "https://mx.pinterest.com/pin/273241902380992811/" --download
```

Tanpa `--download`, skrip **hanya** mengambil metadata halaman dan menampilkan URL gambar, tanpa menulis file. Dengan `--download`, file dan manifest JSON disimpan di `apps/api/cv/geometry/source_recovery/pinterest_candidates/` (folder isolasi wajib; file yang sudah ada tidak ditimpa). Skrip menolak gambar dengan sisi terpendek di bawah 224 px, respons terlalu besar, URL/redirect di luar Pinterest dan `i.pinimg.com`, serta format selain JPEG, PNG, WebP.

**Perhatian:** gambar hasil unduhan masih berstatus `candidate_manual_review`. Pin Pinterest bukan bukti lisensi/izin penggunaan. Verifikasi sumber asli, izin penggunaan, label bergelombang, back-view, duplikasi dengan dataset, dan kesesuaian citra sebelum dimasukkan ke dataset final. Jangan menganggap `og:image` sebagai jaminan resolusi asli atau semua gambar dalam pin multi-slide.

Uji offline: `python -m unittest discover -s apps/api/cv/geometry -p 'test_download_public_pin.py'`.
