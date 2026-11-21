"""Tests for the full gold removal + all-black buttons.

Owner decision, voice call 2026-11-21 ~08:45-08:47 EST ("sunehra
poora nikaal do"): ALL gold styling is gone from the website, the
customer app (/app) and the driver app (/driver). Non-button elements
are plain black / white / grey. Final colour decision, voice call
~08:54 EST ("Black hai to poora"): ALL buttons are FULLY BLACK with
white normal text — no gold, no blue, no gradient — on all three
surfaces. No layout or position changes.

Notes:
- The class name `.btn-gold` and the variable `var(--gold)` still
  exist by name; only their rendered values changed (the variable now
  resolves to a neutral grey/black, the class renders flat black).
- The owner dashboard (/owner, owner.css) is NOT in scope and is not
  checked here.
- Page-background gradients (hero photo overlay, sky tints, dark
  canvas) are not buttons and are untouched.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS_FILES = ("static/css/customer.css",
             "static/css/customer-app.css",
             "static/css/driver.css")

# Gold colour values that must not render anywhere on the three surfaces.
BANNED_VALUES = ("#c9a227", "#e8d9a0", "#a8861d", "#b08d1e", "#dcbd4d",
                 "#e6cb62", "#d4af2f", "#b8921f", "#fff4d6", "#fffdf4",
                 "#fdf6e3", "#ecd9a0", "#6b5510", "rgba(201, 162, 39")

# Blue button styling: fully out since 2026-11-21 ~08:54 EST.
BANNED_BLUE = ("var(--blue)", "#0b5fff", "#004fe0")


def _read(relpath):
    with open(os.path.join(REPO_DIR, relpath), encoding="utf-8") as fh:
        return fh.read()


def _rule(css, selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    if m is None:
        raise AssertionError("missing rule: %s" % selector)
    return m.group(1)


class NoGoldCase(unittest.TestCase):
    def test_no_gold_colour_values_anywhere(self):
        for rel in CSS_FILES:
            css = _read(rel)
            for token in BANNED_VALUES:
                self.assertNotIn(token, css, "%s: %s" % (rel, token))

    def test_gold_variables_resolve_to_neutrals(self):
        site = _read("static/css/customer.css")
        self.assertIn("--gold: #1a1a1a;", site)
        self.assertIn("--gold-soft: #d8d8d8;", site)
        for rel in ("static/css/customer-app.css",
                    "static/css/driver.css"):
            css = _read(rel)
            self.assertIn("--gold: #9a9a9a;", css, rel)
            self.assertIn("--gold-soft: #d8d8d8;", css, rel)

    def test_no_blue_button_styling(self):
        for rel in CSS_FILES:
            css = _read(rel)
            for token in BANNED_BLUE:
                self.assertNotIn(token, css, "%s: %s" % (rel, token))

    def test_all_primary_buttons_flat_black_white_text(self):
        for rel in CSS_FILES:
            css = _read(rel)
            for selector in (".btn-primary", ".btn-gold"):
                body = _rule(css, selector)
                self.assertIn("background: var(--black);", body,
                              "%s %s" % (rel, selector))
                self.assertIn("color: var(--white);", body,
                              "%s %s" % (rel, selector))
                self.assertNotIn("linear-gradient", body,
                                 "%s %s" % (rel, selector))

    def test_driver_accept_and_toggle_black(self):
        css = _read("static/css/driver.css")
        for selector in (".btn-accept", ".toggle-btn",
                         "#screen-home .toggle-btn"):
            body = _rule(css, selector)
            self.assertIn("background: var(--black);", body, selector)
            self.assertIn("color: var(--white);", body, selector)
        for selector in (".toggle-btn.on",
                         "#screen-home .toggle-btn.on"):
            body = _rule(css, selector)
            self.assertIn("background: var(--black);", body, selector)
            self.assertIn("color: var(--white);", body, selector)

    def test_chat_fab_and_pay_buttons_black(self):
        site = _read("static/css/customer.css")
        for selector in (".chat-fab", "#pay-open-btn"):
            body = _rule(site, selector)
            self.assertIn("background: var(--black);", body, selector)
            self.assertIn("color: var(--white);", body, selector)
        body = _rule(site, ".pay-panel .btn-primary")
        self.assertIn("background: var(--black);", body)
        self.assertIn("color: var(--white);", body)
        app = _read("static/css/customer-app.css")
        m = re.search(r"#ca-pay-submit,\s*#ca-chat-send\s*\{([^}]*)\}",
                      app)
        self.assertIsNotNone(m, "missing #ca-pay-submit/#ca-chat-send")
        self.assertIn("background: var(--black);", m.group(1))
        self.assertIn("color: var(--white);", m.group(1))

    def test_buttons_use_normal_weight(self):
        for rel in CSS_FILES:
            css = _read(rel)
            for selector in (".btn-gold",):
                body = _rule(css, selector)
                self.assertIn("font-weight: 400;", body,
                              "%s %s" % (rel, selector))


if __name__ == "__main__":
    unittest.main()
