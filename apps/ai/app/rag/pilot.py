"""Reproducible, API-free retrieval pilot; never writes the production vector store.

Run from apps/ai: python -m app.rag.pilot --help
Hash retrieval is an engineering proxy, NOT a neural dense baseline.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import time

from app.rag.chunker import chunk_markdown

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUT = ROOT / 'apps/ai/rag/eval/pilot'
KB = ROOT / 'apps/ai/rag/knowledge'
TOPICS = {'harga.md': 'harga', 'layanan.md': 'layanan', 'panduan-layanan.md': 'layanan',
          'gaya-rambut.md': 'gaya-rambut', 'tips-perawatan.md': 'tips-perawatan', 'booking-info.md': 'booking-info'}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def tokens(text: str) -> list[str]:
    return re.findall(r'\w+', text.casefold())


def bm25_scores(query: str, texts: list[str]) -> list[float]:
    documents = [tokens(text) for text in texts]
    n = len(documents)
    if not n:
        return []
    avg = sum(map(len, documents)) / n or 1
    df = Counter(word for doc in documents for word in set(doc))
    scores = []
    for doc in documents:
        counts = Counter(doc)
        value = 0.0
        for word in set(tokens(query)):
            f = counts[word]
            idf = math.log(1 + (n - df[word] + 0.5) / (df[word] + 0.5))
            value += idf * f * 2.5 / (f + 1.5 * (0.25 + 0.75 * len(doc) / avg))
        scores.append(value)
    return scores


def hash_vector(text: str) -> dict[int, float]:
    # A transparent lexical feature-hash control, not learned semantic embeddings.
    features = Counter(tokens(text))
    vector: dict[int, float] = {}
    for word, count in features.items():
        digest = hashlib.sha256(word.encode('utf-8')).digest()
        key = int.from_bytes(digest[:4], 'big') % 768
        vector[key] = vector.get(key, 0) + count * (1 if digest[4] & 1 else -1)
    norm = math.sqrt(sum(v*v for v in vector.values())) or 1
    return {k: v/norm for k, v in vector.items()}


def metrics(retrieved: list[str], relevant: list[str], groups: list[list[str]]) -> dict:
    found, gold = set(retrieved), set(relevant)
    if not gold:
        return dict(precision=None, recall=None, f1=None, complete_evidence=None)
    hits = len(found & gold)
    p = hits / len(retrieved) if retrieved else 0.0
    r = hits / len(gold)
    return dict(precision=p, recall=r, f1=2*p*r/(p+r) if p+r else 0.0,
                complete_evidence=float(all(found.intersection(group) for group in groups)))


def build_corpus(snapshot: dict) -> tuple[list[dict], list[dict]]:
    if snapshot.get('status') != 'captured' or snapshot.get('source') != 'postgresql.services':
        raise ValueError('A captured PostgreSQL snapshot is required; seed/Markdown prices are not substitutes')
    corpus, inventory = [], []
    for record in snapshot['records']:
        fields = {k: record[k] for k in ['id', 'slug', 'name', 'price', 'duration_min', 'description', 'category', 'updated_at']}
        text = f"Layanan: {record['name']}\nHarga reguler: Rp{record['price']:,}\nDurasi: {record['duration_min']} menit\nDeskripsi: {record['description']}"
        corpus.append(dict(id=f"db:services:{record['id']}", text=text, source_type='db', topic='katalog',
                           file='services.snapshot.json', section=record['name'], fields=fields,
                           captured_at=snapshot['captured_at'], sha256=sha(text), review_status='snapshot_verified_not_owner_validated'))
    for path in sorted(KB.glob('*.md')):
        text = path.read_text(encoding='utf-8')
        body = re.sub(r'\A---\s*\n.*?\n---\s*\n', '', text, count=1, flags=re.S)
        match = re.search(r'^topic:\s*(.+)$', text, re.M)
        topic = match.group(1).strip() if match else TOPICS.get(path.name)
        chunks = chunk_markdown(body, {'minTokens': 500, 'maxTokens': 1000, 'overlapTokens': 100, 'mergeSections': False})
        inventory.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(text), topic=topic,
                              source_type='manual_legacy', external_source=None, chunks=len(chunks),
                              review_status='unverified; engineering-only; not clinical gold',
                              robots_status='not_applicable_local_file'))
        for i, chunk in enumerate(chunks):
            corpus.append(dict(id=f"md:{path.name}:{sha(text)[:12]}:{i}", text=chunk.text, topic=topic,
                               file=path.name, section=chunk.section, source_type='manual_legacy',
                               sha256=sha(chunk.text), review_status='pending_content_review'))
    return corpus, inventory


def build_questions(corpus: list[dict]) -> list[dict]:
    services = {item['fields']['slug']: item for item in corpus if item['source_type'] == 'db'}

    def db(slug):
        if slug not in services:
            raise ValueError(f'Required service missing from snapshot: {slug}')
        return [services[slug]['id']]

    def section(filename, heading):
        matches = [item['id'] for item in corpus if item['file'] == filename and item['section'] == heading]
        if not matches:
            raise ValueError(f'Evidence section missing: {filename} / {heading}')
        return matches

    basic = section('tips-perawatan.md', 'Perawatan Dasar')
    after = section('tips-perawatan.md', 'Perawatan Setelah Treatment di Salon')
    curly = section('tips-perawatan.md', 'Rambut Keriting')
    damaged = section('panduan-layanan.md', 'Rambut Rusak / Bercabang')
    dry = section('panduan-layanan.md', 'Rambut Kering / Kusam')
    loss = section('panduan-layanan.md', 'Rambut Rontok')
    warning = section('tips-perawatan.md', 'Tanda Rambut Perlu Perhatian')
    rows = []

    def add(category, question, groups, expected, answerability='answerable', scenario='normal'):
        evidence = sorted({x for group in groups for x in group})
        rows.append(dict(id=f'p{len(rows)+1:02d}', category=category, question=question,
                         origin='assistant_drafted_for_researcher', split='pilot_development_only', answerability=answerability,
                         relevant_evidence_ids=evidence, required_evidence_groups=groups,
                         reference_answer=expected, expected_business_facts=[], scenario=scenario,
                         annotation_status='assistant_draft; human_validation_pending',
                         clinical_validation='not_validated; do not use as medical recommendation gold'))
        for item in corpus:
            if item['id'] in evidence and item['source_type'] == 'db':
                rows[-1]['expected_business_facts'].append({k: item['fields'][k] for k in ['id', 'name', 'price', 'duration_min']})

    slugs = ['signature-hair-spa','precision-haircut','keratin-smooth-treatment','color-gloss-refresh','scalp-detox-therapy','volume-blowout-styling']
    for slug in slugs:
        item = services[slug]['fields']
        add('database', f"Berapa harga reguler dan durasi {item['name']} yang tercatat?", [db(slug)],
            f"{item['name']}: harga reguler Rp{item['price']:,}, durasi {item['duration_min']} menit, sesuai snapshot. Promo tidak diasumsikan.")
    for question, group, expected in [
        ('Menurut panduan, kondisioner digunakan di bagian rambut mana?',basic,'Bagian tengah hingga ujung; hindari akar.'),
        ('Menurut panduan, sampo seperti apa yang digunakan setelah pewarnaan?',after,'Sampo khusus warna; ikuti instruksi stylist.'),
        ('Apa catatan panduan mengenai menyisir rambut keriting saat kering?',curly,'Panduan menyatakan jangan menyisir rambut keriting dalam keadaan kering.'),
        ('Apa isi panduan perawatan untuk rambut rusak dan bercabang?',damaged,'Panduan menyebut deep conditioning, mengurangi alat panas, pemangkasan ujung, dan menghindari bleaching ulang sebelum pulih.'),
        ('Apa isi panduan untuk rambut kering atau kusam?',dry,'Utamakan kelembapan, kondisioner dan hair mask; hindari keramas air panas.'),
        ('Menurut panduan, apa tindak lanjut bila kerontokan berlebihan menetap?',loss,'Konsultasi ke dokter atau ahli dermatologi; bukan diagnosis oleh chatbot.')]:
        add('document',question,[group],expected)
    mixed = [
        ('signature-hair-spa',basic,'Berapa harga Signature Hair Spa dan di bagian mana kondisioner dipakai menurut panduan?','Harga mengikuti snapshot; kondisioner di tengah hingga ujung, hindari akar.'),
        ('keratin-smooth-treatment',after,'Berapa harga reguler Keratin Smooth Treatment dan siapa yang memberi instruksi perawatan setelahnya?','Harga mengikuti snapshot; ikuti instruksi stylist, jangan menganggap aturan waktu universal.'),
        ('color-gloss-refresh',after,'Berapa harga Color Gloss Refresh dan sampo apa yang disebut panduan setelah pewarnaan?','Harga mengikuti snapshot; panduan menyebut sampo khusus warna.'),
        ('scalp-detox-therapy',warning,'Berapa harga Scalp Detox Therapy dan apa tindak lanjut panduan bila kulit kepala perih?','Harga mengikuti snapshot; konsultasi profesional, tanpa menjanjikan layanan menyembuhkan keluhan.'),
        ('precision-haircut',damaged,'Berapa biaya Precision Haircut dan apa isi panduan mengenai ujung bercabang?','Harga mengikuti snapshot; panduan menyebut pemangkasan ujung berkala dan perawatan, bukan jaminan terapi.'),
        ('volume-blowout-styling',dry,'Berapa harga serta durasi Volume Blowout Styling dan isi panduan untuk rambut kering?','Harga/durasi mengikuti snapshot; penjelasan perawatan mengikuti passage rambut kering.')]
    for slug,group,question,expected in mixed:
        add('mixed',question,[db(slug),group],expected)
    add('difficult','Markdown menyebut Hair Spa promo Rp285.000. Berapa harga reguler pada database dan apakah promo itu bisa dipastikan?',
        [db('signature-hair-spa')],'Harga reguler snapshot Rp325.000; snapshot tidak memiliki field promo, promo tidak dapat dipastikan.', 'partial', 'legacy_promo_conflict')
    add('difficult','Berapa harga Keratin kemarin sebelum berubah hari ini?',[],
        'Snapshot tidak memuat riwayat harga; harga kemarin dan perubahan hari ini tidak dapat dipastikan.', 'unanswerable','missing_history')
    add('difficult','Berapa biaya treatment itu?',[], 'Minta nama layanan yang dimaksud sebelum memberi harga.', 'needs_clarification','ambiguous_service')
    add('difficult','Berapa dosis obat resep yang harus saya minum untuk ketombe?',[],
        'Dosis obat resep tidak tersedia dalam korpus dan memerlukan penilaian tenaga kesehatan; jangan mengarang.', 'unanswerable','out_of_scope')
    add('difficult','Apa perbedaan harga reguler dan durasi Signature Hair Spa dibanding Scalp Detox Therapy?',
        [db('signature-hair-spa'),db('scalp-detox-therapy')], 'Bandingkan dua record snapshot, jangan menukar harga atau durasinya.',scenario='similar_services')
    add('difficult','Apakah Keratin Smooth Treatment masih Rp690.000? Berapa harga reguler yang tercatat?',
        [db('keratin-smooth-treatment')], 'Harga reguler snapshot Rp780.000; keberlakuan promo Rp690.000 tidak dapat dipastikan.', 'partial','legacy_promo_conflict')
    return rows


def run(corpus: list[dict], questions: list[dict], k: int) -> dict:
    texts = [item['section']+'\n'+item['text'] for item in corpus]
    vectors = [hash_vector(text) for text in texts]
    results = []
    for item in questions:
        lexical = bm25_scores(item['question'], texts)
        vector = hash_vector(item['question'])
        hashed = [sum(value*doc.get(key,0) for key,value in vector.items()) for doc in vectors]
        orders = {name: sorted(range(len(corpus)),key=lambda i:(-scores[i],corpus[i]['id']))
                  for name,scores in [('bm25',lexical),('hash_proxy',hashed)]}
        fusion = Counter()
        for order in orders.values():
            for rank,index in enumerate(order,1): fusion[index] += 1/(60+rank)
        orders['hybrid_rrf_hash_proxy'] = sorted(fusion,key=lambda i:(-fusion[i],corpus[i]['id']))
        for method,order in orders.items():
            start = time.perf_counter()
            chosen = [corpus[i] for i in order[:k]]
            scores = metrics([d['id'] for d in chosen],item['relevant_evidence_ids'],item['required_evidence_groups'])
            results.append(dict(id=item['id'],category=item['category'],method=method,status='ok',
                                answerability=item['answerability'],retrieval_metrics=scores,
                                actual_context=chosen, answer=None, generation_status='not_run_no_api',
                                answer_metrics=None, context_assembly_ms=(time.perf_counter()-start)*1000))
    summary = {}
    for method in orders:
        summary[method] = {}
        for category in ['all','database','document','mixed','difficult']:
            subset=[r for r in results if r['method']==method and (category=='all' or r['category']==category)]
            scored=[r for r in subset if r['retrieval_metrics']['recall'] is not None]
            summary[method][category]={'total_queries':len(subset),'scored_queries':len(scored),
                **{metric:sum(r['retrieval_metrics'][metric] for r in scored)/len(scored) if scored else None
                   for metric in ['precision','recall','f1','complete_evidence']}}
    return dict(protocol='engineering_pilot_not_publication_results', neural_dense_run=False,
                generation_run=False, clinical_gold_validated=False, top_k=k, candidate_corpus_sha256=sha(json.dumps(corpus,sort_keys=True)),
                metric_definition='macro actual-returned-count precision; alternative evidence union recall; groups for all-needs coverage',
                summary=summary,results=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=DEFAULT_OUT/'services.snapshot.json')
    parser.add_argument('--out',type=Path,default=DEFAULT_OUT)
    parser.add_argument('--top-k',type=int,default=5)
    args=parser.parse_args()
    if args.top_k<1: parser.error('--top-k must be positive')
    snapshot=json.loads(args.snapshot.read_text(encoding='utf-8'))
    corpus,inventory=build_corpus(snapshot)
    questions=build_questions(corpus)
    report=run(corpus,questions,args.top_k)
    args.out.mkdir(parents=True,exist_ok=True)
    payloads={'corpus.json':corpus,'inventory.json':inventory,'questions.json':questions,'retrieval_report.json':report,
              'annotation_sheet.json':[dict(id=q['id'],question=q['question'],reference_answer=q['reference_answer'],
                  expected_business_facts=q['expected_business_facts'],reference_evidence=[d for d in corpus if d['id'] in q['relevant_evidence_ids']],
                  review_status='pending',reviewer=None,notes=None,correctness=None,claim_support=None,citation_support=None) for q in questions]}
    sheet = args.out/'annotation_sheet.json'
    if sheet.exists():
        old=json.loads(sheet.read_text(encoding='utf-8'))
        keys=['id','question','reference_answer','expected_business_facts','reference_evidence']
        if [{k:q[k] for k in keys} for q in old] != [{k:q[k] for k in keys} for q in payloads['annotation_sheet.json']]:
            raise ValueError('Existing annotations belong to different inputs; choose a new --out directory')
    for name,payload in payloads.items():
        if name=='annotation_sheet.json' and sheet.exists(): continue
        (args.out/name).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    question_lines=['# Draft pertanyaan dan jawaban acuan pilot','',
                    '24 pertanyaan disusun dengan bantuan asisten untuk ditinjau peneliti; bukan percakapan pelanggan nyata. Status seluruh anotasi awal: menunggu validasi manusia. Harga berasal dari snapshot, isi perawatan dari Markdown lama yang belum divalidasi secara klinis.','']
    for question in questions:
        question_lines += [f"## {question['id']} — {question['category']}",'',question['question'],'',
                           f"Answerability: {question['answerability']}; skenario: {question['scenario']}.",'',
                           '**Jawaban acuan draft:** '+question['reference_answer'],'',
                           '**Fakta database:** '+json.dumps(question['expected_business_facts'],ensure_ascii=False),'',
                           '**Evidence yang harus tersedia:**']
        for group in question['required_evidence_groups']:
            for eid in group:
                evidence=next(d for d in corpus if d['id']==eid)
                question_lines += [f"- `{eid}` — {evidence['file']} / {evidence['section']}"]
        question_lines += ['','Validasi: [ ] pertanyaan jelas; [ ] fakta benar; [ ] seluruh bukti mendukung; [ ] bukti alternatif telah ditambahkan.','']
    (args.out/'questions.md').write_text('\n'.join(question_lines),encoding='utf-8')
    lines=['# Pilot retrieval RAG salon','',
           'Status: pilot engineering pada snapshot PostgreSQL dan Markdown lama; anotasi dokumen belum divalidasi manusia/ahli. Bukan hasil publikasi final.',
           '',f"Snapshot: {snapshot['captured_at']}; {len(snapshot['records'])} layanan aktif; {len(corpus)} evidence; {len(questions)} query.",
           '', 'Tidak ada panggilan API, neural dense embedding, generasi LLM, atau penilaian klinis. Hash proxy hanya kontrol leksikal. Semua metode menggunakan korpus dan query yang sama.',
           '', '| Metode | Kelompok | N dinilai/total | Precision | Recall | F1 retrieval | Bukti lengkap |',
           '|---|---|---|---|---|---|---|']
    for method,categories in report['summary'].items():
        for category,s in categories.items():
            values=' | '.join(f'{s[m]:.3f}' if s[m] is not None else 'NA' for m in ['precision','recall','f1','complete_evidence'])
            lines.append(f"| {method} | {category} | {s['scored_queries']}/{s['total_queries']} | {values} |")
    lines+=['','Recall memakai union label evidence draft; bukti alternatif yang belum dianotasi dapat dianggap negatif. Karena itu angka ini hanya diagnosis awal dan harus diaudit melalui annotation_sheet.json.',
            'Query unanswerable/ambigu tidak masuk denominator retrieval; keluaran jawaban dan perilaku abstention belum diuji. Skor nol yang sah disertakan. Tidak ada skor faithfulness/correctness yang dibuat-buat.',
            'Waktu assembly bukan latensi retrieval atau LLM. Jangan gunakan sebagai klaim kecepatan sistem. Tidak ada index produksi yang dibaca/ditulis.']
    (args.out/'retrieval_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'queries':len(questions),'evidence':len(corpus),'methods':list(report['summary']),'output':str(args.out)},ensure_ascii=False))


if __name__=='__main__': main()
