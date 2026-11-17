"""Bridge between FastAPI and the Phase 4 Hierarchical CV Pipeline in apps/api/cv/geometry."""

from __future__ import annotations

import io
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Locate apps/api/cv/geometry
AI_APP_DIR = Path(__file__).resolve().parents[2]  # apps/ai
REPO_ROOT = AI_APP_DIR.parent.parent  # workspace root
GEOMETRY_DIR = REPO_ROOT / "apps" / "api" / "cv" / "geometry"
if str(GEOMETRY_DIR) not in sys.path:
    sys.path.insert(0, str(GEOMETRY_DIR))

# Champion 3-class hair type model path (verified partner retrain)
CHAMPION_3CLASS_TYPE_ONNX = (
    GEOMETRY_DIR
    / "experiments"
    / "partner-20261114-threeclass-corrected-seed42"
    / "weights"
    / "hair_type.onnx"
)

_pipeline = None


def reset_hierarchical_pipeline() -> None:
    """Reset cached pipeline instance (useful in tests and reloads)."""
    global _pipeline
    _pipeline = None


def get_hierarchical_pipeline(type_onnx: Path | None = None):
    global _pipeline
    if _pipeline is None:
        import os
        from classify_hierarchical import HierarchicalHairPipeline

        target_type_onnx = type_onnx
        if target_type_onnx is None:
            env_type = os.getenv("MODEL_TYPE_PATH") or os.getenv("CV_TYPE_ONNX")
            if env_type and Path(env_type).exists():
                target_type_onnx = Path(env_type)
            elif CHAMPION_3CLASS_TYPE_ONNX.exists():
                target_type_onnx = CHAMPION_3CLASS_TYPE_ONNX

        if target_type_onnx is not None:
            logger.info("Initializing HierarchicalHairPipeline with type_onnx=%s", target_type_onnx)
            _pipeline = HierarchicalHairPipeline(type_onnx=target_type_onnx)
        else:
            logger.info("Initializing HierarchicalHairPipeline with default ONNX models...")
            _pipeline = HierarchicalHairPipeline()
    return _pipeline


def run_hierarchical_analysis(buffer: bytes) -> dict[str, Any]:
    """Run full Phase 4 hierarchical inference on image bytes."""
    from PIL import Image

    from app.cv.hair_features import compute_hair_features
    from app.cv.preprocessing import preprocess
    from measure_length import measure_hair_length

    # Preprocess for GLCM + HSV features
    _tensor, roi_rgb = preprocess(buffer)
    hair_features = compute_hair_features(roi_rgb)

    pipe = get_hierarchical_pipeline()
    with Image.open(io.BytesIO(buffer)) as im:
        raw_res, mask = pipe.predict_pil(im)

    type_res = raw_res["stage1_hair_type"]
    length_dict = raw_res["stage2_conditional_attributes"]["length"]
    volume_dict = raw_res["stage2_conditional_attributes"]["volume"]
    tied_res = raw_res["tied_hair_assessment"]
    seg_res = raw_res["stage2_segmentation"]

    # Hair length label & confidence
    length_label = length_dict.get("predicted_class")
    length_conf = length_dict.get("confidence")
    if not length_label:
        m_len = measure_hair_length(mask)
        length_label = m_len.get("predicted_class") or "menengah"
        length_conf = m_len.get("confidence") or 0.50

    # Hair volume (if available)
    volume_label = volume_dict.get("volume_class")
    volume_conf = volume_dict.get("confidence")
    volume_res = (
        {"label": volume_label, "confidence": volume_conf}
        if volume_label
        else None
    )

    # Confidence status
    low_length = (length_conf or 0.0) < 0.60
    low_type = (type_res.get("confidence") or 0.0) < 0.60
    status = "low_confidence" if (low_length or low_type) else "ok"

    return {
        "hairLength": {
            "label": length_label,
            "confidence": round(float(length_conf), 4),
        },
        "hairType": {
            "label": type_res["predicted_class"],
            "confidence": round(float(type_res["confidence"]), 4),
        },
        "hairVolume": volume_res,
        "tiedHair": {
            "tied": tied_res.get("tied"),
            "style": tied_res.get("style"),
            "confidence": tied_res.get("confidence"),
        },
        "hairFeatures": hair_features,
        "geometry": {
            "head_units": length_dict.get("head_units"),
            "relative_shoulder_ratio": length_dict.get("relative_shoulder_ratio"),
            "method": length_dict.get("method"),
            "hair_coverage": seg_res.get("hair_coverage"),
            "probabilities": type_res.get("probabilities"),
        },
        "status": status,
        "latency_ms": raw_res.get("total_latency_ms"),
    }
