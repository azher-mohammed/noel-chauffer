"""Tests for the driver app white pages + black text.

Owner decision, main chat 2026-11-21 ~10:03 EST ("Driver app mein
page should be white background and text should be black"): the DRIVER
APP pages are white with black text — this replaces the dark /
black-and-gold driver app background. Applies to ALL driver app
screens: sign-in / register / reset, home, jobs/offers, trip,
earnings, tax info, documents, profile.

Buttons stay BLUE (#5b9bd5, full business look — see
test_blue_buttons.py), EXCEPT the Go online / Go offline toggle,
which is BLACK (owner 2026-11-21 ~21:05 EST, a deliberate exception
to the never-black rule). The wordmark keeps only "Chauffeur"
golden, in the BRIGHT gold #D4AF37 with a subtle sheen on all three
surfaces (owner 2026-11-22 ~06:49 EST); "Noel" is black ink.

These are static pins on static/css/driver.css only: the change is
CSS-only, so the shipped stylesheet is the whole change.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = "static/css/driver.css"


def _read(relpath):
    with open(os.path.join(REPO_DIR, relpath), encoding="utf-8") as fh:
        return fh.read()


def _rule(css, selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    if m is None:
        raise AssertionError("missing rule: %s" % selector)
    return m.group(1)


class DriverWhiteCase(unittest.TestCase):
    def test_page_background_is_white_text_is_black(self):
        css = _read(CSS)
        body = _rule(css, "body")
        self.assertIn("background: var(--white);", body)
        self.assertIn("color: var(--ink);", body)
        phone = _rule(css, ".phone")
        self.assertIn("background: var(--white);", phone)
        # No dark page canvas anywhere.
        self.assertNotIn("color-scheme: dark;", css)
        self.assertNotIn("#1d1d1f", css)
        self.assertNotIn("#262628", css)
        self.assertNotIn("#2a2a2c", css)
        self.assertNotIn("#232326", css)
        self.assertNotIn("#f2f0ea", css)
        self.assertNotIn("#b9b7ae", css)
        self.assertNotIn("#a8a6a0", css)

    def test_header_is_white_with_black_text(self):
        body = _rule(_read(CSS), ".app-head")
        self.assertIn("background: var(--white);", body)
        self.assertIn("color: var(--ink);", body)
        self.assertNotIn("background: var(--black);", body)
        self.assertNotIn("color: var(--white);", body)
        tag = _rule(_read(CSS), ".app-head .tag")
        self.assertIn("color: var(--grey);", tag)
        hello = _rule(_read(CSS), ".app-head .hello")
        self.assertIn("color: var(--grey);", hello)

    def test_wordmark_readable_on_white(self):
        css = _read(CSS)
        span = _rule(css, ".app-head .brand span")
        self.assertIn("color: var(--wordmark-gold);", span)
        self.assertIn("--wordmark-gold: #D4AF37;", css)
        self.assertNotIn("#e8cf8f", css)
        self.assertNotIn("#8a6d14", css)

    def test_login_screen_is_white(self):
        css = _read(CSS)
        login = _rule(css, "#screen-login")
        self.assertIn("color-scheme: light;", login)
        self.assertIn("background: var(--white);", login)
        self.assertIn("color: var(--ink);", login)
        self.assertNotIn("linear-gradient", login)
        self.assertNotIn("radial-gradient", login)
        h2 = _rule(css, "#screen-login h2")
        self.assertIn("color: var(--ink);", h2)
        field = _rule(css, "#screen-login .field input")
        self.assertIn("background: var(--white);", field)
        self.assertIn("color: var(--ink);", field)
        self.assertIn("border: 1px solid #cfccc2;", field)

    def test_signed_in_canvas_is_white(self):
        css = _read(CSS)
        m = re.search(
            r"#screen-home,\s*#screen-trip,\s*#screen-earnings,\s*"
            r"#screen-documents,\s*#screen-profile\s*\{([^}]*)\}", css)
        self.assertIsNotNone(m, "missing signed-in canvas rule")
        body = m.group(1)
        self.assertIn("color-scheme: light;", body)
        self.assertIn("background: var(--white);", body)
        self.assertIn("color: var(--ink);", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("radial-gradient", body)

    def test_cards_are_white_with_black_text(self):
        css = _read(CSS)
        for selector in ("#screen-home .offer",
                         "#screen-trip .trip-card",
                         "#screen-trip .chat-box",
                         "#screen-earnings .payout-setup",
                         "#screen-earnings .earn-sum",
                         "#screen-tax .earn-sum",
                         "#screen-earnings .pay-week",
                         "#screen-documents .doc-status",
                         "#screen-profile .profile-card",
                         "#screen-profile .referral-box",
                         "#screen-trip .cancel-reason-panel",
                         "#screen-documents .doc-reupload",
                         ".nav-chooser-card",
                         ".earn-sum"):
            body = _rule(css, selector)
            self.assertIn("background: var(--white);", body, selector)
        self.assertIn("color: var(--ink);",
                      _rule(css, "#screen-home .offer .route"))
        self.assertIn("color: var(--ink);",
                      _rule(css, "#screen-trip .trip-card .route"))
        self.assertIn("color: var(--ink);",
                      _rule(css, "#screen-earnings .earn-sum .amount"))
        self.assertIn("color: var(--ink);",
                      _rule(css, "#screen-earnings .pay-week .pw-range"))
        self.assertIn("color: var(--ink);",
                      _rule(css, "#screen-profile .referral-box .referral-line"))

    def test_tabbar_is_white_with_blue_active_tab(self):
        css = _read(CSS)
        bar = _rule(css, ".tabbar")
        self.assertIn("background: var(--white);", bar)
        self.assertIn("border-top: 1px solid var(--line);", bar)
        btn = _rule(css, ".tabbar button")
        self.assertIn("color: var(--grey);", btn)
        active = _rule(css, ".tabbar button.active")
        self.assertIn("color: var(--blue);", active)

    def test_inputs_are_white_with_black_text(self):
        css = _read(CSS)
        for selector in ("#screen-trip .field input",
                         "#screen-trip .chat-box .chat-input-row input",
                         "#screen-trip .field textarea"):
            body = _rule(css, selector)
            self.assertIn("background: var(--white);", body, selector)
            self.assertIn("color: var(--ink);", body, selector)
            self.assertIn("border: 1px solid #cfccc2;", body, selector)
        focus = _rule(css, "#screen-trip .field input:focus")
        self.assertIn("border-color: var(--blue);", focus)

    def test_stage_list_readable_on_white(self):
        css = _read(CSS)
        li = _rule(css, "#screen-trip .stage-list li")
        self.assertIn("background: var(--white);", li)
        self.assertIn("color: var(--ink);", li)
        done = _rule(css, "#screen-trip .stage-list li.done")
        self.assertIn("color: var(--ok);", done)
        current = _rule(css, "#screen-trip .stage-list li.current")
        self.assertIn("color: var(--ink);", current)
        self.assertIn("background: #eef4ff;", current)

    def test_seo_section_readable_on_white(self):
        css = _read(CSS)
        seo = _rule(css, ".seo-drive")
        self.assertIn("color: var(--ink);", seo)
        p = _rule(css, ".seo-drive p")
        self.assertIn("color: #444444;", p)
        h1 = _rule(css, ".seo-drive h1")
        self.assertIn("color: #1a1a1a;", h1)

    def test_buttons_still_blue_on_white(self):
        css = _read(CSS)
        # The Go online / Go offline toggle is NOT in this list: it
        # is BLACK (owner 2026-11-21 ~21:05 EST exception — see
        # test_driver_colours_slide.py).
        for selector in (".btn-primary", ".btn-gold", ".btn-accept"):
            body = _rule(css, selector)
            self.assertIn("background: var(--blue);", body, selector)
            self.assertIn("color: var(--white);", body, selector)


if __name__ == "__main__":
    unittest.main()
