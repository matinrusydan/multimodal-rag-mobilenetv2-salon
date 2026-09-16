"""FastAPI brain engine — CV (MobileNetV2 ONNX), RAG (ChromaDB + Gemini), Crawl4AI.

Entry point: uvicorn app.main:app --port 5000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import analyze, chat, health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG-Salon Brain Engine", version="0.1.0")

# --- Routes ---
app.include_router(health.router, prefix="/ai")
app.include_router(analyze.router, prefix="/ai")
app.include_router(chat.router, prefix="/ai")


# --- Global error handler (Problem Details-like) ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "type": "internal_error",
            "title": "Kesalahan internal brain engine",
            "status": 500,
            "detail": str(exc),
        },
    )


@app.on_event("startup")
async def startup():
    logger.info("Brain engine dimulai (port=%s, host=%s)", settings.ai_port, settings.ai_host)