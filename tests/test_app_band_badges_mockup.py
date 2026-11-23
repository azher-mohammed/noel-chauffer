"""App band: badges EXACTLY equal size + phone mockup back in the band
(owner order, voice call 2026-11-22 ~21:52 EST — "Haan. Kar do.").

1. BADGES: the App Store badge rendered visibly LARGER than the Google
   Play badge on screen even though both carry height="48". Root cause:
   the Google Play PNG (646x250) was NOT tightly cropped — its visible
   black badge body occupied only the middle 64% of the image height
   (transparent padding around it), so at 48px the visible body was
   ~31px tall while the App Store SVG (a tight crop) rendered the full
   48px. Fix: the PNG is trimmed to its alpha bbox (564x168), so its
   visible body now fills the frame and both badges render at the full
   48px height. Neither badge is stretched: widths stay natural
   (Google Play ~161px, App Store ~144px at 48px height).

2. PHONE MOCKUP: the band had no phone mockup at all (heading + two
   badges only). The owner's screenshot showed phone mockups in this
   band, so a non-interactive phone-frame preview of the /app booking
   screen ("Book your ride" flow) is back in the band, between the
   heading and the badges. Decorative only: aria-hidden and
   pointer-events none — it can never be tapped or filled in.

Badge links stay /app (native apps not listed yet). Nothing else in
the band changes: no "Open the app" button, no old heading/paragraph.

Run:  python -m unittest discover -s tests -v
"""

import re
import unittest
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
CSS = (REPO_DIR / "static" / "css" / "customer.css").read_text()
INDEX = (REPO_DIR / "static" / "index.html").read_text()
PNG = REPO_DIR / "static" / "img" / "google-play-badge.png"
SVG = (REPO_DIR / "static" / "img" / "app-store-badge.svg").read_text()


def _rule(selector):
    return " ".join(
        m.group(1)
        for m in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    )


def _band():
    m = re.search(
        r'<section class="app-band move-band" id="app-band">(.*?)</section>',
        INDEX,
        re.S,
    )
    assert m is not None, "app band section not found"
    return m.group(1)


class TestBadgesEqualSize(unittest.TestCase):
    def test_google_play_png_is_tightly_cropped(self):
        # The visible badge body must fill the frame: no transparent
        # padding left, or the badge renders smaller than the SVG.
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        im = Image.open(PNG).convert("RGBA")
        bbox = im.getchannel("A").getbbox()
        self.assertIsNotNone(bbox, "badge PNG is fully transparent")
        w, h = im.size
        self.assertGreaterEqual((bbox[2] - bbox[0]) / w, 0.98)
        self.assertGreaterEqual((bbox[3] - bbox[1]) / h, 0.98)

    def test_app_store_svg_is_tightly_cropped(self):
        # The SVG viewBox must match its own width/height attrs: the
        # badge fills the whole canvas, no padding.
        m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', SVG)
        self.assertIsNotNone(m, "SVG viewBox not found")
        self.assertAlmostEqual(float(m.group(1)), 119.66407, places=3)
        self.assertAlmostEqual(float(m.group(2)), 40.0, places=3)
        self.assertIn('width="119.66407" height="40"', SVG)

    def test_both_badges_render_at_the_same_height(self):
        self.assertEqual(INDEX.count('height="48"'), 2)
        img = _rule(".store-badges img")
        self.assertIn("height: 48px", img)
        self.assertIn("display: block", img)
        self.assertIn("width: auto", img)

    def test_badge_links_unchanged(self):
        band = _band()
        self.assertIn('href="/app"><img src="/static/img/google-play-badge.png"', band)
        self.assertIn('href="/app"><img src="/static/img/app-store-badge.svg"', band)


class TestPhoneMockup(unittest.TestCase):
    def test_mockup_present_in_band_between_heading_and_badges(self):
        band = _band()
        self.assertIn('>We move with you</h2>', band)  # h2 carries data-i18n="home.move" now
        self.assertIn('class="phone-mockup"', band)
        self.assertLess(
            band.index('class="phone-mockup"'),
            band.index('class="app-actions"'),
            "mockup must sit above the badges, not inside the badge row",
        )
        self.assertNotIn('class="phone-mockup"', band.split('class="app-actions"')[1])

    def test_mockup_shows_the_booking_screen(self):
        band = _band()
        for marker in [
            "Book your ride",
            "One way",
            "By the hour",
            "Pickup address",
            "Drop-off address",
            "Date",
            "Pickup time",
            "View options",
            "My Rides",
            "Support",
        ]:
            self.assertIn(marker, band, marker)

    def test_mockup_is_decorative_only(self):
        band = _band()
        self.assertIn('aria-hidden="true"', band)
        self.assertIn("pointer-events: none", _rule(".move-band .phone-mockup"))
        # No form controls inside the mockup: nothing to tap or fill.
        mockup = band[
            band.index('class="phone-mockup"') : band.index('class="app-actions"')
        ]
        self.assertNotIn("<input", mockup)
        self.assertNotIn("<button", mockup)
        self.assertNotIn("<a ", mockup)

    def test_mockup_has_phone_frame_styling(self):
        mockup = _rule(".move-band .phone-mockup")
        self.assertIn("border-radius: 38px", mockup)
        self.assertIn("overflow: hidden", mockup)
        self.assertIn("width: 232px", mockup)


if __name__ == "__main__":
    unittest.main()
