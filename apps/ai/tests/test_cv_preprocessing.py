"""Tests for CV preprocessing pipeline (decode -> EXIF -> resize 256 -> crop 224 -> ImageNet NCHW).

No model/network needed — pure image transforms.
"""

import io

import numpy as np
import pytest
from PIL import Image

from app.cv.preprocessing import CROP, IMAGENET_MEAN, IMAGENET_STD, preprocess


def _png_bytes(width: int, height: int, color=(120, 80, 60)) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_preprocess_returns_nchw_tensor_and_roi():
    tensor, roi = preprocess(_png_bytes(500, 600))
    assert tensor.shape == (1, 3, CROP, CROP), "tensor harus NCHW 1x3x224x224"
    assert tensor.dtype == np.float32
    assert roi.shape == (CROP, CROP, 3)
    assert roi.dtype == np.uint8


def test_preprocess_normalization_is_imagenet():
    # Pixel constant -> setelah normalisasi nilai ≈ (c/255 - mean) / std untuk tiap kanal.
    color = (255, 128, 0)
    tensor, roi = preprocess(_png_bytes(300, 300, color))
    for c in range(3):
        expected = (color[c] / 255.0 - IMAGENET_MEAN[c]) / IMAGENET_STD[c]
        assert np.allclose(tensor[0, c], expected, atol=1e-5), f"kanal {c} tidak ternormalisasi ImageNet"
    # ROI tetap nilai asli 0..255 (untuk ekstraksi fitur warna/tekstur).
    assert np.all(roi[..., 0] == color[0])


def test_preprocess_center_crop_is_square():
    # Input non-square -> crop tetap 224x224 (keep-aspect lalu center-crop).
    tensor, roi = preprocess(_png_bytes(800, 300))
    assert tensor.shape == (1, 3, CROP, CROP)
    assert roi.shape == (CROP, CROP, 3)


def test_preprocess_rejects_small_image():
    with pytest.raises(ValueError, match="terlalu kecil"):
        preprocess(_png_bytes(100, 100))


def test_preprocess_rejects_non_image():
    with pytest.raises(ValueError, match="tidak dapat dibaca"):
        preprocess(b"ini bukan gambar")


def test_preprocess_handles_exif_orientation():
    # Gambar landscape dengan EXIF orientation 6 (rotate 90) -> tetap diproses tanpa error.
    img = Image.new("RGB", (600, 400), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    tensor, roi = preprocess(buf.getvalue())
    assert tensor.shape == (1, 3, CROP, CROP)
    assert roi.shape == (CROP, CROP, 3)


def test_preprocess_accepts_jpeg_and_webp():
    for fmt in ("JPEG", "WEBP"):
        img = Image.new("RGB", (400, 400), (50, 60, 70))
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        tensor, _ = preprocess(buf.getvalue())
        assert tensor.shape == (1, 3, CROP, CROP), f"format {fmt} gagal"
