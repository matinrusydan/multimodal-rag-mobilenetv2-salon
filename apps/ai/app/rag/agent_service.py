"""AgentService — agent admin: RAG (katalog dari DB) + tool-call data live (Gemini).

Alur:
  1. Embed pertanyaan -> retrieve dokumen katalog dari ChromaDB (konteks semantik).
  2. Kirim ke Gemini dengan `tools` (function declarations). Gemini dapat:
     - memanggil tool (get_services_summary / get_revenue_summary / get_reservations_stats)
       untuk angka live, lalu menjawab;
     - atau menjawab langsung dari konteks katalog.
  3. Fallback offline bila Gemini tidak tersedia: bangun jawaban dari konteks + tool dasar.

RBAC: `auth` (dari Express) diteruskan; tool yang butuh izin bisa dijaga di sini.
"""

from __future__ import annotations

import asyncio
import json
import logging

from app.config import settings
from app.rag.agent_tools import TOOL_DECLARATIONS, execute_tool
from app.rag.embedding import embed
from app.rag.retriever import Retriever
from app.rag.vector_store import AGENT_TOPICS
from app.settings_loader import gemini_api_key

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = (
    "Anda adalah asisten agent ADMIN untuk sebuah salon. Anda membantu pemilik/staf admin "
    "menjawab pertanyaan operasional: layanan yang tersedia, harga, pemasukan, dan reservasi.\n"
    "ATURAN:\n"
    "- Untuk angka/data terbaru (pemasukan, jumlah reservasi, daftar layanan terkini), "
    "WAJIB memanggil tool yang sesuai, jangan menebak.\n"
    "- Untuk pertanyaan konsep/umum, gunakan KONTEKS katalog yang diberikan.\n"
    "- Jawab ringkas, dalam Bahasa Indonesia, dengan angka yang jelas (format Rupiah bila uang).\n"
    "- Bila data kosong/tidak tersedia, katakan jujur. Jangan mengarang angka."
)


def _format_rupiah(value: int | float | None) -> str:
    if value is None:
        return "-"
    return f"Rp{int(value):,}".replace(",", ".")


class AgentService:
    def __init__(self) -> None:
        self.top_k = settings.rag_top_k
        # Agent memakai koleksi katalog + KB (AGENT_TOPICS), bukan retriever publik.
        self.retriever = Retriever(topics=list(AGENT_TOPICS))

    async def _retrieve_context(self, query: str) -> list[str]:
        try:
            if settings.rag_retrieval_provider in {'bm25','bm25_source_balanced'}:
                from app.rag.bm25_retrieval import retrieve
                return [d.snippet or '' for d in retrieve(query, self.top_k)]
            embedding = (await embed([query]))[0]
            docs = await self.retriever.retrieve(embedding, top_k=self.top_k)
            return [d.snippet or "" for d in docs if d.snippet]
        except Exception as exc:
            logger.warning("retrieve katalog gagal: %s", exc)
            return []

    async def _call_gemini_with_tools(
        self, query: str, context: list[str], history: list[dict]
    ) -> dict:
        """Satu arah: kirim + jalankan tool-call hingga jumlah iterasi terbatas."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=gemini_api_key())

        ctx_block = "\n\n".join(f"- {c}" for c in context) if context else "(tidak ada konteks katalog)"
        system_instruction = f"{SYSTEM_INSTRUCTION}\n\nKONTEKS KATALOG:\n{ctx_block}"

        contents: list[types.Content] = []
        for h in history[-8:]:
            role = "user" if h.get("role") == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=h.get("content", ""))]))
        contents.append(types.Content(role="user", parts=[types.Part(text=query)]))

        tools = [types.Tool(function_declarations=[
            types.FunctionDeclaration(**decl) for decl in TOOL_DECLARATIONS
        ])]
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,
            max_output_tokens=1000,
            tools=tools,
        )

        tool_trace: list[dict] = []
        model = settings.llm_model
        for _ in range(5):  # batas iterasi tool-call
            response = await client.aio.models.generate_content(
                model=model, contents=contents, config=config
            )
            candidate = response.candidates[0]
            parts = candidate.content.parts if candidate.content else []

            calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
            if not calls:
                return {"reply": (response.text or "").strip(), "tool_trace": tool_trace}

            # echo model turn, lalu jawab tiap tool-call
            contents.append(candidate.content)
            for call in calls:
                args = dict(call.args) if call.args else {}
                result = await execute_tool(call.name, args)
                tool_trace.append({"tool": call.name, "args": args, "ok": result.get("ok", False)})
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=call.name, response=result
                    )],
                ))

        return {"reply": "(agent berhenti: terlalu banyak langkah tool)", "tool_trace": tool_trace}

    async def _call_chatgpt_with_tools(self, query, context, history):
        from app.rag import chatgpt_plan
        inputs=[{'role':'system','content':SYSTEM_INSTRUCTION+'\nKONTEKS KATALOG (dapat berupa snapshot; angka live harus memakai tool):\n'+'\n'.join(context)}]
        inputs += [{'role':'user' if h.get('role')=='user' else 'assistant','content':str(h.get('content',''))} for h in history[-8:]]
        inputs.append({'role':'user','content':query})
        tools=[{'type':'function',**declaration,'strict':False} for declaration in TOOL_DECLARATIONS]
        trace=[]
        for _ in range(5):
            response=await chatgpt_plan.response(inputs,tools=tools,max_tokens=1000)
            calls=[item for item in response.get('output',[]) if item.get('type')=='function_call']
            if not calls:
                reply=chatgpt_plan.output_text(response)
                if not reply:raise RuntimeError('ChatGPT agent returned no answer')
                return {'reply':reply,'tool_trace':trace}
            inputs.extend(response['output'])
            for call in calls:
                args=json.loads(call['arguments'])
                if not isinstance(args,dict):raise ValueError('Tool arguments must be an object')
                result=await execute_tool(call['name'],args)
                trace.append({'tool':call['name'],'args':args,'result':result})
                inputs.append({'type':'function_call_output','call_id':call['call_id'],'output':json.dumps(result,ensure_ascii=False)})
        raise RuntimeError('ChatGPT agent exceeded tool-call limit')

    def _offline_reply(self, query: str, context: list[str]) -> str:
        if context:
            return (
                "(Mode offline — tanpa generasi LLM.) Berikut konteks katalog yang relevan:\n\n"
                + "\n".join(f"- {c}" for c in context[:5])
            )
        return "(Mode offline — tanpa generasi LLM.) Tidak ada konteks katalog tersedia."

    async def answer(
        self,
        query: str,
        auth: dict | None = None,
        history: list[dict] | None = None,
        context_id: str | None = None,
    ) -> dict:
        history = history or []
        context = await self._retrieve_context(query)

        if settings.ai_llm_provider == 'chatgpt':
            from app.rag import chatgpt_plan
            is_local = not chatgpt_plan.available()
        else:
            is_local = settings.ai_llm_provider != "gemini" or not gemini_api_key()
        tool_trace: list[dict] = []

        if is_local:
            reply = self._offline_reply(query, context)
        else:
            try:
                out = await self._call_chatgpt_with_tools(query, context, history) if settings.ai_llm_provider == 'chatgpt' else await self._call_gemini_with_tools(query, context, history)
                reply = out["reply"]
                tool_trace = out.get("tool_trace", [])
            except Exception as exc:
                logger.warning("LLM agent gagal (%s); fallback offline", type(exc).__name__)
                reply = self._offline_reply(query, context)

        sources = [{"file": "katalog", "snippet": c} for c in context[:5]]
        return {
            "reply": reply,
            "sources": sources,
            "toolTrace": tool_trace,
            "contextId": context_id,
        }


agent_service = AgentService()
