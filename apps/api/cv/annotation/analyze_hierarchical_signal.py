# -*- coding: utf-8 -*-
"""Hierarchical signal analysis — cross-level: hair_type vs conditional_attribute.

Investigates whether the conditional attribute (length/volume) distribution
differs significantly across hair types. This is NOT a model evaluation.

Questions:
  - Does length distribution differ between straight and wavy?
  - Does volume distribution differ between curly and kinky?
  - Are there systematic patterns (e.g. kinky more likely high-volume)?

Uses ONLY human annotation. No pseudo-labels.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" annotation\\analyze_hierarchical_signal.py
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
REPORT_DIR = BASE / "annotation" / "reports"


def load_human_gt(annotator: str) -> list[dict]:
    path = GT_DIR / f"annotator_{annotator}.json"
    if not path.exists():
        raise FileNotFoundError(f"Annotation file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [r for r in data if not r.get("ungradable", False)]


def analyze_length_by_type(records: list[dict]) -> dict:
    """Length distribution: straight vs wavy."""
    length_records = [r for r in records if r.get("hair_type") in ("straight", "wavy")]
    if not length_records:
        return {"error": "No straight/wavy records", "n": 0}

    by_type = defaultdict(list)
    for r in length_records:
        cond = r.get("conditional_attribute", {})
        val = cond.get("value")
        if val:
            by_type[r["hair_type"]].append(val)

    # Chi-square: does length distribution differ by type?
    types_with_data = [t for t in ("straight", "wavy") if len(by_type.get(t, [])) > 0]
    length_classes = ["short", "shoulder", "mid_back", "long"]

    # Build contingency table
    table = []
    for t in types_with_data:
        counts = Counter(by_type[t])
        table.append([counts.get(c, 0) for c in length_classes])

    result = {
        "n_total": len(length_records),
        "by_type": {t: dict(Counter(by_type[t])) for t in types_with_data},
        "contingency_table": table,
        "length_classes": length_classes,
        "types": types_with_data,
    }

    if len(table) >= 2 and len(table[0]) >= 2:
        try:
            chi2, p, dof, expected = stats.chi2_contingency(np.array(table))
            result["chi_square"] = {
                "chi2": round(float(chi2), 4),
                "p_value": float(p),
                "dof": int(dof),
            }
        except Exception as exc:
            result["chi_square"] = {"error": str(exc)}

    return result


def analyze_volume_by_type(records: list[dict]) -> dict:
    """Volume distribution: curly vs kinky. PROVISIONAL."""
    vol_records = [r for r in records if r.get("hair_type") in ("curly", "kinky")]
    if not vol_records:
        return {"error": "No curly/kinky records", "n": 0}

    by_type = defaultdict(list)
    for r in vol_records:
        cond = r.get("conditional_attribute", {})
        val = cond.get("value")
        if val:
            by_type[r["hair_type"]].append(val)

    types_with_data = [t for t in ("curly", "kinky") if len(by_type.get(t, [])) > 0]
    vol_classes = ["low", "medium", "high"]

    table = []
    for t in types_with_data:
        counts = Counter(by_type[t])
        table.append([counts.get(c, 0) for c in vol_classes])

    result = {
        "provisional": True,
        "n_total": len(vol_records),
        "by_type": {t: dict(Counter(by_type[t])) for t in types_with_data},
        "contingency_table": table,
        "volume_classes": vol_classes,
        "types": types_with_data,
    }

    if len(table) >= 2 and len(table[0]) >= 2:
        try:
            chi2, p, dof, expected = stats.chi2_contingency(np.array(table))
            result["chi_square"] = {
                "chi2": round(float(chi2), 4),
                "p_value": float(p),
                "dof": int(dof),
            }
        except Exception as exc:
            result["chi_square"] = {"error": str(exc)}

    return result


def analyze_viewpoint_distribution(records: list[dict]) -> dict:
    """Viewpoint distribution across hair types."""
    by_type = defaultdict(Counter)
    for r in records:
        vp = r.get("viewpoint", "unknown")
        by_type[r.get("hair_type", "unknown")][vp] += 1

    return {
        "by_type": {t: dict(c) for t, c in by_type.items()},
        "overall": dict(Counter(r.get("viewpoint", "unknown") for r in records)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Hierarchical signal analysis (cross-level).")
    ap.add_argument("--annotator", default="A", help="Annotator (default: A)")
    ap.add_argument("--out", default=str(REPORT_DIR / "hierarchical_signal.json"), help="Output path")
    args = ap.parse_args()

    print("=== Hierarchical Signal Analysis ===")
    print(f"Annotator: {args.annotator}")
    print()

    try:
        records = load_human_gt(args.annotator)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        print("Run annotation tool first: python -m annotation.annotation_tool.runner --annotator A")
        return
    print(f"Total gradable records: {len(records)}")

    print("\n--- LENGTH by HAIR TYPE (straight vs wavy) ---")
    length_result = analyze_length_by_type(records)
    if "error" not in length_result:
        print(f"  n_total: {length_result['n_total']}")
        for t, dist in length_result["by_type"].items():
            print(f"  {t}: {dist}")
        if "chi_square" in length_result:
            cs = length_result["chi_square"]
            print(f"  Chi-square: chi2={cs['chi2']}, p={cs['p_value']:.6f}, dof={cs['dof']}")
    else:
        print(f"  {length_result['error']}")

    print("\n--- VOLUME by HAIR TYPE (curly vs kinky) [PROVISIONAL] ---")
    volume_result = analyze_volume_by_type(records)
    if "error" not in volume_result:
        print(f"  n_total: {volume_result['n_total']}")
        for t, dist in volume_result["by_type"].items():
            print(f"  {t}: {dist}")
        if "chi_square" in volume_result:
            cs = volume_result["chi_square"]
            print(f"  Chi-square: chi2={cs['chi2']}, p={cs['p_value']:.6f}, dof={cs['dof']}")
    else:
        print(f"  {volume_result['error']}")

    print("\n--- VIEWPOINT distribution ---")
    vp_result = analyze_viewpoint_distribution(records)
    for t, dist in vp_result["by_type"].items():
        print(f"  {t}: {dist}")

    report = {
        "analysis": "hierarchical_signal",
        "annotator": args.annotator,
        "n_gradable": len(records),
        "length_by_type": length_result,
        "volume_by_type": volume_result,
        "viewpoint_distribution": vp_result,
        "note": "Cross-level analysis. Not model evaluation. Uses only human annotation.",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport -> {out_path}")


if __name__ == "__main__":
    main()
