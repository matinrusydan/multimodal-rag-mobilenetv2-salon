"""FastAPI brain engine — CV (Hierarchical Multi-Attribute ONNX) & RAG (BM25/ChromaDB + Gemini/ChatGPT).

Entry point: uvicorn app.main:app --port 5000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.rag.live_services import close_catalog_client, start_catalog_client
from app.routers import agent, analyze, chat, health, knowledge

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    settings.validate_runtime()
    await start_catalog_client()
    try:
        yield
    finally:
        await close_catalog_client()


app = FastAPI(title="TIEN Salon Brain Engine", version="1.0.0", lifespan=lifespan)

# --- Routes ---
app.include_router(health.router, prefix="/ai")
app.include_router(analyze.router, prefix="/ai")
app.include_router(chat.router, prefix="/ai")
app.include_router(agent.router, prefix="/ai")
app.include_router(knowledge.router, prefix="/ai")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled runtime error (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        media_type="application/problem+json",
        content={
            "type": "internal_error",
            "title": "Kesalahan internal brain engine",
            "status": 500,
            "detail": "Permintaan belum dapat diproses. Silakan coba lagi.",
        },
    )
