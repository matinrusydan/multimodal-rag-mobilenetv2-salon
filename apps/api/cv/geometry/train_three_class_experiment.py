"""Isolated three-class experiment; never changes canonical source labels."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from train_hair_type import HERE, train_and_evaluate

CLASSES = ['lurus', 'bergelombang', 'keriting']
MAPPING = {**{c: c for c in CLASSES}, 'sangat-keriting': 'keriting'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Output must be a new experiment directory')
    manifest = json.loads(args.source_manifest.read_text('utf8'))
    for rec in manifest['records']:
        source = Path(rec['image_id'])
        assert source.is_absolute() and source.is_file()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == rec['sha256']
        rec['four_class_label'] = rec['approved_label']
        rec['approved_label'] = MAPPING[rec['approved_label']]
    manifest['classes'] = CLASSES
    manifest['label_mapping'] = MAPPING
    manifest['source_manifest'] = str(args.source_manifest.resolve())
    args.output.mkdir(parents=True)
    path = args.output / 'curated_manifest.json'
    path.write_text(json.dumps(manifest, indent=2), encoding='utf8')
    print('Mapped counts:', {s: dict(Counter(r['approved_label'] for r in manifest['records'] if r['split'] == s)) for s in ['train', 'val', 'test']}, flush=True)
    active = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / 'weights').glob('hair_type*') if p.is_file()}
    (args.output / 'active_model_hashes_before.json').write_text(json.dumps(active, indent=2), encoding='utf8')
    if args.prepare_only:
        return
    train_and_evaluate(manifest_path=path, weights_dir=args.output / 'weights',
                       reports_dir=args.output / 'reports', figures_dir=args.output / 'figures',
                       arch='efficientnet_v2_s', batch_size=8, epochs=35, patience=10,
                       seed=args.seed, device_str='cuda', class_names=CLASSES)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p, digest in active.items())


if __name__ == '__main__':
    main()
