import json
from unittest.mock import AsyncMock
import pytest
from app.rag.answer_policy import service_clarification,cited_sources
from app.rag.retriever import RetrievedDoc
from app.rag import rag_service


def catalog(tmp_path):
    path=tmp_path/'corpus.json'
    path.write_text(json.dumps([{'id':'db:1','source_type':'db','section':'Keratin Smooth Treatment','file':'services.json','text':'Keratin Smooth Treatment','fields':{'name':'Keratin Smooth Treatment'}},
                                {'id':'db:2','source_type':'db','section':'Signature Hair Spa','file':'services.json','text':'Signature Hair Spa','fields':{'name':'Signature Hair Spa'}}]))
    return path


def test_ambiguous_price_asks_and_lists_without_guessing(tmp_path):
    path=catalog(tmp_path)
    result=service_clarification('Berapa biaya treatment itu?',path)
    assert 'yang mana' in result['reply']
    assert 'Keratin Smooth Treatment' in result['reply'] and 'Signature Hair Spa' in result['reply']
    assert all('- '+name+' [1]' in result['reply'] for name in ('Keratin Smooth Treatment','Signature Hair Spa'))
    assert result['sources'][0]['citation_number']==1
    assert 'Rp' not in result['reply'] and 'Jika yang dimaksud' not in result['reply']
    assert service_clarification('Berapa harga keratin?',path) is None
    assert service_clarification('Bagaimana memakai kondisioner?',path) is None


@pytest.mark.asyncio
async def test_clarification_never_calls_model_or_retriever(tmp_path,monkeypatch):
    monkeypatch.setattr(rag_service.settings,'rag_retrieval_provider','bm25_source_balanced')
    monkeypatch.setattr(rag_service.settings,'rag_corpus_file',catalog(tmp_path))
    retrieve=AsyncMock(side_effect=AssertionError('No similarity lookup'))
    monkeypatch.setattr(rag_service.retriever,'retrieve',retrieve)
    answer=await rag_service.RagService().answer('Berapa biaya treatment itu?',include_trace=True)
    assert answer['_trace']['generation_status']=='policy_clarification'
    assert 'Rp' not in answer['reply']
    retrieve.assert_not_awaited()


def test_only_cited_evidence_returned_not_all_retrieved_docs():
    docs=[RetrievedDoc(id='service1',file='services.snapshot.json',section='Hair Spa',snippet='325000',metadata={'source_type':'db'}),
          RetrievedDoc(id='service2',file='services.snapshot.json',section='Haircut',snippet='220000',metadata={'source_type':'db'}),
          RetrievedDoc(id='care',file='care.md',section='Kondisioner',snippet='care',metadata={'source_url':'https://www.aad.org/example'})]
    reply,sources,trace=cited_sources('Harga [1]. Perawatan [3].',docs)
    assert [s['id'] for s in sources]==['service1','care']
    assert sources[0]['title']=='Data layanan: Hair Spa (snapshot penelitian)'
    assert sources[1]['url']=='https://www.aad.org/example'
    assert trace['entailment_verified'] is False


def test_duplicate_evidence_indices_normalized_and_invalid_removed():
    doc=RetrievedDoc(id='same',file='care.md',section='care',snippet='text')
    reply,sources,trace=cited_sources('A [1], B [2], invalid [99].',[doc,doc])
    assert '[2]' not in reply and '[99]' not in reply
    assert len(sources)==1 and trace['invalid_citation_indices']==[99]
    assert cited_sources('No citation.',[doc])[1]==[]
