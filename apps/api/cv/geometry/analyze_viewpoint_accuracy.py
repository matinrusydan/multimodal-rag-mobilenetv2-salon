# -*- coding: utf-8 -*-
"""TAHAP 1 — Mode Pengukuran: analisis akurasi viewpoint gate AS-IS.

Mengukur seberapa akurat model gate TANPA intervensi manusia:
  - % tebakan BENAR (jawaban "ya")
  - % tebakan SALAH (jawaban "tidak")
  - % ambigu (jawaban "ragu")
  - Confusion: ketika model salah, koreksinya apa (jika diberikan)
  - Akurasi per kelas prediksi

Koreksi manusia OPSIONAL: jika tidak diisi, tetap dihitung sebagai salah.
Ini mengukur kemampuan model apa adanya.

Input:
  geometry/ground_truth/viewpoint_verification_*.json (hasil verify_viewpoint.py)

Output:
  geometry/reports/viewpoint_accuracy.json

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" geometry\\analyze_viewpoint_accuracy.py
  & ".venv\\Scripts\\python.exe" geometry\\analyze_viewpoint_accuracy.py --annotators A B
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
GEO = Path(__file__).resolve().parents[0]
GT_DIR = GEO / "ground_truth"
REPORTS = GEO / "reports"

VIEWPOINT_CLASSES = ["depan", "samping", "belakang"]


def load_verification(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["image_id"]: r for r in data.get("records", [])}


def main():
    ap = argparse.ArgumentParser(description="Mode Pengukuran: akurasi viewpoint gate as-is.")
    ap.add_argument("--annotators", nargs="*", default=["A"], help="ID annotator")
    ap.add_argument("--out", default=str(REPORTS / "viewpoint_accuracy.json"))
    args = ap.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)

    all_records = {}
    per_annotator = {}
    for a in args.annotators:
        recs = load_verification(GT_DIR / f"viewpoint_verification_{a}.json")
        per_annotator[a] = len(recs)
        all_records.update(recs)  # gabung (bila >1 annotator, id unik)

    if not all_records:
        print("ERROR: belum ada hasil verifikasi. Jalankan verify_viewpoint.py dulu.")
        return

    n = len(all_records)
    correct = sum(1 for r in all_records.values() if r["is_correct"] == "ya")
    wrong = sum(1 for r in all_records.values() if r["is_correct"] == "tidak")
    ragu = sum(1 for r in all_records.values() if r["is_correct"] == "ragu")

    acc = correct / n if n else 0.0
    acc_excl_ragu = correct / (correct + wrong) if (correct + wrong) else 0.0

    # confusion: prediksi model -> koreksi manusia (hanya yg salah & ada koreksi)
    conf_mat = defaultdict(Counter)
    n_with_correction = 0
    for r in all_records.values():
        if r["is_correct"] == "tidak" and r.get("correction"):
            conf_mat[r["model_prediction"]][r["correction"]] += 1
            n_with_correction += 1

    # akurasi per kelas prediksi
    per_class = {}
    for c in VIEWPOINT_CLASSES:
        rows = [r for r in all_records.values() if r["model_prediction"] == c]
        if not rows:
            continue
        cc = sum(1 for r in rows if r["is_correct"] == "ya")
        per_class[c] = {
            "n": len(rows),
            "correct": cc,
            "accuracy": round(cc / len(rows), 4),
        }

    # distribusi jawaban
    dist = Counter(r["is_correct"] for r in all_records.values())

    report = {
        "analysis": "viewpoint_accuracy_asmode",
        "mode": "pengukuran (as-is, tanpa bantuan manusia)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "annotators": args.annotators,
        "n_verified": n,
        "n_per_annotator": per_annotator,
        "metrics": {
            "accuracy": round(acc, 4),
            "accuracy_excluding_ragu": round(acc_excl_ragu, 4),
            "n_correct": correct,
            "n_wrong": wrong,
            "n_ragu": ragu,
            "ragu_rate": round(ragu / n, 4) if n else 0.0,
        },
        "answer_distribution": dict(dist),
        "accuracy_per_predicted_class": per_class,
        "confusion_model_to_human_correction": {k: dict(v) for k, v in conf_mat.items()},
        "n_corrections_given": n_with_correction,
        "note": (
            "Ini mengukur kemampuan model gate SENDIRI (as-is). "
            "Koreksi manusia opsional; 'tidak' tetap dihitung salah walau tanpa koreksi. "
            "'accuracy_excluding_ragu' = akurasi hanya pada kasus yang jelas (benar vs salah)."
        ),
    }

    out = Path(args.out)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== MODE PENGUKURAN — Akurasi Viewpoint Gate (as-is) ===")
    print(f"  Total terverifikasi: {n}")
    print(f"  Akurasi: {acc:.2%}  ({correct} benar / {wrong} salah / {ragu} ragu)")
    print(f"  Akurasi (excl. ragu): {acc_excl_ragu:.2%}")
    print(f"  Ragu rate: {ragu/n:.2%}" if n else "")
    print("\n  Akurasi per kelas prediksi:")
    for c, v in per_class.items():
        print(f"    {c:18s} {v['accuracy']:.2%} (n={v['n']})")
    if conf_mat:
        print("\n  Confusion (model salah -> koreksi manusia):")
        for pred, corrs in conf_mat.items():
            print(f"    {pred} -> {dict(corrs)}")
    print(f"\nReport -> {out}")


if __name__ == "__main__":
    main()
