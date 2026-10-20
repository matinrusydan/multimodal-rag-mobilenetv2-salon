"""Check exploration controls independently of any expected improvement."""
import copy
import json

from app.rag.algorithm_trial import METHODS, mmr, plan, rrf, run, select
from app.rag.pilot import DEFAULT_OUT, bm25_scores


def fixture_corpus():
    return [
        {'id': 'db:1', 'source_type': 'db', 'section': 'Example Care', 'text': 'harga Example Care 100 durasi 60', 'fields': {'name': 'Example Care'}},
        {'id': 'md:1', 'source_type': 'manual_legacy', 'section': 'Kondisioner', 'text': 'kondisioner digunakan pada ujung rambut'},
        {'id': 'md:2', 'source_type': 'manual_legacy', 'section': 'Katalog', 'text': 'harga Example Care durasi layanan'},
    ]


def test_catalog_names_do_not_create_a_care_intent():
    c = fixture_corpus()
    c[0]['fields']['name'] = 'Perawatan Kering'
    assert plan('Berapa harga Perawatan Kering?', c)['document'] is False
    assert plan('Berapa harga Perawatan Kering dan kondisioner dipakai di mana?', c)['document'] is True


def test_two_source_reservations_and_small_budget():
    c = fixture_corpus()
    orders, _ = select('Berapa harga Example Care dan kondisioner di mana?', c, 2)
    selected = [c[i]['source_type'] for i in orders['bm25_routed_decomposed']]
    assert selected == ['db', 'manual_legacy']
    for k in (1, 2, 5):
        orders, _ = select('harga dan kondisioner', c, k)
        assert all(len(order) == min(k, len(c)) and len(order) == len(set(order)) for order in orders.values())


def test_rrf_repeated_item_and_tie_are_deterministic():
    c = fixture_corpus()
    assert rrf([[1, 0, 2], [0, 1, 2]], c) == [0, 1, 2]
    assert rrf([[1, 0], [1, 2]], c)[0] == 1


def test_mmr_redundancy_penalty_can_change_selection():
    c = fixture_corpus()
    chosen = mmr([0, 1, 2], [1, .99, .9], ['same words', 'same words', 'different topic'], c, 2)
    assert chosen == [0, 2]


def test_labels_do_not_enter_selection_and_inputs_remain_unchanged():
    c = fixture_corpus()
    original = copy.deepcopy(c)
    q = [{'id': 'x', 'category': 'mixed', 'question': 'harga dan kondisioner',
          'relevant_evidence_ids': ['db:1'], 'required_evidence_groups': [['db:1']]}]
    a = run(c, q)
    q[0].update(category='document', relevant_evidence_ids=['md:2'], required_evidence_groups=[['md:2']])
    b = run(c, q)
    assert [r['selected_ids'] for r in a['results']] == [r['selected_ids'] for r in b['results']]
    assert c == original


def test_baseline_exactly_reproduces_frozen_pilot():
    c = json.loads((DEFAULT_OUT/'corpus.json').read_text(encoding='utf-8'))
    q = json.loads((DEFAULT_OUT/'questions.json').read_text(encoding='utf-8'))
    old = json.loads((DEFAULT_OUT/'retrieval_report.json').read_text(encoding='utf-8'))
    new = run(c, q)
    expected = {r['id']: [d['id'] for d in r['actual_context']] for r in old['results'] if r['method'] == 'bm25'}
    assert all(r['selected_ids'] == expected[r['id']] for r in new['results'] if r['method'] == 'bm25')
    assert len(new['results']) == len(q) * len(METHODS)
    assert new['summary']['bm25']['all']['scored'] == 21
    assert max(len(d['snippet']) for r in new['results'] for d in r['contexts']) <= 400


def test_raw_bm25_selection_is_score_order_not_fixture_label_order():
    c = fixture_corpus()
    text = [d['section']+'\n'+d['text'] for d in c]
    scores = bm25_scores('kondisioner ujung', text)
    assert select('kondisioner ujung', c)[0]['bm25'][0] == scores.index(max(scores))
