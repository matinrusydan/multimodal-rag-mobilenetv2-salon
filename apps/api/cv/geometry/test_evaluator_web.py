"""Web-Based CV 3-Class Model Accuracy Evaluator on External Dataset.

Alat evaluasi mandiri berbasis web khusus untuk menguji akurasi model 3 kelas
(lurus, bergelombang, keriting) pada citra baru di luar split data lama.

Catatan Siklus Hidup:
- Berkas ini dibuat untuk pengujian/debugging akurasi data baru.
- Dapat dihapus setelah selesai dengan persetujuan pengguna:
    Remove-Item apps/api/cv/geometry/test_evaluator_web.py
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import io
import json
import logging
import os
import sys
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from classify_hierarchical import preprocess_for_hair_type, softmax

DEFAULT_PORT = 8790
DEFAULT_HOST = "127.0.0.1"
CLASSES = ["lurus", "bergelombang", "keriting"]
DEFAULT_MODEL_PATH = (
    HERE
    / "experiments"
    / "partner-20261114-threeclass-corrected-seed42"
    / "weights"
    / "hair_type.onnx"
)

# Global in-memory evaluation session
SESSION_STORE: Dict[str, Any] = {
    "model_path": str(DEFAULT_MODEL_PATH),
    "model_loaded": False,
    "model_info": {},
    "records": [],  # List of evaluation items
    "rejected_records": [],  # List of rejected duplicate items
    "session_file": HERE / "eval_records_3class.json",
    "known_raw_hashes": {},
    "known_pixel_hashes": {},
}

_classifier_session = None
_input_name = None


def load_known_manifest_hashes() -> None:
    """Index all raw SHA256 and pixel SHA256 hashes from existing split manifests."""
    manifest_paths = [
        HERE / "experiments" / "partner-20261114-threeclass-corrected-seed42" / "curated_manifest.json",
        HERE / "reports" / "phase1" / "curated_manifest.json",
        HERE / "experiments" / "partner-20261114-seed42" / "curated_manifest.json",
        HERE / "experiments" / "partner-20261114-threeclass-seed42" / "curated_manifest.json",
    ]
    raw_map = {}
    pixel_map = {}
    for p in manifest_paths:
        if not p.is_file():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            for r in d.get("records", []):
                name = Path(r["image_id"]).name
                split = r.get("split", "unknown")
                label = r.get("approved_label", "unknown")
                info = {"name": name, "split": split, "label": label, "image_id": r["image_id"]}
                if r.get("sha256") and r["sha256"] not in raw_map:
                    raw_map[r["sha256"]] = info
                if r.get("pixel_sha256") and r["pixel_sha256"] not in pixel_map:
                    pixel_map[r["pixel_sha256"]] = info
        except Exception as e:
            logging.warning("Gagal memuat manifest %s: %s", p, e)

    SESSION_STORE["known_raw_hashes"] = raw_map
    SESSION_STORE["known_pixel_hashes"] = pixel_map
    print(f"Proteksi duplikat siap: Terindeks {len(raw_map)} citra split lama (train/val/test).")


def check_known_duplicate(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    """Check if uploaded image bytes match any existing train/val/test images."""
    raw_sha = hashlib.sha256(image_bytes).hexdigest()
    raw_map = SESSION_STORE.get("known_raw_hashes", {})
    if raw_sha in raw_map:
        m = raw_map[raw_sha]
        return {
            "type": "exact_file_hash",
            "split": m["split"],
            "name": m["name"],
            "label": m["label"],
            "sha256": raw_sha,
        }

    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            digest = hashlib.sha256()
            digest.update(f"{image.width}x{image.height}:RGB:".encode("ascii"))
            digest.update(image.tobytes())
            pix_sha = digest.hexdigest()
            pixel_map = SESSION_STORE.get("known_pixel_hashes", {})
            if pix_sha in pixel_map:
                m = pixel_map[pix_sha]
                return {
                    "type": "pixel_hash",
                    "split": m["split"],
                    "name": m["name"],
                    "label": m["label"],
                    "pixel_sha256": pix_sha,
                }
    except Exception:
        pass
    return None


def get_classifier(model_path: Path):
    global _classifier_session, _input_name
    if _classifier_session is None:
        import onnxruntime as ort

        if not model_path.is_file():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        _classifier_session = sess
        _input_name = sess.get_inputs()[0].name
        SESSION_STORE["model_loaded"] = True
        SESSION_STORE["model_info"] = {
            "name": model_path.name,
            "path": str(model_path),
            "size_mb": round(model_path.stat().st_size / (1024 * 1024), 2),
            "classes": CLASSES,
        }
    return _classifier_session, _input_name


def predict_image(image_bytes: bytes) -> Dict[str, Any]:
    """Predict 3-class hair type from image bytes."""
    sess, inp_name = get_classifier(Path(SESSION_STORE["model_path"]))
    t0 = time.perf_counter()

    with Image.open(io.BytesIO(image_bytes)) as original:
        img_rgb = ImageOps.exif_transpose(original).convert("RGB")
        orig_w, orig_h = img_rgb.size

        # Create thumbnail for web preview
        thumb = img_rgb.copy()
        thumb.thumbnail((320, 320), Image.Resampling.LANCZOS)
        thumb_buf = io.BytesIO()
        thumb.save(thumb_buf, format="JPEG", quality=80)
        thumb_b64 = "data:image/jpeg;base64," + base64.b64encode(thumb_buf.getvalue()).decode("utf-8")

        tensor = preprocess_for_hair_type(img_rgb)

    logits = sess.run(None, {inp_name: tensor})[0][0]
    probs = softmax(logits)
    pred_idx = int(np.argmax(probs))
    pred_cls = CLASSES[pred_idx]
    conf = float(probs[pred_idx])
    lat_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "pred_label": pred_cls,
        "confidence": round(conf, 4),
        "probabilities": {cls_name: round(float(p), 4) for cls_name, p in zip(CLASSES, probs)},
        "latency_ms": round(lat_ms, 2),
        "width": orig_w,
        "height": orig_h,
        "thumb_b64": thumb_b64,
    }


def compute_evaluation_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate overall accuracy, macro-F1, per-class stats, and confusion matrix."""
    # Filter only evaluated records (with valid true_label in CLASSES)
    eval_recs = [r for r in records if r.get("true_label") in CLASSES]
    n = len(eval_recs)

    if n == 0:
        return {
            "total_items": len(records),
            "evaluated_count": 0,
            "correct_count": 0,
            "misclassified_count": 0,
            "accuracy": 0.0,
            "accuracy_percent": 0.0,
            "macro_f1": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "per_class": {
                c: {"support": 0, "correct": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
                for c in CLASSES
            },
            "confusion_matrix": {t: {p: 0 for p in CLASSES} for t in CLASSES},
            "avg_confidence": 0.0,
            "avg_latency_ms": 0.0,
        }

    cm = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    correct = 0
    total_conf = 0.0
    total_lat = 0.0

    for r in eval_recs:
        t = r["true_label"]
        p = r["pred_label"]
        if t in cm and p in cm[t]:
            cm[t][p] += 1
        if t == p:
            correct += 1
        total_conf += r.get("confidence", 0.0)
        total_lat += r.get("latency_ms", 0.0)

    per_class = {}
    f1_list, prec_list, rec_list = [], [], []

    for c in CLASSES:
        tp = cm[c][c]
        support = sum(cm[c].values())
        pred_pos = sum(cm[t][c] for t in CLASSES)

        prec = (tp / pred_pos) if pred_pos > 0 else 0.0
        rec = (tp / support) if support > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        per_class[c] = {
            "support": support,
            "correct": tp,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
        }
        f1_list.append(f1)
        prec_list.append(prec)
        rec_list.append(rec)

    acc = correct / n
    return {
        "total_items": len(records),
        "evaluated_count": n,
        "correct_count": correct,
        "misclassified_count": n - correct,
        "accuracy": round(acc, 4),
        "accuracy_percent": round(acc * 100.0, 2),
        "macro_f1": round(float(np.mean(f1_list)), 4),
        "macro_precision": round(float(np.mean(prec_list)), 4),
        "macro_recall": round(float(np.mean(rec_list)), 4),
        "per_class": per_class,
        "confusion_matrix": cm,
        "avg_confidence": round(total_conf / n, 4),
        "avg_latency_ms": round(total_lat / n, 2),
    }


def save_session_to_disk() -> None:
    session_file: Path = SESSION_STORE["session_file"]
    try:
        data = {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model_info": SESSION_STORE.get("model_info", {}),
            "records": [
                {k: v for k, v in r.items() if k != "thumb_b64"}
                for r in SESSION_STORE["records"]
            ],
            "rejected_records": SESSION_STORE.get("rejected_records", []),
        }
        session_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logging.warning("Gagal menyimpan sesi evaluasi ke disk: %s", e)


def load_session_from_disk() -> None:
    session_file: Path = SESSION_STORE["session_file"]
    if session_file.is_file():
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            recs = data.get("records", [])
            SESSION_STORE["records"] = recs
            SESSION_STORE["rejected_records"] = data.get("rejected_records", [])
            print(f"Memulihkan {len(recs)} riwayat pengujian ({len(SESSION_STORE['rejected_records'])} ditolak) dari {session_file.name}")
        except Exception as e:
            logging.warning("Gagal memuat sesi sebelumnya: %s", e)


class EvaluatorHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        # Keep console output concise
        if getattr(args, "__getitem__", None) and len(args) > 1 and str(args[1]) in ("400", "500"):
            super().log_message(format, *args)

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, html_text: str, status: int = 200) -> None:
        payload = html_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send_html(get_dashboard_html())
            return

        if path == "/api/status":
            metrics = compute_evaluation_metrics(SESSION_STORE["records"])
            self._send_json({
                "status": "ok",
                "model_info": SESSION_STORE.get("model_info", {}),
                "metrics": metrics,
                "records": SESSION_STORE["records"],
                "rejected_records": SESSION_STORE.get("rejected_records", []),
                "known_images_count": len(SESSION_STORE.get("known_raw_hashes", {})),
            })
            return

        if path == "/api/metrics":
            metrics = compute_evaluation_metrics(SESSION_STORE["records"])
            self._send_json({"status": "ok", "metrics": metrics})
            return

        if path == "/api/export/csv":
            self._export_csv()
            return

        if path == "/api/export/json":
            metrics = compute_evaluation_metrics(SESSION_STORE["records"])
            export_data = {
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "model_info": SESSION_STORE.get("model_info", {}),
                "metrics": metrics,
                "records": [
                    {k: v for k, v in r.items() if k != "thumb_b64"}
                    for r in SESSION_STORE["records"]
                ],
            }
            payload = json.dumps(export_data, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="evaluation_3class_results.json"')
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def _export_csv(self) -> None:
        output = io.StringIO()
        output.write("id,filename,true_label,pred_label,is_correct,confidence,prob_lurus,prob_bergelombang,prob_keriting,latency_ms,tested_at\n")
        for r in SESSION_STORE["records"]:
            probs = r.get("probabilities", {})
            p_l = probs.get("lurus", "")
            p_b = probs.get("bergelombang", "")
            p_k = probs.get("keriting", "")
            is_corr = "1" if r.get("is_correct") else "0"
            output.write(
                f'"{r.get("id","")}","{r.get("filename","")}","{r.get("true_label","")}",'
                f'"{r.get("pred_label","")}",{is_corr},{r.get("confidence","")},'
                f'{p_l},{p_b},{p_k},{r.get("latency_ms","")},"{r.get("tested_at","")}"\n'
            )
        payload = output.getvalue().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="evaluasi_akurasi_3kelas.csv"')
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 50 * 1024 * 1024:  # 50MB max upload
            self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Payload too large")
            return

        body = self.rfile.read(content_length)

        if path == "/api/predict":
            try:
                data = json.loads(body.decode("utf-8"))
                filename = data.get("filename", "unnamed.jpg")
                image_b64 = data.get("image_b64", "")
                true_label = data.get("true_label")
                if true_label not in CLASSES:
                    true_label = None

                if "," in image_b64:
                    image_b64 = image_b64.split(",", 1)[1]
                image_bytes = base64.b64decode(image_b64)

                # Check duplicate against existing split dataset (train/val/test)
                dup_match = check_known_duplicate(image_bytes)
                if dup_match:
                    reason = (
                        f"Citra '{filename}' DITOLAK: Terdeteksi merupakan data "
                        f"{dup_match['split'].upper()} lama (ID: {dup_match['name']}, Kelas: {dup_match['label']})."
                    )
                    rej_entry = {
                        "filename": filename,
                        "reason": reason,
                        "split": dup_match["split"],
                        "name": dup_match["name"],
                        "label": dup_match["label"],
                        "match_type": dup_match["type"],
                        "rejected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    if "rejected_records" not in SESSION_STORE:
                        SESSION_STORE["rejected_records"] = []
                    SESSION_STORE["rejected_records"].insert(0, rej_entry)
                    save_session_to_disk()
                    self._send_json({
                        "status": "rejected",
                        "rejected": True,
                        "filename": filename,
                        "reason": reason,
                        "match": dup_match,
                    })
                    return

                res = predict_image(image_bytes)
                item_id = str(uuid.uuid4())[:8]

                is_correct = (res["pred_label"] == true_label) if true_label else None

                record = {
                    "id": item_id,
                    "filename": filename,
                    "true_label": true_label,
                    "pred_label": res["pred_label"],
                    "is_correct": is_correct,
                    "confidence": res["confidence"],
                    "probabilities": res["probabilities"],
                    "latency_ms": res["latency_ms"],
                    "width": res["width"],
                    "height": res["height"],
                    "thumb_b64": res["thumb_b64"],
                    "tested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }

                SESSION_STORE["records"].insert(0, record)
                save_session_to_disk()

                metrics = compute_evaluation_metrics(SESSION_STORE["records"])
                self._send_json({"status": "ok", "record": record, "metrics": metrics})
            except Exception as e:
                logging.exception("Predict error")
                self._send_json({"status": "error", "message": str(e)}, status=500)
            return

        if path == "/api/update-label":
            try:
                data = json.loads(body.decode("utf-8"))
                item_id = data.get("id")
                new_label = data.get("true_label")
                if new_label not in CLASSES and new_label is not None:
                    self._send_json({"status": "error", "message": "Invalid label"}, status=400)
                    return

                found = False
                for r in SESSION_STORE["records"]:
                    if r.get("id") == item_id:
                        r["true_label"] = new_label
                        r["is_correct"] = (r["pred_label"] == new_label) if new_label else None
                        found = True
                        break

                if found:
                    save_session_to_disk()
                    metrics = compute_evaluation_metrics(SESSION_STORE["records"])
                    self._send_json({"status": "ok", "metrics": metrics})
                else:
                    self._send_json({"status": "error", "message": "Item not found"}, status=404)
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, status=500)
            return

        if path == "/api/delete-item":
            try:
                data = json.loads(body.decode("utf-8"))
                item_id = data.get("id")
                SESSION_STORE["records"] = [r for r in SESSION_STORE["records"] if r.get("id") != item_id]
                save_session_to_disk()
                metrics = compute_evaluation_metrics(SESSION_STORE["records"])
                self._send_json({"status": "ok", "metrics": metrics})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, status=500)
            return

        if path == "/api/clear-all":
            SESSION_STORE["records"] = []
            SESSION_STORE["rejected_records"] = []
            save_session_to_disk()
            metrics = compute_evaluation_metrics([])
            self._send_json({"status": "ok", "metrics": metrics, "rejected_records": []})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")


def get_dashboard_html() -> str:
    """Return responsive SPA evaluation dashboard HTML with interactive analytics."""
    return """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Evaluator Akurasi CV 3-Kelas | Data Baru Non-Split</title>
  <!-- Tailwind CSS via CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 50: '#eef2ff', 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca' }
          }
        }
      }
    }
  </script>
  <style>
    .dragover { border-color: #6366f1 !important; background-color: #e0e7ff !important; }
    .dark .dragover { background-color: #1e1b4b !important; }
  </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen font-sans antialiased">

  <!-- Top Navigation Header -->
  <header class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">
          CV
        </div>
        <div>
          <h1 class="text-base font-semibold leading-tight text-white flex items-center gap-2">
            Evaluator Model 3-Kelas
            <span class="text-xs font-medium px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              Data Baru (Non-Split)
            </span>
          </h1>
          <p class="text-xs text-slate-400">
            Model: <code class="text-indigo-300 font-mono" id="modelName">hair_type.onnx (EfficientNetV2-S Corrected)</code>
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2 text-xs">
        <a href="/api/export/csv" class="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5">
          <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          Export CSV
        </a>
        <a href="/api/export/json" class="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5">
          <svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
          Export JSON
        </a>
        <button onclick="clearAllRecords()" class="px-3 py-1.5 rounded-md bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800/60 transition">
          Reset Data
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 py-6 space-y-6">

    <!-- Information / Scope Banner -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-4 text-xs text-indigo-200/90 flex items-start gap-3">
        <span class="text-xl">🎯</span>
        <div class="space-y-1">
          <p class="font-semibold text-indigo-300">Tujuan Pengujian Data Baru:</p>
          <p>Halaman ini dikhususkan untuk menguji akurasi model hasil retrain 3-kelas (<span class="font-mono text-white">lurus, bergelombang, keriting</span>) pada citra baru yang <strong>bukan</strong> bagian dari split training/val/test lama. Setiap gambar yang diuji akan dihitung matriks akurasi, Macro-F1, dan Confusion Matrix secara langsung (live).</p>
        </div>
      </div>

      <div class="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 text-xs text-rose-200/90 flex items-start gap-3">
        <span class="text-xl">🛡️</span>
        <div class="space-y-1">
          <p class="font-semibold text-rose-300 flex items-center justify-between">
            <span>Proteksi Anti Data-Leakage (Tolak Otomatis):</span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-300" id="antiLeakageBadge">
              654 Citra Terproteksi
            </span>
          </p>
          <p>Setiap foto yang diunggah otomatis dicek terhadap <strong id="knownImagesCount">654 citra</strong> dataset split lama (train, validation, test). Citra yang identik langsung <strong>ditolak</strong> dan tidak dimasukkan ke dalam metrik akurasi.</p>
        </div>
      </div>
    </div>

    <!-- Upload & Batch Ingestion Section -->
    <section class="bg-slate-950/60 border border-slate-800 rounded-2xl p-5 shadow-xl">
      <h2 class="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
        <span>📤</span> Unggah Citra Uji Baru
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <div class="md:col-span-3">
          <label class="block text-xs font-medium text-slate-300 mb-1">
            Ground Truth Bawaan untuk Batch Unggahan (Opsional):
          </label>
          <div class="flex flex-wrap items-center gap-3">
            <label class="inline-flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
              <input type="radio" name="batchGt" value="" checked class="text-indigo-600 focus:ring-indigo-500">
              <span class="text-slate-400">Tentukan Nanti (Manual per foto)</span>
            </label>
            <label class="inline-flex items-center gap-1.5 text-xs text-emerald-400 cursor-pointer">
              <input type="radio" name="batchGt" value="lurus" class="text-indigo-600 focus:ring-indigo-500">
              <span>Semua Lurus</span>
            </label>
            <label class="inline-flex items-center gap-1.5 text-xs text-amber-400 cursor-pointer">
              <input type="radio" name="batchGt" value="bergelombang" class="text-indigo-600 focus:ring-indigo-500">
              <span>Semua Bergelombang</span>
            </label>
            <label class="inline-flex items-center gap-1.5 text-xs text-purple-400 cursor-pointer">
              <input type="radio" name="batchGt" value="keriting" class="text-indigo-600 focus:ring-indigo-500">
              <span>Semua Keriting</span>
            </label>
          </div>
          <p class="text-[11px] text-slate-500 mt-1">
            Tip: Jika Anda punya folder khusus berisi foto lurus, pilih "Semua Lurus" sebelum drag-and-drop agar otomatis dihitung akurasinya!
          </p>
        </div>

        <div class="flex items-end justify-end">
          <span id="uploadProgress" class="text-xs text-indigo-400 font-medium hidden">
            Memproses... (<span id="progressCount">0/0</span>)
          </span>
        </div>
      </div>

      <!-- Dropzone -->
      <div id="dropZone" class="border-2 border-dashed border-slate-700 hover:border-indigo-500 rounded-xl p-8 text-center cursor-pointer transition bg-slate-900/50">
        <input type="file" id="fileInput" multiple accept="image/jpeg,image/png,image/webp" class="hidden">
        <div class="flex flex-col items-center justify-center gap-2">
          <div class="w-12 h-12 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center text-2xl">
            🖼️
          </div>
          <div class="text-sm font-medium text-slate-200">
            Seret & Jatuhkan Foto di sini, atau <span class="text-indigo-400 underline">Klik untuk Memilih File</span>
          </div>
          <p class="text-xs text-slate-500">
            Mendukung JPG, PNG, WEBP (bisa pilih banyak file sekaligus)
          </p>
        </div>
      </div>
    </section>

    <!-- Key Metrics Cards -->
    <section class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      <!-- Accuracy Card -->
      <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col justify-between">
        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Akurasi Uji</span>
        <div class="mt-2 flex items-baseline gap-1">
          <span class="text-3xl font-extrabold text-emerald-400" id="metricAcc">0.0%</span>
        </div>
        <span class="text-[11px] text-slate-500 mt-1" id="metricCorrectRatio">0 / 0 citra</span>
      </div>

      <!-- Macro-F1 Card -->
      <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col justify-between">
        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Macro-F1</span>
        <div class="mt-2">
          <span class="text-3xl font-extrabold text-indigo-400" id="metricMacroF1">0.0000</span>
        </div>
        <span class="text-[11px] text-slate-500 mt-1">Rata-rata 3 kelas</span>
      </div>

      <!-- Macro Precision -->
      <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col justify-between">
        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Macro Precision</span>
        <div class="mt-2">
          <span class="text-3xl font-extrabold text-sky-400" id="metricMacroPrec">0.0000</span>
        </div>
        <span class="text-[11px] text-slate-500 mt-1">Kemurnian prediksi</span>
      </div>

      <!-- Macro Recall -->
      <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col justify-between">
        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Macro Recall</span>
        <div class="mt-2">
          <span class="text-3xl font-extrabold text-amber-400" id="metricMacroRec">0.0000</span>
        </div>
        <span class="text-[11px] text-slate-500 mt-1">Cakupan deteksi</span>
      </div>

      <!-- Error Count -->
      <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col justify-between">
        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Salah Prediksi</span>
        <div class="mt-2">
          <span class="text-3xl font-extrabold text-rose-400" id="metricErrors">0</span>
        </div>
        <span class="text-[11px] text-slate-500 mt-1" id="metricErrorNote">0 error terdeteksi</span>
      </div>

      <!-- Average Latency -->
      <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col justify-between">
        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Rerata Latensi</span>
        <div class="mt-2">
          <span class="text-3xl font-extrabold text-teal-400" id="metricLatency">0.0 ms</span>
        </div>
        <span class="text-[11px] text-slate-500 mt-1">CPU onnxruntime</span>
      </div>
    </section>

    <!-- Analytics Row: Confusion Matrix & Per-Class Breakdown -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Confusion Matrix Card (5 cols) -->
      <div class="lg:col-span-5 bg-slate-950/60 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <span>📊</span> Confusion Matrix (3x3)
          </h2>
          <span class="text-[11px] text-slate-500">Baris: Aktual | Kolom: Prediksi</span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-center border-collapse text-xs">
            <thead>
              <tr class="border-b border-slate-800 text-slate-400">
                <th class="p-2 text-left">Aktual / Pred</th>
                <th class="p-2 text-emerald-400 font-medium">Lurus</th>
                <th class="p-2 text-amber-400 font-medium">Gelombang</th>
                <th class="p-2 text-purple-400 font-medium">Keriting</th>
              </tr>
            </thead>
            <tbody id="cmBody">
              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>
        <p class="text-[11px] text-slate-500 mt-3 italic">
          * Sel hijau pada diagonal utama menandakan prediksi yang benar.
        </p>
      </div>

      <!-- Per-Class Metrics Table (7 cols) -->
      <div class="lg:col-span-7 bg-slate-950/60 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <h2 class="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
          <span>📈</span> Rincian Metrik Per-Kelas
        </h2>

        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="border-b border-slate-800 text-slate-400">
                <th class="p-2.5 font-medium">Kelas Rambut</th>
                <th class="p-2.5 font-medium text-center">Jumlah (Support)</th>
                <th class="p-2.5 font-medium text-center">Benar</th>
                <th class="p-2.5 font-medium text-center">Precision</th>
                <th class="p-2.5 font-medium text-center">Recall</th>
                <th class="p-2.5 font-medium text-center">F1-Score</th>
              </tr>
            </thead>
            <tbody id="perClassBody">
              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Tested Images Gallery & Filter Section -->
    <section class="bg-slate-950/60 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <span>🖼️</span> Daftar Citra yang Telah Diuji (<span id="recordCount">0</span>)
          </h2>
          <p class="text-xs text-slate-400">
            Anda dapat mengubah Ground Truth langsung pada masing-masing kartu gambar untuk mengoreksi anotasi.
          </p>
        </div>

        <!-- Filter Controls -->
        <div class="flex flex-wrap items-center gap-2 text-xs">
          <span class="text-slate-500">Filter:</span>
          <button onclick="setFilter('all')" id="btnFilterAll" class="px-2.5 py-1 rounded-md bg-indigo-600 text-white font-medium">
            Semua
          </button>
          <button onclick="setFilter('errors')" id="btnFilterErrors" class="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-rose-300 border border-rose-900/40">
            Salah Prediksi Saja
          </button>
          <button onclick="setFilter('correct')" id="btnFilterCorrect" class="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-900/40">
            Benar Saja
          </button>
          <button onclick="setFilter('unlabeled')" id="btnFilterUnlabeled" class="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-400 border border-slate-700">
            Belum Di-label
          </button>
          <button onclick="toggleRejectedModal()" id="btnRejectedView" class="px-2.5 py-1 rounded-md bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/50 flex items-center gap-1">
            <span>🛡️ Ditolak (Old Split):</span>
            <span class="font-bold text-rose-400" id="rejectedBadgeCount">0</span>
          </button>
        </div>
      </div>

      <!-- Image Cards Grid -->
      <div id="recordsGrid" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <!-- Rendered via JS -->
      </div>

      <div id="emptyNotice" class="text-center py-12 text-slate-500 text-xs">
        Belum ada citra uji. Unggah foto rambut melalui kotak di atas untuk memulai evaluasi!
      </div>
    </section>

  </main>

  <!-- Rejected Records Modal -->
  <div id="rejectedModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-slate-900 border border-rose-800/80 rounded-2xl max-w-2xl w-full p-5 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <div class="flex items-center gap-2">
          <span class="text-xl">🛡️</span>
          <h3 class="text-sm font-semibold text-rose-300">Daftar Citra Ditolak (Old Split Leakage Prevention)</h3>
        </div>
        <button onclick="toggleRejectedModal()" class="text-slate-400 hover:text-white text-base">✕</button>
      </div>

      <p class="text-xs text-slate-300">
        Foto di bawah ini <strong>otomatis ditolak</strong> karena identik dengan citra dataset split lama (train/val/test). Foto-foto ini <strong>tidak dimasukkan</strong> ke perhitungan skor akurasi data baru.
      </p>

      <div class="overflow-y-auto space-y-2 flex-1 pr-1" id="rejectedList">
        <!-- Rendered via JS -->
      </div>

      <div class="pt-3 border-t border-slate-800 flex justify-end">
        <button onclick="toggleRejectedModal()" class="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-200">
          Tutup
        </button>
      </div>
    </div>
  </div>

  <!-- Notification Toast -->
  <div id="toast" class="fixed bottom-5 right-5 px-4 py-2.5 rounded-lg bg-indigo-600 text-white text-xs shadow-xl transition-all opacity-0 pointer-events-none z-50">
    Pesan toast
  </div>

  <script>
    let currentFilter = 'all';
    let allRecords = [];
    let rejectedRecords = [];
    let currentMetrics = null;

    function showToast(msg, isError = false) {
      const el = document.getElementById('toast');
      el.textContent = msg;
      el.className = `fixed bottom-5 right-5 px-4 py-2.5 rounded-lg text-white text-xs shadow-xl transition-all z-50 ${isError ? 'bg-rose-600' : 'bg-indigo-600'}`;
      el.classList.remove('opacity-0', 'pointer-events-none');
      setTimeout(() => el.classList.add('opacity-0', 'pointer-events-none'), 3500);
    }

    async function loadStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        allRecords = data.records || [];
        rejectedRecords = data.rejected_records || [];
        currentMetrics = data.metrics;
        if (data.known_images_count) {
          document.getElementById('knownImagesCount').textContent = `${data.known_images_count} citra`;
          document.getElementById('antiLeakageBadge').textContent = `${data.known_images_count} Citra Terproteksi`;
        }
        renderAll();
      } catch (err) {
        console.error('Failed to load status', err);
      }
    }

    function renderAll() {
      renderMetrics();
      renderConfusionMatrix();
      renderPerClassTable();
      renderRecordsGrid();
      renderRejectedInfo();
    }

    function toggleRejectedModal() {
      const modal = document.getElementById('rejectedModal');
      modal.classList.toggle('hidden');
    }

    function renderRejectedInfo() {
      const countEl = document.getElementById('rejectedBadgeCount');
      if (countEl) countEl.textContent = rejectedRecords.length;

      const listEl = document.getElementById('rejectedList');
      if (!listEl) return;
      listEl.innerHTML = '';

      if (rejectedRecords.length === 0) {
        listEl.innerHTML = '<div class=\"text-center py-6 text-slate-500 text-xs\">Belum ada citra yang ditolak. Seluruh unggahan berstatus data baru.</div>';
        return;
      }

      rejectedRecords.forEach(rej => {
        const row = document.createElement('div');
        row.className = 'p-3 rounded-lg bg-rose-950/40 border border-rose-800/40 text-xs flex flex-col gap-1';
        row.innerHTML = `
          <div class=\"flex items-center justify-between font-medium text-rose-300\">
            <span class=\"truncate max-w-[320px]\">${rej.filename}</span>
            <span class=\"px-2 py-0.5 rounded bg-rose-900/60 text-[10px] font-mono uppercase text-rose-200 border border-rose-700/50\">
              ${rej.split || 'OLD SPLIT'}
            </span>
          </div>
          <div class=\"text-[11px] text-slate-400\">
            Cocok dengan citra lama: <code class=\"text-rose-200 font-mono\">${rej.name || '-'}</code> (Kelas: ${rej.label || '-'}, Tipe: ${rej.match_type || 'hash'})
          </div>
          <div class=\"text-[10px] text-slate-500 font-mono\">Ditolak pada: ${rej.rejected_at || '-'}</div>
        `;
        listEl.appendChild(row);
      });
    }

    function renderMetrics() {
      if (!currentMetrics) return;
      const m = currentMetrics;
      document.getElementById('metricAcc').textContent = m.accuracy_percent.toFixed(1) + '%';
      document.getElementById('metricCorrectRatio').textContent = `${m.correct_count} / ${m.evaluated_count} citra`;
      document.getElementById('metricMacroF1').textContent = m.macro_f1.toFixed(4);
      document.getElementById('metricMacroPrec').textContent = m.macro_precision.toFixed(4);
      document.getElementById('metricMacroRec').textContent = m.macro_recall.toFixed(4);
      document.getElementById('metricErrors').textContent = m.misclassified_count;
      document.getElementById('metricErrorNote').textContent = `${m.misclassified_count} error dari ${m.evaluated_count}`;
      document.getElementById('metricLatency').textContent = m.avg_latency_ms.toFixed(1) + ' ms';
      document.getElementById('recordCount').textContent = allRecords.length;
    }

    function renderConfusionMatrix() {
      const tbody = document.getElementById('cmBody');
      tbody.innerHTML = '';
      if (!currentMetrics || !currentMetrics.confusion_matrix) return;

      const cm = currentMetrics.confusion_matrix;
      const classes = ['lurus', 'bergelombang', 'keriting'];

      classes.forEach(trueCls => {
        const tr = document.createElement('tr');
        tr.className = 'border-b border-slate-800/60 hover:bg-slate-900/50';

        let rowHtml = `<td class="p-2 text-left font-medium text-slate-300 capitalize">${trueCls}</td>`;
        classes.forEach(predCls => {
          const count = cm[trueCls][predCls] || 0;
          const isDiagonal = trueCls === predCls;
          const cellColor = isDiagonal
            ? (count > 0 ? 'bg-emerald-950/70 text-emerald-300 font-bold border border-emerald-800/40' : 'text-slate-500')
            : (count > 0 ? 'bg-rose-950/70 text-rose-300 font-bold border border-rose-800/40' : 'text-slate-600');

          rowHtml += `<td class="p-2"><span class="inline-block min-w-[28px] py-1 px-1.5 rounded ${cellColor}">${count}</span></td>`;
        });

        tr.innerHTML = rowHtml;
        tbody.appendChild(tr);
      });
    }

    function renderPerClassTable() {
      const tbody = document.getElementById('perClassBody');
      tbody.innerHTML = '';
      if (!currentMetrics || !currentMetrics.per_class) return;

      const pc = currentMetrics.per_class;
      const classes = ['lurus', 'bergelombang', 'keriting'];

      classes.forEach(cls => {
        const item = pc[cls] || { support: 0, correct: 0, precision: 0, recall: 0, f1: 0 };
        const tr = document.createElement('tr');
        tr.className = 'border-b border-slate-800/60 hover:bg-slate-900/50';
        tr.innerHTML = `
          <td class="p-2.5 font-medium capitalize text-slate-200">${cls}</td>
          <td class="p-2.5 text-center text-slate-300">${item.support}</td>
          <td class="p-2.5 text-center text-emerald-400 font-semibold">${item.correct}</td>
          <td class="p-2.5 text-center text-sky-300">${item.precision.toFixed(4)}</td>
          <td class="p-2.5 text-center text-amber-300">${item.recall.toFixed(4)}</td>
          <td class="p-2.5 text-center text-indigo-300 font-bold">${item.f1.toFixed(4)}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    function setFilter(filterType) {
      currentFilter = filterType;
      ['All', 'Errors', 'Correct', 'Unlabeled'].forEach(f => {
        const btn = document.getElementById('btnFilter' + f);
        if (f.toLowerCase() === filterType) {
          btn.className = 'px-2.5 py-1 rounded-md bg-indigo-600 text-white font-medium';
        } else {
          btn.className = 'px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700';
        }
      });
      renderRecordsGrid();
    }

    function renderRecordsGrid() {
      const grid = document.getElementById('recordsGrid');
      const empty = document.getElementById('emptyNotice');
      grid.innerHTML = '';

      let filtered = allRecords;
      if (currentFilter === 'errors') {
        filtered = allRecords.filter(r => r.true_label && r.is_correct === false);
      } else if (currentFilter === 'correct') {
        filtered = allRecords.filter(r => r.true_label && r.is_correct === true);
      } else if (currentFilter === 'unlabeled') {
        filtered = allRecords.filter(r => !r.true_label);
      }

      if (filtered.length === 0) {
        empty.classList.remove('hidden');
        return;
      }
      empty.classList.add('hidden');

      filtered.forEach(r => {
        const card = document.createElement('div');
        const isEval = r.true_label != null;
        const isMatch = r.is_correct === true;

        const borderStyle = !isEval
          ? 'border-slate-800'
          : (isMatch ? 'border-emerald-600/50 bg-emerald-950/10' : 'border-rose-600/60 bg-rose-950/15');

        card.className = `rounded-xl border ${borderStyle} p-3 bg-slate-900/60 flex flex-col justify-between shadow-md relative group`;

        // Probs breakdown bar
        const probs = r.probabilities || {};
        const pLurus = Math.round((probs.lurus || 0) * 100);
        const pGelombang = Math.round((probs.bergelombang || 0) * 100);
        const pKeriting = Math.round((probs.keriting || 0) * 100);

        card.innerHTML = `
          <div>
            <div class="relative w-full h-44 rounded-lg overflow-hidden bg-slate-950 mb-2">
              <img src="${r.thumb_b64 || ''}" alt="${r.filename}" class="w-full h-full object-contain">
              <div class="absolute top-1.5 right-1.5">
                <button onclick="deleteRecord('${r.id}')" title="Hapus foto ini" class="w-6 h-6 rounded-full bg-rose-950/80 hover:bg-rose-900 text-rose-300 text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
                  ✕
                </button>
              </div>
              <div class="absolute bottom-1 left-1 bg-slate-950/80 text-[10px] text-slate-400 px-1.5 py-0.5 rounded font-mono">
                ${r.width || 0}x${r.height || 0}
              </div>
            </div>

            <div class="flex items-center justify-between text-xs mb-1">
              <span class="font-medium text-slate-300 truncate max-w-[170px]" title="${r.filename}">
                ${r.filename}
              </span>
              <span class="text-[10px] text-slate-500 font-mono">${r.latency_ms}ms</span>
            </div>

            <!-- Predicted label -->
            <div class="flex items-center justify-between text-xs my-1">
              <span class="text-slate-400 text-[11px]">Prediksi:</span>
              <span class="font-semibold px-2 py-0.5 rounded text-[11px] ${getLabelColor(r.pred_label)}">
                ${r.pred_label} (${(r.confidence * 100).toFixed(1)}%)
              </span>
            </div>

            <!-- Ground Truth selector -->
            <div class="flex items-center justify-between text-xs mt-2 pt-2 border-t border-slate-800">
              <span class="text-slate-400 text-[11px]">Ground Truth:</span>
              <select onchange="updateGroundTruth('${r.id}', this.value)" class="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded px-1.5 py-0.5 focus:border-indigo-500 focus:outline-none">
                <option value="" ${!r.true_label ? 'selected' : ''}>-- Belum --</option>
                <option value="lurus" ${r.true_label === 'lurus' ? 'selected' : ''}>Lurus</option>
                <option value="bergelombang" ${r.true_label === 'bergelombang' ? 'selected' : ''}>Bergelombang</option>
                <option value="keriting" ${r.true_label === 'keriting' ? 'selected' : ''}>Keriting</option>
              </select>
            </div>

            <!-- Probabilities Bars -->
            <div class="mt-2.5 pt-2 border-t border-slate-800 text-[10px] space-y-1 text-slate-400">
              <div class="flex justify-between"><span>Lurus:</span> <span class="font-mono text-emerald-300">${pLurus}%</span></div>
              <div class="w-full bg-slate-950 h-1 rounded overflow-hidden"><div class="bg-emerald-500 h-full" style="width: ${pLurus}%"></div></div>

              <div class="flex justify-between mt-1"><span>Bergelombang:</span> <span class="font-mono text-amber-300">${pGelombang}%</span></div>
              <div class="w-full bg-slate-950 h-1 rounded overflow-hidden"><div class="bg-amber-500 h-full" style="width: ${pGelombang}%"></div></div>

              <div class="flex justify-between mt-1"><span>Keriting:</span> <span class="font-mono text-purple-300">${pKeriting}%</span></div>
              <div class="w-full bg-slate-950 h-1 rounded overflow-hidden"><div class="bg-purple-500 h-full" style="width: ${pKeriting}%"></div></div>
            </div>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function getLabelColor(label) {
      if (label === 'lurus') return 'bg-emerald-950 text-emerald-300 border border-emerald-800/60';
      if (label === 'bergelombang') return 'bg-amber-950 text-amber-300 border border-amber-800/60';
      if (label === 'keriting') return 'bg-purple-950 text-purple-300 border border-purple-800/60';
      return 'bg-slate-800 text-slate-400';
    }

    async function updateGroundTruth(id, newLabel) {
      try {
        const res = await fetch('/api/update-label', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: jsonWrap({ id, true_label: newLabel || null })
        });
        const data = await res.json();
        if (data.status === 'ok') {
          currentMetrics = data.metrics;
          const rec = allRecords.find(r => r.id === id);
          if (rec) {
            rec.true_label = newLabel || null;
            rec.is_correct = newLabel ? (rec.pred_label === newLabel) : null;
          }
          renderAll();
          showToast('Ground truth berhasil diperbarui!');
        }
      } catch (e) {
        showToast('Gagal update ground truth');
      }
    }

    async function deleteRecord(id) {
      try {
        const res = await fetch('/api/delete-item', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: jsonWrap({ id })
        });
        const data = await res.json();
        if (data.status === 'ok') {
          allRecords = allRecords.filter(r => r.id !== id);
          currentMetrics = data.metrics;
          renderAll();
          showToast('Foto berhasil dihapus');
        }
      } catch (e) {
        showToast('Gagal menghapus');
      }
    }

    async function clearAllRecords() {
      if (!confirm('Apakah Anda yakin ingin menghapus seluruh data uji pada sesi ini?')) return;
      try {
        const res = await fetch('/api/clear-all', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
          allRecords = [];
          currentMetrics = data.metrics;
          renderAll();
          showToast('Seluruh data uji berhasil di-reset');
        }
      } catch (e) {
        showToast('Gagal me-reset data');
      }
    }

    function jsonWrap(obj) { return JSON.stringify(obj); }

    // Upload & Dropzone Handling
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    dropZone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(name => {
      dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    });
    ['dragleave', 'drop'].forEach(name => {
      dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); });
    });

    dropZone.addEventListener('drop', (e) => {
      const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
      if (files.length > 0) handleFiles(files);
    });

    fileInput.addEventListener('change', () => {
      const files = Array.from(fileInput.files);
      if (files.length > 0) handleFiles(files);
      fileInput.value = '';
    });

    async function handleFiles(files) {
      const batchGt = document.querySelector('input[name="batchGt"]:checked')?.value || null;
      const progressBox = document.getElementById('uploadProgress');
      const progressCount = document.getElementById('progressCount');
      progressBox.classList.remove('hidden');

      let done = 0;
      let acceptedCount = 0;
      let rejectedCount = 0;
      progressCount.textContent = `${done}/${files.length}`;

      for (const file of files) {
        try {
          const b64 = await readFileAsBase64(file);
          const res = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: jsonWrap({
              filename: file.name,
              image_b64: b64,
              true_label: batchGt
            })
          });
          const data = await res.json();
          if (data.status === 'ok') {
            allRecords.unshift(data.record);
            currentMetrics = data.metrics;
            acceptedCount++;
          } else if (data.status === 'rejected') {
            rejectedCount++;
            rejectedRecords.unshift({
              filename: file.name,
              split: data.match?.split || 'old_split',
              name: data.match?.name || '-',
              label: data.match?.label || '-',
              match_type: data.match?.type || 'hash',
              rejected_at: new Date().toLocaleTimeString(),
            });
            showToast(`🛡️ ${file.name} DITOLAK: Citra dataset split lama (${data.match?.name})`, true);
          }
        } catch (err) {
          console.error('Error uploading file:', file.name, err);
        }
        done++;
        progressCount.textContent = `${done}/${files.length}`;
      }

      progressBox.classList.add('hidden');
      renderAll();
      if (rejectedCount > 0 && acceptedCount > 0) {
        showToast(`${acceptedCount} citra diproses, ${rejectedCount} citra ditolak (data lama).`);
      } else if (rejectedCount > 0 && acceptedCount === 0) {
        showToast(`Seluruh ${rejectedCount} citra DITOLAK karena terdeteksi data split lama!`, true);
      } else {
        showToast(`${acceptedCount} citra baru berhasil diproses!`);
      }
    }

    function readFileAsBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    }

    // Initialize
    loadStatus();
  </script>
</body>
</html>
"""


def run_evaluator_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, model_path: Optional[Path] = None):
    if model_path:
        SESSION_STORE["model_path"] = str(model_path)

    # Initialize ONNX model immediately at startup
    print(f"Menyiapkan model 3-kelas: {SESSION_STORE['model_path']}")
    get_classifier(Path(SESSION_STORE["model_path"]))
    load_known_manifest_hashes()
    load_session_from_disk()

    server = ThreadingHTTPServer((host, port), EvaluatorHandler)
    url = f"http://{host}:{port}"
    print("=" * 70)
    print("🌐 WEB EVALUATOR AKURASI MODEL 3-KELAS (DATA BARU NON-SPLIT) SIAP!")
    print(f"👉 Buka browser di: {url}")
    print("Fitur:")
    print(" - Pengujian foto baru (upload single atau batch drag-and-drop)")
    print(" - Penentuan Ground Truth otomatis atau manual per citra")
    print(" - Penghitungan Akurasi, Macro-F1, Confusion Matrix 3x3, dan Latensi secara live")
    print(" - Export laporan hasil pengujian ke format CSV dan JSON")
    print("=" * 70)
    print("Tekan Ctrl+C untuk menghentikan server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMenghentikan evaluator server...")
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port (default: 8790)")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH, help="Path to 3-class ONNX model")
    args = parser.parse_args()

    run_evaluator_server(host=args.host, port=args.port, model_path=args.model)


if __name__ == "__main__":
    main()
