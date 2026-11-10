import unittest

import tempfile
from pathlib import Path

from pose_feasibility import (discover, landmark_is_valid, matching_pairs,
                              summarize, wilson_interval)


class PoseFeasibilityHelpersTest(unittest.TestCase):
    def test_wilson_handles_empty_and_bounds(self):
        self.assertIsNone(wilson_interval(0, 0))
        self.assertEqual(wilson_interval(0, 10)[0], 0.0)
        self.assertAlmostEqual(wilson_interval(10, 10)[1], 1.0)

    def test_landmark_threshold_and_tolerance(self):
        self.assertTrue(landmark_is_valid({"x": 1.1, "y": 0.5, "visibility": 0.5}))
        self.assertFalse(landmark_is_valid({"x": 1.16, "y": 0.5, "visibility": 0.9}))
        self.assertFalse(landmark_is_valid({"x": 0.5, "y": 0.5, "visibility": 0.49}))

    def test_summary_separates_unconditional_and_pose_conditional(self):
        rows = [{"cohort": "figaro1k", "hair_class": "lurus", "pose_ok": True,
                 "shoulder_ok": True, "head_ok": False},
                {"cohort": "figaro1k", "hair_class": "lurus", "pose_ok": False,
                 "shoulder_ok": False, "head_ok": False}]
        result = summarize(rows)["figaro1k|lurus"]
        self.assertEqual(result["shoulder_ok_rate"], 0.5)
        self.assertEqual(result["shoulder_ok_conditional_rate"], 1.0)
        self.assertEqual(result["head_ok_conditional_rate"], 0.0)

    def test_pairs_select_new_dataset_to_its_backup(self):
        records = [{"cohort": cohort, "hair_class": "lurus", "filename": "same.jpg", "image_id": cohort}
                   for cohort in ("figaro1k", "new_dataset", "new_dataset_backup_lowres")]
        pair = matching_pairs(records, "new_dataset", "new_dataset_backup_lowres")
        self.assertEqual(len(pair), 1)
        self.assertEqual(pair[0][0]["cohort"], "new_dataset")
        self.assertEqual(pair[0][1]["cohort"], "new_dataset_backup_lowres")

    def test_discovery_excludes_noncanonical_and_keeps_backup_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for folder in ("figaro1k/lurus", "figaro1k/extra", "new_dataset/sangat keriting",
                           "new_dataset/sangat-keriting_backup_lowres", "new_dataset/misc_backup_lowres"):
                path = root / folder
                path.mkdir(parents=True)
                (path / "x.jpg").write_bytes(b"not decoded during discovery")
            rows = discover(root)
            self.assertEqual({(r["cohort"], r["hair_class"]) for r in rows},
                             {("figaro1k", "lurus"), ("new_dataset", "sangat-keriting"),
                              ("new_dataset_backup_lowres", "sangat-keriting")})


if __name__ == "__main__":
    unittest.main()
