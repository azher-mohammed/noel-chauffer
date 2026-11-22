"""Tests for the LIGHT BLUE buttons with a full business look.

Owner standing rule, main chat 2026-11-21 ~09:55-09:57 EST ("I dont
like black" / "Blue kar do" / "Aab se best color use karo" / "Not black
buttons" / "Ek dum business wala button"): from now on the BEST colour
is used — ALL buttons are BLUE, with white normal text, clean
professional business styling (no gradient, no glow, normal weight).
NEVER black buttons. This supersedes the all-black buttons order of
~08:54 EST ("Black hai to poora"), which itself superseded the gold
buttons. Owner correction, voice call 2026-11-21 ~19:00 EST ("ekdum
light blue" / "bahut dark blue ho gaya"): the blue must be VERY LIGHT
— #5b9bd5, NOT the dark #0b5fff — on EVERY button, including the
"Chat with us" floating button.

Gold stays OUT everywhere EXCEPT the brand name: only the word
"Chauffeur" in "Noel Chauffer" is golden — a BRIGHT gold
(#D4AF37 with a subtle sheen, owner order 2026-11-22 ~06:49 EST,
superseding the 2026-11-21 light gold #e8cf8f); see test_no_gold.py.
Applies on the website, the customer app (/app) AND the driver app
(/driver). Two driver-app button exceptions (owner 2026-11-21
~21:05 EST): Decline is light red and the Go online / Go offline
toggle is black — see test_driver_colours_slide.py.

These are static pins on the three stylesheets only: the change is
CSS-only, so the shipped stylesheets are the whole change.

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


class BlueButtonsCase(unittest.TestCase):
    # -- website: Pay $X submit --------------------------------------
    def test_website_pay_submit_blue_white_normal(self):
        body = _rule(_read("static/css/customer.css"),
                     ".pay-panel .btn-primary")
        self.assertIn("background: var(--blue);", body)
        self.assertIn("color: var(--white);", body)
        self.assertIn("font-weight: 400;", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("gold", body)

    def test_website_pay_submit_hover_plain(self):
        body = _rule(_read("static/css/customer.css"),
                     ".pay-panel .btn-primary:hover")
        self.assertIn("background: #4a8ac2;", body)
        self.assertNotIn("linear-gradient", body)

    def test_website_pay_by_card_opener_blue_white_normal(self):
        body = _rule(_read("static/css/customer.css"), "#pay-open-btn")
        self.assertIn("background: var(--blue);", body)
        self.assertIn("color: var(--white);", body)
        self.assertIn("font-weight: 400;", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("gold", body)

    # -- website: Chat with us pill ----------------------------------
    # WhatsApp green (owner 2026-11-22): #25D366, clean shiny look
    # like WhatsApp's button. Explicit exception to the no-green
    # rule, for THIS button only — all other buttons stay blue.
    def test_website_chat_fab_whatsapp_green(self):
        # Two .chat-fab rules exist; the later one wins.
        body = _last_rule(_read("static/css/customer.css"), ".chat-fab")
        self.assertIn("background: #25D366;", body)
        self.assertIn("color: var(--white);", body)
        self.assertIn("font-weight: 400;", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("gold", body)

    def test_website_chat_fab_hover_plain(self):
        body = _last_rule(_read("static/css/customer.css"),
                          ".chat-fab:hover")
        self.assertIn("background: #1eb856;", body)
        self.assertNotIn("linear-gradient", body)

    # -- customer app: Pay stays blue, Chat send goes green -----------
    def test_app_pay_submit_blue_white_normal(self):
        css = _read("static/css/customer-app.css")
        m = re.search(r"#ca-pay-submit\s*\{([^}]*)\}", css)
        self.assertIsNotNone(m, "missing #ca-pay-submit rule")
        body = m.group(1)
        self.assertIn("background: var(--blue);", body)
        self.assertIn("color: var(--white);", body)
        self.assertIn("font-weight: 400;", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("gold", body)

    def test_app_chat_send_whatsapp_green(self):
        # Chat-with-us Send buttons (trip chat + support chat):
        # WhatsApp green #25D366 (owner 2026-11-22).
        css = _read("static/css/customer-app.css")
        m = re.search(
            r"#ca-chat-send,\s*#ca-support-send\s*\{([^}]*)\}", css)
        self.assertIsNotNone(m, "missing #ca-chat-send/#ca-support-send rule")
        body = m.group(1)
        self.assertIn("background: #25D366;", body)
        self.assertIn("color: var(--white);", body)
        self.assertIn("font-weight: 400;", body)
        self.assertNotIn("linear-gradient", body)
        self.assertNotIn("gold", body)

    # -- guards: View options is blue, never black --------------------
    def test_view_options_is_blue_not_black(self):
        css = _read("static/css/customer.css")
        # Two .booking-card .btn-primary rules exist; the later one
        # (dark booking card) sets the background.
        matches = re.findall(
            r"\.booking-card \.btn-primary\s*\{([^}]*)\}", css)
        self.assertTrue(matches, "missing .booking-card .btn-primary")
        self.assertIn("background: var(--blue);", matches[-1])
        self.assertNotIn("background: var(--black);", matches[-1])
        m = re.search(
            r"\.ride-tab\.active\s*\{([^}]*)\}",
            css[css.index("/* ---- Blacklane-style"):] if
            "/* ---- Blacklane-style" in css else css)
        self.assertIsNotNone(m, "missing .ride-tab.active")
        self.assertIn("background: var(--blue);", m.group(1))
        self.assertIn("var(--blue)", css)
        self.assertIn("#5b9bd5", css)
        self.assertNotIn("#0b5fff", css, "dark blue is OUT (owner 2026-11-21 ~19:00 EST)")

    def test_ghost_danger_are_blue_decline_is_light_red(self):
        # Ghost and danger stay very light blue. Decline is LIGHT RED
        # (owner 2026-11-21 ~21:05 EST) — see
        # test_driver_colours_slide.py for the full pin.
        for rel in ("static/css/customer.css",
                    "static/css/customer-app.css",
                    "static/css/driver.css"):
            css = _read(rel)
            for selector in (".btn-ghost", ".btn-danger"):
                body = _rule(css, selector)
                self.assertIn("background: var(--blue);", body,
                              "%s %s" % (rel, selector))
                self.assertIn("color: var(--white);", body,
                              "%s %s" % (rel, selector))
        body = _rule(_read("static/css/driver.css"), ".btn-decline")
        self.assertIn("background: #f5c6c2;", body)
        self.assertIn("border: 1px solid #e8a49e;", body)
        self.assertIn("color: var(--ink);", body)
        self.assertNotIn("var(--blue)", body)

    def test_header_cta_and_home_menu_are_blue(self):
        body = _rule(_read("static/css/customer.css"), ".header-cta")
        self.assertIn("background: var(--blue);", body)
        self.assertIn("color: var(--white);", body)
        body = _rule(_read("static/css/driver.css"), ".home-menu-btn")
        self.assertIn("background: var(--blue);", body)
        self.assertIn("color: var(--white);", body)

    def test_dark_blue_is_gone_from_all_three_sheets(self):
        # The dark #0b5fff / #004fe0 are OUT everywhere (owner
        # 2026-11-21 ~19:00 EST: "ekdum light blue").
        for rel in ("static/css/customer.css",
                    "static/css/customer-app.css",
                    "static/css/driver.css"):
            css = _read(rel)
            self.assertNotIn("#0b5fff", css, rel)
            self.assertNotIn("#004fe0", css, rel)
            self.assertIn("#5b9bd5", css, rel)

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
