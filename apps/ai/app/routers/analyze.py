"""Analyze router — CV hierarchical multi-attribute classification (multipart image)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

logger = logging.getLogger(__name__)

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
        from app.cv.hierarchical import run_hierarchical_analysis

        result = run_hierarchical_analysis(buffer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analyze failure")
        raise HTTPException(
            status_code=500, detail=f"Gagal memproses analisis citra: {exc}"
        ) from exc

    return {
        "data": {
            "hairLength": result["hairLength"],
            "hairType": result["hairType"],
            "hairVolume": result.get("hairVolume"),
            "tiedHair": result.get("tiedHair"),
            "hairFeatures": result.get("hairFeatures"),
            "geometry": result.get("geometry"),
            "analyzedAt": datetime.now(timezone.utc).isoformat(),
            "status": result.get("status", "ok"),
        }
    }
