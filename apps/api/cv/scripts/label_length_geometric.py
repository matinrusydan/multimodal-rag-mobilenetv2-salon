# -*- coding: utf-8 -*-
"""Label panjang rambut 4 kelas dari fitur geometris (Metode B) — Fase 3.2.

Mengikuti arahan: parameter panjang per tipe rambut berbeda.
  - lurus/bergelombang : PRIORITAS panjang (span/bbox memanjang + face_ratio)
  - keriting           : MIX panjang + ketebalan (bobot seimbang)
  - sangat-keriting    : PRIORITAS ketebalan/massa (bulk), panjang visual menipu

Skor "panjang efektif" per citra:
  score = w_panjang * z(panjang) + w_tebal * z(ketebalan)
  di mana panjang = kombinasi(bbox_aspect, face_ratio, span_ratio)
        ketebalan = kombinasi(solidity_inv, fill_ratio)  [massa padat -> panjang asli besar]

Bobot per tipe (dari hipotesis Fase 3.1):
  lurus, bergelombang : (0.85 panjang, 0.15 tebal)
  keriting            : (0.55 panjang, 0.45 tebal)
  sangat-keriting     : (0.35 panjang, 0.65 tebal)

Kelas 4 tingkat dibentuk dari kuartil skor (per dataset) -> pendek, pendek-menengah,
menengah, panjang.

Output:
  apps/api/cv/dataset/hair_length_geometris/  (manifest json + salinan .pt akan dibuat di Fase 3.3)
  apps/api/cv/reports/hair_length_geometris.json

Jalankan (venv CV atau global; hanya numpy):
  apps\\api\\cv\\.venv\\Scripts\\python.exe apps\\api\\cv\\scripts\\label_length_geometric.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"
GEO_JSON = REPORTS / "hair_geometry.json"
OUT_JSON = REPORTS / "hair_length_geometris.json"
OUT_DIR = BASE / "dataset" / "hair_length_geometris"

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]

# bobot (panjang, tebal) per tipe rambut — hipotesis dari studi pemisah 3.1
WEIGHTS = {
    "lurus": (0.85, 0.15),
    "bergelombang": (0.80, 0.20),
    "keriting": (0.55, 0.45),
    "sangat-keriting": (0.35, 0.65),
}


def zscore(arr: np.ndarray) -> np.ndarray:
    mu = arr.mean()
    sd = arr.std() or 1.0
    return (arr - mu) / sd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()

    rows = json.loads(GEO_JSON.read_text(encoding="utf-8"))
    rows = [r for r in rows if r.get("kelas") in WEIGHTS]
    if not rows:
        raise SystemExit("tidak ada data geometris — jalankan extract_hair_geometry.py dulu")

    # fitur mentah
    bbox_aspect = np.array([r["bbox_aspect"] for r in rows], dtype=float)
    span_ratio = np.array([r["span_ratio"] for r in rows], dtype=float)
    face_ratio = np.array([r.get("face_ratio") or r["span_ratio"] for r in rows], dtype=float)
    solidity = np.array([r["solidity"] for r in rows], dtype=float)
    fill_ratio = np.array([r["fill_ratio"] for r in rows], dtype=float)

    # panjang: gabungan sinyal memanjang. z-score dinormalisasi antar-citra.
    panjang = (zscore(bbox_aspect) + zscore(span_ratio) + zscore(face_ratio)) / 3.0
    # ketebalan/massa: solidity rendah & fill rendah -> coil/berkembang -> panjang asli lebih
    # (kita balik tandanya: kerapatan tinggi cenderung rambut lurus panjang terlihat)
    tebal = (zscore(solidity) + zscore(fill_ratio)) / 2.0

    scores = []
    for r, p, t in zip(rows, panjang, tebal, strict=False):
        wp, wt = WEIGHTS[r["kelas"]]
        scores.append(wp * p + wt * t)
    scores_arr = np.array(scores)

    # kuartil -> 4 kelas panjang (global, tanpa memandang tipe)
    qs = np.quantile(scores_arr, [0.25, 0.5, 0.75])

    def kelas_from_score(s: float) -> str:
        if s <= qs[0]:
            return LENGTH_CLASSES[0]
        if s <= qs[1]:
            return LENGTH_CLASSES[1]
        if s <= qs[2]:
            return LENGTH_CLASSES[2]
        return LENGTH_CLASSES[3]

    records = []
    for r, s in zip(rows, scores_arr, strict=False):
        records.append(
            {
                "frame": r["frame"],
                "tipe": r["kelas"],
                "panjang_label": kelas_from_score(float(s)),
                "score": round(float(s), 5),
                "bbox_aspect": r["bbox_aspect"],
                "solidity": r["solidity"],
                "span_ratio": r["span_ratio"],
                "face_ratio": r.get("face_ratio"),
            }
        )

    # distribusi
    dist: dict[str, dict[str, int]] = {}
    for tipe in WEIGHTS:
        dist[tipe] = {c: 0 for c in LENGTH_CLASSES}
    for rec in records:
        dist[rec["tipe"]][rec["panjang_label"]] += 1

    report = {
        "method": "geometric",
        "length_classes": LENGTH_CLASSES,
        "weights_per_type": {k: {"panjang": v[0], "tebal": v[1]} for k, v in WEIGHTS.items()},
        "quartiles": {"q25": round(float(qs[0]), 5), "q50": round(float(qs[1]), 5), "q75": round(float(qs[2]), 5)},
        "distribution_per_type": dist,
        "n": len(records),
        "records": records,
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # tulis manifest ringkas untuk dipakai Fase 3.3
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {f"{r['frame']:05d}": r["panjang_label"] for r in records}
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== Label geometris (n={len(records)}) ===")
    print(f"kuartil skor: {report['quartiles']}")
    for tipe, d in dist.items():
        print(f"  {tipe:16s} " + " ".join(f"{c[:8]}={d[c]}" for c in LENGTH_CLASSES))
    print(f"\nJSON     -> {args.out}")
    print(f"Manifest -> {OUT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    main()
