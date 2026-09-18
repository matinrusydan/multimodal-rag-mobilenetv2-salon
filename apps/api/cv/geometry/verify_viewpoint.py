# -*- coding: utf-8 -*-
"""TAHAP 1 — Verifikasi Viewpoint (human-in-the-loop, MODE PENGUKURAN).

Filosofi:
  Model gate sudah memprediksi viewpoint (paksa pilih). Tugas anotator BUKAN
  melabeli dari nol, tetapi MEMVERIFIKASI tebakan model:
      "Apakah benar? [Ya / Tidak / Ragu]"
  Koreksi (jawaban "seharusnya apa") OPSIONAL.

  Tujuan utama = MENGUKUR seberapa akurat model bekerja SENDIRI (as-is),
  tanpa intervensi manusia. Ini baseline jujur. "Don't fix what you haven't
  measured."

Sampling cerdas: prioritaskan
  - confidence rendah (model ragu)
  - confidence menengah
  - random (acak, untuk cakupan)
agar beban anotator efisien tapi tetap representatif.

Output:
  geometry/ground_truth/viewpoint_verification.json
  (schema: image_id, model_prediction, is_correct: ya|tidak|ragu, correction: <kelas>|null)

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" -m geometry.verify_viewpoint --help
  & ".venv\\Scripts\\python.exe" geometry\\verify_viewpoint.py --annotator A --n 60

Butuh (opsional): predictions dari viewpoint_gate.py. Jika belum ada, tool
tetap berjalan (mode tanpa tebakan) — prediksi dikosongkan.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

BASE = Path(__file__).resolve().parents[1]          # apps/api/cv
GEO = Path(__file__).resolve().parents[0]
GT_DIR = GEO / "ground_truth"
REPORTS = GEO / "reports"
PRED_PATH = REPORTS / "viewpoint_predictions.json"

VIEWPOINT_CLASSES = ["depan", "samping", "belakang"]
T_VIEWPOINT = {
    "depan": "Depan",
    "samping": "Samping",
    "belakang": "Belakang",
}
SEED = 42


# ------------------------------------------------------------------
# Sampling cerdas
# ------------------------------------------------------------------
def smart_sample(records: list[dict], n: int, seed: int) -> list[dict]:
    """Prioritaskan confidence rendah + menengah + random."""
    rng = random.Random(seed)
    preds = [r for r in records if r.get("predicted_viewpoint")]
    if not preds:
        return []

    low = sorted(preds, key=lambda r: r.get("confidence", 1.0))  # confidence terendah dulu
    n_low = int(n * 0.4)
    n_mid = int(n * 0.3)
    n_rand = n - n_low - n_mid

    chosen: list[dict] = []
    seen = set()

    for r in low[: n_low * 2]:  # ambil lebih, lalu subset acak
        if len(chosen) >= n_low:
            break
        chosen.append(r)
        seen.add(r["image_id"])

    # tengah: acak dari setengah bawah sisanya
    rest = [r for r in preds if r["image_id"] not in seen]
    rest_sorted = sorted(rest, key=lambda r: r.get("confidence", 1.0))
    mid_pool = rest_sorted[: max(n_mid * 2, n_mid)]
    for r in rng.sample(mid_pool, min(n_mid, len(mid_pool))):
        if r["image_id"] not in seen:
            chosen.append(r)
            seen.add(r["image_id"])

    # random sisa
    rest2 = [r for r in preds if r["image_id"] not in seen]
    for r in rng.sample(rest2, min(n_rand, len(rest2))):
        chosen.append(r)
        seen.add(r["image_id"])

    rng.shuffle(chosen)
    return chosen[:n]


# ------------------------------------------------------------------
# GUI
# ------------------------------------------------------------------
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

    def _out_path(self) -> Path:
        return GT_DIR / f"viewpoint_verification_{self.annotator}.json"

    def _load_existing(self) -> dict:
        p = self._out_path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return {r["image_id"]: r for r in data.get("records", [])}
            except Exception:
                return {}
        return {}

    def _save(self):
        GT_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "annotator": self.annotator,
            "schema": "viewpoint_verification",
            "mode": "pengukuran",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "n": len(self.results),
            "records": list(self.results.values()),
        }
        self._out_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_ui(self):
        self.root.title(f"Verifikasi Viewpoint — Annotator {self.annotator} (pengukuran)")
        self.root.geometry("1100x780")
        self.root.configure(bg="#f4f6f8")

        # header
        top = tk.Frame(self.root, bg="#f4f6f8")
        top.pack(side="top", fill="x", padx=12, pady=8)
        self.progress = tk.Label(top, text="0 / 0", font=("Segoe UI", 13, "bold"), bg="#f4f6f8")
        self.progress.pack(side="left")
        self.imgid = tk.Label(top, text="", font=("Segoe UI", 9), bg="#f4f6f8")
        self.imgid.pack(side="right")

        # body: gambar kiri, panel kanan
        body = tk.Frame(self.root, bg="#f4f6f8")
        body.pack(fill="both", expand=True, padx=12, pady=4)
        self.canvas = tk.Label(body, bg="#d9dde1", text="Memuat...")
        self.canvas.pack(side="left", fill="both", expand=True)

        panel = tk.Frame(body, bg="white", width=360)
        panel.pack(side="right", fill="y", padx=(12, 0))
        panel.pack_propagate(False)

        # prediksi model
        tk.Label(panel, text="Tebakan Model", font=("Segoe UI", 11, "bold"), bg="white").pack(anchor="w", padx=12, pady=(12, 2))
        self.pred_label = tk.Label(panel, text="-", font=("Segoe UI", 18, "bold"), fg="#1565c0", bg="white")
        self.pred_label.pack(anchor="w", padx=12)
        self.conf_label = tk.Label(panel, text="confidence: -", font=("Segoe UI", 9), bg="white", fg="#666")
        self.conf_label.pack(anchor="w", padx=12)
        self.scores_label = tk.Label(panel, text="", font=("Consolas", 8), bg="white", fg="#666", justify="left")
        self.scores_label.pack(anchor="w", padx=12, pady=(2, 8))

        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=12)

        # pertanyaan
        tk.Label(panel, text="Apakah tebakan ini BENAR?", font=("Segoe UI", 11, "bold"), bg="white").pack(anchor="w", padx=12, pady=(10, 4))
        for label, val in [("Ya", "ya"), ("Tidak", "tidak"), ("Ragu-ragu", "ragu")]:
            tk.Button(panel, text=label, font=("Segoe UI", 10), width=28,
                      command=lambda v=val: self._set_correct(v)).pack(anchor="w", padx=12, pady=2)
        self.correct_label = tk.Label(panel, text="", font=("Segoe UI", 9, "italic"), bg="white", fg="#2e7d32")
        self.correct_label.pack(anchor="w", padx=12)

        # koreksi opsional
        tk.Label(panel, text="Koreksi (OPSIONAL — seharusnya apa?)", font=("Segoe UI", 10, "bold"), bg="white").pack(anchor="w", padx=12, pady=(12, 2))
        self.corr_combo = ttk.Combobox(panel, state="readonly", width=26,
                                       values=["(tidak ada)"] + [T_VIEWPOINT[c] for c in VIEWPOINT_CLASSES])
        self.corr_combo.set("(tidak ada)")
        self.corr_combo.pack(anchor="w", padx=12)
        self.corr_combo.bind("<<ComboboxSelected>>", self._on_corr)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", padx=12, pady=12)

        # nav
        tk.Button(panel, text="< Sebelumnya (←)", font=("Segoe UI", 10),
                  command=self._prev).pack(anchor="w", padx=12, pady=2)
        tk.Button(panel, text="Simpan & Lanjut (Enter) >", font=("Segoe UI", 10, "bold"),
                  bg="#c8e6c9", command=self._save_next).pack(anchor="w", padx=12, pady=2)

        tk.Label(panel, text="Tips: jawab 'Ragu' jika memang ambigu.\nKoreksi tidak wajib diisi.",
                 font=("Segoe UI", 8), bg="white", fg="#888", justify="left").pack(anchor="w", padx=12, pady=(10, 0))

        # Panduan kasus khusus
        guide = (
            "PANDUAN KASUS KHUSUS:\n"
            "• SAMPING: biasanya hanya 1 lengan/bahu terlihat.\n"
            "• Badan belakang tapi MUKA MENOLEH → tetap BELAKANG.\n"
            "• Rambut pendek (cowok/cewe) yang memperlihatkan\n"
            "  rahang/telinga/bahu → tetap BELAKANG (bukan depan),\n"
            "  selama tidak terlihat wajah frontal (2 mata+mulut).\n"
            "• DEPAN: hanya jika wajah menghadap kamera (mata+mulut\n"
            "  terlihat frontal)."
        )
        tk.Label(panel, text=guide, font=("Segoe UI", 8), bg="#fff8e1", fg="#6d4c00",
                 justify="left", wraplength=320, padx=6, pady=6).pack(anchor="w", padx=12, pady=(8, 12))

    def _bind_keys(self):
        self.root.bind("<Return>", lambda e: self._save_next())
        self.root.bind("<Left>", lambda e: self._prev())
        self.root.bind("<Right>", lambda e: self._save_next())
        self.root.bind("y", lambda e: self._set_correct("ya"))
        self.root.bind("t", lambda e: self._set_correct("tidak"))
        self.root.bind("r", lambda e: self._set_correct("ragu"))

    def _set_correct(self, v):
        self.is_correct.set(v)
        self.correct_label.config(text=f"Dipilih: {v.upper()}")

    def _on_corr(self, _e=None):
        label = self.corr_combo.get()
        for k, v in T_VIEWPOINT.items():
            if v == label:
                self.correction.set(k)
                return
        self.correction.set("")

    def _load_current(self):
        if self.idx >= len(self.records):
            messagebox.showinfo("Selesai", "Semua gambar terverifikasi!")
            self.root.destroy()
            return
        rec = self.records[self.idx]
        self.progress.config(text=f"{self.idx + 1} / {len(self.records)}")
        self.imgid.config(text=rec["image_id"])

        # gambar
        p = BASE / rec["relpath"]
        try:
            im = Image.open(p)
            w, h = im.size
            aw, ah = max(self.canvas.winfo_width(), 640), max(self.canvas.winfo_height(), 480)
            s = min(aw / w, ah / h)
            im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.Resampling.LANCZOS)
            self._tk_img = ImageTk.PhotoImage(im)
            self.canvas.config(image=self._tk_img, text="")
        except Exception as exc:
            self.canvas.config(image="", text=f"Gagal: {exc}")

        # prediksi
        pred = rec.get("predicted_viewpoint", "-")
        self.pred_label.config(text=T_VIEWPOINT.get(pred, pred))
        self.conf_label.config(text=f"confidence: {rec.get('confidence', '-')}")
        sc = rec.get("decision_detail", {}).get("scores", {})
        self.scores_label.config(text="\n".join(f"{k}={v}" for k, v in sc.items()) if sc else "")

        # reset jawaban (atau muat yang sudah ada)
        self.is_correct.set("")
        self.correction.set("")
        self.correct_label.config(text="")
        self.corr_combo.set("(tidak ada)")
        existing = self.results.get(rec["image_id"])
        if existing:
            self.is_correct.set(existing.get("is_correct", ""))
            self.correct_label.config(text=f"Dipilih: {existing.get('is_correct','').upper()}")
            corr = existing.get("correction")
            if corr:
                self.correction.set(corr)
                self.corr_combo.set(T_VIEWPOINT.get(corr, "(tidak ada)"))

    def _save_next(self):
        rec = self.records[self.idx]
        if not self.is_correct.get():
            messagebox.showwarning("Belum dijawab", "Pilih dulu: Ya / Tidak / Ragu-ragu.")
            return
        self.results[rec["image_id"]] = {
            "image_id": rec["image_id"],
            "model_prediction": rec.get("predicted_viewpoint"),
            "model_confidence": rec.get("confidence"),
            "is_correct": self.is_correct.get(),
            "correction": self.correction.get() or None,
            "annotator": self.annotator,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._save()
        self.idx += 1
        self._load_current()

    def _prev(self):
        if self.idx > 0:
            self.idx -= 1
            self._load_current()

    def skip_to_first_unverified(self):
        for i, r in enumerate(self.records):
            if r["image_id"] not in self.results:
                self.idx = i
                return
        self.idx = len(self.records) - 1


def main():
    ap = argparse.ArgumentParser(description="Verifikasi viewpoint (human-in-the-loop, mode pengukuran).")
    ap.add_argument("--annotator", required=True, help="ID annotator (mis. A, B)")
    ap.add_argument("--n", type=int, default=60, help="Jumlah sampel (sampling cerdas)")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--pred", default=str(PRED_PATH), help="File prediksi dari viewpoint_gate.py")
    args = ap.parse_args()

    pred_path = Path(args.pred)
    if not pred_path.exists():
        print(f"ERROR: file prediksi belum ada: {pred_path}")
        print("Jalankan dulu: python geometry/viewpoint_gate.py --source figaro --all")
        return

    data = json.loads(pred_path.read_text(encoding="utf-8"))
    records = data.get("records", [])
    sampled = smart_sample(records, args.n, args.seed)
    print(f"Total prediksi: {len(records)} | disampling: {len(sampled)}")

    root = tk.Tk()
    app = VerifyApp(root, args.annotator, sampled)
    app.skip_to_first_unverified()
    root.update_idletasks()
    app._load_current()
    root.mainloop()


if __name__ == "__main__":
    main()
