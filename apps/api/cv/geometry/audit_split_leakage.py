"""Read-only cross-split duplicate screening; similarity is not subject identity."""
import argparse
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, ImageDraw
from scipy.fft import dctn


def phash(im):
    coeff = dctn(np.asarray(im.resize((32, 32)), dtype=float), norm='ortho')[:8, :8].flatten()
    return np.packbits(coeff > np.median(coeff[1:])).tobytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Use a new output directory'
    cv2.setNumThreads(2)
    cv2.setRNGSeed(42)
    records = json.loads(args.manifest.read_text('utf8'))['records']
    sift = cv2.SIFT_create(nfeatures=600)
    features, hashes, thumbs, exact = [], [], [], []
    for r in records:
        path = Path(r['image_id'])
        raw = hashlib.sha256(path.read_bytes()).hexdigest()
        assert raw == r['sha256'], f'Image changed: {path}'
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert('RGB')
            pixel = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
            exact.append((raw, pixel))
            gray = image.convert('L')
            views = [gray, ImageOps.mirror(gray)]
            w, h = gray.size
            crop = gray.crop((int(w*.1), int(h*.1), int(w*.9), int(h*.9)))
            views += [crop, ImageOps.mirror(crop)]
            hashes.append([np.unpackbits(np.frombuffer(phash(v), dtype=np.uint8)) for v in views])
            vectors = []
            for v in views[:2]:
                a = np.asarray(v.resize((24, 24)), dtype=np.float32).flatten()
                a -= a.mean()
                vectors.append(a / max(float(np.linalg.norm(a)), 1e-6))
            thumbs.append(vectors)
            image.thumbnail((640, 640))
            g = np.asarray(image.convert('L'))
            kp, des = sift.detectAndCompute(g, None)
            features.append((kp, des, g.shape))
    hashes = np.array(hashes)
    thumbs = np.array(thumbs)
    candidates = {}
    total_pairs = 0
    exact_pairs = []
    # Every cross-split pair gets full/flip/center-crop hash and thumbnail screening.
    for i, a in enumerate(records):
        scored = []
        for j in range(i + 1, len(records)):
            b = records[j]
            if a['split'] == b['split']:
                continue
            total_pairs += 1
            distance = int(np.count_nonzero(hashes[i, :, None, :] != hashes[j, None, :, :], axis=2).min())
            similarity = float((thumbs[i] @ thumbs[j].T).max())
            pair = {'i': i, 'j': j, 'phash_min_distance': distance, 'thumbnail_correlation': similarity}
            if exact[i][0] == exact[j][0] or exact[i][1] == exact[j][1]:
                exact_pairs.append(pair)
            scored.append(pair)
            if distance <= 10 or similarity >= .93:
                candidates[i, j] = pair
        # Retain nearest pairs for each split, even when broad thresholds are missed.
        for split in ['train', 'val', 'test']:
            pool = [p for p in scored if records[p['j']]['split'] == split]
            for key, reverse in [('phash_min_distance', False), ('thumbnail_correlation', True)]:
                for pair in sorted(pool, key=lambda p: p[key], reverse=reverse)[:3]:
                    candidates[pair['i'], pair['j']] = pair
    print('Screened pairs:', total_pairs, 'local-feature candidates:', len(candidates), flush=True)
    bf = cv2.BFMatcher()
    results = []
    for pair in candidates.values():
        i, j = pair['i'], pair['j']
        k1, d1, shape1 = features[i]
        k2, d2, shape2 = features[j]
        best = {'inliers': 0, 'good_matches': 0, 'inlier_ratio': 0., 'coverage_a': 0., 'coverage_b': 0.}
        if d1 is not None and d2 is not None and len(d2) >= 2:
            good = [m for matches in bf.knnMatch(d1, d2, k=2) if len(matches) == 2
                    for m, n in [matches] if m.distance < .7 * n.distance]
            if len(good) >= 6:
                p1 = np.float32([k1[m.queryIdx].pt for m in good])
                p2 = np.float32([k2[m.trainIdx].pt for m in good])
                for flip in [False, True]:
                    query = p1.copy()
                    if flip:
                        query[:, 0] = shape1[1] - 1 - query[:, 0]
                    matrix, mask = cv2.findHomography(query, p2, cv2.RANSAC, 4., maxIters=1000)
                    if mask is None:
                        continue
                    keep = mask.ravel().astype(bool)
                    count = int(keep.sum())
                    if count > best['inliers']:
                        def coverage(points, shape):
                            return float(cv2.contourArea(cv2.convexHull(points)) / (shape[0]*shape[1])) if len(points) >= 3 else 0.
                        best = {'inliers': count, 'good_matches': len(good), 'inlier_ratio': count/len(good),
                                'coverage_a': coverage(p1[keep], shape1), 'coverage_b': coverage(p2[keep], shape2)}
        strong = best['inliers'] >= 15 and best['inlier_ratio'] >= .5 and min(best['coverage_a'], best['coverage_b']) >= .03
        results.append({**pair, **best, 'geometric_flag': strong,
                        'a': {k: records[i].get(k) for k in ['image_id', 'split', 'approved_label', 'cohort']},
                        'b': {k: records[j].get(k) for k in ['image_id', 'split', 'approved_label', 'cohort']}})
    results.sort(key=lambda p: (p['geometric_flag'], p['inliers'], -p['phash_min_distance']), reverse=True)
    args.output.mkdir(parents=True)
    summary = {'images': len(records), 'split_counts': dict(Counter(r['split'] for r in records)),
               'cross_split_pairs_screened': total_pairs, 'exact_cross_split_pairs': exact_pairs,
               'local_feature_pairs_checked': len(results), 'geometric_flag_count': sum(p['geometric_flag'] for p in results),
               'manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
               'limitations': ['Heuristic retrieval, not exhaustive local-feature verification.',
                              'No reliable subject IDs or original source URLs; subject independence cannot be established.',
                              'SIFT descriptors are not flip-invariant; flipped hashes aid retrieval, not guaranteed feature verification.',
                              'Geometric matches may be background/watermark, requiring visual review.',
                              'No datasets, models or splits modified.']}
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf8')
    (args.output/'pairs.json').write_text(json.dumps(results, indent=2), encoding='utf8')
    selected = results[:40]
    # Also show hash-nearest candidates without geometric flags.
    for p in sorted(results, key=lambda p: p['phash_min_distance'])[:20]:
        if p not in selected:
            selected.append(p)
    links = []
    for rank, p in enumerate(selected):
        canvas = Image.new('RGB', (800, 460), 'white')
        draw = ImageDraw.Draw(canvas)
        for col, key in enumerate(['a', 'b']):
            with Image.open(p[key]['image_id']) as source:
                im = ImageOps.exif_transpose(source).convert('RGB')
                im.thumbnail((390, 385))
                canvas.paste(im, (col*400+(390-im.width)//2, 45))
            draw.text((col*400+5, 5), p[key]['split']+' / '+p[key]['approved_label'], fill='black')
            draw.text((col*400+5, 25), Path(p[key]['image_id']).name[:45], fill='black')
        draw.text((5, 435), f"#{rank} inliers={p['inliers']} ratio={p['inlier_ratio']:.2f} phash={p['phash_min_distance']} geom={p['geometric_flag']}", fill='black')
        filename=f'pair_{rank:03d}.jpg'
        canvas.save(args.output/filename, quality=85)
        links.append(f'<figure><img loading="lazy" src="{filename}"><figcaption>{html.escape(str(p["i"]))} vs {p["j"]}</figcaption></figure>')
    (args.output/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Cross-split audit</title><h1>Heuristic candidates, not confirmed duplicates</h1>'+''.join(links), encoding='utf8')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
