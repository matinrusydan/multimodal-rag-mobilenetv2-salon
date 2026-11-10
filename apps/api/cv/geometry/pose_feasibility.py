"""Reproducible Phase-0 MediaPipe Pose feasibility evaluation.

This evaluator measures model landmark availability, not anatomical correctness.
It deliberately imports MediaPipe only when inference is requested.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
CV_DIR = HERE.parent
DATASET = CV_DIR / "dataset"
SEED = 42
LANDMARKS = {"nose": 0, "ear_L": 7, "ear_R": 8, "shoulder_L": 11, "shoulder_R": 12}
CANONICAL_CLASSES = {"lurus", "bergelombang", "keriting", "sangat-keriting"}


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    """Two-sided Wilson score interval for a binomial proportion."""
    if total <= 0:
        return None
    p = successes / total
    d = 1 + z * z / total
    center = (p + z * z / (2 * total)) / d
    margin = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / d
    return [max(0.0, center - margin), min(1.0, center + margin)]


def landmark_is_valid(point: dict | None, v_min: float = 0.5, coord_tol: float = 0.15) -> bool:
    return bool(point and point.get("visibility", 0) >= v_min
                and -coord_tol <= point.get("x", 2) <= 1 + coord_tol
                and -coord_tol <= point.get("y", 2) <= 1 + coord_tol)


def summarize(records: list[dict], fields: tuple[str, ...] = ("cohort", "hair_class")) -> dict:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        groups[tuple(record.get(field, "unknown") for field in fields)].append(record)
    result = {}
    for key, rows in sorted(groups.items(), key=lambda pair: tuple(map(str, pair[0]))):
        key_name = "|".join(map(str, key))
        n = len(rows)
        row_summary = {"n": n}
        for metric in ("pose_ok", "shoulder_ok", "head_ok"):
            count = sum(bool(row.get(metric)) for row in rows)
            row_summary[metric] = count
            row_summary[f"{metric}_rate"] = count / n if n else None
            row_summary[f"{metric}_wilson95"] = wilson_interval(count, n)
            detected = [row for row in rows if row.get("pose_ok")]
            conditional = sum(bool(row.get(metric)) for row in detected)
            row_summary[f"{metric}_conditional_count"] = conditional
            row_summary[f"{metric}_conditional_rate"] = conditional / len(detected) if detected else None
            row_summary[f"{metric}_conditional_wilson95"] = wilson_interval(conditional, len(detected))
        result[key_name] = row_summary
    return result


def discover(dataset: Path = DATASET) -> list[dict]:
    rows = []
    cohort_defs = (("figaro1k", dataset / "figaro1k", False), ("new_dataset", dataset / "new_dataset", False),
                   ("new_dataset_backup_lowres", dataset / "new_dataset", True))
    for _, root, _ in cohort_defs:
        if not root.is_dir():
            raise FileNotFoundError(f"Required dataset root missing: {root}")
    for cohort, root, backup in cohort_defs:
        for class_dir in sorted(root.iterdir()):
            name = class_dir.name.removesuffix("_backup_lowres") if backup else class_dir.name
            name = "sangat-keriting" if name == "sangat keriting" else name
            if not class_dir.is_dir() or name not in CANONICAL_CLASSES or ("_backup_lowres" in class_dir.name) != backup:
                continue
            hair_class = name
            for path in sorted(class_dir.iterdir()):
                if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
                    rows.append({"path": path, "image_id": path.relative_to(dataset).as_posix(),
                                 "cohort": cohort, "hair_class": hair_class,
                                 "filename": path.name, "backup_lowres": backup})
    return rows


def matching_pairs(records: list[dict], left_cohort: str, right_cohort: str) -> list[tuple[dict, dict]]:
    """Pair class+filename candidates across the requested cohorts (not scene identity)."""
    left = {(r["hair_class"], r["filename"]): r for r in records if r["cohort"] == left_cohort}
    right = {(r["hair_class"], r["filename"]): r for r in records if r["cohort"] == right_cohort}
    return [(left[key], right[key]) for key in sorted(left.keys() & right.keys())]


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer(path: Path, landmarker, v_min: float, coord_tol: float) -> dict:
    try:
        with Image.open(path) as source:
            image = source.convert("RGB")
            width, height = image.size
            import numpy as np
            import mediapipe as mp
            result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(image)))
    except Exception as exc:
        return {"width": None, "height": None, "pose_ok": False, "shoulder_ok": False, "head_ok": False,
                "landmarks": {}, "error": f"inference_or_load_error: {type(exc).__name__}: {exc}"}
    if not result.pose_landmarks:
        return {"width": width, "height": height, "pose_ok": False, "shoulder_ok": False,
                "head_ok": False, "landmarks": {}, "error": "no_pose"}
    points = result.pose_landmarks[0]
    landmarks = {name: {"x": float(points[idx].x), "y": float(points[idx].y),
                        "visibility": float(points[idx].visibility)} for name, idx in LANDMARKS.items()}
    sh = all(landmark_is_valid(landmarks[key], v_min, coord_tol) for key in ("shoulder_L", "shoulder_R"))
    hd = any(landmark_is_valid(landmarks[key], v_min, coord_tol) for key in ("nose", "ear_L", "ear_R"))
    return {"width": width, "height": height, "pose_ok": True, "shoulder_ok": sh,
            "head_ok": hd, "landmarks": landmarks, "error": None}


def overlay(path: Path, record: dict, destination: Path, v_min: float, coord_tol: float) -> None:
    with Image.open(path) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for name, point in record.get("landmarks", {}).items():
        x, y = int(point["x"] * width), int(point["y"] * height)
        color = "lime" if landmark_is_valid(point, v_min, coord_tol) else "red"
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color, outline="black")
        draw.text((x + 5, y), name, fill=color, stroke_width=1, stroke_fill="black")
    image.save(destination)


def contact_sheet(paths: list[Path], destination: Path) -> None:
    tile_w, tile_h = 240, 280
    canvas = Image.new("RGB", (tile_w * 4, tile_h * max(1, (len(paths) + 3) // 4)), "white")
    draw = ImageDraw.Draw(canvas)
    for index, path in enumerate(paths):
        with Image.open(path) as source:
            image = source.convert("RGB")
        image.thumbnail((tile_w - 8, tile_h - 32))
        x, y = (index % 4) * tile_w, (index // 4) * tile_h
        canvas.paste(image, (x, y + 20))
        draw.text((x + 3, y + 3), path.name[:34], fill="black")
    canvas.save(destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "reports" / "phase0")
    parser.add_argument("--limit", type=int, help="Maximum images per cohort/class (deterministic sample)")
    parser.add_argument("--model", choices=("lite", "heavy"), default="lite")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--v-min", type=float, default=0.5)
    parser.add_argument("--coord-tol", type=float, default=0.15)
    parser.add_argument("--min-detection", type=float, default=0.3)
    args = parser.parse_args(argv)
    out = args.out.resolve()
    if not out.is_relative_to(HERE):
        parser.error("--out must resolve inside apps/api/cv/geometry/")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")

    items = discover()
    rng = random.Random(args.seed)
    if args.limit:
        selected = []
        groups: dict[tuple, list] = defaultdict(list)
        for item in items:
            groups[(item["cohort"], item["hair_class"])].append(item)
        for key in sorted(groups):
            rows = groups[key]
            rng.shuffle(rows)
            selected.extend(rows[:args.limit])
        items = sorted(selected, key=lambda row: row["image_id"])

    weights = CV_DIR / "weights" / f"pose_landmarker_{args.model}.task"
    if not weights.exists():
        parser.error(f"pose model not found (no downloads): {weights}")
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(weights)),
        running_mode=vision.RunningMode.IMAGE, num_poses=1,
        min_pose_detection_confidence=args.min_detection,
        min_pose_presence_confidence=args.min_detection,
        output_segmentation_masks=False)
    out.mkdir(parents=True, exist_ok=True)
    overlay_dir = out / "overlays"
    overlay_dir.mkdir(exist_ok=True)
    rows = []
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        for item in items:
            record = {key: item[key] for key in ("image_id", "cohort", "hair_class", "filename", "backup_lowres")}
            record["sha256"] = checksum(item["path"])
            record.update(infer(item["path"], landmarker, args.v_min, args.coord_tol))
            rows.append(record)
            if record["landmarks"]:
                status = "success" if record["shoulder_ok"] and record["head_ok"] else "failure"
                safe = hashlib.sha1(record["image_id"].encode()).hexdigest()[:12]
                overlay(item["path"], record, overlay_dir / f"{status}_{safe}.jpg", args.v_min, args.coord_tol)
            elif record["error"] == "no_pose":
                safe = hashlib.sha1(record["image_id"].encode()).hexdigest()[:12]
                shutil.copyfile(item["path"], overlay_dir / f"failure_no_pose_{safe}.jpg")

    overall = summarize(rows)
    by_cohort = summarize(rows, ("cohort",))
    canonical_rows = [row for row in rows if row["cohort"] in {"figaro1k", "new_dataset"}]
    canonical_by_class = summarize(canonical_rows)
    canonical_by_cohort = summarize(canonical_rows, ("cohort",))
    paired = []
    for old, new in matching_pairs(rows, "figaro1k", "new_dataset"):
        paired.append({"hair_class": old["hair_class"], "filename": old["filename"], "figaro_image_id": old["image_id"],
                       "new_image_id": new["image_id"], "same_scene_verified": False,
                       "note": "Filename and class match only; this does not establish same scene."})
    for high, low in matching_pairs(rows, "new_dataset", "new_dataset_backup_lowres"):
        paired.append({"hair_class": high["hair_class"], "filename": high["filename"], "new_image_id": high["image_id"],
                       "backup_image_id": low["image_id"], "same_scene_verified": False,
                       "new": {metric: high.get(metric) for metric in ("pose_ok", "shoulder_ok", "head_ok")},
                       "backup": {metric: low.get(metric) for metric in ("pose_ok", "shoulder_ok", "head_ok")},
                       "delta_backup_minus_new": {metric: (int(bool(low.get(metric))) - int(bool(high.get(metric))))
                                                  for metric in ("pose_ok", "shoulder_ok", "head_ok")},
                       "note": "Pencocokan kelas+nama berkas tidak membuktikan adegan sama; pemulihan mungkin mengubah crop/adegan, bukan hanya resolusi."})
    records = []
    old_pairs = {(a["image_id"], b["image_id"]) for a, b in matching_pairs(rows, "figaro1k", "new_dataset")}
    backup_pairs = {(a["image_id"], b["image_id"]) for a, b in matching_pairs(rows, "new_dataset", "new_dataset_backup_lowres")}
    for row in rows:
        records.append({**row, "paired_filename_candidate": any(row["image_id"] in pair for pair in old_pairs | backup_pairs)})
    actual_counts = {name: sum(row["cohort"] == name for row in rows)
                     for name in ("figaro1k", "new_dataset", "new_dataset_backup_lowres")}
    dimensions = {}
    for cohort in actual_counts:
        cohort_rows = [row for row in rows if row["cohort"] == cohort]
        dimensions[cohort] = {"min_width": min((row["width"] for row in cohort_rows if row["width"]), default=None),
                              "min_height": min((row["height"] for row in cohort_rows if row["height"]), default=None),
                              "min_short_side": min((min(row["width"], row["height"]) for row in cohort_rows if row["width"] and row["height"]), default=None),
                              "images_both_dimensions_ge_224": sum(bool(row["width"] and row["height"] and min(row["width"], row["height"]) >= 224) for row in cohort_rows)}
    n = len(canonical_rows)
    sh = sum(row["shoulder_ok"] for row in canonical_rows)
    hd = sum(row["head_ok"] for row in canonical_rows)
    gate = {"status": "NOT_ASSESSED" if n == 0 else
            ("LULUS" if sh / n >= .70 and hd / n >= .80 else "NOT_MET"),
            "canonical_n": n, "shoulder_rate": sh / n if n else None, "head_rate": hd / n if n else None,
            "shoulder_threshold": .70, "head_threshold": .80,
            "human_validation": "not performed; this gate is not fully human validated"}
    import importlib.metadata
    versions = {}
    for package in ("mediapipe", "Pillow", "numpy"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    payload = {"phase": "0_pose_feasibility", "created_utc": datetime.now(timezone.utc).isoformat(),
               "seed": args.seed, "model": args.model, "model_path": str(weights),
               "model_sha256": checksum(weights), "package_versions": versions,
               "parameters": {"min_detection_and_presence": args.min_detection, "visibility": args.v_min,
                              "coordinate_tolerance": args.coord_tol},
               "canonical_expected_counts": {"figaro1k": 252, "new_dataset": 137}, "actual_cohort_counts": actual_counts,
               "dimensions_by_cohort": dimensions, "n_evaluated": len(rows), "aggregate_unconditional_by_cohort_class": overall,
               "aggregate_unconditional_by_cohort": by_cohort,
               "aggregate_canonical_by_cohort_class": canonical_by_class,
               "aggregate_canonical_by_cohort": canonical_by_cohort,
               "canonical_gate_figaro_plus_new_dataset": gate,
               "exploratory_all_cohorts": {"by_cohort_class": overall},
               "paired_filename_candidates": paired,
               "caveats": ["Conditional rates are conditioned on pose_ok; unconditional rates use all evaluated images.",
                           "MediaPipe visibility is not anatomical accuracy; manual cross-check is not performed.",
                           "Low-resolution backups are a separate cohort and excluded from canonical gate.",
                           "No synthetic downsampling is substituted for absent backup images."], "records": records}
    (out / "pose_feasibility.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if rows:
        with (out / "pose_feasibility.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            fields = ["image_id", "cohort", "hair_class", "filename", "backup_lowres", "sha256", "width", "height",
                      "pose_ok", "shoulder_ok", "head_ok", "error", "landmarks"]
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({**row, "landmarks": json.dumps(row["landmarks"], ensure_ascii=False)})
    successes = [overlay_dir / f"success_{hashlib.sha1(row['image_id'].encode()).hexdigest()[:12]}.jpg"
                 for row in rows if row.get("landmarks") and row["shoulder_ok"] and row["head_ok"]]
    failures = [overlay_dir / f"failure_{hashlib.sha1(row['image_id'].encode()).hexdigest()[:12]}.jpg"
                for row in rows if row.get("landmarks") and not (row["shoulder_ok"] and row["head_ok"])]
    failures += [overlay_dir / f"failure_no_pose_{hashlib.sha1(row['image_id'].encode()).hexdigest()[:12]}.jpg"
                 for row in rows if row.get("error") == "no_pose"]
    contact_sheet(successes[:24], out / "contact_success.jpg")
    contact_sheet(failures[:24], out / "contact_failure.jpg")
    table = ["| Kohort | N aktual | Min dimensi (px) | Semua dimensi ≥224 | Pose | Bahu | Kepala |", "|---|---:|---:|---:|---:|---:|---:|"]
    for cohort, summary in by_cohort.items():
        dim = dimensions[cohort]
        minimum = f"sisi pendek minimum {dim['min_short_side']}" if dim["min_short_side"] is not None else "—"
        table.append(f"| {cohort} | {summary['n']} | {minimum} | {dim['images_both_dimensions_ge_224']} | {summary['pose_ok_rate']:.3f} | {summary['shoulder_ok_rate']:.3f} | {summary['head_ok_rate']:.3f} |")
    lines = ["# Laporan kelayakan pose — Fase 0", "", f"Model: `{args.model}` (SHA-256 `{payload['model_sha256']}`); seed: `{args.seed}`; gambar dievaluasi: {len(rows)}.",
             "", "## Ringkasan kohort (hasil skrip ini)", "", *table,
             "", "| Gate kanonik | N | Rate bahu | Rate kepala | Status |", "|---|---:|---:|---:|---|",
             f"| Figaro + new_dataset | {n} | {gate['shoulder_rate']} | {gate['head_rate']} | {gate['status']} |",
             "", "Angka ringkasan di atas dihasilkan dari eksekusi evaluator yang sama. Tabel detail per kelas dan interval Wilson 95% (unconditional serta conditional pada pose terdeteksi) tersedia di JSON.",
             "", "## Batasan dan interpretasi", "", "Skor visibility MediaPipe bukan validasi akurasi anatomi; evaluasi independen manusia belum dilakukan, sehingga gate ini belum tervalidasi penuh.",
             "Pemulihan backup dapat mengubah crop atau adegan, bukan semata resolusi; pasangan berdasarkan nama berkas bukan bukti adegan sama. Backup rendah resolusi terpisah dan tidak termasuk gate kanonik. Tidak ada downsampling sintetis sebagai pengganti backup.",
             "", "Artefak: `pose_feasibility.json`, `pose_feasibility.csv`, lembar kontak dan overlay per gambar."]
    (out / "README-phase0.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Evaluated {len(rows)} images; canonical gate: {gate['status']}; outputs: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
