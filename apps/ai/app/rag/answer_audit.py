"""Score explicit human annotations, never guess labels from generated prose."""
import argparse
import json
from pathlib import Path


def score_annotation(record):
    if record.get('review_status')!='approved' or not str(record.get('reviewer') or '').strip():
        return {'status':'pending_manual_review','metrics':None}
    if not str(record.get('answer') or '').strip():
        raise ValueError('An approved annotation must include the actual answer being reviewed')
    required={(v['service_id'],v['field']):v['value'] for v in record.get('required_business_fields',[])}
    observed=record.get('observed_business_fields',[])
    if len({(v['service_id'],v['field']) for v in observed})!=len(observed):
        raise ValueError('Resolve duplicate observed business fields before scoring')
    source={(v['service_id'],v['field']):v['value'] for v in record.get('source_business_fields',[])}
    if any(key not in source or source[key]!=value for key,value in required.items()):
        raise ValueError('Required business facts must match the frozen source')
    answers={(v['service_id'],v['field']):v['value'] for v in observed}
    claims=record.get('claims',[])
    for claim in claims:
        for name in ('supported','citation_required','citation_supported'):
            if claim.get(name) is not None and not isinstance(claim[name],bool):
                raise ValueError('Claim judgments must be true, false or null')
    assessed=[c for c in claims if isinstance(c.get('supported'),bool)]
    citations=[c for c in claims if c.get('citation_required') is True]
    checked=[c for c in citations if isinstance(c.get('citation_supported'),bool)]
    units=record.get('required_answer_units',[])
    policies=record.get('policy_checks',[])
    for item in units+policies:
        if item.get('passed') is not None and not isinstance(item['passed'],bool):
            raise ValueError('Unit and policy judgments must be true, false or null')
    scored_units=[u for u in units if isinstance(u.get('passed'),bool)]
    scored_policies=[p for p in policies if isinstance(p.get('passed'),bool)]
    ratio=lambda n,d:n/d if d else None
    return dict(status='human_annotation_scored',metrics=dict(
        required_business_field_coverage=ratio(sum(k in answers and answers[k]==v for k,v in required.items()),len(required)),
        stated_business_field_accuracy=ratio(sum(k in source and source[k]==v for k,v in answers.items()),len(answers)),
        faithfulness_manual=ratio(sum(c['supported'] for c in assessed),len(assessed)),
        citation_support_manual=ratio(sum(c['citation_supported'] for c in checked),len(checked)),
        answer_unit_completeness_manual=ratio(sum(u['passed'] for u in scored_units),len(scored_units)),
        policy_compliance_manual=ratio(sum(p['passed'] for p in scored_policies),len(scored_policies))),
        counts=dict(required_fields=len(required),stated_fields=len(answers),claims=len(claims),
                    claims_assessed=len(assessed),claims_missing=len(claims)-len(assessed),
                    citations_required=len(citations),citations_assessed=len(checked),
                    citations_missing=len(citations)-len(checked),
                    answer_units_missing=len(units)-len(scored_units),policy_checks_missing=len(policies)-len(scored_policies)),
        warning='Scores summarize human labels; incomplete assessments and coverage must be reported alongside averages.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():parser.error('Use a new output file; previous reviews are preserved')
    rows=json.loads(args.annotations.read_text(encoding='utf-8'))
    results=[dict(id=r['id'],**score_annotation(r)) for r in rows]
    report=dict(protocol='manual_answer_audit_v1',total=len(results),
                scored=sum(r['status']=='human_annotation_scored' for r in results),results=results)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'total':report['total'],'scored':report['scored'],'report':str(args.out)}))


if __name__=='__main__':main()
