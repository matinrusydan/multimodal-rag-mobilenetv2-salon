"""Unit tests for Phase 4 Hierarchical Classification Pipeline."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from classify_hierarchical import (
    HairTypeClassifier,
    HierarchicalHairPipeline,
    preprocess_for_hair_type,
    required_attributes_for_type,
    softmax,
)


class ClassifyHierarchicalTests(unittest.TestCase):
    def test_required_attributes(self):
        self.assertEqual(required_attributes_for_type("lurus"), ["length"])
        self.assertEqual(required_attributes_for_type("bergelombang"), ["length"])
        self.assertEqual(required_attributes_for_type("keriting"), ["length", "volume"])
        self.assertEqual(required_attributes_for_type("sangat-keriting"), ["volume"])
        with self.assertRaises(ValueError):
            required_attributes_for_type("unknown_type")

    def test_softmax_function(self):
        logits = np.array([2.0, 1.0, 0.1, -1.0])
        probs = softmax(logits)
        self.assertAlmostEqual(float(probs.sum()), 1.0, places=5)
        self.assertTrue((probs >= 0.0).all())
        self.assertEqual(int(np.argmax(probs)), 0)

    def test_preprocess_for_hair_type(self):
        img = Image.new("RGB", (400, 600), color=(128, 128, 128))
        tensor = preprocess_for_hair_type(img, resize_side=256, crop_size=224)
        self.assertEqual(tensor.shape, (1, 3, 224, 224))
        self.assertEqual(tensor.dtype, np.float32)

    def test_hierarchical_pipeline_mocked(self):
        with patch.object(HairTypeClassifier, "__init__", return_value=None), \
             patch.object(HairTypeClassifier, "predict_pil") as mock_type, \
             patch("classify_hierarchical.HairSegmenter.__init__", return_value=None), \
             patch("classify_hierarchical.HairSegmenter.predict_pil") as mock_seg:

            mock_type.return_value = {
                "predicted_class": "keriting",
                "confidence": 0.88,
                "probabilities": {
                    "lurus": 0.02,
                    "bergelombang": 0.05,
                    "keriting": 0.88,
                    "sangat-keriting": 0.05,
                },
                "latency_ms": 12.3,
            }
            mask = np.zeros((100, 100), dtype=np.uint8)
            mask[20:80, 20:80] = 255
            mock_seg.return_value = {
                "mask": mask,
                "hair_coverage": 0.36,
                "orig_size": [100, 100],
                "latency_ms": 25.1,
            }

            pipeline = HierarchicalHairPipeline(type_onnx=Path("fake_type.onnx"), seg_onnx=Path("fake_seg.onnx"))
            dummy_img = Image.new("RGB", (100, 100), color="white")
            res, cleaned_mask = pipeline.predict_pil(dummy_img)

            self.assertEqual(res["decision"], "ok")
            self.assertEqual(res["stage1_hair_type"]["predicted_class"], "keriting")
            self.assertEqual(res["stage2_segmentation"]["hair_coverage"], 0.36)
            self.assertEqual(res["stage2_conditional_attributes"]["target_attributes"], ["length", "volume"])
            self.assertEqual(res["stage2_conditional_attributes"]["length"]["status"], "blocked_phase0_gate")
            self.assertEqual(res["stage2_conditional_attributes"]["volume"]["status"], "reference_not_validated")
            self.assertIsNone(res["tied_hair_assessment"]["tied"])
            self.assertEqual(res["tied_hair_assessment"]["status"], "uncalibrated")
            self.assertEqual(cleaned_mask.shape, (100, 100))


if __name__ == "__main__":
    unittest.main()
