"""Deterministic clarification and citation attribution; not an entailment judge."""
import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path


def service_clarification(query: str, corpus_file: Path, *, corpus=None, live=False):
    from app.rag.catalog_operations import parse_catalog_query
    if parse_catalog_query(query) is not None:
        return None  # Explicit catalog operations are handled before clarification.
    text=' '.join(query.casefold().split())
    if not re.search(r'\b(harga|biaya|tarif|price|cost|durasi)\b',text):return None
    if not re.search(r'\b(harga|biaya|tarif|price|cost)\b',text) and re.search(r'kondisioner|conditioner|leave[ -]?in|sampo|shampoo',text):
        return None  # Product dwell time is not a request for a salon service.
    if re.search(r'promo|diskon|histori|kemarin|dulu|sebelum|bulan lalu|minggu lalu',text):return None
    if corpus is None:corpus=json.loads(corpus_file.read_text(encoding='utf-8'))
    services=[d for d in corpus if d['source_type']=='db']
    if not services:return None
    names=[d['fields']['name'] for d in services]
    from app.rag.service_matching import match_services
    if match_services(query,services):return None
    reply='Treatment atau layanan yang Anda maksud yang mana? Pilihan pada '+('katalog aktif salon' if live else 'katalog penelitian ini')+':\n\n'
    reply+='\n'.join('- '+name+' [1]' for name in names)
    reply+='\n\nSilakan pilih atau sebutkan nama layanannya agar saya dapat memberikan harga yang tepat.'
    return {'reply':reply,'sources':[{'id':'live:service-options' if live else 'snapshot:service-options','file':'services.live.json' if live else 'services.snapshot.json',
             'title':'Pilihan layanan — katalog aktif salon' if live else 'Pilihan layanan — katalog snapshot penelitian','snippet':'; '.join(names),'usage':'catalog_options','citation_number':1}],
            'catalog_ids':[d['id'] for d in services]}


def source_payload(doc, number=None, usage='retrieved_excerpt'):
    meta=doc.metadata or {}
    title=('Data layanan: '+str(doc.section or 'katalog')+(' (database aktif)' if meta.get('business_mode')=='live' else ' (snapshot penelitian)') if meta.get('source_type')=='db'
           else doc.section or meta.get('title') or doc.file.removesuffix('.md'))
    source={'id':doc.id or doc.file+'#'+str(doc.section or ''),'file':doc.file,'section':doc.section or '',
            'title':title,'snippet':doc.snippet or '', 'usage':usage}
    url=meta.get('source_url') or meta.get('source')
    if isinstance(url,str) and url.startswith(('https://','http://')):source['url']=url
    if number is not None:source['citation_number']=number
    return source


def cited_sources(reply, docs):
    """Keep references explicitly cited by the model; invalid indices are removed.

    A citation is model attribution only. Its presence does not prove entailment.
    """
    chosen=OrderedDict();canonical={};invalid=[]
    for match in re.finditer(r'\[(\d+)\]',reply):
        number=int(match.group(1))
        if not 1<=number<=len(docs):invalid.append(number);continue
        doc=docs[number-1]
        key=doc.id or doc.file+'#'+str(doc.section or '')+hashlib.sha256((doc.snippet or '').encode()).hexdigest()
        if key not in chosen:chosen[key]=(doc,number)
        canonical[number]=chosen[key][1]
    cleaned=re.sub(r'\[(\d+)\]',lambda m:'['+str(canonical[int(m.group(1))])+']' if int(m.group(1)) in canonical else '',reply)
    sources=[source_payload(doc,n,'model_cited_not_independently_verified') for doc,n in chosen.values()]
    return cleaned,sources,{'status':'model_attribution_only' if sources else 'no_valid_citations',
                            'invalid_citation_indices':invalid,'entailment_verified':False}
