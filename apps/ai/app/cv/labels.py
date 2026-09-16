"""Label mapping for hair classification — MUST match shared-types constants.

These class names appear all over CV, RAG prompt, and UI. Do not change casually.
"""

HAIR_LENGTH_LABELS: list[str] = [
    "pendek",
    "pendek-menengah",
    "menengah",
    "panjang",
]

HAIR_TYPE_LABELS: list[str] = [
    "lurus",
    "bergelombang",
    "keriting",
    "sangat-keriting",
]