# -*- coding: utf-8 -*-
# ============================================================================
# _make_hair_fixture.py — Fixture deterministik hair features untuk uji Node.
# ----------------------------------------------------------------------------
# 1) Baca satu citra nyata figaro1k, hitung ROI 224x224 (pipeline sama),
# 2) simpan crop KOMPOSISI RGB polos ke `tests/fixtures/hair_roi.raw`,
# 3) hitung stats hair features dengan fungsi yang SAMA -> `expected.json`.
#
# Node test membaca .raw (byte persis) lalu membandingkan komputasinya dengan
# expected.json — menguji kesamaan MATEMATIKA port, terlepas dari perbedaan
# preprocessing (sharp vs cv2) yang sudah terpisah scope-nya.
# ============================================================================
from __future__ import annotations

import json
import sys
from pathlib import Path

_PIKE_ARG = sys.argv[1] if len(sys.argv) > 1 else ""
# extract_features membaca sys.argv[1] sebagai MAX_PER_CLASS — netralkan dulu.
sys.argv = ["_make_hair_fixture.py"]

import numpy as np

from extract_features import _extract, _roi, _load_rgb

PENGGUNAAN = "python _make_hair_fixture.py <gambar.jpg>"

def main() -> int:
    if not _PIKE_ARG:
        print("Gunakan:", PENGGUNAAN, file=sys.stderr)
        return 1
    gambar = Path(_PIKE_ARG)
    img = _load_rgb(gambar)
    if img is None:
        print(f"ERROR: tidak bisa membaca citra {gambar}", file=sys.stderr)
        return 1
    roi = _roi(img)
    stats = _extract(img)
    stats.pop("file", None)
    stats.pop("kelas", None)
    stats.pop("warna", None)

    fixtures = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    raw = fixtures / "hair_roi.raw"
    raw.write_bytes(np.ascontiguousarray(roi, dtype=np.uint8).tobytes())

    expected = {k: round(float(v), 8) for k, v in stats.items()}
    text = json.dumps(expected, ensure_ascii=False, indent=2) + "\n"
    (fixtures / "hair_features.expected.json").write_text(text, encoding="utf-8", newline="\n")
    print(f"ROI        -> {raw} ({roi.shape})")
    print(f"Expected   -> {fixtures / 'hair_features.expected.json'}")
    print("Stats sample:", json.dumps(expected, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())