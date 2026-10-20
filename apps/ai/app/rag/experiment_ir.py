"""Offline paired IR experiments. No model, network, DB writes or production ingest.

python -m app.rag.experiment_ir --out rag/eval/ir-experiment-v1
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import time
import tracemalloc

from app.rag.lexical_index import BM25Index, corpus_index, ranking_text, cached_index
from app.rag.bm25_retrieval import balanced_order
from app.rag.context_selection import select_context
from app.rag.ir_metrics import evaluate_ranking, NAMES
from app.rag.pilot import bm25_scores

ROOT=Path(__file__).resolve().parents[4]
METHODS=('bm25_scan','bm25_indexed','bm25_allocated_no_decomposition','bm25_source_balanced')


def implementation_hashes():
    folder=Path(__file__).resolve().parent
    return {name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in
            ('experiment_ir.py','lexical_index.py','bm25_retrieval.py','query_planning.py',
             'context_selection.py','ir_metrics.py','pilot.py','eval_rag.py')}


def rss_bytes():
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class Memory(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in
                ('peak_rss','rss','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype=ctypes.c_void_p
        psapi=ctypes.WinDLL('psapi',use_last_error=True)
        fn=psapi.GetProcessMemoryInfo
        fn.argtypes=[ctypes.c_void_p,ctypes.POINTER(Memory),wintypes.DWORD]
        info=Memory();info.cb=ctypes.sizeof(info)
        return info.rss if fn(kernel.GetCurrentProcess(),ctypes.byref(info),info.cb) else None
    path=Path('/proc/self/statm')
    if path.exists():return int(path.read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
    return None


def percentile(values,p):
    values=sorted(values)
    if not values:return None
    index=(len(values)-1)*p
    lo=math.floor(index);hi=math.ceil(index)
    return values[lo]+(values[hi]-values[lo])*(index-lo)


def rank(method,query,corpus,index,texts,k):
    if method=='bm25_scan':scores=bm25_scores(query,texts)
    else:scores=index.scores(query)
    if method in {'bm25_source_balanced','bm25_allocated_no_decomposition'}:
        return balanced_order(query,corpus,k,index=index,scores=scores,
                              decompose=method=='bm25_source_balanced')
    return sorted(range(len(corpus)),key=lambda i:(-scores[i],corpus[i]['id']))[:k]


def validate_package(folder):
    from app.rag import eval_rag
    previous=(eval_rag.TESTSET_FILE,eval_rag.DATASET_PROVENANCE)
    try:
        eval_rag.TESTSET_FILE=folder/'questions.json'
        questions=eval_rag.load_testset()
        provenance=eval_rag.DATASET_PROVENANCE
    finally:
        eval_rag.TESTSET_FILE,eval_rag.DATASET_PROVENANCE=previous
    return json.loads((folder/'corpus.json').read_text(encoding='utf-8')),questions,provenance


def experiment(corpus,questions,k=5):
    texts=[ranking_text(d) for d in corpus]
    index=BM25Index(texts)
    rows=[]
    for q in questions:
        baseline=None
        for method in METHODS:
            selected=rank(method,q['question'],corpus,index,texts,k)
            if method=='bm25_scan':baseline=selected
            if method=='bm25_indexed' and selected!=baseline:
                raise AssertionError('Index changed the baseline ranking: '+q['id'])
            ids=[corpus[i]['id'] for i in selected]
            metrics=evaluate_ranking(ids,q['relevant_evidence_ids'],q['required_evidence_groups'],k)
            for strategy in ('head','query_window'):
                contexts=[dict(id=corpus[i]['id'],**select_context(corpus[i]['text'],q['question'],400,strategy)) for i in selected]
                rows.append(dict(id=q['id'],category=q['category'],method=method,context_strategy=strategy,
                                 metrics=metrics,retrieved_ids=ids,contexts=contexts,
                                 context_characters=sum(len(c['text']) for c in contexts),
                                 semantic_support_after_windowing='not_scored_no_human_span_labels',
                                 generation_status='not_run',answer_metrics=None))
    summary={}
    for method in METHODS:
        summary[method]={}
        for category in ['all']+sorted({q['category'] for q in questions}):
            # Retrieval is identical across context strategies; do not count a
            # question twice or attribute a ranking gain to snippet selection.
            subset=[r for r in rows if r['method']==method and r['context_strategy']=='head'
                    and (category=='all' or r['category']==category)]
            entry={'total':len(subset),'scored':sum(r['metrics']['recall_at_k'] is not None for r in subset)}
            for name in NAMES:
                values=[r['metrics'][name] for r in subset if r['metrics'][name] is not None]
                entry[name]=statistics.mean(values) if values else None
            entry['map_at_k']=entry['average_precision_at_k']
            entry['mrr_at_k']=entry['reciprocal_rank_at_k']
            summary[method][category]=entry
    return rows,summary


def paired_intervals(rows,seed=42,repeats=1000):
    baseline={r['id']:r['metrics'] for r in rows if r['method']=='bm25_indexed' and r['context_strategy']=='head'}
    out={}
    for method in METHODS:
        if method=='bm25_indexed':continue
        subset=[r for r in rows if r['method']==method and r['context_strategy']=='head']
        out[method]={}
        for metric in ('recall_at_k','complete_evidence','average_precision_at_k'):
            differences=[r['metrics'][metric]-baseline[r['id']][metric] for r in subset if r['metrics'][metric] is not None]
            if not differences:continue
            rng=random.Random(seed)
            samples=[statistics.mean(rng.choices(differences,k=len(differences))) for _ in range(repeats)]
            out[method][metric]=dict(pairs=len(differences),mean_delta=statistics.mean(differences),
                bootstrap_percentile_95=[percentile(samples,.025),percentile(samples,.975)])
    return out


def benchmark(corpus,query,repeats=10,multipliers=(1,10,100),k=5):
    results=[]
    for multiplier in multipliers:
        expanded=[dict(d,id=d['id']+f':replica:{j}') for j in range(multiplier) for d in corpus]
        texts=[ranking_text(d) for d in expanded]
        rss_before=rss_bytes()
        start=time.perf_counter_ns();index=BM25Index(texts);build_ms=(time.perf_counter_ns()-start)/1e6
        # Memory profiling is separate: tracing overhead is excluded from timing.
        tracemalloc.start()
        measured=BM25Index(texts)
        index_bytes,index_peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        del measured
        timing={}
        cached_index.cache_clear();corpus_index(expanded)
        for method in METHODS:
            values=[]
            # A first call is not a cloud cold start. Label it accurately.
            for _ in range(repeats):
                start=time.perf_counter_ns()
                current=corpus_index(expanded) if method!='bm25_scan' else index
                rank(method,query,expanded,current,texts,k)
                values.append((time.perf_counter_ns()-start)/1e6)
            timing[method]=dict(median_ms=statistics.median(values),p95_ms=percentile(values,.95),
                                samples_ms=values)
        results.append(dict(evidence_count=len(expanded),multiplier=multiplier,index_build_ms=build_ms,
                            python_index_retained_bytes=index_bytes,python_index_peak_bytes=index_peak,
                            process_rss_before_bytes=rss_before,process_rss_after_bytes=rss_bytes(),
                            timing=timing))
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'apps/ai/rag/eval/curated-development-v2')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--top-k',type=int,default=5)
    parser.add_argument('--repeats',type=int,default=10)
    args=parser.parse_args()
    if args.top_k<1 or args.repeats<3:parser.error('top-k must be positive; at least 3 timing repetitions required')
    if args.out.exists():parser.error('Use a new output directory; existing reports are preserved')
    software=implementation_hashes()
    corpus,questions,provenance=validate_package(args.input)
    rows,summary=experiment(corpus,questions,args.top_k)
    report=dict(protocol='ir_component_experiment_v1',input=provenance,publication_ready=False,
        top_k=args.top_k,methods=METHODS,ndcg_gain='2**grade-1; binary known relevance in this package',
        ap_denominator='all known relevant IDs, including those outside top-k',
        corpus_size=len(corpus),question_count=len(questions),summary=summary,results=rows,
        paired_vs_indexed=paired_intervals(rows),bootstrap_seed=42,bootstrap_repetitions=1000,
        benchmark=benchmark(corpus,'Berapa harga Signature Hair Spa dan bagaimana memakai kondisioner untuk rambut kering?',args.repeats,k=args.top_k),
        executed_at_utc=datetime.now(timezone.utc).isoformat(),implementation_sha256=software,
        environment=dict(python=platform.python_version(),platform=platform.platform(),
                         processor=platform.processor(),logical_cpu_count=os.cpu_count()),
        limitations=['Development-only; no locked held-out test or independent graded judgments.',
                     'Timing uses duplicated texts, preloaded corpus and warm process; not deployed app cold start or concurrency.',
                     'RSS is a whole-process reading, not per-method peak memory; tracemalloc reports Python index allocations only.',
                     'No database/network/generator calls; no generated answer, faithfulness or citation-entailment scores.',
                     'Snippet strategies have identical retrieval labels; semantic evidence survival requires span annotation.',
                     'Paired intervals describe this small selected development set, not general improvement or significance.'])
    # Refuse to publish a report if inputs changed during the experiment.
    for name,digest in provenance['input_sha256'].items():
        if hashlib.sha256((args.input/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Input changed during experiment: '+name)
    if implementation_hashes()!=software:raise ValueError('Implementation changed during experiment')
    args.out.mkdir(parents=True)
    output=args.out/'report.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Eksperimen komponen IR v1','', 'Development, bukan hasil publikasi final. Tidak ada panggilan model atau database.','',
           '| Metode | P@k ketat | Recall@k | F1@k | MAP@k | MRR@k | nDCG@k biner | Bukti lengkap |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for method in METHODS:
        s=summary[method]['all']
        lines.append('| '+method+' | '+' | '.join(f'{s[n]:.4f}' for n in
           ('precision_at_k','recall_at_k','f1_at_k','map_at_k','mrr_at_k','ndcg_at_k','complete_evidence'))+' |')
    lines+=['','## Pengukuran komputasi lokal sintetis','',
            '| Evidence | Bangun indeks ms | Scan median ms | Indexed median ms | Source-balanced median ms | Alokasi indeks Python KiB |',
            '|---|---:|---:|---:|---:|---:|']
    for b in report['benchmark']:
        lines.append(f"| {b['evidence_count']} | {b['index_build_ms']:.3f} | {b['timing']['bm25_scan']['median_ms']:.3f} | {b['timing']['bm25_indexed']['median_ms']:.3f} | {b['timing']['bm25_source_balanced']['median_ms']:.3f} | {b['python_index_retained_bytes']/1024:.1f} |")
    lines+=['','## Batas interpretasi','']+['- '+s for s in report['limitations']]
    (args.out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(output),'summary':summary['bm25_source_balanced']['all']},indent=2))


if __name__=='__main__':main()
