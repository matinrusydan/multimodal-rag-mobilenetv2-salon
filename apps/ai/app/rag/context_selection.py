"""Exact contiguous evidence windows; selection never receives gold labels."""
import hashlib
import re
from app.rag.lexical_index import tokenize


def select_context(text,query='',limit=400,strategy='head'):
    if limit<1:raise ValueError('Context limit must be positive')
    if strategy not in {'head','query_window'}:raise ValueError('Unknown context strategy')
    start=0
    if strategy=='query_window' and len(text)>limit:
        terms=set(tokenize(query))
        positions=[m for m in re.finditer(r'\w+',text) if m.group().casefold() in terms]
        # Candidate windows are chosen from lexical matches, not answer labels.
        candidates={0}
        for match in positions:
            candidates.add(min(max(0,match.start()-limit//4),len(text)-limit))
        def score(offset):
            return len(set(tokenize(text[offset:offset+limit])) & terms)
        start=min(candidates,key=lambda offset:(-score(offset),offset))
    used=text[start:start+limit]
    return dict(text=used,start=start,end=start+len(used),strategy=strategy,
                source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                used_sha256=hashlib.sha256(used.encode()).hexdigest())


def context_records(docs,query='',strategy='head'):
    return [dict(id=d.id,**select_context(d.snippet or '',query,
                  1100 if d.file.startswith('web:') else 400,strategy)) for d in docs]
