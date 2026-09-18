# -*- coding: utf-8 -*-
"""Evaluasi model ONNX klasifikasi rambut (hair_type / hair_length).

Menghitung accuracy, precision/recall/F1 per kelas, dan confusion matrix dari
folder tensor NCHW (.pt) hasil preprocess. Output JSON + PNG confusion matrix.

Jalankan (venv apps/ai yang punya onnxruntime+numpy+Pillow):
  .\\apps\\ai\\.venv\\Scripts\\python.exe apps\\api\\cv\\scripts\\evaluate_onnx.py \\
      --model apps/api/cv/weights/hair_type.onnx \\
      --data  apps/api/cv/preprocessed \\
      --task  hair_type \\
      --out   apps/api/cv/reports

Argumen:
  --model   path .onnx
  --data    folder dataset berisi val/<kelas>/*.pt  (dan opsional train/)
  --task    nama task (untuk penamaan output) -> default dari nama model
  --split   subfolder split (default: val)
  --out     folder output laporan
  --labels  path hair_*_labels.json (opsional; default di samping model)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import onnxruntime as ort

try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover
    Image = None  # type: ignore


INPUT_NAME = "input"
OUTPUT_NAME = "logits"


# ---------------------------------------------------------------- data loading
def load_tensor(path: Path) -> np.ndarray | None:
    """Load tensor .pt (NCHW) memakai numpy jika formatnya mentah; fallback torch bila ada."""
    try:
        import torch  # type: ignore

        t = torch.load(path, weights_only=True, map_location="cpu")
        arr = t.detach().cpu().numpy()
        if arr.ndim == 3:
            arr = arr[np.newaxis, ...]
        return arr.astype(np.float32)
    except Exception:
        return None


def discover_classes(data_dir: Path, labels_path: Path | None) -> list[str]:
    """Urutan kelas HARUS mengikuti labels JSON (urutan training), bukan alphabetical.

    Alphabetical folder (bergelombang, keriting, lurus, sangat-keriting) != urutan
    training (lurus, bergelombang, keriting, sangat-keriting) -> index argmax ONNX
    akan salah label kalau memakai urutan folder.
    """
    folder_classes = sorted([d.name for d in data_dir.iterdir() if d.is_dir()])
    if labels_path and labels_path.exists():
        try:
            saved = json.loads(labels_path.read_text(encoding="utf-8")).get("classes")
            if saved and set(saved) == set(folder_classes):
                return list(saved)
        except Exception:
            pass
    return folder_classes


# ---------------------------------------------------------------- inference
def run_batch(session: ort.InferenceSession, batch: np.ndarray) -> np.ndarray:
    out = session.run([OUTPUT_NAME], {INPUT_NAME: batch})[0]
    arr = np.asarray(out, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr[np.newaxis, ...]
    return arr


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e / np.sum(e, axis=-1, keepdims=True)


# ---------------------------------------------------------------- metrics
def confusion_and_metrics(y_true: list[int], y_pred: list[int], n: int) -> dict:
    cm = np.zeros((n, n), dtype=int)
    for t, p in zip(y_true, y_pred, strict=False):
        cm[t, p] += 1

    total = int(cm.sum())
    acc = float(np.trace(cm) / total) if total else 0.0

    per_class = {}
    for i in range(n):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum() - tp)
        fn = int(cm[i, :].sum() - tp)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        support = int(cm[i, :].sum())
        per_class[i] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    supports = [per_class[i]["support"] for i in range(n)]
    macro_f1 = float(np.mean([per_class[i]["f1"] for i in range(n)])) if n else 0.0
    weighted_f1 = (
        float(sum(per_class[i]["f1"] * supports[i] for i in range(n)) / sum(supports))
        if sum(supports)
        else 0.0
    )

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class": {str(i): per_class[i] for i in range(n)},
        "confusion_matrix": cm.tolist(),
        "n_samples": total,
    }


def save_confusion_png(cm: list[list[int]], classes: list[str], out_path: Path) -> bool:
    if Image is None:
        return False
    n = len(classes)
    cell = 60
    margin = 140
    w = margin + cell * n + 20
    h = margin + cell * n + 20
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    arr = np.array(cm)
    vmax = arr.max() if arr.size and arr.max() > 0 else 1

    for i in range(n):
        for j in range(n):
            v = int(arr[i, j])
            shade = int(255 - 200 * (v / vmax))
            x0 = margin + j * cell
            y0 = margin + i * cell
            d.rectangle([x0, y0, x0 + cell, y0 + cell], fill=(shade, shade, 255), outline="gray")
            d.text((x0 + cell / 2 - 6, y0 + cell / 2 - 6), str(v), fill="black")
        d.text((10, margin + i * cell + cell / 2 - 6), classes[i][:14], fill="black")
        d.text((margin + i * cell + cell / 2 - 6, 10), classes[i][:14], fill="black")
    d.text((margin, h - 25), "Prediksi ->", fill="black")
    d.text((5, margin - 30), "Aktual v", fill="black")
    img.save(out_path)
    return True


# ---------------------------------------------------------------- main
def evaluate(model_path: Path, data_dir: Path, split: str, labels_path: Path | None) -> dict:
    global INPUT_NAME, OUTPUT_NAME

    classes = discover_classes(data_dir / split, labels_path)
    if not classes:
        raise SystemExit(f"Tidak ada kelas di {data_dir / split}")

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    INPUT_NAME = inputs[0].name if inputs else INPUT_NAME
    OUTPUT_NAME = outputs[0].name if outputs else OUTPUT_NAME

    y_true: list[int] = []
    y_pred: list[int] = []
    per_class_conf: dict[int, list[float]] = defaultdict(list)
    missing = 0

    for cls_idx, cls in enumerate(classes):
        files = sorted((data_dir / split / cls).glob("*.pt"))
        for f in files:
            tensor = load_tensor(f)
            if tensor is None:
                missing += 1
                continue
            logits = run_batch(session, tensor)
            probs = softmax(logits)
            pred = int(np.argmax(probs[0]))
            y_true.append(cls_idx)
            y_pred.append(pred)
            per_class_conf[cls_idx].append(float(probs[0][pred]))

    metrics = confusion_and_metrics(y_true, y_pred, len(classes))
    metrics["classes"] = classes
    metrics["model"] = str(model_path)
    metrics["split"] = split
    metrics["unreadable_tensors"] = missing
    metrics["mean_confidence_per_class"] = {
        classes[i]: round(float(np.mean(v)), 4) if v else None
        for i, v in per_class_conf.items()
    }
    if labels_path and labels_path.exists():
        metrics["labels_file"] = json.loads(labels_path.read_text(encoding="utf-8"))
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluasi ONNX klasifikasi rambut")
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--task", default=None)
    ap.add_argument("--split", default="val")
    ap.add_argument("--out", default=None)
    ap.add_argument("--labels", default=None)
    args = ap.parse_args()

    model_path = Path(args.model).resolve()
    data_dir = Path(args.data).resolve()
    task = args.task or re.sub(r"\.onnx$", "", model_path.name)
    out_dir = Path(args.out).resolve() if args.out else model_path.parent / ".." / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    labels_path = Path(args.labels).resolve() if args.labels else (model_path.parent / f"{task}_labels.json")

    metrics = evaluate(model_path, data_dir, args.split, labels_path)

    report_path = out_dir / f"eval_{task}.json"
    report_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    png_path = out_dir / f"eval_{task}_confusion.png"
    save_confusion_png(metrics["confusion_matrix"], metrics["classes"], png_path)

    print(f"\n=== Evaluasi {task} (split={args.split}) ===")
    print(f"akurasi   : {metrics['accuracy']}")
    print(f"macro-F1  : {metrics['macro_f1']}")
    print(f"weighted-F1: {metrics['weighted_f1']}")
    for i, cls in enumerate(metrics["classes"]):
        m = metrics["per_class"][str(i)]
        print(f"  {cls:16s} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} n={m['support']}")
    print(f"\nJSON -> {report_path}")
    print(f"PNG  -> {png_path}")
    if metrics["unreadable_tensors"]:
        print(f"WARNING: {metrics['unreadable_tensors']} tensor tidak terbaca (perlu torch)", file=sys.stderr)


if __name__ == "__main__":
    main()
