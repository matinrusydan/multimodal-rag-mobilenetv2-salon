"""Offline algorithm exploration on the frozen development pilot; no production writes.

Run from apps/ai: python -m app.rag.algorithm_trial --help
Rules and parameters are exploratory, not a validated general-purpose intent parser.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re

from app.rag.pilot import DEFAULT_OUT, bm25_scores, metrics, sha, tokens

STOP = set('berapa apa dan serta yang di ke pada untuk menurut isi panduan tercatat reguler atau itu seperti mana siapa dengan apakah masih dari saya'.split())
BUSINESS = set('harga biaya durasi menit promo diskon'.split())
CARE = re.compile(r'perawatan|merawat|kondisioner|sampo|keramas|menyisir|bercabang|kering|kusam|rontok|kerontokan|kulit kepala|pewarnaan|stylist|perih|obat|resep')
METHODS = ('bm25', 'bm25_clean', 'bm25_mmr', 'bm25_decomposed_rrf', 'bm25_routed', 'bm25_routed_decomposed')


def clean(query: str) -> str:
    return ' '.join(t for t in tokens(query) if t not in STOP)


def plan(query: str, corpus: list[dict]) -> dict:
    # Catalog names are input data, not answer labels. No query IDs/categories enter here.
    residual = query.casefold()
    for name in sorted((d['fields']['name'] for d in corpus if d['source_type'] == 'db'), key=len, reverse=True):
        residual = re.sub(re.escape(name.casefold()), ' ', residual)
    business = bool(set(tokens(query)) & BUSINESS)
    care = bool(CARE.search(residual))
    care_query = ' '.join(t for t in tokens(residual) if t not in STOP | BUSINESS)
    return {'business': business, 'document': care,
            'original_query': query, 'document_query': care_query or clean(query)}


def rank(scores: list[float], corpus: list[dict]) -> list[int]:
    return sorted(range(len(corpus)), key=lambda i: (-scores[i], corpus[i]['id']))


def rrf(orders: list[list[int]], corpus: list[dict]) -> list[int]:
    scores: Counter = Counter()
    for order in orders:
        for position, index in enumerate(order, 1):
            scores[index] += 1 / (60 + position)
    return sorted(scores, key=lambda i: (-scores[i], corpus[i]['id']))


def mmr(order: list[int], relevance: list[float], texts: list[str], corpus: list[dict], k: int) -> list[int]:
    # Lexical TF-IDF cosine redundancy, not a neural embedding or semantic MMR.
    bags = [Counter(tokens(t)) for t in texts]
    df = Counter(t for b in bags for t in b)
    vectors = [{t: n * (math.log((1 + len(bags)) / (1 + df[t])) + 1) for t, n in b.items()} for b in bags]
    norms = [math.sqrt(sum(v*v for v in b.values())) or 1 for b in vectors]

    def sim(a, b):
        return sum(v * vectors[b].get(t, 0) for t, v in vectors[a].items()) / (norms[a] * norms[b])

    chosen = []
    ceiling = max(relevance, default=1) or 1
    remaining = set(order)
    while remaining and len(chosen) < k:
        best = min(remaining, key=lambda i: (-(0.7 * relevance[i] / ceiling - 0.3 * max((sim(i,j) for j in chosen), default=0)), corpus[i]['id']))
        chosen.append(best)
        remaining.remove(best)
    return chosen


def select(query: str, corpus: list[dict], k: int = 5) -> tuple[dict[str, list[int]], dict]:
    if k < 1:
        raise ValueError('k must be positive')
    texts = [d['section'] + '\n' + d['text'] for d in corpus]
    original_scores = bm25_scores(query, texts)
    original = rank(original_scores, corpus)
    route = plan(query, corpus)
    document = rank(bm25_scores(route['document_query'], texts), corpus)
    orders = {'bm25': original[:k], 'bm25_clean': rank(bm25_scores(clean(query), texts), corpus)[:k],
              'bm25_mmr': mmr(original, original_scores, texts, corpus, k),
              'bm25_decomposed_rrf': rrf([original, document] if route['document'] else [original], corpus)[:k]}
    for method, document_order in [('bm25_routed', original), ('bm25_routed_decomposed', document)]:
        reserved = []
        # Reserve one slot per detected source need, then fill by original BM25.
        # At k=1 business takes priority; the unresolved document need remains measurable.
        if route['business']:
            reserved += [i for i in original if corpus[i]['source_type'] == 'db'][:1]
        if route['document']:
            reserved += [i for i in document_order if corpus[i]['source_type'] != 'db'][:1]
        orders[method] = list(dict.fromkeys(reserved + original))[:k]
    return orders, route


def run(corpus: list[dict], questions: list[dict], k: int = 5) -> dict:
    rows = []
    for question in questions:
        selections, route = select(question['question'], corpus, k)
        # Reference labels are consulted only after selection.
        for method, indices in selections.items():
            chosen = [corpus[i] for i in indices]
            rows.append({'id': question['id'], 'category': question['category'], 'method': method, 'plan': route,
                         'selected_ids': [d['id'] for d in chosen],
                         'contexts': [{'id': d['id'], 'source_type': d['source_type'], 'section': d['section'], 'snippet': d['text'][:400]} for d in chosen],
                         'metrics': metrics([d['id'] for d in chosen], question['relevant_evidence_ids'], question['required_evidence_groups'])})
    summary = {}
    for method in METHODS:
        summary[method] = {}
        for category in ('all', 'database', 'document', 'mixed', 'difficult'):
            subset = [r for r in rows if r['method'] == method and (category == 'all' or r['category'] == category)]
            scored = [r for r in subset if r['metrics']['recall'] is not None]
            summary[method][category] = {'total': len(subset), 'scored': len(scored), **{
                key: sum(r['metrics'][key] for r in scored)/len(scored) if scored else None
                for key in ('precision', 'recall', 'f1', 'complete_evidence')}}
    return {'protocol': 'exploratory_development_only_not_confirmatory', 'top_k': k, 'max_chars_per_context': 400,
            'input_hashes': {'corpus': sha(json.dumps(corpus, sort_keys=True)), 'questions': sha(json.dumps(questions, sort_keys=True))},
            'config': {'bm25_k1': 1.5, 'bm25_b': 0.75, 'rrf_constant': 60, 'mmr_lambda': 0.7,
                       'stopwords': sorted(STOP), 'business_terms': sorted(BUSINESS), 'care_pattern': CARE.pattern,
                       'rules_selected_after_baseline_error_inspection': True, 'parameter_search': False},
            'limitations': ['Same development queries used to diagnose and propose rules; selection bias expected.',
                            'Gold passage IDs pending human review; metrics do not verify every clipped claim.',
                            'Source reservation alone does not validate evidence relevance, resolve conflicts or enforce generation.',
                            'All methods score the same 51-item corpus; additional BM25 passes differ in work.',
                            'No LLM, neural dense retrieval, live SQL or abstention evaluation.'],
            'summary': summary, 'results': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT.parent/'algorithm-trial')
    parser.add_argument('--top-k', type=int, default=5)
    args = parser.parse_args()
    corpus = json.loads((args.input/'corpus.json').read_text(encoding='utf-8'))
    questions = json.loads((args.input/'questions.json').read_text(encoding='utf-8'))
    report = run(corpus, questions, args.top_k)
    if args.out.resolve() == args.input.resolve():
        parser.error('Output must differ from frozen pilot directory')
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# Eksplorasi algoritma retrieval', '', 'Data development: 24 pertanyaan draft, 51 evidence; belum divalidasi manusia. Bukan hasil pengujian akhir.', '',
             '| Metode | Kelompok | N dinilai/total | Precision | Recall | F1 retrieval | Bukti lengkap |', '|---|---|---|---|---|---|---|']
    for method, groups in report['summary'].items():
        for group, scores in groups.items():
            values = ' | '.join('NA' if scores[m] is None else f'{scores[m]:.3f}' for m in ('precision','recall','f1','complete_evidence'))
            lines.append(f"| {method} | {group} | {scores['scored']}/{scores['total']} | {values} |")
    lines += ['', 'Semua metode top-5, cuplikan maksimal 400 karakter per evidence. Metrik menghitung ID evidence draft, bukan kualitas jawaban atau dukungan klaim setelah pemotongan.',
              'Query ambigu/tanpa bukti (3/24) tidak memiliki skor retrieval; tidak dianggap berhasil. Aturan diusulkan setelah inspeksi kegagalan baseline, sehingga kenaikan pada data ini rentan bias seleksi.',
              'BM25 MMR memakai kemiripan leksikal TF-IDF. Decomposed RRF menggabungkan dua ranking BM25, bukan BM25 + neural dense. Routing berbasis aturan, bukan classifier terlatih.',
              'Tidak ada API, generasi jawaban, perubahan database atau index produksi. Lihat report.json untuk parameter, hash input, rencana routing, dan seluruh konteks.']
    (args.out/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
