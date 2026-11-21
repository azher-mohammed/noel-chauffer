"""Tests for the show/hide password (eye) toggle in the driver app.

Owner decision, voice call 2026-11-21 ~23:28 EST: inside each
password field there is an eye (Show/Hide); tapping it shows the
whole password in plain text, tapping again hides it behind dots.

Scope: the five password fields only — sign-in (#signin-password),
registration (#reg-password, #reg-password-confirm) and reset
(#reset-password, #reset-password-confirm). The masked bank-number
fields (#reg-bank-account, #reg-bank-routing) are NOT passwords and
get no toggle.

Static pins only (same pattern as tests/test_driver_entry_flow.py):
the toggle lives in shipped HTML/CSS/JS, so these tests read the
shipped files.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASSWORD_FIELDS = (
    "signin-password",
    "reg-password",
    "reg-password-confirm",
    "reset-password",
    "reset-password-confirm",
)


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class DriverPasswordEyeCase(unittest.TestCase):
    # -- one eye toggle per password field --------------------------
    def test_each_password_field_has_an_eye_toggle(self):
        html = read("static/driver.html")
        for field in PASSWORD_FIELDS:
            self.assertIn('id="%s" type="password"' % field, html)
            button = (
                '<button class="password-eye" type="button" '
                'data-for="%s" aria-label="Show password">Show</button>'
                % field
            )
            self.assertIn(button, html)

    def test_eye_toggle_sits_inside_a_password_wrap(self):
        html = read("static/driver.html")
        for field in PASSWORD_FIELDS:
            start = html.index('id="%s"' % field)
            wrap = html.rindex('<div class="password-wrap">', 0, start)
            self.assertGreater(start, wrap)
            # The wrap closes after the toggle button.
            close = html.index("</div>", start)
            self.assertIn('data-for="%s"' % field, html[start:close])

    def test_eye_buttons_are_not_submit_buttons(self):
        html = read("static/driver.html")
        self.assertEqual(html.count('class="password-eye" type="button"'),
                         len(PASSWORD_FIELDS))
        self.assertNotIn('class="password-eye" type="submit"', html)

    def test_bank_fields_have_no_eye_toggle(self):
        html = read("static/driver.html")
        self.assertIn('id="reg-bank-account"', html)
        self.assertIn('id="reg-bank-routing"', html)
        self.assertNotIn('data-for="reg-bank-account"', html)
        self.assertNotIn('data-for="reg-bank-routing"', html)
        self.assertEqual(html.count('class="password-eye"'),
                         len(PASSWORD_FIELDS))

    # -- styling: toggle sits inside the field, gold, readable ------
    def test_password_wrap_css_positions_eye_inside_field(self):
        css = read("static/css/driver.css")
        self.assertIn(".password-wrap { position: relative; }", css)
        self.assertIn(".password-wrap input { padding-right: 62px; }", css)
        self.assertIn(".password-eye {", css)
        self.assertIn("position: absolute; right: 4px;", css)
        self.assertIn("color: var(--gold);", css)

    # -- behaviour: tap flips type password <-> text and label ------
    def test_init_wires_all_eye_buttons_and_is_called(self):
        js = read("static/js/driver.js")
        self.assertIn("function initPasswordEyes() {", js)
        self.assertIn('document.querySelectorAll(".password-eye")', js)
        self.assertIn('btn.getAttribute("data-for")', js)
        self.assertIn('input.type === "text"', js)
        self.assertIn('input.type = showing ? "password" : "text";', js)
        self.assertIn('btn.textContent = showing ? "Show" : "Hide";', js)
        self.assertIn(
            'btn.setAttribute("aria-label", showing ? "Show password" '
            ': "Hide password");', js)
        # Wired once at startup, before boot().
        self.assertIn("initPasswordEyes();", js)
        self.assertLess(js.index("initPasswordEyes();"),
                        js.index("boot();"))

    def test_toggle_never_touches_value_or_submit(self):
        js = read("static/js/driver.js")
        handler = js[js.index("function initPasswordEyes()"):]
        handler = handler[:handler.index("function initCarModelDropdown")]
        self.assertNotIn(".value", handler)
        self.assertNotIn("submit", handler)
        self.assertNotIn("fetch(", handler)


if __name__ == "__main__":
    unittest.main()
