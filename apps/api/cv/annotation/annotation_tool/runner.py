# -*- coding: utf-8 -*-
"""CLI runner untuk tool anotasi (tkinter).

Cara pakai (dari apps/api/cv):
  & ".venv\\Scripts\\python.exe" -m annotation.annotation_tool.runner --annotator A
  & ".venv\\Scripts\\python.exe" -m annotation.annotation_tool.runner --annotator B

Syarat:
  - annotation/ground_truth/pilot_manifest.json harus ada (jalankan sample_pilot.py dulu)
  - tkinter (bawaan Python)
  - Pillow (sudah ada di venv)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS = Path(__file__).resolve().parents[2]  # apps/api/cv
if str(THIS) not in sys.path:
    sys.path.insert(0, str(THIS))

from annotation.annotation_tool.app import run  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Jalankan tool anotasi rambut (tkinter).")
    ap.add_argument(
        "--annotator",
        required=True,
        choices=["A", "B"],
        help="ID annotator (A atau B). Output disimpan ke annotator_<id>.json.",
    )
    ap.add_argument(
        "--manifest",
        default=None,
        help="Path manifest JSON (default: annotation/ground_truth/pilot_manifest.json). "
        "Untuk pilot 240 gunakan: annotation/ground_truth/pilot_manifest_240.json",
    )
    args = ap.parse_args()

    manifest = Path(args.manifest) if args.manifest else (
        THIS / "annotation" / "ground_truth" / "pilot_manifest.json"
    )
    if not manifest.is_absolute():
        manifest = (Path.cwd() / manifest).resolve()
    if not manifest.exists():
        print(f"ERROR: Manifest tidak ditemukan: {manifest}")
        print("Jalankan dulu: python annotation/sample_pilot.py")
        sys.exit(1)

    print(f"Memulai tool anotasi — Annotator {args.annotator}")
    print(f"Manifest: {manifest}")
    print(f"Output  : {THIS / 'annotation' / 'ground_truth'}")
    print("Tombol pintas: 1-4=jenis rambut, Q/W/E/R=panjang, A/S/D=volume,")
    print("               U=tidak bisa dinilai, H/M/L=confidence, Enter=simpan & lanjut, <-/->=navigasi")
    print()

    run(args.annotator, manifest)


if __name__ == "__main__":
    main()
