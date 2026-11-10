"""Boundary tests for the exploratory training-only batch runner."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import extract_mask_features as runner


class FeatureRunnerTests(unittest.TestCase):
    def test_training_only_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            model = root / "model.onnx"
            model.write_bytes(b"fake model for mocked session")
            records = [{"image_id": "figaro1k/lurus/00010.jpg", "split": split,
                        "approved_label": "lurus"} for split in ("train", "val", "test")]
            manifest.write_text(json.dumps({"records": records}), encoding="utf-8")
            out = root / "results"
            with patch.object(runner, "HairSegmenter") as factory, patch.object(runner, "save_mask_and_overlay"):
                factory.return_value.predict_file.return_value = {
                    "mask": np.ones((16, 16), dtype=np.uint8) * 255,
                    "orig_size": [16, 16], "hair_coverage": 1.0,
                }
                report = runner.run(manifest, model, out)
                self.assertEqual(report["n"], 1)
                factory.return_value.predict_file.assert_called_once()
                self.assertEqual(report["gate"]["status"], "NOT_ASSESSED")
                self.assertIsNone(report["records"][0]["length"]["value"])
                self.assertIsNone(report["records"][0]["mask_shape_assessment"]["tied"])
                self.assertTrue((out / "mask_features.json").is_file())
                with self.assertRaises(FileExistsError):
                    runner.run(manifest, model, out)

    def test_output_escape_and_bad_limit_rejected_before_loading(self):
        with self.assertRaises(ValueError):
            runner.run(Path("missing.json"), Path("missing.onnx"), runner.HERE.parent / "escape")
        with self.assertRaises(ValueError):
            runner.run(Path("missing.json"), Path("missing.onnx"), runner.HERE / "not_created", limit=0)


if __name__ == "__main__":
    unittest.main()
