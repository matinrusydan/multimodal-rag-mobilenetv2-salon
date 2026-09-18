# -*- coding: utf-8 -*-
"""viewpoint/measure.py — Ukur akurasi gate vs verifikasi manusia (as-is).

Koreksi manusia opsional: "tidak" tetap dihitung salah walau tanpa koreksi.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\measure.py --annotators A
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import VIEWPOINT_CLASSES
from common.io_utils import load_json, save_json

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground_truth"
REPORTS = HERE / "reports"


def main():
    ap = argparse.ArgumentParser(description="Mode pengukuran: akurasi gate viewpoint.")
    ap.add_argument("--annotators", nargs="*", default=["A"])
    ap.add_argument("--out", default=str(REPORTS / "viewpoint_accuracy.json"))
    args = ap.parse_args()

    all_recs, per_ann = {}, {}
    for a in args.annotators:
        p = GT_DIR / f"viewpoint_verification_{a}.json"
        if p.exists():
            recs = {r["image_id"]: r for r in load_json(p).get("records", [])}
            per_ann[a] = len(recs); all_recs.update(recs)

    if not all_recs:
        print("ERROR: belum ada verifikasi. Jalankan viewpoint/verify.py dulu.")
        return

    n = len(all_recs)
    correct = sum(1 for r in all_recs.values() if r["is_correct"] == "ya")
    wrong = sum(1 for r in all_recs.values() if r["is_correct"] == "tidak")
    ragu = sum(1 for r in all_recs.values() if r["is_correct"] == "ragu")
    acc = correct / n if n else 0.0
    acc_excl = correct / (correct + wrong) if (correct + wrong) else 0.0

    conf = defaultdict(Counter)
    for r in all_recs.values():
        if r["is_correct"] == "tidak" and r.get("correction"):
            conf[r["model_prediction"]][r["correction"]] += 1

    per_class = {}
    for c in VIEWPOINT_CLASSES:
        rows = [r for r in all_recs.values() if r["model_prediction"] == c]
        if rows:
            cc = sum(1 for r in rows if r["is_correct"] == "ya")
            per_class[c] = {"n": len(rows), "correct": cc, "accuracy": round(cc / len(rows), 4)}

    report = {
        "analysis": "viewpoint_accuracy_asmode", "mode": "pengukuran (as-is)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "annotators": args.annotators, "n_verified": n, "n_per_annotator": per_ann,
        "metrics": {"accuracy": round(acc, 4), "accuracy_excluding_ragu": round(acc_excl, 4),
                    "n_correct": correct, "n_wrong": wrong, "n_ragu": ragu,
                    "ragu_rate": round(ragu / n, 4) if n else 0.0},
        "accuracy_per_predicted_class": per_class,
        "confusion_model_to_human": {k: dict(v) for k, v in conf.items()},
    }
    save_json(args.out, report)

    print("=== Akurasi Viewpoint Gate (as-is) ===")
    print(f"  n={n} | accuracy={acc:.2%} ({correct}/{wrong}/{ragu})")
    print(f"  accuracy (excl. ragu): {acc_excl:.2%}")
    print("  per kelas:")
    for c, v in per_class.items():
        print(f"    {c:10s} {v['accuracy']:.2%} (n={v['n']})")
    if conf:
        print("  confusion (model salah -> koreksi):")
        for k, v in conf.items():
            print(f"    {k} -> {dict(v)}")
    print(f"\nReport -> {args.out}")


if __name__ == "__main__":
    main()
