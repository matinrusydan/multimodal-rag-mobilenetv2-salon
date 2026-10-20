"""Regression checks for evidence isolation, real zero scores and actual contexts."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.rag import eval_rag, ingest, rag_service
from app.rag.embedding import embed
from app.rag.pilot import bm25_scores, build_corpus, build_questions, metrics
from app.rag.retriever import RetrievedDoc


class MemoryStore:
    def __init__(self): self.data = {}
    def existing_ids(self, topic): return list(self.data.get(topic, {}))
    def clear(self, topic): self.data[topic] = {}
    def delete_by_ids(self, topic, ids):
        for cid in ids: self.data[topic].pop(cid, None)
    def upsert(self, topic, ids, texts, embeddings, metadatas):
        self.data.setdefault(topic, {}).update({cid: meta for cid, meta in zip(ids, metadatas)})


def test_ingest_keeps_other_files_and_updates_only_current_file(tmp_path, monkeypatch):
    store = MemoryStore()
    monkeypatch.setattr(ingest, 'vector_store', store)
    monkeypatch.setattr(ingest, 'embed_sync', lambda texts: [[1.0] for _ in texts])
    for name in ['one.md','two.md']:
        (tmp_path/name).write_text('---\ntopic: layanan\nsource: https://example.test/source\ntype: web\n---\n## Bagian\nIsi '+name,encoding='utf-8')
    ingest.plan_ingest(tmp_path)
    first = set(store.existing_ids('layanan'))
    assert len(first)==2
    assert all(meta['source']=='https://example.test/source' for meta in store.data['layanan'].values())
    ingest.plan_ingest(tmp_path)
    assert set(store.existing_ids('layanan'))==first
    path=tmp_path/'one.md'
    path.write_text(path.read_text(encoding='utf-8')+' changed',encoding='utf-8')
    ingest.plan_ingest(tmp_path)
    current=set(store.existing_ids('layanan'))
    assert len(current)==2
    assert {x for x in first if x.startswith('two.md#')} <= current
    assert not {x for x in first if x.startswith('one.md#')} & current


@pytest.mark.parametrize('text,expected',[('SKOR: 0',0),('SKOR: 0.5\nALASAN: parsial',0.5),
    ('SKOR: 1.0',1),('',None),('Gemini 3.1 failed 429',None),('SKOR: 1.5',None),('SKOR: 10',None)])
def test_score_parser_distinguishes_zero_from_failure(text,expected):
    assert eval_rag.parse_score(text)==expected


def test_summary_retains_zero_and_reports_missing_denominators():
    rows=[dict(status='ok',metrics={k:0 for k in eval_rag.METRICS}),
          dict(status='pipeline_error',metrics={k:None for k in eval_rag.METRICS})]
    summary=eval_rag.summarize(rows)
    assert summary['avg_faithfulness']==0
    assert summary['metric_counts']['faithfulness']==dict(valid=1,missing=1,zero_scores=1,not_applicable=0)
    assert summary['execution_errors']==1
    assert eval_rag.retryable_metrics(rows[0])==[]
    assert len(eval_rag.retryable_metrics(rows[1]))==4
    assert eval_rag.summarize([])['avg_faithfulness'] is None


def test_judge_reference_includes_snapshot_business_values(tmp_path,monkeypatch):
    from app.rag.pilot import ROOT
    monkeypatch.setattr(eval_rag,'TESTSET_FILE',ROOT/'apps/ai/rag/eval/curated-development-v2/questions.json')
    assert '325000' in eval_rag.load_testset()[0]['ground_truth']


@pytest.mark.asyncio
async def test_evaluator_uses_only_context_returned_by_generation(monkeypatch):
    answer=AsyncMock(return_value={'reply':'response','_trace':dict(generation_status='llm_success',
        contexts=['actual web context'],retrieved_docs=[{'id':'actual'}])})
    monkeypatch.setattr(rag_service.RagService,'answer',answer)
    result=await eval_rag.run_rag_pipeline('query')
    assert result['contexts']==['actual web context']
    answer.assert_awaited_once()
    assert answer.call_args.kwargs['include_trace'] is True
    assert answer.call_args.kwargs['allow_web'] is False


@pytest.mark.asyncio
async def test_trace_is_opt_in_and_matches_retrieved_docs(monkeypatch):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','chroma')
    monkeypatch.setattr(rag_service.settings,'ai_llm_provider','gemini')
    monkeypatch.setattr(rag_service.settings,'web_fallback_enabled',False)
    monkeypatch.setattr(rag_service.settings,'ai_embedding_provider','local')
    monkeypatch.setattr(rag_service,'gemini_api_key',lambda:None)
    monkeypatch.setattr(rag_service,'embed',AsyncMock(return_value=[[1.0]]))
    doc=RetrievedDoc(file='source.md',section='A',snippet='Exact context',id='chunk-1',metadata={'source':'origin'})
    retrieve=AsyncMock(return_value=[doc])
    monkeypatch.setattr(rag_service.retriever,'retrieve',retrieve)
    service=rag_service.RagService()
    regular=await service.answer('query')
    assert '_trace' not in regular
    assert set(regular)=={'reply','sources','contextId'}
    traced=await service.answer('query',include_trace=True)
    assert traced['_trace']['contexts']==['Exact context']
    assert traced['_trace']['retrieved_docs'][0]['id']=='chunk-1'
    assert traced['_trace']['generation_status']=='offline_extracts'
    assert retrieve.await_count==2  # one retrieval per answer, not per metric


@pytest.mark.asyncio
async def test_context_id_changes_when_evidence_changes(monkeypatch):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','chroma')
    monkeypatch.setattr(rag_service.settings,'ai_llm_provider','gemini')
    monkeypatch.setattr(rag_service.settings,'ai_embedding_provider','local')
    monkeypatch.setattr(rag_service,'gemini_api_key',lambda:None)
    monkeypatch.setattr(rag_service,'embed',AsyncMock(return_value=[[1.0]]))
    retrieve=AsyncMock(side_effect=[[RetrievedDoc(file='price.md',snippet='100')],
                                    [RetrievedDoc(file='price.md',snippet='200')]])
    monkeypatch.setattr(rag_service.retriever,'retrieve',retrieve)
    service=rag_service.RagService()
    a=await service.answer('price',allow_web=False)
    b=await service.answer('price',allow_web=False)
    assert a['contextId']!=b['contextId']


@pytest.mark.asyncio
async def test_strict_embedding_refuses_local_fallback(monkeypatch):
    from app.rag import embedding
    monkeypatch.setattr(embedding.settings,'ai_embedding_provider','local')
    with pytest.raises(RuntimeError,match='Strict embedding'):
        await embed(['query'],strict=True)


def test_retrieval_metrics_need_all_groups_and_count_misses():
    m=metrics(['db','noise'],['db','doc'],[['db'],['doc']])
    assert m==dict(precision=0.5,recall=0.5,f1=0.5,complete_evidence=0)
    assert metrics([],['db'],[['db']])['f1']==0
    assert metrics(['noise'],[],[])['f1'] is None
    assert metrics(['db','doc'],['db','doc'],[['db'],['doc']])['complete_evidence']==1


def test_bm25_ranks_matching_service_and_handles_empty_corpus():
    scores=bm25_scores('keratin',['Layanan keratin harga','layanan haircut'])
    assert scores[0]>scores[1]
    assert bm25_scores('query',[])==[]


def test_trace_context_limits_equal_prompt_evidence():
    from app.rag.prompt_builder import build_prompt, context_snippets
    docs=[RetrievedDoc(file='kb.md',snippet='x'*401),RetrievedDoc(file='web:source',snippet='y'*1101)]
    snippets=context_snippets(docs)
    assert list(map(len,snippets))==[400,1100]
    prompt=build_prompt('query',docs)[1]['content']
    assert 'x'*400 in prompt and 'x'*401 not in prompt
    assert 'y'*1100 in prompt and 'y'*1101 not in prompt


def test_pilot_uses_actual_snapshot_and_balanced_draft_questions():
    import json
    from app.rag.pilot import DEFAULT_OUT
    snapshot=json.loads((DEFAULT_OUT/'services.snapshot.json').read_text(encoding='utf-8'))
    corpus,_=build_corpus(snapshot)
    questions=build_questions(corpus)
    assert len(questions)==24
    assert len({q['id'] for q in questions})==24
    from collections import Counter
    assert set(Counter(q['category'] for q in questions).values())=={6}
    ids={d['id'] for d in corpus}
    assert all(set(q['relevant_evidence_ids']) <= ids for q in questions)
    for doc in corpus:
        if doc['source_type']=='db':
            assert doc['captured_at']==snapshot['captured_at']
    with pytest.raises(ValueError,match='captured PostgreSQL'):
        build_corpus({'status':'seed_fixture'})
