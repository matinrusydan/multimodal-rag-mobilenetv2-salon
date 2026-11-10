"""Extract exploratory mask features on the training split only.

This is not a pose geometry pipeline or a calibrated tied-hair classifier.
No validation/test images are used to choose postprocessing parameters.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from segment_infer import HairSegmenter, save_mask_and_overlay
from threshold_binary import cleanup_mask
from detect_tied_hair import assess_tied_hair

HERE = Path(__file__).resolve().parent


def run(manifest: Path, model: Path, out: Path, limit: int | None = None) -> dict:
    out = out.resolve()
    if not out.is_relative_to(HERE):
        raise ValueError("Output must remain inside apps/api/cv/geometry/")
    if out.exists():
        raise FileExistsError(f"Output already exists; choose a new directory: {out}")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    records = sorted((r for r in payload["records"] if r["split"] == "train"),
                     key=lambda r: r["image_id"])
    if limit is not None:
        records = records[:limit]
    if not records:
        raise ValueError("No training records found")
    dataset = HERE.parent / "dataset"
    # Validate the whole input list before creating outputs.
    for rec in records:
        path = (dataset / rec["image_id"]).resolve()
        if not path.is_relative_to(dataset.resolve()) or not path.is_file():
            raise ValueError(f"Invalid source image: {rec['image_id']}")
    segmenter = HairSegmenter(model)
    out.mkdir(parents=True)
    rows = []
    for index, rec in enumerate(records):
        source = dataset / rec["image_id"]
        prediction = segmenter.predict_file(source)
        mask = cleanup_mask(prediction["mask"])
        assessment = assess_tied_hair(mask)
        row = {
            "image_id": rec["image_id"], "split": "train",
            "hair_class": rec["approved_label"],
            "orig_size": prediction["orig_size"],
            "hair_coverage": prediction["hair_coverage"],
            "mask_shape_assessment": assessment,
            "length": {"status": "blocked_phase0_gate", "value": None},
            "volume": {"status": "reference_not_validated", "value": None},
        }
        rows.append(row)
        if index < 8:
            name = hashlib.sha256(rec["image_id"].encode()).hexdigest()[:12]
            save_mask_and_overlay(source, mask, mask_out=out / f"{name}_mask.png",
                                  overlay_out=out / f"{name}_overlay.jpg")
        print(f"[{index + 1}/{len(records)}] {rec['image_id']}", flush=True)
    report = {
        "phase": "3_partial_mask_features_only",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "seed": 42, "sampling": "sorted training records; no randomness",
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "onnx_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
        "split": "train", "n": len(rows), "limited": limit is not None,
        "postprocessing": "identity defaults; no morphology, filling, or component removal",
        "gate": {"status": "NOT_ASSESSED", "reason":
                 "Pose gate not passed; length/volume references and tied-hair thresholds not validated."},
        "limitations": [
            "Shape features describe predicted silhouettes, not anatomical measurements.",
            "Training split extraction is not independent evaluation.",
            "No tied-hair decisions or rejection flags are calibrated.",
            "No absolute cm, head-unit, or final length/volume classes are inferred.",
        ],
        "records": rows,
    }
    (out / "mask_features.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / "reports/phase1/curated_manifest.json")
    parser.add_argument("--model", type=Path, default=HERE / "weights/hair_segmentation.onnx")
    parser.add_argument("--out", type=Path, default=HERE / "reports/phase3_mask_features")
    parser.add_argument("--limit", type=int, help="First N sorted training images for a smoke run")
    args = parser.parse_args()
    report = run(args.manifest, args.model, args.out, args.limit)
    print(f"Extracted {report['n']} training masks; Phase 3 gate NOT_ASSESSED")


if __name__ == "__main__":
    main()
