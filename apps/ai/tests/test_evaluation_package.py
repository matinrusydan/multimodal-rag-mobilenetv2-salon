import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.rag import eval_rag, rag_service

PACKAGE=Path(__file__).resolve().parents[1]/'rag/eval/curated-development-v2'


@pytest.fixture
def package(tmp_path,monkeypatch):
    target=tmp_path/'package'
    shutil.copytree(PACKAGE,target)
    monkeypatch.setattr(eval_rag,'TESTSET_FILE',target/'questions.json')
    monkeypatch.setattr(eval_rag,'DATASET_PROVENANCE',None)
    monkeypatch.setattr(settings,'rag_corpus_file',target/'corpus.json')
    monkeypatch.setattr(settings,'rag_retrieval_provider','bm25_source_balanced')
    return target


def test_package_references_are_versioned_and_not_legacy_promo(package):
    items=eval_rag.load_testset()
    assert len(items)==24 and '285.000' not in items[0]['ground_truth']
    assert items[0]['dataset_version']=='curated-development-v2'
    assert eval_rag.DATASET_PROVENANCE['publication_ready'] is False
    assert eval_rag.DATASET_PROVENANCE['input_sha256']['corpus.json']
    eval_rag.verify_dataset_unchanged()


@pytest.mark.parametrize('name',['questions.json','corpus.json','evaluation-context.json'])
def test_modified_references_corpus_or_policy_are_rejected(package,name):
    (package/name).write_text('[]',encoding='utf-8')
    with pytest.raises(ValueError,match='changed'):
        eval_rag.load_testset()


def test_legacy_reference_without_manifest_is_rejected(tmp_path,monkeypatch):
    path=tmp_path/'testset.json';path.write_text('[]',encoding='utf-8')
    monkeypatch.setattr(eval_rag,'TESTSET_FILE',path)
    with pytest.raises(ValueError,match='legacy'):
        eval_rag.load_testset()


def test_runtime_corpus_must_match_selected_package(package,monkeypatch):
    eval_rag.load_testset()
    monkeypatch.setattr(settings,'rag_corpus_file',PACKAGE/'corpus.json')
    with pytest.raises(ValueError,match='Runtime corpus'):
        eval_rag.verify_dataset_unchanged()


def test_vector_index_without_provenance_is_not_claimed_to_match_package(package,monkeypatch):
    eval_rag.load_testset()
    monkeypatch.setattr(settings,'rag_retrieval_provider','chroma')
    with pytest.raises(ValueError,match='index provenance'):
        eval_rag.verify_dataset_unchanged()


@pytest.mark.asyncio
async def test_valid_clarification_is_scored_without_retrieval_or_faithfulness_judge(package,monkeypatch):
    item=next(q for q in eval_rag.load_testset() if q['id']=='r21')
    monkeypatch.setattr(settings,'rag_retrieval_provider','bm25_source_balanced')
    judge=AsyncMock(return_value=0)
    monkeypatch.setattr(eval_rag,'eval_answer_relevancy',judge)
    monkeypatch.setattr(eval_rag.asyncio,'sleep',AsyncMock())
    result=await eval_rag.evaluate_one(item)
    assert result['status']=='ok'
    assert result['trace']['generation_status']=='policy_clarification'
    assert result['metrics']['answer_relevancy']==0  # Real zero survives.
    assert result['behavior_evaluation']['clarification_route_match'] is True
    assert result['metric_applicability']['faithfulness'] is False
    assert not eval_rag.retryable_metrics(result)
    summary=eval_rag.summarize([result])
    assert summary['execution_errors']==0
    assert summary['metric_counts']['context_recall']==dict(valid=0,missing=0,zero_scores=0,not_applicable=1)
    judge.assert_awaited_once()


@pytest.mark.asyncio
async def test_unexpected_clarification_is_not_automatically_quality_success(monkeypatch):
    pipeline=AsyncMock(return_value=dict(answer='Layanan mana?',contexts=[],retrieved_docs=[],
                         trace={'generation_status':'policy_clarification'}))
    monkeypatch.setattr(eval_rag,'run_rag_pipeline',pipeline)
    monkeypatch.setattr(eval_rag,'eval_answer_relevancy',AsyncMock(return_value=0))
    monkeypatch.setattr(eval_rag.asyncio,'sleep',AsyncMock())
    result=await eval_rag.evaluate_one(dict(id='new',question='Harga Hair Spa?',ground_truth='325000',answerability='answerable'))
    assert result['behavior_evaluation']['clarification_route_match'] is False
    assert result['metrics']['answer_relevancy']==0


@pytest.mark.asyncio
async def test_catalog_lookup_is_valid_but_not_ranked_retrieval(monkeypatch):
    monkeypatch.setattr(eval_rag,'run_rag_pipeline',AsyncMock(return_value=dict(answer='Catalog answer',contexts=['record'],
        retrieved_docs=[{'id':'db:1'}],trace={'generation_status':'catalog_lookup'})))
    monkeypatch.setattr(eval_rag,'eval_faithfulness',AsyncMock(return_value=1))
    monkeypatch.setattr(eval_rag,'eval_answer_relevancy',AsyncMock(return_value=1))
    monkeypatch.setattr(eval_rag.asyncio,'sleep',AsyncMock())
    result=await eval_rag.evaluate_one(dict(id='catalog',question='Semua layanan?',ground_truth='Catalog'))
    assert result['status']=='ok'
    assert result['metrics']['faithfulness']==1
    assert result['metric_applicability']['context_precision'] is False
    assert result['metric_applicability']['context_recall'] is False


@pytest.mark.asyncio
async def test_cli_invalid_package_fails_before_any_pipeline_call(package,monkeypatch):
    (package/'questions.json').write_text('[]',encoding='utf-8')
    pipeline=AsyncMock(side_effect=AssertionError('Must validate before spending quota'))
    monkeypatch.setattr(eval_rag,'evaluate_one',pipeline)
    with pytest.raises(ValueError,match='changed'):
        await eval_rag.run_cli(SimpleNamespace(retry_failed=False,limit=None))
    pipeline.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_reports_are_preserved(package,monkeypatch,tmp_path):
    output=tmp_path/'existing.json';output.write_text('old report',encoding='utf-8')
    monkeypatch.setattr(eval_rag,'REPORT_JSON',output)
    monkeypatch.setattr(eval_rag,'REPORT_MD',output.with_suffix('.md'))
    with pytest.raises(ValueError,match='not be overwritten'):
        await eval_rag.run_cli(SimpleNamespace(retry_failed=False,limit=None))
    assert output.read_text()=='old report'


@pytest.mark.asyncio
async def test_retry_refuses_another_reference_package(package,monkeypatch,tmp_path):
    path=tmp_path/'report.json'
    path.write_text(json.dumps(dict(protocol=eval_rag.PROTOCOL,judge_model=eval_rag.JUDGE_MODEL,
        generation_model=eval_rag.GENERATION_MODEL,generation_provider=settings.ai_llm_provider,
        retrieval_provider=settings.rag_retrieval_provider,dataset={'wrong':'package'},results=[])),encoding='utf-8')
    monkeypatch.setattr(eval_rag,'REPORT_JSON',path)
    with pytest.raises(ValueError,match='hashes'):
        await eval_rag.run_cli(SimpleNamespace(retry_failed=True,limit=None))
