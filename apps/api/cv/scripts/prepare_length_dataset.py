# -*- coding: utf-8 -*-
"""Siapkan dataset tensor hair_length dari manifest label + tensor preprocessed (Fase 3.3).

Tensor preprocessed sudah ada di apps/api/cv/preprocessed/{train,val}/<tipe>/*.pt
(nama file: <frame>_r<aug>.pt). Kita TIDAK menyalin (boros), melainkan membuat
manifest mapping: split/tipe/frame -> panjang_label. Latih memakai dataset custom
yang membaca tensor langsung dari lokasi asli (lihat export_to_onnx_length.py).

Input : manifest label dari Metode A (gemini) atau B (geometris)
Output: apps/api/cv/preprocessed_length/index.json
          { "train": [ {pt, tipe, frame, label} ... ], "val": [...] }

Jalankan:
  apps\\api\\cv\\.venv\\Scripts\\python.exe apps\\api\\cv\\scripts\\prepare_length_dataset.py --method geometric
  ... --method gemini
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PRE = BASE / "preprocessed"
REPORTS = BASE / "reports"
OUT_DIR = BASE / "preprocessed_length"
FRAME_RE = re.compile(r"^(\d{5})_r\d$")


def label_map_geometric() -> dict[str, str]:
    data = json.loads((REPORTS / "hair_length_geometris.json").read_text(encoding="utf-8"))
    return {f"{r['frame']:05d}": r["panjang_label"] for r in data["records"]}


def label_map_gemini() -> dict[str, str]:
    data = json.loads((REPORTS / "hair_length_gemini.json").read_text(encoding="utf-8"))
    # records: {"00001": {"label": ..., ...}}
    return {k: v["label"] for k, v in data["records"].items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["geometric", "gemini"], required=True)
    args = ap.parse_args()

    lmap = label_map_geometric() if args.method == "geometric" else label_map_gemini()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    index: dict[str, list[dict]] = {"train": [], "val": []}
    used = 0
    skipped = 0

    for split in ("train", "val"):
        for tipe_dir in sorted((PRE / split).iterdir()):
            if not tipe_dir.is_dir():
                continue
            for pt in sorted(tipe_dir.glob("*.pt")):
                stem = pt.stem  # e.g. 00151_r2
                base = stem.split("_r")[0]
                frame = f"{int(base):05d}" if base.isdigit() else base
                label = lmap.get(frame)
                if not label:
                    skipped += 1
                    continue
                index[split].append(
                    {
                        "pt": str(pt.relative_to(BASE)).replace("\\", "/"),
                        "tipe": tipe_dir.name,
                        "frame": frame,
                        "label": label,
                    }
                )
                used += 1

    OUT_INDEX = OUT_DIR / f"index_{args.method}.json"
    OUT_INDEX.write_text(
        json.dumps({"method": args.method, "index": index}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    from collections import Counter

    for split in ("train", "val"):
        c = Counter(r["label"] for r in index[split])
        print(f"{split}: {len(index[split])} tensor | {dict(c)}")
    print(f"used={used} skipped={skipped}")
    print(f"Index -> {OUT_INDEX}")

if __name__ == "__main__":
    main()
