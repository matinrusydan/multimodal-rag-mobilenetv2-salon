# Build from the repository root: docker build -f apps/ai/Dockerfile .
FROM python:3.13-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHON_DOTENV_DISABLED=1 \
    AI_ENV=production \
    AI_HOST=0.0.0.0 \
    PORT=5000 \
    AI_LLM_PROVIDER=chatgpt \
    RAG_RETRIEVAL_PROVIDER=bm25_source_balanced \
    RAG_LIVE_SERVICES=true \
    RAG_CONTEXT_SELECTION=source_scoped \
    RAG_RUNTIME_CORPUS_FILE=./rag/runtime/curated-care-v1/corpus.json \
    RAG_KNOWLEDGE_DIR=/data/knowledge \
    XDG_DATA_HOME=/data
COPY apps/ai/requirements-rag.lock.txt ./requirements-rag.lock.txt
RUN pip install --no-cache-dir -r requirements-rag.lock.txt \
    && groupadd --gid 10001 salon \
    && useradd --uid 10001 --gid salon --create-home salon \
    && mkdir -p /data/RAGSalon /data/knowledge \
    && chown -R salon:salon /data \
    && chmod 700 /data/RAGSalon
COPY apps/ai/app ./app
COPY apps/ai/rag/runtime ./rag/runtime
USER salon
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ['PORT']+'/ai/health',timeout=3)"
CMD ["sh", "-c", "exec python -m uvicorn app.rag_app:app --host \"$AI_HOST\" --port \"$PORT\""]
