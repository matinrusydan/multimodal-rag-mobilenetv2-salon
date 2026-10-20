"""IR protocol v1: fixed-k precision, union recall, AP@k, RR@k, nDCG@k.

AP@k denominator is all known relevant IDs (not min(k, |gold|)).
nDCG uses gain 2**grade-1 and discount log2(rank+1). Unjudged IDs count as
nonrelevant only relative to the supplied judgments; no global recall claim.
"""
import math

NAMES=('precision_at_k','precision_returned','recall_at_k','f1_at_k','average_precision_at_k',
       'reciprocal_rank_at_k','ndcg_at_k','complete_evidence')


def evaluate_ranking(retrieved,relevant,groups,k=5,grades=None):
    if k<1:raise ValueError('k must be positive')
    if len(set(retrieved))!=len(retrieved):raise ValueError('Duplicate retrieved IDs')
    gold=set(relevant)
    if any(not g for g in groups) or any(not set(g)<=gold for g in groups):
        raise ValueError('Invalid evidence groups')
    if not gold:return {name:None for name in NAMES}
    top=retrieved[:k]
    count=0;ap=0;rr=0
    for rank,eid in enumerate(top,1):
        if eid in gold:
            count+=1;ap+=count/rank
            if not rr:rr=1/rank
    precision=count/k
    recall=count/len(gold)
    judged={eid:1 for eid in gold} if grades is None else grades
    if any(isinstance(g,bool) or not isinstance(g,(int,float)) or not math.isfinite(g) or not 0<=g<=3 for g in judged.values()):
        raise ValueError('Relevance grades must be finite numbers from 0 to 3')
    def dcg(values):return sum((2**g-1)/math.log2(i+2) for i,g in enumerate(values))
    ideal=dcg(sorted(judged.values(),reverse=True)[:k])
    return dict(precision_at_k=precision,precision_returned=count/len(top) if top else 0,
                recall_at_k=recall,f1_at_k=2*precision*recall/(precision+recall) if precision+recall else 0,
                average_precision_at_k=ap/len(gold),reciprocal_rank_at_k=rr,
                ndcg_at_k=dcg([judged.get(eid,0) for eid in top])/ideal if ideal else None,
                complete_evidence=float(all(set(g)&set(top) for g in groups)) if groups else None)
