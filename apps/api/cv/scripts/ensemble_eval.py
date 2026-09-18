# -*- coding: utf-8 -*-
"""Evaluasi ensemble + TTA untuk hair_length (boost akurasi final).

Menggabungkan beberapa model ONNX (rata-rata softmax) + Test-Time Augmentation
(hflip) -> prediksi lebih stabil & akurat. Lalu memilih konfigurasi terbaik dan
menyalinnya ke model produksi (single-file, TTA-consistent).

Jalankan (global/ai venv: onnxruntime + torch):
  python apps\\api\\cv\\scripts\\ensemble_eval.py
"""

from __future__ import annotations

import json
import shutil
from itertools import combinations
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

BASE = Path(__file__).resolve().parents[1]
WEIGHTS = BASE / "weights"
INDEX = BASE / "preprocessed_length_merged" / "index_merged.json"
PROD = BASE.parents[1] / "ai" / "cv" / "weights"
CLS = ["pendek", "pendek-menengah", "menengah", "panjang"]

CANDIDATES = ["hair_length_s42.onnx", "hair_length_s7.onnx", "hair_length_s123.onnx"]


def softmax(x):
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def load_sessions():
    out = {}
    for name in CANDIDATES:
        p = WEIGHTS / name
        if p.exists():
            out[name] = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
    return out


def predict(sessions, tensor, tta=True):
    """Rata-rata probabilitas seluruh model & (opsional) TTA hflip."""
    probs = []
    for s in sessions.values():
        iname = s.get_inputs()[0].name
        probs.append(softmax(s.run(None, {iname: tensor})[0])[0])
        if tta:
            flip = tensor[:, :, :, ::-1].copy()
            probs.append(softmax(s.run(None, {iname: flip})[0])[0])
    return np.mean(probs, axis=0)


def eval_combo(sessions, val_entries, tta):
    yt, yp = [], []
    for e in val_entries:
        a = torch.load(BASE / e["pt"], weights_only=True).numpy().astype(np.float32)
        yt.append(CLS.index(e["kelas"]))
        yp.append(int(np.argmax(predict(sessions, a, tta))))
    acc = sum(1 for t, p in zip(yt, yp, strict=False) if t == p) / len(yt)
    return acc, yt, yp


def main():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    val_entries = [e for e in idx["index"]["val"] if e["sumber"] != "figaro"]
    all_sessions = load_sessions()
    print(f"model tersedia: {list(all_sessions)}")
    print(f"val: {len(val_entries)}")

    # bandingkan: single, ensemble, tiap dgn/tanpa TTA
    results = {}
    names = list(all_sessions)
    for r in range(1, len(names) + 1):
        for combo in combinations(names, r):
            sub = {k: all_sessions[k] for k in combo}
            for tta in (False, True):
                acc, yt, yp = eval_combo(sub, val_entries, tta)
                key = "+".join(k.replace("hair_length_", "").replace(".onnx", "") for k in combo) + ("+TTA" if tta else "")
                results[key] = acc
                print(f"  {key:40s} acc={acc:.4f}")

    best_key = max(results, key=results.get)
    best_acc = results[best_key]
    print(f"\n>>> TERBAIK: {best_key} = {best_acc:.4f}")

    # simpan laporan
    (BASE / "reports" / "hair_length_ensemble.json").write_text(
        json.dumps({"val": len(val_entries), "results": results, "best": best_key, "best_acc": round(best_acc, 4)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # deploy: pilih model INDIVIDU dengan akurasi tertinggi (single-file, tanpa ensemble
    # agar produksi tetap ringan & TTA-consistent).
    single_keys = [k for k in results if "+" not in k]
    best_single = max(single_keys, key=lambda k: results[k])
    tag = best_single.replace("hair_length_", "").replace(".onnx", "")
    src = WEIGHTS / f"hair_length_{tag}.onnx"
    PROD.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, PROD / "hair_length.onnx")
    print(f"deploy: {src.name} -> {PROD / 'hair_length.onnx'} (acc={results[best_single]:.4f})")


if __name__ == "__main__":
    main()
