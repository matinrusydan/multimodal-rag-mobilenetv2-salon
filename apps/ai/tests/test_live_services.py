"""Operational catalog freshness and isolation from frozen research evidence."""
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.rag import chatgpt_plan, live_services, rag_service
from app.rag.answer_policy import source_payload
from app.rag.retriever import RetrievedDoc


def row(price=280000, **kwargs):
    return dict(id=6, name='Volume Blowout Styling', slug='volume-blowout-styling',
                price=price, durationMin=55, description='Styling rambut') | kwargs


def mock_api(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(live_services.httpx, 'AsyncClient',
                        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setattr(rag_service.settings, 'rag_retrieval_provider', 'bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings, 'ai_llm_provider', 'chatgpt')
    monkeypatch.setattr(chatgpt_plan, 'available', lambda: True)
    generate = AsyncMock(return_value='Jawaban layanan [1].')
    monkeypatch.setattr(chatgpt_plan, 'generate', generate)
    return generate


@pytest.mark.asyncio
async def test_new_price_and_inactive_service_follow_next_request(monkeypatch, runtime):
    state = {'price':280000, 'inactive':False}
    def handler(request):
        assert request.url.path == '/api/services'
        assert 'x-internal-token' not in request.headers
        return httpx.Response(200, json={'data':[row(state['price'], isActive=not state['inactive'])]})
    mock_api(monkeypatch, handler)
    async def ask():
        return await rag_service.RagService().answer('Berapa harga dan durasi Volume Blowout Styling?',
                live_services=True, allow_web=False, include_trace=True)
    first = await ask()
    db = [d for d in first['_trace']['retrieved_docs'] if d['metadata']['source_type']=='db']
    assert len(db)==1 and '280,000' in db[0]['snippet']
    assert first['sources'][0]['title'].endswith('(database aktif)')
    state['price'] = 300000
    second = await ask()
    assert '300,000' in second['_trace']['contexts'][0]
    assert first['contextId'] != second['contextId']
    assert second['_trace']['prompt_messages'] is None
    assert second['_trace']['generation_status']=='catalog_lookup'
    assert 'Rp300.000' in second['reply']
    runtime.assert_not_awaited()
    state['inactive'] = True
    third = await ask()
    assert not any(d['metadata']['source_type']=='db' for d in third['_trace']['retrieved_docs'])
    assert all('services.snapshot.json' not in c for c in third['_trace']['contexts'])


@pytest.mark.asyncio
@pytest.mark.parametrize('payload', [None, {'data':[row(price=-1)]}, {'data':[row(durationMin=True)]}])
async def test_bad_catalog_never_restores_snapshot_prices(monkeypatch, runtime, payload):
    mock_api(monkeypatch, lambda request: httpx.Response(503) if payload is None else httpx.Response(200,json=payload))
    result = await rag_service.RagService().answer('Berapa harga Signature Hair Spa?',
                live_services=True, allow_web=False, include_trace=True)
    trace=result['_trace']
    assert trace['business_source_mode']=='unavailable'
    assert not any(d['metadata']['source_type']=='db' for d in trace['retrieved_docs'])
    assert trace['generation_status']=='policy_unavailable'
    assert trace['prompt_messages'] is None
    assert 'belum dapat diakses' in result['reply']
    runtime.assert_not_awaited()
    assert '325,000' not in json.dumps(trace['contexts'])


@pytest.mark.asyncio
async def test_live_clarification_uses_current_options_without_llm(monkeypatch, runtime):
    mock_api(monkeypatch, lambda request: httpx.Response(200,json={'data':[row()]}))
    result=await rag_service.RagService().answer('Berapa biaya treatment itu?',
                live_services=True,allow_web=False,include_trace=True)
    assert 'katalog aktif salon' in result['reply'] and 'Volume Blowout Styling' in result['reply']
    assert 'Keratin' not in result['reply'] and 'Rp' not in result['reply']
    runtime.assert_not_awaited()


@pytest.mark.asyncio
async def test_default_evaluation_is_snapshot_even_when_http_live_enabled(monkeypatch, runtime):
    monkeypatch.setattr(rag_service.settings, 'rag_live_services', True)
    load=AsyncMock(side_effect=AssertionError('Evaluation must not fetch live data'))
    monkeypatch.setattr(live_services,'load_services',load)
    result=await rag_service.RagService().answer('Berapa harga Volume Blowout Styling?',allow_web=False,include_trace=True)
    assert result['_trace']['business_source_mode']=='snapshot'
    assert any(d['file']=='services.snapshot.json' for d in result['_trace']['retrieved_docs'])
    load.assert_not_awaited()


@pytest.mark.asyncio
async def test_router_enables_configured_live_catalog(monkeypatch):
    from app.routers.chat import chat, ChatRequest
    monkeypatch.setattr(rag_service.settings,'rag_live_services',True)
    answer=AsyncMock(return_value={'reply':'test','sources':[],'contextId':'test'})
    monkeypatch.setattr(rag_service.rag_service,'answer',answer)
    await chat(ChatRequest(message='test'))
    assert answer.call_args.kwargs['live_services'] is True


@pytest.mark.asyncio
async def test_connection_reuse_still_reads_changed_prices_and_closes_cleanly(monkeypatch):
    state={'price':280000,'calls':0}
    def handler(request):
        state['calls']+=1
        return httpx.Response(200,json={'data':[row(price=state['price'])]})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(live_services,'_catalog_client',client)
    try:
        first=await live_services.load_services()
        state['price']=310000
        second=await live_services.load_services()
        assert first[0]['fields']['price']==280000 and second[0]['fields']['price']==310000
        assert state['calls']==2 and not client.is_closed
    finally:
        await live_services.close_catalog_client()
    assert client.is_closed and live_services._catalog_client is None
