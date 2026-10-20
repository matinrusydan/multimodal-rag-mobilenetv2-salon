"""Report RAG readiness without exposing tokens or performing paid API calls."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path

from app.config import settings
from app.rag.corpus_loader import load_corpus


async def check(check_catalog=False):
    checks=[]
    def record(name,ok,**details):checks.append(dict(name=name,ok=ok,**details))
    record('retrieval_provider',settings.rag_retrieval_provider in {'bm25','bm25_source_balanced'},value=settings.rag_retrieval_provider)
    record('top_k',1<=settings.rag_top_k<=20,value=settings.rag_top_k)
    record('context_strategy',settings.rag_context_strategy in {'head','query_window'},value=settings.rag_context_strategy)
    record('context_selection',settings.rag_context_selection in {'all','source_scoped'},value=settings.rag_context_selection)
    record('generation_deadline',0<settings.rag_generation_timeout_seconds<=60,value_seconds=settings.rag_generation_timeout_seconds)
    record('live_catalog_enabled',settings.rag_live_services)
    path=settings.rag_runtime_corpus_file or settings.rag_corpus_file
    try:
        corpus=load_corpus(path,require_manifest=settings.rag_runtime_corpus_file is not None)
        record('runtime_corpus',bool(corpus),evidence_count=len(corpus),
               business_snapshot_records=sum(d['source_type']=='db' for d in corpus))
    except ValueError:
        record('runtime_corpus',False,reason='Knowledge corpus missing or invalid')
    if settings.ai_llm_provider=='chatgpt':
        from app.rag import chatgpt_plan
        try:available=chatgpt_plan.available()
        except (ValueError,OSError,TypeError,AttributeError):available=False
        record('generation_configuration',bool(settings.chatgpt_model and available),provider='chatgpt',
               model=settings.chatgpt_model,application_session_available=available,
               inference_status='not_tested_no_model_call')
    else:
        record('generation_configuration',False,provider=settings.ai_llm_provider,
               reason='RAG-only profile expects ChatGPT grant; deterministic catalog still operates')
    if check_catalog:
        from app.rag.live_services import load_services
        try:
            rows=await load_services()
            record('catalog_api',True,active_services=len(rows))
        except Exception as exc:
            record('catalog_api',False,error_type=type(exc).__name__)
    return dict(executed_at_utc=datetime.now(timezone.utc).isoformat(),
                status='configuration_ready' if all(c['ok'] for c in checks) else 'needs_attention',
                checks=checks,limitations=['Application session presence is not an inference success.',
                    'No claim about publication readiness, cloud deployment or independent answer accuracy.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-catalog',action='store_true')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    if args.out and args.out.exists():parser.error('Use a new report file')
    result=asyncio.run(check(args.check_catalog))
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['status']!='configuration_ready':raise SystemExit(2)


if __name__=='__main__':main()
