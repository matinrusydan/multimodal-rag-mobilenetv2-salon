"""Agent router — admin agent (RAG katalog + tool-call data live).

Endpoint ini HANYA boleh dipanggil oleh Express API (dijaga X-Internal-Token).
RBAC admin ditegakkan di Express sebelum meneruskan ke sini.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.rag.agent_service import agent_service

router = APIRouter()


class AgentHistoryItem(BaseModel):
    role: str
    content: str


class AgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    contextId: str | None = None
    history: list[AgentHistoryItem] | None = None
    auth: dict | None = None


@router.post("/agent")
async def agent(
    req: AgentRequest,
    x_internal_token: str | None = Header(default=None),
) -> dict:
    # Guard token internal (bila dikonfigurasi).
    if settings.agent_internal_token and x_internal_token != settings.agent_internal_token:
        raise HTTPException(status_code=401, detail="Token internal tidak valid")

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong")

    result = await agent_service.answer(
        query=req.message.strip(),
        auth=req.auth,
        history=[h.model_dump() for h in (req.history or [])],
        context_id=req.contextId,
    )

    return {
        "data": {
            "reply": result["reply"],
            "sources": result["sources"],
            "toolTrace": result.get("toolTrace", []),
            "contextId": result["contextId"],
        }
    }
