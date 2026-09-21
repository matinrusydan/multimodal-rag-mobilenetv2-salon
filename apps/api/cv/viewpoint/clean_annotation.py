# -*- coding: utf-8 -*-
"""viewpoint/clean_annotation.py — Tool GUI anotasi cleaning dataset harvested.

Anotator melihat setiap gambar harvest dan memutuskan: KEEP atau BUANG.
- KEEP  : gambar layak dipakai (back-view rambut)
- BUANG : non-rambut / objek / salah sudut / blur / tidak layak

Tidak menghapus file asli. Menyimpan keputusan ke JSON. Setelah selesai,
script `apply_clean.py` (atau flag) menyalin file KEEP ke folder bersih MANUAL.

Sampling: default review SEMUA gambar di folder harvest (atau subset).

Output: viewpoint/ground_truth/clean_annotation_<annotator>.json
  {gambar, keputusan: keep|delete, alasan, waktu}

Usage (from apps/api/cv):
  & ".venv\\Scripts\\python.exe" viewpoint\\clean_annotation.py --annotator A
  & ".venv\\Scripts\\python.exe" viewpoint\\clean_annotation.py --annotator A --source openverse
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.io_utils import save_json

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground_truth"

# Sumber harvest (apps/ai/app/crawler/harvest)
HARVEST = HERE.parents[2] / "ai" / "app" / "crawler" / "harvest"
SRC_DIRS = ["back_view", "openverse", "huggingface", "back_view_clean"]

# Alasan buang (opsional)
REASONS = ["", "bukan_rambut", "bukan_orang", "depan_samping", "blur", "objek", "duplikat", "lainnya"]


def collect_images(sources: list[str]) -> list[dict]:
    items = []
    for d in sources:
        dd = HARVEST / d
        if not dd.exists():
            continue
        for f in sorted(dd.glob("*.jpg")):
            items.append({"path": str(f), "source": d, "name": f.name})
        for f in sorted(dd.glob("*.png")):
            items.append({"path": str(f), "source": d, "name": f.name})
    return items


class CleanApp:
    def __init__(self, root: tk.Tk, annotator: str, items: list[dict]):
        self.root = root
        self.annotator = annotator
        self.items = items
        self.idx = 0
        self.decisions = self._load_existing()
        self._tk_img = None
        self._build_ui()
        self._load_current()
        self._bind_keys()

    def _out_path(self):
        return GT_DIR / f"clean_annotation_{self.annotator}.json"

    def _load_existing(self):
        p = self._out_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8")).get("records", {})
            except Exception:
                return {}
        return {}

    def _save(self):
        GT_DIR.mkdir(parents=True, exist_ok=True)
        save_json(self._out_path(), {
            "annotator": self.annotator, "schema": "clean_annotation_v1",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "n": len(self.decisions), "records": self.decisions,
        })

    def _build_ui(self):
        self.root.title(f"Cleaning Dataset — Annotator {self.annotator}")
        self.root.geometry("1100x800")
        self.root.configure(bg="#f4f6f8")

        top = tk.Frame(self.root, bg="#f4f6f8"); top.pack(fill="x", padx=12, pady=8)
        self.progress = tk.Label(top, text="0 / 0", font=("Segoe UI", 13, "bold"), bg="#f4f6f8"); self.progress.pack(side="left")
        self.stats = tk.Label(top, text="", font=("Segoe UI", 10), bg="#f4f6f8"); self.stats.pack(side="right")

        body = tk.Frame(self.root, bg="#f4f6f8"); body.pack(fill="both", expand=True, padx=12, pady=4)
        self.canvas = tk.Label(body, bg="#d9dde1", text="Memuat..."); self.canvas.pack(side="left", fill="both", expand=True)

        panel = tk.Frame(body, bg="white", width=340); panel.pack(side="right", fill="y", padx=(12, 0)); panel.pack_propagate(False)
        self.name_label = tk.Label(panel, text="-", font=("Segoe UI", 10, "bold"), bg="white", wraplength=310, justify="left")
        self.name_label.pack(anchor="w", padx=12, pady=(12, 4))
        self.src_label = tk.Label(panel, text="", font=("Segoe UI", 9), bg="white", fg="#666"); self.src_label.pack(anchor="w", padx=12)

        tk.Label(panel, text="Keputusan (untuk dataset bersih):", font=("Segoe UI", 11, "bold"), bg="white").pack(anchor="w", padx=12, pady=(14, 6))
        self.btn_keep = tk.Button(panel, text="✓ KEEP (K) — layak dipakai", font=("Segoe UI", 11, "bold"),
                                  bg="#c8e6c9", command=self._keep).pack(fill="x", padx=12, pady=3)
        self.btn_del = tk.Button(panel, text="✗ BUANG (H) — tidak dipakai", font=("Segoe UI", 11, "bold"),
                                 bg="#ffcdd2", command=self._delete).pack(fill="x", padx=12, pady=3)

        tk.Label(panel, text="Alasan buang (opsional):", font=("Segoe UI", 9), bg="white").pack(anchor="w", padx=12, pady=(10, 2))
        self.reason = tk.StringVar(value="")
        from tkinter import ttk
        ttk.Combobox(panel, textvariable=self.reason, values=REASONS, state="readonly").pack(fill="x", padx=12)

        tk.Frame(panel, bg="#eee", height=1).pack(fill="x", padx=12, pady=12)
        tk.Button(panel, text="< Sebelumnya (←)", command=self._prev).pack(anchor="w", padx=12, pady=2)
        tk.Button(panel, text="Selesai / Simpan", command=self._finish).pack(anchor="w", padx=12, pady=2)

        tk.Label(panel, text=("PANDUAN:\n• KEEP jika: foto orang dari BELAKANG, rambut jelas,\n"
                              "  tidak blur, bukan objek/hewan/makanan.\n"
                              "• BUANG jika: bukan rambut, bukan orang, depan/samping,\n"
                              "  graphic/diagram, objek (kursi/roti/dll), blur berat.\n"
                              "• Fokus: foto back-view rambut manusia."),
                 font=("Segoe UI", 8), bg="#fff8e1", fg="#6d4c00", justify="left", wraplength=300, padx=6, pady=6).pack(anchor="w", padx=12, pady=(14, 12))

    def _bind_keys(self):
        self.root.bind("k", lambda e: self._keep())
        self.root.bind("h", lambda e: self._delete())
        self.root.bind("<Left>", lambda e: self._prev())
        self.root.bind("<Right>", lambda e: self._next())

    def _load_current(self):
        if self.idx >= len(self.items):
            messagebox.showinfo("Selesai", "Semua gambar sudah dianotasi!"); self.root.destroy(); return
        it = self.items[self.idx]
        self.progress.config(text=f"{self.idx + 1} / {len(self.items)}")
        k = sum(1 for v in self.decisions.values() if v["decision"] == "keep")
        d = sum(1 for v in self.decisions.values() if v["decision"] == "delete")
        self.stats.config(text=f"KEEP: {k} | BUANG: {d}")
        self.name_label.config(text=it["name"])
        self.src_label.config(text=f"sumber: {it['source']}")
        try:
            im = Image.open(it["path"])
            w, h = im.size
            aw, ah = max(self.canvas.winfo_width(), 640), max(self.canvas.winfo_height(), 500)
            s = min(aw / w, ah / h)
            im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.Resampling.LANCZOS)
            self._tk_img = ImageTk.PhotoImage(im); self.canvas.config(image=self._tk_img, text="")
        except Exception as exc:
            self.canvas.config(image="", text=f"Gagal: {exc}")
        # pra-isi keputusan lama
        old = self.decisions.get(it["path"])
        self.reason.set(old.get("reason", "") if old else "")

    def _record(self, decision: str):
        it = self.items[self.idx]
        self.decisions[it["path"]] = {
            "path": it["path"], "name": it["name"], "source": it["source"],
            "decision": decision, "reason": self.reason.get() or None,
            "annotator": self.annotator, "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def _keep(self):
        self._record("keep"); self._next()

    def _delete(self):
        self._record("delete"); self._next()

    def _next(self):
        if self.idx < len(self.items) - 1:
            self.idx += 1; self._load_current()

    def _prev(self):
        if self.idx > 0:
            self.idx -= 1; self._load_current()

    def _finish(self):
        self._save()
        k = sum(1 for v in self.decisions.values() if v["decision"] == "keep")
        d = sum(1 for v in self.decisions.values() if v["decision"] == "delete")
        messagebox.showinfo("Tersimpan", f"Selesai. KEEP: {k} | BUANG: {d}\n-> {self._out_path()}")
        self.root.destroy()

    def skip_to_first_undecided(self):
        for i, it in enumerate(self.items):
            if it["path"] not in self.decisions:
                self.idx = i; return
        self.idx = len(self.items) - 1


def main():
    ap = argparse.ArgumentParser(description="Anotasi cleaning dataset harvested (KEEP/BUANG).")
    ap.add_argument("--annotator", required=True)
    ap.add_argument("--source", nargs="*", default=SRC_DIRS, help="Folder sumber (default semua)")
    ap.add_argument("--max", type=int, default=0, help="Batasi jumlah (0=semua)")
    args = ap.parse_args()

    items = collect_images(args.source)
    if args.max > 0:
        items = items[: args.max]
    if not items:
        print("ERROR: tidak ada gambar. Cek folder harvest.")
        return
    print(f"Total gambar: {len(items)}")

    root = tk.Tk()
    app = CleanApp(root, args.annotator, items)
    app.skip_to_first_undecided()
    root.update_idletasks(); app._load_current(); root.mainloop()


if __name__ == "__main__":
    main()
