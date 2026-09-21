# -*- coding: utf-8 -*-
"""viewpoint/clip_filter.py — Pipeline 3-lapis filter dataset harvest.

Masalah: harvest berbasis TAG -> banyak gambar tidak relevan:
  - frontal (menghadap depan), bukan back-view;
  - non-manusia: anime, patung, hewan, dokumen, potret jadul.

Solusi pipeline (satu jalan, urut, rekam alasan buang):
  Lapis A  CLIP "hair back-view photo"  : gambar harus foto orang DARI BELAKANG
                                           (bukan frontal).
  Lapis B  CLIP zero-shot "real human"  : gambar harus manusia nyata (bukan anime/
                                           patung/hewan/dokumen).
  Lapis C  Gate viewpoint (mediapipe)   : prediksi harus "belakang".

Reuse clip-base (sudah terunduh, offline) + gate.py (mediapipe).

Output:
  apps/ai/app/crawler/harvest/final_clean/*.jpg   (lolos semua lapis)
  apps/api/cv/viewpoint/reports/pipeline_result.json

Usage (venv ComfyUI/GPU):
  & "C:\\Users\\lilol\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" apps\\api\\cv\\viewpoint\\clip_filter.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

# pakai cache lokal saja (model sudah terunduh). Set "0" untuk paksa online.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

# --- import gate (mediapipe) dari apps/api/cv ---
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gate import (  # noqa: E402
        decide_viewpoint,
        face_landmark_signal,
        face_signal,
        make_face,
        make_face_landmarker,
        make_pose,
        pose_signal,
    )
    from common.constants import FACE_LM_MODEL, FACE_MODEL, POSE_MODEL  # noqa: E402

    HAS_GATE = True
except Exception as exc:  # pragma: no cover
    HAS_GATE = False
    GATE_IMPORT_ERR = str(exc)

HERE = Path(__file__).resolve().parent
CV_DIR = HERE.parent
APPS = CV_DIR.parents[1]
HARVEST = APPS / "ai" / "app" / "crawler" / "harvest"
SRC_DIRS = ["back_view", "openverse", "huggingface", "bing"]
# Lapis A+B (CLIP) jalan di venv ComfyUI (ada torch). Gate mediapipe jalan terpisah
# di venv apps/api/cv (lihat gate_filter.py) -> output akhir: harvest/final_clean/.
OUT_DIR = HARVEST / "clip_ab"
REPORTS = HERE / "reports"

# ------------------------------------------------------------------
# Prompts CLIP
# ------------------------------------------------------------------
# Lapis A: foto CLOSE-UP rambut dari belakang (bukan frontal, bukan pemandangan)
POS_A = [
    "a close-up photograph of human hair taken from behind, hair fills the frame",
    "back view of a person's head showing their hairstyle up close",
    "a photo focusing on the hair on the back of a person's head",
    "rear view of a hairstyle, hair is the main subject of the photo",
    "the back of a head covered with hair, photographed for a hairstyle",
]
NEG_A = [
    "a frontal face portrait looking at the camera",
    "a close-up of a human face with eyes, nose and mouth visible",
    "the front of a person's face smiling at the camera",
    "a wide scenery or street photo with a tiny distant person",
    "a full body photo of a person standing in a room or outdoors",
    "a crowd of many people or a group activity",
    "a bald head or a scalp with no hair",
]

# Lapis B: manusia nyata vs non-manusia / bukan foto
POS_B = ["a real photograph of a human person"]
NEG_B = [
    "an anime, cartoon or illustration of a character",
    "a sculpture or statue of a head or person",
    "an animal, insect, bird or spider",
    "a document, book page, logo, or product photo",
    "a drawing, painting or sketch",
    "an object, food, furniture or tool",
    "a doll, figurine or puppet",
]


def _feat(out):
    """Ambil tensor fitur dari output CLIPModel (transformers 4.x -> tensor, 5.x -> objek)."""
    if hasattr(out, "pooler_output"):
        return out.pooler_output
    if isinstance(out, (tuple, list)):
        return out[0]
    return out


def collect_images(sources):
    items = []
    for d in sources:
        dd = HARVEST / d
        if not dd.exists():
            continue
        for f in sorted(dd.glob("*.jpg")):
            items.append(f)
        for f in sorted(dd.glob("*.png")):
            items.append(f)
    return items


def main():
    ap = argparse.ArgumentParser(description="Pipeline 3-lapis filter dataset harvest.")
    ap.add_argument("--model", default="openai/clip-vit-base-patch32")
    ap.add_argument("--margin-a", type=float, default=0.03, help="Lapis A: KEEP jika pos > negA + margin")
    ap.add_argument("--margin-b", type=float, default=0.0, help="Lapis B: KEEP jika person > negB + margin")
    ap.add_argument("--source", nargs="*", default=SRC_DIRS)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--no-gate", action="store_true", help="Lewati lapis C (gate) untuk uji cepat")
    ap.add_argument("--out", default=str(REPORTS / "pipeline_result.json"))
    args = ap.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = collect_images(args.source)
    if args.max > 0:
        items = items[: args.max]
    print(f"=== Pipeline 3-lapis ===\nmodel={args.model}\ngambar={len(items)}")
    print(f"margin_a={args.margin_a} margin_b={args.margin_b} gate={'off' if args.no_gate else 'on'}")
    if not items:
        print("ERROR: tidak ada gambar.")
        return

    import torch
    from transformers import CLIPModel, CLIPProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}", flush=True)
    model = CLIPModel.from_pretrained(args.model).to(device).eval()
    proc = CLIPProcessor.from_pretrained(args.model)

    with torch.no_grad():
        tA = _feat(model.get_text_features(**proc(text=POS_A + NEG_A, return_tensors="pt", padding=True).to(device)))
        tA = tA / tA.norm(dim=-1, keepdim=True)
        tB = _feat(model.get_text_features(**proc(text=POS_B + NEG_B, return_tensors="pt", padding=True).to(device)))
        tB = tB / tB.norm(dim=-1, keepdim=True)
    npa, npb = len(POS_A), len(POS_B)

    # --- siapkan gate (lapis C) ---
    gate_ok = HAS_GATE and not args.no_gate
    if gate_ok:
        for m in (POSE_MODEL, FACE_MODEL):
            if not m.exists():
                print(f"WARNING: model gate tidak ada: {m} -> gate dimatikan")
                gate_ok = False
                break
    pose_lk = face_det = face_lm_lk = None
    if gate_ok:
        pose_lk = make_pose(POSE_MODEL, 0.3)
        face_det = make_face(FACE_MODEL, 0.3)
        face_lm_lk = make_face_landmarker(FACE_LM_MODEL, 0.3) if FACE_LM_MODEL.exists() else None
    elif not HAS_GATE:
        print(f"WARNING: gate tidak bisa diimpor ({GATE_IMPORT_ERR}) -> hanya lapis A+B")

    passed, results = [], []
    reject = Counter()
    batch_ok = args.batch
    i = 0
    while i < len(items):
        chunk = items[i : i + batch_ok]
        try:
            imgs = [Image.open(p).convert("RGB") for p in chunk]
            with torch.no_grad():
                inp = proc(images=imgs, return_tensors="pt").to(device)
                emb = _feat(model.get_image_features(**inp))
                emb = emb / emb.norm(dim=-1, keepdim=True)
                sA = (emb @ tA.T).cpu().numpy()
                sB = (emb @ tB.T).cpu().numpy()
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower() and batch_ok > 1:
                batch_ok = max(1, batch_ok // 2)
                print(f"  OOM -> batch={batch_ok}", flush=True)
                continue
            raise

        for j, p in enumerate(chunk):
            rec = {"file": p.name, "source": p.parent.name}
            # ---- Lapis A ----
            a = sA[j]
            pos_a, neg_a = float(np.max(a[:npa])), float(np.max(a[npa:]))
            rec.update(score_a_pos=round(pos_a, 4), score_a_neg=round(neg_a, 4),
                       diff_a=round(pos_a - neg_a, 4))
            if not (pos_a > neg_a + args.margin_a):
                rec["decision"] = "reject"
                rec["reject_layer"] = "A_not_backview"
                reject["A_not_backview"] += 1
                results.append(rec)
                continue
            # ---- Lapis B ----
            b = sB[j]
            pos_b, neg_b = float(b[0]), float(np.max(b[npb:]))
            rec.update(score_b_person=round(pos_b, 4), score_b_neg=round(neg_b, 4),
                       diff_b=round(pos_b - neg_b, 4))
            if not (pos_b > neg_b + args.margin_b):
                rec["decision"] = "reject"
                rec["reject_layer"] = "B_not_human"
                reject["B_not_human"] += 1
                results.append(rec)
                continue
            # ---- Lapis C ----
            if gate_ok:
                try:
                    arr = np.asarray(Image.open(p).convert("RGB"))
                    face = face_signal(face_det, arr)
                    pose = pose_signal(pose_lk, arr, 0.5)
                    f_lm = face_landmark_signal(face_lm_lk, arr)
                    cls, conf, _ = decide_viewpoint(face, pose, f_lm)
                except Exception as exc:
                    cls, conf = "error", 0.0
                    rec["gate_error"] = str(exc)
                rec["viewpoint"] = cls
                rec["viewpoint_conf"] = round(float(conf), 3)
                if cls != "belakang":
                    rec["decision"] = "reject"
                    rec["reject_layer"] = f"C_viewpoint_{cls}"
                    reject[f"C_viewpoint_{cls}"] += 1
                    results.append(rec)
                    continue
            # ---- LOLOS ----
            rec["decision"] = "keep"
            results.append(rec)
            dst = OUT_DIR / p.name
            if not dst.exists():
                shutil.copy2(p, dst)
            passed.append(p)

        i += len(chunk)
        if i % 50 < batch_ok:
            print(f"  {i}/{len(items)}... keep={len(passed)}", flush=True)

    if gate_ok:
        pose_lk.close()
        face_det.close()
        if face_lm_lk:
            face_lm_lk.close()

    vp_dist = Counter(r.get("viewpoint") for r in results if r.get("viewpoint"))
    report = {
        "analysis": "pipeline_3layer",
        "model": args.model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "margin_a": args.margin_a,
        "margin_b": args.margin_b,
        "gate_enabled": gate_ok,
        "total": len(items),
        "keep": len(passed),
        "reject": len(items) - len(passed),
        "reject_breakdown": dict(reject),
        "viewpoint_distribution": dict(vp_dist),
        "per_source_keep": dict(Counter(p.parent.name for p in passed)),
        "records": results,
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== HASIL PIPELINE ===")
    print(f"  input   : {len(items)}")
    print(f"  buang A (bukan back-view) : {reject['A_not_backview']}")
    print(f"  buang B (bukan manusia)   : {reject['B_not_human']}")
    for k, v in reject.items():
        if k.startswith("C_"):
            print(f"  buang C ({k[2:]}) : {v}")
    print(f"  KEEP    : {len(passed)}")
    print(f"  per sumber (keep): {report['per_source_keep']}")
    print(f"  -> {OUT_DIR}\n  Report -> {args.out}")


if __name__ == "__main__":
    main()
