"""Phase 3/4: Geometric Hair Volume / Thickness Measurement.

Extracts normalized volumetric and lateral spread ratios relative to cranial dimensions:
- R_vol = Area_hair / (H_head^2)  (dimensionless normalized area)
- R_width = W_hair_max / W_cranial (lateral spread relative to cranial width)

Maps ratios to canonical 3 classes:
- 'tipis': R_vol <= 0.70 and R_width <= 1.15 (thin / close to scalp)
- 'sedang': intermediate spread and volume
- 'tebal': R_vol >= 1.35 or R_width >= 1.35 (thick / highly voluminous)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional, Tuple

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
from measure_length import estimate_cranial_reference

HAIR_VOLUME_CLASSES = ["tipis", "sedang", "tebal"]


def classify_volume_from_ratios(
    volume_ratio: float,
    width_ratio: float,
) -> Tuple[str, float]:
    """Classify volume into canonical classes with confidence scoring."""
    r_v = volume_ratio
    r_w = width_ratio

    if r_v <= 0.70 and r_w <= 1.15:
        cls_name = "tipis"
        margin = min(0.70 - r_v, 1.15 - r_w)
    elif r_v >= 1.35 or r_w >= 1.35:
        cls_name = "tebal"
        margin = max(r_v - 1.35, r_w - 1.35)
    else:
        cls_name = "sedang"
        dist_to_tipis = max(0.0, min(r_v - 0.70, r_w - 1.15))
        dist_to_tebal = max(0.0, min(1.35 - r_v, 1.35 - r_w))
        margin = min(dist_to_tipis, dist_to_tebal)

    conf = min(0.98, max(0.55, 0.72 + float(margin) * 0.30))
    return cls_name, round(conf, 4)


def measure_hair_volume(
    mask: np.ndarray,
    cranial_ref: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Measure normalized hair volume and lateral spread from binary mask."""
    if cranial_ref is None:
        cranial_ref = estimate_cranial_reference(mask)

    if cranial_ref["is_empty"]:
        return {
            "status": "empty_mask",
            "volume_class": None,
            "confidence": None,
            "volume_ratio": None,
            "width_ratio": None,
            "features": {
                "hair_area_pixels": 0,
                "max_hair_width": 0,
                "cranial_width": None,
                "estimated_head_height": None,
            },
        }

    binary = (mask > 0).astype(np.uint8)
    hair_area = int(binary.sum())
    max_hair_width = int(binary.sum(axis=1).max()) if hair_area > 0 else 0

    w_cran = cranial_ref["cranial_width"]
    h_head = cranial_ref["estimated_head_height"]

    r_vol = float(hair_area) / max(1.0, float(h_head * h_head))
    r_width = float(max_hair_width) / max(1.0, float(w_cran))

    cls_name, conf = classify_volume_from_ratios(r_vol, r_width)

    return {
        "status": "ok",
        "volume_class": cls_name,
        "confidence": conf,
        "volume_ratio": round(r_vol, 4),
        "width_ratio": round(r_width, 4),
        "features": {
            "hair_area_pixels": hair_area,
            "max_hair_width": max_hair_width,
            "cranial_width": w_cran,
            "estimated_head_height": h_head,
        },
    }


def _geometry_output(path: str) -> Path:
    out = Path(path).resolve()
    if not out.is_relative_to(HERE):
        raise ValueError("Output path must remain inside apps/api/cv/geometry/")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mask", required=True, type=Path, help="Input hair mask image path")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path inside geometry/")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file")
    args = parser.parse_args(argv)

    mask_img = cv2.imread(str(args.mask), cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        parser.error(f"Could not read mask image: {args.mask}")

    result = measure_hair_volume(mask_img)
    output_text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"

    if args.out:
        out_path = _geometry_output(str(args.out))
        if out_path.exists() and not args.overwrite:
            parser.error(f"Output file already exists: {out_path} (use --overwrite)")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"Saved volume measurement to {out_path}")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
