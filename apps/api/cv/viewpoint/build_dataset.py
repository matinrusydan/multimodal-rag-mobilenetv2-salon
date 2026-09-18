# -*- coding: utf-8 -*-
"""viewpoint/build_dataset.py — Bangun dataset viewpoint 3-kelas dari label MANUSIA.

Gabung:
  1. viewpoint/ground_truth/viewpoint_verification_*.json  (verifikasi, kualitas terbaik)
  2. annotation/ground_truth/_archive_annotator_A_p240_v2.json  (pilot manual)

Normalisasi 3 kelas; buang label ragu/null. Verifikasi menang saat duplikat.

Output: viewpoint/dataset/index.json — (image_id, relpath, label, source)

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\build_dataset.py
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import CV_DIR, VIEWPOINT_CLASSES
from common.io_utils import load_json, save_json, relpath_of

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground_truth"
OUT_DIR = HERE / "dataset"
ANN_GT = CV_DIR / "annotation" / "ground_truth"


def norm_label(vp: str | None) -> str | None:
    if not vp:
        return None
    vp = vp.lower()
    if vp in ("back", "back_left", "back_right", "belakang", "belakang_nyerong"):
        return "belakang"
    if vp in ("front", "depan"):
        return "depan"
    if vp in ("side", "samping"):
        return "samping"
    return None


def load_verification() -> dict[str, dict]:
    out = {}
    for f in GT_DIR.glob("viewpoint_verification_*.json"):
        for r in load_json(f).get("records", []):
            if r["is_correct"] == "ya":
                lab = norm_label(r["model_prediction"])
            elif r["is_correct"] == "tidak":
                lab = norm_label(r.get("correction"))
            else:
                lab = None
            if lab:
                out[r["image_id"]] = {"label": lab, "source": "verification_human"}
    return out


def load_pilot() -> dict[str, dict]:
    out = {}
    p = ANN_GT / "_archive_annotator_A_p240_v2.json"
    if not p.exists():
        return out
    data = load_json(p)
    recs = data if isinstance(data, list) else data.get("records", [])
    for r in recs:
        lab = norm_label(r.get("viewpoint"))
        if lab:
            out[r["image_id"]] = {"label": lab, "source": "pilot_manual"}
    return out


def main():
    ap = argparse.ArgumentParser(description="Bangun dataset viewpoint dari label manusia.")
    ap.add_argument("--out", default=str(OUT_DIR / "index.json"))
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ver, pil = load_verification(), load_pilot()
    merged = dict(pil)
    merged.update(ver)  # verifikasi menang

    records, missing = [], 0
    for iid, rec in merged.items():
        rel = relpath_of(iid)
        if not (CV_DIR / rel).exists():
            missing += 1
            continue
        records.append({"image_id": iid, "relpath": rel, "label": rec["label"], "source": rec["source"]})

    dist = Counter(r["label"] for r in records)
    save_json(args.out, {
        "schema_version": "viewpoint_dataset_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "classes": VIEWPOINT_CLASSES, "n_total": len(records),
        "distribution": {c: dist.get(c, 0) for c in VIEWPOINT_CLASSES},
        "source_distribution": dict(Counter(r["source"] for r in records)),
        "records": records,
    })
    print("=== Dataset Viewpoint ===")
    print(f"  total: {len(records)} (missing: {missing})")
    print(f"  distribusi: {dict((c, dist.get(c, 0)) for c in VIEWPOINT_CLASSES)}")
    print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
