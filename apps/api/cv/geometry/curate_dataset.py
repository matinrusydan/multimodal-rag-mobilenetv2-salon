"""Deterministic, non-destructive Phase 1 dataset audit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATASET = HERE.parent / "dataset"
DEFAULT_OUT = HERE / "reports" / "phase1"
CLASSES = {"lurus", "bergelombang", "keriting", "sangat-keriting"}
ALIASES = {"sangat keriting": "sangat-keriting"}
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dct_matrix(size: int = 32) -> np.ndarray:
    x = np.arange(size, dtype=np.float64)
    k = x[:, None]
    matrix = np.cos((math.pi / size) * (x + 0.5) * k)
    matrix[0] *= math.sqrt(1 / size)
    matrix[1:] *= math.sqrt(2 / size)
    return matrix


DCT32 = _dct_matrix()


def perceptual_hashes(rgb: Image.Image) -> tuple[str, str]:
    gray = rgb.convert("L")
    dh = np.asarray(gray.resize((9, 8), Image.Resampling.LANCZOS), dtype=np.int16)
    differences = (dh[:, :-1] > dh[:, 1:]).flatten()
    dhash = sum(int(value) << i for i, value in enumerate(differences))
    small = np.asarray(gray.resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float64)
    coeff = DCT32 @ small @ DCT32.T
    low = coeff[:8, :8].flatten()
    median = float(np.median(low[1:]))
    phash = sum(int(value > median) << i for i, value in enumerate(low))
    return f"{dhash:016x}", f"{phash:016x}"


def discover(dataset: Path) -> list[dict]:
    rows = []
    for cohort in ("figaro1k", "new_dataset"):
        root = dataset / cohort
        if not root.is_dir():
            raise FileNotFoundError(f"Required dataset root missing: {root}")
        for class_dir in sorted(root.iterdir()):
            label = ALIASES.get(class_dir.name, class_dir.name)
            if not class_dir.is_dir() or label not in CLASSES or "backup" in class_dir.name.lower():
                continue
            for path in sorted(class_dir.iterdir()):
                if path.is_file() and path.suffix.lower() in EXTENSIONS:
                    rows.append({"image_id": path.relative_to(dataset).as_posix(), "path": path,
                                 "cohort": cohort, "hair_class": label})
    return rows


def inspect(item: dict) -> dict:
    path = item["path"]
    row = {k: item[k] for k in ("image_id", "cohort", "hair_class")}
    row.update({"sha256": sha256_file(path), "pixel_sha256": None, "width": None, "height": None,
                "min_side_ge_224": False, "dhash64": None, "phash64": None, "error": None,
                "source_review": "unknown_pending_review", "license_review": "unknown_pending_review",
                "label_review": "unknown_pending_review", "subject_review": "unknown_pending_review"})
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            row["width"], row["height"] = image.size
            row["min_side_ge_224"] = min(image.size) >= 224
            digest = hashlib.sha256()
            digest.update(f"{image.width}x{image.height}:RGB:".encode("ascii"))
            digest.update(image.tobytes())
            row["pixel_sha256"] = digest.hexdigest()
            row["dhash64"], row["phash64"] = perceptual_hashes(image)
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def duplicate_candidates(records: list[dict]) -> list[dict]:
    candidates = []
    for i, first in enumerate(records):
        for second in records[i + 1:]:
            exact = ("raw_sha256" if first["sha256"] == second["sha256"] else
                     "decoded_rgb_pixels" if first["pixel_sha256"] and first["pixel_sha256"] == second["pixel_sha256"] else None)
            dh = hamming(first["dhash64"], second["dhash64"]) if first["dhash64"] and second["dhash64"] else None
            ph = hamming(first["phash64"], second["phash64"]) if first["phash64"] and second["phash64"] else None
            if exact or (dh is not None and dh <= 6) or (ph is not None and ph <= 6):
                candidates.append({"image_id_a": first["image_id"], "image_id_b": second["image_id"],
                                   "dhash_distance": dh, "phash_distance": ph, "exact_kind": exact,
                                   "label_conflict": first["hair_class"] != second["hair_class"],
                                   "review_status": "manual_review_required",
                                   "interpretation": "Heuristic pair candidate; does not establish subject identity."})
    return candidates


def run(dataset: Path, out: Path, seed: int, overwrite: bool = False) -> dict:
    out = out.resolve()
    dataset = dataset.resolve()
    if not out.is_relative_to(HERE):
        raise ValueError("--out must resolve inside geometry/")
    if out.is_relative_to(dataset) or out.is_relative_to(HERE / "source_recovery"):
        raise ValueError("--out cannot be inside dataset or source_recovery")
    targets = [out / "dataset_curation.json", out / "records.csv", out / "duplicate_candidates.csv"]
    if not overwrite and any(path.exists() for path in targets):
        raise FileExistsError("Output exists; use --overwrite to replace report files")
    records = [inspect(item) for item in discover(dataset)]
    candidates = duplicate_candidates(records)
    grouped = defaultdict(Counter)
    for row in records:
        group = grouped[row["cohort"]]
        group["total"] += 1
        group[row["hair_class"]] += 1
        group["decode_errors"] += row["error"] is not None
        group["min_side_ge_224"] += row["min_side_ge_224"]
    summary = {cohort: {"total": counts["total"], "by_class": {label: counts[label] for label in sorted(CLASSES)},
                        "decode_errors": counts["decode_errors"], "min_side_ge_224": counts["min_side_ge_224"]}
               for cohort, counts in sorted(grouped.items())}
    payload = {"phase": "1_dataset_audit", "created_utc": datetime.now(timezone.utc).isoformat(),
               "seed": seed, "status": "NOT_READY_PENDING_REVIEW", "cohort_summary": summary,
               "record_count": len(records), "duplicate_candidate_count": len(candidates),
               "review_policy": "Source, license, label, and subject status remain unknown pending human review. Technical checks do not approve images or determine training validity.",
               "duplicate_policy": "Exact hashes identify identical content only; perceptual pairs are heuristic candidates for manual review, not identity or split decisions.",
               "records": records}
    out.mkdir(parents=True, exist_ok=True)
    (out / targets[0].name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for filename, rows, fields in (
        ("records.csv", records, ["image_id", "cohort", "hair_class", "sha256", "pixel_sha256", "width", "height", "min_side_ge_224", "dhash64", "phash64", "error", "source_review", "license_review", "label_review", "subject_review"]),
        ("duplicate_candidates.csv", candidates, ["image_id_a", "image_id_b", "dhash_distance", "phash_distance", "exact_kind", "label_conflict", "review_status", "interpretation"]),
    ):
        with (out / filename).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true", help="Replace only this tool's three report files")
    args = parser.parse_args(argv)
    try:
        report = run(args.dataset, args.out, args.seed, args.overwrite)
    except (ValueError, FileExistsError, OSError) as exc:
        parser.error(str(exc))
    print(f"Audit {report['record_count']} citra; status {report['status']}; output {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
