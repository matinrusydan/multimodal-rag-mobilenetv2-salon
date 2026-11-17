"""Phase 3/4: Person Silhouette Segmentation Inference Module.

Provides MobileNetV3-LRASPP ONNX person segmentation to isolate body/garment
silhouettes outside the hair mask (M_person \\ M_hair) for shoulder detection.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DEFAULT_PERSON_ONNX = HERE / "weights" / "person_segmentation_lraspp.onnx"

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class PersonSegmenter:
    """Wrapper around onnxruntime InferenceSession for MobileNetV3-LRASPP person segmentation."""

    def __init__(self, onnx_path: Path = DEFAULT_PERSON_ONNX, input_size: int = 512):
        self.onnx_path = Path(onnx_path)
        self.input_size = input_size
        self._session = None
        self._input_name = None

    @property
    def session(self):
        if self._session is None and self.onnx_path.is_file():
            try:
                import onnxruntime as ort

                self._session = ort.InferenceSession(
                    str(self.onnx_path), providers=["CPUExecutionProvider"]
                )
                self._input_name = self._session.get_inputs()[0].name
            except Exception:
                self._session = None
                self._input_name = None
        return self._session

    def is_available(self) -> bool:
        return self.session is not None

    def predict_mask(self, img_bgr: np.ndarray) -> Optional[np.ndarray]:
        """Predict binary person silhouette mask (uint8 HxW 0 or 255) for BGR image."""
        if not self.is_available() or img_bgr is None or img_bgr.size == 0:
            return None
        h, w = img_bgr.shape[:2]
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(
            rgb, (self.input_size, self.input_size), interpolation=cv2.INTER_LINEAR
        ).astype(np.float32) / 255.0
        norm = (resized - IMAGENET_MEAN) / IMAGENET_STD
        chw = np.transpose(norm, (2, 0, 1))[None, ...].astype(np.float32)

        out = self.session.run(None, {self._input_name: chw})[0][0]
        # PASCAL VOC class 15 is 'person'
        pred_cls = np.argmax(out, axis=0).astype(np.uint8)
        mask_small = (pred_cls == 15).astype(np.uint8) * 255
        return cv2.resize(mask_small, (w, h), interpolation=cv2.INTER_NEAREST)

    def predict_pil(self, img: Image.Image) -> Optional[np.ndarray]:
        """Predict binary person silhouette mask for PIL Image."""
        im_trans = ImageOps.exif_transpose(img).convert("RGB")
        rgb_arr = np.asarray(im_trans)
        img_bgr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
        return self.predict_mask(img_bgr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run person segmentation inference on an image.")
    parser.add_argument("--image", type=Path, required=True, help="Input image path")
    parser.add_argument("--model", type=Path, default=DEFAULT_PERSON_ONNX, help="Path to person_segmentation_lraspp.onnx")
    parser.add_argument("--mask-out", type=Path, default=None, help="Optional output path for binary mask PNG")
    args = parser.parse_args(argv)

    with Image.open(args.image) as im:
        rgb = np.asarray(ImageOps.exif_transpose(im).convert("RGB"))
        img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    segmenter = PersonSegmenter(onnx_path=args.model)
    mask = segmenter.predict_mask(img_bgr)

    if mask is None:
        print("Person segmentation failed or model unavailable.")
        return 1

    coverage = float((mask > 0).mean())
    print(f"Person mask computed: shape={mask.shape}, coverage={coverage:.4f}")

    if args.mask_out:
        args.mask_out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.mask_out), mask)
        print(f"Saved mask to {args.mask_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
