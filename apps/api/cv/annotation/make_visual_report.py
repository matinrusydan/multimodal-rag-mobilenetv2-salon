# -*- coding: utf-8 -*-
"""Visual report: contact sheet untuk analisis kualitatif agreement/disagreement A vs B.

Menghasilkan:
  1. Contact sheet per kelas length (straight/wavy) — contoh gambar + label A/B
  2. Contact sheet per kelas volume (curly/kinky) — PROVISIONAL
  3. Contact sheet per pasangan disagreement (A vs B)
  4. Contact sheet per kelas hair type
  5. Ringkasan teks (markdown)

Gambar diambil dari dataset/figaro1k/. Semua output di annotation/reports/figures/.

TIDAK mengubah data anotasi. Read-only terhadap ground truth.

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" annotation\\make_visual_report.py
  & ".venv\\Scripts\\python.exe" annotation\\make_visual_report.py --per-sheet 9
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
from PIL import Image

BASE = Path(__file__).resolve().parents[1]
GT_DIR = BASE / "annotation" / "ground_truth"
FIG_DIR = BASE / "annotation" / "reports" / "figures"

T_LENGTH = {"short": "Pendek", "shoulder": "Sekitar Bahu", "mid_back": "Punggung Tengah", "long": "Panjang"}
T_VOLUME = {"low": "Tipis", "medium": "Sedang", "high": "Tebal"}
T_HAIRTYPE = {"straight": "Lurus", "wavy": "Bergelombang", "curly": "Keriting", "kinky": "Kribo"}


def load_annotations(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["image_id"]: r for r in data}


def value_of(rec: dict) -> str:
    if rec.get("ungradable"):
        return "TIDAK DINILAI"
    x = (rec.get("conditional_attribute") or {}).get("value")
    return x if x else "KOSONG"


def img_path(image_id: str) -> Path:
    # image_id: figaro1k/lurus/00029.jpg -> dataset/figaro1k/lurus/00029.jpg
    rel = image_id.replace("figaro1k/", "dataset/figaro1k/")
    return BASE / rel


def draw_contact_sheet(items: list[dict], title: str, out_path: Path, cols: int = 3) -> None:
    """items: list of dict {image_id, caption (multi-line)}."""
    if not items:
        # tetap buat gambar kosong dengan pesan
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, f"(tidak ada contoh)\n{title}", ha="center", va="center", fontsize=12)
        ax.axis("off")
        fig.savefig(out_path, dpi=110, bbox_inches="tight")
        plt.close(fig)
        return

    n = len(items)
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.2, rows * 3.6))
    if rows == 1 and cols == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]
    elif cols == 1:
        axes = [[a] for a in axes]

    for idx in range(rows * cols):
        r, c = divmod(idx, cols)
        ax = axes[r][c]
        if idx >= n:
            ax.axis("off")
            continue
        item = items[idx]
        p = img_path(item["image_id"])
        try:
            im = Image.open(p).convert("RGB")
            w, h = im.size
            scale = 320 / max(w, h)
            if scale < 1:
                im = im.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            ax.imshow(im)
        except Exception as exc:
            ax.text(0.5, 0.5, f"gagal muat\n{exc}", ha="center", va="center", fontsize=8)
        ax.set_title(item["caption"], fontsize=8)
        ax.axis("off")

    fig.suptitle(title, fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Visual report contact sheet (A vs B).")
    ap.add_argument("--per-sheet", type=int, default=9, help="Max gambar per sheet (default: 9)")
    ap.add_argument("--max-sheets-per-pair", type=int, default=1, help="Max sheet per pasangan (default: 1)")
    args = ap.parse_args()

    FIG_DIR.mkdir(parents=True, exist_ok=True)

    A = load_annotations(GT_DIR / "annotator_A.json")
    B = load_annotations(GT_DIR / "annotator_B.json")

    summary_lines = ["# Visual Report — Anotasi A vs B", ""]
    common = sorted(set(A) & set(B))
    summary_lines.append(f"Total gambar dianotasi dua annotator: {len(common)}")
    summary_lines.append("")

    # ---------- 1. Hair type per kelas ----------
    summary_lines.append("## 1. Contoh per Kelas Hair Type (label A)")
    for ht in ("straight", "wavy", "curly", "kinky"):
        items = []
        for iid in common:
            if A[iid].get("hair_type") != ht:
                continue
            cap = f"{iid.rsplit('/',2)[-2]}/{iid.rsplit('/',1)[-1]}\nA: {T_HAIRTYPE.get(A[iid].get('hair_type'),'?')} | B: {T_HAIRTYPE.get(B[iid].get('hair_type'),'?')}"
            items.append({"image_id": iid, "caption": cap})
            if len(items) >= args.per_sheet:
                break
        out = FIG_DIR / f"hairtype_{ht}.png"
        draw_contact_sheet(items, f"Hair Type: {T_HAIRTYPE.get(ht, ht)} (label A)", out)
        summary_lines.append(f"- `figures/hairtype_{ht}.png` ({len(items)} contoh)")

    # ---------- 2. Length per kelas (straight/wavy) ----------
    summary_lines.append("")
    summary_lines.append("## 2. Contoh per Kelas LENGTH (straight/wavy)")
    length_ids = [iid for iid in common if ("/lurus/" in iid or "/bergelombang/" in iid)]
    for cls in ("short", "shoulder", "mid_back", "long"):
        items = []
        for iid in length_ids:
            if value_of(A[iid]) == cls or value_of(B[iid]) == cls:
                va = T_LENGTH.get(value_of(A[iid]), value_of(A[iid]))
                vb = T_LENGTH.get(value_of(B[iid]), value_of(B[iid]))
                cap = f"{iid.rsplit('/',2)[-2]}/{iid.rsplit('/',1)[-1]}\nA: {va}\nB: {vb}"
                items.append({"image_id": iid, "caption": cap})
                if len(items) >= args.per_sheet:
                    break
        out = FIG_DIR / f"length_{cls}.png"
        draw_contact_sheet(items, f"Length: {T_LENGTH[cls]}", out)
        summary_lines.append(f"- `figures/length_{cls}.png` ({len(items)} contoh)")

    # ---------- 3. Volume per kelas (curly/kinky) ----------
    summary_lines.append("")
    summary_lines.append("## 3. Contoh per Kelas VOLUME (curly/kinky) [PROVISIONAL]")
    vol_ids = [iid for iid in common if ("/keriting/" in iid or "/sangat-keriting/" in iid)]
    for cls in ("low", "medium", "high"):
        items = []
        for iid in vol_ids:
            if value_of(A[iid]) == cls or value_of(B[iid]) == cls:
                va = T_VOLUME.get(value_of(A[iid]), value_of(A[iid]))
                vb = T_VOLUME.get(value_of(B[iid]), value_of(B[iid]))
                cap = f"{iid.rsplit('/',2)[-2]}/{iid.rsplit('/',1)[-1]}\nA: {va}\nB: {vb}"
                items.append({"image_id": iid, "caption": cap})
                if len(items) >= args.per_sheet:
                    break
        out = FIG_DIR / f"volume_{cls}.png"
        draw_contact_sheet(items, f"Volume: {T_VOLUME[cls]} [PROVISIONAL]", out)
        summary_lines.append(f"- `figures/volume_{cls}.png` ({len(items)} contoh)")

    # ---------- 4. Disagreement pairs ----------
    summary_lines.append("")
    summary_lines.append("## 4. Pasangan Disagreement (A vs B)")
    pairs = defaultdict(list)
    for iid in common:
        va, vb = value_of(A[iid]), value_of(B[iid])
        if va != vb:
            key = "|".join(sorted([va, vb]))
            pairs[key].append(iid)

    pair_summary = {k: len(v) for k, v in sorted(pairs.items(), key=lambda kv: -len(kv[1]))}
    summary_lines.append(f"Total disagreement: {sum(pair_summary.values())}")
    summary_lines.append("")
    summary_lines.append("| Pasangan (A|B) | Jumlah |")
    summary_lines.append("|---|---|")
    for k, v in pair_summary.items():
        summary_lines.append(f"| {k} | {v} |")

    for key, ids in sorted(pairs.items(), key=lambda kv: -len(kv[1])):
        sheet = 0
        for start in range(0, len(ids), args.per_sheet):
            if sheet >= args.max_sheets_per_pair:
                break
            chunk = ids[start:start + args.per_sheet]
            items = []
            for iid in chunk:
                cap = f"{iid.rsplit('/',2)[-2]}/{iid.rsplit('/',1)[-1]}\nA: {value_of(A[iid])}\nB: {value_of(B[iid])}"
                items.append({"image_id": iid, "caption": cap})
            safe = key.replace("|", "_vs_").replace(" ", "")
            out = FIG_DIR / f"disagree_{safe}_{sheet}.png"
            draw_contact_sheet(items, f"Disagreement: {key} (n={len(ids)})", out)
            summary_lines.append(f"- `figures/disagree_{safe}_{sheet}.png`")
            sheet += 1

    # tulis ringkasan markdown
    md_path = FIG_DIR / "VISUAL_REPORT.md"
    md_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print("=== Visual report selesai ===")
    print(f"Total disagreement: {sum(pair_summary.values())}")
    for k, v in pair_summary.items():
        print(f"  {k}: {v}")
    print(f"\nFigur -> {FIG_DIR}")
    print(f"Ringkasan -> {md_path}")


if __name__ == "__main__":
    main()
