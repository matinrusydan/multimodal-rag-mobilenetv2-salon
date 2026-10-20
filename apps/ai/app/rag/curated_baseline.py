"""Offline BM25 diagnosis of a versioned curated development set. No APIs or ingest."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from app.rag.pilot import ROOT, bm25_scores, metrics


def evaluate(corpus: list[dict], questions: list[dict], k: int = 5, *, selector=None, method='bm25') -> dict:
    if k < 1:
        raise ValueError('top-k must be positive')
    ids = {d['id'] for d in corpus}
    if len(ids) != len(corpus):
        raise ValueError('Duplicate evidence IDs')
    if len({q['id'] for q in questions}) != len(questions):
        raise ValueError('Duplicate question IDs')
    texts = [d['section']+'\n'+d['text'] for d in corpus]
    rows = []
    for q in questions:
        groups = q['required_evidence_groups']
        if any(not g for g in groups):
            raise ValueError('Empty required group: '+q['id'])
        gold = {eid for g in groups for eid in g}
        if not gold <= ids or gold != set(q['relevant_evidence_ids']):
            raise ValueError('Evidence labels do not resolve or disagree: '+q['id'])
        if bool(gold) != q['retrieval_scoring_applicable']:
            raise ValueError('Scoring applicability disagrees with labels: '+q['id'])
        scores = bm25_scores(q['question'], texts)
        order = sorted(range(len(corpus)), key=lambda i: (-scores[i], corpus[i]['id']))
        selected = selector(q['question'],corpus,k) if selector else order[:k]
        chosen = [corpus[i] for i in selected]
        score = metrics([d['id'] for d in chosen], sorted(gold), groups) if gold else None
        rows.append(dict(id=q['id'],question=q['question'],category=q['category'],answerability=q['answerability'],
                         scoring_applicable=bool(gold),metrics=score,
                         retrieved=[dict(id=corpus[i]['id'],section=corpus[i]['section'],source_type=corpus[i]['source_type'],
                                         score=scores[i],snippet=corpus[i]['text'][:400]) for i in selected],
                         required_evidence_groups=groups,
                         gold_ranks={eid:next(rank for rank,i in enumerate(order,1) if corpus[i]['id']==eid) for eid in sorted(gold)},
                         missing_groups=[g for g in groups if not set(g)&{d['id'] for d in chosen}],
                         generation_status='not_run',behavior_status='not_evaluated',answer=None))
    summary = {}
    for category in ['all']+sorted({q['category'] for q in questions}):
        subset = [r for r in rows if category=='all' or r['category']==category]
        scored = [r for r in subset if r['scoring_applicable']]
        summary[category] = dict(total=len(subset),scored=len(scored),excluded=len(subset)-len(scored),
                                 **{key:sum(r['metrics'][key] for r in scored)/len(scored) if scored else None
                                    for key in ('precision','recall','f1','complete_evidence')})
    return dict(protocol='curated_development_diagnosis_only',method=method,top_k=k,bm25_k1=1.5,bm25_b=0.75,
                snippet_char_limit=400,corpus_size=len(corpus),question_count=len(questions),
                summary=summary,results=rows,
                limitations=['Labels and revised wording remain researcher-review candidates, not final gold.',
                             'Only annotated supported factual needs are measured; partial answers can have perfect retrieval.',
                             'No score is assigned to questions without gold; behavior and generation are not run.',
                             'Recall uses union of relevant IDs; groups are also reported for coverage. Current groups are singletons.',
                             'Evidence ID hits do not establish claim support after snippet truncation.',
                             'Small selected development corpus; no held-out evaluation or algorithm improvement claim.',
                             'Not comparable to old pilot scores as an isolated algorithm change.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'apps/ai/rag/eval/curated-development-v1')
    parser.add_argument('--out',type=Path,default=ROOT/'apps/ai/rag/eval/curated-baseline-v1')
    parser.add_argument('--top-k',type=int,default=5)
    args=parser.parse_args()
    if args.out.exists():
        parser.error('Choose a new output directory; previous results will not be overwritten')
    input_files = ['corpus.json','questions.json','source-register.json','evaluation-context.json','protocol.json']
    original = {name:(args.input/name).read_bytes() for name in input_files}
    manifest = json.loads((args.input/'manifest.json').read_text(encoding='utf-8'))
    for name,value in original.items():
        if hashlib.sha256(value).hexdigest()!=manifest['output_sha256'][name]:
            raise ValueError('Input changed since creation: '+name)
    corpus,questions,sources,context,protocol = [json.loads(original[n]) for n in input_files]
    report=evaluate(corpus,questions,args.top_k)
    report['input_sha256']={name:hashlib.sha256(value).hexdigest() for name,value in original.items()}
    policies={p['id'] for p in context['policy_instructions']}
    source_ids={s['id'] for s in sources['selected_sources']}
    checks=[]
    for q in questions:
        if not set(q['always_available_policy_ids'])<=policies:
            raise ValueError('Unresolved policy reference: '+q['id'])
        checks.append(dict(id=q['id'],evidence_and_policy_ids_resolve=True,
                           new_manual_validation_recorded=False,
                           note='Prior narrative retained as lineage; no new approval inferred.'))
    assert all(d.get('source_id') in source_ids for d in corpus if d['source_type']!='db')
    assert protocol['retrieval_scoreable']==report['summary']['all']['scored']
    assert all((args.input/name).read_bytes()==value for name,value in original.items())
    report['reference_checks']=dict(structural_checks=checks,
                                    semantic_claim_support='source audit available; not independently re-annotated in this run',
                                    policy_context='prepared for equal use across configurations; no generation run',
                                    expected_business_facts_note='Do not demand every stored field in every answer; judge only the facts requested by the question.')
    args.out.mkdir(parents=True)
    (args.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Baseline BM25 — curated development v1','',
           f"{len(corpus)} evidence, {len(questions)} pertanyaan. Top-{args.top_k}; BM25 k1=1,5 dan b=0,75. Tidak ada API, generasi, atau perubahan index.",'',
           'Acuan dan pemetaan bukti baru masih kandidat. Pemeriksaan otomatis memastikan ID, sumber, kebijakan dan hash konsisten; bukan pengganti penilaian semantik manusia.','',
           '| Kategori | Dinilai/total | Precision | Recall | F1 retrieval | Bukti lengkap |','|---|---|---|---|---|---|']
    for category,s in report['summary'].items():
        values=' | '.join('NA' if s[k] is None else f'{s[k]:.3f}' for k in ('precision','recall','f1','complete_evidence'))
        lines.append(f"| {category} | {s['scored']}/{s['total']} | {values} |")
    lines+=['','## Kegagalan menemukan kelompok bukti','']
    failures=[r for r in report['results'] if r['missing_groups']]
    if not failures:lines+=['Tidak ada kelompok gold yang terlewat pada pertanyaan yang dinilai. Ini tetap tidak membuktikan jawaban generasi benar atau semua kebutuhan terpenuhi.']
    for row in failures:
        lines += [f"### {row['id']}",'',row['question'],'',
                  'Kelompok terlewat: '+json.dumps(row['missing_groups'],ensure_ascii=False),'',
                  'Urutan bukti gold: '+json.dumps(row['gold_ranks'],ensure_ascii=False),'',
                  'Top-k: '+', '.join(d['section'] for d in row['retrieved'])+'.','']
    lines+=['','## Batas interpretasi','',
            'Precision adalah proporsi ID gold dalam evidence yang diambil; recall adalah proporsi ID gold terambil. F1 retrieval dihitung per pertanyaan lalu dirata-ratakan. Kelengkapan bernilai 1 jika setiap kelompok wajib terwakili. Saat ini seluruh kelompok berisi satu ID.','',
            'r08, r20, r21 dan r22 tidak memiliki gold retrieval dan dikeluarkan dari denominator; tidak dinyatakan berhasil. Kepatuhan kebijakan, klarifikasi, penolakan resep, dan abstention belum diuji. Kasus partial hanya menilai kebutuhan faktual yang didukung, misalnya harga; skor tinggi tidak membuktikan saran sampo atau instruksi perawatan khusus benar.','',
            'Seluruh teks kandidat diperingkatkan, tetapi cuplikan hasil dibatasi 400 karakter per evidence. Hit pada ID tidak memverifikasi setiap klaim dalam cuplikan. Atribut expected_business_facts dapat memuat field konteks yang tidak diminta pertanyaan; jangan menghukum jawaban karena tidak menyebut field yang tidak ditanyakan.','',
            'Korpus kecil dan diseleksi berdasarkan inspeksi development. Jangan membandingkan skor ini dengan pilot lama sebagai efek peningkatan algoritma, karena korpus dan label berubah. Tidak ada keluaran neural dense, RAGAS, faithfulness, atau akurasi jawaban yang dibuat dari tes ini.','',
            'Langkah berikut: audit error per pertanyaan dan bukti alternatif; perluas korpus/keluarga pertanyaan; tinjau pemetaan sebelum pembekuan gold. Jika menjalankan variasi algoritma, gunakan korpus/pertanyaan/budget yang sama dan pisahkan test final.']
    (args.out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],ensure_ascii=False,indent=2))


if __name__=='__main__':main()
