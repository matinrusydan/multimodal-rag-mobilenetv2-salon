"""Evidence-based consultation with structured catalog, BM25 and optional LLM."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import replace
from typing import Optional

from app.config import settings
from app.rag.embedding import embed
from app.rag.prompt_builder import build_prompt, context_snippets
from app.rag.context_selection import context_records
from app.rag.retriever import RetrievedDoc, retriever
from app.rag.web_fallback import live_crawl_docs,needs_web_fallback
from app.settings_loader import gemini_api_key
from app.rag.corpus_loader import load_corpus

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
    def _ctx_hash(query: str, doc_ids: list[str], hair_context: Optional[dict], context_spans=None) -> str:
        identity = {"query": query, "hairContext": hair_context, "docIds": doc_ids}
        if context_spans is not None:
            identity['contextSpans'] = context_spans
        raw = json.dumps(identity, sort_keys=True)
        return "ctx-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _fallback_reply(query: str, docs: list[RetrievedDoc]) -> str:
        lines = []
        for i, d in enumerate(docs[:5]):
            source = d.file.replace(".md", "")
            section = f" — {d.section}" if d.section else ""
            snippet = " ".join((d.snippet or "").split())[:240]
            lines.append(f"{i + 1}. {source}{section}\n   {snippet}")
        return f"Penyusunan jawaban otomatis sedang tidak tersedia. Berikut kutipan sumber yang berhasil ditemukan untuk \"{query}\":\n\n" + "\n".join(lines)

    async def _call_one(self, client, model: str, system_prompt, contents) -> tuple[str, str]:
        """Panggil satu model; return (model, text). Raise bila gagal."""
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=build_config(system_instruction=system_prompt, temperature=0.7, max_output_tokens=900),
        )
        return model, extract_text(response)

    async def _call_gemini(self, messages: list[dict], model_override: Optional[str] = None) -> str:
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

        all_models = [model_override] if model_override else [settings.llm_model, *settings.llm_fallback_models]
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
        *,
        include_trace: bool = False,
        allow_web: Optional[bool] = None,
        strict_embedding: bool = False,
        generation_model: Optional[str] = None,
        live_services: bool = False,
    ) -> dict:
        from app.rag.scope_policy import scope_policy
        policy_reply=scope_policy(query)
        if policy_reply:
            payload={'reply':policy_reply['reply'],'sources':[],
                     'contextId':self._ctx_hash(query,[policy_reply['rule']],hair_context)}
            if include_trace:
                payload['_trace']={'generation_status':'policy_unavailable',
                    'generation_provider':'deterministic_policy','actual_generation_model':None,
                    'policy_rule':policy_reply['rule'],'retrieved_docs':[],'contexts':[],
                    'prompt_messages':None,'business_source_mode':'not_requested',
                    'retrieval_provider':'policy_only'}
            return payload
        # Evaluation calls remain frozen unless explicitly opted into live data.
        live_corpus = None
        catalog_status = 'snapshot'
        if live_services:
            if settings.rag_retrieval_provider not in {'bm25','bm25_source_balanced'}:
                raise ValueError('Live services require BM25 retrieval')
            frozen = load_corpus(settings.rag_runtime_corpus_file or settings.rag_corpus_file,
                                 require_manifest=settings.rag_runtime_corpus_file is not None)
            live_corpus = [d for d in frozen if d['source_type'] != 'db']
            from app.rag.live_services import load_services
            try:
                live_corpus += await load_services()
                catalog_status = 'live'
            except Exception as exc:
                logger.warning('Live catalog unavailable (%s)', type(exc).__name__)
                catalog_status = 'unavailable'
        if settings.rag_retrieval_provider in {'bm25','bm25_source_balanced'}:
            from app.rag.catalog_operations import catalog_answer
            catalog_corpus = live_corpus if live_services else load_corpus(settings.rag_corpus_file)
            lookup = catalog_answer(query,catalog_corpus,mode=catalog_status)
            if lookup:
                payload={'reply':lookup['reply'],'sources':lookup['sources'],
                         'contextId':self._ctx_hash(query,[lookup['fingerprint']],hair_context)}
                if include_trace:
                    payload['_trace']={'generation_status':lookup['status'],
                                       'generation_provider':'deterministic_catalog', 'actual_generation_model':None,
                                       'retrieved_docs':[{'id':d.id,'file':d.file,'section':d.section,'snippet':d.snippet,'metadata':d.metadata} for d in lookup['docs']],
                                       'contexts':[d.snippet for d in lookup['docs']], 'prompt_messages':None,
                                       'catalog_evidence_ids':lookup['catalog_ids'], 'catalog_operation':lookup['plan'],
                                       'business_source_mode':catalog_status, 'retrieval_provider':'structured_catalog_scan'}
                return payload
            from app.rag.answer_policy import service_clarification
            clarification=service_clarification(query,settings.rag_corpus_file,corpus=live_corpus,live=live_services)
            if clarification:
                payload={'reply':clarification['reply'],'sources':clarification['sources'],
                         'contextId':self._ctx_hash(query,clarification['catalog_ids'],hair_context)}
                if include_trace:
                    payload['_trace']={'generation_status':'policy_clarification','generation_provider':settings.ai_llm_provider,
                                       'actual_generation_model':None,'retrieved_docs':[],'contexts':[],
                                       'prompt_messages':None,'catalog_evidence_ids':clarification['catalog_ids'],
                                       'business_source_mode':catalog_status,
                                       'retrieval_provider':settings.rag_retrieval_provider}
                return payload
            from app.rag.care_intent import conditioner_clarification,unresolved_reference
            from app.rag.service_matching import match_services
            named=match_services(query,[d for d in catalog_corpus if d['source_type']=='db'])
            care_question=unresolved_reference(query,known_service=bool(named)) or conditioner_clarification(query)
            if care_question:
                # Resolve the explicit business part without assuming a care product.
                facts=[]
                if re.search(r'\b(harga|biaya|tarif)\b',query,re.I):facts.append('harga')
                if re.search(r'\b(durasi|menit)\b',query,re.I):facts.append('durasi')
                modifiers=[]
                if re.search(r'promo|diskon',query,re.I):modifiers.append('promo diskon')
                if re.search(r'riwayat|histori|kemarin|sebelumnya|bulan lalu|minggu lalu|harga lama',query,re.I):modifiers.append('riwayat harga')
                business= catalog_answer('Berapa '+' dan '.join(facts)+' '+ ' dan '.join(d['fields']['name'] for d in named)+' '+' '.join(modifiers)+'?',
                                         catalog_corpus,mode=catalog_status) if named and facts else None
                payload={'reply':(business['reply']+'\n\n' if business else '')+care_question['reply'],
                         'sources':business['sources'] if business else [],
                         'contextId':self._ctx_hash(query,[care_question['rule']]+[d['id'] for d in named],hair_context)}
                if include_trace:
                    payload['_trace']={'generation_status':'policy_clarification','generation_provider':'deterministic_policy',
                        'policy_rule':care_question['rule'],'actual_generation_model':None,
                        'retrieved_docs':[{'id':d.id,'file':d.file,'section':d.section,'snippet':d.snippet,'metadata':d.metadata} for d in business['docs']] if business else [],
                        'contexts':[d.snippet for d in business['docs']] if business else [],'prompt_messages':None,
                        'business_source_mode':catalog_status,'retrieval_provider':'explicit_product_clarification'}
                return payload
        # Retrieve local evidence first. Web augments missing topic coverage;
        # enabling it must not discard curated evidence or live catalog facts.
        if settings.rag_retrieval_provider in {'bm25','bm25_source_balanced'}:
            from app.rag.bm25_retrieval import retrieve
            kb_docs=retrieve(query,self.top_k,corpus=live_corpus) if live_services else retrieve(query,self.top_k)
        else:
            query_embedding=(await embed([query],strict=True))[0] if strict_embedding else (await embed([query]))[0]
            kb_docs=await retriever.retrieve(query_embedding,top_k=self.top_k,query=query)
        use_web=settings.web_fallback_enabled if allow_web is None else allow_web
        webpage_docs: list[RetrievedDoc] = []
        web_sources: list[dict] = []
        if use_web and needs_web_fallback(query,kb_docs):
            webpage_docs, web_sources = await live_crawl_docs(
                query,
                max_pages=settings.web_fallback_max_docs,
            )
        if settings.rag_context_selection=='source_scoped':
            from app.rag.care_intent import compatible_product_evidence
            webpage_docs=[d for d in webpage_docs if compatible_product_evidence(query,
                {'section':d.section or '', 'text':d.snippet or '', 'source_type':(d.metadata or {}).get('source_type')})]
        docs=kb_docs+webpage_docs

        if not docs or (settings.rag_retrieval_provider in {'bm25','bm25_source_balanced'}
                        and all((d.metadata or {}).get('bm25_score',1)<=0 for d in docs)):
            payload={'reply':'Saya belum menemukan sumber yang mendukung pertanyaan tersebut. Mohon perjelas layanan atau kebutuhan perawatan rambut yang dimaksud. Informasi yang belum tersedia dapat dikonfirmasikan kepada staf TIEN SALON.',
                     'sources':[],'contextId':self._ctx_hash(query,['no_matching_evidence'],hair_context)}
            if include_trace:
                payload['_trace']={'generation_status':'policy_unavailable',
                    'generation_provider':'deterministic_policy','actual_generation_model':None,
                    'policy_rule':'no_matching_evidence','retrieved_docs':[],'contexts':[],
                    'prompt_messages':None,'business_source_mode':catalog_status,
                    'retrieval_provider':settings.rag_retrieval_provider}
            return payload

        doc_ids = [f"{d.id or d.file}#{d.section or ''}:{hashlib.sha256((d.snippet or '').encode('utf-8')).hexdigest()[:16]}" for d in docs]
        context_id = self._ctx_hash(query, doc_ids, hair_context,
                                    context_records(docs,query,settings.rag_context_strategy))

        if settings.ai_llm_provider == 'chatgpt':
            from app.rag import chatgpt_plan
            try:
                is_local = not chatgpt_plan.available()
            except (ValueError,OSError,TypeError,AttributeError) as exc:
                logger.warning('ChatGPT session unavailable (%s)',type(exc).__name__)
                is_local=True
        else:
            is_local = settings.ai_llm_provider != 'gemini' or not gemini_api_key()

        # Dedup web sources by file (sudah unik dari live_crawl_docs, jaga-jaga).
        seen_web: set[str] = set()
        web_sources_uniq = []
        for s in web_sources:
            key = s.get("file", "")
            if key and key not in seen_web:
                seen_web.add(key)
                web_sources_uniq.append(s)

        def response(reply: str, generation_status: str) -> dict:
            from app.rag.answer_policy import cited_sources, source_payload
            citation_trace=None
            if generation_status=='llm_success':
                used=context_snippets(docs,query)
                reply,shown_sources,citation_trace=cited_sources(reply,[replace(d,snippet=text) for d,text in zip(docs,used)])
            else:
                shown_sources=[source_payload(d) for d in docs[:5]]
                if catalog_status == 'unavailable':
                    reply = 'Data layanan aktif belum dapat diakses. Harga, durasi, dan ketersediaan layanan belum dapat dipastikan.\n\n' + reply
            payload = {"reply": reply, "sources": shown_sources, "contextId": context_id}
            if include_trace:
                payload["_trace"] = {
                    "retrieved_docs": [
                        {"id": d.id, "file": d.file, "section": d.section,
                         "snippet": d.snippet, "distance": d.distance, "metadata": d.metadata}
                        for d in docs
                    ],
                    "contexts": context_snippets(docs,query) if generation_status == "llm_success" else [" ".join((d.snippet or "").split())[:240] for d in docs[:5]],
                    "context_spans": context_records(docs,query,settings.rag_context_strategy) if generation_status=='llm_success' else None,
                    "prompt_messages": messages if generation_status == "llm_success" else None,
                    "generation_status": generation_status,
                    "source_mode": "mixed_web_kb" if webpage_docs else "kb",
                    "actual_generation_model": (generation_model or (settings.chatgpt_model if settings.ai_llm_provider == 'chatgpt' else None)) if generation_status == "llm_success" else None,
                    "generation_provider": settings.ai_llm_provider,
                    "retrieval_provider": settings.rag_retrieval_provider,
                    "business_source_mode": catalog_status,
                    "citations": citation_trace,
                    "model_policy": "pinned" if generation_model or settings.ai_llm_provider == 'chatgpt' else "runtime_race; actual model not retained",
                }
            return payload

        if is_local:
            reply = self._fallback_reply(query, docs)
            logger.info("RagService.answer (offline) docs=%d", len(docs))
            return response(reply, "offline_extracts")

        messages = build_prompt(query, docs, hair_context, hair_features, web_sources=web_sources_uniq)
        if settings.rag_retrieval_provider in {'bm25','bm25_source_balanced'} and not live_services:
            from app.rag.bm25_retrieval import evaluation_policy_context
            policy = evaluation_policy_context()
            if policy:
                messages[0]['content'] += '\n\nKEBIJAKAN DAN BATAS SUMBER:\n' + policy
        if live_services:
            from app.rag.live_services import runtime_policy
            messages[0]['content'] += '\n\n' + runtime_policy(catalog_status == 'live')
        try:
            if settings.ai_llm_provider == 'chatgpt':
                reply = await asyncio.wait_for(chatgpt_plan.generate(messages, model=generation_model),
                                               timeout=settings.rag_generation_timeout_seconds)
            else:
                reply = await asyncio.wait_for(self._call_gemini(messages, model_override=generation_model),
                                               timeout=settings.rag_generation_timeout_seconds)
            if not reply or not reply.strip():raise RuntimeError('Empty model answer')
            generation_status = "llm_success"
        except Exception as exc:
            logger.warning("LLM gagal (%s); fallback offline", type(exc).__name__)
            reply = self._fallback_reply(query, docs)
            generation_status = "llm_error_offline_fallback"

        return response(reply, generation_status)


rag_service = RagService()
