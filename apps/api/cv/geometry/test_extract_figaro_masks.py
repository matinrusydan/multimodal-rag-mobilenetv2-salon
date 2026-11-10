"""Unit tests for Figaro-1k mask extraction and verification."""
from __future__ import annotations

import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

from extract_figaro_masks import (
    extract_and_convert_pbm,
    extract_masks,
    parse_central_directory,
    verify_mask_coverage,
)


class ExtractFigaroMasksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_extract_and_convert_pbm_binary(self):
        # Create a small binary PBM (P4) in memory via PIL
        arr = np.zeros((16, 16), dtype=np.uint8)
        arr[4:12, 4:12] = 255
        im_1 = Image.fromarray(arr).convert("1")
        buf = io.BytesIO()
        im_1.save(buf, format="PPM")
        pbm_bytes = buf.getvalue()

        converted = extract_and_convert_pbm(pbm_bytes)
        self.assertEqual(converted.mode, "L")
        self.assertEqual(converted.size, (16, 16))
        out_arr = np.asarray(converted)
        self.assertEqual(out_arr.min(), 0)
        self.assertEqual(out_arr.max(), 255)
        self.assertAlmostEqual(verify_mask_coverage(converted), 64 / 256)

    def test_verify_mask_coverage_rejects_empty_or_full(self):
        empty = Image.fromarray(np.zeros((16, 16), dtype=np.uint8))
        with self.assertRaises(ValueError):
            verify_mask_coverage(empty)

        full = Image.fromarray(np.full((16, 16), 255, dtype=np.uint8))
        with self.assertRaises(ValueError):
            verify_mask_coverage(full)

    def test_extract_from_local_zip_and_verify_only(self):
        dataset_dir = self.tmp / "dataset"
        figaro_cls_dir = dataset_dir / "figaro1k" / "lurus"
        figaro_cls_dir.mkdir(parents=True, exist_ok=True)
        out_dir = self.tmp / "out_gt"

        # Create dummy source image (20x30)
        img = Image.new("RGB", (20, 30), color=(100, 100, 100))
        img.save(figaro_cls_dir / "00010.jpg")

        # Create manifest
        manifest = {
            "records": [
                {
                    "image_id": "figaro1k/lurus/00010.jpg",
                    "cohort": "figaro1k",
                    "width": 20,
                    "height": 30,
                }
            ]
        }
        manifest_path = self.tmp / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        # Create dummy zip containing GT/Frame00010-gt.pbm
        arr = np.zeros((30, 20), dtype=np.uint8)
        arr[5:25, 5:15] = 255
        pbm_buf = io.BytesIO()
        Image.fromarray(arr).convert("1").save(pbm_buf, format="PPM")

        zip_path = self.tmp / "Figaro-1k.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("Figaro1k/GT/Frame00010-gt.pbm", pbm_buf.getvalue())

        res = extract_masks(
            manifest_path=manifest_path,
            dataset_dir=dataset_dir,
            out_dir=out_dir,
            zip_path=zip_path,
        )
        self.assertEqual(res["status"], "extracted_from_local_zip")
        self.assertEqual(res["count"], 1)
        self.assertTrue((out_dir / "00010.png").exists())

        # Verify-only check
        ver = extract_masks(
            manifest_path=manifest_path,
            dataset_dir=dataset_dir,
            out_dir=out_dir,
            verify_only=True,
        )
        self.assertEqual(ver["status"], "verified")
        self.assertEqual(ver["count"], 1)

    def test_parse_central_directory_extracts_gt_entries(self):
        # Build a minimal valid ZIP file and parse its central directory
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("Figaro1k/GT/Frame00042-gt.pbm", b"P4\n2 2\n\xc0\x00")
            z.writestr("Figaro1k/Original/Frame00042.jpg", b"fakejpg")

        raw = buf.getvalue()
        eocd = raw.rfind(b"PK\x05\x06")
        _, _, _, _, cd_size, cd_offset = struct.unpack_from("<HHHHII", raw, eocd + 4)
        cd_bytes = raw[cd_offset : cd_offset + cd_size]

        entries = parse_central_directory(cd_bytes)
        self.assertIn(42, entries)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[42]["name"], "Figaro1k/GT/Frame00042-gt.pbm")


if __name__ == "__main__":
    unittest.main()
