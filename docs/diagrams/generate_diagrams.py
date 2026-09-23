# -*- coding: utf-8 -*-
"""generate_diagrams.py — Menghasilkan diagram arsitektur/alur untuk dokumentasi TA.

Output (docs/diagrams/):
  1. cv_pipeline_flowchart      — Flowchart pipeline CV (gate -> type -> length)
  2. rag_flowchart              — Flowchart alur RAG (ingest & query)
  3. sequence_chat_rag          — Sequence diagram chat RAG
  4. sequence_analyze_cv        — Sequence diagram analisis foto CV
  5. system_architecture        — Arsitektur sistem (web/api/ai/db)

Requires:
  - Python package `graphviz` (pip install graphviz)
  - Graphviz binary `dot` terpasang di PATH.

Jalankan:
  cd apps/ai
  .venv\\Scripts\\python.exe ..\\..\\docs\\diagrams\\generate_diagrams.py
  (atau: python docs/diagrams/generate_diagrams.py dari root)
"""

from __future__ import annotations

from pathlib import Path

from graphviz import Digraph

OUT = Path(__file__).resolve().parent


def _render(g: Digraph, name: str) -> None:
    for fmt in ("png", "svg"):
        g.format = fmt
        g.render(filename=name, directory=str(OUT), cleanup=True)
    print(f"  ok: {name}.png / {name}.svg")


def cv_pipeline_flowchart() -> None:
    g = Digraph("cv_pipeline", comment="Pipeline Computer Vision")
    g.attr(rankdir="TB", fontname="Helvetica", bgcolor="white")
    g.attr("node", shape="box", style="rounded,filled", fontname="Helvetica", fontsize="11")
    g.attr("edge", fontname="Helvetica", fontsize="9")

    g.node("input", "Foto rambut (mentah)", fillcolor="#E3F2FD")
    g.node("pre", "Preprocessing\nRGB -> EXIF -> resize 256\n-> center-crop 224\n-> ImageNet norm", fillcolor="#E8F5E9")

    with g.subgraph(name="cluster_gate") as s:
        s.attr(label="TAHAP 0 — Viewpoint Gate (mediapipe)", style="dashed", color="#888")
        s.node("gate", "Prediksi posisi\n(depan / samping / belakang)", fillcolor="#FFF8E1")
        s.node("stop", "STOP: minta foto ulang\n(dari belakang)", shape="box", fillcolor="#FFEBEE")
        s.node("pass", "LOLOS (belakang)", shape="box", fillcolor="#E8F5E9")

    g.node("type", "TAHAP 1 — Hair Type\nCNN (MobileNetV2)\nlurus/bergelombang/\nkeriting/sangat-keriting", fillcolor="#E1F5FE")
    g.node("length", "TAHAP 2 — Hair Length\nCNN / geometris\npendek/pendek-menengah/\nmenengah/panjang", fillcolor="#E1F5FE")
    g.node("out", "Hasil: hairLength + hairType\n(+ features: warna, tekstur, risk)", fillcolor="#F3E5F5")
    g.node("rag", "Diteruskan ke RAG\n(konteks multimodal)", fillcolor="#FCE4EC")

    g.edge("input", "pre")
    g.edge("pre", "gate")
    g.edge("gate", "stop", label="depan/samping")
    g.edge("gate", "pass", label="belakang")
    g.edge("pass", "type")
    g.edge("type", "length")
    g.edge("length", "out")
    g.edge("out", "rag")
    _render(g, "cv_pipeline_flowchart")


def rag_flowchart() -> None:
    g = Digraph("rag_flow", comment="Alur RAG")
    g.attr(rankdir="TB", fontname="Helvetica", bgcolor="white")
    g.attr("node", shape="box", style="rounded,filled", fontname="Helvetica", fontsize="11")
    g.attr("edge", fontname="Helvetica", fontsize="9")

    g.node("kb", "Knowledge base\nrag/knowledge/*.md\n(+ hasil crawl)", fillcolor="#E8F5E9")
    g.node("ingest", "Ingest + Chunking\n(500-1000 token, overlap 100)", fillcolor="#E3F2FD")
    g.node("embed", "Embedding (Gemini)\ngemini-embedding-001 768d", fillcolor="#E3F2FD")
    g.node("chroma", "ChromaDB\n(koleksi per topik)", shape="cylinder", fillcolor="#FFF8E1")

    g.node("query", "Pertanyaan user (+ hairContext CV)", fillcolor="#FCE4EC")
    g.node("qembed", "Embed pertanyaan (Gemini 768d)", fillcolor="#E3F2FD")
    g.node("retrieve", "Retrieve top-k (cosine, merge topik)", fillcolor="#E3F2FD")
    g.node("prompt", "Bangun prompt\n(anti-halusinasi + konteks CV)", fillcolor="#E1F5FE")
    g.node("llm", "Gemini LLM\n(+ fallback offline / web)", fillcolor="#F3E5F5")
    g.node("answer", "Jawaban + sumber", fillcolor="#E8F5E9")

    g.edge("kb", "ingest")
    g.edge("ingest", "embed")
    g.edge("embed", "chroma")
    g.edge("query", "qembed")
    g.edge("qembed", "retrieve")
    g.edge("chroma", "retrieve", style="dashed", label="vektor")
    g.edge("retrieve", "prompt")
    g.edge("prompt", "llm")
    g.edge("llm", "answer")
    _render(g, "rag_flowchart")


def sequence_chat_rag() -> None:
    g = Digraph("seq_chat", comment="Sequence: chat RAG")
    g.attr(rankdir="LR", fontname="Helvetica", bgcolor="white")
    g.attr("node", shape="box", style="filled", fontname="Helvetica", fontsize="10")
    g.attr("edge", fontname="Helvetica", fontsize="9")

    actors = [
        ("web", "Web (Next.js)", "#E3F2FD"),
        ("api", "Express API", "#E8F5E9"),
        ("ai", "FastAPI /ai/chat", "#FFF8E1"),
        ("chroma", "ChromaDB", "#F3E5F5"),
        ("gemini", "Gemini LLM", "#FCE4EC"),
    ]
    for k, label, color in actors:
        g.node(k, label, fillcolor=color)

    g.edge("web", "api", label="POST /api/chat\n{message, hairContext}")
    g.edge("api", "ai", label="POST /ai/chat")
    g.edge("ai", "ai", label="embed query")
    g.edge("ai", "chroma", label="query top-k")
    g.edge("chroma", "ai", label="dokumen relevan", style="dashed")
    g.edge("ai", "gemini", label="generate (prompt+konteks)")
    g.edge("gemini", "ai", label="jawaban", style="dashed")
    g.edge("ai", "api", label="{reply, sources}", style="dashed")
    g.edge("api", "web", label="200 OK", style="dashed")
    _render(g, "sequence_chat_rag")


def sequence_analyze_cv() -> None:
    g = Digraph("seq_cv", comment="Sequence: analisis foto CV")
    g.attr(rankdir="LR", fontname="Helvetica", bgcolor="white")
    g.attr("node", shape="box", style="filled", fontname="Helvetica", fontsize="10")
    g.attr("edge", fontname="Helvetica", fontsize="9")

    actors = [
        ("web", "Web (Next.js)", "#E3F2FD"),
        ("api", "Express API", "#E8F5E9"),
        ("ai", "FastAPI /ai/analyze", "#FFF8E1"),
        ("gate", "Viewpoint Gate\n(mediapipe)", "#E1F5FE"),
        ("cnn", "CNN ONNX\n(type/length)", "#F3E5F5"),
    ]
    for k, label, color in actors:
        g.node(k, label, fillcolor=color)

    g.edge("web", "api", label="POST /api/analyze (multipart image)")
    g.edge("api", "ai", label="POST /ai/analyze")
    g.edge("ai", "gate", label="preprocessing")
    g.edge("gate", "ai", label="belakang / tolak", style="dashed")
    g.edge("ai", "cnn", label="infer (jika belakang)")
    g.edge("cnn", "ai", label="type + length", style="dashed")
    g.edge("ai", "api", label="{hairLength, hairType, features}", style="dashed")
    g.edge("api", "web", label="200 OK", style="dashed")
    _render(g, "sequence_analyze_cv")


def system_architecture() -> None:
    g = Digraph("arch", comment="Arsitektur sistem")
    g.attr(rankdir="TB", fontname="Helvetica", bgcolor="white")
    g.attr("node", shape="box", style="rounded,filled", fontname="Helvetica", fontsize="11")
    g.attr("edge", fontname="Helvetica", fontsize="9")

    with g.subgraph(name="cluster_client") as c:
        c.attr(label="Client", style="dashed", color="#888")
        c.node("web", "Next.js Web (:3000)\nLanding + Admin", fillcolor="#E3F2FD")

    with g.subgraph(name="cluster_api") as c:
        c.attr(label="Backend", style="dashed", color="#888")
        c.node("api", "Express API (:4000)\nRBAC + Proxy", fillcolor="#E8F5E9")
        c.node("pg", "PostgreSQL (:5432)\nservices, users, RBAC, settings", shape="cylinder", fillcolor="#FFF8E1")

    with g.subgraph(name="cluster_ai") as c:
        c.attr(label="Brain Engine (FastAPI :5000)", style="dashed", color="#888")
        c.node("cv", "CV\nMediaPipe gate + ONNX CNN", fillcolor="#E1F5FE")
        c.node("rag", "RAG\nChromaDB + Gemini", fillcolor="#F3E5F5")
        c.node("crawl", "Crawler\nCrawl4AI", fillcolor="#FCE4EC")

    g.edge("web", "api", label="REST")
    g.edge("api", "pg", label="Knex")
    g.edge("api", "cv", label="proxy /ai/analyze")
    g.edge("api", "rag", label="proxy /ai/chat, /ai/agent")
    g.edge("rag", "crawl", label="web fallback / ingest", style="dashed")
    _render(g, "system_architecture")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Generate diagram -> {OUT}")
    cv_pipeline_flowchart()
    rag_flowchart()
    sequence_chat_rag()
    sequence_analyze_cv()
    system_architecture()
    print("SELESAI (5 diagram x PNG+SVG).")


if __name__ == "__main__":
    main()
