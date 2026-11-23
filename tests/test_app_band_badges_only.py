"""App band: "We move with you" (owner order, voice call 2026-11-22
~20:09 EST — homepage below the booking form matches the owner's
screenshot exactly).

The screenshot's app band is a pale-blue band with the heading
"We move with you" and the two store badges (Google Play + App
Store), SAME SIZE (equal height, 48px), on one straight horizontal
row, both still linking to /app. This supersedes the 2026-11-22
~06:47 EST badges-only order (no heading) — the image is the
latest clear order and it carries the heading.

A phone mockup of the /app booking screen was added to the band by
a later owner order (voice call 2026-11-22 ~21:52 EST) — see
tests/test_app_band_badges_mockup.py. It sits between the heading
and the badges, NOT inside the badge row.

Still true from the earlier order:
- NO "Open the app" button
- NO "Your rides, in your pocket" heading
- NO "Book your ride, follow your chauffeur..." paragraph
- NO cabin photo in the band (the cabin photo lives beside
  "Punctual. Professional." now — exactly once on the homepage).

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
    def test_no_button_old_heading_or_paragraph_in_band(self):
        self.assertNotIn("Open the app", INDEX)
        self.assertNotIn("Your rides, in your pocket", INDEX)
        self.assertNotIn("Book your ride, follow your chauffeur", INDEX)

    def test_heading_and_badges_kept(self):
        self.assertIn(">We move with you</h2>", INDEX)  # h2 carries data-i18n="home.move" now
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

    def test_band_is_pale_blue(self):
        self.assertIn("var(--sky-soft)", _rule(".move-band"))

    def test_separate_app_page_untouched(self):
        self.assertIn("Your rides, in your pocket.", APP_PAGE)
        self.assertIn("Book your ride, follow your chauffeur", APP_PAGE)
        self.assertIn('href="/app">Open the app</a>', APP_PAGE)


if __name__ == "__main__":
    unittest.main()
