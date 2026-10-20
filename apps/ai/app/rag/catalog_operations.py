"""Read-only catalog operations, separate from ranked document retrieval."""
import hashlib
import json
import re
from decimal import Decimal

from app.rag.answer_policy import source_payload
from app.rag.retriever import RetrievedDoc

MONEY = r'(?:rp\.?\s*)?(\d+(?:[.,]\d+)*)(?:\s*(ribu|rb|k|juta|jt)\b)?'
CARE = re.compile(r'bagaimana|mengapa|kenapa|cara\b|kondisioner|conditioner|sampo|shampoo|keramas|kering|rusak|rontok|ketombe|perih|resep|obat')


def rupiah(value):
    return 'Rp' + f'{value:,}'.replace(',', '.')


def amount(number, unit):
    if unit:
        normalized = number.replace('.', '') if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', number) else number.replace(',', '.')
        value = Decimal(normalized) * (1000000 if unit in {'juta', 'jt'} else 1000)
    else:
        if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+', number):
            number = number.replace('.', '').replace(',', '')
        value = Decimal(number)
    if value < 0 or value != value.to_integral_value():
        raise ValueError('Price must be whole rupiah')
    return int(value)


def parse_catalog_query(query):
    text = ' '.join(query.casefold().split()).rstrip('?.!')
    if not re.search(r'\b(layanan|treatment|perawatan|katalog)\b', text) or CARE.search(text):
        return None
    if re.search(r'promo|diskon|kemarin|histori|sebelum|dulu', text):
        return None
    comparison = r'di\s*bawah|kurang dari|di\s*atas|lebih dari|maksimal|minimal|setidaknya|antara|hingga|sampai|[<>]'
    bulk = re.search(r'semua|seluruh|daftar|apa saja|layanan apa|jumlah|berapa banyak|berapa layanan|termurah|termahal|paling murah|paling mahal|urutkan', text)
    has_filter = re.search(comparison, text)
    if not bulk and not has_filter:
        return None
    plan = {'kind':'count' if re.search(r'jumlah|berapa banyak|berapa layanan',text) else 'list',
            'filters':[], 'order':'id', 'extreme':None}
    if re.search(r'termurah|paling murah', text):
        plan.update(order='price_asc', extreme='min')
    elif re.search(r'termahal|paling mahal', text):
        plan.update(order='price_desc', extreme='max')
    elif 'urutkan' in text:
        plan['order'] = 'price_desc' if re.search(r'tertinggi|mahal|menurun|turun',text) else 'price_asc'
    if has_filter:
        # Unsupported negation is clarified rather than silently inverted.
        if re.search(r'\b(tidak|bukan|kecuali|atau)\b',text):
            return {'kind':'clarify_filter'}
        if re.search(MONEY+r'\s*(?:menit|jam)\b',text):
            return None  # Never interpret a duration threshold as rupiah.
        ranges = re.search(r'antara\s+'+MONEY+r'\s+(?:dan|sampai|hingga)\s+'+MONEY,text)
        try:
            if ranges:
                low, high = amount(*ranges.groups()[:2]), amount(*ranges.groups()[2:])
                if low > high:
                    return {'kind':'clarify_filter'}
                plan['filters'] = [('ge',low),('le',high)]
            else:
                operators=r'<=|>=|<|>|maksimal|hingga|sampai(?: dengan)?|minimal|setidaknya|di\s*bawah|kurang dari|di\s*atas|lebih dari'
                starts=[]
                for match in re.finditer('('+operators+r')\s*'+MONEY,text):
                    starts.append(match.start())
                    operator=match.group(1)
                    if re.fullmatch(r'maksimal|hingga|sampai(?: dengan)?|<=',operator): key='le'
                    elif re.fullmatch(r'minimal|setidaknya|>=',operator): key='ge'
                    elif re.fullmatch(r'di\s*bawah|kurang dari|<',operator): key='lt'
                    else: key='gt'
                    plan['filters'].append((key,amount(*match.groups()[1:])))
                if not plan['filters'] or any(m.start() not in starts for m in re.finditer(operators,text)):
                    return {'kind':'clarify_filter'}
        except Exception as exc:
            if not isinstance(exc,(ValueError,ArithmeticError)):
                raise
            return {'kind':'clarify_filter'}
    elif re.search(r'\d',text):
        # Bare numbers may mean budget, duration, or result count. Do not guess.
        return {'kind':'clarify_filter'}
    return plan


def catalog_answer(query, corpus, *, mode='snapshot'):
    plan = parse_catalog_query(query)
    if plan is None:
        return None
    records = [d for d in corpus if d['source_type']=='db']
    fingerprint = hashlib.sha256(json.dumps(records,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    base = dict(plan=plan,catalog_ids=[d['id'] for d in records],fingerprint=fingerprint)
    if plan['kind']=='clarify_filter':
        return dict(base,status='policy_clarification',sources=[],docs=[],
                    reply='Batas harga yang Anda inginkan berapa? Sebutkan angkanya dan apakah batas tersebut termasuk, misalnya “maksimal Rp300.000”.')
    if mode=='unavailable':
        return dict(base,status='policy_unavailable',sources=[],docs=[],
                    reply='Katalog layanan aktif belum dapat diakses. Daftar, harga, durasi, dan jumlah layanan belum dapat dipastikan. Silakan coba lagi atau konfirmasikan ke staf salon.')
    selected = records
    for op, value in plan['filters']:
        compare = {'lt':lambda p:p<value,'le':lambda p:p<=value,'gt':lambda p:p>value,'ge':lambda p:p>=value}[op]
        selected = [d for d in selected if compare(d['fields']['price'])]
    if plan['extreme'] and selected:
        extreme = (min if plan['extreme']=='min' else max)(d['fields']['price'] for d in selected)
        selected = [d for d in selected if d['fields']['price']==extreme]
    selected = sorted(selected,key=lambda d: ((-1 if plan['order']=='price_desc' else 1)*d['fields']['price'], d['id'])
                      if plan['order']!='id' else (d['fields']['id'],d['id']))
    docs = [RetrievedDoc(id=d['id'],file=d['file'],section=d['section'],snippet=d['text'],
                         metadata={k:v for k,v in d.items() if k not in {'text','fields'}}) for d in records]
    scope = 'database aktif yang dibaca pada permintaan ini' if mode=='live' else 'snapshot penelitian; bukan konfirmasi harga terkini'
    # A catalog-level citation records the entire scan, including empty results.
    summary = {'id':('live' if mode=='live' else 'snapshot')+':catalog-query',
               'file':'services.live.json' if mode=='live' else 'services.snapshot.json',
               'title':'Hasil penelusuran katalog '+('aktif' if mode=='live' else 'snapshot penelitian'),
               'snippet':json.dumps({'operation':plan,'scanned_ids':base['catalog_ids'],
                                     'matched_ids':[d['id'] for d in selected],'matched_count':len(selected)},ensure_ascii=False),
               'usage':'deterministic_catalog_lookup','citation_number':1}
    heading = f'Ditemukan **{len(selected)} layanan**'
    if plan['filters']:
        labels={'lt':'kurang dari','le':'maksimal','gt':'lebih dari','ge':'minimal'}
        heading += ' dengan harga reguler '+ ' dan '.join(labels[op]+' '+rupiah(value) for op,value in plan['filters'])
    elif plan['extreme']:
        heading += ' dengan harga reguler '+('terendah' if plan['extreme']=='min' else 'tertinggi')
    heading += f' berdasarkan {scope}. [1]'
    sources = [summary]
    if plan['kind']=='count' or not selected:
        return dict(base,status='catalog_lookup',sources=sources,docs=docs,reply=heading)
    # Bound the rendered list explicitly, never describe a truncated list as complete.
    limit=30
    lines=[heading,'']
    if plan['order']!='id':
        lines += ['Urutan harga '+('tertinggi ke terendah.' if plan['order']=='price_desc' else 'terendah ke tertinggi.'),'']
    by_id={d.id:d for d in docs}
    for number, d in enumerate(selected[:limit],start=2):
        fields=d['fields']
        lines.append(f"- **{fields['name']}** — harga reguler {rupiah(fields['price'])}; durasi {fields['duration_min']} menit. [{number}]")
        sources.append(source_payload(by_id[d['id']],number,'deterministic_catalog_lookup'))
    if len(selected)>limit:
        lines += ['',f'Ditampilkan {limit} dari {len(selected)} layanan yang cocok. Persempit batas harga untuk melihat hasil yang lebih sedikit.']
    return dict(base,status='catalog_lookup',sources=sources,docs=docs,reply='\n'.join(lines))
