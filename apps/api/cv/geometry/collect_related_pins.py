"""Collect visible related pins in a user-operated browser; no token handling."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urljoin

from download_public_pin import PinError, pin_id_from_url, run


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "source_recovery" / "pinterest_related"
PROFILE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Temp" / "opencode" / "pinterest-related-profile"
PIN_PATH = re.compile(r"/pin/([0-9]+)/?")


def related_ids(links: list[str], source_id: str, maximum: int) -> list[str]:
    """Dedupe pin IDs from rendered related-pin links (not arbitrary image URLs)."""
    result: list[str] = []
    seen = {source_id}
    for link in links:
        match = PIN_PATH.search(link)
        if not match or match.group(1) in seen:
            continue
        candidate = urljoin("https://www.pinterest.com/", link)
        try:
            found = pin_id_from_url(candidate)
        except (PinError, ValueError):
            continue
        seen.add(found)
        result.append(found)
        if len(result) >= maximum:
            break
    return result


def collect(url: str, maximum: int, scrolls: int, pause: float, output: Path, download: bool) -> dict:
    source_id = pin_id_from_url(url)
    if not output.resolve().is_relative_to(OUTPUT.resolve()):
        raise PinError(f"Output harus berada di bawah {OUTPUT}.")
    manifest = output / f"source_{source_id}.csv"
    if manifest.exists():
        raise PinError("Manifest sudah ada; pindahkan/arsipkan sebelum menjalankan lagi agar tidak tertimpa.")
    # Keep the browser profile outside the repository. Never access or print cookies.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise PinError("Pasang Playwright: python -m pip install playwright; python -m playwright install chromium") from exc

    links: list[str] = []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(PROFILE), headless=False)
        try:
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print("Browser khusus telah terbuka. Jika diperlukan, login sendiri di browser tersebut.", file=sys.stderr)
            input("Setelah halaman pin terbuka, tekan Enter di terminal untuk mulai membaca gambar terkait...")
            # Collect only anchors rendered in the related section. No private APIs or hidden data.
            for _ in range(scrolls):
                if "pinterest.com" not in (page.url or ""):
                    raise PinError("Halaman berpindah dari Pinterest; proses dihentikan.")
                visible_text = page.locator("body").inner_text(timeout=5000).lower()
                if any(word in visible_text for word in ("captcha", "unusual activity", "terlalu banyak permintaan")):
                    raise PinError("Halaman meminta verifikasi atau membatasi akses; proses dihentikan.")
                # Related grid appears below the pin; collect only visible anchor links.
                anchors = page.locator('a[href*="/pin/"]:visible')
                for index in range(min(anchors.count(), 300)):
                    link = anchors.nth(index).get_attribute("href")
                    if link:
                        links.append(link)
                if len(related_ids(links, source_id, maximum)) >= maximum:
                    break
                page.mouse.wheel(0, 950)
                page.wait_for_timeout(int(pause * 1000))
        finally:
            context.close()

    ids = related_ids(links, source_id, maximum)
    rows = []
    for pin_id in ids:
        pin_url = f"https://www.pinterest.com/pin/{pin_id}/"
        row = {"source_pin": url, "related_pin": pin_url, "pin_id": pin_id,
               "status": "url_candidate", "filename": "", "error": ""}
        if download:
            try:
                result = run(pin_url, output / "images", True, 224)
                row.update(status=result["status"], filename=result["filename"])
            except Exception as exc:
                # This manifest is an audit of candidate URLs, not a log of credentials.
                row.update(status="download_failed", error=type(exc).__name__)
            time.sleep(pause)
        rows.append(row)

    output.mkdir(parents=True, exist_ok=True)
    with manifest.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["source_pin", "related_pin", "pin_id", "status", "filename", "error"])
        writer.writeheader()
        writer.writerows(rows)
    return {"manifest": str(manifest), "related_found": len(ids),
            "downloaded": sum(row["status"] == "candidate_manual_review" for row in rows)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Kumpulkan pin terkait yang terlihat di browser; login dilakukan manual.")
    parser.add_argument("url", help="URL satu pin Pinterest publik")
    parser.add_argument("--max", type=int, default=40, help="Batas pin terkait (1–40)")
    parser.add_argument("--scrolls", type=int, default=12, help="Jumlah scroll maksimum (1–20)")
    parser.add_argument("--pause", type=float, default=2.0, help="Jeda antar-scroll/unduhan (minimal 1 detik)")
    parser.add_argument("--download", action="store_true", help="Unduh gambar utama pin terkait sebagai kandidat")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    if not 1 <= args.max <= 40 or not 1 <= args.scrolls <= 20 or args.pause < 1:
        parser.error("--max 1–40, --scrolls 1–20, dan --pause minimal 1 detik")
    try:
        print(collect(args.url, args.max, args.scrolls, args.pause, args.output, args.download))
    except (PinError, OSError, EOFError) as exc:
        print(f"Gagal: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
