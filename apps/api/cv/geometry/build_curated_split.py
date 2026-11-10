"""Deterministic, leakage-free curated dataset manifest and train/val/test split.

This tool builds the final curated dataset manifest for Phase 1 by applying
the human duplicate review decisions to the dataset audit, verifying image
integrity, and generating a stratified train/val/test split.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET = HERE.parent / "dataset"
PHASE1_DIR = HERE / "reports" / "phase1"
AUDIT_JSON = PHASE1_DIR / "dataset_curation.json"
RESOLUTION_JSON = PHASE1_DIR / "duplicate_review_resolution.json"

CLASSES = ("lurus", "bergelombang", "keriting", "sangat-keriting")
GATE_MIN_IMAGES = 150


def load_curated_records(
    audit_path: Path = AUDIT_JSON,
    resolution_path: Path = RESOLUTION_JSON,
) -> tuple[list[dict], dict]:
    """Load audited records and apply review resolutions."""
    if not audit_path.exists():
        raise FileNotFoundError(f"Audit report missing: {audit_path}")
    if not resolution_path.exists():
        raise FileNotFoundError(f"Resolution decisions missing: {resolution_path}")

    audit_data = json.loads(audit_path.read_text(encoding="utf-8"))
    resolution_data = json.loads(resolution_path.read_text(encoding="utf-8"))

    raw_records = {r["image_id"]: r for r in audit_data.get("records", [])}

    # Extract exclusions and relabeling
    excluded_ids = set()
    relabel_map = {}

    # Resolved group (e.g. 3 duplicate files excluded)
    group = resolution_data.get("resolved_group", {})
    if group.get("action") == "exclude_all_from_curated_dataset":
        excluded_ids.update(group.get("image_ids", []))

    # Other pairwise decisions
    for item in resolution_data.get("other_decisions", []):
        if item.get("relation") == "sama":
            if "excluded_image_id" in item:
                excluded_ids.add(item["excluded_image_id"])
            if "selected_image_id" in item and "approved_label" in item:
                relabel_map[item["selected_image_id"]] = item["approved_label"]
        elif item.get("relation") == "berbeda":
            for sub in item.get("images", []):
                if sub.get("image_id") and sub.get("approved_label"):
                    relabel_map[sub["image_id"]] = sub["approved_label"]

    curated = []
    for image_id, rec in sorted(raw_records.items()):
        if image_id in excluded_ids:
            continue
        original_label = rec["hair_class"]
        approved_label = relabel_map.get(image_id, original_label)
        curated.append({
            "image_id": image_id,
            "cohort": rec["cohort"],
            "original_label": original_label,
            "approved_label": approved_label,
            "sha256": rec["sha256"],
            "pixel_sha256": rec.get("pixel_sha256"),
            "width": rec["width"],
            "height": rec["height"],
            "min_side_ge_224": rec.get("min_side_ge_224", False),
        })

    metadata = {
        "raw_total": len(raw_records),
        "excluded_count": len(excluded_ids),
        "excluded_image_ids": sorted(excluded_ids),
        "relabeled_count": len(relabel_map),
        "relabeled_map": relabel_map,
        "curated_total": len(curated),
    }
    return curated, metadata


def assign_splits(
    records: list[dict],
    seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> list[dict]:
    """Perform deterministic stratified train/val/test split."""
    if not (0 < train_ratio < 1 and 0 < val_ratio < 1 and train_ratio + val_ratio < 1):
        raise ValueError("train_ratio and val_ratio must sum to less than 1.0")

    rng = random.Random(seed)
    by_class: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_class[r["approved_label"]].append(r)

    assigned = []
    for label in sorted(by_class.keys()):
        class_rows = sorted(by_class[label], key=lambda x: x["image_id"])
        rng.shuffle(class_rows)

        n = len(class_rows)
        n_train = round(train_ratio * n)
        n_val = round(val_ratio * n)
        # Ensure at least 1 image per split if class has >= 3 images
        if n >= 3:
            n_train = max(1, n_train)
            n_val = max(1, n_val)
        n_test = n - n_train - n_val

        for i, row in enumerate(class_rows):
            if i < n_train:
                split = "train"
            elif i < n_train + n_val:
                split = "val"
            else:
                split = "test"
            assigned.append({**row, "split": split})

    assigned.sort(key=lambda x: x["image_id"])
    return assigned


def summarize_splits(records: list[dict]) -> dict:
    """Compute summary statistics per split and per class."""
    total = len(records)
    splits = ("train", "val", "test")
    split_counts = {s: 0 for s in splits}
    by_class = {c: {s: 0 for s in splits} for c in CLASSES}
    by_cohort = defaultdict(lambda: {s: 0 for s in splits})

    for r in records:
        s = r["split"]
        c = r["approved_label"]
        cohort = r["cohort"]
        split_counts[s] += 1
        if c in by_class:
            by_class[c][s] += 1
        by_cohort[cohort][s] += 1

    class_totals = {c: sum(by_class[c].values()) for c in CLASSES}

    return {
        "total": total,
        "split_counts": split_counts,
        "split_percentages": {s: round(split_counts[s] / total * 100, 1) if total else 0 for s in splits},
        "class_totals": class_totals,
        "by_class": by_class,
        "by_cohort": {k: dict(v) for k, v in sorted(by_cohort.items())},
    }


def run(
    dataset_dir: Path = DATASET,
    out_dir: Path = PHASE1_DIR,
    seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> dict:
    """Generate curated manifest, CSV, and formal Phase 1 decision."""
    out_dir = out_dir.resolve()
    if not out_dir.is_relative_to(HERE):
        raise ValueError("--out must resolve inside apps/api/cv/geometry/")

    curated, meta = load_curated_records()
    assigned = assign_splits(curated, seed=seed, train_ratio=train_ratio, val_ratio=val_ratio)
    summary = summarize_splits(assigned)

    # Check Gate
    is_gate_met = len(assigned) >= GATE_MIN_IMAGES
    gate_decision = {
        "gate": "fase_1_kurasi_data",
        "status": "LULUS" if is_gate_met else "NOT_MET",
        "criteria": f"Jumlah citra valid untuk task >= {GATE_MIN_IMAGES}",
        "actual_count": len(assigned),
        "threshold": GATE_MIN_IMAGES,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "curation_metadata": meta,
    }

    manifest_payload = {
        "phase": "1_curated_manifest",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "split_ratios": {"train": train_ratio, "val": val_ratio, "test": round(1.0 - train_ratio - val_ratio, 2)},
        "gate_status": gate_decision["status"],
        "curation_metadata": meta,
        "summary": summary,
        "records": assigned,
    }

    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. curated_manifest.json
    (out_dir / "curated_manifest.json").write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 2. curated_manifest.csv
    csv_fields = [
        "image_id", "cohort", "approved_label", "original_label", "split",
        "sha256", "pixel_sha256", "width", "height", "min_side_ge_224",
    ]
    with (out_dir / "curated_manifest.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(assigned)

    # 3. phase1_decision.json
    (out_dir / "phase1_decision.json").write_text(
        json.dumps(gate_decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return manifest_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=PHASE1_DIR, help="Output directory inside geometry/")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic split")
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Train ratio (default 0.70)")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Val ratio (default 0.15)")
    args = parser.parse_args(argv)

    try:
        manifest = run(
            out_dir=args.out,
            seed=args.seed,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
        )
    except Exception as exc:
        parser.error(str(exc))

    total = manifest["summary"]["total"]
    status = manifest["gate_status"]
    print(f"Curated manifest generated: {total} images; Gate Fase 1: {status}; output: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
