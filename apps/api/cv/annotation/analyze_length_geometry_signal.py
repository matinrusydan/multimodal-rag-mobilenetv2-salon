# -*- coding: utf-8 -*-
"""E0 Gate: Geometry signal analysis for hair LENGTH (straight/wavy only).

Joins human ground truth (annotator_A or adjudicated) with existing hair_geometry.json
to test whether geometric features carry signal for human-defined length classes.

Uses ONLY human annotation as ground truth. Gemini/geometric pseudo-labels are NOT used.

Statistical tests:
  - Kruskal-Wallis H (non-parametric ANOVA) via scipy.stats
  - Effect size epsilon-squared: eps^2 = (H - (k - 1)) / (n - 1)
  - Pairwise Mann-Whitney U + Holm correction (manual)

Features tested:
  bbox_aspect, bbox_h, bbox_w, span_ratio, face_ratio, area_ratio, fill_ratio, solidity

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" annotation\\analyze_length_geometry_signal.py
  & ".venv\\Scripts\\python.exe" annotation\\analyze_length_geometry_signal.py --annotator A
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

BASE = Path(__file__).resolve().parents[1]  # apps/api/cv
GT_DIR = BASE / "annotation" / "ground_truth"
GEO_JSON = BASE / "reports" / "hair_geometry.json"
REPORT_DIR = BASE / "annotation" / "reports"

LENGTH_CLASSES = ["short", "shoulder", "mid_back", "long"]
LENGTH_ORDER = {"short": 0, "shoulder": 1, "mid_back": 2, "long": 3}
FEATURES = [
    "bbox_aspect",
    "bbox_h",
    "bbox_w",
    "span_ratio",
    "face_ratio",
    "area_ratio",
    "fill_ratio",
    "solidity",
]


def load_human_gt(annotator: str) -> dict:
    """Load human annotations and return dict: frame_id -> length label (or None)."""
    path = GT_DIR / f"annotator_{annotator}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Annotation file not found: {path}\nRun annotation tool first."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for rec in data:
        if rec.get("hair_type") not in ("straight", "wavy"):
            continue
        if rec.get("ungradable", False):
            continue
        cond = rec.get("conditional_attribute", {})
        if cond.get("value") in LENGTH_ORDER:
            # Extract frame number from image_id (e.g. figaro1k/lurus/00029.jpg -> 00029 -> 29)
            iid = rec["image_id"]
            frame_str = iid.rsplit("/", 1)[-1].split(".")[0]
            try:
                frame = int(frame_str)
            except ValueError:
                continue
            result[frame] = cond["value"]
    return result


def load_geometry() -> dict:
    """Load hair_geometry.json -> {frame: feature_dict}."""
    if not GEO_JSON.exists():
        raise FileNotFoundError(
            f"Geometry file not found: {GEO_JSON}\nRun extract_hair_geometry.py first."
        )
    data = json.loads(GEO_JSON.read_text(encoding="utf-8"))
    return {r["frame"]: r for r in data}


def mann_whitney_holm(groups: list[list[float]], labels: list[str]) -> list[dict]:
    """Pairwise Mann-Whitney U with Holm-Bonferroni correction (manual)."""
    n_groups = len(groups)
    pairs = []
    for i in range(n_groups):
        for j in range(i + 1, n_groups):
            if len(groups[i]) < 2 or len(groups[j]) < 2:
                pairs.append(
                    {"pair": f"{labels[i]} vs {labels[j]}", "p_value": None, "significant": None}
                )
                continue
            try:
                _, p = stats.mannwhitneyu(groups[i], groups[j], alternative="two-sided")
            except Exception:
                p = float("nan")
            pairs.append({"pair": f"{labels[i]} vs {labels[j]}", "p_value": float(p)})

    # Holm correction
    m = len(pairs)
    sorted_idx = sorted(range(m), key=lambda k: pairs[k]["p_value"] or 1.0)
    holm_sig = [False] * m
    for rank, idx in enumerate(sorted_idx):
        p = pairs[idx]["p_value"]
        if p is None:
            continue
        threshold = 0.05 / (m - rank)
        if p < threshold:
            holm_sig[idx] = True
        else:
            break  # Holm stops at first non-significant

    for idx, pair in enumerate(pairs):
        pair["holm_significant"] = holm_sig[idx]

    return pairs


def analyze_feature(feature_name: str, geo: dict, gt: dict) -> dict:
    """Analyze one feature: distribution per class + Kruskal-Wallis + effect size."""
    groups_by_class = defaultdict(list)
    for frame, label in gt.items():
        if frame in geo:
            val = geo[frame].get(feature_name)
            if val is not None:
                groups_by_class[label].append(float(val))

    # Only classes with data
    classes_with_data = [c for c in LENGTH_CLASSES if len(groups_by_class.get(c, [])) > 0]
    groups = [groups_by_class[c] for c in classes_with_data]

    result = {
        "feature": feature_name,
        "n_total": sum(len(g) for g in groups),
        "per_class": {},
    }

    for cls, vals in zip(classes_with_data, groups, strict=False):
        arr = np.array(vals) if vals else np.array([])
        result["per_class"][cls] = {
            "n": len(arr),
            "median": float(np.median(arr)) if len(arr) else None,
            "iqr_q1": float(np.percentile(arr, 25)) if len(arr) else None,
            "iqr_q3": float(np.percentile(arr, 75)) if len(arr) else None,
            "mean": float(np.mean(arr)) if len(arr) else None,
            "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else None,
        }

    # Kruskal-Wallis (need at least 2 groups with data)
    if len(groups) >= 2 and all(len(g) >= 2 for g in groups):
        try:
            h_stat, p_value = stats.kruskal(*groups)
            k = len(groups)
            n = sum(len(g) for g in groups)
            eps_sq = (h_stat - (k - 1)) / (n - 1) if n > 1 else float("nan")
            result["kruskal_wallis"] = {
                "H": round(float(h_stat), 4),
                "p_value": float(p_value),
                "k_groups": k,
                "n_total": n,
                "effect_size_epsilon_squared": round(float(eps_sq), 6),
            }
        except Exception as exc:
            result["kruskal_wallis"] = {"error": str(exc)}

        # Pairwise
        result["pairwise_mann_whitney_holm"] = mann_whitney_holm(groups, classes_with_data)
    else:
        result["kruskal_wallis"] = None
        result["pairwise_mann_whitney_holm"] = None
        result["note"] = "Insufficient data for Kruskal-Wallis (need >=2 groups with >=2 samples each)."

    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="E0 Gate: geometry signal for hair LENGTH (human GT).")
    ap.add_argument("--annotator", default="A", help="Annotator to use as GT (default: A)")
    ap.add_argument("--out", default=str(REPORT_DIR / "length_geometry_signal.json"), help="Output path")
    args = ap.parse_args()

    print("=== E0: Geometry Signal Analysis — LENGTH (straight/wavy) ===")
    print(f"Using annotator: {args.annotator}")
    print()

    try:
        gt = load_human_gt(args.annotator)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        print("Run annotation tool first: python -m annotation.annotation_tool.runner --annotator A")
        return
    print(f"Human GT (length, straight/wavy only): {len(gt)} frames")

    if not gt:
        print("ERROR: No human length labels found. Run annotation tool first.")
        return

    geo = load_geometry()
    print(f"Geometry records: {len(geo)}")

    # Class distribution
    from collections import Counter
    class_dist = Counter(gt.values())
    print(f"Class distribution: {dict(class_dist)}")
    print()

    results = {}
    for feat in FEATURES:
        print(f"--- {feat} ---")
        r = analyze_feature(feat, geo, gt)
        results[feat] = r
        if r.get("kruskal_wallis"):
            kw = r["kruskal_wallis"]
            print(f"  Kruskal-Wallis H={kw['H']}, p={kw['p_value']:.6f}, eps²={kw['effect_size_epsilon_squared']}")
        else:
            print(f"  {r.get('note', 'No Kruskal-Wallis (insufficient data)')}")

    # Summary: which features have signal?
    signal_features = []
    for feat, r in results.items():
        kw = r.get("kruskal_wallis")
        if kw and kw.get("p_value", 1.0) < 0.05:
            signal_features.append(feat)

    print(f"\n=== SUMMARY ===")
    print(f"Features with significant signal (p < 0.05): {signal_features}")
    print(f"Total features tested: {len(FEATURES)}")

    report = {
        "analysis": "length_geometry_signal",
        "annotator": args.annotator,
        "n_frames": len(gt),
        "class_distribution": dict(class_dist),
        "features": results,
        "significant_features": signal_features,
        "note": (
            "This is E0 Gate. If NO features have significant signal, "
            "geometry-only approach for length is NOT supported by human GT. "
            "Use human GT as reference; Gemini/geometric pseudo-labels were NOT used."
        ),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport -> {out_path}")


if __name__ == "__main__":
    main()
