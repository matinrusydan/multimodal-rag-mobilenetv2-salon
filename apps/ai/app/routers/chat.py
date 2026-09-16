"""Chat router — RAG query via ChromaDB + Gemini (or local fallback)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.rag_service import rag_service

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    hairContext: dict | None = None
    hairFeatures: dict | None = None
    contextId: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest) -> dict:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong")

    result = await rag_service.answer(
        query=req.message.strip(),
        hair_context=req.hairContext,
        hair_features=req.hairFeatures,
    )

    return {
        "data": {
            "reply": result["reply"],
            "sources": result["sources"],
            "contextId": result["contextId"],
        }
    }