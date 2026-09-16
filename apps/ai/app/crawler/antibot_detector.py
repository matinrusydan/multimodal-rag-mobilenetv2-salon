"""Anti-bot detection heuristics for crawl results.

Adapted from crawl4ai's antibot_detector (Apache-2.0):
https://github.com/unclecode/crawl4ai/blob/main/crawl4ai/antibot_detector.py

Examines HTTP status codes and HTML content patterns to determine
if a crawl was blocked by anti-bot protection.

Detection philosophy: false positives are cheap (the fallback mechanism
rescues them), false negatives are catastrophic (user gets garbage).
Err on the side of detection.
"""

import re
from typing import Optional, Tuple


_TIER1_PATTERNS = [
    (re.compile(r"Reference\s*#\s*[\d]+\.[0-9a-f]+\.\d+\.[0-9a-f]+", re.IGNORECASE), "Akamai block (Reference #)"),
    (re.compile(r"Pardon\s+Our\s+Interruption", re.IGNORECASE), "Akamai challenge (Pardon Our Interruption)"),
    (re.compile(r"challenge-form.*?__cf_chl_f_tk=", re.IGNORECASE | re.DOTALL), "Cloudflare challenge form"),
    (re.compile(r"<span\s+class=\"cf-error-code\">\d{4}</span>", re.IGNORECASE), "Cloudflare firewall block"),
    (re.compile(r"/cdn-cgi/challenge-platform/\S+orchestrate", re.IGNORECASE), "Cloudflare JS challenge"),
    (re.compile(r"window\._pxAppId\s*=", re.IGNORECASE), "PerimeterX block"),
    (re.compile(r"captcha\.px-cdn\.net", re.IGNORECASE), "PerimeterX captcha"),
    (re.compile(r"captcha-delivery\.com", re.IGNORECASE), "DataDome captcha"),
    (re.compile(r"_Incapsula_Resource", re.IGNORECASE), "Imperva/Incapsula block"),
    (re.compile(r"Incapsula\s+incident\s+ID", re.IGNORECASE), "Imperva/Incapsula incident"),
    (re.compile(r"Sucuri\s+WebSite\s+Firewall", re.IGNORECASE), "Sucuri firewall block"),
    (re.compile(r"KPSDK\.scriptStart\s*=\s*KPSDK\.now\(\)", re.IGNORECASE), "Kasada challenge"),
    (re.compile(r"blocked\s+by\s+network\s+security", re.IGNORECASE), "Network security block"),
]

_TIER2_PATTERNS = [
    (re.compile(r"Access\s+Denied", re.IGNORECASE), "Access Denied on short page"),
    (re.compile(r"Checking\s+your\s+browser", re.IGNORECASE), "Cloudflare browser check"),
    (re.compile(r"<title>\s*Just\s+a\s+moment", re.IGNORECASE), "Cloudflare interstitial"),
    (re.compile(r"class=[\"']g-recaptcha[\"']", re.IGNORECASE), "reCAPTCHA on block page"),
    (re.compile(r"class=[\"']h-captcha[\"']", re.IGNORECASE), "hCaptcha on block page"),
    (re.compile(r"Access\s+to\s+This\s+Page\s+Has\s+Been\s+Blocked", re.IGNORECASE), "PerimeterX block page"),
    (re.compile(r"blocked\s+by\s+security", re.IGNORECASE), "Blocked by security"),
    (re.compile(r"Request\s+unsuccessful", re.IGNORECASE), "Request unsuccessful (Imperva)"),
]

_TIER2_ALWAYS = [
    (re.compile(r"Access\s+Denied", re.IGNORECASE), "Access Denied"),
    (re.compile(r"blocked\s+by\s+security", re.IGNORECASE), "Blocked by security"),
]

_TIER3_ALWAYS = [
    (re.compile(r"Access\s+Denied", re.IGNORECASE), "Access Denied"),
]

_TIER2_MAX_SIZE = 10000
_STRUCTURAL_MAX_SIZE = 50000
_BLOCK_PAGE_MAX_SIZE = 5000
_EMPTY_CONTENT_THRESHOLD = 100

_CONTENT_ELEMENTS_RE = re.compile(r"<(?:p|h[1-6]|article|section|li|td|a|pre)\b", re.IGNORECASE)
_SCRIPT_TAG_RE = re.compile(r"<script\b", re.IGNORECASE)
_STYLE_TAG_RE = re.compile(r"<style\b[\s\S]*?</style>", re.IGNORECASE)
_SCRIPT_BLOCK_RE = re.compile(r"<script\b[\s\S]*?</script>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_BODY_RE = re.compile(r"<body\b", re.IGNORECASE)


def _looks_like_data(html: str) -> bool:
    stripped = html.strip()
    if not stripped:
        return False
    if stripped[0] in ("{", "["):
        return True
    if stripped[:10].lower().startswith(("<html", "<!")):
        if re.search(r"<body[^>]*>\s*<pre[^>]*>\s*[{\[]", stripped[:500], re.IGNORECASE):
            return True
        return False
    return stripped[0] == "<"


def _structural_integrity_check(html: str) -> Tuple[bool, str]:
    if len(html) > _STRUCTURAL_MAX_SIZE or _looks_like_data(html):
        return False, ""

    signals = []
    if not _BODY_RE.search(html):
        return True, f"Structural: no <body> tag ({len(html)} bytes)"

    body_match = re.search(r"<body\b[^>]*>([\s\S]*)</body>", html, re.IGNORECASE)
    body_content = body_match.group(1) if body_match else html
    stripped = _SCRIPT_BLOCK_RE.sub("", body_content)
    stripped = _STYLE_TAG_RE.sub("", stripped)
    visible_text = _TAG_RE.sub("", stripped).strip()
    visible_len = len(visible_text)
    if visible_len < 50:
        signals.append("minimal_text")

    content_elements = len(_CONTENT_ELEMENTS_RE.findall(html))
    if content_elements == 0:
        signals.append("no_content_elements")

    script_count = len(_SCRIPT_TAG_RE.findall(html))
    if script_count > 0 and content_elements == 0 and visible_len < 100:
        signals.append("script_heavy_shell")

    if len(signals) >= 2:
        return True, f"Structural: {', '.join(signals)} ({len(html)} bytes, {visible_len} chars visible)"
    if len(signals) == 1 and len(html) < 5000:
        return True, f"Structural: {signals[0]} on small page ({len(html)} bytes, {visible_len} chars visible)"

    return False, ""


def is_blocked(
    status_code: Optional[int],
    html: str,
    error_message: Optional[str] = None,
) -> Tuple[bool, str]:
    """Detect if a crawl result was blocked by anti-bot protection.

    Returns:
        (is_blocked, reason). reason is empty string when not blocked.
    """
    html = html or ""
    html_len = len(html)

    if status_code == 429:
        return True, "HTTP 429 Too Many Requests"

    snippet = html[:15000]
    if snippet:
        for pattern, reason in _TIER1_PATTERNS:
            if pattern.search(snippet):
                return True, reason

    if html_len > 15000:
        _stripped_for_t1 = _SCRIPT_BLOCK_RE.sub("", html[:500000])
        _stripped_for_t1 = _STYLE_TAG_RE.sub("", _stripped_for_t1)
        _deep_snippet = _stripped_for_t1[:30000]
        for pattern, reason in _TIER1_PATTERNS:
            if pattern.search(_deep_snippet):
                return True, reason

    if status_code in (403, 503) and not _looks_like_data(html):
        if html_len < _EMPTY_CONTENT_THRESHOLD:
            return True, f"HTTP {status_code} with near-empty response ({html_len} bytes)"
        _snippet = snippet
        if html_len > _TIER2_MAX_SIZE:
            _stripped = _SCRIPT_BLOCK_RE.sub("", html[:500000])
            _stripped = _STYLE_TAG_RE.sub("", _stripped)
            _snippet = _stripped[:30000]
        for pattern, reason in _TIER2_PATTERNS:
            if pattern.search(_snippet):
                return True, f"{reason} (HTTP {status_code}, {html_len} bytes)"
        return True, f"HTTP {status_code} with HTML content ({html_len} bytes)"

    if status_code and status_code >= 400 and html_len < _TIER2_MAX_SIZE:
        for pattern, reason in _TIER2_PATTERNS:
            if pattern.search(snippet):
                return True, f"{reason} (HTTP {status_code}, {html_len} bytes)"

    if status_code == 200:
        stripped = html.strip()
        if len(stripped) < _EMPTY_CONTENT_THRESHOLD and not _looks_like_data(html):
            return True, f"Near-empty content ({len(stripped)} bytes) with HTTP 200"

    _blocked, _reason = _structural_integrity_check(html)
    if _blocked:
        return True, _reason

    return False, ""