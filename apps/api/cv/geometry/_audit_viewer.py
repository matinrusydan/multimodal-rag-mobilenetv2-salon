"""Temporary Web-Based CV Inference & Geometry Audit Viewer.

This is a standalone, self-contained inspection tool for visually auditing
real inference results, segmentation masks, and geometric keypoints across
the 59 locked test split images and arbitrary custom uploaded photos.

Designed for TEMPORARY use and safe single-command deletion afterward:
    Remove-Item apps/api/cv/geometry/_audit_viewer.py
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from classify_hierarchical import HierarchicalHairPipeline
from hair_type_model import HAIR_TYPE_CLASSES
from measure_length import HAIR_LENGTH_CLASSES
from measure_volume import HAIR_VOLUME_CLASSES

DEFAULT_PORT = 8787
DEFAULT_HOST = "127.0.0.1"
MANIFEST_PATH = HERE / "reports" / "phase1" / "curated_manifest.json"
DATASET_DIR = HERE.parent / "dataset"

# Global application cache
APP_STATE: Dict[str, Any] = {
    "pipeline": None,
    "records": [],
    "records_by_id": {},
    "masks": {},
    "summary": {},
}


def render_annotated_overlay(img_bgr: np.ndarray, mask: np.ndarray, res: dict) -> np.ndarray:
    """Render translucent mask, contour outline, and geometric lines onto the image."""
    overlay = img_bgr.copy()
    h, w = img_bgr.shape[:2]

    # 1. Hair mask cyan/emerald tint
    mask_bool = mask > 0
    if mask_bool.any():
        tint = np.zeros_like(img_bgr)
        tint[:, :] = [210, 170, 30]  # BGR
        overlay[mask_bool] = cv2.addWeighted(img_bgr[mask_bool], 0.65, tint[mask_bool], 0.35, 0)

        # 2. Crisp contour outline
        contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Geometric keypoint annotations
    length_attr = res.get("stage2_conditional_attributes", {}).get("length", {})
    if length_attr.get("status") == "ok":
        kp = length_attr.get("keypoints", {})
        y_top = int(kp.get("y_head_top", 0))
        y_end = int(kp.get("y_hair_end", 0))
        y_sh = int(kp.get("y_shoulder", 0))
        w_cran = kp.get("cranial_width", 0)
        h_head = kp.get("head_height_estimate", 0)
        method = length_attr.get("method", "est")
        pred_len = length_attr.get("predicted_class", "")
        u_head = length_attr.get("head_units", 0)
        r_sh = length_attr.get("relative_shoulder_ratio", 0)

        # Vertex line (cyan)
        if 0 <= y_top < h:
            cv2.line(overlay, (15, y_top), (w - 15, y_top), (255, 230, 0), 2)
            cv2.putText(
                overlay,
                f"Vertex (y={y_top})",
                (20, max(22, y_top - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (255, 230, 0),
                2,
                cv2.LINE_AA,
            )

        # Shoulder line (amber / gold)
        if 0 <= y_sh < h:
            # Draw line with method badge
            cv2.line(overlay, (15, y_sh), (w - 15, y_sh), (0, 215, 255), 2)
            cv2.putText(
                overlay,
                f"Bahu ({method}): y={y_sh}",
                (20, max(22, y_sh - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (0, 215, 255),
                2,
                cv2.LINE_AA,
            )

        # Hair end line (coral / red)
        if 0 <= y_end < h:
            cv2.line(overlay, (15, y_end), (w - 15, y_end), (0, 80, 255), 2)
            cv2.putText(
                overlay,
                f"Ujung Rambut [{pred_len}]: y={y_end} (Uhead={u_head:.2f}, Rsh={r_sh:.2f})",
                (20, min(h - 10, y_end + 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (0, 80, 255),
                2,
                cv2.LINE_AA,
            )

    return overlay


def encode_jpeg(img_bgr: np.ndarray, quality: int = 85) -> bytes:
    """Encode OpenCV BGR image to JPEG bytes."""
    success, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not success:
        raise RuntimeError("Failed to encode image to JPEG")
    return buf.tobytes()


def precompute_test_records() -> None:
    """Precompute inference results across the 59 test images."""
    print("Memuat pipeline EfficientNetV2-S + UNet...")
    pipeline = HierarchicalHairPipeline()
    APP_STATE["pipeline"] = pipeline

    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    test_recs = [r for r in manifest["records"] if r["split"] == "test"]
    print(f"Ditemukan {len(test_recs)} citra locked test split. Memulai pra-komputasi inferensi...")

    t0 = time.perf_counter()
    processed_records = []
    correct_count = 0
    per_class_stats: Dict[str, Dict[str, int]] = {
        cls: {"total": 0, "correct": 0} for cls in HAIR_TYPE_CLASSES
    }
    confusion_matrix: Dict[str, Dict[str, int]] = {
        true_cls: {pred_cls: 0 for pred_cls in HAIR_TYPE_CLASSES}
        for true_cls in HAIR_TYPE_CLASSES
    }

    total_latency = 0.0

    for idx, r in enumerate(test_recs, 1):
        image_id = r["image_id"]
        img_path = DATASET_DIR / image_id
        if not img_path.is_file():
            print(f"Warning: File not found: {img_path}")
            continue

        true_label = r["approved_label"]
        res, mask = pipeline.predict_file(img_path)

        pred_cls = res["stage1_hair_type"]["predicted_class"]
        conf = res["stage1_hair_type"]["confidence"]
        is_correct = pred_cls == true_label

        if is_correct:
            correct_count += 1
            per_class_stats[true_label]["correct"] += 1
        per_class_stats[true_label]["total"] += 1
        confusion_matrix[true_label][pred_cls] += 1

        total_latency += res.get("total_latency_ms", 0)

        record_entry = {
            "index": idx,
            "image_id": image_id,
            "filename": Path(image_id).name,
            "cohort": r.get("cohort", "figaro1k"),
            "width": r.get("width", 0),
            "height": r.get("height", 0),
            "true_label": true_label,
            "pred_label": pred_cls,
            "is_correct": is_correct,
            "confidence": conf,
            "probabilities": res["stage1_hair_type"]["probabilities"],
            "stage1_latency_ms": res["stage1_hair_type"]["latency_ms"],
            "stage2_latency_ms": res["stage2_segmentation"]["latency_ms"],
            "total_latency_ms": res.get("total_latency_ms", 0),
            "hair_coverage": res["stage2_segmentation"]["hair_coverage"],
            "tied_hair": res.get("tied_hair_assessment", {}),
            "conditional_attributes": res.get("stage2_conditional_attributes", {}),
            "full_result": res,
        }

        processed_records.append(record_entry)
        APP_STATE["records_by_id"][image_id] = record_entry
        APP_STATE["masks"][image_id] = mask

    total_time = time.perf_counter() - t0
    total_imgs = len(processed_records)
    acc = (correct_count / total_imgs * 100.0) if total_imgs > 0 else 0.0
    avg_latency = (total_latency / total_imgs) if total_imgs > 0 else 0.0

    APP_STATE["records"] = processed_records
    APP_STATE["summary"] = {
        "total_test_images": total_imgs,
        "correct_predictions": correct_count,
        "misclassified_predictions": total_imgs - correct_count,
        "accuracy_percent": round(acc, 2),
        "mean_latency_ms": round(avg_latency, 2),
        "precompute_time_seconds": round(total_time, 2),
        "per_class_stats": per_class_stats,
        "confusion_matrix": confusion_matrix,
    }

    print(
        f"Pra-komputasi selesai dalam {total_time:.2f}s! "
        f"Akurasi: {correct_count}/{total_imgs} ({acc:.2f}%)"
    )


class AuditRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler serving API and single-page audit interface."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress noisy request logs, only log errors or custom events."""
        if getattr(args, "__getitem__", None) and len(args) > 1 and str(args[1]) in ("400", "404", "500"):
            super().log_message(format, *args)

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _send_bytes(self, payload: bytes, content_type: str = "image/jpeg") -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("", "/"):
            # Serve the embedded Single Page Application
            html = HTML_PAGE_TEMPLATE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        if path == "/api/summary":
            self._send_json(APP_STATE["summary"])
            return

        if path == "/api/records":
            # Return all 59 precomputed records (without large mask buffers)
            self._send_json({"records": APP_STATE["records"]})
            return

        if path == "/api/image":
            image_id = query.get("id", [None])[0]
            view_type = query.get("view", ["overlay"])[0]

            if not image_id or image_id not in APP_STATE["records_by_id"]:
                self.send_error(404, f"Image record not found: {image_id}")
                return

            img_path = DATASET_DIR / image_id
            if not img_path.is_file():
                self.send_error(404, f"File not found on disk: {img_path}")
                return

            img_bgr = None
            try:
                with Image.open(img_path) as im:
                    rgb = np.asarray(ImageOps.exif_transpose(im).convert("RGB"))
                    img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            except Exception:
                img_bgr = None

            if img_bgr is None:
                self.send_error(500, "Failed to read image")
                return

            mask = APP_STATE["masks"].get(image_id)
            record = APP_STATE["records_by_id"][image_id]

            if view_type == "orig":
                self._send_bytes(encode_jpeg(img_bgr, 85))
            elif view_type == "mask":
                mask_display = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                self._send_bytes(encode_jpeg(mask_display, 85))
            else:  # 'overlay' default
                overlay = render_annotated_overlay(img_bgr, mask, record["full_result"])
                self._send_bytes(encode_jpeg(overlay, 90))
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload_infer":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0 or content_length > 20 * 1024 * 1024:
                self.send_error(400, "Invalid image payload size (max 20MB)")
                return

            raw_bytes = self.rfile.read(content_length)
            try:
                # Open with PIL to support JPG, PNG, WEBP, etc.
                pil_raw = Image.open(io.BytesIO(raw_bytes))
                pil_img = ImageOps.exif_transpose(pil_raw).convert("RGB")
                pipeline: HierarchicalHairPipeline = APP_STATE["pipeline"]
                res, mask = pipeline.predict_pil(pil_img)

                # Prepare OpenCV BGR
                rgb_array = np.array(pil_img)
                img_bgr = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

                overlay = render_annotated_overlay(img_bgr, mask, res)
                overlay_b64 = base64.b64encode(encode_jpeg(overlay, 88)).decode("ascii")
                mask_b64 = base64.b64encode(encode_jpeg(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), 85)).decode("ascii")
                orig_b64 = base64.b64encode(encode_jpeg(img_bgr, 85)).decode("ascii")

                response_payload = {
                    "success": True,
                    "result": res,
                    "images": {
                        "overlay": f"data:image/jpeg;base64,{overlay_b64}",
                        "mask": f"data:image/jpeg;base64,{mask_b64}",
                        "orig": f"data:image/jpeg;base64,{orig_b64}",
                    },
                }
                self._send_json(response_payload)
            except Exception as exc:
                self._send_json({"success": False, "error": str(exc)}, status=500)
            return

        self.send_error(404, "Not Found")


# Embedded responsive Single Page Application
HTML_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CV Hair Inference & Geometric Audit Viewer</title>
  <style>
    :root {
      --bg: #0f172a;
      --surface: #1e293b;
      --surface-hover: #334155;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --success: #10b981;
      --success-bg: rgba(16, 185, 129, 0.15);
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.15);
      --warning: #f59e0b;
      --warning-bg: rgba(245, 158, 11, 0.15);
      --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.2);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding-bottom: 50px;
    }
    header {
      background: #0b1329;
      border-bottom: 1px solid var(--border);
      padding: 16px 24px;
      position: sticky;
      top: 0;
      z-index: 40;
    }
    .header-content {
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .brand h1 { font-size: 1.25rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px; }
    .brand p { font-size: 0.85rem; color: var(--text-muted); }
    .badge-temp {
      font-size: 0.7rem;
      background: #f59e0b;
      color: #000;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .header-metrics {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .stat-pill {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 6px 14px;
      font-size: 0.85rem;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .stat-pill .val { font-weight: 700; font-size: 1.1rem; color: var(--primary); }
    .stat-pill .lbl { font-size: 0.72rem; color: var(--text-muted); }

    .nav-tabs {
      max-width: 1400px;
      margin: 16px auto 0;
      padding: 0 24px;
      display: flex;
      gap: 10px;
      border-bottom: 1px solid var(--border);
    }
    .tab-btn {
      background: none;
      border: none;
      color: var(--text-muted);
      font-weight: 600;
      padding: 10px 16px;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      font-size: 0.92rem;
      transition: all 0.2s;
    }
    .tab-btn:hover { color: var(--text); }
    .tab-btn.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
    }

    main {
      max-width: 1400px;
      margin: 20px auto;
      padding: 0 24px;
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* Filters Bar */
    .filter-bar {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 18px;
      margin-bottom: 24px;
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: center;
    }
    .filter-group {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .filter-group label {
      font-size: 0.8rem;
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
    }
    .filter-group select, .filter-group input {
      background: #0f172a;
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.85rem;
      outline: none;
    }
    .filter-group select:focus, .filter-group input:focus {
      border-color: var(--primary);
    }
    .filter-count {
      margin-left: auto;
      font-size: 0.85rem;
      color: var(--text-muted);
    }

    /* Grid of Cards */
    .grid-gallery {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 20px;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.15s, border-color 0.15s;
      box-shadow: var(--card-shadow);
      cursor: pointer;
    }
    .card:hover {
      transform: translateY(-3px);
      border-color: var(--primary);
    }
    .card-img-wrap {
      position: relative;
      width: 100%;
      height: 280px;
      background: #020617;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
    .card-img-wrap img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      transition: opacity 0.2s;
    }
    .card-badges-float {
      position: absolute;
      top: 10px;
      left: 10px;
      right: 10px;
      display: flex;
      justify-content: space-between;
      pointer-events: none;
    }
    .badge {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    .badge-correct { background: var(--success); color: #fff; }
    .badge-wrong { background: var(--danger); color: #fff; }
    .badge-neutral { background: rgba(15, 23, 42, 0.85); color: #fff; border: 1px solid #475569; }
    .badge-type { background: #3b82f6; color: #fff; }

    .card-body {
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex: 1;
    }
    .card-title {
      font-size: 0.9rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .card-meta-row {
      font-size: 0.8rem;
      display: flex;
      justify-content: space-between;
      color: var(--text-muted);
    }
    .card-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 4px;
    }
    .chip {
      font-size: 0.72rem;
      background: #0f172a;
      border: 1px solid var(--border);
      padding: 2px 8px;
      border-radius: 4px;
      color: #cbd5e1;
    }
    .card-footer-btn {
      margin-top: auto;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: var(--primary);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 600;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
    }
    .card:hover .card-footer-btn {
      background: var(--primary);
      color: #000;
    }

    /* Modal Inspection */
    .modal-backdrop {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.85);
      z-index: 50;
      padding: 20px;
      overflow-y: auto;
      align-items: center;
      justify-content: center;
    }
    .modal-backdrop.active { display: flex; }
    .modal-container {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      max-width: 1200px;
      width: 100%;
      max-height: 92vh;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .modal-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      background: var(--surface);
      z-index: 2;
    }
    .modal-header h2 { font-size: 1.15rem; font-weight: 700; color: #fff; }
    .modal-close {
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 1.5rem;
      cursor: pointer;
      line-height: 1;
    }
    .modal-close:hover { color: #fff; }
    .modal-body {
      padding: 20px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    @media (max-width: 900px) {
      .modal-body { grid-template-columns: 1fr; }
    }
    .modal-img-col {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .modal-img-view {
      position: relative;
      width: 100%;
      min-height: 400px;
      max-height: 550px;
      background: #020617;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      border: 1px solid var(--border);
    }
    .modal-img-view img {
      max-width: 100%;
      max-height: 550px;
      object-fit: contain;
      transition: opacity 0.15s ease-in-out;
    }
    .modal-img-loader {
      position: absolute;
      font-size: 0.85rem;
      color: var(--text-muted);
      pointer-events: none;
      display: none;
      align-items: center;
      gap: 8px;
    }
    .view-switcher {
      display: flex;
      gap: 8px;
      justify-content: center;
    }
    .view-btn {
      background: #0f172a;
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
    }
    .view-btn.active {
      background: var(--primary);
      color: #000;
      border-color: var(--primary);
    }

    .modal-info-col {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .info-section {
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px 16px;
    }
    .info-section h3 {
      font-size: 0.85rem;
      text-transform: uppercase;
      color: var(--primary);
      margin-bottom: 10px;
      letter-spacing: 0.5px;
      font-weight: 700;
    }
    .prob-bar-row {
      margin-bottom: 8px;
    }
    .prob-bar-label {
      display: flex;
      justify-content: space-between;
      font-size: 0.82rem;
      margin-bottom: 3px;
    }
    .prob-bar-bg {
      height: 8px;
      background: #1e293b;
      border-radius: 4px;
      overflow: hidden;
    }
    .prob-bar-fill {
      height: 100%;
      background: var(--primary);
      border-radius: 4px;
    }
    .data-table {
      width: 100%;
      font-size: 0.82rem;
      border-collapse: collapse;
    }
    .data-table td {
      padding: 5px 0;
      border-bottom: 1px solid rgba(51, 65, 85, 0.4);
    }
    .data-table td:first-child { color: var(--text-muted); width: 45%; }
    .data-table td:last-child { font-weight: 600; color: #fff; text-align: right; }

    /* Custom Upload Tab */
    .upload-container {
      background: var(--surface);
      border: 2px dashed var(--border);
      border-radius: 14px;
      padding: 40px 20px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      margin-bottom: 24px;
    }
    .upload-container:hover, .upload-container.dragover {
      border-color: var(--primary);
      background: rgba(56, 189, 248, 0.05);
    }
    .upload-icon { font-size: 3rem; margin-bottom: 12px; }
    .upload-btn {
      background: var(--primary);
      color: #000;
      border: none;
      padding: 10px 20px;
      border-radius: 6px;
      font-weight: 700;
      cursor: pointer;
      margin-top: 12px;
      display: inline-block;
    }

    /* Confusion Matrix Table */
    .cm-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
      font-size: 0.85rem;
    }
    .cm-table th, .cm-table td {
      border: 1px solid var(--border);
      padding: 10px 12px;
      text-align: center;
    }
    .cm-table th { background: #0f172a; color: var(--text-muted); font-weight: 600; }
    .cm-cell-diag { background: rgba(16, 185, 129, 0.2); font-weight: 700; color: var(--success); }
    .cm-cell-err { background: rgba(239, 68, 68, 0.2); font-weight: 700; color: var(--danger); }
  </style>
</head>
<body>

  <header>
    <div class="header-content">
      <div class="brand">
        <h1>
          🔍 Hair CV & Geometry Audit Viewer
          <span class="badge-temp">Audit Sementara</span>
        </h1>
        <p>Inspeksi inferensi nyata pada 59 citra locked test split & live upload</p>
      </div>
      <div class="header-metrics" id="headerMetrics">
        <!-- Injected via JS -->
      </div>
    </div>
  </header>

  <nav class="nav-tabs">
    <button class="tab-btn active" onclick="switchTab('gallery')">📁 Dataset Test Split (59 Citra)</button>
    <button class="tab-btn" onclick="switchTab('analysis')">📊 Analisis & Matriks Kebingungan</button>
    <button class="tab-btn" onclick="switchTab('upload')">⚡ Uji Foto Mandiri (Live Inference)</button>
  </nav>

  <main>
    <!-- TAB 1: Gallery -->
    <div id="tab-gallery" class="tab-content active">
      <div class="filter-bar">
        <div class="filter-group">
          <label>True Label:</label>
          <select id="filterTrueLabel" onchange="applyFilters()">
            <option value="all">Semua Tipe</option>
            <option value="lurus">Lurus</option>
            <option value="bergelombang">Bergelombang</option>
            <option value="keriting">Keriting</option>
            <option value="sangat-keriting">Sangat-Keriting</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Status Akurasi:</label>
          <select id="filterStatus" onchange="applyFilters()">
            <option value="all">Semua Hasil</option>
            <option value="correct">Hanya Benar (✓)</option>
            <option value="wrong">Hanya Salah (✗ Misklasifikasi)</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Panjang Geometris:</label>
          <select id="filterLength" onchange="applyFilters()">
            <option value="all">Semua Panjang</option>
            <option value="pendek">Pendek</option>
            <option value="pendek-menengah">Pendek-Menengah</option>
            <option value="menengah">Menengah</option>
            <option value="panjang">Panjang</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Gaya Ikatan:</label>
          <select id="filterTied" onchange="applyFilters()">
            <option value="all">Semua Gaya</option>
            <option value="loose">Terurai (Loose)</option>
            <option value="ponytail">Kuncir (Ponytail)</option>
            <option value="bun">Cepol (Bun)</option>
          </select>
        </div>
        <div class="filter-group">
          <label>Cari:</label>
          <input type="text" id="filterSearch" placeholder="00017.jpg..." oninput="applyFilters()">
        </div>
        <div class="filter-count" id="filterCount">Menampilkan 59 dari 59 citra</div>
      </div>

      <div class="grid-gallery" id="galleryGrid">
        <!-- Card elements injected via JS -->
      </div>
    </div>

    <!-- TAB 2: Analysis -->
    <div id="tab-analysis" class="tab-content">
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 24px;">
        <div class="info-section">
          <h3>Ringkasan Performa Tahap 1 (Hair Type)</h3>
          <table class="data-table">
            <tr><td>Total Citra Test</td><td id="statTotal">59</td></tr>
            <tr><td>Akurasi Global</td><td id="statAcc">88.14% (52/59)</td></tr>
            <tr><td>Misklasifikasi</td><td id="statMis">7 citra</td></tr>
            <tr><td>Rata-rata Latensi Inferensi</td><td id="statLatency">~120 ms / citra</td></tr>
          </table>
        </div>
        <div class="info-section">
          <h3>Statistik Per Kelas</h3>
          <table class="data-table" id="perClassTable">
            <!-- Injected via JS -->
          </table>
        </div>
      </div>

      <div class="info-section" style="margin-bottom: 24px;">
        <h3>Matriks Kebingungan (Confusion Matrix) Test Split</h3>
        <table class="cm-table" id="cmTable">
          <!-- Injected via JS -->
        </table>
      </div>

      <div class="info-section">
        <h3>Daftar 7 Kasus Misklasifikasi untuk Audit Manual</h3>
        <div id="misclassifiedList" style="margin-top: 10px; display: flex; flex-direction: column; gap: 8px;">
          <!-- Injected via JS -->
        </div>
      </div>
    </div>

    <!-- TAB 3: Live Upload -->
    <div id="tab-upload" class="tab-content">
      <input type="file" id="fileInput" accept="image/*" style="display: none;" onchange="handleFileSelect(event)">
      <div class="upload-container" id="dropZone" onclick="document.getElementById('fileInput').click()">
        <div class="upload-icon">📷</div>
        <h2>Unggah Foto Rambut untuk Uji Nyata</h2>
        <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 6px;">
          Pilih file foto dari komputer Anda untuk menjalankan pipeline EfficientNetV2-S + UNet + Geometri secara instan
        </p>
        <button class="upload-btn" type="button">Pilih Berkas Citra</button>
      </div>

      <div id="uploadResult" style="display: none;">
        <!-- Injected upon successful inference -->
      </div>
    </div>
  </main>

  <!-- MODAL INSPECT -->
  <div class="modal-backdrop" id="modalBackdrop" onclick="if(event.target === this) closeModal()">
    <div class="modal-container">
      <div class="modal-header">
        <h2 id="modalTitle">Inspeksi Visual Citra</h2>
        <button class="modal-close" onclick="closeModal()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="modal-img-col">
          <div class="view-switcher">
            <button class="view-btn active" id="btnViewOverlay" onclick="switchModalView('overlay')">Annotated Overlay</button>
            <button class="view-btn" id="btnViewOrig" onclick="switchModalView('orig')">Foto Asli</button>
            <button class="view-btn" id="btnViewMask" onclick="switchModalView('mask')">Binary Mask</button>
          </div>
          <div class="modal-img-view">
            <div class="modal-img-loader" id="modalImgLoader">Memuat citra...</div>
            <img id="modalImg" src="" alt="Citra Inspeksi">
          </div>
          <div style="font-size: 0.78rem; color: var(--text-muted); text-align: center;">
            Kuning: Garis Bahu (y<sub>shoulder</sub>) &bull; Cyan: Puncak Kepala (y<sub>top</sub>) &bull; Merah: Ujung Rambut (y<sub>end</sub>)
          </div>
        </div>
        <div class="modal-info-col" id="modalInfoCol">
          <!-- Injected via JS -->
        </div>
      </div>
    </div>
  </div>

  <script>
    const PAGE_LOAD_TIME = Date.now();
    let ALL_RECORDS = [];
    let CURRENT_RECORD = null;
    let CURRENT_MODAL_VIEW = 'overlay';

    async function initApp() {
      try {
        const [sumRes, recRes] = await Promise.all([
          fetch('/api/summary'),
          fetch('/api/records')
        ]);
        const summary = await sumRes.json();
        const recordsData = await recRes.json();
        ALL_RECORDS = recordsData.records;

        renderHeaderMetrics(summary);
        renderGallery(ALL_RECORDS);
        renderAnalysis(summary, ALL_RECORDS);
      } catch (err) {
        console.error("Gagal menginisialisasi:", err);
      }
    }

    function renderHeaderMetrics(s) {
      const container = document.getElementById('headerMetrics');
      container.innerHTML = `
        <div class="stat-pill"><span class="val">${s.total_test_images}</span><span class="lbl">Total Citra</span></div>
        <div class="stat-pill"><span class="val" style="color: var(--success);">${s.accuracy_percent}%</span><span class="lbl">Akurasi (${s.correct_predictions}/${s.total_test_images})</span></div>
        <div class="stat-pill"><span class="val" style="color: var(--danger);">${s.misclassified_predictions}</span><span class="lbl">Misklasifikasi</span></div>
        <div class="stat-pill"><span class="val">${s.mean_latency_ms} ms</span><span class="lbl">Latensi Rata-rata</span></div>
      `;
    }

    function renderGallery(records) {
      const grid = document.getElementById('galleryGrid');
      grid.innerHTML = '';

      records.forEach(r => {
        const isOk = r.is_correct;
        const card = document.createElement('div');
        card.className = 'card';
        card.onclick = () => openModal(r);

        const lenAttr = r.conditional_attributes?.length || {};
        const lenText = lenAttr.status === 'ok' ? `${lenAttr.predicted_class} (U=${lenAttr.head_units})` : '-';
        const tiedAttr = r.tied_hair || {};
        const tiedText = tiedAttr.style ? tiedAttr.style : 'loose';

        card.innerHTML = `
          <div class="card-img-wrap">
            <img src="/api/image?id=${encodeURIComponent(r.image_id)}&view=overlay&t=${PAGE_LOAD_TIME}" loading="lazy" alt="${r.filename}">
            <div class="card-badges-float">
              <span class="badge ${isOk ? 'badge-correct' : 'badge-wrong'}">${isOk ? '✓ Benar' : '✗ Salah'}</span>
              <span class="badge badge-neutral">${(r.confidence * 100).toFixed(1)}%</span>
            </div>
          </div>
          <div class="card-body">
            <div class="card-title">
              <span>${r.filename}</span>
              <span class="badge badge-type">${r.pred_label}</span>
            </div>
            <div class="card-meta-row">
              <span>Ground Truth:</span>
              <strong style="color: ${isOk ? 'var(--success)' : 'var(--danger)'};">${r.true_label}</strong>
            </div>
            <div class="card-chips">
              <span class="chip">📏 ${lenText}</span>
              <span class="chip">🎀 ${tiedText}</span>
              <span class="chip">⏱ ${r.total_latency_ms}ms</span>
            </div>
            <div class="card-footer-btn">Inspeksi Visual & Metrik ➔</div>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function applyFilters() {
      const trueVal = document.getElementById('filterTrueLabel').value;
      const statusVal = document.getElementById('filterStatus').value;
      const lenVal = document.getElementById('filterLength').value;
      const tiedVal = document.getElementById('filterTied').value;
      const searchVal = document.getElementById('filterSearch').value.toLowerCase().trim();

      const filtered = ALL_RECORDS.filter(r => {
        if (trueVal !== 'all' && r.true_label !== trueVal) return false;
        if (statusVal === 'correct' && !r.is_correct) return false;
        if (statusVal === 'wrong' && r.is_correct) return false;

        const lenClass = r.conditional_attributes?.length?.predicted_class;
        if (lenVal !== 'all' && lenClass !== lenVal) return false;

        const tiedStyle = r.tied_hair?.style || 'loose';
        if (tiedVal !== 'all' && tiedStyle !== tiedVal) return false;

        if (searchVal && !r.image_id.toLowerCase().includes(searchVal)) return false;
        return true;
      });

      document.getElementById('filterCount').innerText = `Menampilkan ${filtered.length} dari ${ALL_RECORDS.length} citra`;
      renderGallery(filtered);
    }

    function openModal(r) {
      CURRENT_RECORD = r;
      CURRENT_MODAL_VIEW = 'overlay';
      ['btnViewOverlay', 'btnViewOrig', 'btnViewMask'].forEach(id => {
        document.getElementById(id).classList.remove('active');
      });
      document.getElementById('btnViewOverlay').classList.add('active');

      document.getElementById('modalTitle').innerText = `${r.image_id} — Detail Audit`;

      const img = document.getElementById('modalImg');
      const loader = document.getElementById('modalImgLoader');
      if (img) {
        img.style.opacity = '0';
        img.src = '';
      }
      if (loader) loader.style.display = 'flex';

      updateModalImage();

      const isOk = r.is_correct;
      const probs = r.probabilities || {};
      const lenAttr = r.conditional_attributes?.length || {};
      const volAttr = r.conditional_attributes?.volume || {};
      const tied = r.tied_hair || {};
      const kp = lenAttr.keypoints || {};

      let probBarsHtml = '';
      for (const [clsName, pVal] of Object.entries(probs)) {
        const pct = (pVal * 100).toFixed(1);
        const isPred = clsName === r.pred_label;
        probBarsHtml += `
          <div class="prob-bar-row">
            <div class="prob-bar-label">
              <span style="${isPred ? 'font-weight: 700; color: var(--primary);' : ''}">${clsName} ${isPred ? '★' : ''}</span>
              <span>${pct}%</span>
            </div>
            <div class="prob-bar-bg">
              <div class="prob-bar-fill" style="width: ${pct}%; background: ${isPred ? 'var(--primary)' : '#475569'};"></div>
            </div>
          </div>
        `;
      }

      const infoCol = document.getElementById('modalInfoCol');
      infoCol.innerHTML = `
        <div class="info-section">
          <h3>Klasifikasi Tahap 1: Jenis Rambut</h3>
          <table class="data-table">
            <tr><td>True Label (Ground Truth)</td><td style="color: ${isOk ? 'var(--success)' : 'var(--danger)'};">${r.true_label}</td></tr>
            <tr><td>Prediksi Model</td><td style="color: var(--primary); font-size: 1rem;">${r.pred_label}</td></tr>
            <tr><td>Confidence Score</td><td>${(r.confidence * 100).toFixed(2)}%</td></tr>
            <tr><td>Status Verifikasi</td><td>${isOk ? '<span class="badge badge-correct">✓ Sesuai Target</span>' : '<span class="badge badge-wrong">✗ Misklasifikasi</span>'}</td></tr>
          </table>
          <div style="margin-top: 14px;">
            <div style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 6px; font-weight: 600;">DISTRIBUSI PROBABILITAS SOFTMAX:</div>
            ${probBarsHtml}
          </div>
        </div>

        <div class="info-section">
          <h3>Tahap 2: Pengukuran Geometris Panjang & Ketebalan</h3>
          <table class="data-table">
            <tr><td>Panjang Rambut Terprediksi</td><td><span class="badge badge-neutral" style="font-size:0.85rem;">${lenAttr.predicted_class || 'not_required'}</span></td></tr>
            <tr><td>Rasio Kepala (Head Units)</td><td>${lenAttr.head_units ? lenAttr.head_units + ' U' : '-'}</td></tr>
            <tr><td>Rasio Bahu (Shoulder Ratio)</td><td>${lenAttr.relative_shoulder_ratio || '-'}</td></tr>
            <tr><td>Metode Estimasi Bahu</td><td>${lenAttr.method || '-'}</td></tr>
            <tr><td>Level Puncak (y_top)</td><td>${kp.y_head_top ?? '-'} px</td></tr>
            <tr><td>Level Bahu (y_shoulder)</td><td>${kp.y_shoulder ?? '-'} px</td></tr>
            <tr><td>Level Ujung Rambut (y_end)</td><td>${kp.y_hair_end ?? '-'} px</td></tr>
            <tr><td>Lebar Kranial (W_cranial)</td><td>${kp.cranial_width ? kp.cranial_width + ' px' : '-'}</td></tr>
            <tr><td>Ketebalan / Volume</td><td>${volAttr.volume_class ? volAttr.volume_class + ' (R_vol=' + volAttr.volume_ratio + ')' : '-'}</td></tr>
          </table>
        </div>

        <div class="info-section">
          <h3>Deteksi Ikatan & Latensi</h3>
          <table class="data-table">
            <tr><td>Gaya Rambut (Tied Hair)</td><td><strong>${tied.style || 'loose'}</strong> (${tied.tied ? 'Terikat' : 'Terurai Bebas'})</td></tr>
            <tr><td>Waist Constriction Ratio</td><td>${tied.features?.waist_constriction_ratio ?? '-'}</td></tr>
            <tr><td>Circularity & Solidity</td><td>${(tied.features?.circularity || 0).toFixed(3)} / ${(tied.features?.solidity || 0).toFixed(3)}</td></tr>
            <tr><td>Hair Coverage</td><td>${((r.hair_coverage || 0) * 100).toFixed(1)}% area gambar</td></tr>
            <tr><td>Latensi Tahap 1 (Type)</td><td>${r.stage1_latency_ms} ms</td></tr>
            <tr><td>Latensi Tahap 2 (UNet Seg)</td><td>${r.stage2_latency_ms} ms</td></tr>
            <tr><td>Total Latensi Inferensi</td><td><strong>${r.total_latency_ms} ms</strong></td></tr>
          </table>
        </div>
      `;

      document.getElementById('modalBackdrop').classList.add('active');
    }

    function switchModalView(view) {
      CURRENT_MODAL_VIEW = view;
      ['btnViewOverlay', 'btnViewOrig', 'btnViewMask'].forEach(id => {
        document.getElementById(id).classList.remove('active');
      });
      if (view === 'overlay') document.getElementById('btnViewOverlay').classList.add('active');
      if (view === 'orig') document.getElementById('btnViewOrig').classList.add('active');
      if (view === 'mask') document.getElementById('btnViewMask').classList.add('active');
      updateModalImage();
    }

    function updateModalImage() {
      if (!CURRENT_RECORD) return;
      const img = document.getElementById('modalImg');
      const loader = document.getElementById('modalImgLoader');
      img.style.opacity = '0';
      if (loader) loader.style.display = 'flex';
      const targetSrc = `/api/image?id=${encodeURIComponent(CURRENT_RECORD.image_id)}&view=${CURRENT_MODAL_VIEW}&t=${Date.now()}`;
      img.onload = () => {
        img.style.opacity = '1';
        if (loader) loader.style.display = 'none';
      };
      img.src = targetSrc;
    }

    function closeModal() {
      document.getElementById('modalBackdrop').classList.remove('active');
      const img = document.getElementById('modalImg');
      const loader = document.getElementById('modalImgLoader');
      if (img) {
        img.style.opacity = '0';
        img.src = '';
      }
      if (loader) loader.style.display = 'none';
      CURRENT_RECORD = null;
    }

    function switchTab(tabName) {
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      if (tabName === 'gallery') {
        document.querySelectorAll('.tab-btn')[0].classList.add('active');
        document.getElementById('tab-gallery').classList.add('active');
      } else if (tabName === 'analysis') {
        document.querySelectorAll('.tab-btn')[1].classList.add('active');
        document.getElementById('tab-analysis').classList.add('active');
      } else if (tabName === 'upload') {
        document.querySelectorAll('.tab-btn')[2].classList.add('active');
        document.getElementById('tab-upload').classList.add('active');
      }
    }

    function renderAnalysis(summary, records) {
      document.getElementById('statTotal').innerText = summary.total_test_images;
      document.getElementById('statAcc').innerText = `${summary.accuracy_percent}% (${summary.correct_predictions}/${summary.total_test_images})`;
      document.getElementById('statMis').innerText = `${summary.misclassified_predictions} citra`;
      document.getElementById('statLatency').innerText = `${summary.mean_latency_ms} ms / citra`;

      const stats = summary.per_class_stats || {};
      const pcTable = document.getElementById('perClassTable');
      let pcHtml = '';
      for (const [cls, s] of Object.entries(stats)) {
        const pct = s.total > 0 ? (s.correct / s.total * 100).toFixed(1) : 0;
        pcHtml += `<tr><td>${cls}</td><td>${pct}% (${s.correct}/${s.total})</td></tr>`;
      }
      pcTable.innerHTML = pcHtml;

      // Confusion Matrix Table
      const cm = summary.confusion_matrix || {};
      const classes = ['lurus', 'bergelombang', 'keriting', 'sangat-keriting'];
      let cmHtml = `
        <thead>
          <tr>
            <th>True \\ Pred</th>
            ${classes.map(c => `<th>${c}</th>`).join('')}
            <th>Recall</th>
          </tr>
        </thead>
        <tbody>
      `;
      classes.forEach(trueCls => {
        const row = cm[trueCls] || {};
        const total = classes.reduce((sum, c) => sum + (row[c] || 0), 0);
        const correct = row[trueCls] || 0;
        const recall = total > 0 ? (correct / total * 100).toFixed(1) : 0;

        cmHtml += `<tr><th style="text-align: left;">${trueCls}</th>`;
        classes.forEach(predCls => {
          const val = row[predCls] || 0;
          const isDiag = trueCls === predCls;
          const cellClass = isDiag ? 'cm-cell-diag' : (val > 0 ? 'cm-cell-err' : '');
          cmHtml += `<td class="${cellClass}">${val}</td>`;
        });
        cmHtml += `<td><strong>${recall}%</strong></td></tr>`;
      });
      cmHtml += '</tbody>';
      document.getElementById('cmTable').innerHTML = cmHtml;

      // Misclassified list
      const misList = document.getElementById('misclassifiedList');
      const misRecords = records.filter(r => !r.is_correct);
      misList.innerHTML = '';
      misRecords.forEach(m => {
        const item = document.createElement('div');
        item.style.cssText = 'background: #1e293b; border: 1px solid var(--border); padding: 10px 14px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; cursor: pointer;';
        item.onclick = () => openModal(m);
        item.innerHTML = `
          <div>
            <strong>${m.image_id}</strong>
            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">
              Ground Truth: <span style="color: var(--danger); font-weight: 600;">${m.true_label}</span> ➔ Prediksi: <span style="color: var(--primary); font-weight: 600;">${m.pred_label}</span> (${(m.confidence * 100).toFixed(1)}%)
            </div>
          </div>
          <span class="view-btn" style="background: rgba(56, 189, 248, 0.2); color: var(--primary);">Inspeksi Visual ➔</span>
        `;
        misList.appendChild(item);
      });
    }

    // Drag and drop handlers
    const dropZone = document.getElementById('dropZone');
    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.add('dragover'); }, false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); }, false);
    });
    dropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length) uploadAndInfer(files[0]);
    });

    function handleFileSelect(e) {
      if (e.target.files.length) uploadAndInfer(e.target.files[0]);
    }

    async function uploadAndInfer(file) {
      dropZone.innerHTML = '<div class="upload-icon">⏳</div><h2>Memproses Inferensi Citra...</h2><p>Menjalankan EfficientNetV2-S + UNet + Geometri...</p>';
      try {
        const res = await fetch('/api/upload_infer', {
          method: 'POST',
          body: file,
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error || 'Gagal memproses citra');

        renderUploadResult(data);
      } catch (err) {
        alert('Gagal: ' + err.message);
      } finally {
        dropZone.innerHTML = `
          <div class="upload-icon">📷</div>
          <h2>Unggah Foto Rambut untuk Uji Nyata</h2>
          <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 6px;">Pilih file foto dari komputer Anda untuk menjalankan pipeline EfficientNetV2-S + UNet + Geometri secara instan</p>
          <button class="upload-btn" type="button">Pilih Berkas Citra</button>
        `;
      }
    }

    function renderUploadResult(data) {
      const container = document.getElementById('uploadResult');
      container.style.display = 'block';
      const r = data.result;
      const imgs = data.images;
      const typeRes = r.stage1_hair_type;
      const lenRes = r.stage2_conditional_attributes?.length || {};
      const volRes = r.stage2_conditional_attributes?.volume || {};
      const tied = r.tied_hair_assessment || {};

      container.innerHTML = `
        <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-top: 20px;">
          <h2 style="margin-bottom: 16px; color: var(--primary);">Hasil Inferensi Citra Unggahan</h2>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
            <div>
              <div style="display: flex; gap: 8px; justify-content: center; margin-bottom: 10px;">
                <button class="view-btn active" id="upBtnOverlay" onclick="document.getElementById('upImgView').src='${imgs.overlay}'; this.classList.add('active'); document.getElementById('upBtnOrig').classList.remove('active'); document.getElementById('upBtnMask').classList.remove('active');">Annotated Overlay</button>
                <button class="view-btn" id="upBtnOrig" onclick="document.getElementById('upImgView').src='${imgs.orig}'; this.classList.add('active'); document.getElementById('upBtnOverlay').classList.remove('active'); document.getElementById('upBtnMask').classList.remove('active');">Foto Asli</button>
                <button class="view-btn" id="upBtnMask" onclick="document.getElementById('upImgView').src='${imgs.mask}'; this.classList.add('active'); document.getElementById('upBtnOverlay').classList.remove('active'); document.getElementById('upBtnOrig').classList.remove('active');">Binary Mask</button>
              </div>
              <div style="background: #000; border-radius: 8px; overflow: hidden; max-height: 500px; display: flex; align-items: center; justify-content: center;">
                <img id="upImgView" src="${imgs.overlay}" style="max-width: 100%; max-height: 500px;" alt="Overlay">
              </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 14px;">
              <div class="info-section">
                <h3>Tahap 1: Jenis Rambut</h3>
                <table class="data-table">
                  <tr><td>Prediksi Kelas</td><td><span class="badge badge-type" style="font-size:0.9rem;">${typeRes.predicted_class}</span></td></tr>
                  <tr><td>Confidence</td><td><strong>${(typeRes.confidence * 100).toFixed(2)}%</strong></td></tr>
                  <tr><td>Latensi Tahap 1</td><td>${typeRes.latency_ms} ms</td></tr>
                </table>
              </div>
              <div class="info-section">
                <h3>Tahap 2: Pengukuran Geometris</h3>
                <table class="data-table">
                  <tr><td>Panjang Rambut</td><td><span class="badge badge-neutral">${lenRes.predicted_class || 'not_required'}</span></td></tr>
                  <tr><td>Head Units</td><td>${lenRes.head_units ?? '-'}</td></tr>
                  <tr><td>Shoulder Ratio</td><td>${lenRes.relative_shoulder_ratio ?? '-'}</td></tr>
                  <tr><td>Metode</td><td>${lenRes.method ?? '-'}</td></tr>
                  <tr><td>Gaya Rambut</td><td><strong>${tied.style || 'loose'}</strong></td></tr>
                  <tr><td>Ketebalan (Volume)</td><td>${volRes.volume_class ? volRes.volume_class + ' (R_vol=' + volRes.volume_ratio + ')' : '-'}</td></tr>
                  <tr><td>Total Latensi</td><td><strong>${r.total_latency_ms} ms</strong></td></tr>
                </table>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    document.addEventListener('DOMContentLoaded', initApp);
  </script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run temporary CV Inference & Geometric Audit Viewer")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host address (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port number (default: {DEFAULT_PORT})")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("  CV Hair Inference & Geometric Audit Viewer (Temporary)")
    print("=" * 70)
    precompute_test_records()

    server_address = (args.host, args.port)
    httpd = ThreadingHTTPServer(server_address, AuditRequestHandler)

    url = f"http://{args.host}:{args.port}"
    print("-" * 70)
    print(f"Server audit viewer aktif di:  {url}")
    print("Buka tautan di atas pada peramban web (browser) Anda.")
    print("")
    print("Petunjuk setelah audit selesai:")
    print("1. Tekan Ctrl+C di terminal ini untuk mematikan server.")
    print("2. Hapus file audit ini dengan satu perintah PowerShell:")
    print("   Remove-Item apps/api/cv/geometry/_audit_viewer.py")
    print("-" * 70)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer audit viewer dihentikan.")
        httpd.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
