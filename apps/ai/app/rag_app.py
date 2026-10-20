"""RAG-only service; leaves the existing CV application and routes unchanged.

uvicorn app.rag_app:app --host 127.0.0.1 --port 5000
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import chat,health
from app.rag.live_services import start_catalog_client,close_catalog_client


@asynccontextmanager
async def lifespan(app):
    await start_catalog_client()
    try:yield
    finally:await close_catalog_client()

app=FastAPI(title='TIEN Salon RAG',version='1.0.0',lifespan=lifespan)
app.include_router(health.router,prefix='/ai')
app.include_router(chat.router,prefix='/ai')
