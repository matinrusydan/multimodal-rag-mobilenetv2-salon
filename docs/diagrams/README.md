# Diagram Arsitektur & Alur

Diagram untuk dokumentasi TA (CV & RAG), dibuat dengan **Graphviz** via `generate_diagrams.py`.

## Daftar Diagram

| File | Isi |
|---|---|
| `cv_pipeline_flowchart.png/svg` | **Flowchart** pipeline CV (preprocessing → gate → hair type → hair length) |
| `rag_flowchart.png/svg` | **Flowchart** alur RAG (ingest & query) |
| `sequence_chat_rag.png/svg` | **Sequence diagram** chat RAG (Web → API → AI → Chroma → Gemini) |
| `sequence_analyze_cv.png/svg` | **Sequence diagram** analisis foto CV (Web → API → AI → gate → CNN) |
| `system_architecture.png/svg` | **Arsitektur sistem** (Next.js / Express / FastAPI / PostgreSQL / ChromaDB) |

## Regenerasi

Prasyarat:
- Python package `graphviz`: `pip install graphviz`
- Graphviz binary (`dot`) terpasang di PATH. Cek: `dot -V`

Jalankan:

```bash
# dari root
apps\ai\.venv\Scripts\python.exe docs\diagrams\generate_diagrams.py

# atau dari apps/ai
.venv\Scripts\python.exe ..\..\docs\diagrams\generate_diagrams.py
```

Output PNG + SVG ditulis ke folder ini.
