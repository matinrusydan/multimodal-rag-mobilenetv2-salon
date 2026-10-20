"""Create a versioned document-only runtime corpus from a validated package."""
import argparse
import hashlib
import json
from pathlib import Path

from app.config import BASE_DIR


def build(source,out):
    from app.rag.experiment_ir import validate_package
    corpus,_,provenance=validate_package(source)
    documents=[d for d in corpus if d['source_type']!='db']
    if not documents:raise ValueError('No curated documents to deploy')
    if out.exists():raise ValueError('Use a new version directory; existing runtime corpus is preserved')
    for doc in documents:
        if not doc.get('id') or not doc.get('text') or not doc.get('file'):
            raise ValueError('Document missing identity or content')
    out.mkdir(parents=True)
    payload=(json.dumps(documents,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    (out/'corpus.json').write_bytes(payload)
    register=(source/'source-register.json').read_bytes()
    (out/'source-register.json').write_bytes(register)
    manifest=dict(version=out.name,document_count=len(documents),contains_business_snapshot=False,
        source_package=provenance,output_sha256={'corpus.json':hashlib.sha256(payload).hexdigest(),
            'source-register.json':hashlib.sha256(register).hexdigest()},
        review_status='inherited_source_review_status_not_new_human_approval',
        runtime='Use live catalog for all business facts; no snapshot price fallback')
    (out/'manifest.json').write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=BASE_DIR/'rag/eval/curated-development-v2')
    parser.add_argument('--out',type=Path,default=BASE_DIR/'rag/runtime/curated-care-v1')
    args=parser.parse_args()
    result=build(args.source,args.out)
    print(json.dumps(dict(output=str(args.out),documents=result['document_count'],contains_snapshot=False)))


if __name__=='__main__':main()
