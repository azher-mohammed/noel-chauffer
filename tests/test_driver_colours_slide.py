"""Tests for the driver-app colours + slide-to-confirm trip buttons.

Owner orders, voice call 2026-11-21 ~21:05 EST (driver-app colours)
and voice call 2026-11-22 ~03:29 EST (slide buttons, Uber-style):

1. COLOURS (driver app only, except the wordmark):
   - Decline button (offer card) is LIGHT RED (#f5c6c2 bg,
     #e8a49e border, dark ink text). Accept stays very light blue.
   - Go online / Go offline toggle button is BLACK — a deliberate
     exception to the standing never-black-buttons rule, for this
     button only. Both states black, white text, never green.
   - Premium wordmark — TEXT ONLY, no logo: "Noel" plain,
     "Chauffeur" in bright gold #D4AF37 with a subtle sheen, clean Georgia serif with
     wider tracking (0.06–0.07em) and medium weight, the SAME style
     on all three surfaces: driver app, website, customer app. The
     old dull driver gold #8a6d14 and the very light gold #e8cf8f
     are gone.
2. SLIDE BUTTONS (driver trip screen): "Head to pickup",
   "I have arrived", "Start trip" and "Complete trip" advance by
   SLIDING the thumb to the end of the track (80% of the way),
   not by tapping. The slide calls the same advance path as the
   old tap: the 100 m location gate (Azher + Sana exemption),
   the Maps/Waze chooser on Head to pickup / Start trip, and the
   stage flow are all unchanged. Keyboard Enter/Space on the
   focused slide completes it.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DRIVER_CSS = "static/css/driver.css"
SITE_CSS = "static/css/customer.css"
APP_CSS = "static/css/customer-app.css"

WORDMARK_GOLD = "#D4AF37"
DECLINE_BG = "#f5c6c2"
DECLINE_BORDER = "#e8a49e"


def _read(relpath):
    with open(os.path.join(REPO_DIR, relpath), encoding="utf-8") as fh:
        return fh.read()


def _rule(css, selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    if m is None:
        raise AssertionError("missing rule: %s" % selector)
    return m.group(1)


class DriverColoursCase(unittest.TestCase):
    def test_decline_button_is_light_red(self):
        css = _read(DRIVER_CSS)
        body = _rule(css, ".btn-decline")
        self.assertIn("background: %s;" % DECLINE_BG, body)
        self.assertIn("border: 1px solid %s;" % DECLINE_BORDER, body)
        # Dark ink text on the light red, for readability.
        self.assertIn("color: var(--ink);", body)
        self.assertNotIn("var(--blue)", body)

    def test_accept_button_stays_light_blue(self):
        css = _read(DRIVER_CSS)
        body = _rule(css, ".btn-accept")
        self.assertIn("background: var(--blue);", body)
        self.assertIn("color: var(--white);", body)

    def test_go_online_offline_button_is_black(self):
        css = _read(DRIVER_CSS)
        for selector in (".toggle-btn",
                         "#screen-home .toggle-btn"):
            body = _rule(css, selector)
            self.assertIn("background: var(--black);", body, selector)
            self.assertIn("color: var(--white);", body, selector)
            self.assertNotIn("var(--blue)", body, selector)
        for selector in (".toggle-btn.on",
                         "#screen-home .toggle-btn.on"):
            body = _rule(css, selector)
            self.assertIn("background: var(--black);", body, selector)
            self.assertIn("color: var(--white);", body, selector)
            self.assertNotIn("--ok", body, selector)
            self.assertNotIn("#1e7a4c", body, selector)
        # The black toggle is the ONLY black button in the driver
        # app: every other button stays very light blue.
        self.assertIn("background: var(--blue);",
                      _rule(css, ".btn-primary"))
        self.assertIn("background: var(--blue);",
                      _rule(css, ".home-menu-btn"))

    def test_wordmark_bright_gold_same_on_all_three_surfaces(self):
        expected = {
            DRIVER_CSS: ".app-head .brand span",
            SITE_CSS: ".wordmark span",
            APP_CSS: ".app-head .brand span",
        }
        for rel, selector in expected.items():
            css = _read(rel)
            # The bright gold is defined once per sheet, as the
            # --wordmark-gold variable (owner 2026-11-22 sheen
            # refinement of the 2026-11-21 flat bright gold).
            self.assertEqual(css.count("--wordmark-gold: %s;" % WORDMARK_GOLD), 1,
                             "%s: --wordmark-gold must be defined exactly once" % rel)
            self.assertIn("--wordmark-gold: %s;" % WORDMARK_GOLD, css, rel)
            body = _rule(css, selector)
            self.assertIn("color: var(--wordmark-gold);", body, rel)
            # Subtle metallic sheen on the wordmark text only.
            self.assertIn("linear-gradient(105deg", body, rel)
            self.assertIn("#F6E27A", body, rel)
            self.assertIn("background-clip: text;", body, rel)
        # Old golds are gone from all three sheets.
        for rel in (DRIVER_CSS, SITE_CSS, APP_CSS):
            css = _read(rel)
            self.assertNotIn("#e8cf8f", css, rel)
            self.assertNotIn("#8a6d14", css, rel)

    def test_wordmark_premium_tracking_and_weight(self):
        # Wider tracking + medium weight, same premium text style
        # everywhere; sizes stay as they were (26px driver + site,
        # 24px customer app).
        driver = _read(DRIVER_CSS)
        brand = _rule(driver, ".app-head .brand")
        self.assertIn("letter-spacing: 0.07em;", brand)
        self.assertIn("font-weight: 500;", brand)
        self.assertIn("font-size: 26px", brand)
        site = _read(SITE_CSS)
        wordmark = _rule(site, ".wordmark")
        self.assertIn("letter-spacing: 0.07em;", wordmark)
        self.assertIn("font-weight: 500;", wordmark)
        app = _read(APP_CSS)
        app_brand = _rule(app, ".app-head .brand")
        self.assertIn("letter-spacing: 0.06em;", app_brand)
        self.assertIn("font-weight: 500;", app_brand)
        self.assertIn("font-size: 24px", app_brand)


class SlideConfirmCase(unittest.TestCase):
    def test_trip_button_is_a_slide_control(self):
        html = _read("static/driver.html")
        m = re.search(
            r'<button[^>]*id="trip-next-btn"[^>]*>(.*?)</button>',
            html, re.S)
        self.assertIsNotNone(m, "missing #trip-next-btn")
        self.assertIn("slide-confirm", m.group(0))
        self.assertIn('class="slide-label"', m.group(1))
        self.assertIn('class="slide-thumb"', m.group(1))
        self.assertIn("Head to pickup", m.group(1))
        # No other button on the trip screen becomes a slide.
        self.assertEqual(html.count("slide-confirm"), 1)

    def test_slide_wiring_and_threshold(self):
        js = _read("static/js/driver.js")
        # Pointer drag on the button, completing at 80% of the track.
        self.assertIn('SLIDE_COMPLETE_FRACTION = 0.8;', js)
        self.assertIn(
            '$("trip-next-btn").addEventListener("pointerdown"', js)
        self.assertIn(
            '$("trip-next-btn").addEventListener("pointermove"', js)
        self.assertIn(
            '$("trip-next-btn").addEventListener("pointerup"', js)
        self.assertIn(
            '$("trip-next-btn").addEventListener("pointercancel"', js)
        # A short drag snaps the thumb back; only a full slide fires.
        self.assertIn("if (done) fireStageAdvance();", js)
        self.assertIn("function fireStageAdvance() {", js)
        # No tap-to-advance click listener is left on the button.
        self.assertNotIn(
            '$("trip-next-btn").addEventListener("click"', js
        )
        # Keyboard fallback: Enter/Space completes the slide.
        self.assertIn('e.key === "Enter" || e.key === " "', js)
        # A disabled slide (location gate) cannot be dragged.
        self.assertIn("if (btn.disabled || state.advancing", js)

    def test_slide_styles(self):
        css = _read(DRIVER_CSS)
        track = _rule(css, "#screen-trip #trip-next-btn.slide-confirm")
        self.assertIn("position: relative;", track)
        self.assertIn("overflow: hidden;", track)
        self.assertIn("touch-action: pan-y;", track)
        thumb = _rule(css, "#screen-trip #trip-next-btn .slide-thumb")
        self.assertIn("position: absolute;", thumb)
        label = _rule(css, "#screen-trip #trip-next-btn .slide-label")
        self.assertIn("display: flex;", label)
        disabled = _rule(css, "#screen-trip #trip-next-btn:disabled")
        self.assertIn("opacity: 0.55;", disabled)
        # The slide keeps the blue button look.
        self.assertIn("btn-primary btn-gold slide-confirm",
                      _read("static/driver.html"))

    def test_stage_label_goes_into_the_slide_label(self):
        js = _read("static/js/driver.js")
        # renderStages writes the stage name into the label span —
        # setting textContent on the button would wipe the thumb.
        self.assertIn(
            'document.querySelector("#trip-next-btn .slide-label")', js)
        self.assertIn(
            'stageLabel.textContent = STAGE_BUTTON[current]', js)
        # Stage names themselves are unchanged.
        self.assertIn('en_route: "Head to pickup",', js)
        self.assertIn('arrived: "I have arrived",', js)
        self.assertIn('complete: "Complete trip"', js)

    def test_advance_path_unchanged_behind_the_slide(self):
        js = _read("static/js/driver.js")
        # The slide calls the same advance: location gate first,
        # then the server event, then the nav chooser.
        self.assertIn("function fireStageAdvance() {", js)
        self.assertIn("getFreshPosition(function (pos) {", js)
        self.assertIn("advanceStage(current, extra, btn);", js)
        self.assertIn("function advanceStage(current, extra, btn) {", js)
        self.assertIn("maybeShowNavChooser(current);", js)
        # Gate + exemption still in place.
        self.assertIn("PROXIMITY_GATE_METERS", js)
        self.assertIn("LOCATION_EXEMPT_EMAILS", js)


if __name__ == "__main__":
    unittest.main()
