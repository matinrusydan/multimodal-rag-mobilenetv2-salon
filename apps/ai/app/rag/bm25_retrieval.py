"""API-free retrieval of the explicitly configured, versioned JSON corpus."""
import json
from app.config import settings
from app.rag.pilot import bm25_scores
from app.rag.retriever import RetrievedDoc


def balanced_order(query, corpus, top_k=5):
    """Reserve source slots for detected mixed needs; no reference labels are read."""
    from app.rag.algorithm_trial import plan
    scores=bm25_scores(query,[d['section']+'\n'+d['text'] for d in corpus])
    original=sorted(range(len(corpus)),key=lambda i:(-scores[i],corpus[i]['id']))
    needs=plan(query,corpus)
    if not (needs['business'] and needs['document']) or top_k<3:return original[:top_k]
    named=sum(d['fields']['name'].casefold() in query.casefold() for d in corpus if d['source_type']=='db')
    db_slots=min(max(named,1),2,top_k-2)
    doc_scores=bm25_scores(needs['document_query'],[d['section']+'\n'+d['text'] for d in corpus])
    documents=sorted((i for i,d in enumerate(corpus) if d['source_type']!='db'),key=lambda i:(-doc_scores[i],corpus[i]['id']))
    reserved=[i for i in original if corpus[i]['source_type']=='db'][:db_slots]+documents[:2]
    return list(dict.fromkeys(reserved+original))[:top_k]


def retrieve(query, top_k=5, corpus=None):
    if corpus is None:corpus=json.loads(settings.rag_corpus_file.read_text(encoding='utf-8'))
    scores=bm25_scores(query,[d['section']+'\n'+d['text'] for d in corpus])
    order=sorted(range(len(corpus)),key=lambda i:(-scores[i],corpus[i]['id']))[:top_k]
    if settings.rag_retrieval_provider=='bm25_source_balanced':order=balanced_order(query,corpus,top_k)
    return [RetrievedDoc(id=corpus[i]['id'],file=corpus[i]['file'],section=corpus[i]['section'],snippet=corpus[i]['text'],
                         metadata={**{k:v for k,v in corpus[i].items() if k not in {'text','fields'}},'retrieval_provider':settings.rag_retrieval_provider,'bm25_score':scores[i]}) for i in order]


def evaluation_policy_context():
    path=settings.rag_corpus_file.with_name('evaluation-context.json')
    if not path.exists():return None
    context=json.loads(path.read_text(encoding='utf-8'))
    return json.dumps({'dataset_mode':'development_snapshot_not_live_database','snapshot_date':context['business_snapshot_date'],
                       'missing_information':context['missing_information'],
                       'policy_instructions':context['policy_instructions']},ensure_ascii=False)
