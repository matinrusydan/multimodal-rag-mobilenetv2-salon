# -*- coding: utf-8 -*-
"""Web app validasi labeling manual (ground truth tool) — Fase 5.

Server ringan (FastAPI) untuk mereview & mengoreksi label panjang rambut pada
citra Figaro-1k. Menampilkan prediksi Metode A (gemini) & Metode B (geometric)
berdampingan, lalu menyimpan koreksi Anda sebagai ground truth (CSV + JSON).

Jalankan (venv apps/ai):
  apps\\ai\\.venv\\Scripts\\python.exe apps\\ai\\tools\\label_validator\\server.py
Buka: http://127.0.0.1:5199

Output koreksi:
  apps/api/cv/reports/ground_truth_length.json   (label final per frame)
  apps/api/cv/reports/ground_truth_length.csv    (untuk analisis)
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response

BASE = Path(__file__).resolve()
CV = BASE.parents[3] / "api" / "cv"  # apps/api/cv
ZIP_PATH = CV / "dataset" / "figaro-1k.zip"
REPORTS = CV / "reports"
GEO_LABELS = REPORTS / "hair_length_geometris.json"
GEMINI_LABELS = REPORTS / "hair_length_gemini.json"
OUT_JSON = REPORTS / "ground_truth_length.json"
OUT_CSV = REPORTS / "ground_truth_length.csv"

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]
CLASSES = [("lurus", 1, 150), ("bergelombang", 151, 300), ("keriting", 301, 450), ("sangat-keriting", 451, 600)]

app = FastAPI(title="Label Validator")


def _load_json(p: Path) -> dict:
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _geo_map() -> dict[str, dict]:
    data = _load_json(GEO_LABELS)
    return {f"{r['frame']:05d}": r for r in data.get("records", [])}


def _gemini_map() -> dict[str, dict]:
    data = _load_json(GEMINI_LABELS)
    return data.get("records", {})


def _gt_map() -> dict[str, dict]:
    data = _load_json(OUT_JSON)
    return data.get("records", {})


def _class_of(frame: int) -> str | None:
    for name, lo, hi in CLASSES:
        if lo <= frame <= hi:
            return name
    return None


def _all_frames() -> list[int]:
    return [f for _, lo, hi in CLASSES for f in range(lo, hi + 1)]


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


@app.get("/api/items")
def items(limit: int = 0, only_unlabeled: bool = False, per_type: int = 0) -> JSONResponse:
    geo = _geo_map()
    gem = _gemini_map()
    gt = _gt_map()
    out = []
    counter: dict[str, int] = {name: 0 for name, _, _ in CLASSES}
    for frame in _all_frames():
        fkey = f"{frame:05d}"
        tipe = _class_of(frame)
        # subset representatif: ambil N pertama per tipe (lintas kelas panjang)
        if per_type and tipe is not None:
            if counter[tipe] >= per_type:
                continue
            counter[tipe] += 1
        rec = {
            "frame": frame,
            "key": fkey,
            "tipe_asal": tipe,
            "geometric": geo.get(fkey, {}).get("panjang_label"),
            "gemini": gem.get(fkey, {}).get("label"),
            "ground_truth": gt.get(fkey, {}).get("label") if fkey in gt else None,
        }
        if only_unlabeled and rec["ground_truth"]:
            continue
        out.append(rec)
    if limit:
        out = out[:limit]
    return JSONResponse({"total": len(out), "classes": LENGTH_CLASSES, "items": out})


@app.get("/api/image/{frame}")
def image(frame: int) -> Response:
    with zipfile.ZipFile(ZIP_PATH) as z:
        cands = [n for n in z.namelist() if f"Frame{frame:05d}-org.jpg" in n]
        if not cands:
            raise HTTPException(404, "frame tidak ditemukan")
        data = z.read(cands[0])
    return Response(content=data, media_type="image/jpeg")


@app.get("/api/mask/{frame}")
def mask(frame: int) -> Response:
    """Sajikan mask GT sebagai PNG agar bisa di-overlay di UI."""
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise HTTPException(500, f"PIL tidak tersedia: {exc}") from exc
    with zipfile.ZipFile(ZIP_PATH) as z:
        cands = [n for n in z.namelist() if f"Frame{frame:05d}-gt.pbm" in n]
        if not cands:
            raise HTTPException(404, "mask tidak ditemukan")
        data = z.read(cands[0])
    img = Image.open(io.BytesIO(data)).convert("L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@app.post("/api/label")
def label(payload: dict) -> JSONResponse:
    key = str(payload.get("key", "")).strip()
    lbl = str(payload.get("label", "")).strip()
    if not key or lbl not in LENGTH_CLASSES:
        raise HTTPException(400, "key/label tidak valid")

    gt = _gt_map()
    gt[key] = {
        "label": lbl,
        "frame": int(payload.get("frame", int(key))),
        "tipe_asal": payload.get("tipe_asal"),
        "geometric": payload.get("geometric"),
        "gemini": payload.get("gemini"),
    }
    _save(gt)
    total = len(gt)
    return JSONResponse({"ok": True, "total_labeled": total})


@app.post("/api/clear")
def clear(payload: dict | None = None) -> JSONResponse:
    key = str((payload or {}).get("key", "")).strip()
    gt = _gt_map()
    if key and key in gt:
        del gt[key]
        _save(gt)
    return JSONResponse({"ok": True, "total_labeled": len(gt)})


def _save(gt: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"length_classes": LENGTH_CLASSES, "n": len(gt), "records": gt}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["frame", "tipe_asal", "geometric", "gemini", "ground_truth"])
        for k in sorted(gt):
            r = gt[k]
            w.writerow([r["frame"], r.get("tipe_asal"), r.get("geometric"), r.get("gemini"), r.get("label")])


@app.get("/api/stats")
def stats() -> JSONResponse:
    gt = _gt_map()
    dist = {c: 0 for c in LENGTH_CLASSES}
    for r in gt.values():
        if r["label"] in dist:
            dist[r["label"]] += 1
    return JSONResponse({"total": len(gt), "distribution": dist, "target": len(_all_frames())})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5199, log_level="info")
