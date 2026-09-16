"""Health router for the brain engine."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "data": {"status": "ok", "service": "ai-brain-engine"}}