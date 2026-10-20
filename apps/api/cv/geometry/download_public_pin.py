"""Download the primary image of one public Pinterest pin (not recommendations)."""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import socket
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parent
MAX_HTML_BYTES = 3 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
PIN_RE = re.compile(r"^/pin/([0-9]+)/?$")


class PinError(Exception):
    """A public pin could not be resolved or downloaded safely."""


def pin_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port
            or parsed.query or parsed.fragment or not
            (host == "pinterest.com" or host.endswith(".pinterest.com"))):
        raise PinError("Gunakan URL HTTPS pin publik Pinterest tanpa parameter tambahan.")
    match = PIN_RE.fullmatch(parsed.path)
    if not match:
        raise PinError("URL harus merujuk tepat ke satu pin: /pin/<nomor>/.")
    return match.group(1)


def valid_page_url(url: str, pin_id: str) -> bool:
    try:
        return pin_id_from_url(url) == pin_id
    except (PinError, ValueError):
        return False


def valid_image_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (parsed.scheme == "https" and parsed.hostname == "i.pinimg.com"
                and not parsed.username and not parsed.password and parsed.port is None
                and not parsed.query and not parsed.fragment and parsed.path.startswith("/"))
    except ValueError:
        return False


class StrictRedirect(HTTPRedirectHandler):
    def __init__(self, predicate):
        self.predicate = predicate

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if not self.predicate(newurl):
            raise PinError("Redirect menuju alamat yang tidak diizinkan.")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def fetch(url: str, predicate, limit: int) -> tuple[bytes, str]:
    if not predicate(url):
        raise PinError("Alamat tidak diizinkan.")
    opener = build_opener(StrictRedirect(predicate))
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PublicPinImage/1.0)"})
    with opener.open(request, timeout=12) as response:
        if not predicate(response.url):
            raise PinError("Alamat hasil respons tidak diizinkan.")
        if response.headers.get("Content-Length") and int(response.headers["Content-Length"]) > limit:
            raise PinError("Respons melebihi batas ukuran.")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise PinError("Respons melebihi batas ukuran.")
        return data, response.url


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        attrs = dict(attrs)
        key = attrs.get("property") or attrs.get("name")
        if key and attrs.get("content") and key not in self.values:
            self.values[key] = attrs["content"]


def find_pin_image(html: bytes) -> str:
    parser = Metadata()
    parser.feed(html.decode("utf-8", errors="replace"))
    url = parser.values.get("og:image")
    if not url or not valid_image_url(url):
        raise PinError("Gambar utama pin publik tidak ditemukan pada metadata og:image.")
    return url


def checked_image(raw: bytes, min_side: int) -> tuple[int, int, str]:
    try:
        with Image.open(io.BytesIO(raw)) as img:
            image_format = img.format
            width, height = img.size
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise PinError("Respons bukan gambar yang valid.") from exc
    if image_format not in {"JPEG", "PNG", "WEBP"}:
        raise PinError("Format gambar tidak didukung (JPEG/PNG/WebP saja).")
    if min(width, height) < min_side:
        raise PinError(f"Resolusi terlalu kecil: {width}x{height}, minimal {min_side} per sisi.")
    return width, height, {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[image_format]


def run(url: str, output: Path, download: bool, min_side: int) -> dict:
    pin_id = pin_id_from_url(url)
    page, final_page = fetch(url, lambda link: valid_page_url(link, pin_id), MAX_HTML_BYTES)
    image_url = find_pin_image(page)
    result = {"pin_id": pin_id, "pin_url": final_page, "image_url": image_url,
              "status": "preview_only", "rights_review": "required",
              "viewpoint_label_review": "required"}
    if not download:
        return result
    # Network access is permitted only for pinimg, and output must remain isolated.
    allowed_roots = (ROOT / "source_recovery" / "pinterest_candidates",
                     ROOT / "source_recovery" / "pinterest_related" / "images")
    if not any(output.resolve().is_relative_to(root.resolve()) for root in allowed_roots):
        raise PinError("Output harus berada di folder kandidat Pinterest terisolasi.")
    raw, final_image = fetch(image_url, valid_image_url, MAX_IMAGE_BYTES)
    width, height, ext = checked_image(raw, min_side)
    result.update(image_url=final_image, width=width, height=height,
                  sha256=hashlib.sha256(raw).hexdigest())
    filename = f"pin_{pin_id}{ext}"
    destination = output / filename
    manifest = output / f"pin_{pin_id}.json"
    if destination.exists() or manifest.exists():
        raise PinError("File pin sudah ada; tidak akan ditimpa.")
    output.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as stream:
            stream.write(raw)
        result.update(status="candidate_manual_review", filename=filename)
        with manifest.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except Exception:
        if destination.exists() and not manifest.exists():
            destination.unlink()
        raise
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pratinjau/unduh gambar utama satu pin Pinterest publik.")
    parser.add_argument("url", help="URL https://...pinterest.com/pin/<id>/")
    parser.add_argument("--download", action="store_true", help="Unduh gambar utama (default hanya pratinjau URL)")
    parser.add_argument("--output", type=Path, default=ROOT / "source_recovery" / "pinterest_candidates")
    parser.add_argument("--min-side", type=int, default=224, help="Sisi terpendek minimum dalam piksel (default 224)")
    args = parser.parse_args(argv)
    if args.min_side < 1:
        parser.error("--min-side harus positif")
    try:
        print(json.dumps(run(args.url, args.output, args.download, args.min_side), ensure_ascii=False, indent=2))
    except (PinError, HTTPError, URLError, TimeoutError, socket.timeout, OSError) as exc:
        print(f"Gagal: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
