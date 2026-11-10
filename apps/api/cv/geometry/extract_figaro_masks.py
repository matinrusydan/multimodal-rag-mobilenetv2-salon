"""Extract and verify Figaro-1k ground-truth hair segmentation masks.

This tool extracts the pixel-accurate ground-truth masks (.pbm) for the curated
Figaro-1k dataset records directly from the canonical Figaro-1k archive using
targeted HTTP Range requests (or a local archive if provided), converts them
into standard 8-bit binary PNG masks (0 = background, 255 = hair), and verifies
1:1 spatial dimension alignment against the source images.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import struct
import sys
import urllib.request
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image

DEFAULT_URL = (
    "https://www.dropbox.com/scl/fi/bkzbwgobxayoaeqohgvrp/"
    "Figaro-1k.zip?rlkey=qahueoko45prpzmsadzmus5ga&dl=1"
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
DEFAULT_MANIFEST = HERE / "reports" / "phase1" / "curated_manifest.json"
DEFAULT_DATASET = HERE.parent / "dataset"
DEFAULT_OUT_DIR = HERE / "data" / "figaro1k_gt"


def parse_central_directory(cd_bytes: bytes) -> Dict[int, dict]:
    """Parse ZIP central directory records and find FrameNNNNN-gt.pbm entries."""
    entries: Dict[int, dict] = {}
    pos = 0
    total_len = len(cd_bytes)

    while pos < total_len:
        if cd_bytes[pos : pos + 4] != b"PK\x01\x02":
            break
        (
            _,
            _,
            _,
            comp_method,
            _,
            _,
            _,
            comp_size,
            uncomp_size,
            name_len,
            extra_len,
            comment_len,
            _,
            _,
            _,
            local_offset,
        ) = struct.unpack_from("<HHHHHHIIIHHHHHII", cd_bytes, pos + 4)

        name = cd_bytes[pos + 46 : pos + 46 + name_len].decode("utf-8", "ignore")
        m = re.search(r"Frame(\d+)-gt\.pbm$", name)
        if m:
            frame_no = int(m.group(1))
            entries[frame_no] = {
                "name": name,
                "comp_size": comp_size,
                "uncomp_size": uncomp_size,
                "comp_method": comp_method,
                "local_offset": local_offset,
            }

        pos += 46 + name_len + extra_len + comment_len

    return entries


def fetch_central_directory(url: str, timeout: int = 30) -> bytes:
    """Fetch the end-of-central-directory and central directory via HTTP Range."""
    # Find archive length by requesting the last 65 KB first
    tail_req = urllib.request.Request(url, headers={"Range": "bytes=-65536"})
    with urllib.request.urlopen(tail_req, timeout=timeout) as resp:
        tail_data = resp.read()
        cr = resp.headers.get("Content-Range", "")
        # format: bytes start-end/total
        m = re.search(r"/(\d+)$", cr)
        if not m:
            raise RuntimeError(f"Could not determine total file size from Content-Range: {cr}")
        total_size = int(m.group(1))

    # Locate EOCD signature PK\x05\x06 in tail
    eocd_pos = tail_data.rfind(b"PK\x05\x06")
    if eocd_pos == -1:
        raise RuntimeError("EOCD record not found in archive tail")

    # EOCD structure from offset 4:
    # 2: disk_num, 2: cd_start_disk, 2: cd_entries_disk, 2: cd_entries_total, 4: cd_size, 4: cd_offset
    num_disk, cd_start_disk, cd_entries_disk, cd_entries_total, cd_size, cd_offset = struct.unpack_from(
        "<HHHHII", tail_data, eocd_pos + 4
    )

    # Fetch entire central directory
    cd_req = urllib.request.Request(url, headers={"Range": f"bytes={cd_offset}-{cd_offset + cd_size - 1}"})
    with urllib.request.urlopen(cd_req, timeout=timeout) as resp:
        return resp.read()


def decompress_entry(raw_chunk: bytes, rel_offset: int, comp_size: int, comp_method: int) -> bytes:
    """Decompress an entry from a raw ZIP chunk given relative offset to local header."""
    loc_hdr = raw_chunk[rel_offset : rel_offset + 30]
    loc_name_len, loc_extra_len = struct.unpack_from("<HH", loc_hdr, 26)
    data_start = rel_offset + 30 + loc_name_len + loc_extra_len
    comp_bytes = raw_chunk[data_start : data_start + comp_size]
    if comp_method == 8:
        return zlib.decompress(comp_bytes, -15)
    return comp_bytes


def extract_and_convert_pbm(pbm_bytes: bytes) -> Image.Image:
    """Convert Netpbm PBM binary/ascii mask bytes to PIL Image (mode 'L', 0 or 255)."""
    with Image.open(io.BytesIO(pbm_bytes)) as im:
        return im.convert("L")


def verify_mask_coverage(mask: Image.Image, min_coverage: float = 0.01, max_coverage: float = 0.99) -> float:
    """Verify mask has reasonable hair coverage and return ratio."""
    import numpy as np

    arr = np.asarray(mask)
    ratio = float((arr > 127).mean())
    if ratio < min_coverage or ratio > max_coverage:
        raise ValueError(f"Abnormal hair coverage ratio {ratio:.4f} (expected {min_coverage}..{max_coverage})")
    return ratio


def extract_masks(
    manifest_path: Path = DEFAULT_MANIFEST,
    dataset_dir: Path = DEFAULT_DATASET,
    out_dir: Path = DEFAULT_OUT_DIR,
    url: str = DEFAULT_URL,
    zip_path: Optional[Path] = None,
    overwrite: bool = False,
    verify_only: bool = False,
) -> dict:
    """Extract and verify ground-truth masks for curated Figaro-1k cohort."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    figaro_records = [r for r in manifest.get("records", []) if r.get("cohort") == "figaro1k"]
    target_frames = {int(Path(r["image_id"]).stem): r for r in figaro_records}

    if not target_frames:
        raise ValueError("No figaro1k records found in manifest")

    out_dir.mkdir(parents=True, exist_ok=True)

    if verify_only:
        verified_count = 0
        coverages = []
        for frame_no, r in sorted(target_frames.items()):
            mask_path = out_dir / f"{frame_no:05d}.png"
            if not mask_path.exists():
                raise FileNotFoundError(f"Missing mask for frame {frame_no:05d}: {mask_path}")
            img_path = dataset_dir / r["image_id"]
            if not img_path.exists():
                raise FileNotFoundError(f"Source image missing: {img_path}")
            with Image.open(img_path) as im, Image.open(mask_path) as mk:
                if im.size != mk.size:
                    raise ValueError(f"Dimension mismatch for frame {frame_no}: {im.size} vs {mk.size}")
                cov = verify_mask_coverage(mk)
                coverages.append(cov)
                verified_count += 1
        return {
            "status": "verified",
            "count": verified_count,
            "min_coverage": min(coverages),
            "max_coverage": max(coverages),
        }

    # If masks already exist and overwrite is false, check if complete
    existing_masks = [f for f in out_dir.glob("*.png")]
    if len(existing_masks) >= len(target_frames) and not overwrite:
        # Run fast verification
        return extract_masks(
            manifest_path=manifest_path,
            dataset_dir=dataset_dir,
            out_dir=out_dir,
            url=url,
            zip_path=zip_path,
            overwrite=False,
            verify_only=True,
        )

    # Need extraction
    if zip_path and zip_path.exists():
        import zipfile
        with zipfile.ZipFile(zip_path) as z:
            name_map = {}
            for name in z.namelist():
                m = re.search(r"Frame(\d+)-gt\.pbm$", name)
                if m:
                    name_map[int(m.group(1))] = name

            extracted = 0
            for frame_no, rec in sorted(target_frames.items()):
                if frame_no not in name_map:
                    raise KeyError(f"Frame {frame_no} not found in zip archive")
                raw_pbm = z.read(name_map[frame_no])
                mask_l = extract_and_convert_pbm(raw_pbm)
                assert mask_l.size == (rec["width"], rec["height"]), f"Size mismatch for frame {frame_no}"
                mask_l.save(out_dir / f"{frame_no:05d}.png")
                extracted += 1
            return {"status": "extracted_from_local_zip", "count": extracted}

    # Fetch via HTTP Range requests
    cd_bytes = fetch_central_directory(url)
    all_entries = parse_central_directory(cd_bytes)
    selected_entries = {k: v for k, v in all_entries.items() if k in target_frames}

    if len(selected_entries) != len(target_frames):
        missing = set(target_frames.keys()) - set(selected_entries.keys())
        raise KeyError(f"Could not find CD entries for frames: {missing}")

    min_start = min(e["local_offset"] for e in selected_entries.values())
    max_end = max(e["local_offset"] + 30 + 100 + e["comp_size"] for e in selected_entries.values())

    req = urllib.request.Request(url, headers={"Range": f"bytes={min_start}-{max_end}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw_chunk = resp.read()

    extracted = 0
    for frame_no, ent in sorted(selected_entries.items()):
        rec = target_frames[frame_no]
        rel_offset = ent["local_offset"] - min_start
        decomp = decompress_entry(raw_chunk, rel_offset, ent["comp_size"], ent["comp_method"])
        mask_l = extract_and_convert_pbm(decomp)
        if mask_l.size != (rec["width"], rec["height"]):
            raise ValueError(
                f"Extracted mask size {mask_l.size} does not match image size ({rec['width']}, {rec['height']})"
            )
        mask_l.save(out_dir / f"{frame_no:05d}.png")
        extracted += 1

    return {"status": "extracted_via_http_range", "count": extracted}


def main():
    parser = argparse.ArgumentParser(
        description="Extract and verify ground-truth masks for curated Figaro-1k images."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Path to curated manifest JSON (default: {DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Path to dataset directory (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory for binary PNG masks (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_URL,
        help="Canonical archive URL for Figaro-1k.zip",
    )
    parser.add_argument(
        "--zip-path",
        type=Path,
        default=None,
        help="Optional path to local Figaro-1k.zip",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Force re-extraction even if masks already exist",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing masks against manifest and source images",
    )
    args = parser.parse_args()

    result = extract_masks(
        manifest_path=args.manifest,
        dataset_dir=args.dataset_dir,
        out_dir=args.out_dir,
        url=args.url,
        zip_path=args.zip_path,
        overwrite=args.overwrite,
        verify_only=args.verify_only,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
