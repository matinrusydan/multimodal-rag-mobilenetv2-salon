# -*- coding: utf-8 -*-
"""Evaluasi & bandingkan dua model hair_length (geometric vs gemini) — Fase 3.3.

Membaca index_{method}.json (label benar) lalu evaluasi ONNX pada split val.
Menghasilkan laporan perbandingan + confusion matrix PNG per metode.

Jalankan (Python global: torch + onnxruntime):
  $env:PYTHONIOENCODING='utf-8'; python apps\\api\\cv\\scripts\\compare_length_models.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

try:
    from PIL import Image, ImageDraw

    HAS_PIL = True
except Exception:
    HAS_PIL = False

BASE = Path(__file__).resolve().parents[1]
WEIGHTS = BASE / "weights"
INDEX_DIR = BASE / "preprocessed_length"
REPORTS = BASE / "reports"

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e / np.sum(e, axis=-1, keepdims=True)


def load_tensor(rel: str) -> np.ndarray:
    t = torch.load(BASE / rel, weights_only=True, map_location="cpu")
    a = t.detach().cpu().numpy()
    if a.ndim == 3:
        a = a[np.newaxis, ...]
    return a.astype(np.float32)


def metrics(y_true, y_pred, classes) -> dict:
    n = len(classes)
    cm = np.zeros((n, n), dtype=int)
    idx = {c: i for i, c in enumerate(classes)}
    for t, p in zip(y_true, y_pred, strict=False):
        cm[idx[t], idx[p]] += 1
    total = int(cm.sum())
    acc = float(np.trace(cm) / total) if total else 0.0
    per = {}
    for i, c in enumerate(classes):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum() - tp)
        fn = int(cm[i, :].sum() - tp)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per[c] = {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4), "support": int(cm[i, :].sum())}
    macro = float(np.mean([per[c]["f1"] for c in classes])) if classes else 0.0
    return {"accuracy": round(acc, 4), "macro_f1": round(macro, 4), "per_class": per, "confusion_matrix": cm.tolist(), "n": total}


def evaluate_model(onnx_path: Path, index: dict) -> dict:
    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    in_name = sess.get_inputs()[0].name
    out_name = sess.get_outputs()[0].name

    val = index["index"]["val"]
    y_true, y_pred = [], []
    for entry in val:
        a = load_tensor(entry["pt"])
        out = sess.run([out_name], {in_name: a})[0]
        probs = softmax(np.asarray(out, dtype=np.float32))
        pred_idx = int(np.argmax(probs[0]))
        y_true.append(entry["label"])
        y_pred.append(LENGTH_CLASSES[pred_idx])
    return metrics(y_true, y_pred, LENGTH_CLASSES)


def save_cm_png(cm, classes, path: Path) -> None:
    if not HAS_PIL:
        return
    n = len(classes)
    cell, margin = 70, 160
    W = margin + cell * n + 20
    H = margin + cell * n + 20
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    arr = np.array(cm)
    vmax = arr.max() if arr.max() else 1
    for i in range(n):
        for j in range(n):
            v = int(arr[i, j])
            shade = int(255 - 200 * (v / vmax))
            x0, y0 = margin + j * cell, margin + i * cell
            d.rectangle([x0, y0, x0 + cell, y0 + cell], fill=(shade, shade, 255), outline="gray")
            d.text((x0 + cell / 2 - 6, y0 + cell / 2 - 6), str(v), fill="black")
        d.text((10, margin + i * cell + 20), classes[i][:14], fill="black")
        d.text((margin + i * cell + 10, 10), classes[i][:14], fill="black")
    img.save(path)


def main() -> None:
    results = {}
    for method, onnx_name in [("geometric", "hair_length_geom.onnx"), ("gemini", "hair_length_gemini.onnx")]:
        index_path = INDEX_DIR / f"index_{method}.json"
        onnx_path = WEIGHTS / onnx_name
        if not index_path.exists() or not onnx_path.exists():
            print(f"SKIP {method}: index/onnx tidak ada")
            continue
        index = json.loads(index_path.read_text(encoding="utf-8"))
        res = evaluate_model(onnx_path, index)
        res["onnx"] = str(onnx_path)
        res["val_label_distribution"] = {c: sum(1 for e in index["index"]["val"] if e["label"] == c) for c in LENGTH_CLASSES}
        results[method] = res
        save_cm_png(res["confusion_matrix"], LENGTH_CLASSES, REPORTS / f"eval_hair_length_{method}_confusion.png")

    out = REPORTS / "hair_length_comparison.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== Perbandingan model hair_length ===")
    for method, res in results.items():
        print(f"\n[{method}] akurasi={res['accuracy']} macro-F1={res['macro_f1']} val n={res['n']}")
        for c in LENGTH_CLASSES:
            m = res["per_class"][c]
            print(f"   {c:16s} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} n={m['support']}")

    if results:
        best = max(results.items(), key=lambda kv: kv[1]["accuracy"])
        print(f"\n>>> METODE TERBAIK: {best[0]} (akurasi {best[1]['accuracy']})")
    print(f"\nLaporan -> {out}")


if __name__ == "__main__":
    main()
