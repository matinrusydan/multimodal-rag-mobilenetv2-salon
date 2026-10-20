"""Optional bounded HTTP fallback with robots checks and source provenance."""
import asyncio
from collections import OrderedDict
import hashlib
import logging
import re
import time
from urllib.parse import urlsplit

import httpx

from app.crawler.stealth import ALODOKTER_SLUG_MAP
from app.rag.retriever import RetrievedDoc
from app.rag.web_fetch import fetch_article

logger=logging.getLogger(__name__)
_CRAWL_CACHE=OrderedDict()


def needs_web_fallback(query,docs):
    """A lexical coverage heuristic, not a semantic answerability judgment."""
    terms=set(re.findall(r'ketombe|rontok|perih|gatal|luntur|kering|kusam|bercabang|patah|botak|alopecia|berminyak',query.casefold()))
    local=' '.join(d.snippet or '' for d in docs if (d.metadata or {}).get('source_type')!='db').casefold()
    return bool(terms) and not all(term in local for term in terms)


def _crawl_target(query):
    text=query.casefold()
    for keyword,slug in sorted(ALODOKTER_SLUG_MAP.items(),key=lambda item:-len(item[0])):
        if keyword in text:return 'https://www.alodokter.com/'+slug
    return None


def _chunk_text(text,max_chars=2500):
    if max_chars<=100:raise ValueError('Chunk must exceed overlap')
    return [text[i:i+max_chars] for i in range(0,len(text),max_chars-100)]


async def live_crawl_docs(query,*,max_pages=2,delay=1.5):
    target=_crawl_target(query)
    if target is None or max_pages<1:return [],[]
    entry=_CRAWL_CACHE.get(target)
    if entry and entry[0]>time.monotonic():
        article=entry[1];_CRAWL_CACHE.move_to_end(target)
    else:
        _CRAWL_CACHE.pop(target,None)
        try:
            article=await fetch_article(target)
        except (httpx.HTTPError,ValueError,asyncio.TimeoutError) as exc:
            logger.info('Web fallback unavailable (%s); no browser retry',type(exc).__name__)
            return [],[]
        _CRAWL_CACHE[target]=(time.monotonic()+3600,article)
        while len(_CRAWL_CACHE)>32:_CRAWL_CACHE.popitem(last=False)
    # Rank all chunks; no assumption that evidence is at the article beginning.
    from app.rag.lexical_index import BM25Index
    chunks=_chunk_text(article['text'])
    scores=BM25Index(chunks).scores(query)
    order=sorted(range(len(chunks)),key=lambda i:(-scores[i],i))[:min(max_pages,2)]
    digest=hashlib.sha256(article['url'].encode()).hexdigest()[:16]
    docs=[]
    for index in order:
        docs.append(RetrievedDoc(id=f'web:{digest}:{index}',file='web:'+urlsplit(article['url']).path.strip('/'),
            section='Artikel '+urlsplit(article['url']).hostname,snippet=chunks[index],
            metadata={**{k:v for k,v in article.items() if k!='text'},'source_url':article['url'],
                      'source_type':'web','chunk_index':index,'bm25_score':scores[index]}))
    sources=[dict(file=d.file,url=article['url'],snippet=(d.snippet or '')[:180]) for d in docs[:1]]
    return docs,sources
