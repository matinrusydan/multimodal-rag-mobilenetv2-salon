"""URL pattern -> topic mapping for the site crawler.

Default mapping (configurable via env):
  /services*       -> layanan
  /reservation*    -> booking-info
  /about*          -> layanan  (about us = general salon info)
  /                -> layanan
  everything else  -> layanan (fallback)
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

SITE_TOPIC_MAP: list[tuple[str, str]] = [
    (r"^/services", "layanan"),
    (r"^/reservation", "booking-info"),
    (r"^/about", "layanan"),
    (r"^/$", "layanan"),
    (r"^/home$", "layanan"),
    (r"^/prices?$", "harga"),
    (r"^/hair-style", "gaya-rambut"),
    (r"^/tips", "tips-perawatan"),
]

DEFAULT_TOPIC = "layanan"


def resolve_topic_from_url(url: str) -> str:
    """Resolve a URL path -> KB topic string."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    for pattern, topic in SITE_TOPIC_MAP:
        if re.match(pattern, path, re.IGNORECASE):
            return topic
    return DEFAULT_TOPIC