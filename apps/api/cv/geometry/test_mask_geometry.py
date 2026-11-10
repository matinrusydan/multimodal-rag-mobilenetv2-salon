"""Tests for binary mask cleanup and tied-hair descriptive geometry."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from detect_tied_hair import assess_tied_hair, detect_tied_hair, extract_shape_features
from threshold_binary import cleanup_mask


class CleanupMaskTests(unittest.TestCase):
    def test_binary_identity_and_copy(self):
        source = np.array([[0, 255], [255, 0]], dtype=np.uint8)
        original = source.copy()
        result = cleanup_mask(source)
        np.testing.assert_array_equal(result, source)
        np.testing.assert_array_equal(source, original)
        self.assertIsNot(result, source)
        self.assertEqual(result.dtype, np.uint8)

    def test_float_threshold(self):
        result = cleanup_mask(np.array([[0.2, 0.5, 1.0]], dtype=np.float32))
        np.testing.assert_array_equal(result, [[0, 255, 255]])

    def test_validation(self):
        for invalid in (np.zeros((2, 2, 1)), np.array([[np.nan]]), np.array([[2]], dtype=np.uint8), np.array([[-0.1]])):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    cleanup_mask(invalid)
        for kwargs in ({"threshold": 1.1}, {"opening_kernel": 2}, {"closing_kernel": -1}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    cleanup_mask(np.zeros((3, 3), np.uint8), **kwargs)

    def test_opening_removes_isolated_pixel_and_closing_fills_gap(self):
        mask = np.zeros((9, 9), np.uint8)
        mask[4, 4] = 255
        self.assertEqual(int(cleanup_mask(mask, opening_kernel=3).sum()), 0)
        gap = np.zeros((9, 9), np.uint8)
        gap[3:6, 2:4] = 255
        gap[3:6, 5:7] = 255
        self.assertEqual(int(cleanup_mask(gap, closing_kernel=3)[4, 4]), 255)

    def test_fill_holes_and_largest_component(self):
        mask = np.zeros((11, 11), np.uint8)
        mask[2:9, 2:9] = 255
        mask[4:7, 4:7] = 0
        self.assertEqual(cleanup_mask(mask, fill_holes=True)[5, 5], 255)

        # Test fill_holes when foreground touches (0, 0)
        touching_corner = np.zeros((5, 5), np.uint8)
        touching_corner[0, 0] = 255
        filled_corner = cleanup_mask(touching_corner, fill_holes=True)
        self.assertEqual(filled_corner[0, 0], 255)
        self.assertEqual(filled_corner[2, 2], 0)
        self.assertEqual(int(filled_corner.sum()), 255)

        mask[0, 0] = 255
        largest = cleanup_mask(mask, largest_component=True)
        self.assertEqual(largest[0, 0], 0)
        self.assertEqual(largest[3, 3], 255)


class ShapeFeatureTests(unittest.TestCase):
    def test_empty_safe_and_detector_uncalibrated(self):
        mask = np.zeros((8, 9), np.uint8)
        features = extract_shape_features(mask)
        self.assertEqual(features["pixel_area"], 0)
        self.assertEqual(features["area_pixels"], 0)
        self.assertIsNone(features["bbox"])
        self.assertIsNone(features["circularity"])
        self.assertIsNone(features["solidity"])
        detected = assess_tied_hair(mask)
        self.assertIsNone(detected["tied"])
        self.assertIsNone(detected["confidence"])
        self.assertEqual(detected["status"], "uncalibrated")

    def test_rectangle_metrics_and_inclusive_bbox(self):
        mask = np.zeros((10, 12), np.uint8)
        mask[2:6, 3:8] = 255
        features = extract_shape_features(mask)
        self.assertEqual(features["pixel_area"], 20)
        self.assertEqual(features["area_pixels"], 20)
        self.assertEqual(features["bbox"], {"x": 3, "y": 2, "width": 5, "height": 4})
        self.assertEqual(features["max_row_width"], 5)
        self.assertEqual(features["component_count"], 1)
        self.assertEqual(features["contour_area"], 12.0)
        self.assertIsNotNone(features["circularity"])
        self.assertIsNotNone(features["solidity"])

    def test_multicomponent_border_and_degenerate_masks(self):
        multi = np.zeros((8, 8), np.uint8)
        multi[1:3, 1:3] = 255
        multi[6, 7] = 255
        feats = extract_shape_features(multi)
        self.assertEqual(feats["component_count"], 2)
        self.assertTrue(feats["border_contact"])
        self.assertTrue(feats["cropped"])
        for points in ([(2, 2)], [(2, 2), (2, 3), (2, 4)]):
            mask = np.zeros((7, 7), np.uint8)
            for y, x in points:
                mask[y, x] = 255
            feats = extract_shape_features(mask)
            self.assertEqual(feats["pixel_area"], len(points))
            self.assertIsNone(feats["circularity"])
            self.assertIsNone(feats["solidity"])


if __name__ == "__main__":
    unittest.main()
