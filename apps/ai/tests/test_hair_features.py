"""Tests for hair_features (HSV stats + GLCM) — pure numpy, no network."""

import numpy as np

from app.cv.hair_features import (
    GLCM_LEVELS,
    build_hair_features,
    compute_hair_feature_stats,
    compute_hair_features,
    hair_color_label,
)


def _solid(rgb, size=224):
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = rgb
    return arr


def test_stats_keys_present():
    stats = compute_hair_feature_stats(_solid((120, 80, 60)))
    expected_keys = {
        "H_min", "H_max", "H_p10", "H_median", "H_p90", "H_std",
        "S_mean", "S_std", "V_mean", "V_std", "V_p10", "V_p90",
        "contrast", "dissimilarity", "homogeneity", "energy", "correlation", "entropy",
    }
    assert expected_keys <= set(stats.keys())


def test_stats_deterministic():
    img = _solid((100, 150, 200))
    a = compute_hair_feature_stats(img)
    b = compute_hair_feature_stats(img)
    for k in a:
        assert a[k] == b[k], f"{k} tidak deterministik"


def test_solid_color_hue_and_saturation():
    # Biru murni: H≈240, S=1, V=1
    stats = compute_hair_feature_stats(_solid((0, 0, 255)))
    assert abs(stats["H_median"] - 240.0) < 1.0
    assert abs(stats["S_mean"] - 1.0) < 1e-6
    assert abs(stats["V_mean"] - 1.0) < 1e-6


def test_grayscale_has_zero_saturation():
    stats = compute_hair_feature_stats(_solid((128, 128, 128)))
    assert stats["S_mean"] < 1e-6


def test_glcm_levels_constant():
    # GLCM quantization level dipakai konsisten (32) — perubahan menggeser semua nilai.
    assert GLCM_LEVELS == 32


def test_hair_color_label_boundaries():
    assert hair_color_label(0.10, 0.5) == "hitam"
    assert hair_color_label(0.30, 0.05) == "abu-gelap"
    assert hair_color_label(0.30, 0.50) == "gelap"
    assert hair_color_label(0.50, 0.50) == "cokelat"
    assert hair_color_label(0.50, 0.05) == "abu"
    assert hair_color_label(0.90, 0.05) == "pirang"
    assert hair_color_label(0.90, 0.50) == "terang"


def test_build_hair_features_no_absolute_health_claim():
    """Anti-halusinasi: health TIDAK boleh mengklaim kondisi absolut."""
    stats = {k: 0.0 for k in (
        "H_min", "H_max", "H_p10", "H_median", "H_p90", "H_std",
        "S_mean", "S_std", "V_mean", "V_std", "V_p10", "V_p90",
        "contrast", "dissimilarity", "homogeneity", "energy", "correlation", "entropy",
    )}
    stats["V_mean"] = 0.5
    stats["S_mean"] = 0.3
    features = build_hair_features(stats)
    assert features["health"] == "tidak-diketahui"
    assert "riskSigns" in features
    assert set(features["riskSigns"]) == {"bleach", "dry"}


def test_build_hair_features_texture_tiers():
    base = {k: 0.0 for k in (
        "H_min", "H_max", "H_p10", "H_median", "H_p90", "H_std",
        "S_mean", "S_std", "V_mean", "V_std", "V_p10", "V_p90",
        "contrast", "dissimilarity", "homogeneity", "energy", "correlation", "entropy",
    )}
    base.update({"V_mean": 0.5, "S_mean": 0.3, "contrast": 1.0, "energy": 0.5})
    assert build_hair_features(base)["texture"] == "halus"
    base["contrast"] = 4.0
    assert build_hair_features(base)["texture"] == "sedang"
    base["contrast"] = 9.0
    assert build_hair_features(base)["texture"] == "kasar"


def test_compute_hair_features_end_to_end():
    features = compute_hair_features(_solid((90, 60, 40)))
    assert features["color"] in {
        "hitam", "gelap", "abu-gelap", "cokelat", "abu", "terang", "pirang", "cokelat-terang",
    }
    assert features["texture"] in {"halus", "sedang", "kasar"}
    assert features["health"] == "tidak-diketahui"
