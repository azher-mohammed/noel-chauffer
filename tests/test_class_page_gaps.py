"""Class-page gaps (owner order, voice call 2026-11-23 ~00:37 EST,
"theek karke khaali batao", from his screenshot of the "Choose your
experience" page after "View options" — the customer app, same page
exists on the website):

1. Car-photo side gaps: the class-card photo sat in a white box with
   WHITE GAPS on its left and right — the square car photos (1600x1600)
   were rendered with `object-fit: contain` in a wide, short box, so
   the image letterboxed. Fix: `object-fit: cover` (+ center) so the
   photo fills the full card width, no white bars. Photos, card size,
   prices and capacity text unchanged.
2. Big empty vertical gap below the highlights carousel: the track
   mixes tall photo slides (~250px) with short text slides (~150px);
   a flex track stays as tall as the tallest slide, so a text slide
   left a big dead gap above the dots (measured ~170px in his
   screenshot, larger than the text card itself). Fix: the track is
   sized to the ACTIVE slide in JS (paintClassDetails + a resize
   listener), with `align-items: flex-start` so slides keep their
   natural height. Carousel content, dots and list items unchanged.

Pinned here (website + customer app):
- `.class-option-car` uses `object-fit: cover` (no `contain` left in
  that rule) on both CSS files.
- `.highlights-track` uses `align-items: flex-start` on both CSS files.
- Both JS files size the track to the active slide's offsetHeight
  inside paintClassDetails and re-sync on window resize.
- The served CSS files carry the fix.
- Carousel content untouched (5 highlights, first caption, text-slide
  min-heights).
- Fares untouched (JFK -> Times Square Business driver $102.46).

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from decimal import Decimal as D

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-class-gaps-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "class-gaps-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
from blacklane_pricing import compute_blacklane_one_way  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(REPO_DIR, path), encoding="utf-8") as fh:
        return fh.read()


def rule_bodies(css, selector):
    return re.findall(re.escape(selector) + r"\s*\{[^}]*\}", css)


class ClassPageGapsCase(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.css = read("static/css/customer.css")
        self.app_css = read("static/css/customer-app.css")
        self.js = read("static/js/customer.js")
        self.app_js = read("static/js/customer-app.js")

    # ---- Gap 1: car photo fills the card width ---------------------------
    def test_class_option_car_covers_full_width(self):
        for name, css in (("website", self.css), ("app", self.app_css)):
            bodies = rule_bodies(css, ".class-option-car")
            self.assertTrue(bodies, "%s: no .class-option-car rule" % name)
            base = [b for b in bodies if "object-fit" in b]
            self.assertEqual(len(base), 1,
                             "%s: expected exactly one object-fit rule" % name)
            self.assertIn("object-fit: cover", base[0], name)
            self.assertIn("object-position: center", base[0], name)
            self.assertNotIn("object-fit: contain", base[0], name)

    # ---- Gap 2: highlights track sized to the active slide ---------------
    def test_highlights_track_keeps_natural_slide_heights(self):
        for name, css in (("website", self.css), ("app", self.app_css)):
            bodies = rule_bodies(css, ".highlights-track")
            self.assertEqual(len(bodies), 1,
                             "%s: expected one .highlights-track rule" % name)
            self.assertIn("align-items: flex-start", bodies[0], name)

    def test_highlights_height_sync_in_js(self):
        for name, js in (("website", self.js), ("app", self.app_js)):
            self.assertIn(
                "track.style.height = activeSlide.offsetHeight",
                js, "%s: track not sized to the active slide" % name)
            self.assertIn('addEventListener("resize"', js,
                          "%s: no resize re-sync" % name)
            self.assertIn("tr.style.height = tr.children[hlIndex].offsetHeight",
                          js, "%s: resize handler does not re-sync" % name)

    # ---- Served files carry the fix ---------------------------------------
    def test_served_css_carries_the_fix(self):
        for path in ("/static/css/customer.css",
                     "/static/css/customer-app.css"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)
            self.assertIn(b"object-fit: cover", resp.data, path)
            self.assertIn(b"align-items: flex-start", resp.data, path)
        for path in ("/static/js/customer.js",
                     "/static/js/customer-app.js"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)
            self.assertIn(b"track.style.height = activeSlide.offsetHeight",
                          resp.data, path)

    # ---- Carousel content untouched ---------------------------------------
    def test_carousel_content_unchanged(self):
        for name, js in (("website", self.js), ("app", self.app_js)):
            self.assertIn("Clean, quiet, and executive-level comfort.", js,
                          name)
            self.assertIn("Arrive fully charged", js, name)
        self.assertIn(".hl-slide-text { padding: 18px; background: var(--paper); "
                      "border-radius: 10px; min-height: 120px; }", self.css)
        self.assertIn("min-height: 110px;", self.app_css)


class TestFaresUnchanged(unittest.TestCase):
    def test_jfk_to_times_square_driver_pay_exact(self):
        r = compute_blacklane_one_way(D("17.9"), "sedan",
                                      "JFK Airport", "Times Square",
                                      toll=D("7.46"))
        self.assertEqual(r["driver_earnings"], D("102.46"))


if __name__ == "__main__":
    unittest.main()
