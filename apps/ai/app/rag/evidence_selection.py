"""Conservative query-only context selection; receives no relevance labels."""
import re
from app.rag.lexical_index import tokenize
from app.rag.query_planning import plan,STOP
from app.rag.service_matching import match_services


QUALIFIERS=re.compile(r'\b(?:tidak|jangan|hindari|kecuali|jika|bila|apabila|khusus|only|not|avoid|unless|if)\b|\buntuk rambut\b')


def qualifier_signature(document):
    """Keep distinct lexical caveats; this is not a semantic equivalence test."""
    text=document['section']+'\n'+document['text']
    return {' '.join(tokenize(sentence)) for sentence in re.split(r'[.!?;\n]+',text)
            if QUALIFIERS.search(sentence.casefold())}


def select_evidence(query,corpus,candidates):
    needs=plan(query,corpus)
    business=[d for d in corpus if d['source_type']=='db']
    named={d['id'] for d in match_services(query,business)}
    words=set(tokenize(query))
    residual=query.casefold()
    for name in sorted((d['fields']['name'] for d in business),key=len,reverse=True):
        residual=re.sub(re.escape(name.casefold()),' ',residual)
    document_words=set(tokenize(residual))
    requests_business=needs['business'] or bool(words & {'layanan','service','treatment','salon','tersedia'}) or bool(named)
    requests_document=needs['document'] or bool(document_words & {
        'conditioner','shampoo','panas','heat','styling','sisir','panduan','tips','edukasi',
        'cara','bagaimana','mengapa','kenapa','manfaat','rekomendasi'})
    keep=[];reasons=[]
    for i in candidates:
        d=corpus[i]
        if d['source_type']=='db':
            if requests_business and (not named or d['id'] in named):keep.append(i)
        elif requests_document or not requests_business:
            keep.append(i)
    documents=[i for i in keep if corpus[i]['source_type']!='db']
    if len(documents)>1:
        qwords=[t for t in tokenize(needs['document_query']) if t not in STOP]
        pairs=set(zip(qwords,qwords[1:]))
        scores={}
        coverage={}
        for i in documents:
            d=corpus[i]
            tokens=[t for t in tokenize(d['section']+' '+d['text']) if t not in STOP]
            scores[i]=len(pairs & set(zip(tokens,tokens[1:])))
            coverage[i]=set(tokens) & set(qwords)
        highest=max(scores.values(),default=0)
        leaders=[i for i,s in scores.items() if s==highest]
        # Only compress when an ordered phrase uniquely identifies a passage.
        # Uncertain/multiple-topic queries retain their candidate documents.
        if highest>0 and len(leaders)==1 and all(words<=coverage[leaders[0]] for words in coverage.values()):
            winner=leaders[0]
            winner_caveats=qualifier_signature(corpus[winner])
            protected={i for i in documents if qualifier_signature(corpus[i])-winner_caveats}
            keep=[i for i in keep if corpus[i]['source_type']=='db' or i==winner or i in protected]
            reasons.append('unique_ordered_phrase_match')
            if protected-{winner}:reasons.append('distinct_caveat_retained')
    if not keep:
        keep=list(candidates)
        reasons.append('uncertain_keep_candidates')
    return keep,dict(strategy='source_scoped_v2',input_count=len(candidates),output_count=len(keep),
                     reasons=reasons,selection_uses_gold=False)
