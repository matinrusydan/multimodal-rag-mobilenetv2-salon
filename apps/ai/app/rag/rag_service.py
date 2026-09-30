"""LLM provider for the RAG answer — Gemini via google-genai, with a deterministic
offline fallback that builds the reply from retrieved docs (same as Node RagService).

Port of `apps/api/src/services/RagService.ts`.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from typing import Optional

from app.config import settings
from app.rag.embedding import embed
from app.rag.prompt_builder import build_prompt
from app.rag.retriever import RetrievedDoc, retriever
from app.rag.web_fallback import live_crawl_docs
from app.settings_loader import gemini_api_key

logger = logging.getLogger(__name__)


def extract_text(response) -> str:
    """Ambil teks dari respons Gemini secara robust.

    Model Gemini 3.x (reasoning) kadang mengembalikan `response.text` kosong
    meski teksnya ada di `candidates[0].content.parts`. Helper ini membaca
    kedua jalur agar tidak kehilangan output.
    """
    try:
        text = getattr(response, "text", None)
        if text:
            return text.strip()
    except Exception:
        pass
    try:
        candidates = getattr(response, "candidates", None) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) or []
            # Lewati bagian "thinking" (thought=True) — ambil jawaban final saja.
            chunks = [p.text for p in parts if getattr(p, "text", None) and not getattr(p, "thought", False)]
            if not chunks:
                chunks = [p.text for p in parts if getattr(p, "text", None)]
            if chunks:
                return "".join(chunks).strip()
    except Exception:
        pass
    return ""


def build_config(system_instruction=None, temperature=0.7, max_output_tokens=900):
    """Bangun GenerateContentConfig yang kompatibel dengan model Gemini 3.x.

    Model 3.x memakai 'thinking' yang dapat menghabiskan jatah max_output_tokens
    sehingga jawaban final sering kosong. Kita nonaktifkan thinking
    (thinking_budget=0) bila SDK mendukung; jika tidak, kembali ke config biasa.
    """
    from google import genai

    kwargs = {"temperature": temperature, "max_output_tokens": max_output_tokens}
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    try:
        return genai.types.GenerateContentConfig(
            thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
            **kwargs,
        )
    except Exception:
        return genai.types.GenerateContentConfig(**kwargs)

# Model yang sedang kena rate-limit/quota → di-skip sementara (cooldown).
# Format: {model_name: monotonic_deadline}
_MODEL_COOLDOWN: dict[str, float] = {}
_COOLDOWN_SECONDS = float(os.getenv("AI_LLM_COOLDOWN_SECONDS", "120"))


def _model_ready(model: str) -> bool:
    deadline = _MODEL_COOLDOWN.get(model)
    return deadline is None or time.monotonic() >= deadline


def _mark_cooldown(model: str, seconds: float | None = None) -> None:
    _MODEL_COOLDOWN[model] = time.monotonic() + (seconds or _COOLDOWN_SECONDS)


class RagService:
    def __init__(self) -> None:
        self.top_k = settings.rag_top_k

    @staticmethod
    def _ctx_hash(query: str, doc_ids: list[str], hair_context: Optional[dict]) -> str:
        raw = json.dumps({"query": query, "hairContext": hair_context, "docIds": doc_ids}, sort_keys=True)
        return "ctx-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _fallback_reply(query: str, docs: list[RetrievedDoc]) -> str:
        lines = []
        for i, d in enumerate(docs[:5]):
            source = d.file.replace(".md", "")
            section = f" — {d.section}" if d.section else ""
            snippet = " ".join((d.snippet or "").split())[:240]
            lines.append(f"{i + 1}. {source}{section}\n   {snippet}")
        return f"(Mode offline — embed lokal, tanpa Gemini.) Berdasarkan knowledge base untuk \"{query}\":\n\n" + "\n".join(lines)

    async def _call_one(self, client, model: str, system_prompt, contents) -> tuple[str, str]:
        """Panggil satu model; return (model, text). Raise bila gagal."""
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=build_config(system_instruction=system_prompt, temperature=0.7, max_output_tokens=900),
        )
        return model, extract_text(response)

    async def _call_gemini(self, messages: list[dict]) -> str:
        from google import genai

        # retry internal SDK dimatikan agar tidak menggantung; fallback ditangani manual.
        try:
            client = genai.Client(
                api_key=gemini_api_key(),
                http_options=genai.types.HttpOptions(retry_options=genai.types.HttpRetryOptions(attempts=1)),
            )
        except Exception:
            client = genai.Client(api_key=gemini_api_key())
        system_prompt = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
        contents = [user_prompt]

        all_models = [settings.llm_model, *settings.llm_fallback_models]
        ready = [m for m in all_models if _model_ready(m)]
        if not ready:
            ready = sorted(all_models, key=lambda m: _MODEL_COOLDOWN.get(m, 0.0))[:1]

        # RACE paralel: coba beberapa model sekaligus, ambil yang pertama sukses.
        # Ini tahan terhadap 503 (high demand) pada sebagian model.
        PER_MODEL_TIMEOUT = float(os.getenv("AI_LLM_TIMEOUT_SECONDS", "35"))
        race = ready[:5]

        tasks = [
            asyncio.create_task(asyncio.wait_for(self._call_one(client, m, system_prompt, contents), timeout=PER_MODEL_TIMEOUT))
            for m in race
        ]

        last_exc: Exception | None = None
        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    model, text = await coro
                    if text:
                        winner = model
                        if winner != settings.llm_model:
                            logger.info("LLM fallback dipakai (race): %s", winner)
                        return text
                except Exception as exc:  # noqa: PERF203
                    last_exc = exc
                    msg = str(exc)
                    is_quota = any(t in msg for t in ("429", "RESOURCE_EXHAUSTED"))
                    is_5xx = any(t in msg for t in ("503", "UNAVAILABLE", "500"))
                    if is_quota:
                        wait = _COOLDOWN_SECONDS
                        m = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)", msg)
                        if m:
                            wait = max(float(m.group(1)), 30.0)
                        _mark_cooldown("gemini", wait)
                    logger.warning(
                        "LLM gagal [%s]: %s",
                        "quota" if is_quota else ("retriable" if is_5xx else "fatal"),
                        msg[:120],
                    )
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

        if last_exc:
            raise last_exc
        raise RuntimeError("semua model LLM gagal")

    async def answer(
        self,
        query: str,
        hair_context: Optional[dict] = None,
        hair_features: Optional[dict] = None,
    ) -> dict:
        # Deteksi mode sumber:
        #  - kesehatan rambut (rontok/ketombe) -> WEB-ONLY (full alodokter)
        #  - layanan salon yang menyentuh kondisi rambut (bleaching/smoothing/rusak)
        #    -> MIX (KB salon + web kesehatan)
        #  - lainnya -> KB lokal saja
        is_health_topic = False
        is_hair_concern = False
        if settings.web_fallback_enabled:
            from app.crawler.stealth import detect_hair_concern, detect_health_topic

            is_health_topic = detect_health_topic(query)
            is_hair_concern = not is_health_topic and detect_hair_concern(query)

        webpage_docs: list[RetrievedDoc] = []
        web_sources: list[dict] = []

        if is_health_topic or is_hair_concern:
            # Live crawl alodokter untuk kedua mode (web-only & mix).
            webpage_docs, web_sources = await live_crawl_docs(
                query,
                max_pages=settings.web_fallback_max_docs,
            )

        if is_health_topic:
            # Full web mode: skip ChromaDB sepenuhnya.
            docs = webpage_docs
            logger.info("web-only mode (topik kesehatan): %d doc web", len(docs))
        else:
            # Mode KB (normal) atau mix: retrieve dari ChromaDB.
            query_embedding = (await embed([query]))[0]
            kb_docs = await retriever.retrieve(query_embedding, top_k=self.top_k, query=query)

            if is_hair_concern and webpage_docs:
                # Mix: dokumen web di depan, lalu KB salon.
                docs = webpage_docs + kb_docs
                logger.info(
                    "mix mode (layanan + kondisi rambut): %d doc web + %d KB doc",
                    len(webpage_docs),
                    len(kb_docs),
                )
            else:
                docs = kb_docs

        doc_ids = [f"{d.file}#{d.section or ''}" for d in docs]
        context_id = self._ctx_hash(query, doc_ids, hair_context)

        is_local = settings.ai_embedding_provider != "gemini" or not gemini_api_key()

        # Bangun sources untuk API: web sources (unik per URL) + KB sources.
        kb_sources = [{"file": d.file, "snippet": d.snippet} for d in docs if not d.file.startswith("web:")]
        # Dedup web sources by file (sudah unik dari live_crawl_docs, jaga-jaga).
        seen_web: set[str] = set()
        web_sources_uniq = []
        for s in web_sources:
            key = s.get("file", "")
            if key and key not in seen_web:
                seen_web.add(key)
                web_sources_uniq.append(s)
        api_sources = web_sources_uniq + kb_sources

        if is_local:
            reply = self._fallback_reply(query, docs)
            logger.info("RagService.answer (offline) docs=%d", len(docs))
            return {
                "reply": reply,
                "sources": api_sources,
                "contextId": context_id,
            }

        messages = build_prompt(query, docs, hair_context, hair_features, web_sources=web_sources_uniq)
        try:
            reply = await self._call_gemini(messages)
        except Exception as exc:
            logger.warning("Gemini LLM gagal (%s); fallback offline", exc)
            reply = self._fallback_reply(query, docs)

        return {
            "reply": reply,
            "sources": api_sources,
            "contextId": context_id,
        }


rag_service = RagService()
