"""Reproducible ambiguity route/evidence checks; no LLM quality claims."""
import argparse
import asyncio
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import httpx

from app.config import settings,BASE_DIR
from app.rag.rag_service import RagService


CASES=[
    ('generic','Bagaimana memakai conditioner?','policy_clarification',None,None),
    ('dry','Bagaimana memakai kondisioner untuk rambut kering?','policy_clarification',None,None),
    ('rinse_question','Apakah conditioner tidak perlu dibilas?','policy_clarification',None,None),
    ('mixed','Berapa harga Signature Hair Spa dan cara memakai conditioner?','policy_clarification',None,None),
    ('unknown_service','Berapa harga Diamond Hair Therapy dan cara memakai kondisioner?','policy_clarification',None,None),
    ('pronoun_product','Produk ini boleh dipakai setiap hari?','policy_clarification',None,None),
    ('pronoun_treatment','Setelah treatment itu kapan boleh keramas?','policy_clarification',None,None),
    ('rinse_explicit','Bagaimana memakai conditioner bilas untuk rambut kering?','offline_extracts','conditioner-by-hair-type','leave-in-placement'),
    ('leave_in_explicit','Bagaimana memakai kondisioner tanpa bilas?','offline_extracts','leave-in-placement','conditioner-by-hair-type'),
    ('leave_in_english','Bagaimana memakai leave in conditioner?','offline_extracts','leave-in-placement','conditioner-by-hair-type'),
    ('catalog','Berapa harga dan durasi Volume Blowout Styling?','catalog_lookup',None,None),
    ('unavailable_sop','Setelah keratin boleh keramas kapan?','policy_unavailable',None,None),
    ('prescription','Berapa dosis obat resep untuk ketombe?','policy_unavailable',None,None),
]


async def run(check_http):
    attributes=('ai_llm_provider','rag_corpus_file','rag_retrieval_provider','rag_context_selection')
    original={key:getattr(settings,key) for key in attributes}
    rows=[]
    try:
        settings.ai_llm_provider='local'
        settings.rag_corpus_file=BASE_DIR/'rag/eval/curated-development-v2/corpus.json'
        settings.rag_retrieval_provider='bm25_source_balanced'
        settings.rag_context_selection='source_scoped'
        for case,query,route,required,forbidden in CASES:
            response=await RagService().answer(query,include_trace=True,allow_web=False,live_services=False)
            trace=response['_trace'];ids=[d['id'] for d in trace.get('retrieved_docs',[])]
            passed=(trace['generation_status']==route and (not required or any(required in i for i in ids))
                and (not forbidden or all(forbidden not in i for i in ids)))
            rows.append(dict(id=case,question=query,expected_route=route,passed=passed,response=response))
    finally:
        for key,value in original.items():setattr(settings,key,value)
    http_rows=[]
    if check_http:
        async with httpx.AsyncClient(timeout=15,trust_env=False) as client:
            # These are deliberately deterministic; no live generative case is sent.
            for case,query,route,_,_ in CASES:
                if route!='policy_clarification':continue
                response=await client.post(settings.api_base_url.rstrip('/')+'/api/chat',json={'message':query})
                data=response.json().get('data',{}) if response.status_code==200 else {}
                reply=data.get('reply','')
                passed=response.status_code==200 and ('yang mana' in reply or 'kondisioner bilas' in reply)
                if case=='mixed':passed=passed and 'Rp325.000' in reply
                if case=='unknown_service':passed=passed and 'Rp' not in reply
                http_rows.append(dict(id=case,status_code=response.status_code,passed=passed,response=data))
    return dict(executed_at_utc=datetime.now(timezone.utc).isoformat(),
        protocol='ambiguity_development_route_audit_v1',model_calls=0,
        checks=len(rows)+len(http_rows),passed=sum(r['passed'] for r in rows+http_rows),
        independent_test=False,human_semantic_approval=False,answer_generation_quality_scored=False,
        limitations=['Finite development cases; natural-language ambiguity cannot be exhaustively eliminated.',
                     'Explicit-type paths use offline extracts; generated answer meaning is not measured.',
                     'HTTP checks use current live catalog; snapshot price checks assume the listed service price has not changed.'],
        implementation_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
        offline_results=rows,http_results=http_rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--check-http',action='store_true')
    args=parser.parse_args()
    if args.out.exists():raise ValueError('Use a new report file')
    result=asyncio.run(run(args.check_http))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('checks','passed','model_calls')}))
    if result['passed']!=result['checks']:raise SystemExit(2)


if __name__=='__main__':main()
