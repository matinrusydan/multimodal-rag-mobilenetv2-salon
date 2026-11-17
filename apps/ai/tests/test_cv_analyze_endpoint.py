"""Tests for the unified Phase 4 hierarchical CV /ai/analyze endpoint."""
from __future__ import annotations

import io
from pathlib import Path

import httpx
from PIL import Image
import pytest

from app.main import app


def _dummy_png_bytes(width: int = 300, height: int = 400) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(110, 75, 45)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_analyze_rejects_invalid_mimetype():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        res = await client.post(
            "/ai/analyze",
            files={"image": ("doc.txt", b"hello", "text/plain")},
        )
    assert res.status_code == 400
    assert "Format gambar" in res.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_rejects_small_image():
    small_png = _dummy_png_bytes(100, 100)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        res = await client.post(
            "/ai/analyze",
            files={"image": ("small.png", small_png, "image/png")},
        )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_analyze_runs_hierarchical_pipeline_on_sample_image():
    sample = Path(__file__).resolve().parents[2] / "api" / "cv" / "dataset" / "figaro1k" / "lurus" / "00001.jpg"
    if not sample.exists():
        pytest.skip("Sample dataset image not present locally")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        res = await client.post(
            "/ai/analyze",
            files={"image": ("00001.jpg", sample.read_bytes(), "image/jpeg")},
        )
    assert res.status_code == 200
    payload = res.json()["data"]
    assert payload["hairType"]["label"] in {"lurus", "bergelombang", "keriting", "sangat-keriting"}
    assert payload["hairLength"]["label"] in {"pendek", "pendek-menengah", "menengah", "panjang"}
    assert "hairFeatures" in payload
    assert "tiedHair" in payload
    assert "geometry" in payload
    assert "probabilities" in payload["geometry"]
    assert set(payload["geometry"]["probabilities"].keys()).issubset({"lurus", "bergelombang", "keriting", "sangat-keriting"})
    assert payload["status"] in {"ok", "low_confidence"}
