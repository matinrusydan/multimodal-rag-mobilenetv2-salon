"""Unit tests for Phase 4 Hair Type model architecture, metrics, and dataset loading."""
from __future__ import annotations

import sys
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

import numpy as np
import torch
from PIL import Image

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from hair_type_model import HAIR_TYPE_CLASSES, build_hair_type_model, export_hair_type_onnx
from train_hair_type import (
    CLASS_TO_IDX,
    HairTypeDataset,
    compute_classification_metrics,
    load_hair_type_split_records,
    evaluate_model,
)


class HairTypeModelTests(unittest.TestCase):
    def test_export_has_local_torch_dependency(self):
        model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(3 * 8 * 8, 4))
        with tempfile.TemporaryDirectory() as directory, patch('torch.onnx.export') as export:
            target = Path(directory) / 'model.onnx'
            self.assertEqual(export_hair_type_onnx(model, target, img_size=8), target)
            self.assertEqual(export.call_args.args[1].shape, (1, 3, 8, 8))

    def test_model_build_and_forward_shapes(self):
        for arch in ("mobilenet_v2", "efficientnet_v2_s"):
            model = build_hair_type_model(arch=arch, pretrained=False, num_classes=4, dropout=0.2)
            model.eval()
            dummy = torch.randn(2, 3, 224, 224)
            with torch.no_grad():
                logits = model(dummy)
            self.assertEqual(logits.shape, (2, 4))

    def test_unsupported_arch_raises(self):
        with self.assertRaises(ValueError):
            build_hair_type_model(arch="unsupported_arch")


class ClassificationMetricsTests(unittest.TestCase):
    def test_three_class_evaluation_does_not_change_canonical_labels(self):
        classes = ['lurus', 'bergelombang', 'keriting']
        loader = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(
            torch.eye(3) * 10, torch.arange(3)), batch_size=3)
        result = evaluate_model(torch.nn.Identity(), loader, torch.nn.CrossEntropyLoss(), torch.device('cpu'), classes)
        self.assertEqual(result['macro_f1'], 1.0)
        self.assertEqual(set(result['per_class']), set(classes))
        self.assertEqual(len(result['confusion_matrix']), 3)
        self.assertEqual(len(HAIR_TYPE_CLASSES), 4)

    def test_perfect_predictions(self):
        probs = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        targets = np.array([0, 1, 2, 3])
        metrics = compute_classification_metrics(probs, targets, HAIR_TYPE_CLASSES)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["macro_f1"], 1.0)
        self.assertEqual(metrics["weighted_f1"], 1.0)
        self.assertEqual(metrics["ece"], 0.0)
        self.assertEqual(metrics["confusion_matrix"], np.eye(4, dtype=int).tolist())

    def test_imbalanced_and_zero_support(self):
        probs = np.array([
            [0.8, 0.2, 0.0, 0.0],
            [0.1, 0.9, 0.0, 0.0],
        ])
        targets = np.array([0, 1])
        metrics = compute_classification_metrics(probs, targets, HAIR_TYPE_CLASSES)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["per_class"]["keriting"]["support"], 0)
        self.assertEqual(metrics["per_class"]["keriting"]["f1"], 0.0)
        # Macro-F1 across 4 classes: (1.0 + 1.0 + 0.0 + 0.0) / 4 = 0.5
        self.assertEqual(metrics["macro_f1"], 0.5)

    def test_empty_predictions_safe(self):
        metrics = compute_classification_metrics(np.zeros((0, 4)), np.zeros(0, dtype=int), HAIR_TYPE_CLASSES)
        self.assertEqual(metrics["accuracy"], 0.0)
        self.assertEqual(metrics["macro_f1"], 0.0)
        self.assertEqual(metrics["ece"], 0.0)


class HairTypeDatasetTests(unittest.TestCase):
    def test_manifest_split_integrity(self):
        manifest_path = HERE / "reports" / "phase1" / "curated_manifest.json"
        dataset_dir = HERE.parent / "dataset"
        splits = load_hair_type_split_records(manifest_path, dataset_dir)

        self.assertEqual(len(splits["train"]), 269)
        self.assertEqual(len(splits["val"]), 57)
        self.assertEqual(len(splits["test"]), 59)

        # Zero leakage between splits
        train_ids = {r["image_id"] for r in splits["train"]}
        val_ids = {r["image_id"] for r in splits["val"]}
        test_ids = {r["image_id"] for r in splits["test"]}
        self.assertEqual(len(train_ids.intersection(val_ids)), 0)
        self.assertEqual(len(train_ids.intersection(test_ids)), 0)
        self.assertEqual(len(val_ids.intersection(test_ids)), 0)

    def test_dataset_transforms(self):
        records = [{
            "image_id": "figaro1k/lurus/00010.jpg",
            "img_path": HERE.parent / "dataset" / "figaro1k" / "lurus" / "00010.jpg",
            "class_idx": 0,
        }]
        ds = HairTypeDataset(records, img_size=224, augment=False)
        tensor, label = ds[0]
        self.assertEqual(tensor.shape, (3, 224, 224))
        self.assertEqual(label, 0)
        self.assertEqual(tensor.dtype, torch.float32)


if __name__ == "__main__":
    unittest.main()
