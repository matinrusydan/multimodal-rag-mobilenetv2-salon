"""Extract descriptive mask geometry and calibrated tied-hair assessment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional, Tuple

import cv2
import numpy as np


def extract_shape_features(mask: np.ndarray) -> dict[str, Any]:
    """Return descriptive geometry; undefined contour metrics are None."""
    if not isinstance(mask, np.ndarray) or mask.ndim != 2:
        raise ValueError("mask must be a two-dimensional numpy array")
    if mask.size == 0:
        raise ValueError("mask must not be empty")
    if not np.isfinite(mask).all():
        raise ValueError("mask values must be finite")
    binary = (mask > 0).astype(np.uint8)
    height, width = binary.shape
    area = int(binary.sum())
    ys, xs = np.nonzero(binary)
    if area:
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        bbox_width, bbox_height = x1 - x0 + 1, y1 - y0 + 1
        max_row_width = int(binary.sum(axis=1).max())
        border_contact = bool(binary[0, :].any() or binary[-1, :].any() or binary[:, 0].any() or binary[:, -1].any())

        # Waist constriction analysis along vertical extent
        h = bbox_height
        if h >= 30:
            row_widths = binary[y0 : y1 + 1].sum(axis=1).astype(float)
            k = max(3, int(0.04 * h))
            sm = np.convolve(row_widths, np.ones(k) / k, mode="same")
            t1 = max(1, h // 3)
            t2 = max(t1 + 1, 2 * h // 3)
            w_upper = float(sm[:t1].max()) if t1 > 0 else 0.0
            w_mid_min = float(sm[t1:t2].min()) if t2 > t1 else 0.0
            w_lower = float(sm[t2:].max()) if h > t2 else 0.0
            denom = max(1.0, min(w_upper, w_lower))
            waist_constriction_ratio = float(w_mid_min / denom) if denom > 5.0 else None
        else:
            waist_constriction_ratio = None
    else:
        x0 = y0 = bbox_width = bbox_height = max_row_width = None
        border_contact = False
        waist_constriction_ratio = None

    contours, _ = cv2.findContours(binary.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    component_count = int(cv2.connectedComponents(binary, connectivity=8)[0] - 1)
    perimeter = float(sum(cv2.arcLength(c, True) for c in contours))
    contour_area = float(sum(cv2.contourArea(c) for c in contours))
    hull_area = float(sum(cv2.contourArea(cv2.convexHull(c)) for c in contours))
    circularity = (4.0 * np.pi * contour_area / (perimeter * perimeter)
                   if perimeter > 0 and contour_area > 0 else None)
    solidity = contour_area / hull_area if hull_area > 0 else None
    aspect_ratio = float(bbox_height) / float(bbox_width) if bbox_width and bbox_height else None
    hair_coverage = float(area) / float(height * width) if height * width > 0 else 0.0

    return {
        "area_pixels": area,
        "pixel_area": area,
        "bbox": None if not area else {"x": x0, "y": y0, "width": bbox_width, "height": bbox_height},
        "max_row_width": max_row_width,
        "component_count": component_count,
        "border_contact": border_contact,
        "cropped": border_contact,
        "contour_perimeter": perimeter if perimeter > 0 else None,
        "contour_area": contour_area,
        "circularity": circularity,
        "solidity": solidity,
        "aspect_ratio": round(aspect_ratio, 4) if aspect_ratio is not None else None,
        "hair_coverage": round(hair_coverage, 4),
        "waist_constriction_ratio": round(waist_constriction_ratio, 4) if waist_constriction_ratio is not None else None,
    }


def assess_tied_hair(
    mask: np.ndarray,
    calibrate: bool = False,
    hair_type: Optional[str] = None,
) -> dict[str, Any]:
    """Assess whether hair is tied (ponytail, bun) or freely loose.

    Default calibrate=False maintains backward compatibility with Phase 3 uncalibrated contract.
    Pass calibrate=True or call classify_tied_hair() for calibrated detection.
    """
    features = extract_shape_features(mask)
    if not calibrate or features["pixel_area"] == 0 or features["circularity"] is None:
        return {"tied": None, "confidence": None, "status": "uncalibrated", "features": features}

    circ = features["circularity"]
    sol = features["solidity"] or 0.0
    aspect = features["aspect_ratio"] or 1.0
    cov = features["hair_coverage"]
    waist = features["waist_constriction_ratio"]

    # 1. Ponytail detection: waist constriction below the cranial base
    if waist is not None and waist < 0.65 and aspect > 1.35 and (sol < 0.96 or circ < 0.50):
        return {
            "tied": True,
            "style": "ponytail",
            "confidence": round(min(0.95, 0.70 + (0.65 - waist) * 0.8), 4),
            "status": "calibrated",
            "features": features,
        }

    # 2. Bun / updo detection: highly circular, compact cluster
    # Exclude kinky/afro hair which naturally has high circularity
    if circ > 0.88 and sol > 0.94 and 0.80 <= aspect <= 1.25 and cov < 0.22 and hair_type != "sangat-keriting":
        return {
            "tied": True,
            "style": "bun",
            "confidence": 0.82,
            "status": "calibrated",
            "features": features,
        }

    # 3. Standard loose hair (freely cascading)
    return {
        "tied": False,
        "style": "loose",
        "confidence": 0.90,
        "status": "calibrated",
        "features": features,
    }


def classify_tied_hair(
    mask: np.ndarray,
    hair_type: Optional[str] = None,
) -> dict[str, Any]:
    """Calibrated detection of tied hair (bun, ponytail) vs loose cascading hair."""
    return assess_tied_hair(mask, calibrate=True, hair_type=hair_type)


def detect_tied_hair(mask: np.ndarray, calibrate: bool = False) -> dict[str, Any]:
    """Backward-compatible alias for :func:`assess_tied_hair`."""
    return assess_tied_hair(mask, calibrate=calibrate)


def _geometry_output(path: str) -> Path:
    output = Path(path).resolve()
    if not output.is_relative_to(Path(__file__).resolve().parent):
        raise ValueError("output path must be inside this geometry directory")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract mask geometry and assess tied-hair status.")
    parser.add_argument("--mask", required=True, help="Input mask image")
    parser.add_argument("--out", required=True, help="JSON output path inside this geometry directory")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--uncalibrated", action="store_true", help="Force uncalibrated mode")
    args = parser.parse_args(argv)
    try:
        output = _geometry_output(args.out)
        if output.exists() and not args.overwrite:
            raise ValueError(f"output already exists (use --overwrite): {output}")
        image = cv2.imread(args.mask, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError(f"could not read mask: {args.mask}")
        if image.ndim == 3:
            if image.shape[2] not in (3, 4):
                raise ValueError("mask image must be grayscale, BGR, or BGRA")
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
        result = assess_tied_hair(image, calibrate=not args.uncalibrated)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
