"""Evaluation controls: real misses, exclusions, and selection independent of labels."""
from copy import deepcopy
import pytest
from app.rag.curated_baseline import evaluate


def inputs():
    corpus=[{'id':'a','section':'Harga','text':'harga haircut','source_type':'db'},
            {'id':'b','section':'Rambut','text':'kondisioner keriting','source_type':'official_professional_guidance'}]
    questions=[{'id':'q','question':'harga haircut','category':'mixed','answerability':'answerable',
                'required_evidence_groups':[['a'],['b']],'relevant_evidence_ids':['a','b'],'retrieval_scoring_applicable':True},
               {'id':'u','question':'berapa dosis','category':'policy_boundary','answerability':'unanswerable',
                'required_evidence_groups':[],'relevant_evidence_ids':[],'retrieval_scoring_applicable':False}]
    return corpus,questions


def test_missing_group_is_a_failure_and_unanswerable_not_counted():
    corpus,questions=inputs()
    report=evaluate(corpus,questions,1)
    assert report['summary']['all']['scored']==1
    assert report['summary']['all']['excluded']==1
    assert report['summary']['all']['recall']==.5
    assert report['summary']['all']['complete_evidence']==0
    assert report['results'][0]['missing_groups']==[['b']]
    assert report['results'][1]['metrics'] is None
    assert report['results'][1]['answer'] is None


def test_changing_gold_changes_score_but_not_retrieved_evidence():
    corpus,questions=inputs()
    before=deepcopy((corpus,questions))
    first=evaluate(corpus,questions,1)
    assert (corpus,questions)==before
    questions[0].update(required_evidence_groups=[['b']],relevant_evidence_ids=['b'])
    second=evaluate(corpus,questions,1)
    assert first['results'][0]['retrieved']==second['results'][0]['retrieved']
    assert second['results'][0]['metrics']['recall']==0


def test_invalid_labels_cannot_silently_enter_denominator():
    corpus,questions=inputs()
    questions[0]['relevant_evidence_ids']=['unknown']
    with pytest.raises(ValueError,match='Evidence labels'):
        evaluate(corpus,questions)
    corpus,questions=inputs()
    questions[0]['retrieval_scoring_applicable']=False
    with pytest.raises(ValueError,match='Scoring applicability'):
        evaluate(corpus,questions)
