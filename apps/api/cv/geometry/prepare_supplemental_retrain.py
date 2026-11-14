"""Snapshot user-approved collector folders for isolated hair-type retraining."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy.fft import dctn

HERE = Path(__file__).resolve().parent
LABELS = ('lurus', 'bergelombang', 'keriting', 'sangat-keriting')


def fingerprints(path):
    raw = hashlib.sha256(path.read_bytes()).hexdigest()
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
        size = image.size
        pixel = hashlib.sha256(str(size).encode() + image.tobytes()).hexdigest()
        gray = image.convert('L')
        dh = np.asarray(gray.resize((9, 8), Image.Resampling.LANCZOS))
        dh = dh[:, 1:] > dh[:, :-1]
        coeff = dctn(np.asarray(gray.resize((32, 32), Image.Resampling.LANCZOS), dtype=float), norm='ortho')[:8, :8].flatten()
        ph = coeff > np.median(coeff[1:])
    return {'sha256': raw, 'pixel_sha256': pixel, 'width': size[0], 'height': size[1],
            'dhash': int.from_bytes(np.packbits(dh).tobytes(), 'big'),
            'phash': int.from_bytes(np.packbits(ph).tobytes(), 'big')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collector', type=Path, default=Path(r'C:\laragon\www\hair-dataset-collector\storage'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='Create immutable snapshot; otherwise audit only')
    args = parser.parse_args()
    assert not (args.collector / 'review_pending.json').exists(), 'Pending review transaction'
    assert not args.output.exists(), 'Use a new experiment directory; never overwrite'
    baseline_path = HERE / 'reports/phase1/curated_manifest.json'
    baseline = json.loads(baseline_path.read_text('utf8'))
    rows = list(csv.DictReader((args.collector / 'manifest.csv').open(encoding='utf8')))
    by_id = {r['id']: r for r in rows}
    assert len(by_id) == len(rows)
    dataset = HERE.parent / 'dataset'
    records, references = [], []
    for record in baseline['records']:
        source = dataset / record['image_id']
        fp = fingerprints(source)
        assert fp['sha256'] == record['sha256'], f'Baseline changed: {source}'
        records.append({**record, 'image_id': str(source.resolve())})
        references.append({'id': record['image_id'], 'split': record['split'], **fp})
    files = sorted((args.collector / 'dataset').rglob('*.jpg'))
    assert len(files) == 269, 'Collection changed; re-audit with user'
    assert len({p.stem for p in files}) == len(files)
    missing = [r['id'] for r in rows if r['status'] == 'accepted' and r['id'] not in {p.stem for p in files}]
    assert missing == ['e4e25a184c1b43f38f49fd1a78f3583e'], 'Unexpected missing accepted images'
    accepted, excluded, corrections = [], [], []
    for source in files:
        row = by_id[source.stem]
        label = source.parent.name
        assert row['status'] == 'accepted' and label in LABELS
        fp = fingerprints(source)
        assert fp['sha256'] == row['sha256'], f'Source bytes changed: {source.name}'
        if label != row['label']:
            corrections.append({'id': source.stem, 'manifest_label': row['label'], 'approved_folder_label': label})
        match = None
        for ref in references:
            exact = fp['sha256'] == ref['sha256'] or fp['pixel_sha256'] == ref['pixel_sha256']
            near = (fp['dhash'] ^ ref['dhash']).bit_count() <= 6 and (fp['phash'] ^ ref['phash']).bit_count() <= 8
            if exact or near:
                match = {'matched_id': ref['id'], 'matched_split': ref['split'],
                         'reason': 'exact_duplicate' if exact else 'conservative_hash_similarity_hold',
                         'dhash_distance': (fp['dhash'] ^ ref['dhash']).bit_count(),
                         'phash_distance': (fp['phash'] ^ ref['phash']).bit_count()}
                break
        if match or min(fp['width'], fp['height']) < 224:
            excluded.append({'id': source.stem, 'label': label, **(match or {'reason': 'resolution_below_224'})})
            continue
        target = args.output / 'dataset/partner' / label / source.name
        accepted.append((source, target, fp))
        records.append({'image_id': str(target.resolve()), 'cohort': 'partner_2026_11_14',
                        'original_label': row['label'], 'approved_label': label,
                        'split': 'train', 'sha256': fp['sha256'], 'pixel_sha256': fp['pixel_sha256'],
                        'width': fp['width'], 'height': fp['height']})
        references.append({'id': 'partner/' + source.name, 'split': 'train', **fp})
    report = {'seed': 42, 'source_images': len(files), 'accepted_for_training': len(accepted),
              'source_counts': dict(collections.Counter(p.parent.name for p in files)),
              'training_addition_counts': dict(collections.Counter(p.parent.name for p, _, _ in accepted)),
              'split_counts': dict(collections.Counter(r['split'] for r in records)),
              'user_confirmed_folder_label_corrections': corrections,
              'missing_excluded_by_user': missing, 'deduplication_holds': excluded,
              'baseline_manifest_sha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
              'limitations': ['Supplemental images used for train only; original val/test preserved.',
                             'Hash checks do not establish subject independence or catch all crops/flips.',
                             'Source rights not independently verified.',
                             'Existing test has been evaluated previously; not a new untouched test set.']}
    print(json.dumps({k: v for k, v in report.items() if k not in ('user_confirmed_folder_label_corrections', 'deduplication_holds')}, indent=2))
    print('label_corrections', len(corrections), 'deduplication_holds', len(excluded))
    if not args.apply:
        return
    args.output.mkdir(parents=True)
    for source, target, fp in accepted:
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == fp['sha256']
    (args.output / 'curated_manifest.json').write_text(json.dumps({'records': records}, indent=2), encoding='utf8')
    (args.output / 'dataset_audit.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print('Snapshot verified:', args.output)


if __name__ == '__main__':
    main()
