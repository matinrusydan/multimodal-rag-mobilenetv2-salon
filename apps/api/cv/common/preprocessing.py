# -*- coding: utf-8 -*-
"""Preprocessing gambar — konsisten untuk training & inference.

Pipeline: decode RGB -> auto-orient EXIF -> resize keep-aspect (sisi pendek 256)
-> center-crop 224 -> normalize ImageNet -> NCHW float32.

Opsional: CLAHE (anti-gelap) untuk kondisi pencahayaan ekstrem.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

from common.constants import IMAGENET_MEAN, IMAGENET_STD, INPUT_SIZE, RESIZE_SIDE

MIN_SIDE = 224


def roi_crop(img: Image.Image, size: int = INPUT_SIZE) -> np.ndarray:
    """Resize keep-aspect (sisi pendek RESIZE_SIDE) -> center-crop `size` -> RGB uint8."""
    w, h = img.size
    scale = RESIZE_SIDE / min(h, w)
    rw = max(size, round(w * scale))
    rh = max(size, round(h * scale))
    resized = img.resize((rw, rh), Image.Resampling.BILINEAR)
    left = (rw - size) // 2
    top = (rh - size) // 2
    crop = resized.crop((left, top, left + size, top + size))
    return np.asarray(crop.convert("RGB"), dtype=np.uint8)


def to_nchw(rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 [H,W,3] -> NCHW float32 [1,3,H,W] ImageNet-normalized."""
    f = rgb.astype(np.float32) / 255.0
    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std = np.array(IMAGENET_STD, dtype=np.float32)
    normalized = (f - mean) / std
    tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...]
    return np.ascontiguousarray(tensor)


def preprocess_bytes(buffer: bytes) -> tuple[np.ndarray, np.ndarray]:
    """Bytes gambar -> (tensor NCHW float32 [1,3,224,224], roi RGB uint8 [224,224,3])."""
    try:
        with Image.open(io.BytesIO(buffer)) as im:
            im = ImageOps.exif_transpose(im)
            if min(im.size) < MIN_SIDE:
                raise ValueError(f"Gambar terlalu kecil (< {MIN_SIDE}px)")
            rgb = roi_crop(im)
    except Exception as exc:
        raise ValueError(f"Gambar tidak dapat dibaca: {exc}") from exc
    return to_nchw(rgb), rgb


def preprocess_file(path) -> tuple[np.ndarray, np.ndarray]:
    """Path gambar -> (tensor NCHW, roi RGB)."""
    with open(path, "rb") as f:
        return preprocess_bytes(f.read())


def apply_clahe(rgb: np.ndarray, clip: float = 2.0, grid: int = 8) -> np.ndarray:
    """CLAHE opsional untuk pencahayaan ekstrem (butuh opencv)."""
    try:
        import cv2
    except Exception:
        return rgb
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
