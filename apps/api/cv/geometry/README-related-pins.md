# Kandidat gambar terkait Pinterest (maksimal 40)

`collect_related_pins.py` membuka Chromium **dengan profil khusus** di `%LOCALAPPDATA%/Temp/opencode/pinterest-related-profile/`. Jika login diperlukan, lakukan sendiri di jendela browser; **jangan masukkan token/cookie ke terminal atau chat**. Profil itu menyimpan status login dan harus Anda lindungi seperti kredensial. Skrip tidak membaca/menampilkan cookie. Jika muncul CAPTCHA, batas akses, atau login gagal, hentikan proses; skrip tidak mencoba melewatinya.

Instalasi satu kali (jika belum ada):

```powershell
python -m pip install playwright pillow
python -m playwright install chromium
```

Contoh, mulai dari pratinjau daftar URL; setelah halaman dan (bila perlu) login siap, tekan Enter di terminal:

```powershell
python apps/api/cv/geometry/collect_related_pins.py "https://mx.pinterest.com/pin/273241902380992811/" --max 40
```

Untuk mengunduh gambar utama pin terkait yang ditemukan:

```powershell
python apps/api/cv/geometry/collect_related_pins.py "https://mx.pinterest.com/pin/273241902380992811/" --max 40 --download
```

**Perhatian:** skrip membaca tautan pin yang *terlihat* saat scrolling di halaman tersebut; Pinterest dapat mengubah tata letak sehingga beberapa tautan tidak terambil atau tautan navigasi lain ikut terambil. Ini bukan verifikasi bahwa seluruh 40 gambar benar-benar rambut bergelombang. Hasil berada di `source_recovery/pinterest_related/` sebagai kandidat, bukan dataset. Periksa tiap gambar, back-view, label, hak penggunaan/sumber asli, resolusi, dan duplikat sebelum merge. Jika tak ada tautan terambil, manifest tetap dibuat dengan 0 baris—jangan mengklaim 40 unduhan berhasil. Jangan menggunakan profil Brave utama.

Manifest bersifat **sekali jalan**: skrip tidak menimpa manifest sebelumnya. Sebelum mencoba ulang, pindahkan/arsipkan manifest lama secara sadar. Pratinjau tidak mengunduh gambar, tetapi menulis daftar URL kandidat. Unduhan hanya mengakses halaman pin publik dan CDN `i.pinimg.com`; tidak memakai sesi login browser untuk permintaan gambar.
