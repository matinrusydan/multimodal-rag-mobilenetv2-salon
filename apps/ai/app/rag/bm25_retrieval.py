"""API-free retrieval of the explicitly configured, versioned JSON corpus."""
import json
from app.config import settings
from app.rag.lexical_index import corpus_index
from app.rag.query_planning import plan
from app.rag.retriever import RetrievedDoc
from app.rag.corpus_loader import load_corpus


def balanced_order(query, corpus, top_k=5, *, index=None, scores=None, decompose=True, allocate=True):
    """Reserve source slots for detected mixed needs; no reference labels are read."""
    if top_k<1:raise ValueError('top_k must be positive')
    index=index or corpus_index(corpus)
    if scores is None:scores=index.scores(query)
    original=sorted(range(len(corpus)),key=lambda i:(-scores[i],corpus[i]['id']))
    needs=plan(query,corpus)
    if not (needs['business'] and needs['document']) or top_k<3:return original[:top_k]
    named=sum(d['fields']['name'].casefold() in query.casefold() for d in corpus if d['source_type']=='db')
    db_slots=min(max(named,1),2,top_k-2)
    doc_scores=index.scores(needs['document_query']) if decompose else scores
    documents=sorted((i for i,d in enumerate(corpus) if d['source_type']!='db'),key=lambda i:(-doc_scores[i],corpus[i]['id']))
    if not allocate:return original[:top_k]
    reserved=[i for i in original if corpus[i]['source_type']=='db'][:db_slots]+documents[:2]
    return list(dict.fromkeys(reserved+original))[:top_k]


def retrieve(query, top_k=5, corpus=None):
    if corpus is None:corpus=load_corpus(settings.rag_corpus_file)
    if top_k<1:raise ValueError('top_k must be positive')
    ranking_query=query
    ranking_corpus=corpus
    if settings.rag_context_selection=='source_scoped':
        from app.rag.care_intent import operational_care_query,compatible_product_evidence
        ranking_query=operational_care_query(query)
        ranking_corpus=[d for d in corpus if compatible_product_evidence(query,d)]
    corpus=ranking_corpus
    if not corpus:return []
    index=corpus_index(corpus)
    scores=index.scores(ranking_query)
    order=sorted(range(len(corpus)),key=lambda i:(-scores[i],corpus[i]['id']))[:top_k]
    if settings.rag_retrieval_provider=='bm25_source_balanced':order=balanced_order(ranking_query,corpus,top_k,index=index,scores=scores)
    selection={'strategy':'all','input_count':len(order),'output_count':len(order)}
    if settings.rag_context_selection=='source_scoped':
        from app.rag.evidence_selection import select_evidence
        order,selection=select_evidence(ranking_query,corpus,order)
    return [RetrievedDoc(id=corpus[i]['id'],file=corpus[i]['file'],section=corpus[i]['section'],snippet=corpus[i]['text'],
                         metadata={**{k:v for k,v in corpus[i].items() if k not in {'text','fields'}},'retrieval_provider':settings.rag_retrieval_provider,'bm25_score':scores[i],'context_selection':selection,'ranking_query':ranking_query}) for i in order]


def evaluation_policy_context():
    path=settings.rag_corpus_file.with_name('evaluation-context.json')
    if not path.exists():return None
    context=json.loads(path.read_text(encoding='utf-8'))
    return json.dumps({'dataset_mode':'development_snapshot_not_live_database','snapshot_date':context['business_snapshot_date'],
                       'missing_information':context['missing_information'],
                       'policy_instructions':[{'id':p['id'],'text':p['text']} for p in context['policy_instructions']]},ensure_ascii=False)
