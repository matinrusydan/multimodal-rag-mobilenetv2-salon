# -*- coding: utf-8 -*-
"""Analyze inter-annotator agreement (Cohen's kappa, weighted kappa) — manual implementation.

Computes:
  1. Raw agreement
  2. Cohen's kappa (unweighted)
  3. Linear weighted kappa
  4. Quadratic weighted kappa
  5. Confusion matrix (5x5 including ungradable)
  6. Per-class agreement
  7. Ungradable rate per annotator
  8. Confidence distribution
  9. Disagreement pairs + boundary frequencies
  10. Decision helper: GREEN / YELLOW / RED (guideline, NOT scientific law)

Ungradable is EXCLUDED from ordinal kappa calculations (reported separately).

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" annotation\\analyze_annotation_agreement.py
  & ".venv\\Scripts\\python.exe" annotation\\analyze_annotation_agreement.py --annotator-a A --annotator-b B
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]  # apps/api/cv
GT_DIR = BASE / "annotation" / "ground_truth"
REPORT_DIR = BASE / "annotation" / "reports"

# Ordinal classes for length (straight/wavy)
LENGTH_ORDER = {"short": 0, "shoulder": 1, "mid_back": 2, "long": 3}
LENGTH_CLASSES = ["short", "shoulder", "mid_back", "long"]

# Volume classes (curly/kinky) — PROVISIONAL, also ordinal but flagged
VOLUME_ORDER = {"low": 0, "medium": 1, "high": 2}
VOLUME_CLASSES = ["low", "medium", "high"]


def load_annotations(path: Path) -> dict:
    """Load annotation JSON (list of records) → dict keyed by image_id."""
    if not path.exists():
        raise FileNotFoundError(f"Annotation file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}, got {type(data)}")
    result = {}
    for rec in data:
        iid = rec.get("image_id")
        if not iid:
            raise ValueError(f"Record missing image_id: {rec}")
        if iid in result:
            raise ValueError(f"Duplicate image_id in {path}: {iid}")
        result[iid] = rec
    return result


def extract_label(rec: dict) -> str | None:
    """Extract the conditional attribute value, or 'ungradable' if ungradable."""
    if rec.get("ungradable", False):
        return "ungradable"
    cond = rec.get("conditional_attribute", {})
    return cond.get("value")


def confusion_matrix(labels_a: list[str], labels_b: list[str], classes: list[str]) -> list[list[int]]:
    """Build NxN confusion matrix (A=rows, B=cols)."""
    idx = {c: i for i, c in enumerate(classes)}
    n = len(classes)
    cm = [[0] * n for _ in range(n)]
    for a, b in zip(labels_a, labels_b, strict=False):
        if a in idx and b in idx:
            cm[idx[a]][idx[b]] += 1
    return cm


def cohen_kappa(cm: list[list[int]]) -> float:
    """Cohen's kappa from NxN confusion matrix (manual)."""
    n = len(cm)
    total = sum(sum(row) for row in cm)
    if total == 0:
        return float("nan")

    # Observed agreement
    po = sum(cm[i][i] for i in range(n)) / total

    # Expected agreement
    row_sums = [sum(cm[i]) for i in range(n)]
    col_sums = [sum(cm[i][j] for i in range(n)) for j in range(n)]
    pe = sum(row_sums[i] * col_sums[i] for i in range(n)) / (total ** 2)

    if pe == 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


def weighted_kappa(cm: list[list[int]], weights: list[list[float]]) -> float:
    """Weighted kappa with custom weight matrix (manual).

    weights[i][j] = penalty for A=i, B=j (0=agree, higher=worse).
    """
    n = len(cm)
    total = sum(sum(row) for row in cm)
    if total == 0:
        return float("nan")

    row_sums = [sum(cm[i]) for i in range(n)]
    col_sums = [sum(cm[i][j] for i in range(n)) for j in range(n)]

    # Observed weighted disagreement
    num_obs = sum(weights[i][j] * cm[i][j] for i in range(n) for j in range(n))
    # Expected weighted disagreement
    num_exp = sum(
        weights[i][j] * row_sums[i] * col_sums[j]
        for i in range(n)
        for j in range(n)
    ) / total

    if num_exp == 0:
        return 1.0
    return 1.0 - (num_obs / num_exp)


def linear_weights(n: int) -> list[list[float]]:
    """Linear weight: w[i][j] = |i - j| / (n - 1)."""
    return [[abs(i - j) / (n - 1) for j in range(n)] for i in range(n)]


def quadratic_weights(n: int) -> list[list[float]]:
    """Quadratic weight: w[i][j] = (i - j)^2 / (n - 1)^2."""
    return [[((i - j) ** 2) / ((n - 1) ** 2) for j in range(n)] for i in range(n)]


def per_class_agreement(cm: list[list[int]], classes: list[str]) -> dict:
    """Per-class recall (from A's perspective)."""
    n = len(classes)
    result = {}
    for i, cls in enumerate(classes):
        row_total = sum(cm[i])
        if row_total > 0:
            result[cls] = {
                "recall": round(cm[i][i] / row_total, 4),
                "n_annotator_a": row_total,
            }
        else:
            result[cls] = {"recall": None, "n_annotator_a": 0}
    return result


def disagreement_pairs(records_a: dict, records_b: dict) -> list[dict]:
    """Find all disagreement pairs and count boundary frequencies."""
    pairs = []
    for iid, ra in records_a.items():
        rb = records_b.get(iid)
        if not rb:
            continue
        la = extract_label(ra)
        lb = extract_label(rb)
        if la != lb:
            pairs.append(
                {
                    "image_id": iid,
                    "annotator_a": la,
                    "annotator_b": lb,
                }
            )
    # Count boundary confusion
    boundary_counts = Counter()
    for p in pairs:
        key = tuple(sorted([str(p["annotator_a"]), str(p["annotator_b"])]))
        boundary_counts[key] += 1
    return pairs, dict(boundary_counts)


def decision_helper(kappa: float, raw_agree: float, ungradable_rate: float, n_disagree: int, n_total: int) -> str:
    """GREEN/YELLOW/RED decision — GUIDELINE, not scientific law."""
    if n_total == 0:
        return "RED"

    disagree_rate = n_disagree / n_total

    # GREEN: high agreement, low ungradable, few disagreements
    if kappa >= 0.80 and raw_agree >= 0.85 and ungradable_rate <= 0.15:
        return "GREEN"

    # RED: very low agreement
    if kappa < 0.40 or raw_agree < 0.50:
        return "RED"

    # YELLOW: everything in between
    return "YELLOW"


def analyze_length_subset(records_a: dict, records_b: dict) -> dict:
    """Analyze agreement for length (straight/wavy images only)."""
    # Filter to straight/wavy
    length_ids = [
        iid
        for iid, r in records_a.items()
        if r.get("hair_type") in ("straight", "wavy") and iid in records_b
    ]

    if not length_ids:
        return {"error": "No straight/wavy images with both annotations", "n": 0}

    labels_a = [extract_label(records_a[iid]) for iid in length_ids]
    labels_b = [extract_label(records_b[iid]) for iid in length_ids]

    # Ordinal kappa: exclude ungradable
    ord_ids = [
        iid for iid in length_ids
        if extract_label(records_a[iid]) in LENGTH_ORDER
        and extract_label(records_b[iid]) in LENGTH_ORDER
    ]
    ord_a = [LENGTH_ORDER[extract_label(records_a[iid])] for iid in ord_ids]
    ord_b = [LENGTH_ORDER[extract_label(records_b[iid])] for iid in ord_ids]

    # Confusion matrix (ordinal only)
    cm_classes = LENGTH_CLASSES
    cm = confusion_matrix(
        [extract_label(records_a[iid]) for iid in ord_ids],
        [extract_label(records_b[iid]) for iid in ord_ids],
        cm_classes,
    )

    # Kappas
    k_unweighted = cohen_kappa(cm)
    k_linear = weighted_kappa(cm, linear_weights(len(cm_classes)))
    k_quadratic = weighted_kappa(cm, quadratic_weights(len(cm_classes)))

    # Raw agreement (ordinal only)
    n_ord = len(ord_ids)
    n_agree_ord = sum(1 for a, b in zip(ord_a, ord_b, strict=False) if a == b)
    raw_agree_ord = n_agree_ord / n_ord if n_ord > 0 else float("nan")

    # Ungradable rate (in length subset)
    n_ungradable_a = sum(1 for l in labels_a if l == "ungradable")
    n_ungradable_b = sum(1 for l in labels_b if l == "ungradable")

    # Confidence distribution
    conf_a = Counter(records_a[iid].get("confidence", "unknown") for iid in length_ids)
    conf_b = Counter(records_b[iid].get("confidence", "unknown") for iid in length_ids)

    # Per-class
    pca = per_class_agreement(cm, cm_classes)

    # Disagreement pairs (all, including ungradable)
    all_pairs, boundary_counts = disagreement_pairs(
        {iid: records_a[iid] for iid in length_ids},
        {iid: records_b[iid] for iid in length_ids},
    )

    # Decision
    ungradable_rate = (n_ungradable_a + n_ungradable_b) / (2 * len(length_ids)) if length_ids else 0
    decision = decision_helper(
        k_quadratic,
        raw_agree_ord,
        ungradable_rate,
        len(all_pairs),
        len(length_ids),
    )

    return {
        "attribute": "length",
        "n_images": len(length_ids),
        "n_ordinal": n_ord,
        "raw_agreement_ordinal": round(raw_agree_ord, 4) if n_ord > 0 else None,
        "cohens_kappa": round(k_unweighted, 4) if not (k_unweighted != k_unweighted) else None,
        "linear_weighted_kappa": round(k_linear, 4) if not (k_linear != k_linear) else None,
        "quadratic_weighted_kappa": round(k_quadratic, 4) if not (k_quadratic != k_quadratic) else None,
        "confusion_matrix": cm,
        "classes": cm_classes,
        "per_class": pca,
        "ungradable_rate_a": round(n_ungradable_a / len(length_ids), 4) if length_ids else None,
        "ungradable_rate_b": round(n_ungradable_b / len(length_ids), 4) if length_ids else None,
        "confidence_distribution": {"A": dict(conf_a), "B": dict(conf_b)},
        "n_disagreements": len(all_pairs),
        "disagreement_boundary_counts": {f"{k[0]}|{k[1]}": v for k, v in boundary_counts.items()},
        "decision": decision,
    }


def analyze_volume_subset(records_a: dict, records_b: dict) -> dict:
    """Analyze agreement for visual_volume (curly/kinky images only). PROVISIONAL."""
    vol_ids = [
        iid
        for iid, r in records_a.items()
        if r.get("hair_type") in ("curly", "kinky") and iid in records_b
    ]

    if not vol_ids:
        return {"error": "No curly/kinky images with both annotations", "n": 0}

    labels_a = [extract_label(records_a[iid]) for iid in vol_ids]
    labels_b = [extract_label(records_b[iid]) for iid in vol_ids]

    # Ordinal kappa
    ord_ids = [
        iid for iid in vol_ids
        if extract_label(records_a[iid]) in VOLUME_ORDER
        and extract_label(records_b[iid]) in VOLUME_ORDER
    ]
    cm_classes = VOLUME_CLASSES
    cm = confusion_matrix(
        [extract_label(records_a[iid]) for iid in ord_ids],
        [extract_label(records_b[iid]) for iid in ord_ids],
        cm_classes,
    )

    k_unweighted = cohen_kappa(cm)
    k_linear = weighted_kappa(cm, linear_weights(len(cm_classes)))
    k_quadratic = weighted_kappa(cm, quadratic_weights(len(cm_classes)))

    n_ord = len(ord_ids)
    raw_agree = (
        sum(1 for iid in ord_ids if extract_label(records_a[iid]) == extract_label(records_b[iid])) / n_ord
        if n_ord > 0
        else float("nan")
    )

    ungradable_a = sum(1 for l in labels_a if l == "ungradable")
    ungradable_b = sum(1 for l in labels_b if l == "ungradable")

    all_pairs, boundary_counts = disagreement_pairs(
        {iid: records_a[iid] for iid in vol_ids},
        {iid: records_b[iid] for iid in vol_ids},
    )

    ungradable_rate = (ungradable_a + ungradable_b) / (2 * len(vol_ids)) if vol_ids else 0
    decision = decision_helper(
        k_quadratic,
        raw_agree,
        ungradable_rate,
        len(all_pairs),
        len(vol_ids),
    )

    return {
        "attribute": "visual_volume",
        "provisional": True,
        "n_images": len(vol_ids),
        "n_ordinal": n_ord,
        "raw_agreement_ordinal": round(raw_agree, 4) if n_ord > 0 else None,
        "cohens_kappa": round(k_unweighted, 4) if not (k_unweighted != k_unweighted) else None,
        "linear_weighted_kappa": round(k_linear, 4) if not (k_linear != k_linear) else None,
        "quadratic_weighted_kappa": round(k_quadratic, 4) if not (k_quadratic != k_quadratic) else None,
        "confusion_matrix": cm,
        "classes": cm_classes,
        "ungradable_rate_a": round(ungradable_a / len(vol_ids), 4) if vol_ids else None,
        "ungradable_rate_b": round(ungradable_b / len(vol_ids), 4) if vol_ids else None,
        "n_disagreements": len(all_pairs),
        "disagreement_boundary_counts": {f"{k[0]}|{k[1]}": v for k, v in boundary_counts.items()},
        "decision": decision,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze inter-annotator agreement (manual kappa).")
    ap.add_argument("--annotator-a", default="A", help="Annotator A id (default: A)")
    ap.add_argument("--annotator-b", default="B", help="Annotator B id (default: B)")
    ap.add_argument("--out", default=str(REPORT_DIR / "annotation_agreement.json"), help="Output path")
    args = ap.parse_args()

    path_a = GT_DIR / f"annotator_{args.annotator_a}.json"
    path_b = GT_DIR / f"annotator_{args.annotator_b}.json"

    print(f"Loading annotations:")
    print(f"  A: {path_a}")
    print(f"  B: {path_b}")

    try:
        records_a = load_annotations(path_a)
        records_b = load_annotations(path_b)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        print("Make sure both annotators have completed annotation.")
        return

    # Common image_ids
    common = set(records_a.keys()) & set(records_b.keys())
    print(f"  Common image_ids: {len(common)}")

    if not common:
        print("ERROR: No common image_ids between annotators!")
        return

    # Overall
    overall_agree = sum(
        1 for iid in common
        if extract_label(records_a[iid]) == extract_label(records_b[iid])
    ) / len(common)

    print(f"\nOverall raw agreement (all labels incl. ungradable): {overall_agree:.4f}")

    # Length subset
    print("\n=== LENGTH (straight/wavy) ===")
    length_result = analyze_length_subset(records_a, records_b)
    if "error" not in length_result:
        print(f"  n_images: {length_result['n_images']}")
        print(f"  raw_agreement_ordinal: {length_result['raw_agreement_ordinal']}")
        print(f"  Cohen's kappa: {length_result['cohens_kappa']}")
        print(f"  Linear weighted kappa: {length_result['linear_weighted_kappa']}")
        print(f"  Quadratic weighted kappa: {length_result['quadratic_weighted_kappa']}")
        print(f"  Decision: {length_result['decision']}")
    else:
        print(f"  {length_result['error']}")

    # Volume subset
    print("\n=== VISUAL VOLUME (curly/kinky) [PROVISIONAL] ===")
    volume_result = analyze_volume_subset(records_a, records_b)
    if "error" not in volume_result:
        print(f"  n_images: {volume_result['n_images']}")
        print(f"  raw_agreement_ordinal: {volume_result['raw_agreement_ordinal']}")
        print(f"  Cohen's kappa: {volume_result['cohens_kappa']}")
        print(f"  Quadratic weighted kappa: {volume_result['quadratic_weighted_kappa']}")
        print(f"  Decision: {volume_result['decision']}")
    else:
        print(f"  {volume_result['error']}")

    # Save report
    report = {
        "overall_raw_agreement": round(overall_agree, 4),
        "n_common_images": len(common),
        "length": length_result,
        "volume": volume_result,
        "note": "Decision (GREEN/YELLOW/RED) is a GUIDELINE, not scientific law. Interpret with disagreement patterns.",
        "kappa_interpretation": {
            "unweighted": "Treats all disagreements equally. Penalizes adjacent-class errors same as distant-class.",
            "linear_weighted": "Penalty proportional to ordinal distance |i - j|.",
            "quadratic_weighted": "Penalty proportional to squared ordinal distance (i - j)^2. More forgiving of adjacent-class errors. Preferred for ordinal data.",
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport -> {out_path}")


if __name__ == "__main__":
    main()
