"""Router kelola dokumen .md RAG + re-ingest ke ChromaDB.

Guard: token internal (X-Internal-Token). Hanya file .md di folder knowledge.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter()

KNOWLEDGE_DIR = settings.rag_knowledge_dir
_SAFE_NAME = re.compile(r"^[a-zA-Z0-9._-]+\.md$")


def _check_token(token: str | None) -> None:
    if settings.agent_internal_token and token != settings.agent_internal_token:
        raise HTTPException(status_code=401, detail="Token internal tidak valid")


def _safe_path(name: str) -> Path:
    if not _SAFE_NAME.match(name):
        raise HTTPException(status_code=400, detail="Nama file tidak valid (harus *.md)")
    p = (KNOWLEDGE_DIR / name).resolve()
    if KNOWLEDGE_DIR.resolve() not in p.parents and p.parent != KNOWLEDGE_DIR.resolve():
        raise HTTPException(status_code=400, detail="Path tidak diizinkan")
    return p


class KnowledgeDoc(BaseModel):
    content: str = Field(default="")


@router.get("/knowledge")
async def list_knowledge(x_internal_token: str | None = Header(default=None)) -> dict:
    _check_token(x_internal_token)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    items = [{"name": f.name, "size": f.stat().st_size} for f in files]
    return {"data": items}


@router.get("/knowledge/{name}")
async def get_knowledge(name: str, x_internal_token: str | None = Header(default=None)) -> dict:
    _check_token(x_internal_token)
    p = _safe_path(name)
    if not p.exists():
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    return {"data": {"name": name, "content": p.read_text(encoding="utf-8")}}


@router.put("/knowledge/{name}")
async def put_knowledge(
    name: str,
    doc: KnowledgeDoc,
    x_internal_token: str | None = Header(default=None),
) -> dict:
    _check_token(x_internal_token)
    p = _safe_path(name)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(doc.content, encoding="utf-8")
    return {"data": {"name": name, "saved": True}}


@router.delete("/knowledge/{name}")
async def delete_knowledge(name: str, x_internal_token: str | None = Header(default=None)) -> dict:
    _check_token(x_internal_token)
    p = _safe_path(name)
    if p.exists():
        p.unlink()
    return {"data": {"name": name, "deleted": True}}


@router.post("/rag/reingest")
async def reingest(x_internal_token: str | None = Header(default=None)) -> dict:
    _check_token(x_internal_token)
    from app.rag.ingest import plan_ingest

    summaries = plan_ingest(settings.rag_knowledge_dir, force=False)
    return {"data": {"files": len(summaries), "summaries": summaries}}
