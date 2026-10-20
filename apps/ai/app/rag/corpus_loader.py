"""Validate a runtime bundle before making its documents available to retrieval."""
import hashlib
import json
from pathlib import Path


class CorpusError(ValueError):pass


def load_corpus(path,*,require_manifest=False):
    path=Path(path)
    try:
        content=path.read_bytes()
        rows=json.loads(content)
        if not isinstance(rows,list):raise ValueError('Corpus must be a list')
        if any(not isinstance(d,dict) or not d.get('id') or not isinstance(d.get('text'),str)
               or not d.get('file') or not isinstance(d.get('section'),str) or not d.get('source_type') for d in rows):
            raise ValueError('Corpus document fields missing')
        if len({d['id'] for d in rows})!=len(rows):raise ValueError('Duplicate evidence IDs')
        manifest_path=path.with_name('manifest.json')
        if require_manifest and not manifest_path.exists():raise ValueError('Runtime manifest required')
        if manifest_path.exists():
            manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
            expected=manifest.get('output_sha256',{}).get(path.name)
            if expected is None or hashlib.sha256(content).hexdigest()!=expected:
                raise ValueError('Corpus hash mismatch')
            if manifest.get('contains_business_snapshot') is False and any(d['source_type']=='db' for d in rows):
                raise ValueError('Runtime corpus must not contain snapshot business facts')
            if require_manifest:
                if manifest.get('contains_business_snapshot') is not False or manifest.get('document_count')!=len(rows):
                    raise ValueError('Invalid runtime bundle declaration')
                if not {path.name,'source-register.json'}<=manifest.get('output_sha256',{}).keys():
                    raise ValueError('Incomplete runtime bundle')
                for name,digest in manifest['output_sha256'].items():
                    target=(path.parent/name).resolve()
                    if not target.is_relative_to(path.parent.resolve()) or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
                        raise ValueError('Runtime bundle hash mismatch')
        return rows
    except (OSError,ValueError,TypeError,KeyError) as exc:
        raise CorpusError('Knowledge corpus unavailable or invalid') from exc
