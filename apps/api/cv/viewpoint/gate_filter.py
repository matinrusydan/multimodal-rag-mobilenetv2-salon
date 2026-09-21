# -*- coding: utf-8 -*-
"""viewpoint/gate_filter.py — Lapis C pipeline: gate viewpoint "belakang saja".

Input : apps/ai/app/crawler/harvest/clip_ab/   (hasil lapis A+B dari clip_filter.py)
Output: apps/ai/app/crawler/harvest/final_clean/ (HANYA prediksi viewpoint = belakang)

Kenapa dipisah: mediapipe HANYA ada di venv apps/api/cv, sedangkan CLIP (layer A+B)
butuh torch/transformers di venv ComfyUI. Jadi lapis C dijalankan terpisah dari sini.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\gate_filter.py
  & ".venv\\Scripts\\python.exe" viewpoint\\gate_filter.py --src clip_ab --all-viewpoints
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

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

HERE = Path(__file__).resolve().parent
APPS = HERE.parents[2]
HARVEST = APPS / "ai" / "app" / "crawler" / "harvest"
REPORTS = HERE / "reports"


def main():
    ap = argparse.ArgumentParser(description="Lapis C: gate viewpoint belakang saja.")
    ap.add_argument("--src", default="clip_ab", help="Folder sumber di harvest/ (hasil lapis A+B)")
    ap.add_argument("--out", default="final_clean", help="Folder output di harvest/")
    ap.add_argument("--min-det", type=float, default=0.3)
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument(
        "--all-viewpoints",
        action="store_true",
        help="Simpan semua viewpoint (beri prefix kelas). Default: hanya belakang.",
    )
    ap.add_argument("--report", default=str(REPORTS / "gate_filter_result.json"))
    args = ap.parse_args()

    src = HARVEST / args.src
    out = HARVEST / args.out
    out.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    items = sorted(src.glob("*.jpg")) + sorted(src.glob("*.png"))
    if args.max > 0:
        items = items[: args.max]
    print(f"=== Lapis C: Gate Viewpoint ===\nsrc={src}\ngambar={len(items)}")
    if not items:
        print("ERROR: tidak ada gambar di sumber.")
        return

    for m in (POSE_MODEL, FACE_MODEL):
        if not m.exists():
            print(f"ERROR: model tidak ada: {m}")
            return

    pose_lk = make_pose(POSE_MODEL, args.min_det)
    face_det = make_face(FACE_MODEL, args.min_det)
    face_lm_lk = make_face_landmarker(FACE_LM_MODEL, args.min_det) if FACE_LM_MODEL.exists() else None

    dist = Counter()
    passed, results = [], []
    for i, p in enumerate(items, 1):
        try:
            arr = np.asarray(Image.open(p).convert("RGB"))
        except Exception as exc:
            results.append({"file": p.name, "error": f"load: {exc}"})
            continue
        face = face_signal(face_det, arr)
        f_lm = face_landmark_signal(face_lm_lk, arr)
        pose = pose_signal(pose_lk, arr, 0.5)
        cls, conf, _ = decide_viewpoint(face, pose, f_lm)
        dist[cls] += 1
        keep = (cls == "belakang") or args.all_viewpoints
        rec = {"file": p.name, "viewpoint": cls, "confidence": round(float(conf), 3), "keep": keep}
        results.append(rec)
        if keep:
            dst = out / (f"{cls}_{p.name}" if args.all_viewpoints else p.name)
            if not dst.exists():
                shutil.copy2(p, dst)
            passed.append(p)
        if i % 50 == 0:
            print(f"  {i}/{len(items)}... belakang={dist.get('belakang', 0)}", flush=True)

    pose_lk.close()
    face_det.close()
    if face_lm_lk:
        face_lm_lk.close()

    report = {
        "analysis": "gate_filter_layerC",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "src": args.src,
        "out": args.out,
        "n_total": len(items),
        "n_keep": len(passed),
        "viewpoint_distribution": dict(dist),
        "all_viewpoints": args.all_viewpoints,
        "records": results,
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== HASIL LAPIS C ===")
    print(f"  input    : {len(items)}")
    for c in ("belakang", "samping", "depan"):
        print(f"  {c:9s}: {dist.get(c, 0)}")
    print(f"  KEEP (belakang) : {len(passed)}")
    print(f"  -> {out}\n  Report -> {args.report}")


if __name__ == "__main__":
    main()
