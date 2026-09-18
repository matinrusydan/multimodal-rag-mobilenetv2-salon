# -*- coding: utf-8 -*-
"""Helper I/O: baca/tulis JSON, list dataset, path relatif."""

from __future__ import annotations

import json
from pathlib import Path

from common.constants import CV_DIR, FIGARO, EXTRA

HAIR_TYPES = ["lurus", "bergelombang", "keriting", "sangat-keriting"]


def load_json(path: Path | str) -> dict | list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: Path | str, data) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def relpath_of(image_id: str) -> str:
    """figaro1k/<type>/<file>.jpg -> dataset/figaro1k/<type>/<file>.jpg"""
    return image_id.replace("figaro1k/", "dataset/figaro1k/", 1)


def image_path(image_id: str) -> Path:
    return CV_DIR / relpath_of(image_id)


def list_figaro() -> list[dict]:
    """List semua Figaro-1k: image_id, relpath, source."""
    items = []
    for t in HAIR_TYPES:
        for p in sorted((FIGARO / t).glob("*.jpg")):
            items.append({
                "image_id": f"figaro1k/{t}/{p.name}",
                "relpath": str(p.relative_to(CV_DIR)).replace("\\", "/"),
                "source": "figaro1k",
            })
    return items


def list_extra() -> list[dict]:
    items = []
    if not EXTRA.exists():
        return items
    for d in sorted(EXTRA.iterdir()):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.jpg")):
            items.append({
                "image_id": f"extra/{d.name}/{p.name}",
                "relpath": str(p.relative_to(CV_DIR)).replace("\\", "/"),
                "source": "extra",
            })
    return items


def collect_images(source: str = "figaro") -> list[dict]:
    items = []
    if source in ("figaro", "all"):
        items += list_figaro()
    if source in ("extra", "all"):
        items += list_extra()
    return items
