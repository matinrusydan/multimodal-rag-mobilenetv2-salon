"""Offline checks for single-pin downloader."""

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import download_public_pin as pin


URL = "https://mx.pinterest.com/pin/273241902380992811/"
IMG = "https://i.pinimg.com/originals/aa/bb/example.jpg"


def sample_image():
    data = io.BytesIO()
    Image.new("RGB", (300, 500), (20, 40, 60)).save(data, format="JPEG")
    return data.getvalue()


class DownloadPinTests(unittest.TestCase):
    def test_only_one_pin_url(self):
        self.assertEqual(pin.pin_id_from_url(URL), "273241902380992811")
        for url in ("http://mx.pinterest.com/pin/12/", "https://evilpinterest.com/pin/12/",
                    "https://pinterest.com/search/pins/?q=wavy", "https://pinterest.com/pin/12/?x=1",
                    "https://pinterest.com@127.0.0.1/pin/12/"):
            with self.subTest(url=url), self.assertRaises(pin.PinError):
                pin.pin_id_from_url(url)

    def test_only_primary_pin_metadata(self):
        html = ('<meta property="og:image" content="' + IMG + '">' +
                '<img src="https://i.pinimg.com/originals/another.jpg">').encode()
        self.assertEqual(pin.find_pin_image(html), IMG)
        self.assertFalse(pin.valid_image_url("https://i.pinimg.com.evil.test/pic.jpg"))
        self.assertFalse(pin.valid_image_url("http://i.pinimg.com/pic.jpg"))
        with self.assertRaises(pin.PinError):
            pin.find_pin_image(b'<meta property="og:image" content="http://127.0.0.1/a.jpg">')

    @patch.object(pin, "fetch")
    def test_preview_does_not_fetch_image_or_write(self, mocked):
        mocked.return_value = (f'<meta property="og:image" content="{IMG}">'.encode(), URL)
        with tempfile.TemporaryDirectory() as tmp:
            result = pin.run(URL, Path(tmp), False, 224)
            self.assertEqual(result["status"], "preview_only")
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    @patch.object(pin, "fetch")
    def test_download_requires_isolated_folder(self, mocked):
        mocked.return_value = (f'<meta property="og:image" content="{IMG}">'.encode(), URL)
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(pin.PinError):
            pin.run(URL, Path(tmp), True, 224)

    def test_verify_image_and_resolution(self):
        self.assertEqual(pin.checked_image(sample_image(), 224)[:2], (300, 500))
        with self.assertRaises(pin.PinError):
            pin.checked_image(sample_image(), 400)
        with self.assertRaises(pin.PinError):
            pin.checked_image(b"not an image", 224)

    @patch.object(pin, "fetch")
    def test_download_creates_manifest_and_never_overwrites(self, mocked):
        mocked.side_effect = [
            (f'<meta property="og:image" content="{IMG}">'.encode(), URL),
            (sample_image(), IMG),
            (f'<meta property="og:image" content="{IMG}">'.encode(), URL),
            (sample_image(), IMG),
        ]
        with tempfile.TemporaryDirectory(dir=pin.ROOT) as tmp:
            output = Path(tmp) / "source_recovery" / "pinterest_candidates"
            # Temporarily isolate ROOT to test without writing production outputs.
            with patch.object(pin, "ROOT", Path(tmp)):
                result = pin.run(URL, output, True, 224)
                self.assertEqual(result["status"], "candidate_manual_review")
                self.assertTrue((output / result["filename"]).exists())
                self.assertTrue((output / "pin_273241902380992811.json").exists())
                with self.assertRaises(pin.PinError):
                    pin.run(URL, output, True, 224)


if __name__ == "__main__":
    unittest.main()
