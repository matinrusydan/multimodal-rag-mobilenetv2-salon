import base64,json,time
from copy import deepcopy
from contextlib import nullcontext
from unittest.mock import AsyncMock
import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from app import chatgpt_auth as auth
from app.rag import chatgpt_plan as plan,rag_service
from app.rag.bm25_retrieval import balanced_order


def b64(data):return base64.urlsafe_b64encode(data).decode().rstrip('=')


def signed_identity(**changes):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    public=key.public_key().public_numbers()
    jwks={'keys':[{'kid':'test','kty':'RSA','n':b64(public.n.to_bytes(256,'big')),'e':b64(public.e.to_bytes(3,'big'))}]}
    claims={'iss':auth.ISSUER,'aud':'client','sub':'subject','exp':time.time()+60,'nonce':'nonce',**changes}
    head=b64(json.dumps({'alg':'RS256','kid':'test'}).encode());body=b64(json.dumps(claims).encode())
    token=head+'.'+body
    return token+'.'+b64(key.sign(token.encode(),padding.PKCS1v15(),hashes.SHA256())),jwks


@pytest.mark.parametrize('changes',[{'nonce':'wrong'},{'aud':'other'},{'iss':'https://example.com'},{'exp':0}])
def test_invalid_identity_rejected(changes):
    token,jwks=signed_identity(**changes)
    with pytest.raises(ValueError):auth.verify_identity(token,'client','nonce',jwks)


def test_signed_identity_verified_and_scope_not_inferred():
    token,jwks=signed_identity()
    assert auth.verify_identity(token,'client','nonce',jwks)['sub']=='subject'
    with pytest.raises(ValueError,match='izin'):
        auth._apply_tokens({},dict(access_token='fake',token_type='Bearer',expires_in=60,scope='openid'))


def test_dedicated_store_roundtrip_and_no_codex_credentials(tmp_path,monkeypatch):
    file=tmp_path/'app.credentials';monkeypatch.setattr(auth,'auth_path',lambda:file)
    p={'access_token':'test-only-secret','scopes':[auth.PLAN_SCOPE]}
    auth.save(p);assert auth.load()==p
    if auth.os.name=='nt':assert b'test-only-secret' not in file.read_bytes()


@pytest.mark.skipif(auth.os.name!='nt',reason='Windows known-folder regression')
def test_auth_location_stable_when_turbo_filters_windows_environment(monkeypatch):
    before=auth.auth_path()
    for key in ['LOCALAPPDATA','APPDATA','USERPROFILE']:
        monkeypatch.delenv(key,raising=False)
    assert auth.auth_path()==before
    assert before.parts[-3:]==('Local','RAGSalon','chatgpt-plan.credentials')


@pytest.mark.asyncio
@pytest.mark.parametrize('completed',[True,False])
async def test_plan_stream_requires_completion_and_never_uses_paid_key(monkeypatch,completed):
    monkeypatch.setattr(auth,'access_token',lambda:'fake-plan-token')
    monkeypatch.setattr(plan.settings,'chatgpt_model','account-model')
    requests=[]
    def handler(request):
        requests.append(request)
        body=json.loads(request.content)
        assert body['store'] is False and body['stream'] is True
        assert 'max_output_tokens' not in body
        assert all(item.get('role')!='system' for item in body['input'])
        assert request.headers['authorization']=='Bearer fake-plan-token'
        assert str(request.url)=='https://api.openai.com/v1/responses'
        event={'type':'response.completed' if completed else 'response.incomplete',
               'response':{'status':'completed' if completed else 'incomplete','output':[{'type':'message','content':[{'type':'output_text','text':'Jawaban uji'}]}]}}
        return httpx.Response(200,text='data: '+json.dumps(event)+'\n\n',headers={'Content-Type':'text/event-stream'})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(plan.httpx,'AsyncClient',lambda **kwargs:client)
    if completed:assert await plan.generate([{'role':'system','content':'aturan'},{'role':'user','content':'uji'}])=='Jawaban uji'
    else:
        with pytest.raises(RuntimeError,match='complete'):await plan.generate([{'role':'user','content':'uji'}])
    assert len(requests)==1


@pytest.mark.asyncio
async def test_stream_deltas_survive_empty_completed_envelope(monkeypatch):
    monkeypatch.setattr(auth,'access_token',lambda:'fake-plan-token')
    monkeypatch.setattr(plan.settings,'chatgpt_model','account-model')
    events=[{'type':'response.output_text.delta','delta':'koneksi '},
            {'type':'response.output_text.delta','delta':'berhasil'},
            {'type':'response.completed','response':{'status':'completed','output':[]}}]
    client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,
        text=''.join('data: '+json.dumps(e)+'\n\n' for e in events))))
    monkeypatch.setattr(plan.httpx,'AsyncClient',lambda **kwargs:client)
    assert await plan.generate([{'role':'user','content':'uji'}])=='koneksi berhasil'


@pytest.mark.asyncio
async def test_bm25_chatgpt_generation_independent_of_embedding_key(monkeypatch):
    from app.rag import bm25_retrieval
    monkeypatch.setattr(rag_service.settings,'ai_llm_provider','chatgpt')
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(plan.settings,'chatgpt_model','pinned-model')
    monkeypatch.setattr(plan,'available',lambda:True)
    monkeypatch.setattr(plan,'generate',AsyncMock(return_value='Jawaban uji'))
    monkeypatch.setattr(bm25_retrieval,'retrieve',lambda *args:[])
    monkeypatch.setattr(bm25_retrieval,'evaluation_policy_context',lambda:'snapshot only')
    embedding=AsyncMock(side_effect=AssertionError('Embedding must not be called'))
    monkeypatch.setattr(rag_service,'embed',embedding)
    result=await rag_service.RagService().answer('uji',allow_web=False,include_trace=True)
    assert result['_trace']['generation_status']=='llm_success'
    assert result['_trace']['actual_generation_model']=='pinned-model'
    assert 'snapshot only' in result['_trace']['prompt_messages'][0]['content']
    embedding.assert_not_awaited()


def test_balanced_selection_reserves_sources_without_reading_labels():
    corpus=[{'id':str(i),'source_type':'db','section':'Example Hair Spa','text':'harga Example Hair Spa durasi',
              'fields':{'name':'Example Hair Spa'}} for i in range(4)]
    corpus += [{'id':'care-a','source_type':'official_professional_guidance','section':'Perawatan','text':'rambut kering kondisioner'},
               {'id':'care-b','source_type':'official_professional_guidance','section':'Kondisioner','text':'kondisioner rambut'}]
    original=deepcopy(corpus)
    order=balanced_order('harga Example Hair Spa dan kondisioner untuk rambut kering',corpus,5)
    assert {'care-a','care-b'}<={corpus[i]['id'] for i in order}
    assert corpus[order[0]]['source_type']=='db'
    assert len(set(order))==5 and corpus==original


def test_refresh_rotates_tokens_and_uses_issued_client(monkeypatch):
    profile={'client_id':'issued-client','subject':'subject','access_token':'old',
             'refresh_token':'old-refresh','scopes':[auth.PLAN_SCOPE],'expires_at':0}
    monkeypatch.setattr(auth,'load',lambda:dict(profile))
    monkeypatch.setattr(auth,'save',lambda p:profile.update(p))
    monkeypatch.setattr(auth,'session_lock',nullcontext)
    calls=[]
    def handler(request):
        calls.append(request)
        assert b'client_id=issued-client' in request.content
        assert b'dynamic_agent_client' not in request.content
        return httpx.Response(200,json={'access_token':'new','refresh_token':'new-refresh','expires_in':3600,'token_type':'Bearer'})
    client=httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(auth.httpx,'Client',lambda **kwargs:client)
    assert auth.access_token()=='new'
    assert profile['refresh_token']=='new-refresh'
    assert auth.access_token()=='new'
    assert len(calls)==1


@pytest.mark.asyncio
async def test_admin_tool_results_are_passed_back_before_answer(monkeypatch):
    from app.rag import agent_service
    request=AsyncMock(side_effect=[{'status':'completed','output':[{'type':'function_call','name':'get_services_summary','call_id':'c1','arguments':'{}'}]},
                                  {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Ringkasan'}]}]}])
    monkeypatch.setattr(plan,'response',request)
    execute=AsyncMock(return_value={'ok':True,'result':{'count':6}})
    monkeypatch.setattr(agent_service,'execute_tool',execute)
    result=await agent_service.AgentService()._call_chatgpt_with_tools('layanan',[],[])
    assert result['reply']=='Ringkasan'
    execute.assert_awaited_once_with('get_services_summary',{})
    assert any(item.get('type')=='function_call_output' and item['call_id']=='c1' for item in request.call_args.args[0])
