import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

import httpx
import pytest

from app.rag import rag_service,chatgpt_plan,web_fallback,web_fetch
from app.rag.catalog_operations import catalog_answer
from app.rag.corpus_loader import load_corpus,CorpusError
from app.rag.service_matching import match_services

PACKAGE=Path(__file__).resolve().parents[1]/'rag/eval/curated-development-v2'


@pytest.fixture
def corpus():return json.loads((PACKAGE/'corpus.json').read_text(encoding='utf-8'))


def test_named_catalog_facts_and_comparison_are_complete(corpus):
    answer=catalog_answer('Berapa harga dan durasi Volume Blowout Styling?',corpus)
    assert answer['status']=='catalog_lookup' and len(answer['sources'])==1
    assert 'Rp280.000' in answer['reply'] and '55 menit' in answer['reply']
    assert 'snapshot penelitian' in answer['reply']
    answer=catalog_answer('Apa perbedaan harga reguler dan durasi Signature Hair Spa dibanding Scalp Detox Therapy?',corpus)
    for fact in ('Rp325.000','Rp360.000','90 menit','75 menit','Rp35.000','15 menit'):
        assert fact in answer['reply']
    assert len(answer['sources'])==2 and 'layanan berbeda' in answer['reply']


@pytest.mark.parametrize('query',[
    'Berapa harga Keratin Smooth Treatment dan apakah termasuk pajak?',
    'Berapa harga Signature Hair Spa dan bagaimana memakai kondisioner?',
])
def test_unsupported_conditions_and_care_are_not_silently_answered_partially(corpus,query):
    assert catalog_answer(query,corpus) is None


@pytest.mark.parametrize('query',[
    'Berapa harga keratin kemarin?',
    'Apakah ada diskon Signature Hair Spa?',
    'Apakah Keratin Smooth Treatment masih Rp690.000?',
])
def test_unavailable_history_and_discount_do_not_invent_change_or_user_error(corpus,query):
    answer=catalog_answer(query,corpus)
    assert answer['status']=='policy_unavailable'
    assert 'belum tersedia' in answer['reply'] and 'staf salon' in answer['reply']
    assert 'berubah sejak' not in answer['reply'] and 'Anda salah' not in answer['reply']


def test_alias_collision_does_not_choose_arbitrary_service(corpus):
    rows=[d for d in corpus if d['source_type']=='db']
    duplicate={**rows[0],'id':'second','fields':{**rows[0]['fields'],'name':'Premium Hair Spa'}}
    assert not match_services('Berapa harga hair spa?',rows+[duplicate])
    assert len(match_services('Berapa harga Signature Hair Spa?',rows+[duplicate]))==1


@pytest.mark.asyncio
@pytest.mark.parametrize('query,rule',[
    ('Berapa dosis obat resep untuk ketombe?','nonclinical_prescription'),
    ('Merek keratin apa yang digunakan TIEN salon?','confidential_products'),
    ('Setelah keratin boleh keramas kapan?','unavailable_aftercare_sop'),
])
async def test_scope_boundaries_need_no_model_catalog_or_web(monkeypatch,query,rule):
    from app.rag import live_services
    model=AsyncMock(side_effect=AssertionError('No model'))
    loader=AsyncMock(side_effect=AssertionError('No catalog needed'))
    monkeypatch.setattr(chatgpt_plan,'generate',model)
    monkeypatch.setattr(live_services,'load_services',loader)
    result=await rag_service.RagService().answer(query,live_services=True,include_trace=True)
    assert result['_trace']['policy_rule']==rule and not result['sources']
    model.assert_not_awaited();loader.assert_not_awaited()


def test_corpus_hash_and_duplicate_id_validation(tmp_path,corpus):
    path=tmp_path/'corpus.json'
    content=json.dumps(corpus).encode();path.write_bytes(content)
    (tmp_path/'manifest.json').write_text(json.dumps({'output_sha256':{'corpus.json':hashlib.sha256(content).hexdigest()}}))
    assert load_corpus(path)==corpus
    path.write_text('[]')
    with pytest.raises(CorpusError):load_corpus(path)
    (tmp_path/'manifest.json').unlink()
    path.write_text(json.dumps([corpus[0],corpus[0]]))
    with pytest.raises(CorpusError):load_corpus(path)


def test_explicit_runtime_bundle_requires_manifest_and_rejects_register_tampering(tmp_path):
    from app.rag.build_runtime_corpus import build
    out=tmp_path/'runtime'
    build(PACKAGE,out)
    assert len(load_corpus(out/'corpus.json',require_manifest=True))==7
    (out/'source-register.json').write_text('[]')
    with pytest.raises(CorpusError):load_corpus(out/'corpus.json',require_manifest=True)
    (out/'manifest.json').unlink()
    with pytest.raises(CorpusError):load_corpus(out/'corpus.json',require_manifest=True)


@pytest.mark.asyncio
async def test_unreadable_corpus_is_service_unavailable_without_path_leak(monkeypatch,tmp_path):
    from fastapi import FastAPI
    from app.routers.chat import router
    monkeypatch.setattr(rag_service.settings,'rag_corpus_file',tmp_path/'private-path.json')
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25')
    monkeypatch.setattr(rag_service.settings,'rag_live_services',False)
    app=FastAPI();app.include_router(router,prefix='/ai')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/ai/chat',json={'message':'Harga haircut?'})
    assert response.status_code==503 and 'private-path' not in response.text


@pytest.mark.asyncio
async def test_generation_timeout_preserves_evidence_and_marks_fallback(monkeypatch):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'ai_llm_provider','chatgpt')
    monkeypatch.setattr(rag_service.settings,'rag_generation_timeout_seconds',.001)
    monkeypatch.setattr(chatgpt_plan,'available',lambda:True)
    async def slow(*args,**kwargs):await asyncio.sleep(1);return 'never returned'
    monkeypatch.setattr(chatgpt_plan,'generate',slow)
    result=await rag_service.RagService().answer('Bagaimana memakai kondisioner bilas untuk rambut kering?',allow_web=False,include_trace=True)
    assert result['_trace']['generation_status']=='llm_error_offline_fallback'
    assert result['_trace']['contexts'] and result['_trace']['prompt_messages'] is None


def test_bm25_runtime_imports_no_chromadb_or_browser():
    result=subprocess.run([sys.executable,'-c',"import sys; from app.rag.rag_service import RagService; assert not any(x in sys.modules for x in ('chromadb','playwright','crawl4ai')); print('light-import-ok')"],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


@pytest.mark.asyncio
async def test_no_matching_evidence_skips_model(monkeypatch):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    model=AsyncMock(side_effect=AssertionError('No supported evidence'))
    monkeypatch.setattr(chatgpt_plan,'generate',model)
    result=await rag_service.RagService().answer('quasar intergalaktik',allow_web=False,include_trace=True)
    assert result['_trace']['policy_rule']=='no_matching_evidence'
    model.assert_not_awaited()


@pytest.mark.asyncio
async def test_attributed_excerpt_is_exactly_the_prompt_window(monkeypatch):
    from app.rag import bm25_retrieval
    from app.rag.retriever import RetrievedDoc
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'ai_llm_provider','chatgpt')
    monkeypatch.setattr(chatgpt_plan,'available',lambda:True)
    monkeypatch.setattr(chatgpt_plan,'generate',AsyncMock(return_value='Edukasi [1].'))
    doc=RetrievedDoc(id='x',file='care.md',section='Edukasi',snippet='Kalimat bukti. '*100,metadata={'bm25_score':1})
    monkeypatch.setattr(bm25_retrieval,'retrieve',lambda *args,**kwargs:[doc])
    result=await rag_service.RagService().answer('Bagaimana perawatan rambut?',allow_web=False,include_trace=True)
    assert result['sources'][0]['snippet']==result['_trace']['contexts'][0]
    assert len(result['sources'][0]['snippet'])==400


@pytest.mark.asyncio
async def test_robots_disallow_prevents_article_request():
    calls=[]
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200,text='User-agent: *\nDisallow: /ketombe',headers={'content-type':'text/plain'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError,match='disallow'):
            await web_fetch.fetch_article('https://www.alodokter.com/ketombe',client=client)
    assert calls==['/robots.txt']


@pytest.mark.asyncio
async def test_web_extracts_article_with_provenance_and_rejects_external_redirect():
    def handler(request):
        if request.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nAllow: /',headers={'content-type':'text/plain'})
        return httpx.Response(200,text='<html><body><nav>Noise</nav><article><h1>Ketombe</h1><p>'+('Edukasi kulit kepala. '*20)+'</p></article></body></html>',headers={'content-type':'text/html'})
    web_fetch._LAST_FETCH.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        article=await web_fetch.fetch_article('https://www.alodokter.com/ketombe',client=client)
    assert 'Edukasi' in article['text'] and 'Noise' not in article['text']
    assert article['robots_sha256'] and article['review_status']=='external_unreviewed'
    def redirect(request):
        if request.url.path=='/robots.txt':return handler(request)
        return httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
    web_fetch._LAST_FETCH.clear()
    async with httpx.AsyncClient(transport=httpx.MockTransport(redirect)) as client:
        with pytest.raises(ValueError,match='allowlist'):
            await web_fetch.fetch_article('https://www.alodokter.com/ketombe',client=client)


@pytest.mark.asyncio
@pytest.mark.parametrize('status',[403,429,503])
async def test_unavailable_robots_is_fail_closed(status):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(status))) as client:
        with pytest.raises(ValueError,match='Robots rules unavailable'):
            await web_fetch.fetch_article('https://www.alodokter.com/ketombe',client=client)


@pytest.mark.asyncio
async def test_web_missing_topic_and_fetch_failure_have_no_unrelated_fallback(monkeypatch):
    web_fallback._CRAWL_CACHE.clear()
    fetch=AsyncMock(side_effect=ValueError('robots denied'))
    monkeypatch.setattr(web_fallback,'fetch_article',fetch)
    assert await web_fallback.live_crawl_docs('cara reservasi')==([],[])
    fetch.assert_not_awaited()
    assert await web_fallback.live_crawl_docs('ketombe')==([],[])
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_curated_topic_coverage_skips_web_and_missing_topic_preserves_local_evidence(monkeypatch):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'ai_llm_provider','local')
    crawl=AsyncMock(return_value=([],[]))
    monkeypatch.setattr(rag_service,'live_crawl_docs',crawl)
    await rag_service.RagService().answer('Bagaimana memakai kondisioner untuk rambut kering?',allow_web=True)
    crawl.assert_not_awaited()
    result=await rag_service.RagService().answer('Bagaimana edukasi ketombe?',allow_web=True,include_trace=True)
    crawl.assert_awaited_once()
    assert result['_trace']['retrieved_docs']
