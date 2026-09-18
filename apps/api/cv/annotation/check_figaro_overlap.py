# -*- coding: utf-8 -*-
"""Check potential subject overlap between Figaro-1k and figaro-extra/bald using dHash.

dHash (difference hashing) computes a 64-bit perceptual hash from image pixels.
It measures VISUAL SIMILARITY, NOT subject identity.

Categories:
  - likely_duplicate:        Hamming distance <= 4
  - possible_same_subject:   Hamming distance <= 10
  - no_evidence:             Hamming distance > 10

[WARNING] dHash similarity is NOT proof of subject identity.
    Suspicious matches require MANUAL REVIEW before group assignment.
    Do NOT auto-delete or auto-merge based on dHash alone.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" annotation\\check_figaro_overlap.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parents[1]  # apps/api/cv
FIGARO1K = BASE / "dataset" / "figaro1k"
EXTRA = BASE / "dataset" / "extra"
REPORT_DIR = BASE / "annotation" / "reports"

# Thresholds (heuristic, documented)
LIKELY_DUP_THRESHOLD = 4
POSSIBLE_SAME_THRESHOLD = 10


def dhash(img_path: Path, hash_size: int = 8) -> np.ndarray | None:
    """Compute 64-bit dHash (difference hash) as a boolean numpy array.

    dHash: resize to (hash_size+1, hash_size) grayscale, then compare adjacent pixels.
    Returns array of (hash_size * hash_size) booleans.
    """
    try:
        img = Image.open(img_path).convert("L").resize(
            (hash_size + 1, hash_size), Image.Resampling.LANCZOS
        )
        arr = np.asarray(img, dtype=np.int16)
        # Difference: left pixel < right pixel -> 1
        diff = arr[:, 1:] > arr[:, :-1]
        return diff.flatten()
    except Exception:
        return None


def hamming(h1: np.ndarray, h2: np.ndarray) -> int:
    """Hamming distance between two boolean arrays."""
    return int(np.count_nonzero(h1 != h2))


def collect_hashes(folder: Path, pattern: str = "*.jpg") -> dict[str, np.ndarray]:
    """Compute dHash for all images in a folder. Returns {relpath: hash}."""
    result = {}
    if not folder.exists():
        return result
    for img_path in sorted(folder.glob(pattern)):
        h = dhash(img_path)
        if h is not None:
            result[str(img_path.relative_to(BASE))] = h
    return result


def collect_figaro_hashes() -> dict[str, np.ndarray]:
    """Collect hashes from Figaro-1k (4 type subfolders)."""
    result = {}
    for type_dir in sorted(FIGARO1K.iterdir()):
        if not type_dir.is_dir():
            continue
        result.update(collect_hashes(type_dir))
    return result


def collect_extra_hashes() -> dict[str, np.ndarray]:
    """Collect hashes from figaro-extra (4 length subfolders)."""
    result = {}
    for length_dir in sorted(EXTRA.iterdir()):
        if not length_dir.is_dir():
            continue
        # Skip Hairstyle40 sketches (not real photos)
        for img_path in sorted(length_dir.glob("*.jpg")):
            if img_path.stem.startswith("hs40_"):
                continue  # skip sketches
            h = dhash(img_path)
            if h is not None:
                result[str(img_path.relative_to(BASE))] = h
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Check Figaro-1k vs figaro-extra overlap (dHash).")
    ap.add_argument(
        "--out", default=str(REPORT_DIR / "figaro_subject_overlap.json"), help="Output path"
    )
    ap.add_argument(
        "--likely-dup", type=int, default=LIKELY_DUP_THRESHOLD, help="Hamming threshold for likely_duplicate"
    )
    ap.add_argument(
        "--possible-same", type=int, default=POSSIBLE_SAME_THRESHOLD, help="Hamming threshold for possible_same_subject"
    )
    args = ap.parse_args()

    print("=== Figaro Overlap Check (dHash) ===")
    print("[WARNING] dHash = visual similarity, NOT proof of subject identity.")
    print(f"Thresholds: likely_dup <= {args.likely_dup}, possible_same <= {args.possible_same}")
    print()

    print("Computing hashes for Figaro-1k...")
    figaro_hashes = collect_figaro_hashes()
    print(f"  Figaro-1k: {len(figaro_hashes)} images hashed")

    print("Computing hashes for figaro-extra (excluding Hairstyle40 sketches)...")
    extra_hashes = collect_extra_hashes()
    print(f"  figaro-extra (real photos only): {len(extra_hashes)} images hashed")

    if not figaro_hashes or not extra_hashes:
        print("ERROR: Not enough images to compare.")
        return

    print("\nComparing all pairs (this may take a moment)...")
    likely_duplicates = []
    possible_same = []
    no_evidence_count = 0
    total_pairs = 0

    for fig_path, fig_hash in figaro_hashes.items():
        for ext_path, ext_hash in extra_hashes.items():
            total_pairs += 1
            dist = hamming(fig_hash, ext_hash)
            if dist <= args.likely_dup:
                likely_duplicates.append(
                    {"figaro_image": fig_path, "extra_image": ext_path, "hamming_distance": dist}
                )
            elif dist <= args.possible_same:
                possible_same.append(
                    {"figaro_image": fig_path, "extra_image": ext_path, "hamming_distance": dist}
                )
            else:
                no_evidence_count += 1

    print(f"\nTotal pairs compared: {total_pairs}")
    print(f"  likely_duplicate (Hamming <= {args.likely_dup}): {len(likely_duplicates)}")
    print(f"  possible_same_subject (Hamming <= {args.possible_same}): {len(possible_same)}")
    print(f"  no_evidence: {no_evidence_count}")

    # Show top likely duplicates
    if likely_duplicates:
        print(f"\n=== LIKELY DUPLICATES (top 20) ===")
        for d in sorted(likely_duplicates, key=lambda x: x["hamming_distance"])[:20]:
            print(f"  d={d['hamming_distance']}: {d['figaro_image']} <-> {d['extra_image']}")

    if possible_same:
        print(f"\n=== POSSIBLE SAME SUBJECT (top 10) ===")
        for d in sorted(possible_same, key=lambda x: x["hamming_distance"])[:10]:
            print(f"  d={d['hamming_distance']}: {d['figaro_image']} <-> {d['extra_image']}")

    report = {
        "method": "dHash (64-bit perceptual hash)",
        "warning": "dHash measures visual similarity, NOT subject identity. Manual review required.",
        "thresholds": {
            "likely_duplicate": args.likely_dup,
            "possible_same_subject": args.possible_same,
        },
        "n_figaro1k_images": len(figaro_hashes),
        "n_extra_images": len(extra_hashes),
        "n_total_pairs": total_pairs,
        "n_likely_duplicate": len(likely_duplicates),
        "n_possible_same_subject": len(possible_same),
        "n_no_evidence": no_evidence_count,
        "likely_duplicates": sorted(likely_duplicates, key=lambda x: x["hamming_distance"]),
        "possible_same_subjects": sorted(possible_same, key=lambda x: x["hamming_distance"]),
        "recommendation": (
            "If likely_duplicates > 0: manually review each pair. "
            "If confirmed same subject: assign same group_id to prevent train/val/test leakage. "
            "Do NOT auto-delete or auto-merge."
        ),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport -> {out_path}")


if __name__ == "__main__":
    main()
