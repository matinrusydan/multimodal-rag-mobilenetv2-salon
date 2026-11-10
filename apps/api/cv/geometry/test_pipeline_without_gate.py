"""Regression tests for the active hair-classification pipeline."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


CV_DIR = Path(__file__).resolve().parents[1]
if str(CV_DIR) not in sys.path:
    sys.path.insert(0, str(CV_DIR))

from pipeline import run
from pipeline.adapters import local_model_paths, model_paths


class PipelineWithoutGateTests(unittest.TestCase):
    def test_main_preprocesses_and_runs_both_classifiers(self) -> None:
        tensor = object()
        outputs = [
            {"label": "lurus", "confidence": 0.9},
            {"label": "panjang", "confidence": 0.8},
        ]
        with (
            patch.object(sys, "argv", ["run.py", "--image", "photo.jpg", "--json"]),
            patch.object(run, "preprocess_file", return_value=(tensor, None)) as preprocess,
            patch.object(run, "run_onnx", side_effect=outputs) as infer,
            patch("pipeline.adapters.model_paths", return_value={
                "hair_type": "type.onnx", "hair_length": "length.onnx"
            }),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            run.main()

        preprocess.assert_called_once_with("photo.jpg")
        self.assertEqual(infer.call_count, 2)
        self.assertEqual(infer.call_args_list[0].args[1], tensor)
        self.assertEqual(infer.call_args_list[1].args[1], tensor)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["decision"], "ok")
        self.assertEqual(result["hair_type"], outputs[0])
        self.assertEqual(result["hair_length"], outputs[1])
        self.assertEqual(set(result.keys()), {"image", "decision", "hair_type", "hair_length"})

    def test_adapters_only_map_hair_models(self) -> None:
        self.assertEqual(set(model_paths()), {"hair_type", "hair_length"})
        self.assertEqual(set(local_model_paths()), {"hair_type", "hair_length"})

    def test_pipeline_import_does_not_load_mediapipe(self) -> None:
        self.assertNotIn("mediapipe", sys.modules)


if __name__ == "__main__":
    unittest.main()
