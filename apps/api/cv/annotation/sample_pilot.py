# -*- coding: utf-8 -*-
"""Generate pilot annotation manifest (80 Figaro-1k images, seed 42, stratified by hair type).

Sampling is INDEPENDENT of all pseudo-labels (Gemini/geometric/style mapping).
Only Figaro-1k real back-view photos are used. Bald and Hairstyle40 sketches are excluded.

Output:
  annotation/ground_truth/pilot_manifest.json

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" annotation\\sample_pilot.py [--seed 42] [--per-type 20]

Read-only: does NOT modify any existing dataset/labels.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]  # apps/api/cv
DATASET = BASE / "dataset" / "figaro1k"
OUT_DIR = Path(__file__).resolve().parents[0] / "ground_truth"
OUT_PATH = OUT_DIR / "pilot_manifest.json"

# Figaro-1k type folders (ID labels) with EN mapping
TYPE_MAP = [
    ("lurus", "straight"),
    ("bergelombang", "wavy"),
    ("keriting", "curly"),
    ("sangat-keriting", "kinky"),
]

TAXONOMY_VERSION = "pilot-v2"
GUIDELINE_VERSION = "pilot-v2"


def collect_frames(type_dir: Path) -> list[str]:
    """Return sorted list of frame stems (without extension) for a type folder."""
    return sorted(f.stem for f in type_dir.glob("*.jpg"))


def carry_over_frames(carry_path: Path | None) -> dict[str, set[str]]:
    """Baca manifest lama -> {type_id: set(frame_stems)} untuk dipertahankan (carry-over).

    Berguna agar sample baru mencakup sample lama (mis. anotasi sebelumnya bisa
    ditinjau ulang, bukan dibuang).
    """
    result: dict[str, set[str]] = {}
    if carry_path is None or not carry_path.exists():
        return result
    try:
        m = json.loads(carry_path.read_text(encoding="utf-8"))
        for img in m.get("images", []):
            tid = img.get("hair_type_id")
            fid = img.get("image_id", "")
            frame = fid.rsplit("/", 1)[-1].split(".")[0]
            if tid and frame:
                result.setdefault(tid, set()).add(frame)
    except Exception as exc:
        print(f"PERINGATAN: gagal baca carry-over {carry_path}: {exc}")
    return result


def build_sample(seed: int, per_type: int, carry: dict[str, set[str]]) -> list[dict]:
    """Stratified random sample: per_type images per hair_type, deterministic via seed.

    Jika `carry` diberikan, frame dari sample lama diprioritaskan dimasukkan,
    sisanya diisi acak dari frame yang belum diambil.
    """
    rng = random.Random(seed)
    images: list[dict] = []
    for type_id, type_en in TYPE_MAP:
        type_dir = DATASET / type_id
        if not type_dir.exists():
            raise FileNotFoundError(f"Figaro type folder missing: {type_dir}")
        frames = collect_frames(type_dir)
        if len(frames) < per_type:
            raise ValueError(
                f"Not enough images for {type_id}: {len(frames)} < {per_type}"
            )

        carry_frames = sorted(carry.get(type_id, set()) & set(frames))
        # Ambil carry dulu (maks per_type), lalu isi sisanya acak
        picked = carry_frames[:per_type]
        remaining = [f for f in frames if f not in set(picked)]
        need = per_type - len(picked)
        if need > 0:
            picked += rng.sample(remaining, need)

        for frame in picked:
            fname = f"{frame}.jpg"
            images.append(
                {
                    "image_id": f"figaro1k/{type_id}/{fname}",
                    "source": "figaro1k",
                    "hair_type": type_en,
                    "hair_type_id": type_id,
                    "relpath": f"dataset/figaro1k/{type_id}/{fname}",
                }
            )
    # Shuffle agar anotator melihat tipe berselang-seling
    rng2 = random.Random(seed + 1)
    rng2.shuffle(images)
    return images


def validate_unique(images: list[dict]) -> None:
    ids = [img["image_id"] for img in images]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate image_id detected in sample!")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate pilot annotation manifest (Figaro-1k only).")
    ap.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    ap.add_argument("--per-type", type=int, default=20, help="Images per hair type (default: 20)")
    ap.add_argument("--out", default=str(OUT_PATH), help="Output manifest path")
    ap.add_argument(
        "--carry-over",
        default=None,
        help="Manifest lama; frame-nya diprioritaskan masuk (default: tidak ada)",
    )
    args = ap.parse_args()

    print(f"Figaro-1k dataset: {DATASET}")
    if not DATASET.exists():
        raise SystemExit(f"Dataset not found: {DATASET}")

    carry_path = Path(args.carry_over) if args.carry_over else None
    carry = carry_over_frames(carry_path)
    if carry:
        n_carry = sum(len(v) for v in carry.values())
        print(f"Carry-over dari {carry_path}: {n_carry} frame")

    images = build_sample(args.seed, args.per_type, carry)
    validate_unique(images)

    # Per-type counts
    from collections import Counter
    counts = Counter(img["hair_type"] for img in images)

    manifest = {
        "schema_version": TAXONOMY_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "guideline_version": GUIDELINE_VERSION,
        "seed": args.seed,
        "per_type": args.per_type,
        "total": len(images),
        "source": "figaro1k",
        "description": (
            f"Pilot annotation sample ({args.per_type} per hair type). "
            "Stratified by hair type. Sampling INDEPENDENT of Gemini/geometric/pseudo-labels. "
            "Only Figaro-1k real photos (bald & Hairstyle40 sketches excluded)."
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "images": images,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        # Safety: backup jika sudah ada, jangan overwrite diam-diam
        import shutil

        backup = out_path.with_suffix(out_path.suffix + ".bak")
        shutil.copy(out_path, backup)
        print(f"CATATAN: {out_path.name} sudah ada -> backup ke {backup.name}")
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nSample generated: {len(images)} images (seed={args.seed})")
    for ht, c in sorted(counts.items()):
        print(f"  {ht:16s} {c}")
    print(f"\nManifest -> {out_path}")


if __name__ == "__main__":
    main()
