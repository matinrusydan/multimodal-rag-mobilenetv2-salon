# -*- coding: utf-8 -*-
# ============================================================================
# fetch_figaro1k.py -- Unduh + verifikasi + ekstrak + partisi FIGARO-1k
# ----------------------------------------------------------------------------
# Sumber   : Figaro1k / 1k Blog (Michele Svanera, Universita di Brescia) --
#            database publik segmentasi & klasifikasi rambut "in the wild".
# Distribusi 7 kelas (150 citra/kelas, total 1050; frame00001..01050):
#   straight  frame00001-00150   lurus
#   wavy      frame00151-00300   bergelombang
#   curly     frame00301-00450   keriting
#   kinky     frame00451-00600   sangat-keriting
#   braids    frame00601-00750   (gaya, TIDAK dipakai -> panjang)
#   dreadlocks frame00751-00900  (gaya, TIDAK dipakai)
#   short-men frame00901-01050   (gaya, TIDAK dipakai)
#
# Keluaran: cv/dataset/figaro1k/{lurus,bergelombang,keriting,sangat-keriting}/
#           -> 4 kelas JENIS rambut salon (150 citra x 4 = 600), RGB berwarna.
#
# Catatan bit-depth/channel: Figaro-1k adalah citra uji RGB 24-bit standard
# (3 channel, 8-bit/channel). Konversi RGB->grayscale (Aktivitas/Panel 2)
# memakai SEBAGIAN kecil sampel dari sini supaya praktikum bermakna.
# ============================================================================
import io
import os
import sys
import zipfile
import urllib.request

# --- Lokasi target (relatif dari folder apps/api) ----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CV_DIR   = os.path.join(BASE_DIR, "cv")
DATA_DIR = os.path.join(CV_DIR, "dataset", "figaro1k")
ZIP_PATH = os.path.join(CV_DIR, "dataset", "figaro-1k.zip")

# --- URL unduhan (Dropbox Figaro-1k; dl=1 -> unduh langsung, tanpa halaman) --
URL = (
    "https://www.dropbox.com/scl/fi/bkzbwgobxayoaeqohgvrp/"
    "Figaro-1k.zip?rlkey=qahueoko45prpzmsadzmus5ga&dl=1"
)

# Petakan rentang frame -> 4 kelas salon (sisanya = gaya, diabaikan)
NAMESPACE = [
    ("lurus",           1,   150),
    ("bergelombang",  151,   300),
    ("keriting",      301,   450),
    ("sangat-keriting",451,  600),
]


def unduh(url=URL, target=ZIP_PATH):
    """Unduh zip ke disk; return target. URL dijamin live (sudah dicek HEAD)."""
    os.makedirs(os.path.dirname(target), exist_ok=True)
    print(f"[1/3] Mengunduh Figaro-1k ({url.split('?')[0]}) ...")
    try:
        urllib.request.urlretrieve(url, target)   # 1 baris unduh dari URL
    except Exception as e:
        print(f"      urllib gagal ({e}); coba fallback requests.")
        import requests                          # alternatif bila tersedia
        r = requests.get(url, timeout=600)       # timeout besar utk 65 MB
        r.raise_for_status()
        with open(target, "wb") as f:
            f.write(r.content)
    ukuran = os.path.getsize(target)
    print(f"      OK -> {target} ({ukuran/1024/1024:.1f} MiB)")
    return target


def verifikasi_zip(target, nama="Figaro-1k.zip"):
    """Cek magic-byte ZIP (PK\\x03\\x04) lalu buka archive; return zip objek."""
    with open(target, "rb") as f:
        magic = f.read(4)
    if magic != b"PK\x03\x04":
        raise SystemExit(f"[GAGAL] Bukan file ZIP valid (magic={magic!r}). Hapus {target} & coba lagi.")
    z = zipfile.ZipFile(target)
    print(f"[2/3] ZIP valid (magic PK\\x03\\x04); {len(z.namelist()):,} entri di dalamnya.")
    return z


def ekstrak_dan_partisi(z, out_dir=DATA_DIR):
    """Ekstrak lalu salin 600 citra ke 4 folder kelas (rename frame -> kelas)."""
    os.makedirs(out_dir, exist_ok=True)
    kelas_dir = {nama: os.path.join(out_dir, nama) for nama, *_ in NAMESPACE}
    for d in kelas_dir.values():
        os.makedirs(d, exist_ok=True)

    # name -> index numerik, dan nama kelas untuknya
    def frame_no(name):
        m = name.split("frame")[-1].replace(".tif", "")
        return int(m)

    salinan = 0
    for entri in z.namelist():
        if not entri.endswith(".tif") or "frame" not in entri:
            continue
        no = frame_no(entri)
        for nama, a, b in NAMESPACE:
            if a <= no <= b:
                data = z.read(entri)            # baca byte mentah 1 citra
                dst = os.path.join(kelas_dir[nama], f"figaro_{nama}_{no:05d}.tif")
                with open(dst, "wb") as f:
                    f.write(data)               # tulis citra ke folder kelas
                salinan += 1
                break
    print(f"[3/3] Tersalin {salinan:,} citra ke 4 folder kelas.")
    for nama, *_ in NAMESPACE:
        n = len(os.listdir(kelas_dir[nama]))
        print(f"      > {nama:<16}  {n} citra")


if __name__ == "__main__":
    unduh()
    z = verifikasi_zip(ZIP_PATH)
    ekstrak_dan_partisi(z)
    print("\nSelesai. Dataset 600 citra RGB siap -> " + DATA_DIR)
