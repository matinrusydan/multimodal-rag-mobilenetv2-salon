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


settings = Settings()