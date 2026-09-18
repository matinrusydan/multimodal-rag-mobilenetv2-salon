# -*- coding: utf-8 -*-
"""Studi pemisah tipe rambut (Fase 3.1) — khususnya keriting vs sangat-keriting.

Membaca fitur geometris (hair_geometry.json) lalu:
  1. Analisis daya pisah tiap fitur antar kelas (ANOVA-like F, overlap antar-kelas).
  2. Uji pemisah biner keriting vs sangat-keriting (threshold terbaik untuk
     bbox_aspect & solidity), laporan akurasi pemisah sederhana.
  3. Uji hipotesis: apakah 'keriting' condong ke sisi kribo (massa) atau
     bergelombang (panjang) — posisi relatif pusat kelas.
  4. Visualisasi scatter (bbox_aspect vs solidity) + histogram -> PNG.

Output:
  apps/api/cv/reports/hair_separability.json
  apps/api/cv/reports/hair_separability_scatter.png

Jalankan:
  apps\\api\\cv\\.venv\\Scripts\\python.exe apps\\api\\cv\\scripts\\analyze_separability.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"
GEO_JSON = REPORTS / "hair_geometry.json"
OUT_JSON = REPORTS / "hair_separability.json"
OUT_PNG = REPORTS / "hair_separability_scatter.png"

CLASSES = ["lurus", "bergelombang", "keriting", "sangat-keriting"]
FEATURES = ["bbox_aspect", "solidity", "fill_ratio", "span_ratio", "thickness_index", "area_ratio"]

try:
    from PIL import Image, ImageDraw

    HAS_PIL = True
except Exception:
    HAS_PIL = False


def load_rows() -> list[dict]:
    data = json.loads(GEO_JSON.read_text(encoding="utf-8"))
    return [r for r in data if r.get("kelas") in CLASSES]


def feature_matrix(rows: list[dict], feat: str) -> dict[str, np.ndarray]:
    out: dict[str, list[float]] = {c: [] for c in CLASSES}
    for r in rows:
        v = r.get(feat)
        if v is not None:
            out[r["kelas"]].append(float(v))
    return {c: np.array(v) for c, v in out.items() if v}


def f_statistic(groups: list[np.ndarray]) -> float:
    """One-way ANOVA F-statistic (antara-kelas vs dalam-kelas)."""
    groups = [g for g in groups if len(g) > 1]
    if len(groups) < 2:
        return 0.0
    all_vals = np.concatenate(groups)
    grand = all_vals.mean()
    k = len(groups)
    n = len(all_vals)
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_within = sum(((g - g.mean()) ** 2).sum() for g in groups)
    df_b = k - 1
    df_w = n - k
    if df_w <= 0 or ss_within <= 0:
        return 0.0
    return float((ss_between / df_b) / (ss_within / df_w))


def best_threshold(a: np.ndarray, b: np.ndarray) -> dict:
    """Threshold terbaik memisahkan a vs b (cari nilai -> akurasi maksimum)."""
    vals = np.concatenate([a, b])
    labels = np.concatenate([np.zeros(len(a)), np.ones(len(b))])
    order = np.argsort(vals)
    vals_sorted = vals[order]
    labs_sorted = labels[order]
    n = len(vals)
    best = {"threshold": None, "accuracy": 0.0, "direction": None}
    for i in range(1, n):
        thr = (vals_sorted[i - 1] + vals_sorted[i]) / 2
        # a < thr, b >= thr
        pred_lt = (vals < thr).astype(int)  # 0 if < thr else 1
        acc_lt = (pred_lt == labels).mean()
        if acc_lt > best["accuracy"]:
            best = {"threshold": round(float(thr), 4), "accuracy": round(float(acc_lt), 4), "direction": "b>=thr"}
        acc_gt = ((vals >= thr).astype(int) == labels).mean()
        if acc_gt > best["accuracy"]:
            best = {"threshold": round(float(thr), 4), "accuracy": round(float(acc_gt), 4), "direction": "a>=thr"}
    return best


def scatter_png(rows: list[dict]) -> bool:
    if not HAS_PIL:
        return False
    W, H = 760, 560
    M = 70
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    xs = [r["bbox_aspect"] for r in rows if r.get("bbox_aspect") and r.get("solidity")]
    ys = [r["solidity"] for r in rows if r.get("bbox_aspect") and r.get("solidity")]
    if not xs:
        return False
    xmin, xmax = 0.4, max(3.6, max(xs))
    ymin, ymax = 0.4, 1.0

    def px(x):
        return M + (x - xmin) / (xmax - xmin) * (W - 2 * M)

    def py(y):
        return H - M - (y - ymin) / (ymax - ymin) * (H - 2 * M)

    # axes
    d.line([(M, H - M), (W - M, H - M)], fill="black")
    d.line([(M, M), (M, H - M)], fill="black")
    d.text((W // 2 - 60, H - 40), "bbox_aspect (panjang/memanjang) ->", fill="black")
    d.text((10, M // 2), "solidity (kepadatan massa) v", fill="black")

    colors = {
        "lurus": (30, 90, 200),
        "bergelombang": (30, 160, 90),
        "keriting": (230, 160, 20),
        "sangat-keriting": (210, 40, 40),
    }
    for r in rows:
        if not r.get("bbox_aspect") or r.get("solidity") is None:
            continue
        x = px(float(r["bbox_aspect"]))
        y = py(float(r["solidity"]))
        col = colors.get(r["kelas"], (0, 0, 0))
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=col)

    # legend
    lx, ly = W - 230, 30
    for i, c in enumerate(CLASSES):
        d.rectangle([lx, ly + i * 20, lx + 12, ly + 12 + i * 20], fill=colors[c])
        d.text((lx + 18, ly + i * 20), c, fill="black")

    img.save(OUT_PNG)
    return True


def main() -> None:
    rows = load_rows()
    if not rows:
        raise SystemExit(f"tidak ada data di {GEO_JSON} — jalankan extract_hair_geometry.py dulu")

    report: dict = {"n_total": len(rows), "classes": CLASSES, "features": {}}

    # 1. daya pisah per fitur
    for feat in FEATURES:
        g = feature_matrix(rows, feat)
        groups = [g[c] for c in CLASSES if c in g]
        report["features"][feat] = {
            "F_statistic": round(f_statistic(groups), 3),
            "per_class_mean": {c: round(float(g[c].mean()), 4) for c in g},
        }

    # urutkan fitur terbaik
    best_features = sorted(
        report["features"].items(), key=lambda kv: kv[1]["F_statistic"], reverse=True
    )
    report["feature_ranking"] = [k for k, _ in best_features]

    # 2. pemisah biner keriting vs sangat-keriting
    km = feature_matrix(rows, "bbox_aspect")
    sm = feature_matrix(rows, "solidity")
    report["keriting_vs_sangat_keriting"] = {}
    for feat, mat in [("bbox_aspect", km), ("solidity", sm), ("fill_ratio", feature_matrix(rows, "fill_ratio"))]:
        a = mat.get("keriting")
        b = mat.get("sangat-keriting")
        if a is not None and b is not None and len(a) and len(b):
            report["keriting_vs_sangat_keriting"][feat] = best_threshold(a, b)

    # 3. posisi relatif kelas (keriting cenderung kribo atau gelombang?)
    pos = {}
    for feat in ["bbox_aspect", "solidity"]:
        g = feature_matrix(rows, feat)
        pos[feat] = {c: round(float(g[c].mean()), 4) for c in CLASSES if c in g}
    report["class_positions"] = pos

    # hipotesis: keriting lebih dekat ke sangat-keriting (massa) atau bergelombang (panjang)?
    def closeness(feat):
        g = feature_matrix(rows, feat)

        def dist(x, y):
            return abs(float(g[x].mean()) - float(g[y].mean()))

        return {
            "keriting_ke_sangat_keriting": round(dist("keriting", "sangat-keriting"), 4),
            "keriting_ke_bergelombang": round(dist("keriting", "bergelombang"), 4),
            "keriting_ke_lurus": round(dist("keriting", "lurus"), 4),
        }

    report["keriting_affinity"] = {
        "bbox_aspect": closeness("bbox_aspect"),
        "solidity": closeness("solidity"),
    }

    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    png_ok = scatter_png(rows)

    # ringkasan konsol
    print(f"=== Studi pemisah tipe rambut (n={len(rows)}) ===")
    print("\nRanking daya pisah (ANOVA F):")
    for feat, meta in best_features:
        print(f"  {feat:16s} F={meta['F_statistic']:8.3f}  " + " ".join(f"{c[:5]}={meta['per_class_mean'].get(c)}" for c in CLASSES))
    print("\nPemisah keriting vs sangat-keriting:")
    for feat, t in report["keriting_vs_sangat_keriting"].items():
        print(f"  {feat:16s} akurasi={t['accuracy']:.3f} @ threshold={t['threshold']} ({t['direction']})")
    print("\nKedekatan 'keriting' (jarak mean):")
    for feat, d in report["keriting_affinity"].items():
        print(f"  {feat:16s} vs sangat-keriting={d['keriting_ke_sangat_keriting']} | vs bergelombang={d['keriting_ke_bergelombang']} | vs lurus={d['keriting_ke_lurus']}")
    print(f"\nJSON -> {OUT_JSON}")
    print(f"PNG  -> {OUT_PNG if png_ok else '(PIL tidak tersedia)'}")


if __name__ == "__main__":
    main()
