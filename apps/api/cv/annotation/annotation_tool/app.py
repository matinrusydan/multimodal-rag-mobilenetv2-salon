# -*- coding: utf-8 -*-
"""Tkinter annotation tool - Hierarchical Hair Classification (pilot v1).

Perbaikan UI v2:
  - Layout grid yang rapi (tidak ada tombol tertutup)
  - Panel kontrol di kanan (scrollable)
  - Tombol pilihan ter-highlight saat aktif
  - Gambar menyesuaikan area tersedia
  - Bahasa Indonesia

Fitur:
  - Viewpoint, Hair Type, Conditional Attribute (dinamis)
  - Ungradable + alasan
  - Confidence, Visibility, Notes
  - Keyboard shortcuts
  - Auto-save + resume
  - Mode annotator independen (--annotator A|B)
  - TIDAK menampilkan pseudo-label/prediksi model/label annotator lain

Usage:
  python -m annotation.annotation_tool.runner --annotator A
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

BASE = Path(__file__).resolve().parents[2]  # apps/api/cv
DEFAULT_MANIFEST_PATH = BASE / "annotation" / "ground_truth" / "pilot_manifest.json"
GT_DIR = BASE / "annotation" / "ground_truth"

# --- Nilai internal (label) ---
HAIR_TYPES = ["straight", "wavy", "curly", "kinky"]
LENGTH_CLASSES = ["short", "shoulder", "mid_back", "long"]
VOLUME_CLASSES = ["low", "medium", "high"]
VIEWPOINTS = ["back", "back_left", "back_right", "side", "front", "unknown"]

# Alasan ungradable v3: dipisah lebih jelas
#   invalid_viewpoint      -> sudut foto tidak valid (butuh sub-posisi)
#   occluded_object        -> terhalang barang/benda/aksesori
#   occluded_tied          -> terhalang karena rambut diikat/dikuncir
#   insufficient_visibility-> ujung/massa tidak terlihat
#   ambiguous              -> benar-benar tidak bisa diputuskan
#   other                  -> lainnya
UNGRADABLE_REASONS = [
    "",
    "invalid_viewpoint",
    "occluded_object",
    "occluded_tied",
    "insufficient_visibility",
    "ambiguous",
    "other",
]

# Sub-opsi untuk invalid_viewpoint: berasal dari mana orangnya?
VIEWPOINT_SUBNOTE = [
    "",
    "from_front",
    "from_side",
    "from_behind_unclear",
    "other_angle",
]

CONFIDENCE_LEVELS = ["high", "medium", "low"]
VISIBILITY_FIELDS = ["hair_ends", "shoulder", "upper_back", "mid_back"]

# --- Terjemahan tampilan (Indonesia) ---
T_HAIR_TYPE = {
    "straight": "Lurus",
    "wavy": "Bergelombang",
    "curly": "Keriting",
    "kinky": "Kribo",
}
T_LENGTH = {
    "short": "Pendek",
    "shoulder": "Sekitar Bahu",
    "mid_back": "Punggung Tengah",
    "long": "Panjang",
}
T_VOLUME = {
    "low": "Tipis",
    "medium": "Sedang",
    "high": "Tebal",
}
T_VIEWPOINT = {
    "back": "Belakang",
    "back_left": "Belakang Kiri",
    "back_right": "Belakang Kanan",
    "side": "Samping",
    "front": "Depan",
    "unknown": "Tidak Jelas",
}
T_REASON = {
    "": "(tidak ada)",
    "invalid_viewpoint": "Sudut tidak valid (salah posisi kamera/orang)",
    "occluded_object": "Terhalang barang/benda",
    "occluded_tied": "Terhalang ikatan rambut (diikat/dikuncir)",
    "insufficient_visibility": "Ujung/massa tidak terlihat",
    "ambiguous": "Ambigu",
    "other": "Lainnya",
}
T_VIEWPOINT_SUBNOTE = {
    "": "(pilih posisi)",
    "from_front": "Foto dari depan",
    "from_side": "Foto dari samping",
    "from_behind_unclear": "Dari belakang tapi tidak jelas",
    "other_angle": "Sudut/posisi lain",
}
T_CONFIDENCE = {
    "high": "Yakin",
    "medium": "Cukup",
    "low": "Ragu",
}
T_VISIBILITY = {
    "hair_ends": "Ujung rambut",
    "shoulder": "Bahu",
    "upper_back": "Punggung atas",
    "mid_back": "Punggung tengah",
}

TAXONOMY_VERSION = "pilot-v3"
GUIDELINE_VERSION = "pilot-v3"

# Warna
C_BG = "#f4f6f8"
C_PANEL = "#ffffff"
C_ACTIVE = "#2e7d32"      # hijau
C_ACTIVE_FG = "#ffffff"
C_INACTIVE = "#e0e0e0"
C_INACTIVE_FG = "#212121"
C_DANGER = "#c62828"
C_ACCENT = "#1565c0"


class AnnotationApp:
    def __init__(self, root: tk.Tk, annotator: str, manifest_path: Path | None = None) -> None:
        self.root = root
        self.annotator = annotator
        self.manifest_path = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST_PATH
        self.manifest = self._load_manifest()
        self.images = self.manifest["images"]
        self.current_idx = 0
        self.annotations = self._load_existing()

        # State
        self.viewpoint = tk.StringVar(value="back")
        self.hair_type = tk.StringVar(value="")
        self.conditional_value = tk.StringVar(value="")
        self.ungradable = tk.BooleanVar(value=False)
        self.ungradable_reason = tk.StringVar(value="")
        self.viewpoint_subnote = tk.StringVar(value="")
        self.confidence = tk.StringVar(value="medium")
        self.vis_vars = {f: tk.BooleanVar(value=False) for f in VISIBILITY_FIELDS}

        # Referensi tombol untuk highlight
        self._btn_viewpoint: dict[str, ttk.Button] = {}
        self._btn_hairtype: dict[str, ttk.Button] = {}
        self._btn_conditional: dict[str, ttk.Button] = {}
        self._btn_confidence: dict[str, ttk.Button] = {}
        self._attr_name = None
        self._current_img_wh = (0, 0)
        self._tk_img = None
        self._notes_widget = None
        self._cond_title = None

        self._build_ui()
        self._load_current_image()
        self._bind_keys()

    # ---------------- File I/O ----------------
    def _load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                f"Manifest tidak ditemukan: {self.manifest_path}\n"
                f"Jalankan dulu: python annotation/sample_pilot.py"
            )
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _output_path(self) -> Path:
        # Jika manifest bukan default (mis. pilot_manifest_240.json), beri suffix agar
        # tidak menimpa anotasi pilot lama.
        stem = self.manifest_path.stem  # pilot_manifest atau pilot_manifest_240
        if stem == "pilot_manifest":
            return GT_DIR / f"annotator_{self.annotator}.json"
        tag = stem.replace("pilot_manifest_", "")
        return GT_DIR / f"annotator_{self.annotator}_p{tag}.json"

    def _load_existing(self) -> dict:
        path = self._output_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {rec["image_id"]: rec for rec in data}
        except Exception as exc:
            print(f"PERINGATAN: gagal memuat anotasi lama: {exc}")
            return {}

    def _save_annotations(self) -> None:
        path = self._output_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        records = list(self.annotations.values())
        path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---------------- UI ----------------
    def _style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=C_BG)
        style.configure("Panel.TFrame", background=C_PANEL)
        style.configure("TLabel", background=C_BG, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=C_PANEL, font=("Segoe UI", 10))
        style.configure("Head.TLabel", background=C_PANEL, font=("Segoe UI", 11, "bold"))
        style.configure("Title.TLabel", background=C_BG, font=("Segoe UI", 13, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("Nav.TButton", font=("Segoe UI", 11, "bold"), padding=8)
        style.configure("Save.TButton", font=("Segoe UI", 11, "bold"), padding=8)
        style.configure(
            "Active.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=6,
            background=C_ACTIVE,
            foreground=C_ACTIVE_FG,
        )
        style.map(
            "Active.TButton",
            background=[("active", C_ACTIVE)],
            foreground=[("active", C_ACTIVE_FG)],
        )

    def _build_ui(self) -> None:
        self._style()
        self.root.title(f"Anotasi Rambut - Annotator {self.annotator} ({TAXONOMY_VERSION}) - {self.manifest_path.name}")
        self.root.geometry("1180x760")
        self.root.minsize(980, 640)
        self.root.configure(bg=C_BG)

        # Grid utama: kiri = gambar, kanan = panel kontrol
        self.root.columnconfigure(0, weight=3)
        self.root.columnconfigure(1, weight=0)
        self.root.rowconfigure(1, weight=1)

        # Header
        header = ttk.Frame(self.root, padding=(12, 8))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Anotasi Rambut", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.progress_label = ttk.Label(header, text="0 / 0", style="Title.TLabel")
        self.progress_label.grid(row=0, column=1, sticky="e")
        self.image_id_label = ttk.Label(header, text="", style="TLabel")
        self.image_id_label.grid(row=1, column=0, columnspan=2, sticky="w")

        # ---- Kiri: gambar ----
        left = ttk.Frame(self.root, padding=(12, 0, 6, 8))
        left.grid(row=1, column=0, sticky="nsew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.canvas = tk.Label(left, text="Memuat...", bg="#d9dde1", fg="#555")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # ---- Kanan: panel kontrol scrollable ----
        right_outer = ttk.Frame(self.root, padding=(0, 0, 12, 8), style="Panel.TFrame")
        right_outer.grid(row=1, column=1, sticky="nsew")
        right_outer.rowconfigure(0, weight=1)
        right_outer.columnconfigure(0, weight=1)

        canvas_ctrl = tk.Canvas(right_outer, bg=C_PANEL, highlightthickness=0, width=400)
        scrollbar = ttk.Scrollbar(right_outer, orient="vertical", command=canvas_ctrl.yview)
        self.panel = ttk.Frame(canvas_ctrl, style="Panel.TFrame", padding=12)
        self.panel.bind(
            "<Configure>",
            lambda e: canvas_ctrl.configure(scrollregion=canvas_ctrl.bbox("all")),
        )
        canvas_ctrl.create_window((0, 0), window=self.panel, anchor="nw", width=390)
        canvas_ctrl.configure(yscrollcommand=scrollbar.set)
        canvas_ctrl.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._panel_canvas = canvas_ctrl
        # scroll dengan mouse wheel
        canvas_ctrl.bind_all(
            "<MouseWheel>",
            lambda e: canvas_ctrl.yview_scroll(int(-e.delta / 120), "units"),
        )

        self._build_panel(self.panel)

        # ---- Bawah: navigasi ----
        nav = ttk.Frame(self.root, padding=(12, 8))
        nav.grid(row=2, column=0, columnspan=2, sticky="ew")
        nav.columnconfigure(1, weight=1)
        self.btn_prev = ttk.Button(nav, text="\u2190 Sebelumnya", style="Nav.TButton", command=self._prev)
        self.btn_prev.grid(row=0, column=0, sticky="w")
        self.btn_save = ttk.Button(
            nav, text="Simpan & Lanjut (Enter) \u2192", style="Save.TButton", command=self._save_and_next
        )
        self.btn_save.grid(row=0, column=2, sticky="e")

    def _build_panel(self, p: ttk.Frame) -> None:
        p.columnconfigure(0, weight=1)
        row = 0

        # --- Viewpoint ---
        ttk.Label(p, text="1. Sudut Foto (Viewpoint)", style="Head.TLabel").grid(
            row=row, column=0, sticky="w", pady=(0, 4)
        )
        row += 1
        vp_grid = ttk.Frame(p, style="Panel.TFrame")
        vp_grid.grid(row=row, column=0, sticky="ew")
        vp_grid.columnconfigure(0, weight=1)
        vp_grid.columnconfigure(1, weight=1)
        for i, vp in enumerate(VIEWPOINTS):
            b = ttk.Button(vp_grid, text=T_VIEWPOINT[vp], command=lambda v=vp: self._set_viewpoint(v))
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
            self._btn_viewpoint[vp] = b
        row += 1

        ttk.Separator(p, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=8)
        row += 1

        # --- Hair Type ---
        ttk.Label(p, text="2. Jenis Rambut", style="Head.TLabel").grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1
        ht_grid = ttk.Frame(p, style="Panel.TFrame")
        ht_grid.grid(row=row, column=0, sticky="ew")
        ht_grid.columnconfigure(0, weight=1)
        ht_grid.columnconfigure(1, weight=1)
        for i, ht in enumerate(HAIR_TYPES):
            b = ttk.Button(ht_grid, text=T_HAIR_TYPE[ht], command=lambda h=ht: self._set_hair_type(h))
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
            self._btn_hairtype[ht] = b
        row += 1

        ttk.Separator(p, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=8)
        row += 1

        # --- Conditional ---
        self._cond_title = ttk.Label(p, text="3. Atribut Kondisional", style="Head.TLabel")
        self._cond_title.grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1
        self.cond_grid = ttk.Frame(p, style="Panel.TFrame")
        self.cond_grid.grid(row=row, column=0, sticky="ew")
        self.cond_grid.columnconfigure(0, weight=1)
        self.cond_grid.columnconfigure(1, weight=1)
        row += 1

        ttk.Separator(p, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=8)
        row += 1

        # --- Ungradable ---
        ug = ttk.Frame(p, style="Panel.TFrame")
        ug.grid(row=row, column=0, sticky="ew")
        ug.columnconfigure(1, weight=1)
        self.btn_ungradable = tk.Button(
            ug, text="TIDAK BISA DINILAI (U)", bg="#ffe0e0", fg=C_DANGER,
            activebackground="#ffcccc", font=("Segoe UI", 10, "bold"),
            relief="raised", command=self._toggle_ungradable,
        )
        self.btn_ungradable.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        ttk.Label(ug, text="Alasan:", style="Panel.TLabel").grid(row=1, column=0, sticky="w", padx=(2, 4), pady=2)
        self.reason_combo = ttk.Combobox(
            ug, state="readonly", values=[T_REASON[r] for r in UNGRADABLE_REASONS], width=36
        )
        self.reason_combo.set(T_REASON[""])
        self.reason_combo.grid(row=1, column=1, columnspan=2, sticky="ew", padx=2, pady=2)
        self.reason_combo.bind("<<ComboboxSelected>>", self._on_reason_selected)

        # Sub-opsi khusus: jika "sudut tidak valid" -> posisi orang dari mana
        self.subnote_label = ttk.Label(ug, text="Posisi orang:", style="Panel.TLabel")
        self.subnote_combo = ttk.Combobox(
            ug, state="readonly", values=[T_VIEWPOINT_SUBNOTE[r] for r in VIEWPOINT_SUBNOTE], width=36
        )
        self.subnote_combo.set(T_VIEWPOINT_SUBNOTE[""])
        self.subnote_combo.bind("<<ComboboxSelected>>", self._on_subnote_selected)
        # grid dulu, disembunyikan sampai reason=invalid_viewpoint
        self.subnote_label.grid(row=2, column=0, sticky="w", padx=(2, 4), pady=2)
        self.subnote_combo.grid(row=2, column=1, columnspan=2, sticky="ew", padx=2, pady=2)
        self.subnote_label.grid_remove()
        self.subnote_combo.grid_remove()
        row += 1

        # Hint aturan v3
        hint = (
            "Aturan: (1) Ujung tidak terlihat + panjang -> TIDAK BISA DINILAI; "
            "(2) Rambut diikat -> pilih alasan 'Terhalang ikatan rambut'; "
            "(3) Foto depan/samping -> 'Sudut tidak valid' + pilih posisi orang; "
            "(4) Volume dinilai dari massa, bukan ujung."
        )
        ttk.Label(p, text=hint, style="Panel.TLabel", wraplength=360, foreground="#555").grid(
            row=row, column=0, sticky="w", pady=(6, 0)
        )
        row += 1

        ttk.Separator(p, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=8)
        row += 1

        # --- Confidence ---
        ttk.Label(p, text="Kepercayaan (Confidence)", style="Head.TLabel").grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1
        cf = ttk.Frame(p, style="Panel.TFrame")
        cf.grid(row=row, column=0, sticky="ew")
        for i in range(3):
            cf.columnconfigure(i, weight=1)
        for i, c in enumerate(CONFIDENCE_LEVELS):
            b = ttk.Button(cf, text=T_CONFIDENCE[c], command=lambda cc=c: self.confidence.set(cc))
            b.grid(row=0, column=i, sticky="ew", padx=2)
            self._btn_confidence[c] = b
        row += 1

        # --- Visibility ---
        ttk.Label(p, text="Visibilitas yang Terlihat", style="Head.TLabel").grid(
            row=row, column=0, sticky="w", pady=(10, 4)
        )
        row += 1
        vis = ttk.Frame(p, style="Panel.TFrame")
        vis.grid(row=row, column=0, sticky="ew")
        for i, vf in enumerate(VISIBILITY_FIELDS):
            cb = ttk.Checkbutton(vis, text=T_VISIBILITY[vf], variable=self.vis_vars[vf])
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=2, pady=2)
        row += 1

        # --- Notes ---
        ttk.Label(p, text="Catatan", style="Head.TLabel").grid(row=row, column=0, sticky="w", pady=(10, 4))
        row += 1
        self._notes_widget = tk.Text(p, height=3, wrap="word", font=("Segoe UI", 10))
        self._notes_widget.grid(row=row, column=0, sticky="ew")
        row += 1

    def _bind_keys(self) -> None:
        self.root.bind("<Return>", lambda e: self._save_and_next())
        self.root.bind("<Left>", lambda e: self._prev())
        self.root.bind("<Right>", lambda e: self._next())
        self.root.bind("1", lambda e: self._set_hair_type("straight"))
        self.root.bind("2", lambda e: self._set_hair_type("wavy"))
        self.root.bind("3", lambda e: self._set_hair_type("curly"))
        self.root.bind("4", lambda e: self._set_hair_type("kinky"))
        self.root.bind("u", lambda e: self._toggle_ungradable())
        self.root.bind("h", lambda e: self._set_confidence("high"))
        self.root.bind("m", lambda e: self._set_confidence("medium"))
        self.root.bind("l", lambda e: self._set_confidence("low"))
        self.root.bind("q", lambda e: self._set_conditional("short"))
        self.root.bind("w", lambda e: self._set_conditional("shoulder"))
        self.root.bind("e", lambda e: self._set_conditional("mid_back"))
        self.root.bind("r", lambda e: self._set_conditional("long"))
        self.root.bind("a", lambda e: self._set_conditional("low"))
        self.root.bind("s", lambda e: self._set_conditional("medium"))
        self.root.bind("d", lambda e: self._set_conditional("high"))

    # ---------------- Highlight helper ----------------
    @staticmethod
    def _highlight(btn: ttk.Button, active: bool) -> None:
        if active:
            btn.configure(style="Active.TButton")
        else:
            btn.configure(style="TButton")

    def _refresh_highlights(self) -> None:
        for vp, b in self._btn_viewpoint.items():
            self._highlight(b, vp == self.viewpoint.get())
        for ht, b in self._btn_hairtype.items():
            self._highlight(b, ht == self.hair_type.get())
        for c, b in self._btn_confidence.items():
            self._highlight(b, c == self.confidence.get())
        for val, b in self._btn_conditional.items():
            self._highlight(b, val == self.conditional_value.get())
        # Ungradable button visual
        if self.ungradable.get():
            self.btn_ungradable.configure(relief="sunken", bg="#ffb3b3", text="\u2713 TIDAK BISA DINILAI (U)")
        else:
            self.btn_ungradable.configure(relief="raised", bg="#ffe0e0", text="TIDAK BISA DINILAI (U)")

    # ---------------- Actions ----------------
    def _set_viewpoint(self, vp: str) -> None:
        self.viewpoint.set(vp)
        self._refresh_highlights()

    def _set_hair_type(self, ht: str) -> None:
        self.hair_type.set(ht)
        self._rebuild_conditional(ht)
        self.conditional_value.set("")
        self._refresh_highlights()

    def _set_confidence(self, c: str) -> None:
        self.confidence.set(c)
        self._refresh_highlights()

    def _set_conditional(self, val: str) -> None:
        # hanya berlaku jika tombol ada untuk nilai ini
        if val in self._btn_conditional:
            self.conditional_value.set(val)
            self._refresh_highlights()

    def _toggle_ungradable(self) -> None:
        self.ungradable.set(not self.ungradable.get())
        self._refresh_highlights()

    def _on_reason_selected(self, _event=None) -> None:
        label = self.reason_combo.get()
        reason = ""
        for k, v in T_REASON.items():
            if v == label:
                reason = k
                break
        self.ungradable_reason.set(reason)
        # Tampilkan sub-opsi posisi HANYA jika alasan = invalid_viewpoint
        if reason == "invalid_viewpoint":
            self.subnote_label.grid()
            self.subnote_combo.grid()
        else:
            self.subnote_label.grid_remove()
            self.subnote_combo.grid_remove()
            self.viewpoint_subnote.set("")
            self.subnote_combo.set(T_VIEWPOINT_SUBNOTE[""])

    def _on_subnote_selected(self, _event=None) -> None:
        label = self.subnote_combo.get()
        for k, v in T_VIEWPOINT_SUBNOTE.items():
            if v == label:
                self.viewpoint_subnote.set(k)
                break

    def _rebuild_conditional(self, hair_type: str) -> None:
        for w in self.cond_grid.winfo_children():
            w.destroy()
        self._btn_conditional = {}
        for i in range(2):
            self.cond_grid.columnconfigure(i, weight=1)

        if not hair_type:
            self._cond_title.configure(text="3. Atribut Kondisional  (pilih jenis rambut dulu)")
            self._attr_name = None
            return

        if hair_type in ("straight", "wavy"):
            self._cond_title.configure(text="3. Panjang Rambut (relatif)")
            classes = LENGTH_CLASSES
            labels = T_LENGTH
            self._attr_name = "length"
        else:
            self._cond_title.configure(text="3. Volume Rambut [PROVISIONAL]")
            classes = VOLUME_CLASSES
            labels = T_VOLUME
            self._attr_name = "visual_volume"

        for i, cls in enumerate(classes):
            b = ttk.Button(self.cond_grid, text=labels[cls], command=lambda c=cls: self._set_conditional(c))
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
            self._btn_conditional[cls] = b

    # ---------------- Image loading ----------------
    def _load_current_image(self) -> None:
        if self.current_idx >= len(self.images):
            messagebox.showinfo("Selesai", "Semua gambar sudah dianotasi!")
            self.root.destroy()
            return

        img_info = self.images[self.current_idx]
        img_id = img_info["image_id"]
        img_path = BASE / img_info["relpath"]

        self.progress_label.configure(text=f"{self.current_idx + 1} / {len(self.images)}")
        self.image_id_label.configure(text=f"Berkas: {img_id}")

        try:
            pil_img = Image.open(img_path)
            w, h = pil_img.size
            area_w = max(self.canvas.winfo_width(), 640)
            area_h = max(self.canvas.winfo_height(), 480)
            scale = min(area_w / w, area_h / h)
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            self._tk_img = ImageTk.PhotoImage(pil_img)
            self.canvas.configure(image=self._tk_img, text="")
            self._current_img_wh = (w, h)
        except Exception as exc:
            self.canvas.configure(image="", text=f"Gagal memuat gambar: {exc}")
            self._current_img_wh = (0, 0)

        self._reset_form()
        existing = self.annotations.get(img_id)
        if existing:
            self._load_existing_annotation(existing)
        self._refresh_highlights()

    def _reset_form(self) -> None:
        self.viewpoint.set("back")
        self.hair_type.set("")
        self.conditional_value.set("")
        self.ungradable.set(False)
        self.ungradable_reason.set("")
        self.viewpoint_subnote.set("")
        self.confidence.set("medium")
        for v in self.vis_vars.values():
            v.set(False)
        if self._notes_widget:
            self._notes_widget.delete("1.0", "end")
        self.reason_combo.set(T_REASON[""])
        self.subnote_combo.set(T_VIEWPOINT_SUBNOTE[""])
        self.subnote_label.grid_remove()
        self.subnote_combo.grid_remove()
        self._rebuild_conditional("")
        self._refresh_highlights()

    def _load_existing_annotation(self, rec: dict) -> None:
        self.viewpoint.set(rec.get("viewpoint", "back"))
        self._set_hair_type(rec.get("hair_type", ""))
        cond = rec.get("conditional_attribute", {})
        val = cond.get("value") or ""
        if val:
            self.conditional_value.set(val)
        self.ungradable.set(rec.get("ungradable", False))
        reason = rec.get("ungradable_reason") or ""
        self.ungradable_reason.set(reason)
        self.reason_combo.set(T_REASON.get(reason, T_REASON[""]))
        # subnote (posisi orang) — hanya utk invalid_viewpoint
        subnote = rec.get("viewpoint_subnote") or ""
        self.viewpoint_subnote.set(subnote)
        self.subnote_combo.set(T_VIEWPOINT_SUBNOTE.get(subnote, T_VIEWPOINT_SUBNOTE[""]))
        if reason == "invalid_viewpoint":
            self.subnote_label.grid()
            self.subnote_combo.grid()
        else:
            self.subnote_label.grid_remove()
            self.subnote_combo.grid_remove()
        self.confidence.set(rec.get("confidence", "medium"))
        vis = rec.get("visibility", {})
        for vf in VISIBILITY_FIELDS:
            self.vis_vars[vf].set(vis.get(vf, False))
        if self._notes_widget:
            self._notes_widget.delete("1.0", "end")
            self._notes_widget.insert("1.0", rec.get("notes", ""))

    # ---------------- Collect & save ----------------
    def _collect_annotation(self) -> dict:
        img_info = self.images[self.current_idx]
        ht = self.hair_type.get()
        if ht in ("straight", "wavy"):
            attr_name = "length"
        elif ht in ("curly", "kinky"):
            attr_name = "visual_volume"
        else:
            # ungradable / jenis belum dipilih: turunkan nama atribut dari label dataset
            type_id = img_info.get("hair_type_id", "")
            attr_name = "length" if type_id in ("lurus", "bergelombang") else (
                "visual_volume" if type_id in ("keriting", "sangat-keriting") else None
            )

        ungradable = self.ungradable.get()
        cond_value = None if ungradable else (self.conditional_value.get() or None)
        w, h = self._current_img_wh
        notes = self._notes_widget.get("1.0", "end").strip() if self._notes_widget else ""

        return {
            "image_id": img_info["image_id"],
            "source": img_info.get("source", "figaro1k"),
            "viewpoint": self.viewpoint.get(),
            "hair_type": ht,
            "hair_type_id": img_info.get("hair_type_id", ""),
            "conditional_attribute": {"name": attr_name, "value": cond_value},
            "ungradable": ungradable,
            "ungradable_reason": self.ungradable_reason.get() or None,
            "viewpoint_subnote": self.viewpoint_subnote.get() or None,
            "confidence": self.confidence.get(),
            "visibility": {vf: self.vis_vars[vf].get() for vf in VISIBILITY_FIELDS},
            "taxonomy_version": TAXONOMY_VERSION,
            "guideline_version": GUIDELINE_VERSION,
            "image_width": w,
            "image_height": h,
            "annotation_timestamp": datetime.now(timezone.utc).isoformat(),
            "annotator": self.annotator,
            "notes": notes,
        }

    def _save_current(self) -> None:
        rec = self._collect_annotation()
        self.annotations[rec["image_id"]] = rec
        self._save_annotations()

    def _validate(self) -> tuple[bool, str]:
        """Validasi sebelum simpan (v3). Kembalikan (valid, pesan_error)."""
        ht = self.hair_type.get()
        ungradable = self.ungradable.get()

        # 1. Jenis rambut wajib kecuali ungradable
        if not ht and not ungradable:
            return False, "Jenis rambut belum dipilih."

        # 2. Jika ungradable, alasan wajib diisi
        if ungradable and not self.ungradable_reason.get():
            return False, "Gambar ditandai TIDAK BISA DINILAI, tapi alasan belum dipilih."

        # 2b. Jika alasan = sudut tidak valid, posisi orang wajib diisi
        if ungradable and self.ungradable_reason.get() == "invalid_viewpoint":
            if not self.viewpoint_subnote.get():
                return False, (
                    "Alasan 'Sudut tidak valid' dipilih.\n"
                    "Pilih juga Posisi orang (dari depan / samping / belakang tidak jelas / lain)."
                )

        # 3. Aturan keras v3: cek konsistensi panjang vs visibility
        if not ungradable:
            if ht in ("straight", "wavy"):
                if not self.cond_value():
                    return False, "Jenis '%s' dipilih, tapi panjang rambut belum dipilih." % T_HAIR_TYPE[ht]
                # Aturan: ujung tidak terlihat -> seharusnya ungradable
                if not self.vis_vars["hair_ends"].get():
                    return False, (
                        "Ujung rambut tidak ditandai terlihat.\n"
                        "Untuk penilaian PANJANG, ujung rambut wajib terlihat.\n"
                        "Centang 'Ujung rambut' ATAU tandai TIDAK BISA DINILAI."
                    )
            elif ht in ("curly", "kinky"):
                if not self.cond_value():
                    return False, "Jenis '%s' dipilih, tapi volume rambut belum dipilih." % T_HAIR_TYPE[ht]

        return True, ""

    def cond_value(self) -> str:
        return self.conditional_value.get() or ""

    def _save_and_next(self) -> None:
        valid, msg = self._validate()
        if not valid:
            messagebox.showwarning("Data belum lengkap", msg + "\n\nSilakan lengkapi dulu.")
            return
        self._save_current()
        self._next()

    def _next(self) -> None:
        if self.current_idx < len(self.images) - 1:
            self.current_idx += 1
            self._load_current_image()

    def _prev(self) -> None:
        if self.current_idx > 0:
            self.current_idx -= 1
            self._load_current_image()

    def _is_incomplete(self, rec: dict) -> bool:
        """Cek apakah record lama tidak lengkap (perlu diperbaiki)."""
        ht = rec.get("hair_type", "")
        ungradable = rec.get("ungradable", False)
        reason = rec.get("ungradable_reason")
        cond_value = (rec.get("conditional_attribute") or {}).get("value")

        if not ht and not ungradable:
            return True
        if ungradable and not reason:
            return True
        # v3: sudut tidak valid wajib punya subnote posisi
        if ungradable and reason == "invalid_viewpoint" and not rec.get("viewpoint_subnote"):
            return True
        if not ungradable and ht and not cond_value:
            return True
        return False

    def skip_to_first_unannotated(self) -> None:
        """Arahkan ke record pertama yang belum dianotasi ATAU tidak lengkap."""
        # Prioritas 1: belum dianotasi sama sekali
        for i, img_info in enumerate(self.images):
            if img_info["image_id"] not in self.annotations:
                self.current_idx = i
                return
        # Prioritas 2: record tidak lengkap (perlu diperbaiki)
        for i, img_info in enumerate(self.images):
            rec = self.annotations.get(img_info["image_id"])
            if rec and self._is_incomplete(rec):
                self.current_idx = i
                return
        # Semua beres -> ke akhir
        self.current_idx = len(self.images) - 1


def run(annotator: str, manifest_path: Path | None = None) -> None:
    root = tk.Tk()
    app = AnnotationApp(root, annotator, manifest_path)
    app.skip_to_first_unannotated()
    # render dulu agar ukuran canvas valid, baru muat gambar
    root.update_idletasks()
    app._load_current_image()
    root.mainloop()
