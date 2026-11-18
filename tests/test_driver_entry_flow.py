"""Tests for the driver-app entry redesign: login first, registration
behind a link, signed-in drivers never see registration again.

Owner decisions, voice call 2026-11-18 ~05:13 EST:
- The driver app opens on a LOGIN screen when signed out, showing
  ONLY an email field, a password field, a Sign in button and the
  Forgot password link.
- A link labeled exactly "New driver registration" sits at the
  BOTTOM of the login screen; only tapping it opens the
  registration form (for new drivers only).
- A signed-in driver goes straight to home/jobs and never sees the
  registration form again ("baar baar driver registration thodi
  batana chahiye" — it should not keep showing registration).
- After Log out the driver lands on the login screen.
- The phone-lookup block is removed from the sign-in UI; the server
  phone-lookup endpoint stays intact (pinned by the API tests in
  tests/test_driver_signin.py).

The registration form itself is unchanged: same fields, rules,
state/city/document lists, labels, hints, validation and the
per-item red error highlight. The password-reset flow
(/driver?reset=<token>) stays reachable on the login screen.

Static pins only (same pattern as the served-page tests in
tests/test_driver_signin.py): the routing lives in shipped JS and
HTML, so these tests read the shipped files.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def login_section(html):
    return html[html.index('id="screen-login"'):html.index('id="screen-register"')]


def register_section(html):
    return html[html.index('id="screen-register"'):html.index('id="screen-home"')]


class DriverEntryFlowCase(unittest.TestCase):
    # -- login screen: only email + password + Sign in + Forgot ------
    def test_login_screen_shows_only_email_password_signin_forgot(self):
        login = login_section(read("static/driver.html"))
        self.assertIn("<h2>Sign in</h2>", login)
        # The only inputs on the login screen: email + password for
        # sign-in, plus the email field of the (hidden) forgot form
        # and the two password fields of the (hidden) reset form.
        inputs = re.findall(r'<input[^>]*id="([^"]+)"', login)
        self.assertEqual(sorted(inputs), sorted([
            "signin-email", "signin-password", "forgot-email",
            "reset-password", "reset-password-confirm",
        ]))
        self.assertNotIn('type="tel"', login)
        self.assertIn('id="signin-submit">Sign in</button>', login)
        self.assertIn('id="forgot-link">Forgot password?</button>', login)
        # Forgot + reset forms start hidden: by default the driver
        # sees only email, password, Sign in and Forgot password.
        self.assertIn('id="forgot-form" class="hidden"', login)
        self.assertIn('id="reset-block" class="hidden"', login)

    def test_login_screen_has_no_phone_block_or_register_form(self):
        html = read("static/driver.html")
        login = login_section(html)
        self.assertNotIn('id="lookup-form"', login)
        self.assertNotIn('id="lookup-phone"', login)
        self.assertNotIn("or continue with your phone number", login)
        self.assertNotIn('id="register-form"', login)
        self.assertNotIn('id="signin-block"', html)
        self.assertNotIn("Already registered?", html)

    def test_new_driver_registration_link_at_bottom_of_login(self):
        login = login_section(read("static/driver.html"))
        # Exact label, and it sits after everything else on the login
        # screen (after the forgot form and the reset block): the
        # bottom of the screen.
        self.assertIn('id="show-register-link">New driver registration</button>',
                      login)
        self.assertLess(login.index('id="forgot-form"'),
                        login.index('id="show-register-link"'))
        self.assertLess(login.index('id="reset-block"'),
                        login.index('id="show-register-link"'))

    def test_registration_link_opens_registration_form(self):
        js = read("static/js/driver.js")
        handler = js[js.index('$("show-register-link").addEventListener'):]
        self.assertIn('showScreen("register");', handler[:300])

    # -- registration form: unchanged ---------------------------------
    def test_registration_screen_unchanged(self):
        section = register_section(read("static/driver.html"))
        self.assertIn("<h2>Driver registration</h2>", section)
        self.assertIn('id="register-intro"', section)
        self.assertIn("Register once. After that, the app opens straight "
                      "to your jobs", section)
        self.assertIn('id="register-form"', section)
        for field in ("reg-name", "reg-phone", "reg-email",
                      "reg-password", "reg-password-confirm",
                      "reg-state", "reg-city", "reg-car-model",
                      "reg-car-year", "reg-car-colour", "reg-plate",
                      "reg-bank-account", "reg-bank-routing"):
            self.assertIn('id="%s"' % field, section)
        self.assertIn('id="register-submit">Complete registration</button>',
                      section)
        # Per-item red error highlight markup intact.
        self.assertIn('id="doc-error-profile_photo"', section)
        self.assertIn('id="doc-error-doc_dmv_license"', section)
        # No sign-in elements on the registration screen.
        self.assertNotIn('id="signin-form"', section)
        self.assertNotIn('id="forgot-link"', section)
        self.assertNotIn('id="reset-block"', section)
        self.assertNotIn('id="show-register-link"', section)

    # -- routing: login by default, home when signed in ---------------
    def test_screens_list_includes_login_and_hides_tabbar(self):
        js = read("static/js/driver.js")
        self.assertIn(
            'var SCREENS = ["login", "register", "home", "trip", '
            '"earnings", "documents", "profile"];', js)
        self.assertIn(
            'if (name === "login" || name === "register" || name === "trip") {',
            js)

    def test_boot_routes_signed_out_and_invalid_tokens_to_login(self):
        js = read("static/js/driver.js")
        boot = js[js.index("function boot()"):js.index("function enterApp")]
        # No token, invalid/expired token, and offline all land on
        # the login screen — never on registration.
        self.assertEqual(boot.count('showScreen("login")'), 3)
        self.assertNotIn('showScreen("register")', boot)
        # The invalid-token path clears the stored token first.
        clear_at = boot.index("clearToken();")
        self.assertIn('showScreen("login");', boot[clear_at:clear_at + 80])
        # The reset-token check runs before the saved-token check.
        self.assertLess(boot.index('get("reset")'), boot.index("getToken()"))

    def test_boot_routes_valid_token_to_home_via_enter_app(self):
        js = read("static/js/driver.js")
        boot = js[js.index("function boot()"):js.index("function enterApp")]
        self.assertIn("enterApp(unwrapDriver(res.j));", boot)
        enter_app = js[js.index("function enterApp"):]
        self.assertIn('showScreen("home");', enter_app[:800])

    def test_registration_screen_reachable_only_via_link(self):
        # The ONLY showScreen("register") in the shipped JS is the
        # "New driver registration" link handler: nothing routes
        # there automatically anymore.
        js = read("static/js/driver.js")
        self.assertEqual(js.count('showScreen("register")'), 1)
        handler = js[js.index('$("show-register-link").addEventListener'):]
        self.assertIn('showScreen("register");', handler[:300])

    def test_registration_success_goes_to_home(self):
        js = read("static/js/driver.js")
        start = js.index('$("register-form")')
        end = js.index('$("signin-form")', start)
        handler = js[start:end]
        # Registration saves the token and enters the app (home).
        self.assertIn("saveToken(res.j.token);", handler)
        self.assertIn("enterApp(unwrapDriver(res.j) || {});", handler)

    def test_logout_reload_lands_on_login(self):
        # Log out clears the token and reloads; boot() with no token
        # shows the login screen (pinned above), so the driver lands
        # on sign-in, never on registration.
        js = read("static/js/driver.js")
        handler = js[js.index("reset-driver-btn"):]
        self.assertIn("clearToken()", handler[:500])
        self.assertIn("window.location.reload()", handler[:500])
        boot = js[js.index("function boot()"):js.index("function enterApp")]
        self.assertIn('if (!token) { showScreen("login"); return; }', boot)

    # -- reset flow stays reachable on the login screen ---------------
    def test_reset_form_shows_on_login_screen(self):
        js = read("static/js/driver.js")
        form = js[js.index("function showResetForm"):]
        form = form[:form.index('$("reset-form")')]
        # Only the reset form shows: sign-in, forgot and the
        # registration link are hidden, the reset block is shown, and
        # the login screen is displayed.
        self.assertIn('hide($("signin-form"));', form)
        self.assertIn('hide($("forgot-link"));', form)
        self.assertIn('hide($("forgot-form"));', form)
        self.assertIn('hide($("show-register-link"));', form)
        self.assertIn('show($("reset-block"));', form)
        self.assertIn('showScreen("login");', form)
        self.assertNotIn("screen-register", form)
        self.assertNotIn("signin-block", form)
        self.assertNotIn("register-form", form)

    def test_reset_back_returns_to_signin(self):
        js = read("static/js/driver.js")
        handler = js[js.index('$("reset-back-btn")'):]
        self.assertIn('window.location.assign("/driver");', handler[:300])

    def test_reset_endpoints_still_wired(self):
        js = read("static/js/driver.js")
        self.assertIn("/api/drivers/me/forgot-password", js)
        self.assertIn("/api/drivers/me/reset-password", js)
        self.assertIn('get("reset")', js)


if __name__ == "__main__":
    unittest.main()
