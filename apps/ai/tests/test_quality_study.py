from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.rag.evidence_selection import select_evidence
from app.rag.quality_study import offline_audit,parse_judgment,score_judgment,judge_payload
from app.rag.resume_quality import pending_answers,summarize

PACKAGE=Path(__file__).resolve().parents[1]/'rag/eval/curated-development-v2'


def test_selection_reduces_context_without_hiding_fixed_k_denominator_or_gold_loss():
    corpus=json.loads((PACKAGE/'corpus.json').read_text(encoding='utf-8'))
    questions=json.loads((PACKAGE/'questions.json').read_text(encoding='utf-8'))
    original=deepcopy((corpus,questions))
    result=offline_audit(corpus,questions)
    assert (corpus,questions)==original
    before=result['context_summary']['all'];after=result['context_summary']['source_scoped']
    assert result['selection_gate']['no_per_question_gold_coverage_loss']
    assert before['precision_at_5']==after['precision_at_5']==.25
    assert before['f1_at_5']==after['f1_at_5']
    assert after['precision_returned']>before['precision_returned']
    assert after['mean_context_characters']<before['mean_context_characters']
    assert all(r['semantic_reference_approval']=='not_performed_by_structural_audit' for r in result['reference_audit'])


def test_unique_phrase_does_not_drop_a_separate_explicit_need():
    corpus=[dict(id='heat',source_type='education',section='Panas',text='Batasi alat styling panas.'),
            dict(id='conditioner',source_type='education',section='Kondisioner',text='Gunakan kondisioner setelah keramas.')]
    indices,trace=select_evidence('Bagaimana menggunakan alat styling panas dan kondisioner?',corpus,[0,1])
    assert indices==[0,1] and trace['selection_uses_gold'] is False


@pytest.mark.parametrize('caveat',[
    'Jangan gunakan kondisioner pada akar rambut.',
    'Untuk rambut lurus gunakan kondisioner hanya pada ujung rambut.',
    'Jika kulit kepala perih hentikan penggunaan kondisioner.',
    'Avoid conditioner on the scalp.',
])
def test_ordered_phrase_cannot_erase_distinct_care_caveats(caveat):
    corpus=[dict(id='general',source_type='education',section='Perawatan',text='Gunakan kondisioner setelah keramas.'),
            dict(id='caveat',source_type='education',section='Perawatan',text=caveat)]
    selected,trace=select_evidence('Cara gunakan kondisioner?',corpus,[0,1])
    assert selected==[0,1]
    # Some caveats also have unique query words and are retained before compression.
    assert trace['selection_uses_gold'] is False


def test_identical_caveat_does_not_prevent_safe_lexical_compression():
    corpus=[dict(id='full',source_type='education',section='Perawatan',text='Gunakan kondisioner setelah keramas. Hindari akar rambut.'),
            dict(id='copy',source_type='education',section='Perawatan',text='Hindari akar rambut.')]
    selected,_=select_evidence('Cara gunakan kondisioner?',corpus,[0,1])
    assert selected==[0]


def test_named_record_filter_does_not_remove_required_document():
    corpus=[dict(id='spa',source_type='db',section='Hair Spa',text='Harga',fields={'name':'Hair Spa'}),
            dict(id='other',source_type='db',section='Haircut',text='Harga',fields={'name':'Haircut'}),
            dict(id='care',source_type='education',section='Kondisioner',text='Kondisioner pada batang rambut.')]
    indices,_=select_evidence('Berapa harga Hair Spa dan bagaimana memakai kondisioner?',corpus,[0,1,2])
    assert indices==[0,2]


def test_service_name_styling_is_not_an_extra_document_request():
    corpus=[dict(id='service',source_type='db',section='Volume Blowout Styling',text='Harga dan durasi',fields={'name':'Volume Blowout Styling'}),
            dict(id='care',source_type='education',section='Styling panas',text='Batasi alat panas.')]
    indices,_=select_evidence('Berapa harga dan durasi Volume Blowout Styling?',corpus,[0,1])
    assert indices==[0]


@pytest.mark.parametrize('need',['cara memakai conditioner','penggunaan shampoo','cara membatasi panas'])
def test_common_document_wording_is_not_dropped_from_mixed_business_question(need):
    corpus=[dict(id='spa',source_type='db',section='Signature Hair Spa',text='Harga',fields={'name':'Signature Hair Spa'}),
            dict(id='care',source_type='education',section='Perawatan',text='Kondisioner shampoo dan panas.')]
    indices,_=select_evidence('Berapa harga Signature Hair Spa dan '+need+'?',corpus,[0,1])
    assert indices==[0,1]


def judgment():
    return dict(results=[dict(id='q',answer_relevancy=0,
        claims=[dict(text='Unsupported claim',supported=False,support_ids=[],citation_required=True,citation_supported=False)],
        required_units=[dict(text='Required answer',covered=False)])])


def test_judge_payload_omits_internal_metadata_and_does_not_repeat_policies():
    row=dict(id='q',question='Question',reference='Reference',reply='Answer',
        _trace={'retrieved_docs':[dict(id='evidence',metadata={'source_file':'private/path'})],'contexts':['Exact excerpt']},
        sources=[dict(id='evidence',snippet='Exact excerpt',file='private/path',citation_number=1)])
    payload,expected=judge_payload([row,{**row,'id':'q2'}],[dict(id='POL',text='Shared rule',source_file='private/annotator')])
    serialized=json.dumps(payload)
    assert 'private' not in serialized and serialized.count('Shared rule')==1
    assert expected['q']=={'evidence','POL'}
    assert payload['cases'][0]['citations']==[dict(id='evidence',citation_number=1)]


def test_judge_zero_scores_are_not_missing_or_filtered_out():
    row=parse_judgment(json.dumps(judgment()),{'q':{'source'}})[0]
    assert all(value==0 for value in score_judgment(row).values())


def test_resume_selects_only_missing_and_keeps_historical_rows_unchanged():
    metrics=dict(faithfulness=0,answer_relevancy=0,citation_support=None,reference_unit_coverage=0)
    report=dict(answer_evaluation=dict(results=[
        dict(id='done',status='ok',judge_metrics=metrics),
        dict(id='pending',status='ok',judge_metrics=None,reply='Saved answer',_trace={}),
        dict(id='failed',status='pipeline_error',judge_metrics=None)]))
    before=deepcopy(report)
    rows,pending=pending_answers(report)
    assert [r['id'] for r in pending]==['pending']
    pending[0]['judge_metrics']=metrics
    assert report==before
    summary=summarize(rows)
    assert summary['judged']==2
    assert summary['metrics']['faithfulness']['mean']==0
    assert summary['metrics']['faithfulness']['missing']==1
    assert summary['metrics']['citation_support']['not_applicable']==2


def test_judge_cannot_invent_claims_absent_from_saved_answer():
    value=json.dumps(judgment())
    with pytest.raises(ValueError,match='actual answer'):
        parse_judgment(value,{'q':{'source'}},{'q':'A different answer'})
    assert parse_judgment(value,{'q':{'source'}},{'q':'**Unsupported claim**.'})


@pytest.mark.parametrize('mutation', ['unknown_id','unknown_support','missing_support','invalid_relevancy','missing_units'])
def test_malformed_or_unverifiable_judge_labels_are_rejected(mutation):
    value=judgment();row=value['results'][0]
    if mutation=='unknown_id':row['id']='other'
    if mutation=='unknown_support':row['claims'][0]['support_ids']=['invented']
    if mutation=='missing_support':row['claims'][0]['supported']=True
    if mutation=='invalid_relevancy':row['answer_relevancy']=True
    if mutation=='missing_units':row['required_units']=[]
    with pytest.raises(ValueError):parse_judgment(json.dumps(value),{'q':{'source'}})
