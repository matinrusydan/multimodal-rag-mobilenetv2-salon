import unittest

from collect_related_pins import related_ids


class RelatedPinTests(unittest.TestCase):
    def test_dedupe_validate_and_limit(self):
        links = ["/pin/111/", "/pin/111/", "/pin/222/", "https://evil.test/pin/333/",
                 "/search/pins/?q=hair", "/pin/444/", "/pin/555/"]
        self.assertEqual(related_ids(links, "111", 2), ["222", "444"])


if __name__ == "__main__":
    unittest.main()
