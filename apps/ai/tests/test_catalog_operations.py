import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.rag import chatgpt_plan, live_services, rag_service
from app.rag.answer_policy import service_clarification
from app.rag.catalog_operations import catalog_answer, parse_catalog_query

CORPUS = Path(__file__).resolve().parents[1]/'rag/eval/curated-development-v2/corpus.json'


@pytest.fixture
def corpus():
    return json.loads(CORPUS.read_text(encoding='utf-8'))


@pytest.mark.parametrize('text,expected',[
    ('Apa saja layanan dengan harga di bawah Rp300.000?', ['Precision Haircut','Volume Blowout Styling']),
    ('Daftar layanan maksimal 280 ribu', ['Precision Haircut','Volume Blowout Styling']),
    ('Layanan di atas 620.000', ['Keratin Smooth Treatment']),
    ('Layanan minimal 620 ribu', ['Keratin Smooth Treatment','Color Gloss Refresh']),
    ('Layanan antara Rp280.000 dan Rp325.000', ['Signature Hair Spa','Volume Blowout Styling']),
    ('Layanan di atas Rp220.000 dan di bawah Rp300.000', ['Volume Blowout Styling']),
    ('Apa layanan termurah?', ['Precision Haircut']),
    ('Apa layanan termahal?', ['Keratin Smooth Treatment']),
    ('Apa saja layanan di atas 1 juta?', []),
])
def test_price_operations_use_record_fields(corpus,text,expected):
    result=catalog_answer(text,corpus)
    assert result['status']=='catalog_lookup'
    scanned=json.loads(result['sources'][0]['snippet'])
    by_id={d['id']:d['fields']['name'] for d in corpus if d['source_type']=='db'}
    assert [by_id[i] for i in scanned['matched_ids']]==expected
    assert 'snapshot penelitian' in result['reply']
    for source in result['sources'][1:]:
        assert str(source['citation_number']) in result['reply']


def test_all_services_and_count_do_not_use_top_k(corpus):
    result=catalog_answer('Sebutkan semua layanan yang tersedia di salon.',corpus)
    assert len(result['sources'])==7  # Full scan citation and all six rows.
    assert len(result['docs'])==6
    assert all(d['fields']['name'] in result['reply'] for d in corpus if d['source_type']=='db')
    result=catalog_answer('Berapa jumlah layanan dengan harga di bawah 300 ribu?',corpus)
    assert '**2 layanan**' in result['reply']


def test_empty_and_unavailable_catalog_are_distinct(corpus):
    empty=catalog_answer('Sebutkan semua layanan',[],mode='live')
    assert '**0 layanan**' in empty['reply'] and empty['status']=='catalog_lookup'
    failure=catalog_answer('Sebutkan semua layanan',[],mode='unavailable')
    assert 'belum dapat diakses' in failure['reply'] and failure['status']=='policy_unavailable'


@pytest.mark.parametrize('text',[
    'Layanan di bawah seratus ribu', 'Layanan antara 300 ribu dan 200 ribu',
    'Apa saja layanan dengan harga 300 ribu?', 'Layanan tidak di bawah Rp300.000',
    'Layanan di bawah Rp300.000 atau di atas Rp500.000',
    'Layanan di bawah Rp300.000 dan di atas seratus ribu',
])
def test_unsupported_or_ambiguous_price_is_clarified(corpus,text):
    result=catalog_answer(text,corpus)
    assert result['status']=='policy_clarification'
    assert not result['sources']


def test_preserve_single_service_clarification_and_document_questions():
    assert parse_catalog_query('Berapa biaya treatment itu?') is None
    assert service_clarification('Berapa biaya treatment itu?',CORPUS)
    assert service_clarification('Apa saja layanan di bawah 300 ribu?',CORPUS) is None
    assert parse_catalog_query('Berapa harga Signature Hair Spa dan bagaimana memakai kondisioner?') is None
    assert parse_catalog_query('Apa saja layanan dan cara merawat rambut kering?') is None
    assert parse_catalog_query('Apa saja layanan maksimal 60 menit?') is None


def test_sort_ties_and_explicit_large_catalog_limit(corpus):
    result=catalog_answer('Urutkan semua layanan berdasarkan harga dari tertinggi',corpus)
    ids=json.loads(result['sources'][0]['snippet'])['matched_ids']
    by_id={d['id']:d['fields']['price'] for d in corpus if d['source_type']=='db'}
    assert [by_id[i] for i in ids]==sorted(by_id.values(),reverse=True)
    large=[]
    template=next(d for d in corpus if d['source_type']=='db')
    for i in range(35):
        d=deepcopy(template);d['id']=f'db:{i}';d['fields']['id']=i;d['fields']['name']=f'Service {i}'
        large.append(d)
    result=catalog_answer('Daftar semua layanan',large)
    assert '**35 layanan**' in result['reply']
    assert 'Ditampilkan 30 dari 35' in result['reply']
    assert len(result['sources'])==31


@pytest.mark.asyncio
async def test_live_catalog_filter_is_fresh_and_never_calls_llm(corpus,monkeypatch):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    rows=deepcopy([d for d in corpus if d['source_type']=='db'])
    for d in rows:
        d['business_mode']='live'
        d['file']='services.live.json'
        d['id']=d['id'].replace('db:','live:')
    loader=AsyncMock(side_effect=lambda:deepcopy(rows))
    monkeypatch.setattr(live_services,'load_services',loader)
    generate=AsyncMock(side_effect=AssertionError('Catalog lookup must not call the model'))
    monkeypatch.setattr(chatgpt_plan,'generate',generate)
    query='Apa saja layanan dengan harga di bawah Rp300.000?'
    first=await rag_service.RagService().answer(query,live_services=True,include_trace=True)
    assert 'Precision Haircut' in first['reply'] and 'Volume Blowout Styling' in first['reply']
    rows[:]=[d for d in rows if d['fields']['name']!='Precision Haircut']
    next(d for d in rows if d['fields']['name']=='Volume Blowout Styling')['fields']['price']=350000
    second=await rag_service.RagService().answer(query,live_services=True,include_trace=True)
    assert '**0 layanan**' in second['reply']
    assert first['contextId']!=second['contextId']
    assert first['_trace']['generation_status']=='catalog_lookup'
    assert first['_trace']['business_source_mode']=='live'
    assert loader.await_count==2
    generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_live_catalog_does_not_leak_snapshot_listing(monkeypatch):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(live_services,'load_services',AsyncMock(side_effect=RuntimeError('unavailable')))
    result=await rag_service.RagService().answer('Sebutkan semua layanan',live_services=True,include_trace=True)
    assert result['_trace']['generation_status']=='policy_unavailable'
    assert 'Hair Spa' not in result['reply'] and result['sources']==[]
