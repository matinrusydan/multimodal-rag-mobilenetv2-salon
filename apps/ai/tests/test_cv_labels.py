"""Tests for CV label mapping — must stay identical to @rag-salon/shared-types constants.

These class names flow through CV -> RAG prompt -> UI. Changing order silently
corrupts every prediction, so we lock them here.
"""

from app.cv.labels import HAIR_LENGTH_LABELS, HAIR_TYPE_LABELS


def test_hair_length_labels_order():
    assert HAIR_LENGTH_LABELS == ["pendek", "pendek-menengah", "menengah", "panjang"]
    assert len(HAIR_LENGTH_LABELS) == 4


def test_hair_type_labels_order():
    assert HAIR_TYPE_LABELS == ["lurus", "bergelombang", "keriting", "sangat-keriting"]
    assert len(HAIR_TYPE_LABELS) == 4


def test_labels_are_unique():
    assert len(set(HAIR_LENGTH_LABELS)) == len(HAIR_LENGTH_LABELS)
    assert len(set(HAIR_TYPE_LABELS)) == len(HAIR_TYPE_LABELS)
