"""Reusable exact BM25 statistics/postings; no model or external dependency."""
from collections import Counter, defaultdict
from functools import lru_cache
import math
import re


def tokenize(text):
    return re.findall(r'\w+', text.casefold())


class BM25Index:
    def __init__(self, texts, k1=1.5, b=0.75):
        if k1<=0 or not 0<=b<=1:
            raise ValueError('Invalid BM25 parameters')
        self.k1, self.b = k1, b
        self.size = len(texts)
        self.lengths=[]
        postings=defaultdict(list)
        for i,text in enumerate(texts):
            words=tokenize(text)
            self.lengths.append(len(words))
            for word,count in Counter(words).items():
                postings[word].append((i,count))
        self.postings=dict(postings)
        self.average_length=sum(self.lengths)/self.size if self.size else 0
        average=self.average_length or 1
        self.norms=[k1*(1-b+b*length/average) for length in self.lengths]
        self.idf={word:math.log(1+(self.size-len(items)+0.5)/(len(items)+0.5))
                  for word,items in self.postings.items()}

    def scores(self, query):
        values=[0.0]*self.size
        for word in set(tokenize(query)):
            for index,count in self.postings.get(word,()):
                values[index]+=self.idf[word]*count*(self.k1+1)/(count+self.norms[index])
        return values


@lru_cache(maxsize=2)
def cached_index(texts: tuple[str,...], k1=1.5, b=0.75):
    # Keys depend on ranking content, not only a path/mtime. At most two versions
    # are retained. Live price/name changes therefore cannot reuse stale statistics.
    return BM25Index(texts,k1,b)


def ranking_text(doc):
    text=doc['text']
    if doc.get('business_mode')=='live':
        # Fetch time belongs to provenance/prompt, not lexical relevance. Otherwise
        # every request would invalidate the index even when facts are unchanged.
        text=re.sub(r'\nSumber: database aktif melalui API, dibaca [^\n]+\.?$', '', text)
    return doc['section']+'\n'+text


def corpus_index(corpus):
    return cached_index(tuple(ranking_text(d) for d in corpus))
