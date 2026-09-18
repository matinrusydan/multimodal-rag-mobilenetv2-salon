# -*- coding: utf-8 -*-
"""Bandingkan agreement pilot v1 vs v2 pada 80 frame yang SAMA (subset).

Tujuan: menguji apakah revisi guideline v2 menurunkan disagreement pada kasus
yang sama (apple-to-apple). Hanya frame yang ada di KEDUA manifest yang dipakai.

Input:
  - v1: annotator_A.json / annotator_B.json (pilot 80)
  - v2: annotator_A_p240.json / annotator_B_p240.json (pilot 240)

Output:
  reports/agreement_v1_vs_v2.json

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" annotation\\compare_agreement_v1_v2.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
GT_DIR = BASE / "annotation" / "ground_truth"
REPORT_DIR = BASE / "annotation" / "reports"

LENGTH_ORDER = {"short": 0, "shoulder": 1, "mid_back": 2, "long": 3}
LENGTH_CLASSES = ["short", "shoulder", "mid_back", "long"]
VOLUME_ORDER = {"low": 0, "medium": 1, "high": 2}
VOLUME_CLASSES = ["low", "medium", "high"]


def load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Tidak ditemukan: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["image_id"]: r for r in data}


def value_of(rec: dict) -> str | None:
    if rec.get("ungradable"):
        return "ungradable"
    x = (rec.get("conditional_attribute") or {}).get("value")
    return x


def cohen_kappa(cm: list[list[int]]) -> float:
    n = len(cm)
    total = sum(sum(row) for row in cm)
    if total == 0:
        return float("nan")
    po = sum(cm[i][i] for i in range(n)) / total
    row_sums = [sum(cm[i]) for i in range(n)]
    col_sums = [sum(cm[i][j] for i in range(n)) for j in range(n)]
    pe = sum(row_sums[i] * col_sums[i] for i in range(n)) / (total ** 2)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


def weighted_kappa(cm: list[list[int]], power: int) -> float:
    n = len(cm)
    total = sum(sum(row) for row in cm)
    if total == 0 or n < 2:
        return float("nan")
    row_sums = [sum(cm[i]) for i in range(n)]
    col_sums = [sum(cm[i][j] for i in range(n)) for j in range(n)]
    denom = (n - 1) ** power
    w = [[((abs(i - j)) ** power) / denom for j in range(n)] for i in range(n)]
    num_obs = sum(w[i][j] * cm[i][j] for i in range(n) for j in range(n))
    num_exp = sum(w[i][j] * row_sums[i] * col_sums[j] for i in range(n) for j in range(n)) / total
    if num_exp == 0:
        return 1.0
    return 1.0 - (num_obs / num_exp)


def confusion(labels_a: list[str], labels_b: list[str], classes: list[str]) -> list[list[int]]:
    idx = {c: i for i, c in enumerate(classes)}
    cm = [[0] * len(classes) for _ in classes]
    for a, b in zip(labels_a, labels_b, strict=False):
        if a in idx and b in idx:
            cm[idx[a]][idx[b]] += 1
    return cm


def analyze_subset(recA: dict, recB: dict, frame_ids: set[str], task: str) -> dict:
    """task: 'length' atau 'volume'."""
    order = LENGTH_ORDER if task == "length" else VOLUME_ORDER
    classes = LENGTH_CLASSES if task == "length" else VOLUME_CLASSES

    ord_ids = [
        iid for iid in frame_ids
        if value_of(recA[iid]) in order and value_of(recB[iid]) in order
    ]
    n_ord = len(ord_ids)
    labels_a = [value_of(recA[iid]) for iid in ord_ids]
    labels_b = [value_of(recB[iid]) for iid in ord_ids]

    cm = confusion(labels_a, labels_b, classes)
    k = cohen_kappa(cm)
    k_lin = weighted_kappa(cm, 1)
    k_quad = weighted_kappa(cm, 2)

    n_common = len([iid for iid in frame_ids if iid in recA and iid in recB])
    n_disagree = sum(
        1 for iid in frame_ids
        if iid in recA and iid in recB and value_of(recA[iid]) != value_of(recB[iid])
    )
    raw_all = 1 - n_disagree / n_common if n_common else float("nan")

    return {
        "task": task,
        "n_common_frames": n_common,
        "n_ordinal": n_ord,
        "raw_agreement_all": round(raw_all, 4) if n_common else None,
        "cohens_kappa": None if k != k else round(k, 4),
        "linear_weighted_kappa": None if k_lin != k_lin else round(k_lin, 4),
        "quadratic_weighted_kappa": None if k_quad != k_quad else round(k_quad, 4),
        "n_disagreements": n_disagree,
        "confusion_matrix": cm,
        "classes": classes,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Bandingkan agreement v1 vs v2 pada frame yang sama.")
    ap.add_argument("--v1-a", default="A", help="ID annotator A pilot v1 (default: A)")
    ap.add_argument("--v1-b", default="B", help="ID annotator B pilot v1 (default: B)")
    ap.add_argument("--v2-a", default="A_p240", help="ID annotator A pilot v2 (default: A_p240)")
    ap.add_argument("--v2-b", default="B_p240", help="ID annotator B pilot v2 (default: B_p240)")
    ap.add_argument("--out", default=str(REPORT_DIR / "agreement_v1_vs_v2.json"))
    args = ap.parse_args()

    print("=== Bandingkan agreement v1 vs v2 (frame identik) ===")
    try:
        A1 = load(GT_DIR / f"annotator_{args.v1_a}.json")
        B1 = load(GT_DIR / f"annotator_{args.v1_b}.json")
        A2 = load(GT_DIR / f"annotator_{args.v2_a}.json")
        B2 = load(GT_DIR / f"annotator_{args.v2_b}.json")
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        print("\nPilot v2 belum dianotasi. Jalankan dulu:")
        print("  & \".venv\\Scripts\\python.exe\" -m annotation.annotation_tool.runner --annotator A --manifest annotation\\ground_truth\\pilot_manifest_240.json")
        print("  & \".venv\\Scripts\\python.exe\" -m annotation.annotation_tool.runner --annotator B --manifest annotation\\ground_truth\\pilot_manifest_240.json")
        return

    # Frame yang ada di v1 DAN v2 (uji apple-to-apple)
    common = set(A1) & set(B1) & set(A2) & set(B2)
    print(f"Frame di v1 DAN v2 (dibandingkan): {len(common)}")

    # Bagi per task berdasarkan direktori dataset (lurus/bergelombang=length, keriting/sangat=volume)
    length_ids = {iid for iid in common if "/lurus/" in iid or "/bergelombang/" in iid}
    volume_ids = {iid for iid in common if "/keriting/" in iid or "/sangat-keriting/" in iid}

    result = {
        "n_common_frames": len(common),
        "n_length_frames": len(length_ids),
        "n_volume_frames": len(volume_ids),
        "length": {
            "v1": analyze_subset(A1, B1, length_ids, "length"),
            "v2": analyze_subset(A2, B2, length_ids, "length"),
        },
        "volume": {
            "v1": analyze_subset(A1, B1, volume_ids, "volume"),
            "v2": analyze_subset(A2, B2, volume_ids, "volume"),
        },
        "note": "Hanya frame yang ada di kedua pilot. v2 diharapkan menurunkan disagreement bila revisi guideline efektif.",
    }

    for task in ("length", "volume"):
        v1 = result[task]["v1"]
        v2 = result[task]["v2"]
        print(f"\n=== {task.upper()} (n frame={result['n_'+task+'_frames']}) ===")
        print(f"  {'metrik':28s} {'v1':>10s} {'v2':>10s} {'delta':>10s}")
        for key in ("raw_agreement_all", "cohens_kappa", "linear_weighted_kappa",
                    "quadratic_weighted_kappa", "n_disagreements"):
            a, b = v1.get(key), v2.get(key)
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                print(f"  {key:28s} {a:>10.4f} {b:>10.4f} {b - a:>+10.4f}")
            else:
                print(f"  {key:28s} {str(a):>10s} {str(b):>10s}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport -> {out_path}")


if __name__ == "__main__":
    main()
