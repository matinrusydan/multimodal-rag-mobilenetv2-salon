"""Conservative binary-mask cleanup helpers and CLI."""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def cleanup_mask(
    mask: np.ndarray,
    *,
    threshold: float = 0.5,
    opening_kernel: int = 0,
    closing_kernel: int = 0,
    fill_holes: bool = False,
    largest_component: bool = False,
) -> np.ndarray:
    """Threshold and optionally clean a 2D mask, returning uint8 values 0/255.

    Integer inputs must contain only binary 0/255 values. Floating inputs are
    probabilities in [0, 1]. The input is never modified.
    """
    if not isinstance(mask, np.ndarray) or mask.ndim != 2:
        raise ValueError("mask must be a two-dimensional numpy array")
    if mask.size == 0:
        raise ValueError("mask must not be empty")
    if not np.issubdtype(mask.dtype, np.number) or np.issubdtype(mask.dtype, np.complexfloating):
        raise ValueError("mask must contain numeric binary values or probabilities")
    if not np.isfinite(mask).all():
        raise ValueError("mask values must be finite")
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be finite and within [0, 1]")
    for name, kernel in (("opening_kernel", opening_kernel), ("closing_kernel", closing_kernel)):
        if isinstance(kernel, bool) or not isinstance(kernel, (int, np.integer)) or kernel < 0 or (kernel != 0 and kernel % 2 == 0):
            raise ValueError(f"{name} must be zero or an odd positive integer")

    if np.issubdtype(mask.dtype, np.floating):
        if np.any(mask < 0) or np.any(mask > 1):
            raise ValueError("float probability mask values must be within [0, 1]")
        result = (mask >= threshold).astype(np.uint8) * 255
    else:
        if np.any((mask != 0) & (mask != 255)):
            raise ValueError("integer mask values must be binary 0/255")
        result = (mask == 255).astype(np.uint8) * 255

    for size, operation in ((opening_kernel, cv2.MORPH_OPEN), (closing_kernel, cv2.MORPH_CLOSE)):
        if size:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(size), int(size)))
            result = cv2.morphologyEx(result, operation, kernel)
    if fill_holes:
        padded = np.pad(result, 1, mode="constant", constant_values=0)
        flood = padded.copy()
        flood_mask = np.zeros((padded.shape[0] + 2, padded.shape[1] + 2), dtype=np.uint8)
        cv2.floodFill(flood, flood_mask, (0, 0), 255)
        holes = cv2.bitwise_not(flood)[1:-1, 1:-1]
        result = cv2.bitwise_or(result, holes)
    if largest_component:
        count, labels, stats, _ = cv2.connectedComponentsWithStats((result > 0).astype(np.uint8), connectivity=8)
        if count > 1:
            chosen = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            result = (labels == chosen).astype(np.uint8) * 255
    return np.ascontiguousarray(result, dtype=np.uint8)


def _geometry_output(path: str) -> Path:
    output = Path(path).resolve()
    root = Path(__file__).resolve().parent
    if not output.is_relative_to(root):
        raise ValueError("output path must be inside the geometry directory")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Threshold and conservatively clean a binary mask.")
    parser.add_argument("--mask", required=True, help="Input mask image")
    parser.add_argument("--out", required=True, help="Output image path inside this geometry directory")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--opening-kernel", type=int, default=0, help="Odd kernel size; 0 disables")
    parser.add_argument("--closing-kernel", type=int, default=0, help="Odd kernel size; 0 disables")
    parser.add_argument("--fill-holes", action="store_true")
    parser.add_argument("--largest-component", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--seed", type=int, default=42, help="Accepted for reproducibility; operation is deterministic and uses no randomness")
    args = parser.parse_args(argv)
    try:
        output = _geometry_output(args.out)
        if output.exists() and not args.overwrite:
            raise ValueError(f"output already exists (use --overwrite): {output}")
        raw = cv2.imread(args.mask, cv2.IMREAD_UNCHANGED)
        if raw is None:
            raise ValueError(f"could not read mask: {args.mask}")
        cleaned = cleanup_mask(raw, threshold=args.threshold, opening_kernel=args.opening_kernel,
                               closing_kernel=args.closing_kernel, fill_holes=args.fill_holes,
                               largest_component=args.largest_component)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(output), cleaned):
            raise ValueError(f"could not write output: {output}")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
