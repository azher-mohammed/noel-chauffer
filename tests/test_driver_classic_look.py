"""Tests for the driver-app classic (business) typography restyle.

Owner decision, voice call 2026-11-21 ~23:31 EST, clarified ~23:32 EST
("matlab samajh rahe ho, business look rehna"): the driver app should
look classic = business-like — professional, clean, understated. Larger,
more readable type and airier spacing, on the existing black-and-gold
palette with the Georgia-serif headings. No new colours, no new fonts,
no flashy effects, no layout moves, no wording or behaviour changes.

These are static pins on static/css/driver.css only: the restyle is
CSS-only, so the shipped stylesheet is the whole change.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def css():
    with open(os.path.join(REPO_DIR, "static/css/driver.css"),
              encoding="utf-8") as fh:
        return fh.read()


class DriverClassicLookCase(unittest.TestCase):
    def _rule(self, selector):
        m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}",
                      css())
        self.assertIsNotNone(m, "missing rule: %s" % selector)
        return m.group(1)

    # -- base readability --------------------------------------------
    def test_body_line_height_roomier(self):
        self.assertIn("line-height: 1.55;", css())

    # -- headings: clear classic hierarchy ----------------------------
    def test_screen_heading_26px(self):
        self.assertIn("font-size: 26px", self._rule(".screen h2"))

    def test_dashboard_headings_30px(self):
        body = css()
        m = re.search(
            r"#screen-trip h2,\n#screen-earnings h2,\n"
            r"#screen-documents h2,\n#screen-profile h2 \{([^}]*)\}",
            body)
        self.assertIsNotNone(m, "missing dashboard h2 rule")
        self.assertIn("font-size: 30px", m.group(1))

    def test_signin_heading_34px(self):
        self.assertIn("font-size: 34px", self._rule("#screen-login h2"))

    def test_brand_wordmark_26px(self):
        self.assertIn("font-size: 26px", self._rule(".app-head .brand"))

    # -- body and labels ----------------------------------------------
    def test_intro_and_field_text_larger(self):
        self.assertIn("font-size: 15.5px", self._rule(".screen .intro"))
        self.assertIn("font-size: 13.5px", self._rule(".field .hint"))
        self.assertIn("letter-spacing: 0.08em",
                      self._rule(".field label"))

    def test_inputs_stay_16px_no_ios_zoom(self):
        # Inputs must stay at 16px: smaller text inputs trigger iOS
        # Safari auto-zoom on focus.
        body = self._rule(".field input, .field select")
        self.assertIn("font-size: 16px", body)

    def test_section_titles_wider_tracking(self):
        body = self._rule(".section-title")
        self.assertIn("font-size: 13.5px", body)
        self.assertIn("letter-spacing: 0.1em", body)

    # -- money figures stay the visual focus ---------------------------
    def test_earnings_summary_amount_42px(self):
        self.assertIn("font-size: 42px", self._rule(".earn-sum .amount"))

    def test_offer_earnings_amount_28px(self):
        self.assertIn("font-size: 28px",
                      self._rule(".offer .earnings .amount"))

    def test_week_amount_24px(self):
        self.assertIn("font-size: 24px", self._rule(".pay-week .pw-amount"))

    # -- availability toggle: bare button, no card -------------------
    # Owner decision 2026-11-21 ~03:04 EST: the availability card
    # and its state line are gone — only the bare Go online /
    # Go offline button remains, centred at the bottom of home.
    def test_no_availability_card_styles(self):
        body = css()
        self.assertNotIn("avail-card", body)
        self.assertIn("font-size: 17px", self._rule(".toggle-btn"))
        self.assertIn("margin: 16px auto 0",
                      self._rule("#screen-home #avail-toggle"))

    def test_primary_buttons_17px(self):
        self.assertIn("font-size: 17px", self._rule(".btn-primary"))
        self.assertIn("font-size: 17px", self._rule(".toggle-btn"))

    def test_tab_bar_labels_13px(self):
        self.assertIn("font-size: 13px", self._rule(".tabbar button"))

    # -- palette and typefaces unchanged ---------------------------------
    def test_no_new_colours_or_web_fonts(self):
        body = css()
        self.assertNotIn("@import", body)
        self.assertNotIn("fonts.googleapis", body)
        self.assertNotIn("fonts.gstatic", body)
        # Georgia serif headings and amounts are the existing classic
        # direction — still present, no new font family introduced.
        self.assertIn('font-family: Georgia, serif', body)
        self.assertIn('font-family: Georgia, "Times New Roman", serif',
                      body)

    def test_photo_dimensions_untouched(self):
        # Pinned by test_passport_profile_photo.py; the restyle must
        # not move them.
        body = css()
        self.assertIn("width: 140px", body)
        self.assertIn("height: 175px", body)
        self.assertIn("width: 76px", body)
        self.assertIn("height: 95px", body)


if __name__ == "__main__":
    unittest.main()
