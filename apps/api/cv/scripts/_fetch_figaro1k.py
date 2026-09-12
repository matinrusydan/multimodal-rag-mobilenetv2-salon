# -*- coding: utf-8 -*-
# ============================================================================
# _fetch_figaro1k.py  —  Partisi FIGARO-1k  ->  dataset rambut salon (4 kelas)
# ----------------------------------------------------------------------------
# Sumber        : FIGARO-1k (Figaro.zip, 62.7 MiB, 2.107 entri; suda terunduh+divalidasi).
#                 Dataset rambut "in the wild" standar (Universitas Brescia, Figaro1k /
#                 blog www.michelesvanera.org/figaro-1k). Frame00001-01050; class labirin:
#                 straight(1-150), wavy(151-300), curly(301-450), kinky(451-600),
#                 braids(601-750), dreadlocks(751-900), short-men(901-1050).
#
# Lokasi file   : C:\laragon\www\RAG-salon\apps\api\cv\dataset\figaro-1k.zip
# Luaran        : apps/api/cv/dataset/figaro1k/<kelas>/*.jpg  (600 citra, 4x150)
#                 + cv/dataset/figaro1k/_manifest.csv (frame -> kelas -> split)
#
# KELAS RAMBUT SALON (label tetap PRD) : tidak bergantung urutan folder.
#   lurus / bergelombang / keriting / sangat-keriting   (masing-masing 150 citra)
# ============================================================================
import csv, os, re, sys, zipfile

ZIP_CV    = r"C:\laragon\www\RAG-salon\apps\api\cv\dataset\figaro-1k.zip"
CV_AKAR   = r"C:\laragon\www\RAG-salon\apps\api\cv\dataset\figaro1k"

# Petakan nomor frame -> kelas salon (hanya 4 kelas jenis rambut yang dipakai)
LABEL = [
    ("lurus",           1, 150, "straight"),
    ("bergelombang",  151, 300, "wavy"),
    ("keriting",      301, 450, "curly"),
    ("sangat-keriting",451, 600, "kinky"),
]

TUJUAN = {k: os.path.join(CV_AKAR, k) for k, _, _, _ in LABEL}

def buka_zip():
    if not os.path.exists(ZIP_CV):
        raise SystemExit(f"ZIP belum ada: {ZIP_CV}. Jalankan unduhan figaro dulu.")
    return zipfile.ZipFile(ZIP_CV)

def baca_semua_original(z):
    """Kumpulkan {frame_no:int -> nama_entry_org.jpg} dari cabang Original/."""
    pola = re.compile(r"Figaro-1k/Original/.*?/Frame(\d{5})-org\.jpg$", re.I)
    hasil = {}
    for nama in z.namelist():
        m = pola.match(nama)
        if m:
            hasil[int(m.group(1))] = nama       # frame -> path dalam zip
    return hasil  # 1050 citra asli

def partisi():
    os.makedirs(CV_AKAR, exist_ok=True)
    for d in TUJUAN.values():
        os.makedirs(d, exist_ok=True)

    z = buka_zip()
    org = baca_semua_original(z)
    print(f"Citra Original ditemukan di ZIP: {len(org):,} (frame 00001-01050)\n")

    total, manifest = 0, []
    for nama_kelas, mula, akhir, _nama_en in LABEL:
        n = 0
        for no in range(mula, akhir + 1):          # rentang frame kelas ini
            entri = org.get(no)
            if entri is None:
                continue
            data = z.read(entri)                    # byte citra dari dalam zip
            nama_dst = f"{nama_kelas}\\{no:05d}.jpg"
            with open(os.path.join(CV_AKAR, nama_dst), "wb") as f:
                f.write(data)                       # tulis 1 citra ke folder kelas
            split = "train" if n < 120 else "val"  # 120 latih + 30 validasi per kelas
            manifest.append((no, nama_kelas, split, entri))
            n += 1
        total += n
        print(f"   > {nama_kelas:<16} tersalin {n:3d} citra (120 train / 30 val)")

    with open(os.path.join(CV_AKAR, "_manifest.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["frame", "kelas_salon", "split", "name_zip"])
        w.writerows(manifest)
    print(f"\nTotal tersalin: {total:,} citra RGB (4 kelas x 150) -> {CV_AKAR}")
    print("Manifest:  ", os.path.join(CV_AKAR, "_manifest.csv"))
    print("Siap makan  : 208 label training; 60 label validasi; 60 uji (dibuat manual)\n")

if __name__ == "__main__":
    partisi()
