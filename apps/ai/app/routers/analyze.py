"""Analyze router — CV classification via MobileNetV2 ONNX (multipart image)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.cv.hair_features import compute_hair_features
from app.cv.model import cv_model
from app.cv.preprocessing import preprocess
from app.config import settings

router = APIRouter()

ALLOWED_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/analyze")
async def analyze(image: UploadFile = File(...)) -> dict:
    if image.content_type not in ALLOWED_MIMETYPES:
        raise HTTPException(status_code=400, detail="Format gambar harus JPG, PNG, atau WebP")

    buffer = await image.read()
    if not buffer:
        raise HTTPException(status_code=400, detail="Gambar kosong (file tidak terbaca)")

    try:
        tensor, roi_rgb = preprocess(buffer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    hair_features = compute_hair_features(roi_rgb)

    try:
        hair_type = cv_model.classify_type(tensor)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Model hair_type tidak tersedia: {exc}") from exc

    hair_length = cv_model.classify_length(tensor)

    low_length = hair_length["confidence"] <= settings.confidence_threshold
    low_type = hair_type["confidence"] < settings.confidence_threshold
    status = "low_confidence" if low_length or low_type else "ok"

    return {
        "data": {
            "hairLength": hair_length,
            "hairType": hair_type,
            "hairFeatures": hair_features,
            "analyzedAt": datetime.now(timezone.utc).isoformat(),
            "status": status,
        }
    }