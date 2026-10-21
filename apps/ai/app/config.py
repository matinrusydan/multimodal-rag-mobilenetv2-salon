"""Environment configuration for the FastAPI brain engine (apps/ai)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load root .env before defaults are read (dotenv does not override existing vars).
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)
# Also load apps/ai/.env if present (helper for dev).
load_dotenv(dotenv_path=BASE_DIR.parents[0] / "apps" / "ai" / ".env", override=False)


class Settings:
    """Typed read of environment variables with sane defaults for local dev."""

    def __init__(self) -> None:
        self.ai_port: int = int(os.getenv("AI_PORT", "5000"))
        self.ai_host: str = os.getenv("AI_HOST", "127.0.0.1")

        # Gemini provider (embed + LLM)
        self.gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
        self.ai_embedding_provider: str = os.getenv("AI_EMBEDDING_PROVIDER", "gemini")
        self.ai_llm_provider: str = os.getenv("AI_LLM_PROVIDER", "gemini")
        # ChatGPT-plan OAuth is separate from both Gemini keys and paid API keys.
        self.chatgpt_model: str = os.getenv("AI_CHATGPT_MODEL", "").strip()
        self.rag_retrieval_provider: str = os.getenv("RAG_RETRIEVAL_PROVIDER", "chroma")
        self.rag_live_services: bool = os.getenv("RAG_LIVE_SERVICES", "false").lower() == "true"
        self.rag_context_strategy: str = os.getenv("RAG_CONTEXT_STRATEGY", "head")
        self.rag_context_selection: str = os.getenv('RAG_CONTEXT_SELECTION','all')
        self.rag_generation_timeout_seconds: float = float(os.getenv('RAG_GENERATION_TIMEOUT_SECONDS','50'))
        self.rag_corpus_file: Path = Path(os.getenv("RAG_CORPUS_FILE", str(BASE_DIR / "rag/eval/curated-development-v2/corpus.json")))
        runtime_path=os.getenv('RAG_RUNTIME_CORPUS_FILE','').strip()
        self.rag_runtime_corpus_file: Path | None = ((Path(runtime_path) if Path(runtime_path).is_absolute() else BASE_DIR/runtime_path) if runtime_path else None)
        self.embedding_model: str = os.getenv("AI_EMBEDDING_MODEL", "gemini-embedding-001")
        self.llm_model: str = os.getenv("AI_LLM_MODEL", "gemini-3.6-flash")
        # Daftar model fallback bila model utama kena rate-limit/quota (429) atau 5xx.
        self.llm_fallback_models: list[str] = [
            m.strip()
            for m in os.getenv(
                "AI_LLM_FALLBACK_MODELS",
                "gemini-3.1-flash-lite,gemini-flash-lite-latest,gemini-3-flash-preview,gemini-flash-latest",
            ).split(",")
            if m.strip()
        ]
        self.embedding_dim: int = int(os.getenv("AI_EMBEDDING_DIM", "768"))

        # ChromaDB
        self.chroma_mode: str = os.getenv("AI_CHROMA_MODE", "persistent")  # persistent | http
        self.chroma_url: str = os.getenv("CHROMA_URL", "http://127.0.0.1:8000")
        self.chroma_persist_dir: Path = Path(os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_db")))

        # RAG tuning (match the Node pipeline)
        self.rag_top_k: int = int(os.getenv("RAG_TOP_K", "5"))
        self.rag_min_chunk_tokens: int = int(os.getenv("RAG_MIN_CHUNK_TOKENS", "500"))
        self.rag_max_chunk_tokens: int = int(os.getenv("RAG_MAX_CHUNK_TOKENS", "1000"))
        self.rag_chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
        # Gabungkan section kecil menjadi chunk besar (~min..max token) sesuai
        # praktik umum RAG (chunk 500-1000 token).
        self.rag_merge_sections: bool = os.getenv("RAG_MERGE_SECTIONS", "false").lower() == "true"
        self.rag_knowledge_dir: Path = Path(os.getenv("RAG_KNOWLEDGE_DIR", str(BASE_DIR / "rag" / "knowledge")))

        # Live web fallback (crawl alodokter saat KB lokal tak menjawab)
        self.web_fallback_enabled: bool = os.getenv("WEB_FALLBACK_ENABLED", "true").lower() == "true"
        self.web_fallback_max_docs: int = int(os.getenv("WEB_FALLBACK_MAX_DOCS", "2"))

        # CV
        self.model_length_path: Path = Path(os.getenv("MODEL_LENGTH_PATH", str(BASE_DIR / "cv" / "weights" / "hair_length.onnx")))
        self.model_type_path: Path = Path(os.getenv("MODEL_TYPE_PATH", str(BASE_DIR / "cv" / "weights" / "hair_type.onnx")))
        self.confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

        # Crawler
        self.crawl_base_url: str = os.getenv("CRAWL_BASE_URL", "http://127.0.0.1:3000")
        self.crawl_use_browser: bool = os.getenv("CRAWL_USE_BROWSER", "false").lower() == "true"
        self.crawl_delay_ms: int = int(os.getenv("CRAWL_DELAY_MS", "1500"))
        self.crawl_tips_url: str = os.getenv("CRAWL_TIPS_URL", "https://alodokter.com")
        # Multi-sumber tips (koma-separated). Bila di-set, menimpa crawl_tips_url tunggal.
        self.crawl_tips_urls: list[str] = [
            u.strip()
            for u in os.getenv(
                "CRAWL_TIPS_URLS",
                "https://www.alodokter.com,https://hellosehat.com/rambut/,"
                "https://www.halodoc.com/artikel/tag/rambut,https://www.healthline.com/health/hair-loss",
            ).split(",")
            if u.strip()
        ]

        # --- Agent Admin (RAG + tool-call ke Express API) ---
        # Base URL Express API untuk tool-call data live & serialisasi katalog.
        self.api_base_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1:4000")
        # Token internal (shared secret) supaya apps/ai boleh memanggil API internal.
        self.agent_internal_token: str | None = os.getenv("AI_INTERNAL_TOKEN") or None
        # Nama koleksi ChromaDB untuk katalog (hasil serialize DB).
        self.rag_catalog_topic: str = os.getenv("RAG_CATALOG_TOPIC", "katalog")
        # Production is opt-in; legacy development defaults remain supported.
        self.production: bool = any(
            os.getenv(name, '').strip().lower() == 'production'
            for name in ('AI_ENV', 'NODE_ENV', 'ENVIRONMENT')
        )
        self.validate_runtime()

    @property
    def legacy_maintenance_enabled(self) -> bool:
        return not self.production and self.rag_retrieval_provider == 'chroma'

    def validate_runtime(self) -> None:
        """Reject unsafe production settings without reporting secret values."""
        if not self.production:
            return
        token = self.agent_internal_token or ''
        compact = token.lower().replace('-', '').replace('_', '').replace(' ', '')
        if (len(token) < 32 or len(set(token)) < 8
                or any(ord(char) < 33 or ord(char) > 126 for char in token) or any(
            word in compact for word in ('changeme', 'replaceme', 'example', 'placeholder', 'yourtoken')
        )):
            raise ValueError('AI_INTERNAL_TOKEN must be a strong secret of at least 32 characters')
        required = {
            'AI_LLM_PROVIDER': self.ai_llm_provider == 'chatgpt',
            'AI_CHATGPT_MODEL': bool(self.chatgpt_model),
            'RAG_RETRIEVAL_PROVIDER': self.rag_retrieval_provider == 'bm25_source_balanced',
            'RAG_LIVE_SERVICES': self.rag_live_services,
            'RAG_RUNTIME_CORPUS_FILE': self.rag_runtime_corpus_file is not None,
            'RAG_CONTEXT_SELECTION': self.rag_context_selection == 'source_scoped',
        }
        for name, valid in required.items():
            if not os.getenv(name, '').strip() or not valid:
                raise ValueError(f'{name} must be explicitly configured for the production RAG profile')
        if (not 1 <= self.rag_top_k <= 20
                or self.rag_context_strategy not in {'head', 'query_window'}
                or not 0 < self.rag_generation_timeout_seconds <= 60):
            raise ValueError('Invalid production RAG retrieval or generation limits')
        from urllib.parse import urlsplit
        target = urlsplit(self.api_base_url)
        if (target.scheme not in {'http', 'https'} or not target.hostname
                or target.username or target.password or target.query or target.fragment):
            raise ValueError('API_BASE_URL must be an HTTP(S) origin without credentials')


settings = Settings()
