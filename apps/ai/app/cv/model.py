"""MobileNetV2 ONNX inference via onnxruntime (Python).

Reuses the existing exported models:
  - hair_type.onnx  : trained from figaro1k (4 hair-type classes).
  - hair_length.onnx: pending labeled dataset -> fallback low_confidence 'menengah'.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import onnxruntime as ort

from app.config import settings
from app.cv.labels import HAIR_LENGTH_LABELS, HAIR_TYPE_LABELS

logger = logging.getLogger(__name__)

INPUT_NAME = "input"
OUTPUT_NAME = "logits"


class CvModel:
    """Lazy-loaded onnxruntime sessions for hair-type (and hair-length when available)."""

    def __init__(self) -> None:
        self._type_session: ort.InferenceSession | None = None
        self._length_session: ort.InferenceSession | None = None

    @staticmethod
    def _load(path: Path) -> ort.InferenceSession | None:
        if not path.exists():
            logger.warning("Model tidak ditemukan: %s", path)
            return None
        try:
            session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            logger.info("ONNX dimuat: %s (%s)", path.name, path)
            return session
        except Exception as exc:  # corrupt/unsupported model file
            logger.warning("Gagal memuat model %s: %s", path, exc)
            return None

    @property
    def type_session(self) -> ort.InferenceSession | None:
        if self._type_session is None and settings.model_type_path:
            self._type_session = self._load(settings.model_type_path)
        return self._type_session

    @property
    def length_session(self) -> ort.InferenceSession | None:
        if self._length_session is None and settings.model_length_path:
            self._length_session = self._load(settings.model_length_path)
        return self._length_session

    @staticmethod
    def _run(session: ort.InferenceSession, tensor: np.ndarray) -> np.ndarray:
        result = session.run([OUTPUT_NAME], {INPUT_NAME: tensor})
        if not result:
            raise ValueError("Output ONNX kosong")
        outputs = result[0]
        logits = np.asarray(outputs, dtype=np.float32)
        if logits.ndim == 1:
            logits = logits[np.newaxis, ...]
        if logits.shape[0] == 0:
            raise ValueError("Output ONNX kosong")
        return logits[0]

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x))
        return e / np.sum(e)

    def classify_type(self, tensor: np.ndarray) -> dict:
        """Return {"label": <HairTypeLabel>, "confidence": float} or raise if no model."""
        session = self.type_session
        if session is None:
            raise RuntimeError("Model hair_type tidak tersedia")
        logits = self._run(session, tensor)
        probs = self._softmax(logits)
        idx = int(np.argmax(probs))
        return {"label": HAIR_TYPE_LABELS[idx], "confidence": round(float(probs[idx]), 4)}

    def classify_length(self, tensor: np.ndarray) -> dict:
        """Return {"label": <HairLengthLabel>, "confidence": float} (ONNX bila ada)."""
        session = self.length_session
        if session is None:
            # Pending labeled dataset -> fallback low confidence 'menengah'.
            return {"label": HAIR_LENGTH_LABELS[2], "confidence": 0.5}
        logits = self._run(session, tensor)
        probs = self._softmax(logits)
        idx = int(np.argmax(probs))
        return {"label": HAIR_LENGTH_LABELS[idx], "confidence": round(float(probs[idx]), 4)}


cv_model = CvModel()