"""Unit tests for Phase 3/4 geometry estimation: length, volume, and tied-hair detection."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from detect_tied_hair import classify_tied_hair, extract_shape_features
from measure_length import (
    classify_length_from_ratios,
    detect_clothing_and_body_shoulder,
    estimate_cranial_reference,
    filter_hair_mask_with_person,
    measure_hair_length,
)
from measure_volume import classify_volume_from_ratios, measure_hair_volume


class GeometricLengthTests(unittest.TestCase):
    def test_empty_mask(self):
        mask = np.zeros((100, 100), dtype=np.uint8)
        res = measure_hair_length(mask)
        self.assertEqual(res["status"], "empty_mask")
        self.assertIsNone(res["predicted_class"])

    def test_short_hair_pose_free(self):
        # Create a short hair mask: head dome width ~80px, height ~80px -> H_head ~104px
        # Hair span 80px -> head_units ~ 0.77 (< 1.0) -> 'pendek'
        mask = np.zeros((300, 300), dtype=np.uint8)
        cv2.ellipse(mask, (150, 80), (40, 40), 0, 0, 360, 255, -1)
        res = measure_hair_length(mask)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["method"], "pose_free_silhouette")
        self.assertEqual(res["predicted_class"], "pendek")
        self.assertLess(res["head_units"], 1.0)

    def test_long_hair_pose_free(self):
        # Cranial width ~80px -> H_head ~104px
        # Long cascading hair from y=30 to y=280 -> span 250px -> head_units ~ 2.4 -> 'panjang'
        mask = np.zeros((300, 300), dtype=np.uint8)
        cv2.rectangle(mask, (110, 30), (190, 280), 255, -1)
        res = measure_hair_length(mask)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["method"], "pose_free_silhouette")
        self.assertEqual(res["predicted_class"], "panjang")
        self.assertGreater(res["head_units"], 2.1)

    def test_pose_guided_shoulder_anchor(self):
        # Image 300x300, hair from y=20 to y=200 (span 180)
        mask = np.zeros((300, 300), dtype=np.uint8)
        cv2.rectangle(mask, (110, 20), (190, 200), 255, -1)
        # Valid pose shoulder at y=0.60 * 300 = 180 (width 0.50 * 300 = 150)
        pose = {
            "shoulder_L": {"x": 0.25, "y": 0.60, "visibility": 0.9},
            "shoulder_R": {"x": 0.75, "y": 0.60, "visibility": 0.9},
        }
        res = measure_hair_length(mask, pose_landmarks=pose)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["method"], "pose_guided")
        self.assertAlmostEqual(res["keypoints"]["y_shoulder"], 180.0, delta=1.0)
        # Hair span = 200 - 20 + 1 = 181. dist_to_shoulder = 180 - 20 = 160.
        # r_shoulder = 181 / 160 ≈ 1.131 -> 'pendek-menengah'
        self.assertAlmostEqual(res["relative_shoulder_ratio"], 1.13, places=2)
        self.assertEqual(res["predicted_class"], "pendek-menengah")

    def test_classify_length_thresholds(self):
        self.assertEqual(classify_length_from_ratios(0.50, 0.70)[0], "pendek")
        self.assertEqual(classify_length_from_ratios(0.95, 1.25)[0], "pendek-menengah")
        self.assertEqual(classify_length_from_ratios(1.40, 1.85)[0], "menengah")
        self.assertEqual(classify_length_from_ratios(1.90, 2.50)[0], "panjang")

    def test_clothing_and_body_shoulder_calibration(self):
        # 300x300 image with white background, hair mask in center (y=20..180, x=100..200)
        img = np.full((300, 300, 3), 250, dtype=np.uint8)
        mask = np.zeros((300, 300), dtype=np.uint8)
        mask[20:180, 100:200] = 255

        # Clothing in dark color (e.g. BGR=[50, 50, 180]) on left/right flanks at y=120..290
        img[120:290, 20:280] = [50, 50, 180]
        # Restore hair region color
        img[20:180, 100:200] = [30, 30, 30]

        res = measure_hair_length(mask, image_bgr=img)
        self.assertEqual(res["status"], "ok")
        self.assertIn(res["method"], ["clothing_color", "clothing_and_body"])
        self.assertAlmostEqual(res["keypoints"]["y_shoulder"], 120.0, delta=15.0)

    def test_person_mask_artifact_filtering(self):
        # 400x400 image: person body at x=100..300, y=50..380
        person_mask = np.zeros((400, 400), dtype=np.uint8)
        person_mask[50:380, 100:300] = 255

        # Hair mask with real hair on head (y=50..200, x=130..270)
        # and a spurious disconnected background artifact (e.g. building at y=60..150, x=330..390)
        hair_mask = np.zeros((400, 400), dtype=np.uint8)
        hair_mask[50:200, 130:270] = 255
        hair_mask[60:150, 330:390] = 255  # completely outside person

        cleaned = filter_hair_mask_with_person(hair_mask, person_mask)
        self.assertEqual(cleaned[60:150, 330:390].sum(), 0)
        self.assertEqual(cleaned[50:200, 130:270].sum(), hair_mask[50:200, 130:270].sum())


class GeometricVolumeTests(unittest.TestCase):
    def test_empty_mask_volume(self):
        mask = np.zeros((100, 100), dtype=np.uint8)
        res = measure_hair_volume(mask)
        self.assertEqual(res["status"], "empty_mask")
        self.assertIsNone(res["volume_class"])

    def test_thin_vs_thick_volume(self):
        # Thin: low-volume crown dome (w=80, h=40 -> cranial width 80 -> H_head 104, area ~2513 -> R_vol ~0.23)
        thin_mask = np.zeros((200, 200), dtype=np.uint8)
        cv2.ellipse(thin_mask, (100, 50), (40, 20), 0, 0, 360, 255, -1)
        res_thin = measure_hair_volume(thin_mask)
        self.assertEqual(res_thin["status"], "ok")
        self.assertEqual(res_thin["volume_class"], "tipis")
        self.assertLessEqual(res_thin["volume_ratio"], 0.70)

        # Thick: cranial top spans top ~25% of image (400x400 -> top 100px has w=40), then flares wide to w=160
        thick_mask = np.zeros((400, 400), dtype=np.uint8)
        cv2.rectangle(thick_mask, (180, 10), (220, 110), 255, -1)
        cv2.rectangle(thick_mask, (120, 110), (280, 350), 255, -1)
        res_thick = measure_hair_volume(thick_mask)
        self.assertEqual(res_thick["status"], "ok")
        self.assertEqual(res_thick["volume_class"], "tebal")
        self.assertGreater(res_thick["width_ratio"], 2.0)

    def test_classify_volume_thresholds(self):
        self.assertEqual(classify_volume_from_ratios(0.50, 1.05)[0], "tipis")
        self.assertEqual(classify_volume_from_ratios(0.95, 1.20)[0], "sedang")
        self.assertEqual(classify_volume_from_ratios(1.60, 1.45)[0], "tebal")


class CalibratedTiedHairTests(unittest.TestCase):
    def test_ponytail_detection(self):
        # Force a clear connected ponytail band with lower hull solidity
        pony = np.zeros((300, 200), dtype=np.uint8)
        cv2.ellipse(pony, (100, 70), (45, 35), 0, 0, 360, 255, -1)
        cv2.rectangle(pony, (94, 95), (106, 150), 255, -1)
        cv2.ellipse(pony, (100, 215), (42, 70), 0, 0, 360, 255, -1)
        res = classify_tied_hair(pony, hair_type="lurus")
        self.assertEqual(res["status"], "calibrated")
        self.assertTrue(res["tied"])
        self.assertEqual(res["style"], "ponytail")

    def test_bun_detection_vs_afro_exclusion(self):
        bun = np.zeros((300, 300), dtype=np.uint8)
        cv2.circle(bun, (150, 100), 45, 255, -1)
        res_bun = classify_tied_hair(bun, hair_type="lurus")
        self.assertTrue(res_bun["tied"])
        self.assertEqual(res_bun["style"], "bun")

        # Same circular shape on kinky/afro hair should NOT be flagged as tied bun
        res_afro = classify_tied_hair(bun, hair_type="sangat-keriting")
        self.assertFalse(res_afro["tied"])
        self.assertEqual(res_afro["style"], "loose")

    def test_loose_hair_detection(self):
        loose = np.zeros((300, 200), dtype=np.uint8)
        pts = np.array([[75, 40], [125, 40], [155, 270], [45, 270]], dtype=np.int32)
        cv2.fillPoly(loose, [pts], 255)
        res = classify_tied_hair(loose, hair_type="bergelombang")
        self.assertEqual(res["status"], "calibrated")
        self.assertFalse(res["tied"])
        self.assertEqual(res["style"], "loose")


if __name__ == "__main__":
    unittest.main()
