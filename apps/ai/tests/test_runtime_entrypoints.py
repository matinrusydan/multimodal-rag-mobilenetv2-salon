"""Mocked runtime checks: no provider calls or access to the user's credentials."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

import httpx
import pytest

from app import chatgpt_auth
from app.config import Settings, settings
from app.rag import live_services
from app.rag_app import app


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(chatgpt_auth, 'auth_path', lambda: tmp_path / 'test.credentials')
    monkeypatch.setattr(chatgpt_auth, 'access_token', lambda: pytest.fail('No token refresh allowed'))
    monkeypatch.setattr(settings, 'production', False)
    monkeypatch.setattr(settings, 'agent_internal_token', 'test-internal-secret')


async def request(method, path, **kwargs):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url='http://test'
    ) as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.parametrize('entrypoint', ['app.main', 'app.rag_app'])
def test_entrypoints_import_without_optional_runtime_dependencies(entrypoint, tmp_path):
    env = {**os.environ, 'PYTHON_DOTENV_DISABLED': '1', 'AI_ENV': 'development',
           'NODE_ENV': 'test', 'ENVIRONMENT': 'test', 'AI_LLM_PROVIDER': 'local',
           'RAG_RETRIEVAL_PROVIDER': 'bm25_source_balanced', 'XDG_DATA_HOME': str(tmp_path)}
    script = """
import importlib, importlib.abc, sys
blocked = {'numpy', 'onnxruntime', 'onnx', 'PIL', 'chromadb', 'crawl4ai', 'playwright', 'google.genai', 'multipart', 'python_multipart'}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {'multipart', 'python_multipart'}:
            # Starlette probes for multipart even when no route needs it.
            raise ModuleNotFoundError(fullname)
        if any(fullname == name or fullname.startswith(name + '.') for name in blocked):
            raise AssertionError('Optional import attempted: ' + fullname)
sys.meta_path.insert(0, Block())
import httpx
httpx.get = lambda *a, **k: (_ for _ in ()).throw(AssertionError('No startup HTTP'))
from app import chatgpt_auth
chatgpt_auth.load = lambda: (_ for _ in ()).throw(AssertionError('No startup credentials'))
module = importlib.import_module(sys.argv[1])
from app.main import app as compatibility
from app.rag_app import app as canonical
assert module.app is compatibility is canonical
paths = set(canonical.openapi()['paths'])
assert {'/ai/agent', '/ai/knowledge', '/ai/chat', '/ai/health', '/ai/analyze', '/ai/ready'} <= paths
assert 'requestBody' not in canonical.openapi()['paths']['/ai/analyze']['post']
assert not any(name in sys.modules for name in blocked)
"""
    result = subprocess.run([sys.executable, '-c', script, entrypoint], env=env,
                            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
@pytest.mark.parametrize('kwargs', [{}, {'json': {}}, {'content': b'not-an-image'},
                                    {'files': {'image': ('photo.jpg', b'fake', 'image/jpeg')}}])
async def test_analyze_is_503_without_parsing_body(kwargs):
    response = await request('POST', '/ai/analyze', **kwargs)
    assert response.status_code == 503
    assert response.headers['content-type'] == 'application/problem+json'
    assert response.json()['title'] == 'Fitur belum tersedia'
    assert response.json()['status'] == 503


@pytest.mark.asyncio
async def test_health_works_without_credentials_or_catalog(monkeypatch):
    monkeypatch.setattr(chatgpt_auth, 'load', lambda: pytest.fail('No auth on liveness'))
    monkeypatch.setattr(live_services, 'load_services', AsyncMock(side_effect=AssertionError('No catalog')))
    assert (await request('GET', '/ai/health')).status_code == 200


@pytest.mark.asyncio
async def test_global_exception_does_not_expose_secret_or_log_it(monkeypatch, caplog):
    from app.rag.agent_service import agent_service
    monkeypatch.setattr(agent_service, 'answer', AsyncMock(side_effect=RuntimeError('secret-token-path')))
    response = await request('POST', '/ai/agent', json={'message': 'uji'},
                             headers={'X-Internal-Token': 'test-internal-secret'})
    assert response.status_code == 500
    assert 'secret-token-path' not in response.text + caplog.text
    assert 'RuntimeError' in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize('provider,production', [('bm25', False), ('bm25_source_balanced', False), ('chroma', True)])
async def test_legacy_maintenance_guard_precedes_optional_imports(monkeypatch, provider, production):
    import builtins
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name in {'app.rag.ingest', 'app.crawler.crawl_tips'}:
            pytest.fail('Legacy maintenance imported in lightweight profile')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', guarded)
    monkeypatch.setattr(settings, 'rag_retrieval_provider', provider)
    monkeypatch.setattr(settings, 'production', production)
    for path, payload in [('/ai/rag/reingest', None), ('/ai/crawl', {})]:
        response = await request('POST', path, json=payload,
                                 headers={'X-Internal-Token': 'test-internal-secret'})
        assert response.status_code == 503
        assert 'korpus runtime' in response.text
        assert (await request('POST', path, json=payload)).status_code == 401


@pytest.mark.asyncio
async def test_legacy_chroma_maintenance_path_is_preserved_with_fakes(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(settings, 'rag_retrieval_provider', 'chroma')
    crawl = AsyncMock(return_value=[{'file': 'test.md'}])
    calls = []
    def ingest(path, force=False):
        calls.append((path, force))
        return [{'inserted': 2}]
    monkeypatch.setitem(sys.modules, 'app.rag.ingest', SimpleNamespace(plan_ingest=ingest))
    monkeypatch.setitem(sys.modules, 'app.crawler.crawl_tips', SimpleNamespace(crawl_tips=crawl))
    headers = {'X-Internal-Token': 'test-internal-secret'}
    response = await request('POST', '/ai/rag/reingest', headers=headers)
    assert response.status_code == 200 and response.json()['data']['files'] == 1
    response = await request('POST', '/ai/crawl', json={'targets': ['https://example.test']}, headers=headers)
    assert response.status_code == 200 and response.json()['data']['ingested'] == 2
    assert len(calls) == 2
    crawl.assert_awaited_once_with(targets=['https://example.test'], use_stealth=True)


@pytest.mark.asyncio
async def test_knowledge_crud_stays_available_without_claiming_corpus_update(monkeypatch, tmp_path):
    from app.routers import knowledge
    monkeypatch.setattr(knowledge, 'KNOWLEDGE_DIR', tmp_path)
    headers = {'X-Internal-Token': 'test-internal-secret'}
    assert (await request('PUT', '/ai/knowledge/care.md', json={'content': 'Edukasi'}, headers=headers)).json()['data']['saved']
    assert (await request('GET', '/ai/knowledge/care.md', headers=headers)).json()['data']['content'] == 'Edukasi'
    assert len((await request('GET', '/ai/knowledge', headers=headers)).json()['data']) == 1
    assert (await request('DELETE', '/ai/knowledge/care.md', headers=headers)).json()['data']['deleted']


def configure_ready(monkeypatch, tmp_path):
    rows = [{'id': 'care', 'file': 'care.md', 'section': 'Edukasi',
             'source_type': 'official_professional_guidance', 'text': 'Kondisioner bilas.'}]
    path = tmp_path / 'private-corpus.json'
    path.write_bytes(json.dumps(rows).encode())
    register = tmp_path / 'source-register.json'
    register.write_bytes(b'[]')
    manifest = {'contains_business_snapshot': False, 'document_count': 1,
                'output_sha256': {file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                                  for file in (path, register)}}
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    for name, value in {'rag_runtime_corpus_file': path, 'rag_retrieval_provider': 'bm25_source_balanced',
                        'rag_top_k': 5, 'rag_live_services': True, 'rag_context_strategy': 'head',
                        'rag_context_selection': 'source_scoped', 'rag_generation_timeout_seconds': 50,
                        'ai_llm_provider': 'chatgpt', 'chatgpt_model': 'mock-model'}.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(chatgpt_auth, 'load', lambda: {'access_token': 'private-access-token',
                        'refresh_token': 'private-refresh-token', 'scopes': [chatgpt_auth.PLAN_SCOPE],
                        'expires_at': 0})
    monkeypatch.setattr(live_services, 'load_services', AsyncMock(return_value=[]))
    return path


@pytest.mark.asyncio
async def test_readiness_distinguishes_local_session_from_provider_verification(monkeypatch, tmp_path):
    configure_ready(monkeypatch, tmp_path)
    response = await request('GET', '/ai/ready')
    assert response.status_code == 200
    checks = {c['name']: c for c in response.json()['checks']}
    generation = checks['generation_configuration']
    assert generation['application_session_available'] and generation['session_expired']
    assert generation['provider_verified'] is False
    assert generation['inference_status'] == 'not_tested_no_model_call'
    assert checks['catalog_api']['ok']
    for value in ('private-access-token', 'private-refresh-token', str(tmp_path)):
        assert value not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['missing_corpus', 'tampered_corpus', 'missing_manifest',
                                    'invalid_manifest', 'tampered_register', 'missing_session', 'catalog'])
async def test_readiness_failures_are_safe(monkeypatch, tmp_path, failure):
    path = configure_ready(monkeypatch, tmp_path)
    if failure == 'missing_corpus': path.unlink()
    elif failure == 'tampered_corpus': path.write_bytes(b'[]')
    elif failure == 'missing_manifest': (tmp_path / 'manifest.json').unlink()
    elif failure == 'invalid_manifest': (tmp_path / 'manifest.json').write_text('[]')
    elif failure == 'tampered_register': (tmp_path / 'source-register.json').write_bytes(b'changed')
    elif failure == 'missing_session': monkeypatch.setattr(chatgpt_auth, 'load', lambda: {})
    else: monkeypatch.setattr(live_services, 'load_services', AsyncMock(side_effect=RuntimeError('private-access-token')))
    response = await request('GET', '/ai/ready')
    assert response.status_code == 503
    assert str(tmp_path) not in response.text and 'private-access-token' not in response.text


@pytest.mark.asyncio
async def test_readiness_catalog_probe_is_bounded(monkeypatch, tmp_path):
    configure_ready(monkeypatch, tmp_path)
    from app.rag import preflight
    wait_for = asyncio.wait_for
    async def bounded(awaitable, *, timeout):
        assert timeout == 3
        return await wait_for(awaitable, timeout=.001)
    async def hanging():
        await asyncio.sleep(60)
    monkeypatch.setattr(live_services, 'load_services', hanging)
    monkeypatch.setattr(preflight.asyncio, 'wait_for', bounded)
    response = await request('GET', '/ai/ready')
    assert response.status_code == 503
    assert next(c for c in response.json()['checks'] if c['name'] == 'catalog_api')['error_type'] == 'TimeoutError'


@pytest.mark.asyncio
async def test_catalog_lifespan_starts_and_closes_without_probing(monkeypatch):
    from app import rag_app
    start, close = AsyncMock(), AsyncMock()
    monkeypatch.setattr(rag_app, 'start_catalog_client', start)
    monkeypatch.setattr(rag_app, 'close_catalog_client', close)
    async with rag_app.lifespan(app):
        start.assert_awaited_once()
        close.assert_not_awaited()
    close.assert_awaited_once()


def production_env(monkeypatch):
    env = {'AI_ENV': 'production', 'AI_INTERNAL_TOKEN': 'A9c5p2Z7q4W8r6T1u3I0o5P9s2D7f4G8',
           'AI_LLM_PROVIDER': 'chatgpt', 'AI_CHATGPT_MODEL': 'mock-model',
           'RAG_RETRIEVAL_PROVIDER': 'bm25_source_balanced', 'RAG_LIVE_SERVICES': 'true',
           'RAG_RUNTIME_CORPUS_FILE': './rag/runtime/test/corpus.json',
           'RAG_CONTEXT_SELECTION': 'source_scoped'}
    for name, value in env.items(): monkeypatch.setenv(name, value)
    return env


@pytest.mark.parametrize('token', ['', 'change-me', 'x' * 64, 'change-me-' + 'A9c5p2Z7q4W8r6T1u3I0o5P9s2D7f4G8',
                                  'A9c5p2Z7q4W8r6T1u3I0o5P9s2D7f4G8\n'])
def test_production_rejects_weak_internal_token(monkeypatch, token):
    production_env(monkeypatch)
    monkeypatch.setenv('AI_INTERNAL_TOKEN', token)
    with pytest.raises(ValueError, match='AI_INTERNAL_TOKEN'): Settings()


@pytest.mark.parametrize('name', ['AI_LLM_PROVIDER', 'AI_CHATGPT_MODEL', 'RAG_RETRIEVAL_PROVIDER',
                                  'RAG_LIVE_SERVICES', 'RAG_RUNTIME_CORPUS_FILE', 'RAG_CONTEXT_SELECTION'])
def test_production_requires_explicit_runtime_settings(monkeypatch, name):
    production_env(monkeypatch)
    monkeypatch.delenv(name)
    with pytest.raises(ValueError, match=name): Settings()


def test_production_config_is_valid_without_startup_calls(monkeypatch):
    production_env(monkeypatch)
    monkeypatch.setattr(chatgpt_auth, 'load', lambda: pytest.fail('No credentials during configuration'))
    assert Settings().production
    monkeypatch.setenv('AI_ENV', 'development')
    monkeypatch.setenv('NODE_ENV', 'test')
    monkeypatch.setenv('ENVIRONMENT', 'test')
    monkeypatch.delenv('AI_INTERNAL_TOKEN')
    assert Settings().agent_internal_token is None
