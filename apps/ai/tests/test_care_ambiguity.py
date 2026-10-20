import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.rag.care_intent import conditioner_kind,conditioner_clarification,compatible_product_evidence
from app.rag import rag_service,chatgpt_plan,bm25_retrieval

PACKAGE=Path(__file__).resolve().parents[1]/'rag/eval/curated-development-v2'


@pytest.mark.parametrize('question,expected',[
    ('Cara memakai conditioner?','unspecified'),
    ('Kondisioner perlu dibilas atau tidak?','unspecified'),
    ('Bagaimana memakai kondisioner bilas?','rinse_out'),
    ('Cara memakai leave in conditioner?','leave_in'),
    ('Cara memakai kondisioner tanpa bilas?','leave_in'),
    ('Cara memakai conditioner yang tidak perlu dibilas?','leave_in'),
    ('Perbedaan kondisioner bilas dan leave-in?','both'),
    ('Pakai yang bukan leave-in conditioner?','unspecified'),
    ('Apakah conditioner tidak perlu dibilas?','unspecified'),
])
def test_product_type_is_explicit_not_inferred(question,expected):
    assert conditioner_kind(question)==expected


def test_comparison_can_discuss_both_types_without_forcing_choice():
    assert conditioner_clarification('Apa perbedaan jenis conditioner?') is None


def test_product_duration_is_not_confused_with_salon_duration():
    from app.rag.answer_policy import service_clarification
    assert service_clarification('Berapa durasi mendiamkan kondisioner bilas?',PACKAGE/'corpus.json') is None


@pytest.mark.asyncio
@pytest.mark.parametrize('question,rule',[
    ('Produk ini boleh dipakai setiap hari?','product_reference_unspecified'),
    ('Bagaimana memakai krim itu?','product_reference_unspecified'),
    ('Setelah treatment itu kapan boleh keramas?','service_reference_unspecified'),
])
async def test_unresolved_references_do_not_trigger_retrieval_or_generation(monkeypatch,question,rule):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'rag_corpus_file',PACKAGE/'corpus.json')
    model=AsyncMock(side_effect=AssertionError('No implicit reference resolution'))
    monkeypatch.setattr(chatgpt_plan,'generate',model)
    result=await rag_service.RagService().answer(question,include_trace=True,allow_web=False)
    assert result['_trace']['generation_status']=='policy_clarification'
    assert result['_trace']['policy_rule']==rule
    model.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('question',[
    'Bagaimana memakai conditioner?',
    'Bagaimana memakai kondisioner untuk rambut kering?',
    'Berapa harga Signature Hair Spa dan cara memakai conditioner?',
])
async def test_ambiguous_product_needs_no_model_or_web(monkeypatch,question):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'rag_corpus_file',PACKAGE/'corpus.json')
    model=AsyncMock(side_effect=AssertionError('No generation for ambiguity'))
    web=AsyncMock(side_effect=AssertionError('No web for ambiguity'))
    monkeypatch.setattr(chatgpt_plan,'generate',model)
    monkeypatch.setattr(rag_service,'live_crawl_docs',web)
    result=await rag_service.RagService().answer(question,include_trace=True)
    assert result['_trace']['generation_status']=='policy_clarification'
    assert result['_trace']['policy_rule']=='conditioner_type_unspecified'
    assert 'kondisioner bilas' in result['reply'] and 'leave-in/tanpa bilas' in result['reply']
    if 'harga' in question:
        assert 'Rp325.000' in result['reply']
        assert [s['id'] for s in result['sources']]==['db:services:1']
    model.assert_not_awaited();web.assert_not_awaited()


@pytest.mark.asyncio
async def test_mixed_unknown_service_does_not_guess_price(monkeypatch):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'rag_corpus_file',PACKAGE/'corpus.json')
    result=await rag_service.RagService().answer('Berapa harga Diamond Hair Therapy dan cara memakai kondisioner?',include_trace=True)
    assert result['_trace']['generation_status']=='policy_clarification'
    assert 'Rp' not in result['reply'] and 'yang mana' in result['reply']


@pytest.mark.asyncio
@pytest.mark.parametrize('query,missing',[
    ('Berapa harga Signature Hair Spa kemarin dan cara memakai conditioner?','Riwayat perubahan harga belum tersedia'),
    ('Berapa harga Signature Hair Spa promo dan cara memakai conditioner?','Informasi promo, diskon'),
])
async def test_product_clarification_preserves_unavailable_business_needs(monkeypatch,query,missing):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'rag_corpus_file',PACKAGE/'corpus.json')
    result=await rag_service.RagService().answer(query,include_trace=True,allow_web=False)
    assert result['_trace']['generation_status']=='policy_clarification'
    assert missing in result['reply'] and 'kondisioner bilas' in result['reply']


@pytest.mark.parametrize('query,allowed,excluded',[
    ('Cara memakai conditioner bilas untuk rambut kering?','care:S01:conditioner-by-hair-type:v1','care:S02:leave-in-placement:v1'),
    ('Cara memakai kondisioner tanpa bilas?','care:S02:leave-in-placement:v1','care:S01:conditioner-by-hair-type:v1'),
])
def test_explicit_product_has_compatible_context_and_equivalent_language(monkeypatch,query,allowed,excluded):
    corpus=json.loads((PACKAGE/'corpus.json').read_text(encoding='utf-8'))
    monkeypatch.setattr(rag_service.settings,'rag_context_selection','source_scoped')
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    docs=bm25_retrieval.retrieve(query,5,corpus)
    ids={d.id for d in docs}
    assert allowed in ids and excluded not in ids
    assert 'kondisioner' in docs[0].metadata['ranking_query']


def test_db_and_comparisons_are_not_filtered_as_care():
    document=dict(source_type='db',section='Hair Spa',text='Harga')
    assert compatible_product_evidence('Cara memakai kondisioner bilas?',document)
    assert compatible_product_evidence('Perbedaan kondisioner bilas dan leave-in?',dict(section='Leave-in',text='Info'))


def test_comparison_retrieves_both_and_plain_bm25_baseline_remains_original(monkeypatch):
    corpus=json.loads((PACKAGE/'corpus.json').read_text(encoding='utf-8'))
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'rag_context_selection','source_scoped')
    query='Apa perbedaan kondisioner bilas dan leave-in conditioner?'
    docs=bm25_retrieval.retrieve(query,5,corpus)
    assert {'care:S01:conditioner-by-hair-type:v1','care:S02:leave-in-placement:v1'}<={d.id for d in docs}
    monkeypatch.setattr(rag_service.settings,'rag_context_selection','all')
    expected=bm25_retrieval.balanced_order(query,corpus,5)
    assert [d.id for d in bm25_retrieval.retrieve(query,5,corpus)]==[corpus[i]['id'] for i in expected]


@pytest.mark.asyncio
@pytest.mark.parametrize('query,required,forbidden',[
    ('Bagaimana memakai conditioner bilas untuk rambut kering?','conditioner-by-hair-type','leave-in-placement'),
    ('Bagaimana memakai kondisioner tanpa bilas?','leave-in-placement','conditioner-by-hair-type'),
])
async def test_explicit_type_reaches_generation_with_correct_source_family(monkeypatch,query,required,forbidden):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'rag_context_selection','source_scoped')
    monkeypatch.setattr(rag_service.settings,'rag_corpus_file',PACKAGE/'corpus.json')
    monkeypatch.setattr(rag_service.settings,'ai_llm_provider','chatgpt')
    monkeypatch.setattr(chatgpt_plan,'available',lambda:True)
    model=AsyncMock(return_value='Panduan yang tersedia [1].')
    monkeypatch.setattr(chatgpt_plan,'generate',model)
    result=await rag_service.RagService().answer(query,include_trace=True,allow_web=False)
    assert result['_trace']['generation_status']=='llm_success'
    ids=[d['id'] for d in result['_trace']['retrieved_docs']]
    assert any(required in i for i in ids)
    assert all(forbidden not in i for i in ids)
    model.assert_awaited_once()


@pytest.mark.asyncio
async def test_web_fallback_cannot_reintroduce_explicitly_wrong_product(monkeypatch):
    from app.rag.retriever import RetrievedDoc
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'rag_context_selection','source_scoped')
    monkeypatch.setattr(rag_service.settings,'rag_corpus_file',PACKAGE/'corpus.json')
    monkeypatch.setattr(rag_service.settings,'ai_llm_provider','chatgpt')
    monkeypatch.setattr(chatgpt_plan,'available',lambda:True)
    monkeypatch.setattr(chatgpt_plan,'generate',AsyncMock(return_value='Panduan [1].'))
    monkeypatch.setattr(rag_service,'needs_web_fallback',lambda *args:True)
    doc=RetrievedDoc(id='web-leave-in',file='web:test',section='Leave-in conditioner',snippet='Aplikasikan leave-in pada rambut lembap.')
    monkeypatch.setattr(rag_service,'live_crawl_docs',AsyncMock(return_value=([doc],[])))
    result=await rag_service.RagService().answer('Cara memakai conditioner bilas?',include_trace=True,allow_web=True)
    assert all(d['id']!='web-leave-in' for d in result['_trace']['retrieved_docs'])
