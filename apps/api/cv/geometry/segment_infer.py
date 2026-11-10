"""Phase 2: Standalone ONNX Hair Segmentation Inference CLI & Module.

Runs inference using the exported `hair_segmentation.onnx` model on any input
image (regardless of aspect ratio/resolution), resizes to model input (256x256),
applies ImageNet normalization, produces a probability map and binary mask
projected back to the original image dimensions, and optionally saves an
overlay or binary mask PNG.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DEFAULT_ONNX = HERE / "weights" / "hair_segmentation.onnx"

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess_for_segmentation(
    img: Image.Image, img_size: int = 256
) -> Tuple[np.ndarray, Tuple[int, int]]:
    """Convert PIL Image -> (NCHW float32 [1,3,H,W], original (width, height))."""
    im = ImageOps.exif_transpose(img).convert("RGB")
    orig_size = im.size  # (W, H)
    resized = im.resize((img_size, img_size), Image.Resampling.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32) / 255.0
    norm = (arr - IMAGENET_MEAN) / IMAGENET_STD
    chw = np.transpose(norm, (2, 0, 1))[None, ...]
    return np.ascontiguousarray(chw, dtype=np.float32), orig_size


def sigmoid(x: np.ndarray) -> np.ndarray:
    x_clip = np.clip(x, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-x_clip))


class HairSegmenter:
    """Wrapper around onnxruntime InferenceSession for hair segmentation."""

    def __init__(self, onnx_path: Path = DEFAULT_ONNX, img_size: int = 256):
        import onnxruntime as ort

        self.onnx_path = Path(onnx_path)
        if not self.onnx_path.exists():
            raise FileNotFoundError(f"ONNX segmentation model not found: {self.onnx_path}")
        self.img_size = img_size
        self.session = ort.InferenceSession(
            str(self.onnx_path), providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name

    def predict_pil(
        self, img: Image.Image, threshold: float = 0.5
    ) -> dict:
        """Predict binary mask and hair coverage stats for a PIL Image."""
        t0 = time.perf_counter()
        tensor, (orig_w, orig_h) = preprocess_for_segmentation(img, self.img_size)
        logits = self.session.run(None, {self.input_name: tensor})[0]
        probs_small = sigmoid(logits[0, 0])  # (img_size, img_size)

        # Resize probability map smoothly back to original image dimensions
        prob_pil = Image.fromarray((probs_small * 255.0).astype(np.uint8), mode="L")
        prob_orig_pil = prob_pil.resize((orig_w, orig_h), Image.Resampling.BILINEAR)
        prob_orig = np.asarray(prob_orig_pil, dtype=np.float32) / 255.0
        mask_bin = (prob_orig >= threshold).astype(np.uint8) * 255

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        hair_ratio = float((mask_bin > 127).mean())

        return {
            "mask": mask_bin,          # uint8 (H, W) 0 or 255
            "prob_map": prob_orig,     # float32 (H, W) 0..1
            "hair_coverage": round(hair_ratio, 4),
            "orig_size": [orig_w, orig_h],
            "latency_ms": round(elapsed_ms, 2),
        }

    def predict_file(self, image_path: Path, threshold: float = 0.5) -> dict:
        """Predict binary mask from an image file path."""
        with Image.open(image_path) as im:
            return self.predict_pil(im, threshold=threshold)


def save_mask_and_overlay(
    image_path: Path,
    mask_bin: np.ndarray,
    mask_out: Optional[Path] = None,
    overlay_out: Optional[Path] = None,
) -> None:
    """Save binary PNG mask and/or visual overlay."""
    if mask_out:
        mask_out.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(mask_bin, mode="L").save(mask_out)

    if overlay_out:
        overlay_out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(image_path) as im_raw:
            im = ImageOps.exif_transpose(im_raw).convert("RGB")
            im_arr = np.asarray(im, dtype=np.float32)
            alpha = (mask_bin > 127).astype(np.float32)[:, :, None]
            green = np.array([34.0, 197.0, 94.0], dtype=np.float32)
            blended = (im_arr * (1.0 - 0.45 * alpha) + green * (0.45 * alpha)).clip(0, 255).astype(np.uint8)
            Image.fromarray(blended).save(overlay_out, quality=92)


def main():
    parser = argparse.ArgumentParser(
        description="Run Phase 2 ONNX hair segmentation inference on an image."
    )
    parser.add_argument("--image", type=Path, required=True, help="Input image path")
    parser.add_argument("--model", type=Path, default=DEFAULT_ONNX, help="Path to hair_segmentation.onnx")
    parser.add_argument("--img-size", type=int, default=256, help="Model input resolution (default: 256)")
    parser.add_argument("--threshold", type=float, default=0.5, help="Binary mask threshold (default: 0.5)")
    parser.add_argument("--mask-out", type=Path, default=None, help="Optional output path for binary mask PNG")
    parser.add_argument("--overlay-out", type=Path, default=None, help="Optional output path for overlay image")
    args = parser.parse_args()

    segmenter = HairSegmenter(onnx_path=args.model, img_size=args.img_size)
    res = segmenter.predict_file(args.image, threshold=args.threshold)

    save_mask_and_overlay(
        image_path=args.image,
        mask_bin=res["mask"],
        mask_out=args.mask_out,
        overlay_out=args.overlay_out,
    )

    summary = {
        "image": str(args.image),
        "orig_size": res["orig_size"],
        "hair_coverage": res["hair_coverage"],
        "latency_ms": res["latency_ms"],
        "mask_saved": str(args.mask_out) if args.mask_out else None,
        "overlay_saved": str(args.overlay_out) if args.overlay_out else None,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
