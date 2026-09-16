"""Hair features (HSV stats + GLCM) — pure-numpy port of the calibrated Node
`hairFeatures.ts`, itself a port of `cv/scripts/extract_features.py` (figaro1k).

For the same 224x224 center-crop RGB, results are mathematically identical to the
Node runtime value (same formulas, thresholds, and rounding).
"""

from __future__ import annotations

import math

import numpy as np

GLCM_LEVELS = 32
GLCM_DIST = 1
GLCM_ANGLES = [0.0, math.pi / 4.0, math.pi / 2.0, 3.0 * math.pi / 4.0]

# Calibration from cv/reports/hair_features_report.json (overall, n=600).
RULES = {
    "bleachS": 0.1815,
    "bleachV": 0.7072,
    "dryContrast": 7.7774,
    "dryEnergy": 0.098,
    "textureQ1": 2.9138,
    "textureQ3": 5.5236,
}


def _percentile(sorted_arr: np.ndarray, p: float) -> float:
    if sorted_arr.size == 0:
        return 0.0
    exact = (sorted_arr.size - 1) * p
    lo = int(math.floor(exact))
    hi = int(math.ceil(exact))
    if lo == hi:
        return float(sorted_arr[lo])
    frac = exact - lo
    return float(sorted_arr[lo] + (sorted_arr[hi] - sorted_arr[lo]) * frac)


def round4(x: float) -> float:
    return round(x, 4)


def _rgb_to_hsv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """RGB uint8 -> H(0..360 deg), S(0..1), V(0..1). Percent-sign modulo non-negative."""
    r = rgb[..., 0].astype(np.float64) / 255.0
    g = rgb[..., 1].astype(np.float64) / 255.0
    b = rgb[..., 2].astype(np.float64) / 255.0
    v = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    diff = v - mn
    s = np.where(v > 0, diff / np.where(diff == 0.0, 1.0, v), 0.0)

    h = np.zeros_like(v, dtype=np.float64)
    safe = np.where(diff == 0.0, 1.0, diff)
    pr = diff > 0
    h = np.where((pr) & (v == r), 60.0 * (((g - b) / safe) % 6.0), h)
    h = np.where((pr) & (v == g), 60.0 * ((b - r) / safe + 2.0), h)
    h = np.where((pr) & (v == b), 60.0 * ((r - g) / safe + 4.0), h)
    h = np.where(h < 0.0, h + 360.0, h)
    return h, s, v


def _luma_gray(rgb: np.ndarray) -> np.ndarray:
    """Luma Y' = 0.299R + 0.587G + 0.114B (0..255 uint8), banker's rounding (np.round)."""
    luma = (
        0.299 * rgb[..., 0].astype(np.float64)
        + 0.587 * rgb[..., 1].astype(np.float64)
        + 0.114 * rgb[..., 2].astype(np.float64)
    )
    return np.clip(np.round(luma), 0, 255).astype(np.uint8)


def _glcm_symmetric_normed(q: np.ndarray) -> list[np.ndarray]:
    """GLCM symmetric + normed per angle (equals skimage graycomatrix with those flags)."""
    h, w = q.shape
    mats: list[np.ndarray] = []
    for ang in GLCM_ANGLES:
        dr = round(math.sin(ang) * GLCM_DIST)
        dc = round(math.cos(ang) * GLCM_DIST)
        P = np.zeros((GLCM_LEVELS, GLCM_LEVELS), dtype=np.float64)
        rows, cols = np.indices((h, w))
        isValidR = ((rows + dr >= 0) & (rows + dr < h))[:, :, np.newaxis]
        isValidC = ((cols + dc >= 0) & (cols + dc < w))[:, :, np.newaxis]
        valid = isValidR & isValidC
        # Vectorized pair counting: flatten valid cells in-memory for simplicity.
        rv = rows[valid[..., 0]]
        cv_ = cols[valid[..., 0]]
        i_vals = q[rv, cv_]
        j_vals = q[rv + dr, cv_ + dc]
        np.add.at(P, (i_vals, j_vals), 1)
        # symmetric: P = P + P.T (diagonal doubled), then normed.
        P = P + P.T
        total = P.sum()
        if total == 0:
            total = 1
        mats.append(P / total)
    return mats


def _glcm_props(mats: list[np.ndarray]) -> dict[str, float]:
    """graycoprops-like means + entropy of the mean matrix."""
    accum = {"contrast": 0.0, "dissimilarity": 0.0, "homogeneity": 0.0, "energy": 0.0, "correlation": 0.0}
    n = len(mats)
    p_flat = np.zeros((GLCM_LEVELS, GLCM_LEVELS), dtype=np.float64)

    idx = np.arange(GLCM_LEVELS, dtype=np.float64)
    i_m, j_m = np.meshgrid(idx, idx, indexing="ij")

    for P in mats:
        total = P.sum()
        if total == 0:
            total = 1
        p = P / total
        p_flat += p / n

        d = i_m - j_m
        contrast = float((p * d * d).sum())
        dissimilarity = float((p * np.abs(d)).sum())
        homogeneity = float((p * (1.0 / (1.0 + d * d))).sum())
        energy = float(np.sqrt((p * p).sum()))
        mean_i = float((i_m * p).sum())
        mean_j = float((j_m * p).sum())
        std_i = math.sqrt(float((p * (i_m - mean_i) ** 2).sum()))
        std_j = math.sqrt(float((p * (j_m - mean_j) ** 2).sum()))
        cov = float((p * (i_m - mean_i) * (j_m - mean_j)).sum())
        correlation = 1.0 if (std_i < 1e-15 or std_j < 1e-15) else cov / (std_i * std_j)

        accum["contrast"] += contrast
        accum["dissimilarity"] += dissimilarity
        accum["homogeneity"] += homogeneity
        accum["energy"] += energy
        accum["correlation"] += correlation

    mask = p_flat > 0
    entropy = round4(-float((p_flat[mask] * np.log2(p_flat[mask])).sum()) / math.log2(GLCM_LEVELS * GLCM_LEVELS))
    return {
        "contrast": accum["contrast"] / n,
        "dissimilarity": accum["dissimilarity"] / n,
        "homogeneity": accum["homogeneity"] / n,
        "energy": accum["energy"] / n,
        "correlation": accum["correlation"] / n,
        "entropy": entropy,
    }


def compute_hair_feature_stats(rgb: np.ndarray) -> dict[str, float]:
    """Compute HSV + GLCM stats from a 224x224 RGB uint8 crop."""
    hue, sat, val = _rgb_to_hsv(rgb)
    gray = _luma_gray(rgb)
    # q = clip(floor(gray * levels / 255), 0, levels-1) — identical to Node.
    q = np.clip((gray.astype(np.float64) * GLCM_LEVELS / 255.0).astype(np.int64), 0, GLCM_LEVELS - 1).astype(np.uint8)

    glcm = _glcm_props(_glcm_symmetric_normed(q))

    hue_sorted = np.sort(hue.ravel())
    val_sorted = np.sort(val.ravel())
    sat_flat = sat.ravel()
    hue_flat = hue.ravel()
    val_flat = val.ravel()
    n = hue_flat.size

    return {
        "H_min": float(hue_sorted[0]),
        "H_max": float(hue_sorted[-1]),
        "H_p10": _percentile(hue_sorted, 0.1),
        "H_median": _percentile(hue_sorted, 0.5),
        "H_p90": _percentile(hue_sorted, 0.9),
        "H_std": float(np.std(hue_flat)),
        "S_mean": float(sat_flat.mean()),
        "S_std": float(np.std(sat_flat)),
        "V_mean": float(val_flat.mean()),
        "V_std": float(np.std(val_flat)),
        "V_p10": _percentile(val_sorted, 0.1),
        "V_p90": _percentile(val_sorted, 0.9),
        **glcm,
    }


def hair_color_label(v_mean: float, s_mean: float) -> str:
    """Coarse color label — port of Node `hairColorLabel` / Python `_color_label`."""
    if v_mean < 0.25:
        return "hitam"
    if v_mean < 0.45:
        return "gelap" if s_mean > 0.15 else "abu-gelap"
    if v_mean < 0.65:
        return "cokelat" if s_mean > 0.15 else "abu"
    if v_mean < 0.85:
        if s_mean > 0.18:
            return "terang"
        return "pirang" if s_mean < 0.1 else "cokelat-terang"
    return "pirang" if s_mean < 0.12 else "terang"


def build_hair_features(stats: dict[str, float]) -> dict:
    """Rule thresholds -> HairFeatures for RAG context (identical to Node).

    Catatan: label di sini adalah HEURISTIK dari statistik HSV+GLCM (warna,
    tekstur, dan *indikasi* risiko) — BUKAN diagnosis kondisi rambut terlatih.
    Karena itu kita tidak lagi mengklaim `health: "kering"|"normal"` sebagai
    kondisi pasti; kita hanya menandai adanya indikasi (riskSigns) agar LLM
    tidak menyimpulkan kondisi yang tidak didukung data.
    """
    bleach = stats["S_mean"] < RULES["bleachS"] and stats["V_mean"] >= RULES["bleachV"]
    dry = stats["contrast"] >= RULES["dryContrast"] or stats["energy"] <= RULES["dryEnergy"]
    texture = "halus"
    if stats["contrast"] >= RULES["textureQ3"]:
        texture = "kasar"
    elif stats["contrast"] >= RULES["textureQ1"]:
        texture = "sedang"
    return {
        "color": hair_color_label(stats["V_mean"], stats["S_mean"]),
        "texture": texture,
        # Tidak ada klasifikasi kondisi terlatih → jangan klaim kondisi absolut.
        # Cukup tandai indikasi (lihat riskSigns). Nilai "tidak-diketahui" jujur.
        "health": "tidak-diketahui",
        "riskSigns": {"bleach": bleach, "dry": dry},
    }


def compute_hair_features(rgb: np.ndarray) -> dict:
    """Full one-call contract for the analyze router."""
    return build_hair_features(compute_hair_feature_stats(rgb))