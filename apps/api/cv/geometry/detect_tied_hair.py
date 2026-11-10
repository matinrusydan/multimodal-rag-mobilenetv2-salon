"""Extract descriptive mask geometry without making a tied-hair decision."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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
    else:
        x0 = y0 = bbox_width = bbox_height = max_row_width = None
        border_contact = False

    contours, _ = cv2.findContours(binary.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    component_count = int(cv2.connectedComponents(binary, connectivity=8)[0] - 1)
    perimeter = float(sum(cv2.arcLength(c, True) for c in contours))
    contour_area = float(sum(cv2.contourArea(c) for c in contours))
    hull_area = float(sum(cv2.contourArea(cv2.convexHull(c)) for c in contours))
    circularity = (4.0 * np.pi * contour_area / (perimeter * perimeter)
                   if perimeter > 0 and contour_area > 0 else None)
    solidity = contour_area / hull_area if hull_area > 0 else None
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
    }


def assess_tied_hair(mask: np.ndarray) -> dict[str, Any]:
    """Return features with a deliberately uncalibrated, non-classifying result."""
    return {"tied": None, "confidence": None, "status": "uncalibrated", "features": extract_shape_features(mask)}


def detect_tied_hair(mask: np.ndarray) -> dict[str, Any]:
    """Backward-compatible alias for :func:`assess_tied_hair`."""
    return assess_tied_hair(mask)


def _geometry_output(path: str) -> Path:
    output = Path(path).resolve()
    if not output.is_relative_to(Path(__file__).resolve().parent):
        raise ValueError("output path must be inside this geometry directory")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract mask geometry; tied-hair detection is uncalibrated.")
    parser.add_argument("--mask", required=True, help="Input mask image")
    parser.add_argument("--out", required=True, help="JSON output path inside this geometry directory")
    parser.add_argument("--overwrite", action="store_true")
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
        result = assess_tied_hair(image)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
