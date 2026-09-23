"""RAG Evaluation Module — LLM-as-judge evaluation for RAG pipeline.

Mengimplementasikan 4 metrik RAGAS (faithfulness, answer relevancy,
context precision, context recall) menggunakan Gemini sebagai judge LLM,
tanpa dependency library RAGAS eksternal.

Metrik:
1. Faithfulness — seberapa setia jawaban terhadap konteks yang diretrieve (0-1)
2. Answer Relevancy — seberapa relevan jawaban terhadap pertanyaan (0-1)
3. Context Precision — seberapa presisi konteks yang diretrieve (0-1)
4. Context Recall — seberapa lengkap konteks relevan yang diretrieve (0-1)

Cara pakai:
    cd apps/ai
    .venv\\Scripts\\python.exe -m app.rag.eval_rag
    .venv\\Scripts\\python.exe -m app.rag.eval_rag --limit 10  # eval 10 Q&A pertama

Output:
    apps/ai/rag/eval/ragas_report.json
    apps/ai/rag/eval/ragas_report.md
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Setup path agar bisa import app modules
BASE_DIR = Path(__file__).resolve().parents[2]  # apps/ai/
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_rag")

# Force UTF-8 untuk Windows console
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Paths
EVAL_DIR = BASE_DIR / "rag" / "eval"
TESTSET_FILE = EVAL_DIR / "testset.json"
REPORT_JSON = EVAL_DIR / "ragas_report.json"
REPORT_MD = EVAL_DIR / "ragas_report.md"


# ─────────────────────────────────────────────────────────────────────────────
# 1) Load test set
# ─────────────────────────────────────────────────────────────────────────────

def load_testset() -> list[dict]:
    """Load Q&A test set dari testset.json."""
    data = json.loads(TESTSET_FILE.read_text(encoding="utf-8"))
    logger.info("Test set loaded: %d Q&A pairs", len(data))
    return data


# ─────────────────────────────────────────────────────────────────────────────
# 2) Run RAG pipeline pada test set
# ─────────────────────────────────────────────────────────────────────────────

async def run_rag_pipeline(question: str) -> dict:
    """Jalankan RAG pipeline pada satu pertanyaan.

    Returns: {"answer": str, "retrieved_docs": list[dict], "contexts": list[str]}
    """
    from app.rag.rag_service import RagService, retriever
    from app.rag.embedding import embed

    # 1. Embed query
    query_embedding = (await embed([question]))[0]

    # 2. Retrieve documents (cosine-similarity via ChromaDB)
    docs = await retriever.retrieve(query_embedding, top_k=5)
    contexts = [d.snippet for d in docs if d.snippet]
    retrieved_docs = [
        {"file": d.file, "section": d.section, "snippet": d.snippet, "distance": d.distance}
        for d in docs
    ]

    # 3. Generate answer via RagService (uses prompt_builder + Gemini)
    svc = RagService()
    try:
        result = await svc.answer(question, hair_context=None, hair_features=None)
        if isinstance(result, dict):
            answer = result.get("answer") or result.get("reply") or ""
        else:
            answer = str(result)
    except Exception as exc:
        logger.warning("  RAG answer error: %s", str(exc)[:100])
        answer = ""

    return {
        "question": question,
        "answer": answer,
        "retrieved_docs": retrieved_docs,
        "contexts": contexts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3) LLM-as-judge: evaluasi metrik
# ─────────────────────────────────────────────────────────────────────────────

async def llm_judge(prompt: str, model: str = None, max_tokens: int = 100) -> str:
    """Panggil Gemini sebagai judge LLM. Pakai model dari config (fallback chain)."""
    from google import genai
    from app.config import settings
    from app.settings_loader import gemini_api_key

    client = genai.Client(api_key=gemini_api_key())

    # Pakai model dari config, bukan hard-coded
    all_models = [settings.llm_model, *settings.llm_fallback_models]
    if model:
        all_models = [model, *all_models]

    for mdl in all_models:
        try:
            response = await client.aio.models.generate_content(
                model=mdl,
                contents=[prompt],
                config={"temperature": 0.0, "max_output_tokens": max_tokens},
            )
            text = (response.text or "").strip()
            if text:
                return text
            logger.warning("LLM judge %s: respons kosong", mdl)
        except Exception as exc:
            logger.warning("LLM judge %s error: %s", mdl, str(exc)[:80])
            continue

    return ""


def parse_score(text: str) -> float:
    """Parse score 0-1 dari response LLM judge. Cari pola 'SKOR:' dulu."""
    import re
    # Cari pola "SKOR: X.X" atau "SKOR: X" (case insensitive)
    score_match = re.search(r"SKOR\s*[:\s]\s*([01](?:\.\d+)?)", text, re.IGNORECASE)
    if score_match:
        score = float(score_match.group(1))
        return max(0.0, min(1.0, score))
    # Fallback: cari angka 0-1 di seluruh teks
    matches = re.findall(r"([01](?:\.\d+)?)", text)
    if matches:
        score = float(matches[0])
        return max(0.0, min(1.0, score))
    return 0.0


async def eval_faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    """Faithfulness: seberapa setia jawaban terhadap konteks yang diretrieve.

    Skor 1.0 = semua klaim dalam jawaban didukung konteks.
    Skor 0.0 = jawaban mengandung halusinasi (klaim tidak ada di konteks).
    """
    context_text = "\n".join(contexts) if contexts else "(tidak ada konteks)"
    prompt = f"""Anda adalah evaluator RAG. Nilai FAITHFULNESS jawaban berikut.

KONTEKS (dokumen yang diretrieve):
{context_text}

PERTANYAAN: {question}
JAWABAN: {answer}

Tugas: Apakah setiap klaim faktual dalam JAWABAN didukung oleh KONTEKS?
- Skor 1.0 jika semua klaim didukung konteks (tidak ada halusinasi).
- Skor 0.5 jika sebagian klaim didukung, sebagian tidak.
- Skor 0.0 jika jawaban mengandung klaim yang sama sekali tidak ada di konteks.

Jawab HANYA dalam format berikut (tanpa teks lain):
SKOR: [angka 0.0-1.0]
ALASAN: [maks 15 kata]"""

    result = await llm_judge(prompt, max_tokens=100)
    return parse_score(result)


async def eval_answer_relevancy(question: str, answer: str) -> float:
    """Answer Relevancy: seberapa relevan jawaban terhadap pertanyaan.

    Skor 1.0 = jawaban langsung menjawab pertanyaan.
    Skor 0.0 = jawaban tidak relevan/menyimpang.
    """
    prompt = f"""Anda adalah evaluator RAG. Nilai ANSWER RELEVANCY jawaban berikut.

PERTANYAAN: {question}
JAWABAN: {answer}

Tugas: Seberapa relevan jawaban terhadap pertanyaan?
- Skor 1.0 jika jawaban langsung menjawab pertanyaan dengan tepat.
- Skor 0.5 jika jawaban sebagian menjawab atau terlalu umum.
- Skor 0.0 jika jawaban tidak relevan atau menyimpang.

Jawab HANYA dalam format berikut (tanpa teks lain):
SKOR: [angka 0.0-1.0]
ALASAN: [maks 15 kata]"""

    result = await llm_judge(prompt, max_tokens=100)
    return parse_score(result)


async def eval_context_precision(question: str, contexts: list[str], ground_truth: str) -> float:
    """Context Precision: seberapa presisi konteks yang diretrieve.

    Skor 1.0 = semua konteks yang diretrieve relevan dengan jawaban yang benar.
    Skor 0.0 = tidak ada konteks yang relevan.
    """
    context_text = "\n".join(contexts) if contexts else "(tidak ada konteks)"
    prompt = f"""Anda adalah evaluator RAG. Nilai CONTEXT PRECISION konteks berikut.

PERTANYAAN: {question}
JAWABAN YANG BENAR (ground truth): {ground_truth}
KONTEKS YANG DIRETRIEVE:
{context_text}

Tugas: Seberapa banyak konteks yang diretrieve benar-benar relevan untuk menjawab pertanyaan?
- Skor 1.0 jika semua konteks relevan dan membantu menjawab.
- Skor 0.5 jika sebagian konteks relevan.
- Skor 0.0 jika tidak ada konteks yang relevan.

Jawab HANYA dalam format berikut (tanpa teks lain):
SKOR: [angka 0.0-1.0]
ALASAN: [maks 15 kata]"""

    result = await llm_judge(prompt, max_tokens=100)
    return parse_score(result)


async def eval_context_recall(question: str, contexts: list[str], ground_truth: str) -> float:
    """Context Recall: seberapa lengkap konteks relevan yang diretrieve.

    Skor 1.0 = konteks mengandung semua info yang dibutuhkan untuk jawaban benar.
    Skor 0.0 = konteks tidak mengandung info yang dibutuhkan.
    """
    context_text = "\n".join(contexts) if contexts else "(tidak ada konteks)"
    prompt = f"""Anda adalah evaluator RAG. Nilai CONTEXT RECALL konteks berikut.

PERTANYAAN: {question}
JAWABAN YANG BENAR (ground truth): {ground_truth}
KONTEKS YANG DIRETRIEVE:
{context_text}

Tugas: Apakah konteks yang diretrieve mengandung semua informasi yang dibutuhkan untuk menjawab pertanyaan?
- Skor 1.0 jika konteks mengandung semua info penting dari jawaban benar.
- Skor 0.5 jika konteks mengandung sebagian info.
- Skor 0.0 jika konteks tidak mengandung info yang dibutuhkan.

Jawab HANYA dalam format berikut (tanpa teks lain):
SKOR: [angka 0.0-1.0]
ALASAN: [maks 15 kata]"""

    result = await llm_judge(prompt, max_tokens=100)
    return parse_score(result)


# ─────────────────────────────────────────────────────────────────────────────
# 4) Orkestrasi evaluasi
# ─────────────────────────────────────────────────────────────────────────────

async def evaluate_one(item: dict) -> dict:
    """Evaluasi satu Q&A pair."""
    qid = item["id"]
    question = item["question"]
    ground_truth = item["ground_truth"]

    logger.info("Evaluating %s: %s", qid, question[:60])

    # 1. Run RAG pipeline
    rag_result = await run_rag_pipeline(question)
    answer = rag_result["answer"]
    contexts = rag_result["contexts"]

    # 2. Evaluate 4 metrics (sequential untuk hindari rate-limit Gemini)
    faithfulness = await eval_faithfulness(question, answer, contexts)
    await asyncio.sleep(1)
    relevancy = await eval_answer_relevancy(question, answer)
    await asyncio.sleep(1)
    ctx_precision = await eval_context_precision(question, contexts, ground_truth)
    await asyncio.sleep(1)
    ctx_recall = await eval_context_recall(question, contexts, ground_truth)

    return {
        "id": qid,
        "topic": item["topic"],
        "question": question,
        "ground_truth": ground_truth,
        "answer": answer,
        "retrieved_docs": rag_result["retrieved_docs"],
        "metrics": {
            "faithfulness": round(faithfulness, 4),
            "answer_relevancy": round(relevancy, 4),
            "context_precision": round(ctx_precision, 4),
            "context_recall": round(ctx_recall, 4),
        },
    }


async def retry_failed():
    """Re-run hanya metrik yang gagal (nilai 0) dari report yang sudah ada.

    Load ragas_report.json, identifikasi metrik yang 0, re-run metrik tersebut
    saja dengan API key/model yang aktif, lalu merge hasilnya.
    """
    import argparse
    from app.config import settings

    if not REPORT_JSON.exists():
        logger.error("Report belum ada: %s. Jalankan full eval dulu.", REPORT_JSON)
        return

    report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    old_results = {r["id"]: r for r in report.get("results", [])}
    testset = {item["id"]: item for item in load_testset()}

    # Cari metrik yang gagal (skor == 0)
    METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    failed_metrics = {}  # {qid: [metric1, metric2, ...]}
    for qid, r in old_results.items():
        m = r.get("metrics", {})
        failed = [metric for metric in METRICS if m.get(metric, 0) == 0]
        if failed:
            failed_metrics[qid] = failed

    if not failed_metrics:
        logger.info("Tidak ada metrik yang gagal (semua non-zero). Tidak perlu re-run.")
        return

    total_retry = sum(len(v) for v in failed_metrics.values())
    logger.info("Ditemukan %d Q&A dengan %d metrik gagal untuk di-re-run",
                len(failed_metrics), total_retry)
    for qid, metrics in failed_metrics.items():
        logger.info("  %s: %s", qid, ", ".join(metrics))

    # Re-run metrik yang gagal
    updates = {}
    for qid, metrics in failed_metrics.items():
        if qid not in testset:
            logger.warning("  %s tidak ada di testset, skip", qid)
            continue

        item = testset[qid]
        question = item["question"]
        ground_truth = item["ground_truth"]
        old = old_results[qid]
        answer = old.get("answer", "")
        contexts = [d.get("snippet", "") for d in old.get("retrieved_docs", []) if d.get("snippet")]

        logger.info("[re-run] %s: %s", qid, ", ".join(metrics))
        updates[qid] = {}

        for metric in metrics:
            try:
                if metric == "faithfulness":
                    score = await eval_faithfulness(question, answer, contexts)
                elif metric == "answer_relevancy":
                    score = await eval_answer_relevancy(question, answer)
                elif metric == "context_precision":
                    score = await eval_context_precision(question, contexts, ground_truth)
                elif metric == "context_recall":
                    score = await eval_context_recall(question, contexts, ground_truth)
                else:
                    score = 0.0
                updates[qid][metric] = round(score, 4)
                logger.info("  %s = %.2f", metric, score)
            except Exception as exc:
                logger.warning("  %s %s error: %s", qid, metric, str(exc)[:80])
                updates[qid][metric] = 0.0
            await asyncio.sleep(1.5)  # jeda antar panggilan judge

        await asyncio.sleep(1)

    # Merge: update hasil lama dengan skor baru
    merged_results = []
    for r in report.get("results", []):
        qid = r["id"]
        if qid in updates:
            for metric, score in updates[qid].items():
                r["metrics"][metric] = score
        merged_results.append(r)

    # Recompute summary
    n = len(merged_results)
    avg_faith = sum(r["metrics"]["faithfulness"] for r in merged_results) / n
    avg_rel = sum(r["metrics"]["answer_relevancy"] for r in merged_results) / n
    avg_prec = sum(r["metrics"]["context_precision"] for r in merged_results) / n
    avg_recall = sum(r["metrics"]["context_recall"] for r in merged_results) / n

    summary = {
        "total_questions": n,
        "avg_faithfulness": round(avg_faith, 4),
        "avg_answer_relevancy": round(avg_rel, 4),
        "avg_context_precision": round(avg_prec, 4),
        "avg_context_recall": round(avg_recall, 4),
        "model_judge": f"{settings.llm_model} (with fallback chain)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "retried_questions": list(updates.keys()),
    }

    full_report = {"summary": summary, "results": merged_results}
    REPORT_JSON.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Regenerate markdown
    md_lines = [
        "# RAG Evaluation Report (LLM-as-judge)",
        "",
        f"**Timestamp:** {summary['timestamp']}",
        f"**Total Questions:** {n}",
        f"**Judge LLM:** {summary['model_judge']}",
        f"**Retried Q&A:** {', '.join(updates.keys())}",
        "",
        "## Summary",
        "",
        "| Metrik | Skor Rata-rata |",
        "|---|---|",
        f"| Faithfulness | {avg_faith:.4f} |",
        f"| Answer Relevancy | {avg_rel:.4f} |",
        f"| Context Precision | {avg_prec:.4f} |",
        f"| Context Recall | {avg_recall:.4f} |",
        "",
        "## Detail per Q&A",
        "",
        "| ID | Topik | Faithfulness | Answer Relevancy | Context Precision | Context Recall |",
        "|---|---|---|---|---|---|",
    ]
    for r in merged_results:
        m = r["metrics"]
        md_lines.append(f"| {r['id']} | {r['topic']} | {m['faithfulness']:.2f} | {m['answer_relevancy']:.2f} | {m['context_precision']:.2f} | {m['context_recall']:.2f} |")
    REPORT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    logger.info("=" * 60)
    logger.info("HASIL RE-RUN EVALUASI RAG")
    logger.info("=" * 60)
    logger.info("Total Q&A: %d", n)
    logger.info("Faithfulness:        %.4f", avg_faith)
    logger.info("Answer Relevancy:    %.4f", avg_rel)
    logger.info("Context Precision:   %.4f", avg_prec)
    logger.info("Context Recall:      %.4f", avg_recall)
    logger.info("=" * 60)


async def main(limit: Optional[int] = None):
    import argparse
    from app.config import settings

    ap = argparse.ArgumentParser(description="RAG Evaluation (LLM-as-judge)")
    ap.add_argument("--limit", type=int, default=None, help="Jumlah Q&A yang dievaluasi (default: all)")
    ap.add_argument("--retry-failed", action="store_true", help="Re-run hanya metrik yang gagal (skor 0)")
    args = ap.parse_args()

    if args.retry_failed:
        await retry_failed()
        return

    logger.info("=" * 60)
    logger.info("RAG Evaluation — LLM-as-judge (Gemini)")
    logger.info("=" * 60)

    testset = load_testset()
    if limit := args.limit:
        testset = testset[:limit]
        logger.info("Limiting to %d Q&A pairs", limit)

    results = []
    for i, item in enumerate(testset, 1):
        logger.info("[%d/%d] %s", i, len(testset), item["id"])
        try:
            result = await evaluate_one(item)
            results.append(result)
            m = result["metrics"]
            logger.info("  faithfulness=%.2f relevancy=%.2f ctx_prec=%.2f ctx_recall=%.2f",
                        m["faithfulness"], m["answer_relevancy"],
                        m["context_precision"], m["context_recall"])
        except Exception as exc:
            logger.error("  Error: %s", str(exc)[:100])
            results.append({
                "id": item["id"],
                "topic": item["topic"],
                "question": item["question"],
                "error": str(exc)[:200],
                "metrics": {"faithfulness": 0, "answer_relevancy": 0, "context_precision": 0, "context_recall": 0},
            })

        # Jeda antar Q&A untuk hindari rate-limit
        await asyncio.sleep(2)

    # Hitung rata-rata
    n = len(results)
    if n == 0:
        logger.error("Tidak ada hasil")
        return

    avg_faith = sum(r["metrics"]["faithfulness"] for r in results) / n
    avg_rel = sum(r["metrics"]["answer_relevancy"] for r in results) / n
    avg_prec = sum(r["metrics"]["context_precision"] for r in results) / n
    avg_recall = sum(r["metrics"]["context_recall"] for r in results) / n

    summary = {
        "total_questions": n,
        "avg_faithfulness": round(avg_faith, 4),
        "avg_answer_relevancy": round(avg_rel, 4),
        "avg_context_precision": round(avg_prec, 4),
        "avg_context_recall": round(avg_recall, 4),
        "model_judge": f"{settings.llm_model} (with fallback chain)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # Save JSON report
    full_report = {"summary": summary, "results": results}
    REPORT_JSON.write_text(json.dumps(full_report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("JSON report: %s", REPORT_JSON)

    # Save Markdown report
    md_lines = [
        "# RAG Evaluation Report (LLM-as-judge)",
        "",
        f"**Timestamp:** {summary['timestamp']}",
        f"**Total Questions:** {n}",
        f"**Judge LLM:** {summary['model_judge']}",
        "",
        "## Summary",
        "",
        "| Metrik | Skor Rata-rata |",
        "|---|---|",
        f"| Faithfulness | {avg_faith:.4f} |",
        f"| Answer Relevancy | {avg_rel:.4f} |",
        f"| Context Precision | {avg_prec:.4f} |",
        f"| Context Recall | {avg_recall:.4f} |",
        "",
        "## Detail per Q&A",
        "",
        "| ID | Topik | Faithfulness | Answer Relevancy | Context Precision | Context Recall |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        m = r["metrics"]
        md_lines.append(f"| {r['id']} | {r['topic']} | {m['faithfulness']:.2f} | {m['answer_relevancy']:.2f} | {m['context_precision']:.2f} | {m['context_recall']:.2f} |")

    REPORT_MD.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info("Markdown report: %s", REPORT_MD)

    # Print summary
    logger.info("=" * 60)
    logger.info("HASIL EVALUASI RAG")
    logger.info("=" * 60)
    logger.info("Total Q&A: %d", n)
    logger.info("Faithfulness:        %.4f", avg_faith)
    logger.info("Answer Relevancy:    %.4f", avg_rel)
    logger.info("Context Precision:   %.4f", avg_prec)
    logger.info("Context Recall:      %.4f", avg_recall)
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
