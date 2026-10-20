"""Offline, AI-authored development probes; no independent test/gold claims."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

from app.config import BASE_DIR
from app.rag.catalog_operations import catalog_answer
from app.rag.evidence_selection import select_evidence
from app.rag.lexical_index import corpus_index
from app.rag.bm25_retrieval import balanced_order
from app.rag.service_matching import match_services


PROBES=[
    ('alias','Berapa tarif hair spa?',{'db:services:1'}),
    ('case_spacing','BERAPA harga   Signature Hair Spa?',{'db:services:1'}),
    ('mixed_english','Harga Signature Hair Spa dan cara memakai conditioner?',{'db:services:1'}),
    ('mixed_heat','Tarif Precision Haircut dan tips membatasi panas styling?',{'db:services:2'}),
    ('two_services','Bandingkan harga hair spa dengan scalp detox.',{'db:services:1','db:services:5'}),
    ('mixed_two_needs','Harga Signature Hair Spa dan cara memakai kondisioner serta menyisir rambut keriting?',{'db:services:1'}),
    ('unknown','Berapa harga Diamond Hair Therapy?',set()),
    ('typo','Berapa harga Signatur Hair Spaa?',set()),
    ('name_substring','Berapa harga superkeratin?',set()),
    ('unsupported_history','Berapa harga keratin bulan lalu?',{'db:services:3'}),
    ('unknown_promo','Apakah hair spa diskon hari ini?',{'db:services:1'}),
    ('service_name_styling','Berapa tarif Volume Blowout Styling?',{'db:services:6'}),
]


def probe(corpus):
    index=corpus_index(corpus);rows=[]
    for family,question,expected in PROBES:
        candidates=balanced_order(question,corpus,5,index=index)
        selected,decision=select_evidence(question,corpus,candidates)
        matched={d['id'] for d in match_services(question,[d for d in corpus if d['source_type']=='db'])}
        result=catalog_answer(question,corpus)
        rows.append(dict(family=family,question=question,matched_service_ids=sorted(matched),
            expected_match_ids=sorted(expected),match_invariant_passed=matched==expected,
            candidate_ids=[corpus[i]['id'] for i in candidates],selected_ids=[corpus[i]['id'] for i in selected],
            selection=decision,catalog_route=result.get('status') if result else None,
            deterministic_reply=result.get('reply') if result else None,
            human_review_status='pending',relevant_evidence_ids=None,reference_answer=None))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--corpus',type=Path,default=BASE_DIR/'rag/eval/curated-development-v2/corpus.json')
    args=parser.parse_args()
    if args.out.exists():raise ValueError('Preserve existing reports; use a new file')
    raw=args.corpus.read_bytes();rows=probe(json.loads(raw))
    report=dict(protocol='AI_authored_development_probes_v1',executed_at_utc=datetime.now(timezone.utc).isoformat(),
        corpus_sha256=hashlib.sha256(raw).hexdigest(),questions=len(rows),
        match_invariants_passed=sum(r['match_invariant_passed'] for r in rows),
        model_calls=0,independent_test=False,semantic_answer_quality_scored=False,publication_ready=False,results=rows)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('questions','match_invariants_passed','model_calls')}))
    if report['match_invariants_passed']!=len(rows):raise SystemExit(2)


if __name__=='__main__':main()
