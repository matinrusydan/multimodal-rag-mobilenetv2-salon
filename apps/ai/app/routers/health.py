"""Health router for the brain engine."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "data": {"status": "ok", "service": "ai-brain-engine"}}


@router.post('/analyze', status_code=503)
async def analyze_unavailable():
    # Do not declare UploadFile/Form: even an empty request must get this result.
    return JSONResponse(
        status_code=503,
        media_type='application/problem+json',
        content={
            'type': 'feature_unavailable',
            'title': 'Fitur belum tersedia',
            'status': 503,
            'detail': 'Analisis foto belum tersedia. Silakan gunakan konsultasi teks.',
        },
    )


@router.get('/ready')
async def ready():
    from app.rag.preflight import check
    report = await check(check_catalog=True)
    return JSONResponse(
        status_code=200 if report['status'] == 'configuration_ready' else 503,
        content=report,
    )
