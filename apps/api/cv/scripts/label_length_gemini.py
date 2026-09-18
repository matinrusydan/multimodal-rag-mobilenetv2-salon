# -*- coding: utf-8 -*-
"""Label panjang rambut 4 kelas via Gemini vision (Metode A) — Fase 3.2.

Mengirim citra ke Gemini (vision) dengan prompt terstruktur untuk mengklasifikasi
panjang rambut salon (pendek / pendek-menengah / menengah / panjang).

Karena free tier hanya ~20 request/hari/model, script ini:
  - memproses SUBSET (--per-type N, default 30) agar hemat kuota,
  - mencoba beberapa model secara berurutan (rotasi) saat kena 429,
  - mendukung RESUME (lewati frame yang sudah punya label di output),
  - menyimpan progres tiap N citra.

Output: apps/api/cv/reports/hair_length_gemini.json

Jalankan (venv apps/ai: google-genai + PIL):
  apps\\ai\\.venv\\Scripts\\python.exe apps\\api\\cv\\scripts\\label_length_gemini.py --per-type 30
"""

from __future__ import annotations

import argparse
import io
import json
import os
import time
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[2]  # repo root (BASE=apps/api/cv)
DATASET_ZIP = BASE / "dataset" / "figaro-1k.zip"
OUT_JSON = BASE / "reports" / "hair_length_gemini.json"

load_dotenv(ROOT / "apps" / "ai" / ".env")

LENGTH_CLASSES = ["pendek", "pendek-menengah", "menengah", "panjang"]
CLASSES = [
    ("lurus", 1, 150),
    ("bergelombang", 151, 300),
    ("keriting", 301, 450),
    ("sangat-keriting", 451, 600),
]
MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
]

PROMPT = (
    "Kamu ahli penata rambut. Lihat foto ini dan klasifikasikan PANJANG rambut orang tersebut "
    "ke SALAH SATU dari 4 kategori salon berikut:\n"
    "- pendek: rambut tidak melewati bawah telinga / di atas bahu\n"
    "- pendek-menengah: ujung rambut sekitar bahu\n"
    "- menengah: ujung rambut antara bahu hingga tengah punggung\n"
    "- panjang: ujung rambut melewati tengah punggung\n\n"
    "Jawab HANYA dengan JSON: {\"label\": \"<salah satu kategori>\", \"confidence\": <0..1>}\n"
    "Tanpa penjelasan tambahan."
)


def frames_by_type(per_type: int) -> list[tuple[int, str]]:
    out = []
    for name, lo, hi in CLASSES:
        for f in range(lo, min(hi, lo + per_type - 1) + 1):
            out.append((f, name))
    return out


def load_image_bytes(z: zipfile.ZipFile, frame: int) -> bytes | None:
    cands = [n for n in z.namelist() if f"Frame{frame:05d}-org.jpg" in n]
    if not cands:
        return None
    return z.read(cands[0])


def parse_label(text: str) -> dict | None:
    text = (text or "").strip()
    import re

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None
    label = str(obj.get("label", "")).strip().lower()
    if label not in LENGTH_CLASSES:
        return None
    conf = obj.get("confidence")
    try:
        conf = float(conf)
    except Exception:
        conf = None
    return {"label": label, "confidence": conf}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-type", type=int, default=30)
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY tidak ditemukan di apps/ai/.env")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    z = zipfile.ZipFile(DATASET_ZIP)

    out_path = Path(args.out)
    existing: dict[str, dict] = {}
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8")).get("records", {})

    targets = frames_by_type(args.per_type)
    model_idx = 0
    cooldown: dict[str, float] = {}
    processed = 0
    skipped = 0
    failures = 0

    for frame, tipe in targets:
        fkey = f"{frame:05d}"
        if fkey in existing:
            skipped += 1
            continue

        img_bytes = load_image_bytes(z, frame)
        if img_bytes is None:
            failures += 1
            continue

        # kompres kecil agar cepat
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        im.thumbnail((512, 512))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
        part = types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")

        label = None
        for attempt in range(len(MODELS)):
            model = MODELS[(model_idx + attempt) % len(MODELS)]
            if cooldown.get(model, 0) > time.time():
                continue
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=[PROMPT, part],
                    config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=100),
                )
                parsed = parse_label(getattr(resp, "text", "") or "")
                if parsed:
                    parsed.update({"frame": frame, "tipe_asal": tipe, "model": model})
                    label = parsed
                    model_idx = (model_idx + attempt) % len(MODELS)
                    break
            except Exception as exc:
                msg = str(exc)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    wait = 120.0
                    import re as _re

                    m = _re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)", msg)
                    if m:
                        wait = max(float(m.group(1)), 60.0)
                    cooldown[model] = time.time() + wait
                continue

        if label:
            existing[fkey] = label
            processed += 1
            if processed % 5 == 0:
                _save(out_path, existing, targets)
                print(f"  +{processed} (frame {fkey}) last={label['label']} via {label.get('model')}")
        else:
            failures += 1
            # jika semua model cooldown, tunggu
            if all(cooldown.get(m, 0) > time.time() for m in MODELS):
                print("  semua model cooldown, menunggu 60s...")
                time.sleep(60)

    _save(out_path, existing, targets)
    z.close()

    dist: dict[str, dict[str, int]] = {t: {c: 0 for c in LENGTH_CLASSES} for t, _, _ in CLASSES}
    for rec in existing.values():
        dist[rec["tipe_asal"]][rec["label"]] += 1

    print(f"\nSelesai. processed={processed} skipped={skipped} failures={failures} total_labeled={len(existing)}")
    for t, d in dist.items():
        print(f"  {t:16s} " + " ".join(f"{c[:8]}={d[c]}" for c in LENGTH_CLASSES))
    print(f"JSON -> {out_path}")


def _save(path: Path, records: dict, targets: list) -> None:
    dist: dict[str, dict[str, int]] = {t: {c: 0 for c in LENGTH_CLASSES} for t, _, _ in CLASSES}
    for rec in records.values():
        dist[rec["tipe_asal"]][rec["label"]] += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "method": "gemini_vision",
                "length_classes": LENGTH_CLASSES,
                "target_frames": len(targets),
                "n_labeled": len(records),
                "distribution_per_type": dist,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
