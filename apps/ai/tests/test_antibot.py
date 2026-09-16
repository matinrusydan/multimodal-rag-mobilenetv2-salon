"""Tests for anti-bot detection + health topic detection (no browser needed)."""

from app.crawler.antibot_detector import is_blocked
from app.crawler.stealth import (
    detect_hair_concern,
    detect_health_topic,
    resolve_alodokter_slug,
)


def test_is_blocked_tier1_akamai():
    ok, reason = is_blocked(
        200,
        "<html><body>Reference #18.2d351ab8.1557333295.a4e16ab</body></html>",
    )
    assert ok
    assert "Akamai" in reason


def test_is_blocked_cloudflare():
    ok, reason = is_blocked(403, "<html><body>Checking your browser</body></html>")
    assert ok
    assert "403" in reason or "Cloudflare" in reason


def test_is_blocked_403_short():
    ok, reason = is_blocked(403, "<html>Access Denied</html>")
    assert ok


def test_is_blocked_429():
    ok, reason = is_blocked(429, "")
    assert ok
    assert "429" in reason


def test_is_blocked_tiny_200():
    ok, _ = is_blocked(200, "")
    assert ok


def test_is_blocked_valid_content_not_blocked():
    html = "<html><body><h1>Artikel</h1><p>" + "konten" * 300 + "</p></body></html>"
    ok, reason = is_blocked(200, html)
    assert not ok, reason


def test_detect_health_topic_hits():
    assert detect_health_topic("tempat potong rambut bagus di bandung") is False
    assert detect_health_topic("saya rambut rontok parah") is True
    assert detect_health_topic("cara mencegah kebotakan") is True
    assert detect_health_topic("ketombe gatal di kulit kepala") is True


def test_detect_health_topic_excludes_salon_services():
    # Pertanyaan layanan salon tidak boleh memicu web mode walau ada kata kesehatan.
    assert detect_health_topic("berapa harga layanan detox kulit kepala?") is False
    assert detect_health_topic("treatment rambut rontok di salon berapa biayanya?") is False
    assert detect_health_topic("booking jadwal perawatan ketombe") is False


def test_detect_hair_concern_mix_mode():
    # Pertanyaan salon yang menyentuh kondisi rambut -> mode mix (KB + web).
    assert detect_hair_concern("apakah aman smoothing setelah bleaching?") is True
    assert detect_hair_concern("rambut saya rusak, apakah boleh di-smoothing?") is True
    assert detect_hair_concern("berapa harga smoothing?") is False
    # Pertanyaan kesehatan murni tetap web-only (bukan concern salon).
    assert detect_hair_concern("cara mengatasi ketombe") is False


def test_hair_concern_not_too_aggressive():
    # Sekadar menyebut riwayat pewarnaan/bleaching TIDAK memicu mode mix.
    assert detect_hair_concern("saya pernah diwarna cokelat 6 bulan lalu") is False
    assert detect_hair_concern("dulu pernah bleaching setahun lalu") is False
    assert detect_hair_concern("mau smoothing, rambut saya lurus") is False


def test_resolve_alodokter_slug():
    assert resolve_alodokter_slug("rambut rontok saat hamil") == "rambut-rontok-hamil"
    assert resolve_alodokter_slug("ada ketombe membandel") == "ketombe"
    assert resolve_alodokter_slug("pertanyaan acak") == "rambut-rontok"