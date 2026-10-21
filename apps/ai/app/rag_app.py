"""Canonical lightweight RAG runtime, including the existing admin endpoints."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import agent, chat, health, knowledge
from app.rag.live_services import start_catalog_client, close_catalog_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    settings.validate_runtime()
    await start_catalog_client()
    try:
        yield
    finally:
        await close_catalog_client()


app = FastAPI(title='TIEN Salon RAG', version='1.0.0', lifespan=lifespan)
app.include_router(health.router, prefix='/ai')
app.include_router(chat.router, prefix='/ai')
app.include_router(agent.router, prefix='/ai')
app.include_router(knowledge.router, prefix='/ai')


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Exception text, request URLs and traceback locals may contain credentials.
    logger.error('Unhandled runtime error (%s)', type(exc).__name__)
    return JSONResponse(
        status_code=500,
        media_type='application/problem+json',
        content={
            'type': 'internal_error',
            'title': 'Kesalahan internal brain engine',
            'status': 500,
            'detail': 'Permintaan belum dapat diproses. Silakan coba lagi.',
        },
    )
