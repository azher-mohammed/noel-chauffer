"""Tests for the black Pay / Chat-with-us buttons (normal business look).

Owner decision, voice call 2026-11-21 ~08:45-08:46 EST: the gold "Pay $X"
button and the gold "Chat with us" pill become BLACK with plain WHITE
text — normal font and weight, no gold, no gradient, no fancy styling.
Applies on the website booking flow AND the customer app (/app).

Final colour decision, voice call 2026-11-21 ~08:54 EST ("Black hai to
poora"): ALL buttons fully black — including "View options" (its blue is
out) and the ghost / danger / decline variants. No layout or position
changes — colour only.

These are static pins on static/css/customer.css and
static/css/customer-app.css only: the change is CSS-only, so the shipped
stylesheets are the whole change.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath):
    with open(os.path.join(REPO_DIR, relpath), encoding="utf-8") as fh:
        return fh.read()


def _rule(css, selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    if m is None:
        raise AssertionError("missing rule: %s" % selector)
    return m.group(1)


def _last_rule(css, selector):
    matches = re.findall(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    if not matches:
        raise AssertionError("missing rule: %s" % selector)
    return matches[-1]


class PayChatButtonsBlackCase(unittest.TestCase):
    # -- website: Pay $X submit --------------------------------------
    def test_website_pay_submit_black_white_normal(self):
        body = _rule(_read("static/css/customer.css"),
                     ".pay-panel .btn-primary")
        self.assertIn("background: var(--black);", body)
        self.assertIn("color: var(--white);", body)
        self.assertIn("font-weight: 400;", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("gold", body)

    def test_website_pay_submit_hover_plain(self):
        body = _rule(_read("static/css/customer.css"),
                     ".pay-panel .btn-primary:hover")
        self.assertIn("background: #222;", body)
        self.assertNotIn("linear-gradient", body)

    def test_website_pay_by_card_opener_black_white_normal(self):
        body = _rule(_read("static/css/customer.css"), "#pay-open-btn")
        self.assertIn("background: var(--black);", body)
        self.assertIn("color: var(--white);", body)
        self.assertIn("font-weight: 400;", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("gold", body)

    # -- website: Chat with us pill ----------------------------------
    def test_website_chat_fab_black_white_normal(self):
        # Two .chat-fab rules exist; the later one wins.
        body = _last_rule(_read("static/css/customer.css"), ".chat-fab")
        self.assertIn("background: var(--black);", body)
        self.assertIn("color: var(--white);", body)
        self.assertIn("font-weight: 400;", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("gold", body)

    def test_website_chat_fab_hover_plain(self):
        body = _last_rule(_read("static/css/customer.css"),
                          ".chat-fab:hover")
        self.assertIn("background: #222;", body)
        self.assertNotIn("linear-gradient", body)

    # -- customer app: Pay + Chat send -------------------------------
    def test_app_pay_submit_black_white_normal(self):
        css = _read("static/css/customer-app.css")
        m = re.search(r"#ca-pay-submit,\s*#ca-chat-send\s*\{([^}]*)\}", css)
        self.assertIsNotNone(m, "missing #ca-pay-submit/#ca-chat-send rule")
        body = m.group(1)
        self.assertIn("background: var(--black);", body)
        self.assertIn("color: var(--white);", body)
        self.assertIn("font-weight: 400;", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("gold", body)

    # -- guards: View options is black too, buttons still present -----
    def test_view_options_is_black_not_blue(self):
        css = _read("static/css/customer.css")
        # Two .booking-card .btn-primary rules exist; the later one
        # (dark booking card) sets the background.
        matches = re.findall(
            r"\.booking-card \.btn-primary\s*\{([^}]*)\}", css)
        self.assertTrue(matches, "missing .booking-card .btn-primary")
        self.assertIn("background: var(--black);", matches[-1])
        m = re.search(
            r"\.ride-tab\.active\s*\{([^}]*)\}",
            css[css.index("/* ---- Blacklane-style"):] if
            "/* ---- Blacklane-style" in css else css)
        self.assertIsNotNone(m, "missing .ride-tab.active")
        self.assertIn("background: var(--black);", m.group(1))
        self.assertNotIn("var(--blue)", css)
        self.assertNotIn("#0b5fff", css)

    def test_ghost_danger_decline_are_black_too(self):
        for rel in ("static/css/customer.css",
                    "static/css/customer-app.css",
                    "static/css/driver.css"):
            css = _read(rel)
            for selector in (".btn-ghost", ".btn-danger"):
                body = _rule(css, selector)
                self.assertIn("background: var(--black);", body,
                              "%s %s" % (rel, selector))
                self.assertIn("color: var(--white);", body,
                              "%s %s" % (rel, selector))
        body = _rule(_read("static/css/driver.css"), ".btn-decline")
        self.assertIn("background: var(--black);", body)
        self.assertIn("color: var(--white);", body)

    def test_buttons_still_present(self):
        html = _read("static/index.html")
        self.assertIn('id="pay-submit"', html)
        self.assertIn('id="pay-open-btn"', html)
        self.assertIn('id="chat-fab"', html)
        app_html = _read("static/customer-app.html")
        self.assertIn('id="ca-pay-submit"', app_html)
        self.assertIn('id="ca-chat-send"', app_html)


if __name__ == "__main__":
    unittest.main()
