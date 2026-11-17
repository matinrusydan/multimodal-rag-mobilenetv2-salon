"""Health router for the brain engine."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "data": {"status": "ok", "service": "ai-brain-engine"}}


@router.get("/ready")
async def ready():
    from app.rag.preflight import check

    report = await check(check_catalog=True)
    return JSONResponse(
        status_code=200 if report["status"] == "configuration_ready" else 503,
        content=report,
    )
