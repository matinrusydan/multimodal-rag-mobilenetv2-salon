# -*- coding: utf-8 -*-
"""Cleaning robust 4 lapis untuk dataset harvested (Wikimedia + Openverse + HF).

Lapis:
  L1 BLACKLIST JUDUL — buang objek/hewan/makanan/graphic (dari title/key).
  L2 DETEKSI MANUSIA — wajib ada wajah (BlazeFace) ATAU pose (Pose Landmarker).
  L3 ADA RAMBUT — heuristik landmark: kepala/telinga/bahu terlihat (indikasi rambut).
  L4 GATE VIEWPOINT — harus "belakang" dengan confidence >= ambang (ketat).

Gambar GAGAL → dibuang (tidak disalin). Gambar LOLOS → disalin ke back_view_clean/.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\filter_harvested.py
  & ".venv\\Scripts\\python.exe" viewpoint\\filter_harvested.py --conf 0.99
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import FACE_LM_MODEL, FACE_MODEL, POSE_MODEL, VIEWPOINT_ACCEPTED

# impor gate
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate import (  # noqa: E402
    face_landmark_signal, face_signal, pose_signal, decide_viewpoint,
    make_face, make_face_landmarker, make_pose,
)

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"

# Sumber harvest (apps/ai/app/crawler/harvest)
HARVEST = HERE.parents[2] / "ai" / "app" / "crawler" / "harvest"
SRC_DIRS = ["back_view", "openverse", "huggingface"]
OUT_DIR = HARVEST / "back_view_clean"

# L1 blacklist judul/kata
BLACKLIST = [
    "armchair", "chair", "comb", "wig", "mannequin", "sculpture", "painting",
    "cat", "horse", "eagle", "bird", "dog", "insect", "fly", "bee", "spider",
    "bread", "raisin", "mango", "nut", "cake", "food",
    "graphic", "diagram", "technique", "stepbystep", "step-by-step", "infographic",
    "map", "terrace", "balcony", "geograph", "riding", "tattoo", "muscle",
    "building", "house", "logo", "icon", "emoji", "cartoon", "drawing", "sketch",
    "illustration", "poster", "stamp", "coin", "logo", "texture-pattern",
]
GRAPHIC_EXT = (".png", ".gif", ".svg")


def is_blacklisted(key: str) -> str | None:
    low = key.lower()
    for w in BLACKLIST:
        if w in low:
            return w
    return None


def main():
    ap = argparse.ArgumentParser(description="Cleaning 4 lapis dataset harvested.")
    ap.add_argument("--conf", type=float, default=0.99, help="Ambang confidence gate (default 0.99)")
    ap.add_argument("--min-det", type=float, default=0.3)
    ap.add_argument("--out", default=str(REPORTS / "filter_harvested_result.json"))
    args = ap.parse_args()

    REPORTS.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # kumpulkan file + key (dari manifest bila ada)
    items = []  # {path, key, source}
    for d in SRC_DIRS:
        dd = HARVEST / d
        if not dd.exists():
            continue
        man = HARVEST / f"_manifest{'' if d=='back_view' else '_'+d}.json"
        keymap = {}
        if man.exists():
            try:
                for rec in json.loads(man.read_text(encoding="utf-8")):
                    keymap[rec["file"]] = rec.get("title") or rec.get("key") or rec["file"]
            except Exception:
                pass
        for f in sorted(dd.glob("*.jpg")):
            items.append({"path": f, "key": keymap.get(f.name, f.name), "source": d})
        for f in sorted(dd.glob("*.png")):
            items.append({"path": f, "key": keymap.get(f.name, f.name), "source": d})

    print(f"=== Cleaning 4 lapis: {len(items)} gambar ===")
    if not items:
        print("ERROR: tidak ada gambar di sumber harvest.")
        return

    # load model
    pose_lk = make_pose(POSE_MODEL, args.min_det)
    face_det = make_face(FACE_MODEL, args.min_det)
    face_lm_lk = make_face_landmarker(FACE_LM_MODEL, args.min_det) if FACE_LM_MODEL.exists() else None

    stats = Counter()
    reject_reason = Counter()
    passed = []

    for i, it in enumerate(items, 1):
        # L1 judul
        w = is_blacklisted(it["key"]) or is_blacklisted(it["path"].name)
        if w or it["path"].suffix.lower() in GRAPHIC_EXT:
            stats["reject_L1_title"] += 1
            reject_reason[f"L1:{w or 'ext'}"] += 1
            continue

        try:
            arr = np.asarray(Image.open(it["path"]).convert("RGB"))
        except Exception:
            stats["reject_load"] += 1
            continue

        face = face_signal(face_det, arr)
        pose = pose_signal(pose_lk, arr, 0.5)
        face_lm = face_landmark_signal(face_lm_lk, arr)

        # L2 manusia: wajah atau pose
        human = face.get("face_present") or pose.get("pose_present")
        if not human:
            stats["reject_L2_no_human"] += 1
            reject_reason["L2:non_human"] += 1
            continue

        # L3 ada rambut: indikasi landmark kepala (telinga/hidung) ATAU wajah
        head_signal = (
            pose.get("ears_both_visible") or pose.get("nose_visible")
            or face.get("face_present") or face_lm.get("face_lm_present")
        )
        if not head_signal:
            stats["reject_L3_no_hair"] += 1
            reject_reason["L3:no_hair_signal"] += 1
            continue

        # L4 gate viewpoint
        cls, conf, _ = decide_viewpoint(face, pose, face_lm)
        if cls not in VIEWPOINT_ACCEPTED or conf < args.conf:
            stats["reject_L4_viewpoint"] += 1
            reject_reason[f"L4:{cls}@<{args.conf}"] += 1
            continue

        # LOLOS
        dst = OUT_DIR / it["path"].name
        try:
            shutil.copy2(it["path"], dst)
        except Exception:
            stats["reject_copy"] += 1
            continue
        stats["passed"] += 1
        passed.append({"file": it["path"].name, "source": it["source"], "key": it["key"], "conf": conf})

        if i % 50 == 0:
            print(f"  {i}/{len(items)}... passed={stats['passed']}", flush=True)

    pose_lk.close()
    face_det.close()
    if face_lm_lk:
        face_lm_lk.close()

    report = {
        "analysis": "filter_harvested_4layer",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_input": len(items),
        "conf_threshold": args.conf,
        "stats": dict(stats),
        "reject_reasons": dict(reject_reason),
        "n_passed": stats["passed"],
        "passed": passed,
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== HASIL CLEANING ===")
    print(f"  input          : {len(items)}")
    print(f"  L1 buang (judul): {stats['reject_L1_title']}")
    print(f"  L2 buang (non-manusia): {stats['reject_L2_no_human']}")
    print(f"  L3 buang (non-rambut): {stats['reject_L3_no_hair']}")
    print(f"  L4 buang (bukan belakang/conf<{args.conf}): {stats['reject_L4_viewpoint']}")
    print(f"  LOLOS          : {stats['passed']}")
    print(f"\nOutput bersih -> {OUT_DIR}")
    print(f"Report -> {args.out}")


if __name__ == "__main__":
    main()
