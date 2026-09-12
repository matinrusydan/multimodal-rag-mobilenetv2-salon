# -*- coding: utf-8 -*-
# ============================================================================
# _verify_dataset.py — Verifikasi metadata Figaro1k partisi salon (Phase 07 CV)
# ----------------------------------------------------------------------------
# Membaca langsung citra nyata dari disk untuk menghasilkan angka laporan:
#   ukuran dimensi (resolusi spatial), jumlah channel, bit-depth, dtype,
#   rentang resolusi tiap kelas. Output berupa tabel ringkas + data JSON.
# ============================================================================
import json, os, glob, cv2, numpy as np

CV_AKAR = r"C:\laragon\www\RAG-salon\apps\api\cv\dataset\figaro1k"
KELAS   = ["lurus", "bergelombang", "keriting", "sangat-keriting"]

def cari_citra(kelas, split="train", maks=10):
    sub = os.path.join(CV_AKAR, kelas, f"train") if False else os.path.join(CV_AKAR, kelas)
    hasil = sorted(glob.glob(os.path.join(sub, "*.jpg")))[:maks]
    return hasil

def metadata(nama):
    img = cv2.imread(nama, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    bit = int(8 * np.dtype(img.dtype).itemsize)
    if img.ndim == 2:
        r, c = img.shape; ch = 1
    else:
        r, c, ch = img.shape
    return {"file": os.path.basename(nama), "dimensi": f"{c}x{r}",
            "channel": ch, "bit": bit, "dtype": str(img.dtype),
            "shape": list(img.shape)}

laporan = {"dataset": "FIGARO-1k (partisi salon 4 kelas)", "kelas": {}}
for k in KELAS:
    daftar = cari_citra(k)
    md = [metadata(n) for n in daftar]
    md = [m for m in md if m]
    if not md:
        continue
    dims = [m["dimensi"] for m in md]
    ch = {m["channel"] for m in md}
    bit = {m["bit"] for m in md}
    laporan["kelas"][k] = {
        "sample_terbaca": len(md),
        "channel": sorted(ch), "bit_depth": sorted(bit),
        "dtype": sorted({m["dtype"] for m in md}),
        "contoh_dimensi": dims,
    }

# ---------------------------------------------------------------
# Tabel ringkas
# ---------------------------------------------------------------
print("=" * 92)
print("LAPORAN METADATA DATASET - FIGARO-1k -> KELAS RAMBUT SALON (Phase 07 CV)")
print("=" * 92)
print(f"{'Kelas':<18}{'Sample':<8}{'Channel':<9}{'Bit-depth':<10}{'dtype':<8} Dimensi contoh (WxH)")
print("-" * 92)
for k, info in laporan["kelas"].items():
    print(f"{k:<18}{info['sample_terbaca']:<8}"
          f"{str(info['channel']):<9}{str(info['bit_depth']):<10}"
          f"{str(info['dtype']):<8} {', '.join(info['contoh_dimensi'][:10])}")
print("-" * 92)
print("Kesimpulan: citra salon dipartisi dari FIGARO-1k (RGB 24-bit, 3 channel,")
print("resolusi bervariasi -> dinormalisasi 256 keep-aspect -> center-crop 224")
print("sesuai pipeline preprocessing Phase 07.)")

# Simpan laporan JSON
path_lapor = os.path.join(CV_AKAR, "_report_figaro1k.json")
with open(path_lapor, "w", encoding="utf-8") as f:
    json.dump(laporan, f, ensure_ascii=False, indent=2)
print("\nLaporan JSON :", path_lapor)
