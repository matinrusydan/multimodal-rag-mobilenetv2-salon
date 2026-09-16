"""Preprocessing for MobileNetV2 inference — identical to training validation (task 07-cv).

Pipeline: decode RGB (sRGB) -> auto-orient from EXIF -> resize keep-aspect
(min side 256) -> center-crop 224 -> normalize per ImageNet -> NCHW float32.
Also returns the 224-224 center-crop RGB (0..255) for hair feature extraction.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

RESIZE_SIDE = 256
CROP = 224
MIN_SIDE = 224

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def _roi(img: Image.Image) -> np.ndarray:
    """Resize keep-aspect min side 256 -> center-crop 224 -> RGB uint8 array."""
    w, h = img.size
    scale = RESIZE_SIDE / min(h, w)
    rw = max(CROP, round(w * scale))
    rh = max(CROP, round(h * scale))
    resized = img.resize((rw, rh), Image.Resampling.BILINEAR)
    left = (rw - CROP) // 2
    top = (rh - CROP) // 2
    box = (left, top, left + CROP, top + CROP)
    crop = resized.crop(box)
    return np.asarray(crop.convert("RGB"), dtype=np.uint8)


def preprocess(buffer: bytes) -> tuple[np.ndarray, np.ndarray]:
    """Return (tensor NCHW float32 [1,3,224,224], roi RGB uint8 [224,224,3])."""
    try:
        with Image.open(io.BytesIO(buffer)) as im:
            im = ImageOps.exif_transpose(im)
            if min(im.size) < MIN_SIDE:
                raise ValueError(f"Gambar terlalu kecil (< {MIN_SIDE}px)")
            rgb = _roi(im)
    except Exception as exc:  # decode/EXIF/resize failures all bubble up
        raise ValueError(f"Gambar tidak dapat dibaca: {exc}") from exc

    # Normalize per ImageNet (same formula as training val).
    f = rgb.astype(np.float32) / 255.0
    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std = np.array(IMAGENET_STD, dtype=np.float32)
    normalized = (f - mean) / std

    # NCHW: [1, 3, CROP, CROP]
    tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...]
    return np.ascontiguousarray(tensor), rgb