"""Phase 3/4: Geometric Hair Length Measurement.

Provides relative, dimensionless hair length estimation invariant to image scale:
1. Pose-guided mode: uses MediaPipe shoulder landmarks when available and valid.
2. Pose-free silhouette mode: estimates cranial reference and shoulder inflection
   using anthropometric head-unit canons (Domljan 2024, Burton 2013) and width profiles.

Maps relative length ratios to canonical classes:
- 'pendek': <= 0.75 shoulder ratio or < 1.0 head units
- 'pendek-menengah': 0.75 - 1.15 shoulder ratio (around neck to shoulder level)
- 'menengah': 1.15 - 1.65 shoulder ratio (shoulder to mid-back)
- 'panjang': > 1.65 shoulder ratio (> 2.1 head units, past mid-back)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from person_segment_infer import PersonSegmenter

HAIR_LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]

# Anthropometric constants (Domljan et al., 2024; Farkas, 1994)
CRANIAL_HEIGHT_TO_WIDTH_RATIO = 1.30  # H_head ≈ 1.30 * W_cranial
VERTEX_TO_SHOULDER_HEAD_UNITS = 1.33  # Shoulder level ≈ 1.33 * H_head from vertex


def filter_hair_mask_with_person(
    hair_mask: np.ndarray,
    person_mask: Optional[np.ndarray],
) -> np.ndarray:
    """Filter out spurious background hair false positives (e.g. building facades) outside person silhouette."""
    if person_mask is None or hair_mask is None:
        return hair_mask
    h, w = hair_mask.shape[:2]
    if person_mask.sum() < 0.05 * h * w:
        return hair_mask

    num, labels, stats, _ = cv2.connectedComponentsWithStats((hair_mask > 0).astype(np.uint8))
    if num <= 2:
        return hair_mask

    largest_idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    cleaned = np.zeros_like(hair_mask)
    for i in range(1, num):
        comp = (labels == i)
        overlap = (comp & (person_mask > 0)).sum()
        # Keep if overlaps person mask by at least 5% or is the largest component
        if overlap > 0.05 * stats[i, 4] or i == largest_idx:
            cleaned[comp] = 255

    return cleaned


def estimate_cranial_reference(mask: np.ndarray) -> dict[str, Any]:
    """Estimate head top, hair bottom, and cranial reference dimensions from hair mask."""
    if not isinstance(mask, np.ndarray) or mask.ndim != 2:
        raise ValueError("mask must be a 2D numpy array")
    if mask.size == 0:
        raise ValueError("mask must not be empty")
    if not np.isfinite(mask).all():
        raise ValueError("mask values must be finite")

    binary = (mask > 0).astype(np.uint8)
    ys, xs = np.nonzero(binary)
    if len(ys) == 0:
        return {
            "is_empty": True,
            "y_head_top": None,
            "y_hair_end": None,
            "hair_span_pixels": 0,
            "cranial_width": None,
            "estimated_head_height": None,
        }

    y_head_top = int(ys.min())
    y_hair_end = int(ys.max())
    hair_span = y_hair_end - y_head_top + 1

    # Extract row width profile across vertical extent
    row_widths = binary[y_head_top : y_hair_end + 1].sum(axis=1)

    # Estimate cranial width from upper dome (top 25% of image or top band of hair)
    img_h = mask.shape[0]
    top_band_len = min(len(row_widths), max(15, int(0.25 * img_h)))
    start_idx = max(1, int(0.05 * top_band_len))
    upper_widths = row_widths[start_idx:top_band_len]

    if len(upper_widths) > 0 and float(np.max(upper_widths)) > 0:
        cranial_width = float(np.percentile(upper_widths, 75))
    else:
        cranial_width = float(np.max(row_widths)) if len(row_widths) > 0 else 0.0

    # Ensure positive cranial width for degenerate single-pixel cases
    cranial_width = max(1.0, cranial_width)
    estimated_head_height = float(CRANIAL_HEIGHT_TO_WIDTH_RATIO * cranial_width)

    return {
        "is_empty": False,
        "y_head_top": y_head_top,
        "y_hair_end": y_hair_end,
        "hair_span_pixels": hair_span,
        "cranial_width": round(cranial_width, 2),
        "estimated_head_height": round(estimated_head_height, 2),
    }


def detect_clothing_and_body_shoulder(
    img_bgr: np.ndarray,
    hair_mask: np.ndarray,
    cranial_ref: dict[str, Any],
    person_mask: Optional[np.ndarray] = None,
) -> Tuple[Optional[float], Optional[str]]:
    """Detect shoulder anchor line using garment color and person body contour outside hair."""
    h, w = img_bgr.shape[:2]
    y_top = cranial_ref["y_head_top"]
    h_head = cranial_ref["estimated_head_height"]

    xs_h = np.where(hair_mask)[1]
    x_mid = int(np.median(xs_h)) if len(xs_h) > 0 else w // 2
    min_flank_px = max(8, int(0.035 * w))

    # Anatomical neck-to-shoulder vertical search window
    y_s = max(y_top + 10, int(y_top + 0.85 * h_head))
    y_e = min(h - 1, int(y_top + 1.65 * h_head))
    if y_e <= y_s:
        return None, None

    # Slight dilation on hair mask to avoid hairline fuzz/flyaway strands
    hair_dilated = cv2.dilate((hair_mask > 0).astype(np.uint8), np.ones((5, 5), np.uint8), iterations=1) > 0

    # 1. Color-based clothing emergence (against uniform studio background using MAD)
    y_garment_color = None
    ch, cw = max(15, int(0.08 * h)), max(20, int(0.12 * w))
    c_left = img_bgr[:ch, :cw]
    c_right = img_bgr[:ch, -cw:]
    med_l = np.median(c_left.reshape(-1, 3), axis=0)
    med_r = np.median(c_right.reshape(-1, 3), axis=0)
    mad_l = float(np.median(np.abs(c_left.astype(float) - med_l)))
    mad_r = float(np.median(np.abs(c_right.astype(float) - med_r)))

    bg_med = None
    bg_mad = 0.0
    if mad_l < 12 and mad_r < 12 and np.linalg.norm(med_l - med_r) < 35:
        bg_med = (med_l + med_r) / 2.0
        bg_mad = max(mad_l, mad_r)

    if bg_med is not None:
        dist_bg = np.linalg.norm(img_bgr.astype(float) - bg_med, axis=2)
        bg_thresh = max(20.0, min(42.0, bg_mad * 4.5))
        fg_non_hair = (dist_bg > bg_thresh) & (~hair_dilated)
        if person_mask is not None and person_mask.sum() > 0.05 * h * w:
            person_dil = cv2.dilate((person_mask > 0).astype(np.uint8), np.ones((15, 15), np.uint8), iterations=1) > 0
            fg_non_hair = fg_non_hair & person_dil

        left_fg = fg_non_hair[:, :x_mid].sum(axis=1)
        right_fg = fg_non_hair[:, x_mid:].sum(axis=1)
        rows_both = [y for y in range(y_s, y_e) if left_fg[y] >= min_flank_px and right_fg[y] >= min_flank_px]
        if rows_both:
            y_garment_color = float(rows_both[0])

    # 2. Person segmentation minus hair mask (body/torso silhouette)
    y_person_seg = None
    if person_mask is not None and person_mask.sum() > 0.05 * h * w:
        body_only = (person_mask > 0) & (~hair_dilated)
        left_b = body_only[:, :x_mid].sum(axis=1)
        right_b = body_only[:, x_mid:].sum(axis=1)

        p_widths = person_mask.sum(axis=1).astype(float)
        if y_e > y_s + 10:
            k = max(5, int(0.03 * h))
            p_sm = np.convolve(p_widths, np.ones(k) / k, mode="same")
            dp = np.gradient(p_sm)
            y_slope = float(y_s + np.argmax(dp[y_s:y_e]))
        else:
            y_slope = None

        flank_rows = [y for y in range(y_s, y_e) if left_b[y] >= min_flank_px and right_b[y] >= min_flank_px]
        y_flank = float(flank_rows[0]) if flank_rows else None

        if y_flank is not None and y_slope is not None:
            y_person_seg = 0.60 * y_flank + 0.40 * y_slope
        elif y_flank is not None:
            y_person_seg = y_flank
        elif y_slope is not None:
            y_person_seg = y_slope

    if y_garment_color is not None and y_person_seg is not None:
        return 0.55 * y_garment_color + 0.45 * y_person_seg, "clothing_and_body"
    elif y_garment_color is not None:
        return y_garment_color, "clothing_color"
    elif y_person_seg is not None:
        return y_person_seg, "body_silhouette"

    return None, None


def estimate_shoulder_anchor(
    mask: np.ndarray,
    cranial_ref: dict[str, Any],
    pose_landmarks: Optional[dict[str, Any]] = None,
    image_bgr: Optional[np.ndarray] = None,
    person_segmenter: Optional[PersonSegmenter] = None,
    person_mask: Optional[np.ndarray] = None,
) -> Tuple[float, str]:
    """Determine vertical shoulder line (y_shoulder) via pose, clothing/body, or silhouette inflection."""
    if cranial_ref["is_empty"]:
        raise ValueError("Cannot estimate shoulder anchor on an empty mask")

    y_top = cranial_ref["y_head_top"]
    h_head = cranial_ref["estimated_head_height"]
    img_h, img_w = mask.shape

    # 1. Check if MediaPipe pose landmarks provide valid shoulders
    if pose_landmarks:
        sh_L = pose_landmarks.get("shoulder_L")
        sh_R = pose_landmarks.get("shoulder_R")
        if sh_L and sh_R:
            v_min = 0.5
            if sh_L.get("visibility", 0) >= v_min and sh_R.get("visibility", 0) >= v_min:
                w_sh = abs(sh_L.get("x", 0) - sh_R.get("x", 0)) * img_w
                # Check realistic anatomical width (> 25% image width)
                if w_sh >= 0.25 * img_w:
                    y_sh = float(sh_L.get("y", 0) + sh_R.get("y", 0)) / 2.0 * img_h
                    if y_sh > y_top:
                        return round(y_sh, 2), "pose_guided"

    # 2. Clothing and body silhouette calibration
    if image_bgr is not None and image_bgr.shape[:2] == (img_h, img_w):
        if person_mask is None:
            if person_segmenter is not None:
                person_mask = person_segmenter.predict_mask(image_bgr)
            elif PersonSegmenter().is_available():
                person_mask = PersonSegmenter().predict_mask(image_bgr)

        y_calibrated, method = detect_clothing_and_body_shoulder(
            img_bgr=image_bgr,
            hair_mask=mask,
            cranial_ref=cranial_ref,
            person_mask=person_mask,
        )
        if y_calibrated is not None and method is not None:
            return round(float(y_calibrated), 2), method

    # 3. Pose-free silhouette inflection analysis
    # Canonical default from Domljan (2024) head-unit canon
    y_sh_canonical = y_top + VERTEX_TO_SHOULDER_HEAD_UNITS * h_head

    # Check mask width expansion around expected shoulder zone
    binary = (mask > 0).astype(np.uint8)
    row_widths = binary.sum(axis=1)

    search_y_start = max(y_top + 1, int(y_top + 1.05 * h_head))
    search_y_end = min(img_h - 1, int(y_top + 1.65 * h_head))

    if search_y_end > search_y_start and search_y_end < len(row_widths):
        window_widths = row_widths[search_y_start : search_y_end + 1]
        if len(window_widths) >= 5:
            # Find maximum lateral expansion in shoulder window
            max_idx = int(np.argmax(window_widths))
            y_inflection = float(search_y_start + max_idx)
            # Weighted average between silhouette expansion and anthropometric canon
            y_sh_refined = 0.60 * y_inflection + 0.40 * y_sh_canonical
            return round(float(y_sh_refined), 2), "pose_free_silhouette"

    return round(float(y_sh_canonical), 2), "pose_free_silhouette"


def classify_length_from_ratios(
    relative_shoulder_ratio: float,
    head_units: float,
) -> Tuple[str, float]:
    """Map continuous relative length ratios to canonical 4 hair length classes."""
    # Canonical thresholds:
    # 'pendek': ends above chin/high neck (head_units < 1.0 or r_sh <= 0.75)
    # 'pendek-menengah': neck to shoulder (1.0 <= head_units < 1.4 or 0.75 < r_sh <= 1.15)
    # 'menengah': past shoulder to mid-back (1.4 <= head_units < 2.1 or 1.15 < r_sh <= 1.65)
    # 'panjang': past mid-back (head_units >= 2.1 or r_sh > 1.65)
    r = relative_shoulder_ratio
    u = head_units

    if r <= 0.75 or u < 1.0:
        cls_name = "pendek"
        margin = max(0.0, min(0.75 - r, 1.0 - u))
    elif r <= 1.15 or u < 1.40:
        cls_name = "pendek-menengah"
        margin = max(0.0, min(max(r - 0.75, u - 1.0), min(1.15 - r, 1.40 - u)))
    elif r <= 1.65 or u < 2.10:
        cls_name = "menengah"
        margin = max(0.0, min(max(r - 1.15, u - 1.40), max(1.65 - r, 2.10 - u)))
    else:
        cls_name = "panjang"
        margin = max(0.0, max(r - 1.65, u - 2.10))

    # Confidence score scaled by distance from class boundary [0.55 .. 0.98]
    conf = min(0.98, max(0.55, 0.75 + float(margin) * 0.35))
    return cls_name, round(conf, 4)


def measure_hair_length(
    mask: np.ndarray,
    pose_landmarks: Optional[dict[str, Any]] = None,
    image_bgr: Optional[np.ndarray] = None,
    person_segmenter: Optional[PersonSegmenter] = None,
    person_mask: Optional[np.ndarray] = None,
) -> dict[str, Any]:
    """Measure hair length from binary mask using pose, clothing/body, or silhouette geometry."""
    if image_bgr is not None and mask is not None:
        if person_mask is None:
            if person_segmenter is not None:
                person_mask = person_segmenter.predict_mask(image_bgr)
            elif PersonSegmenter().is_available():
                person_mask = PersonSegmenter().predict_mask(image_bgr)
        if person_mask is not None:
            mask = filter_hair_mask_with_person(mask, person_mask)

    cranial = estimate_cranial_reference(mask)
    if cranial["is_empty"]:
        return {
            "status": "empty_mask",
            "predicted_class": None,
            "confidence": None,
            "relative_shoulder_ratio": None,
            "head_units": None,
            "method": None,
            "keypoints": cranial,
        }

    y_top = cranial["y_head_top"]
    y_end = cranial["y_hair_end"]
    h_span = cranial["hair_span_pixels"]
    h_head = cranial["estimated_head_height"]

    y_shoulder, method = estimate_shoulder_anchor(
        mask=mask,
        cranial_ref=cranial,
        pose_landmarks=pose_landmarks,
        image_bgr=image_bgr,
        person_segmenter=person_segmenter,
        person_mask=person_mask,
    )

    dist_to_shoulder = max(1.0, y_shoulder - y_top)
    r_shoulder = float(h_span) / dist_to_shoulder
    head_units = float(h_span) / max(1.0, h_head)

    cls_name, conf = classify_length_from_ratios(r_shoulder, head_units)

    return {
        "status": "ok",
        "predicted_class": cls_name,
        "confidence": conf,
        "relative_shoulder_ratio": round(r_shoulder, 4),
        "head_units": round(head_units, 4),
        "method": method,
        "keypoints": {
            "y_head_top": y_top,
            "y_hair_end": y_end,
            "y_shoulder": y_shoulder,
            "cranial_width": cranial["cranial_width"],
            "head_height_estimate": h_head,
            "hair_span_pixels": h_span,
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
    parser.add_argument("--image", type=Path, default=None, help="Optional source image path for clothing/body calibration")
    parser.add_argument("--pose-json", type=Path, default=None, help="Optional pose landmarks JSON")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path inside geometry/")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file")
    args = parser.parse_args(argv)

    mask_img = cv2.imread(str(args.mask), cv2.IMREAD_GRAYSCALE)
    if mask_img is None:
        parser.error(f"Could not read mask image: {args.mask}")

    img_bgr = None
    if args.image and args.image.is_file():
        try:
            with Image.open(args.image) as im:
                rgb = np.asarray(ImageOps.exif_transpose(im).convert("RGB"))
                img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            img_bgr = None

    pose_lm = None
    if args.pose_json and args.pose_json.is_file():
        try:
            pose_lm = json.loads(args.pose_json.read_text(encoding="utf-8")).get("landmarks")
        except Exception:
            pose_lm = None

    result = measure_hair_length(mask_img, pose_landmarks=pose_lm, image_bgr=img_bgr)
    output_text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"

    if args.out:
        out_path = _geometry_output(str(args.out))
        if out_path.exists() and not args.overwrite:
            parser.error(f"Output file already exists: {out_path} (use --overwrite)")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"Saved length measurement to {out_path}")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
