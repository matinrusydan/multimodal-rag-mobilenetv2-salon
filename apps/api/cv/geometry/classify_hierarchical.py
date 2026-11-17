"""Phase 4: Hierarchical Hair Classification Pipeline (Inference & CLI).

Combines Stage 1 (Hair Type ONNX classifier) and Stage 2 (Hair Segmentation ONNX
+ non-pose mask geometry). Respects Phase 0 gate status: pose-dependent length
and volume measurements are cleanly marked unavailable (`blocked_phase0_gate`)
without discarding valid Stage 1 hair type and Stage 2 segmentation outputs.
Tied-hair assessment remains uncalibrated (`tied: null`).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from detect_tied_hair import assess_tied_hair, classify_tied_hair
from hair_type_model import HAIR_TYPE_CLASSES
from measure_length import HAIR_LENGTH_CLASSES, filter_hair_mask_with_person, measure_hair_length
from measure_volume import HAIR_VOLUME_CLASSES, measure_hair_volume
from person_segment_infer import DEFAULT_PERSON_ONNX, PersonSegmenter
from segment_infer import HairSegmenter, save_mask_and_overlay
from threshold_binary import cleanup_mask

DEFAULT_TYPE_ONNX = HERE / "weights" / "hair_type.onnx"
DEFAULT_SEG_ONNX = HERE / "weights" / "hair_segmentation.onnx"

THREE_CLASS_LABELS = ["lurus", "bergelombang", "keriting"]
FOUR_CLASS_LABELS = HAIR_TYPE_CLASSES

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess_for_hair_type(
    img: Image.Image,
    resize_side: int = 256,
    crop_size: int = 224,
) -> np.ndarray:
    """Keep-aspect resize (short side=256) -> center-crop 224 -> NCHW float32."""
    im = ImageOps.exif_transpose(img).convert("RGB")
    w, h = im.size
    scale = resize_side / min(h, w)
    rw = max(crop_size, round(w * scale))
    rh = max(crop_size, round(h * scale))
    resized = im.resize((rw, rh), Image.Resampling.BILINEAR)
    left = (rw - crop_size) // 2
    top = (rh - crop_size) // 2
    cropped = resized.crop((left, top, left + crop_size, top + crop_size))
    arr = np.asarray(cropped, dtype=np.float32) / 255.0
    norm = (arr - IMAGENET_MEAN) / IMAGENET_STD
    chw = np.transpose(norm, (2, 0, 1))[None, ...]
    return np.ascontiguousarray(chw, dtype=np.float32)


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exps = np.exp(shifted)
    return exps / np.sum(exps)


class HairTypeClassifier:
    """Wrapper around onnxruntime InferenceSession for Stage 1 Hair Type.

    Supports both 4-class (default) and 3-class (champion merged) models dynamically.
    """

    def __init__(self, onnx_path: Path = DEFAULT_TYPE_ONNX):
        import onnxruntime as ort

        self.onnx_path = Path(onnx_path)
        if not self.onnx_path.exists():
            raise FileNotFoundError(f"ONNX hair type model not found: {self.onnx_path}")
        self.session = ort.InferenceSession(
            str(self.onnx_path), providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name

        out_shape = self.session.get_outputs()[0].shape
        last_dim = out_shape[-1] if (out_shape and isinstance(out_shape[-1], int)) else None
        if last_dim == 3:
            self.classes = list(THREE_CLASS_LABELS)
        elif last_dim == 4:
            self.classes = list(FOUR_CLASS_LABELS)
        else:
            self.classes = list(FOUR_CLASS_LABELS)

    def predict_pil(self, img: Image.Image) -> dict[str, Any]:
        t0 = time.perf_counter()
        tensor = preprocess_for_hair_type(img)
        logits = self.session.run(None, {self.input_name: tensor})[0][0]
        probs = softmax(np.asarray(logits, dtype=np.float32))
        idx = int(np.argmax(probs))
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        classes = self.classes
        if len(classes) != len(probs):
            if len(probs) == 3:
                classes = THREE_CLASS_LABELS
            elif len(probs) == 4:
                classes = FOUR_CLASS_LABELS
            else:
                classes = FOUR_CLASS_LABELS[:len(probs)]

        return {
            "predicted_class": classes[idx],
            "confidence": round(float(probs[idx]), 4),
            "probabilities": {
                cls: round(float(probs[i]), 4)
                for i, cls in enumerate(classes)
            },
            "latency_ms": round(elapsed_ms, 2),
        }


def required_attributes_for_type(hair_type: str) -> list[str]:
    """Determine conditional Stage 2 attributes per roadmap section 10.1."""
    if hair_type in ("lurus", "bergelombang"):
        return ["length"]
    if hair_type == "keriting":
        return ["length", "volume"]
    if hair_type == "sangat-keriting":
        return ["volume"]
    raise ValueError(f"Unsupported hair type: {hair_type}")


class HierarchicalHairPipeline:
    """Hierarchical inference combining Stage 1 hair type and Stage 2 mask geometry."""

    def __init__(
        self,
        type_onnx: Path = DEFAULT_TYPE_ONNX,
        seg_onnx: Path = DEFAULT_SEG_ONNX,
        person_onnx: Path = DEFAULT_PERSON_ONNX,
    ):
        self.type_classifier = HairTypeClassifier(type_onnx)
        self.segmenter = HairSegmenter(seg_onnx)
        self.person_segmenter = PersonSegmenter(person_onnx)

    def predict_pil(
        self,
        img: Image.Image,
        seg_threshold: float = 0.5,
        enable_geometry: bool = True,
        pose_landmarks: Optional[dict[str, Any]] = None,
    ) -> Tuple[dict[str, Any], np.ndarray]:
        t_start = time.perf_counter()
        im_trans = ImageOps.exif_transpose(img).convert("RGB")
        rgb_arr = np.asarray(im_trans)
        img_bgr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)

        type_res = self.type_classifier.predict_pil(img)
        seg_res = self.segmenter.predict_pil(img, threshold=seg_threshold)

        cleaned_mask = cleanup_mask(seg_res["mask"])
        target_attrs = required_attributes_for_type(type_res["predicted_class"])

        if enable_geometry:
            person_mask = (
                self.person_segmenter.predict_mask(img_bgr)
                if self.person_segmenter is not None and self.person_segmenter.is_available()
                else None
            )
            cleaned_mask = filter_hair_mask_with_person(cleaned_mask, person_mask)

            shape_assessment = classify_tied_hair(
                cleaned_mask, hair_type=type_res["predicted_class"]
            )
            if "length" in target_attrs:
                length_res = measure_hair_length(
                    cleaned_mask,
                    pose_landmarks=pose_landmarks,
                    image_bgr=img_bgr,
                    person_segmenter=self.person_segmenter,
                    person_mask=person_mask,
                )
                length_dict = {"required": True, **length_res}
            else:
                length_dict = {"required": False, "status": "not_required", "value": None}

            if "volume" in target_attrs:
                volume_res = measure_hair_volume(cleaned_mask)
                volume_dict = {"required": True, **volume_res}
            else:
                volume_dict = {"required": False, "status": "not_required", "value": None}

            note = (
                "Geometric attributes unblocked: estimated via anthropometric head-unit "
                "canon and silhouette inflection without rigid pose dependency."
            )
        else:
            shape_assessment = assess_tied_hair(cleaned_mask, calibrate=False)
            length_dict = {
                "required": "length" in target_attrs,
                "status": "blocked_phase0_gate",
                "value": None,
            }
            volume_dict = {
                "required": "volume" in target_attrs,
                "status": "reference_not_validated",
                "value": None,
            }
            note = (
                "Pose-dependent geometry deferred: Phase 0 gate not met and "
                "head-unit references unvalidated."
            )

        total_ms = (time.perf_counter() - t_start) * 1000.0
        hair_cov = round(
            float((cleaned_mask > 0).sum()) / max(1, (cleaned_mask.shape[0] * cleaned_mask.shape[1])),
            4,
        )

        result = {
            "decision": "ok",
            "stage1_hair_type": type_res,
            "stage2_segmentation": {
                "orig_size": seg_res["orig_size"],
                "hair_coverage": hair_cov,
                "latency_ms": seg_res["latency_ms"],
            },
            "tied_hair_assessment": shape_assessment,
            "stage2_conditional_attributes": {
                "target_attributes": target_attrs,
                "length": length_dict,
                "volume": volume_dict,
                "note": note,
            },
            "total_latency_ms": round(total_ms, 2),
        }
        return result, cleaned_mask

    def predict_file(
        self,
        image_path: Path,
        seg_threshold: float = 0.5,
        enable_geometry: bool = True,
        pose_landmarks: Optional[dict[str, Any]] = None,
    ) -> Tuple[dict[str, Any], np.ndarray]:
        with Image.open(image_path) as im:
            result, mask = self.predict_pil(
                im,
                seg_threshold=seg_threshold,
                enable_geometry=enable_geometry,
                pose_landmarks=pose_landmarks,
            )
        result["image"] = str(image_path)
        return result, mask


def _geometry_output(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(HERE):
        raise ValueError("Output path must remain inside apps/api/cv/geometry/")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Phase 4 hierarchical hair classification pipeline."
    )
    parser.add_argument("--image", type=Path, required=True, help="Input image path")
    parser.add_argument(
        "--type-model",
        type=Path,
        default=DEFAULT_TYPE_ONNX,
        help="Path to hair_type.onnx",
    )
    parser.add_argument(
        "--seg-model",
        type=Path,
        default=DEFAULT_SEG_ONNX,
        help="Path to hair_segmentation.onnx",
    )
    parser.add_argument(
        "--person-model",
        type=Path,
        default=DEFAULT_PERSON_ONNX,
        help="Path to person_segmentation_lraspp.onnx",
    )
    parser.add_argument(
        "--mask-out",
        type=Path,
        default=None,
        help="Optional output path for binary mask PNG inside geometry/",
    )
    parser.add_argument(
        "--overlay-out",
        type=Path,
        default=None,
        help="Optional output path for overlay JPEG inside geometry/",
    )
    parser.add_argument(
        "--no-geometry",
        action="store_true",
        help="Disable geometric length and volume estimation (legacy mode)",
    )
    parser.add_argument(
        "--pose-json",
        type=Path,
        default=None,
        help="Optional path to pose landmarks JSON",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output only")
    args = parser.parse_args(argv)

    mask_out = _geometry_output(args.mask_out) if args.mask_out else None
    overlay_out = _geometry_output(args.overlay_out) if args.overlay_out else None

    pose_lm = None
    if args.pose_json and args.pose_json.is_file():
        try:
            pose_lm = json.loads(args.pose_json.read_text(encoding="utf-8")).get("landmarks")
        except Exception:
            pose_lm = None

    pipeline = HierarchicalHairPipeline(
        type_onnx=args.type_model,
        seg_onnx=args.seg_model,
        person_onnx=args.person_model,
    )
    result, mask = pipeline.predict_file(
        args.image,
        enable_geometry=not args.no_geometry,
        pose_landmarks=pose_lm,
    )

    if mask_out or overlay_out:
        save_mask_and_overlay(
            image_path=args.image,
            mask_bin=mask,
            mask_out=mask_out,
            overlay_out=overlay_out,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
