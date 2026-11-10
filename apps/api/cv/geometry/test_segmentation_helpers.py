"""Unit tests for Phase 2 UNet hair segmentation pipeline and inference."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from segment_infer import preprocess_for_segmentation, save_mask_and_overlay, sigmoid

TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None


class Phase2SegmentationHelpersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_preprocess_for_segmentation_shapes_and_normalization(self):
        img = Image.new("RGB", (400, 300), color=(255, 255, 255))
        tensor, orig_size = preprocess_for_segmentation(img, img_size=256)
        self.assertEqual(orig_size, (400, 300))
        self.assertEqual(tensor.shape, (1, 3, 256, 256))
        self.assertEqual(tensor.dtype, np.float32)
        # White (1.0) normalized with ImageNet mean/std should be positive
        self.assertGreater(float(tensor.min()), 2.0)

    def test_sigmoid_bounds(self):
        vals = sigmoid(np.array([-100.0, 0.0, 100.0], dtype=np.float32))
        self.assertAlmostEqual(float(vals[0]), 0.0, places=5)
        self.assertAlmostEqual(float(vals[1]), 0.5, places=5)
        self.assertAlmostEqual(float(vals[2]), 1.0, places=5)

    def test_save_mask_and_overlay_writes_files(self):
        img_path = self.tmp / "sample.jpg"
        Image.new("RGB", (64, 48), color=(120, 80, 60)).save(img_path)

        mask_bin = np.zeros((48, 64), dtype=np.uint8)
        mask_bin[10:38, 16:48] = 255

        mask_out = self.tmp / "out" / "mask.png"
        overlay_out = self.tmp / "out" / "overlay.jpg"
        save_mask_and_overlay(img_path, mask_bin, mask_out=mask_out, overlay_out=overlay_out)

        self.assertTrue(mask_out.exists())
        self.assertTrue(overlay_out.exists())
        with Image.open(mask_out) as mk:
            self.assertEqual(mk.size, (64, 48))
            self.assertEqual(mk.mode, "L")
        with Image.open(overlay_out) as ov:
            self.assertEqual(ov.size, (64, 48))

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch not installed yet")
    def test_unet_forward_and_loss_and_onnx_roundtrip(self):
        import onnxruntime as ort
        import torch
        from train_segmentation import compute_batch_metrics, export_to_onnx, summarize_confusion
        from unet_model import BCEDiceLoss, HairUNet, build_hair_segmentation_model

        for arch in ("scratch", "mobilenet_v2", "resnet34"):
            model = build_hair_segmentation_model(arch=arch, pretrained=False, base_features=8)
            x = torch.randn(2, 3, 64, 64)
            logits = model(x)
            self.assertEqual(tuple(logits.shape), (2, 1, 64, 64), msg=f"Failed shape for {arch}")

        model = HairUNet(in_channels=3, out_channels=1, base_features=8, bilinear=True)
        x = torch.randn(2, 3, 64, 64)
        y = (torch.rand(2, 1, 64, 64) > 0.5).float()

        logits = model(x)
        loss_fn = BCEDiceLoss(alpha=0.5)
        loss = loss_fn(logits, y)
        self.assertGreater(float(loss.item()), 0.0)

        preds = (torch.sigmoid(logits) >= 0.5).float()
        counts = compute_batch_metrics(preds, y)
        summary = summarize_confusion(counts)
        self.assertTrue(0.0 <= summary["iou"] <= 1.0)
        self.assertTrue(0.0 <= summary["dice"] <= 1.0)

        onnx_path = self.tmp / "tiny_unet.onnx"
        export_to_onnx(model, onnx_path, img_size=64)
        self.assertTrue(onnx_path.exists())
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        out = sess.run(None, {"input": np.random.randn(1, 3, 64, 64).astype(np.float32)})[0]
        self.assertEqual(out.shape, (1, 1, 64, 64))


if __name__ == "__main__":
    unittest.main()
