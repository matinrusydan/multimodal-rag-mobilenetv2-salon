"""Require human-assigned scenario families and reject cross-split leakage."""
import re
import argparse
import json
from pathlib import Path


def validate_splits(questions,require_locked_test=False):
    seen={};families={};test_count=0
    for q in questions:
        family=q.get('family_id')
        split=q.get('split')
        if not family or split not in {'development','test'}:
            raise ValueError('Assign scenario family and development/test split: '+q['id'])
        normalized=' '.join(re.findall(r'\w+',q['question'].casefold()))
        if normalized in seen:raise ValueError('Duplicate question: '+q['id'])
        seen[normalized]=q['id']
        if family in families and families[family]!=split:
            raise ValueError('Scenario family crosses development/test: '+family)
        families[family]=split
        if split=='test':
            test_count+=1
            if require_locked_test and (q.get('review_status')!='approved' or not q.get('reviewer') or q.get('locked') is not True):
                raise ValueError('Test question not manually approved and locked: '+q['id'])
    if require_locked_test and not test_count:raise ValueError('No locked test questions')
    return dict(questions=len(questions),families=len(families),test_questions=test_count,
                family_overlap=False,semantic_near_duplicates='still require manual review')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--require-locked-test',action='store_true')
    args=parser.parse_args()
    questions=json.loads(args.input.read_text(encoding='utf-8'))
    try:
        result=dict(status='validated',**validate_splits(questions,args.require_locked_test))
    except ValueError as error:
        result=dict(status='not_ready',reason=str(error))
        print(json.dumps(result,ensure_ascii=False))
        raise SystemExit(2)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
