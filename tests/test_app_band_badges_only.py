"""App band: badges only, no text, no button (owner order, voice call
2026-11-22 ~06:47 EST).

The owner said the "Your rides, in your pocket" band looked messy
("kitna galeez dikh raha") and ordered the text out:
- NO "Open the app" button
- NO "Your rides, in your pocket" heading
- NO "Book your ride, follow your chauffeur..." paragraph
- KEEP the two store badges (Google Play + App Store), SAME SIZE
  (equal height, 48px), on one straight horizontal row, both still
  linking to /app, with the small "Noel Chauffer app" label above
  them and the cabin photo beside them.
- The same tan-leather cabin photo must appear only ONCE on the
  homepage: the repeated large banner above "Sit back and enjoy
  the ride" was removed (that section keeps its heading + text).

The separate page static/your-rides-in-your-pocket.html is untouched
and still carries its own heading, paragraph and button.

Run:  python -m unittest discover -s tests -v
"""

import re
import unittest
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
CSS = (REPO_DIR / "static" / "css" / "customer.css").read_text()
INDEX = (REPO_DIR / "static" / "index.html").read_text()
APP_PAGE = (REPO_DIR / "static" / "your-rides-in-your-pocket.html").read_text()


def _rule(selector):
    return " ".join(
        m.group(1)
        for m in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    )


class TestAppBandBadgesOnly(unittest.TestCase):
    def test_no_button_heading_or_paragraph_in_band(self):
        self.assertNotIn("Open the app", INDEX)
        self.assertNotIn("Your rides, in your pocket", INDEX)
        self.assertNotIn("Book your ride, follow your chauffeur", INDEX)

    def test_label_badges_and_photo_kept(self):
        self.assertIn('<p class="eyebrow">Noel Chauffer app</p>', INDEX)
        self.assertIn('href="/app"><img src="/static/img/google-play-badge.png"', INDEX)
        self.assertIn('href="/app"><img src="/static/img/app-store-badge.svg"', INDEX)
        self.assertIn('src="/static/img/cabin.jpg"', INDEX)

    def test_badges_equal_height_on_one_row(self):
        self.assertEqual(INDEX.count('height="48"'), 2)
        badges = _rule(".store-badges")
        self.assertIn("display: flex", badges)
        self.assertIn("align-items: center", badges)
        img = _rule(".store-badges img")
        self.assertIn("height: 48px", img)
        self.assertIn("display: block", img)

    def test_cabin_photo_appears_exactly_once(self):
        self.assertEqual(INDEX.count("cabin.jpg"), 1)

    def test_experience_section_keeps_heading_and_text(self):
        self.assertIn("Sit back and enjoy the ride.", INDEX)
        self.assertIn("From booking to arrival, every detail is looked after.", INDEX)

    def test_separate_app_page_untouched(self):
        self.assertIn("Your rides, in your pocket.", APP_PAGE)
        self.assertIn("Book your ride, follow your chauffeur", APP_PAGE)
        self.assertIn('href="/app">Open the app</a>', APP_PAGE)


if __name__ == "__main__":
    unittest.main()
