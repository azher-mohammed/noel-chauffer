"""Tests for PERMANENT customer login (owner decision, voice call
2026-11-23 ~01:25 EST: "de do" + "website pe bhi karna na waisa"):
once a customer signs in they stay signed in on that browser until
they sign out — on BOTH the website and the customer app (/app).

What is pinned here:
- Server: POST /api/customers/signin needs a valid email AND a
  phone number (phone compulsory, owner scope addition 2026-11-23
  ~01:25 EST — NO code/OTP for the phone, it is just typed and
  required). A successful sign-in sets a LONG-LIVED session cookie
  (~365 days, PERMANENT_SESSION_LIFETIME); /api/customers/me then
  reports signed_in with email + phone; sign-out clears it fully.
- Website: the hamburger-menu "Sign in" item is a WIRED button
  (not the old plain item). Tapping it opens the sign-in dialog
  (email + phone fields, both compulsory, no code, no password,
  no Google/Apple/Facebook). Signed in, the menu item reads
  "Signed in as <email>" and the dialog shows Sign out.
- Customer app (/app): the header shows the same signed-in state
  ("Signed in as <email>" + Sign out) whenever signed in.
- Sign-in stays email + phone only: NO codes, NO password, NO
  social buttons, anywhere in the new UI.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-permlogin-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "noel.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "permlogin-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EMAIL = "rider@example.com"
PHONE = "+1 929-385-7597"


def _read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as f:
        return f.read()


class PermanentLoginServerCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()

    def test_signin_requires_phone(self):
        """Phone is COMPULSORY in sign-in (owner scope addition
        2026-11-23): email alone cannot sign in, and neither can a
        too-short phone number. No code is involved either way."""
        resp = self.client.post("/api/customers/signin",
                                json={"email": EMAIL})
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        resp = self.client.post("/api/customers/signin",
                                json={"email": EMAIL, "phone": "123"})
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        resp = self.client.post("/api/customers/signin",
                                json={"email": EMAIL, "phone": PHONE})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertTrue(resp.get_json()["signed_in"])

    def test_signin_sets_long_lived_cookie(self):
        """A successful sign-in sets a permanent session cookie of
        ~365 days — the customer stays signed in across visits.
        (Werkzeug emits Expires, not Max-Age, for the cookie.)"""
        from email.utils import parsedate_to_datetime

        resp = self.client.post("/api/customers/signin",
                                json={"email": EMAIL, "phone": PHONE})
        self.assertEqual(resp.status_code, 200)
        cookies = " ".join(resp.headers.getlist("Set-Cookie"))
        m = re.search(r"Expires=([^;]+)", cookies)
        self.assertIsNotNone(m, "session cookie has no Expires: %s" % cookies)
        expires = parsedate_to_datetime(m.group(1))
        delta = expires - datetime.now(timezone.utc)
        self.assertGreaterEqual(delta, timedelta(days=364))
        self.assertLessEqual(delta, timedelta(days=366))

    def test_permanent_session_lifetime_config(self):
        self.assertEqual(
            app_module.app.config["PERMANENT_SESSION_LIFETIME"],
            timedelta(days=365))

    def test_session_persists_and_me_returns_phone(self):
        """After sign-in, later requests on the same browser are
        still signed in, and /me returns the phone too — the class
        page pre-fills it, so the customer is not asked twice."""
        self.client.post("/api/customers/signin",
                         json={"email": EMAIL, "phone": PHONE})
        me = self.client.get("/api/customers/me").get_json()
        self.assertTrue(me["signed_in"])
        self.assertEqual(me["email"], EMAIL)
        self.assertEqual(me["phone"], PHONE)

    def test_signout_clears_permanent_session(self):
        self.client.post("/api/customers/signin",
                         json={"email": EMAIL, "phone": PHONE})
        self.assertTrue(self.client.get("/api/customers/me").get_json()["signed_in"])
        resp = self.client.post("/api/customers/signout")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["signed_in"])
        me = self.client.get("/api/customers/me").get_json()
        self.assertFalse(me["signed_in"])
        self.assertIsNone(me["email"])


class PermanentLoginFrontendCase(unittest.TestCase):
    """Menu wiring + dialog on the website, header display on /app."""

    def test_website_menu_signin_button_and_dialog(self):
        html = _read("static/index.html")
        # The menu item is a WIRED button now, not the old plain span.
        self.assertIn('id="menu-signin-btn"', html)
        self.assertIn('id="menu-signin-label"', html)
        self.assertNotIn(
            '<span class="menu-link menu-plain" data-i18n="menu.sign_in">Sign in</span>',
            html)
        # The dialog exists with email + phone fields, both required
        # by the JS validation (see wiring test), a submit button,
        # an error line, and a signed-in view with Sign out.
        for ident in ("menu-signin-dialog", "menu-signin-form",
                      "menu-signin-email", "menu-signin-phone",
                      "menu-signin-submit", "menu-signin-error",
                      "menu-signedin-view", "menu-signedin-email",
                      "menu-signout", "menu-signin-close"):
            self.assertIn('id="%s"' % ident, html, ident)
        dialog = html[html.index('id="menu-signin-dialog"'):
                      html.index('id="menu-signin-dialog"') + 2500]
        self.assertIn('type="email"', dialog)
        self.assertIn('type="tel"', dialog)
        # No code, no password, no social buttons in the dialog.
        self.assertNotIn("password", dialog.lower())
        self.assertNotIn("Google", dialog)
        self.assertNotIn("Apple", dialog)
        self.assertNotIn("Facebook", dialog)
        self.assertNotIn("6-digit", dialog)
        self.assertNotIn("signin-code", dialog)
        self.assertNotIn("Verify code", dialog)
        # The dialog lives outside the class-step sign-in panel:
        # the class step keeps its own ONE Continue button, with no
        # sign-out inside it (owner 2026-11-22).
        panel = html[html.index('id="class-signin"'):
                     html.index('id="class-discount-note"')]
        self.assertNotIn("menu-signin-dialog", panel)
        self.assertNotIn("menu-signout", panel)

    def test_website_menu_signin_wiring(self):
        js = _read("static/js/customer.js")
        # The menu button opens the dialog; the dialog signs in
        # (email + phone) and signs out; the label refreshes from
        # /api/customers/me and on every language change.
        for marker in ("menu-signin-btn", "menu-signin-dialog",
                       "/api/customers/signout", "noel-language-changed",
                       "NoelMenuSignin"):
            self.assertIn(marker, js, marker)
        # The class-step sign-in also refreshes the menu label, so
        # the menu reads "Signed in as…" right after a class-page
        # sign-in, without waiting for the next menu open.
        cont = js[js.index('$("class-signin-continue").addEventListener'):]
        self.assertIn("NoelMenuSignin", cont)

    def test_app_header_signedin_display(self):
        html = _read("static/customer-app.html")
        for ident in ("ca-header-signedin", "ca-header-signedin-email",
                      "ca-header-signout"):
            self.assertIn('id="%s"' % ident, html, ident)
        head = html[html.index('id="ca-header-signedin"'):
                    html.index('id="ca-header-signedin"') + 600]
        self.assertIn("Signed in as", head)
        self.assertNotIn("password", head.lower())
        js = _read("static/js/customer-app.js")
        for marker in ("refreshAppHeaderSignin", "ca-header-signout",
                       "/api/customers/signout"):
            self.assertIn(marker, js, marker)
        # The header refresh runs after a class-page sign-in too.
        cont = js[js.index('$("ca-signin-continue").addEventListener'):]
        self.assertIn("refreshAppHeaderSignin", cont)

    def test_i18n_signout_keys_have_all_languages(self):
        """New keys must exist in all 19 languages, like every other
        dictionary key (the language-switcher completeness test
        enforces this repo-wide)."""
        src = _read("static/js/i18n.js")
        for key in ("menu.sign_out", "menu.signin_fill"):
            m = re.search(r'NOEL_I18N\["%s"\] = \{(.*?)\};' % re.escape(key),
                          src, re.S)
            self.assertIsNotNone(m, "missing i18n key %s" % key)
            for lang in ("en", "es", "fr", "ar", "pt", "ur", "hi", "bn",
                         "ud", "zh", "de", "it", "ru", "tr", "ko", "ja",
                         "vi", "fa", "th"):
                lm = re.search(r'"%s":\s*"([^"]+)"' % lang, m.group(1))
                self.assertIsNotNone(lm, "%s missing %s" % (key, lang))
                self.assertTrue(lm.group(1).strip(), "%s %s empty" % (key, lang))


if __name__ == "__main__":
    unittest.main()
