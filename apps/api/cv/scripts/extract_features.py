# -*- coding: utf-8 -*-
"""Extract HSV + GLCM hair features (Opsi 3 hibrida) — analisis & kalibrasi.

Fase analisis OFFLINE di Python untuk hair features (task 07-cv.md §2).
ROI mengikuti pipeline inti: RGB 8-bit sRGB, auto-orient EXIF, resize keep-aspect
(sisi pendek 256), center-crop 224. Dari ROI tersebut dihitung:

  - HSV stats: mean/std Hue, Saturation, Value (lightness), persentil V (P10/P90).
  - GLCM (scikit-image, levels=32, 4 offset): contrast, dissimilarity,
    homogeneity, energy, correlation + entropy(total).

Output:
  apps/api/cv/reports/hair_features_report.json  (statistik per kelas + sample)
  apps/api/cv/reports/hair_scatter.png           (scatter S vs V per kelas)

Kalibrasi rule (proposal, TANPA label baru — deskriptif):
  - bleach: Saturation_mean rendah & Value_mean tinggi  (warna pucat, terang)
  - dry   : GLCM contrast tinggi & energy rendah        (tekstur kasar/kusam)

Catatan: angka di sini hanya kalibrasi; formula final di-port ke
CvService.ts (Node) harus menghasilkan nilai IDENTIK untuk citra yang sama.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from statistics import median

import cv2
import numpy as np
from PIL import Image, ImageOps
from skimage.feature import graycomatrix, graycoprops

BASE = Path(__file__).resolve().parents[1]
DATASET = BASE / "dataset" / "figaro1k"
REPORTS = BASE / "reports"
REPORT_JSON = REPORTS / "hair_features_report.json"
SCATTER_PNG = REPORTS / "hair_scatter.png"

CLASSES = ["lurus", "bergelombang", "keriting", "sangat-keriting"]

RESIZE_SIDE = 256
CROP = 224
MIN_SIDE = 224
GLCM_LEVELS = 32
GLCM_ANGLES = [0, math.pi / 4, math.pi / 2, 3 * math.pi / 4]

# Batasi jumlah citra per kelas (default semua; kecilkan untuk smoke cepat)
MAX_PER_CLASS = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # 0 = semua


def _load_rgb(path: Path) -> np.ndarray | None:
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode != "RGB" or min(im.size) < MIN_SIDE:
                return None
            return np.asarray(im.convert("RGB"))
    except Exception:
        return None


def _roi(img: np.ndarray) -> np.ndarray:
    """Resize keep-aspect sisi pendek 256 -> center-crop 224 (identik training val)."""
    h, w = img.shape[:2]
    scale = RESIZE_SIDE / min(h, w)
    rw = max(CROP, int(round(w * scale)))
    rh = max(CROP, int(round(h * scale)))
    resized = cv2.resize(img, (rw, rh), interpolation=cv2.INTER_LINEAR)
    left = (rw - CROP) // 2
    top = (rh - CROP) // 2
    return resized[top : top + CROP, left : left + CROP]


def _rgb_to_hsv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """RGB (uint8, 0..255) -> H (0..360 derajat), S (0..1), V/lightness (0..1).

    Formula manual float64 — HARUS identik dengan implementasi Node (hairFeatures.ts)
    yang akan di-port, sehingga hasil Python == hasil runtime untuk citra yang sama.
    """
    r = rgb[..., 0].astype(np.float64) / 255.0
    g = rgb[..., 1].astype(np.float64) / 255.0
    b = rgb[..., 2].astype(np.float64) / 255.0
    v = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    diff = v - mn
    s = np.where(v > 0, diff / np.where(diff == 0, 1, v), 0.0)

    h = np.zeros_like(v, dtype=np.float64)
    pr = diff > 0
    h = np.where((pr) & (v == r), 60.0 * ((g - b) / np.where(diff == 0, 1, diff) % 6.0), h)
    h = np.where((pr) & (v == g), 60.0 * (((b - r) / np.where(diff == 0, 1, diff)) + 2.0), h)
    h = np.where((pr) & (v == b), 60.0 * (((r - g) / np.where(diff == 0, 1, diff)) + 4.0), h)
    h = np.where(h < 0, h + 360.0, h)
    return h, s, v


def _luma_gray(rgb: np.ndarray) -> np.ndarray:
    """Luma Y' = 0.299R + 0.587G + 0.114B (0..255 uint8) — sama dgn RGB2GRAY OpenCV."""
    luma = (
        0.299 * rgb[..., 0].astype(np.float64)
        + 0.587 * rgb[..., 1].astype(np.float64)
        + 0.114 * rgb[..., 2].astype(np.float64)
    )
    return np.clip(np.round(luma), 0, 255).astype(np.uint8)


def _glcm_stats(gray: np.ndarray) -> dict[str, float]:
    # q = clip(floor(gray * levels/255), 0, levels-1) — harus identik dengan Node.
    g = np.clip((gray.astype(np.float64) * GLCM_LEVELS / 255.0).astype(np.int64), 0, GLCM_LEVELS - 1)
    p = graycomatrix(
        g, distances=[1], angles=GLCM_ANGLES, levels=GLCM_LEVELS, symmetric=True, normed=True
    )
    props = {}
    for name in ("contrast", "dissimilarity", "homogeneity", "energy", "correlation"):
        vals = graycoprops(p, name)
        props[name] = float(np.mean(vals))
    p_flat = np.mean(p, axis=(2, 3))
    mask = p_flat > 0
    entropy = float(-np.sum(p_flat[mask] * np.log2(p_flat[mask])))
    props["entropy"] = round(entropy / math.log2(GLCM_LEVELS * GLCM_LEVELS), 4)
    return props


def _extract(img: np.ndarray) -> dict[str, float]:
    roi = _roi(img)
    hue_deg, sat, lig = _rgb_to_hsv(roi)
    gray = _luma_gray(roi)
    glcm = _glcm_stats(gray)

    return {
        "H_min": float(np.min(hue_deg)),
        "H_max": float(np.max(hue_deg)),
        "H_p10": float(np.percentile(hue_deg, 10)),
        "H_median": float(np.percentile(hue_deg, 50)),
        "H_p90": float(np.percentile(hue_deg, 90)),
        "H_std": float(np.std(hue_deg)),
        "S_mean": float(np.mean(sat)),
        "S_std": float(np.std(sat)),
        "V_mean": float(np.mean(lig)),
        "V_std": float(np.std(lig)),
        "V_p10": float(np.percentile(lig, 10)),
        "V_p90": float(np.percentile(lig, 90)),
        **glcm,
    }


def _percentiles(col: list[float]) -> dict[str, float]:
    if not col:
        return {"n": 0, "min": 0.0, "p10": 0.0, "median": 0.0, "p90": 0.0, "max": 0.0, "mean": 0.0}
    arr = sorted(col)
    n = len(arr)
    def q(p):
        k = (n - 1) * p
        lo = math.floor(k)
        hi = math.ceil(k)
        return arr[lo] + (arr[hi] - arr[lo]) * (k - lo) if lo != hi else arr[lo]
    return {
        "n": n,
        "min": round(arr[0], 4),
        "p10": round(q(0.10), 4),
        "p25": round(q(0.25), 4),
        "median": round(q(0.50), 4),
        "p75": round(q(0.75), 4),
        "p90": round(q(0.90), 4),
        "max": round(arr[-1], 4),
        "mean": round(sum(arr) / n, 4),
    }


def _color_label(v_mean: float, s_mean: float) -> str:
    # HSV -> kategori warna kasar berbasis V (lightness) + S (kroma)
    if v_mean < 0.25:
        return "hitam"
    if v_mean < 0.45:
        return "gelap" if s_mean > 0.15 else "abu-gelap"
    if v_mean < 0.65:
        return "cokelat" if s_mean > 0.15 else "abu"
    if v_mean < 0.85:
        return "terang" if s_mean > 0.18 else "pirang" if s_mean < 0.10 else "cokelat-terang"
    return "pirang" if s_mean < 0.12 else "terang"


def main() -> None:
    if not DATASET.exists():
        print(f"ERROR: dataset tidak ditemukan: {DATASET}", file=sys.stderr)
        sys.exit(1)
    REPORTS.mkdir(parents=True, exist_ok=True)

    per_class: dict[str, list[dict]] = {c: [] for c in CLASSES}
    samples: list[dict] = []
    grand = {k: [] for k in [
        "H_median", "H_std", "S_mean", "S_std", "V_mean", "V_std", "V_p10", "V_p90",
        "contrast", "dissimilarity", "homogeneity", "energy", "correlation", "entropy",
    ]}

    for cls in CLASSES:
        files = sorted((DATASET / cls).glob("*.jpg"))
        if MAX_PER_CLASS > 0:
            files = files[:MAX_PER_CLASS]
        for path in files:
            img = _load_rgb(path)
            if img is None:
                continue
            feats = _extract(img)
            feats["file"] = path.name
            feats["kelas"] = cls
            feats["warna"] = _color_label(feats["V_mean"], feats["S_mean"])
            per_class[cls].append(feats)
            samples.append(feats | {"source": str(path.name)})
            for k in grand:
                grand[k].append(feats[k])

    stats = {c: {k: _percentiles([f[k] for f in items]) for k in grand} for c, items in per_class.items()}
    overall = {k: _percentiles(v) for k, v in grand.items()}

    # Kalibrasi rule (proposal deskriptif): threshold dari persentil gabungan
    s_p25 = overall["S_mean"]["p10"]
    v_p75 = overall["V_mean"]["p90"]
    c_p75 = overall["contrast"]["p90"]
    e_low = overall["energy"]["p10"]
    rule = {
        "bleach": {
            "desc": "S_mean < S_p10_gabungan DAN V_mean >= V_p90_gabungan",
            "s_threshold": s_p25,
            "v_threshold": v_p75,
        },
        "dry": {
            "desc": "GLCM contrast >= contrast_p90_gabungan OR energy <= energy_p10_gabungan",
            "contrast_threshold": c_p75,
            "energy_threshold": e_low,
        },
    }

    report = {
        "dataset": "figaro1k (4 kelas jenis rambut)",
        "roi_pipeline": "RGB sRGB -> exif_transpose -> resize keep-aspect 256 -> center-crop 224",
        "feature_set": "HSV stats (H/S/V mean,std,persentil H) + GLCM(levels=32) contrast/dissimilarity/homogeneity/energy/correlation/entropy",
        "per_kelas": stats,
        "overall": overall,
        "rule_proposal": rule,
        "note": "Kalibrasi DESKRIPTIF tanpa label kondisi ground-truth. Validasi akhir via Node port.",
        "samples": samples[: min(len(samples), 24)],
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Scatter S vs V
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 5))
        colors = {"lurus": "#1f77b4", "bergelombang": "#ff7f0e", "keriting": "#2ca02c", "sangat-keriting": "#d62728"}
        for cls in CLASSES:
            xs = [f["S_mean"] for f in per_class[cls]]
            ys = [f["V_mean"] for f in per_class[cls]]
            ax.scatter(xs, ys, s=18, alpha=0.6, label=cls, color=colors[cls])
        ax.set_xlabel("Saturation mean")
        ax.set_ylabel("Value (lightness) mean")
        ax.set_title("Hair features — HSV S vs V per jenis rambut")
        ax.legend()
        fig.tight_layout()
        fig.savefig(SCATTER_PNG, dpi=110)
        print("Scatter ->", SCATTER_PNG)
    except Exception as e:  # non-fatal
        print(f"WARN: scatter gagal: {e}", file=sys.stderr)

    print(f"\nSELESAI. Citra dianalisis: {sum(len(v) for v in per_class.values())}")
    print("Report JSON ->", REPORT_JSON)
    for cls in CLASSES:
        n = len(per_class[cls])
        if n:
            v = per_class[cls][-1]
            print(f"  {cls:<16} n={n:<4} contoh: S={v['S_mean']:.2f} V={v['V_mean']:.2f} "
                  f"warna={v['warna']} contrast={v['contrast']:.2f} entropy={v['entropy']:.2f}")


if __name__ == "__main__":
    main()