from copy import deepcopy
import json
import math
from pathlib import Path
import random

import pytest

from app.rag.lexical_index import BM25Index,cached_index,corpus_index
from app.rag.pilot import bm25_scores
from app.rag.ir_metrics import evaluate_ranking
from app.rag.context_selection import select_context
from app.rag.answer_audit import score_annotation
from app.rag.split_guard import validate_splits
from app.rag.experiment_ir import experiment,rank,benchmark

PACKAGE=Path(__file__).resolve().parents[1]/'rag/eval/curated-development-v2'


def test_index_scores_and_ranking_match_frozen_scan_on_random_and_empty_inputs():
    rng=random.Random(42)
    texts=[' '.join(rng.choices(['harga','kering','rambut','keratin','325000','tidak'],k=rng.randrange(0,40))) for _ in range(35)]
    for query in ['harga keratin','rambut kering','tidak 325000','unknown','', 'kering kering']:
        expected=bm25_scores(query,texts)
        actual=BM25Index(texts).scores(query)
        assert actual==pytest.approx(expected,abs=1e-12)
        assert sorted(range(35),key=lambda i:(-actual[i],i))==sorted(range(35),key=lambda i:(-expected[i],i))
    assert BM25Index([]).scores('query')==[]


def test_cache_reuses_content_but_price_change_invalidates_and_fetch_time_does_not():
    cached_index.cache_clear()
    corpus=[dict(id='s',source_type='db',business_mode='live',section='Spa',
                 text='Harga: 100\nSumber: database aktif melalui API, dibaca 2026-10-20T01:00:00Z.')]
    first=corpus_index(corpus)
    corpus[0]['text']=corpus[0]['text'].replace('01:00','02:00')
    assert corpus_index(corpus) is first
    corpus[0]['text']=corpus[0]['text'].replace('100','200')
    assert corpus_index(corpus) is not first
    assert first.scores('100')[0]>0 and corpus_index(corpus).scores('100')[0]==0


def test_fixed_k_and_returned_precision_do_not_get_confused():
    score=evaluate_ranking(['a'],['a'],[['a']],5)
    assert score['precision_at_k']==.2 and score['precision_returned']==1
    assert score['recall_at_k']==1 and score['f1_at_k']==pytest.approx(1/3)
    assert score['average_precision_at_k']==score['reciprocal_rank_at_k']==1


def test_ap_denominator_all_gold_and_mrr_only_first_hit():
    score=evaluate_ranking(['x','a','b'],['a','b','c'],[['a'],['b'],['c']],3)
    assert score['average_precision_at_k']==pytest.approx((.5+2/3)/3)
    assert score['reciprocal_rank_at_k']==.5
    assert score['complete_evidence']==0
    assert evaluate_ranking([],['a'],[['a']],3)['recall_at_k']==0
    assert all(v is None for v in evaluate_ranking(['a'],[],[],3).values())


def test_ndcg_requires_explicit_grade_definition_and_rewards_ideal_order():
    grades={'a':3,'b':2,'c':1,'x':0}
    ideal=evaluate_ranking(['a','b','c'],['a','b','c'],[['a']],3,grades)
    wrong=evaluate_ranking(['x','c','a'],['a','b','c'],[['a']],3,grades)
    assert ideal['ndcg_at_k']==1 and 0<wrong['ndcg_at_k']<1
    with pytest.raises(ValueError,match='grades'):
        evaluate_ranking(['a'],['a'],[['a']],1,{'a':float('nan')})
    with pytest.raises(ValueError,match='Duplicate'):
        evaluate_ranking(['a','a'],['a'],[['a']],2)


def test_query_window_keeps_real_substring_and_exact_limit_without_gold():
    text='Pengantar umum. '*40+'Kondisioner digunakan pada batang rambut kering. '+'Penutup. '*30
    head=select_context(text,'kondisioner rambut kering',400,'head')
    selected=select_context(text,'kondisioner rambut kering',400,'query_window')
    assert 'Kondisioner' not in head['text'] and 'Kondisioner' in selected['text']
    assert selected['text']==text[selected['start']:selected['end']]
    assert len(selected['text'])==400 and selected['source_sha256']==head['source_sha256']
    assert selected['used_sha256']!=head['used_sha256']


def test_prompt_window_and_context_identity_follow_selected_evidence(monkeypatch):
    from app.config import settings
    from app.rag.retriever import RetrievedDoc
    from app.rag.prompt_builder import build_prompt,context_snippets
    from app.rag.context_selection import context_records
    from app.rag.rag_service import RagService
    text='Pengantar. '*70+'Kondisioner untuk rambut kering. '+'Penutup. '*35
    docs=[RetrievedDoc(id='care',file='care.md',section='Perawatan',snippet=text,distance=0)]
    query='kondisioner rambut kering'
    monkeypatch.setattr(settings,'rag_context_strategy','head')
    head=context_records(docs,query,'head')
    monkeypatch.setattr(settings,'rag_context_strategy','query_window')
    records=context_records(docs,query,'query_window')
    prompt=build_prompt(query,docs)
    assert context_snippets(docs,query)==[records[0]['text']]
    assert records[0]['text'] in prompt[1]['content']
    assert RagService._ctx_hash(query,['care'],None,records)!=RagService._ctx_hash(query,['care'],None,head)


def test_manual_answer_audit_pending_is_not_scored_and_wrong_service_price_fails():
    assert score_annotation({'review_status':'pending'})['metrics'] is None
    with pytest.raises(ValueError,match='actual answer'):
        score_annotation(dict(review_status='approved',reviewer='test'))
    record=dict(review_status='approved',reviewer='test-reviewer',answer='Layanan 2 Rp325.000.',
                source_business_fields=[dict(service_id=1,field='price',value=325000)],
                required_business_fields=[dict(service_id=1,field='price',value=325000)],
                observed_business_fields=[dict(service_id=2,field='price',value=325000)],
                claims=[dict(claim='claim',supported=False,citation_required=True,citation_supported=None)])
    score=score_annotation(record)
    assert score['metrics']['required_business_field_coverage']==0
    assert score['metrics']['stated_business_field_accuracy']==0
    assert score['metrics']['faithfulness_manual']==0
    assert score['counts']['citations_missing']==1
    assert score['metrics']['citation_support_manual'] is None


def test_split_guard_blocks_paraphrase_family_leakage_and_unreviewed_test():
    questions=[dict(id='a',question='Harga layanan?',family_id='single_price',split='development'),
               dict(id='b',question='Biaya treatment?',family_id='single_price',split='test')]
    with pytest.raises(ValueError,match='crosses'):validate_splits(questions)
    questions[1]['family_id']='new_family'
    with pytest.raises(ValueError,match='approved'):validate_splits(questions,True)
    questions[1].update(review_status='approved',reviewer='test',locked=True)
    assert validate_splits(questions,True)['test_questions']==1


def test_experiment_is_paired_has_no_fake_generation_and_preserves_inputs():
    corpus=json.loads((PACKAGE/'corpus.json').read_text(encoding='utf-8'))
    questions=json.loads((PACKAGE/'questions.json').read_text(encoding='utf-8'))
    before=deepcopy((corpus,questions))
    rows,summary=experiment(corpus,questions)
    assert (corpus,questions)==before
    assert summary['bm25_scan']==summary['bm25_indexed']
    assert summary['bm25_scan']['all']['scored']==20
    assert len(rows)==24*4*2
    assert all(r['answer_metrics'] is None and r['generation_status']=='not_run' for r in rows)
    assert all(r['context_characters']<=2000 for r in rows)


def test_benchmark_outputs_separate_build_timing_memory_and_warm_samples():
    corpus=json.loads((PACKAGE/'corpus.json').read_text(encoding='utf-8'))
    results=benchmark(corpus,'harga rambut',repeats=3,multipliers=(1,))
    assert results[0]['index_build_ms']>=0
    assert results[0]['python_index_peak_bytes']>=results[0]['python_index_retained_bytes']>0
    assert len(results[0]['timing']['bm25_indexed']['samples_ms'])==3
