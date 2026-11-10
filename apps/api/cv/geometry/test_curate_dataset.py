import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

import curate_dataset as curate


class CurateDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.dataset = self.root / "dataset"
        (self.dataset / "figaro1k").mkdir(parents=True)
        (self.dataset / "new_dataset").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, cohort, label, name, image=True):
        folder = self.dataset / cohort / label
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        if image:
            picture = Image.new("RGB", (256, 256), "white")
            draw = ImageDraw.Draw(picture)
            draw.ellipse((55, 30, 200, 245), fill=(80, 25, 140))
            picture.save(path)
        else:
            path.write_bytes(b"not an image")
        return path

    def test_exact_pixels_across_encodings_and_label_conflict(self):
        bmp = self.put("figaro1k", "lurus", "a.bmp")
        png_dir = self.dataset / "new_dataset" / "keriting"
        png_dir.mkdir(parents=True)
        with Image.open(bmp) as im:
            im.save(png_dir / "b.png")
        rows = [curate.inspect(item) for item in curate.discover(self.dataset)]
        self.assertNotEqual(rows[0]["sha256"], rows[1]["sha256"])
        self.assertEqual(rows[0]["pixel_sha256"], rows[1]["pixel_sha256"])
        pair = curate.duplicate_candidates(rows)[0]
        self.assertEqual(pair["exact_kind"], "decoded_rgb_pixels")
        self.assertTrue(pair["label_conflict"])
        self.assertEqual(pair["review_status"], "manual_review_required")

    def test_corrupt_record_reported_and_alias_backup_excluded(self):
        self.put("figaro1k", "sangat keriting", "ok.png")
        self.put("figaro1k", "lurus_backup", "backup.png")
        self.put("new_dataset", "lurus", "broken.jpg", image=False)
        rows = [curate.inspect(item) for item in curate.discover(self.dataset)]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["hair_class"], "sangat-keriting")
        self.assertIsNotNone(rows[1]["error"])
        self.assertEqual(rows[1]["sha256"], curate.sha256_file(self.dataset / rows[1]["image_id"]))

    def test_near_hash_pair_and_output_safety(self):
        self.put("figaro1k", "lurus", "a.png")
        original = self.put("new_dataset", "lurus", "b.png")
        with Image.open(original) as im:
            im = im.copy()
            ImageDraw.Draw(im).point((4, 4), fill=(240, 230, 220))
            im.save(original)
        rows = [curate.inspect(item) for item in curate.discover(self.dataset)]
        self.assertTrue(curate.duplicate_candidates(rows))
        geometry = self.root / "geometry"
        report_dir = geometry / "reports"
        original_here = curate.HERE
        curate.HERE = geometry
        try:
            report = curate.run(self.dataset, report_dir, 42)
            with self.assertRaises(FileExistsError):
                curate.run(self.dataset, report_dir, 42)
            marker = report_dir / "other.txt"
            marker.write_text("preserve")
            curate.run(self.dataset, report_dir, 42, overwrite=True)
            self.assertEqual(marker.read_text(), "preserve")
            with self.assertRaises(ValueError):
                curate.run(self.dataset, self.dataset / "reports", 42)
        finally:
            curate.HERE = original_here
        self.assertEqual(report["status"], "NOT_READY_PENDING_REVIEW")

    def test_dhash_compares_adjacent_columns_within_each_row(self):
        gradient = Image.new("L", (9, 8))
        for y in range(8):
            for x in range(9):
                gradient.putpixel((x, y), x * 25)
        dh_asc, _ = curate.perceptual_hashes(gradient.convert("RGB"))
        self.assertEqual(int(dh_asc, 16), 0)
        inv = Image.new("L", (9, 8))
        for y in range(8):
            for x in range(9):
                inv.putpixel((x, y), (8 - x) * 25)
        dh_desc, _ = curate.perceptual_hashes(inv.convert("RGB"))
        self.assertEqual(int(dh_desc, 16), (1 << 64) - 1)


if __name__ == "__main__":
    unittest.main()
