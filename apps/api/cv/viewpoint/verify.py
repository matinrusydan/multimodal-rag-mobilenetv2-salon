# -*- coding: utf-8 -*-
"""viewpoint/verify.py — Verifikasi manusia (human-in-the-loop).

Anotator MEMVERIFIKASI tebakan gate: "Apakah benar? [Ya/Tidak/Ragu]".
Koreksi OPSIONAL. Tujuan: mengukur akurasi gate apa adanya (as-is).

Sampling cerdas: prioritaskan confidence rendah + menengah + random.

Output: viewpoint/ground_truth/viewpoint_verification_<annotator>.json

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\verify.py --annotator A --n 150
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.constants import CV_DIR, SEED, VIEWPOINT_CLASSES, VIEWPOINT_LABELS_ID
from common.io_utils import load_json, save_json

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground_truth"
REPORTS = HERE / "reports"
PRED_PATH = REPORTS / "viewpoint_predictions.json"


def smart_sample(records: list[dict], n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    preds = [r for r in records if r.get("predicted_viewpoint")]
    if not preds:
        return []
    low = sorted(preds, key=lambda r: r.get("confidence", 1.0))
    n_low, n_mid = int(n * 0.4), int(n * 0.3)
    n_rand = n - n_low - n_mid

    chosen, seen = [], set()
    for r in low[: n_low * 2]:
        if len(chosen) >= n_low:
            break
        chosen.append(r); seen.add(r["image_id"])
    rest = sorted([r for r in preds if r["image_id"] not in seen], key=lambda r: r.get("confidence", 1.0))
    for r in rng.sample(rest[: max(n_mid * 2, n_mid)], min(n_mid, len(rest))):
        if r["image_id"] not in seen:
            chosen.append(r); seen.add(r["image_id"])
    rest2 = [r for r in preds if r["image_id"] not in seen]
    for r in rng.sample(rest2, min(n_rand, len(rest2))):
        chosen.append(r); seen.add(r["image_id"])
    rng.shuffle(chosen)
    return chosen[:n]


class VerifyApp:
    def __init__(self, root: tk.Tk, annotator: str, records: list[dict]):
        self.root = root
        self.annotator = annotator
        self.records = records
        self.idx = 0
        self.results = self._load_existing()
        self.is_correct = tk.StringVar(value="")
        self.correction = tk.StringVar(value="")
        self._tk_img = None
        self._build_ui()
        self._load_current()
        self._bind_keys()

    def _out_path(self):
        return GT_DIR / f"viewpoint_verification_{self.annotator}.json"

    def _load_existing(self):
        p = self._out_path()
        if p.exists():
            try:
                return {r["image_id"]: r for r in load_json(p).get("records", [])}
            except Exception:
                return {}
        return {}

    def _save(self):
        GT_DIR.mkdir(parents=True, exist_ok=True)
        save_json(self._out_path(), {
            "annotator": self.annotator, "schema": "viewpoint_verification",
            "mode": "pengukuran", "updated_at": datetime.now(timezone.utc).isoformat(),
            "n": len(self.results), "records": list(self.results.values()),
        })

    def _build_ui(self):
        self.root.title(f"Verifikasi Viewpoint — Annotator {self.annotator}")
        self.root.geometry("1100x780")
        self.root.configure(bg="#f4f6f8")
        top = tk.Frame(self.root, bg="#f4f6f8"); top.pack(side="top", fill="x", padx=12, pady=8)
        self.progress = tk.Label(top, text="0 / 0", font=("Segoe UI", 13, "bold"), bg="#f4f6f8"); self.progress.pack(side="left")
        self.imgid = tk.Label(top, text="", font=("Segoe UI", 9), bg="#f4f6f8"); self.imgid.pack(side="right")
        body = tk.Frame(self.root, bg="#f4f6f8"); body.pack(fill="both", expand=True, padx=12, pady=4)
        self.canvas = tk.Label(body, bg="#d9dde1", text="Memuat..."); self.canvas.pack(side="left", fill="both", expand=True)
        panel = tk.Frame(body, bg="white", width=360); panel.pack(side="right", fill="y", padx=(12, 0)); panel.pack_propagate(False)
        tk.Label(panel, text="Tebakan Model", font=("Segoe UI", 11, "bold"), bg="white").pack(anchor="w", padx=12, pady=(12, 2))
        self.pred_label = tk.Label(panel, text="-", font=("Segoe UI", 18, "bold"), fg="#1565c0", bg="white"); self.pred_label.pack(anchor="w", padx=12)
        self.conf_label = tk.Label(panel, text="confidence: -", font=("Segoe UI", 9), bg="white", fg="#666"); self.conf_label.pack(anchor="w", padx=12)
        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=12, pady=8)
        tk.Label(panel, text="Apakah tebakan ini BENAR?", font=("Segoe UI", 11, "bold"), bg="white").pack(anchor="w", padx=12, pady=(6, 4))
        for label, val in [("Ya", "ya"), ("Tidak", "tidak"), ("Ragu-ragu", "ragu")]:
            tk.Button(panel, text=label, font=("Segoe UI", 10), width=28, command=lambda v=val: self._set_correct(v)).pack(anchor="w", padx=12, pady=2)
        self.correct_label = tk.Label(panel, text="", font=("Segoe UI", 9, "italic"), bg="white", fg="#2e7d32"); self.correct_label.pack(anchor="w", padx=12)
        tk.Label(panel, text="Koreksi (OPSIONAL)", font=("Segoe UI", 10, "bold"), bg="white").pack(anchor="w", padx=12, pady=(10, 2))
        self.corr_combo = ttk.Combobox(panel, state="readonly", width=26, values=["(tidak ada)"] + [VIEWPOINT_LABELS_ID[c] for c in VIEWPOINT_CLASSES])
        self.corr_combo.set("(tidak ada)"); self.corr_combo.pack(anchor="w", padx=12); self.corr_combo.bind("<<ComboboxSelected>>", self._on_corr)
        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=12, pady=10)
        tk.Button(panel, text="< Sebelumnya (←)", font=("Segoe UI", 10), command=self._prev).pack(anchor="w", padx=12, pady=2)
        tk.Button(panel, text="Simpan & Lanjut (Enter) >", font=("Segoe UI", 10, "bold"), bg="#c8e6c9", command=self._save_next).pack(anchor="w", padx=12, pady=2)
        guide = ("PANDUAN:\n• SAMPING: biasanya 1 lengan/bahu terlihat\n• Badan belakang + muka menoleh → BELAKANG\n• Rambut pendek (rahang/telinga/bahu) → BELAKANG\n• DEPAN: wajah menghadap kamera (mata+mulut)")
        tk.Label(panel, text=guide, font=("Segoe UI", 8), bg="#fff8e1", fg="#6d4c00", justify="left", wraplength=320, padx=6, pady=6).pack(anchor="w", padx=12, pady=(8, 12))

    def _bind_keys(self):
        self.root.bind("<Return>", lambda e: self._save_next())
        self.root.bind("<Left>", lambda e: self._prev())
        self.root.bind("<Right>", lambda e: self._save_next())
        self.root.bind("y", lambda e: self._set_correct("ya"))
        self.root.bind("t", lambda e: self._set_correct("tidak"))
        self.root.bind("r", lambda e: self._set_correct("ragu"))

    def _set_correct(self, v):
        self.is_correct.set(v); self.correct_label.config(text=f"Dipilih: {v.upper()}")

    def _on_corr(self, _e=None):
        label = self.corr_combo.get()
        for k, v in VIEWPOINT_LABELS_ID.items():
            if v == label:
                self.correction.set(k); return
        self.correction.set("")

    def _load_current(self):
        if self.idx >= len(self.records):
            messagebox.showinfo("Selesai", "Semua gambar terverifikasi!"); self.root.destroy(); return
        rec = self.records[self.idx]
        self.progress.config(text=f"{self.idx + 1} / {len(self.records)}")
        self.imgid.config(text=rec["image_id"])
        try:
            im = Image.open(CV_DIR / rec["relpath"])
            w, h = im.size
            aw, ah = max(self.canvas.winfo_width(), 640), max(self.canvas.winfo_height(), 480)
            s = min(aw / w, ah / h)
            im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.Resampling.LANCZOS)
            self._tk_img = ImageTk.PhotoImage(im); self.canvas.config(image=self._tk_img, text="")
        except Exception as exc:
            self.canvas.config(image="", text=f"Gagal: {exc}")
        pred = rec.get("predicted_viewpoint", "-")
        self.pred_label.config(text=VIEWPOINT_LABELS_ID.get(pred, pred))
        self.conf_label.config(text=f"confidence: {rec.get('confidence', '-')}")
        self.is_correct.set(""); self.correction.set(""); self.correct_label.config(text=""); self.corr_combo.set("(tidak ada)")
        ex = self.results.get(rec["image_id"])
        if ex:
            self.is_correct.set(ex.get("is_correct", "")); self.correct_label.config(text=f"Dipilih: {ex.get('is_correct','').upper()}")
            if ex.get("correction"):
                self.correction.set(ex["correction"]); self.corr_combo.set(VIEWPOINT_LABELS_ID.get(ex["correction"], "(tidak ada)"))

    def _save_next(self):
        rec = self.records[self.idx]
        if not self.is_correct.get():
            messagebox.showwarning("Belum dijawab", "Pilih: Ya / Tidak / Ragu-ragu."); return
        self.results[rec["image_id"]] = {
            "image_id": rec["image_id"], "model_prediction": rec.get("predicted_viewpoint"),
            "model_confidence": rec.get("confidence"), "is_correct": self.is_correct.get(),
            "correction": self.correction.get() or None, "annotator": self.annotator,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._save(); self.idx += 1; self._load_current()

    def _prev(self):
        if self.idx > 0:
            self.idx -= 1; self._load_current()

    def skip_to_first_unverified(self):
        for i, r in enumerate(self.records):
            if r["image_id"] not in self.results:
                self.idx = i; return
        self.idx = len(self.records) - 1


def main():
    ap = argparse.ArgumentParser(description="Verifikasi viewpoint (mode pengukuran).")
    ap.add_argument("--annotator", required=True)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--pred", default=str(PRED_PATH))
    args = ap.parse_args()

    pred_path = Path(args.pred)
    if not pred_path.exists():
        print(f"ERROR: prediksi belum ada: {pred_path}\nJalankan: python viewpoint/gate.py --source figaro --all")
        return
    records = load_json(pred_path).get("records", [])
    sampled = smart_sample(records, args.n, args.seed)
    print(f"Total: {len(records)} | disampling: {len(sampled)}")
    root = tk.Tk()
    app = VerifyApp(root, args.annotator, sampled)
    app.skip_to_first_unverified()
    root.update_idletasks(); app._load_current(); root.mainloop()


if __name__ == "__main__":
    main()
