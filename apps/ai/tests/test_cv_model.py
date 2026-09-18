"""Tests for CvModel — softmax/argmax logic and hair_length fallback.

Uses a fake ONNX session so no real model file / onnxruntime session is needed.
"""

import numpy as np

from app.cv.model import CvModel


class FakeSession:
    """Minimal stand-in for ort.InferenceSession returning fixed logits."""

    def __init__(self, logits: np.ndarray) -> None:
        self._logits = logits.astype(np.float32)

    def run(self, output_names, input_feed):  # noqa: ARG002 (mimic ort signature)
        return [self._logits]


def test_softmax_sums_to_one():
    x = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    p = CvModel._softmax(x)
    assert np.isclose(p.sum(), 1.0)
    assert np.all(p >= 0)


def test_softmax_is_invariant_to_shift():
    x = np.array([100.0, 200.0], dtype=np.float32)
    p = CvModel._softmax(x)
    assert np.all(np.isfinite(p))  # tidak overflow
    assert np.isclose(p.sum(), 1.0)


def test_classify_type_argmax_and_confidence():
    model = CvModel()
    # logits: kelas 2 (keriting) paling tinggi
    model._type_session = FakeSession(np.array([[0.1, 0.2, 5.0, 0.3]]))
    result = model.classify_type(np.zeros((1, 3, 224, 224), dtype=np.float32))
    assert result["label"] == "keriting"
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["confidence"] > 0.9


def test_classify_type_without_session_raises():
    model = CvModel()
    model._type_session = None
    model._length_session = None
    # paksa path tanpa model: settings.model_type_path menunjuk file tidak ada -> None
    import app.cv.model as mod
    from app.config import settings

    original = settings.model_type_path
    try:
        settings.model_type_path = None  # type: ignore[assignment]
        model._type_session = None
        try:
            model.classify_type(np.zeros((1, 3, 224, 224), dtype=np.float32))
            raise AssertionError("harusnya raise RuntimeError")
        except RuntimeError as exc:
            assert "tidak tersedia" in str(exc)
    finally:
        settings.model_type_path = original
        mod  # noqa: B018


def test_classify_length_fallback_when_no_model():
    model = CvModel()
    model._length_session = None
    from app.config import settings

    original = settings.model_length_path
    try:
        settings.model_length_path = None  # type: ignore[assignment]
        model._length_session = None
        result = model.classify_length(np.zeros((1, 3, 224, 224), dtype=np.float32))
        # Fallback jujur: label tengah + confidence 0.5 (akan dinilai low_confidence).
        assert result["label"] == "menengah"
        assert result["confidence"] == 0.5
    finally:
        settings.model_length_path = original


def test_classify_length_uses_model_when_available():
    model = CvModel()
    # kelas 3 (panjang) paling tinggi
    model._length_session = FakeSession(np.array([[0.0, 0.0, 0.1, 9.0]]))
    result = model.classify_length(np.zeros((1, 3, 224, 224), dtype=np.float32))
    assert result["label"] == "panjang"
    assert result["confidence"] > 0.9
