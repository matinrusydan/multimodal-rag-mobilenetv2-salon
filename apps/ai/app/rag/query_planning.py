"""Transparent runtime query decomposition; receives no evaluation labels."""
import re
from app.rag.lexical_index import tokenize

STOP=set('berapa apa dan serta yang di ke pada untuk menurut isi panduan tercatat reguler atau itu seperti mana siapa dengan apakah masih dari saya'.split())
BUSINESS=set('harga biaya durasi menit promo diskon'.split())
CARE=re.compile(r'perawatan|merawat|kondisioner|sampo|keramas|menyisir|bercabang|kering|kusam|rontok|kerontokan|kulit kepala|pewarnaan|stylist|perih|obat|resep')


def clean(query):
    return ' '.join(t for t in tokenize(query) if t not in STOP)


def plan(query,corpus):
    residual=query.casefold()
    for name in sorted((d['fields']['name'] for d in corpus if d['source_type']=='db'),key=len,reverse=True):
        residual=re.sub(re.escape(name.casefold()),' ',residual)
    care_query=' '.join(t for t in tokenize(residual) if t not in STOP | BUSINESS)
    return {'business':bool(set(tokenize(query)) & BUSINESS),'document':bool(CARE.search(residual)),
            'original_query':query,'document_query':care_query or clean(query)}
