# -*- coding: utf-8 -*-
"""Geometry signal analysis for VISUAL VOLUME (curly/kinky only) — EXPLORATORY.

[WARNING] PROVISIONAL: Volume taxonomy (low/medium/high) is NOT validated.
This analysis is EXPLORATORY ONLY. Do NOT claim classification results.

Joins human ground truth with existing hair_geometry.json to explore
whether geometric features carry signal for human-defined volume classes.

Uses ONLY human annotation as reference.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" annotation\\analyze_volume_geometry_signal.py
  & ".venv\\Scripts\\python.exe" annotation\\analyze_volume_geometry_signal.py --annotator A
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

BASE = Path(__file__).resolve().parents[1]
GT_DIR = BASE / "annotation" / "ground_truth"
GEO_JSON = BASE / "reports" / "hair_geometry.json"
REPORT_DIR = BASE / "annotation" / "reports"

VOLUME_CLASSES = ["low", "medium", "high"]
VOLUME_ORDER = {"low": 0, "medium": 1, "high": 2}

# Features potentially related to visual volume/mass/silhouette
FEATURES = [
    "area_ratio",
    "fill_ratio",
    "solidity",
    "bbox_aspect",
    "bbox_h",
    "bbox_w",
    "span_ratio",
    "face_ratio",
    "thickness_index",
]


def load_human_gt(annotator: str) -> dict:
    """Load human annotations -> {frame: volume label} for curly/kinky only."""
    path = GT_DIR / f"annotator_{annotator}.json"
    if not path.exists():
        raise FileNotFoundError(f"Annotation file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for rec in data:
        if rec.get("hair_type") not in ("curly", "kinky"):
            continue
        if rec.get("ungradable", False):
            continue
        cond = rec.get("conditional_attribute", {})
        if cond.get("value") in VOLUME_ORDER:
            iid = rec["image_id"]
            frame_str = iid.rsplit("/", 1)[-1].split(".")[0]
            try:
                frame = int(frame_str)
            except ValueError:
                continue
            result[frame] = cond["value"]
    return result


def load_geometry() -> dict:
    if not GEO_JSON.exists():
        raise FileNotFoundError(f"Geometry file not found: {GEO_JSON}")
    data = json.loads(GEO_JSON.read_text(encoding="utf-8"))
    return {r["frame"]: r for r in data}


def analyze_feature(feature_name: str, geo: dict, gt: dict) -> dict:
    groups_by_class = defaultdict(list)
    for frame, label in gt.items():
        if frame in geo:
            val = geo[frame].get(feature_name)
            if val is not None:
                groups_by_class[label].append(float(val))

    classes_with_data = [c for c in VOLUME_CLASSES if len(groups_by_class.get(c, [])) > 0]
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
    else:
        result["kruskal_wallis"] = None
        result["note"] = "Insufficient data for Kruskal-Wallis."

    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Geometry signal — VISUAL VOLUME (curly/kinky) [EXPLORATORY].")
    ap.add_argument("--annotator", default="A", help="Annotator to use as reference (default: A)")
    ap.add_argument("--out", default=str(REPORT_DIR / "volume_geometry_signal.json"), help="Output path")
    args = ap.parse_args()

    print("=== Geometry Signal — VISUAL VOLUME (curly/kinky) [EXPLORATORY] ===")
    print(f"Annotator: {args.annotator}")
    print("[WARNING] PROVISIONAL taxonomy — do NOT claim classification results.")
    print()

    try:
        gt = load_human_gt(args.annotator)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        print("Run annotation tool first: python -m annotation.annotation_tool.runner --annotator A")
        return
    print(f"Human GT (volume, curly/kinky): {len(gt)} frames")

    if not gt:
        print("ERROR: No human volume labels found. Run annotation tool first.")
        return

    geo = load_geometry()
    print(f"Geometry records: {len(geo)}")

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
            print(f"  H={kw['H']}, p={kw['p_value']:.6f}, eps²={kw['effect_size_epsilon_squared']}")
        else:
            print(f"  {r.get('note', 'Insufficient data')}")

    signal_features = [f for f, r in results.items() if r.get("kruskal_wallis") and r["kruskal_wallis"].get("p_value", 1.0) < 0.05]

    print(f"\n=== SUMMARY ===")
    print(f"Features with significant signal (p < 0.05): {signal_features}")

    report = {
        "analysis": "volume_geometry_signal",
        "provisional": True,
        "warning": "Volume taxonomy (low/medium/high) is PROVISIONAL and NOT validated. Analysis is EXPLORATORY ONLY.",
        "annotator": args.annotator,
        "n_frames": len(gt),
        "class_distribution": dict(class_dist),
        "features": results,
        "significant_features": signal_features,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport -> {out_path}")


if __name__ == "__main__":
    main()
