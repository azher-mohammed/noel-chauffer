"""Tests for the compulsory customer sign-in frontend, the second-page
strip, the customer-app white background + black form, and the
standing golden-"Chauffer" wordmark rule.

Owner decisions, voice calls 2026-11-22:
- Sign-in is COMPULSORY after View options / Choose your experience,
  before the booking can proceed to payment. EMAIL ONLY — just an
  email field + Continue, NO password, NO Google/Apple/Facebook
  buttons, NO CODES (owner correction 2026-11-22: "Nahi bhai, no
  codes" — no code is emailed, no code is typed back). The PHONE
  NUMBER is compulsory too. Signed-in customers stay signed in for
  later bookings; My Rides shows their rides. The old phone lookup
  keeps working for rides booked before sign-in existed.
- Second page (Choose your experience), payment page and the
  post-payment confirmation page: NOTHING below the booking flow —
  no section, no link column, no extra text. Only the small
  "powered by" line and the bottom BLACK footer with only our
  address stay. The homepage (first page) is untouched for now.
- Customer app (/app): background WHITE, booking form BLACK.
  Website background unchanged. Driver app UNTOUCHED.
- Standing rule: wherever "Noel Chauffer" is written — website,
  customer app, driver app, footer — "Noel" is plain and
  "Chauffer" is ALWAYS golden bright (#D4AF37 with the sheen),
  never dull or black.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as f:
        return f.read()


def _rule(css, selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css, re.S)
    assert m, "missing rule %s" % selector
    return m.group(1)


class SigninUiTest(unittest.TestCase):
    """The sign-in panel exists on the class step, email-only."""

    def test_website_signin_panel(self):
        html = _read("static/index.html")
        # Inside the class step, after the class options.
        self.assertGreater(html.index('id="class-signin"'),
                           html.index('id="class-step"'))
        for ident in ("class-signin-continue",
                      "class-signedin-note", "class-signedin-email",
                      "class-signout", "class-signin-error"):
            self.assertIn('id="%s"' % ident, html, ident)
        # Email only: no password field and no social buttons anywhere
        # near the sign-in panel.
        panel = html[html.index('id="class-signin"'):
                     html.index('id="class-discount-note"')]
        self.assertNotIn("password", panel.lower())
        self.assertNotIn("Google", panel)
        self.assertNotIn("Apple", panel)
        self.assertNotIn("Facebook", panel)
        self.assertIn("Continue", panel)
        # NO CODES (owner 2026-11-22): no code field, no code button,
        # no code wording anywhere in the panel.
        self.assertNotIn("code-field", panel)
        self.assertNotIn("signin-code", panel)
        self.assertNotIn("Verify code", panel)
        self.assertNotIn("6-digit", panel)
        self.assertNotIn("Email me a sign-in code", panel)

    def test_app_signin_panel(self):
        html = _read("static/customer-app.html")
        self.assertGreater(html.index('id="ca-signin"'),
                           html.index('id="ca-class-step"'))
        for ident in ("ca-signin-continue",
                      "ca-signedin-note", "ca-signedin-email",
                      "ca-signout", "ca-signin-error"):
            self.assertIn('id="%s"' % ident, html, ident)
        panel = html[html.index('id="ca-signin"'):
                     html.index('id="ca-class-discount-note"')]
        self.assertNotIn("password", panel.lower())
        self.assertNotIn("Google", panel)
        self.assertNotIn("Apple", panel)
        self.assertNotIn("Facebook", panel)
        self.assertIn("Continue", panel)
        self.assertNotIn("code-field", panel)
        self.assertNotIn("signin-code", panel)
        self.assertNotIn("Verify code", panel)
        self.assertNotIn("6-digit", panel)
        self.assertNotIn("Email me a sign-in code", panel)

    def test_website_signin_wiring(self):
        js = _read("static/js/customer.js")
        for endpoint in ("/api/customers/me",
                         "/api/customers/signin",
                         "/api/customers/signout"):
            self.assertIn('"%s"' % endpoint, js, endpoint)
        # NO CODES: the old code endpoints are gone entirely.
        self.assertNotIn("/api/customers/signin/request", js)
        self.assertNotIn("/api/customers/signin/verify", js)
        # The gate: Select cannot proceed unless signed in with the
        # same email as the booking.
        self.assertIn("state.customerSignedIn", js)
        self.assertIn("Please sign in first", js)
        # A 401 from /contact re-opens the sign-in step.
        self.assertIn("res.status === 401", js)
        self.assertIn("Your sign-in expired", js)
        # Signed-in sessions pre-fill email + phone on the class step.
        self.assertIn("refreshCustomerSignin()", js)

    def test_app_signin_wiring(self):
        js = _read("static/js/customer-app.js")
        for endpoint in ("/api/customers/me",
                         "/api/customers/signin",
                         "/api/customers/signout"):
            self.assertIn('"%s"' % endpoint, js, endpoint)
        self.assertNotIn("/api/customers/signin/request", js)
        self.assertNotIn("/api/customers/signin/verify", js)
        self.assertIn("state.customerSignedIn", js)
        self.assertIn("Please sign in first", js)
        self.assertIn("res.status === 401", js)
        self.assertIn("refreshCustomerSignin()", js)


class SecondPageStripTest(unittest.TestCase):
    """Below the booking flow: nothing but the powered-by line and
    the black footer with the address."""

    def test_flow_state_sync(self):
        js = _read("static/js/customer.js")
        self.assertIn("function syncFlowState()", js)
        # Every post-form step puts the page in flow state.
        for step in ("flight-step", "hourly-class-step", "class-step",
                     "pay-panel", "thankyou-block", "status-card"):
            self.assertIn('"%s"' % step, js, step)
        self.assertIn('document.body.classList.toggle("in-booking-flow"',
                      js)
        # show()/hide() are the choke point, so every transition
        # re-syncs, including back-buttons and reloads.
        self.assertIn("syncFlowState();", js)

    def test_strip_css(self):
        css = _read("static/css/customer.css")
        # Exactly the strip rules, nothing else: the two rule blocks
        # hide the homepage sections and the footer link columns.
        rules = re.findall(r"(body\.in-booking-flow[^{]*)\{([^}]*)\}",
                           css)
        self.assertEqual(len(rules), 2, rules)
        selectors = " ".join(s for s, _ in rules)
        for target in ("main > section.section",
                       "main > section.app-band", ".footer-inner",
                       ".footer-cols"):
            self.assertIn(target, selectors, target)
        for _, body in rules:
            self.assertEqual(body.strip(), "display: none;")
        # The powered-by line, the address footer and the floating
        # chat button are not in any strip rule.
        for kept in ("#powered-by", ".footer-nap", ".chat-fab"):
            self.assertNotIn(kept, selectors, kept)

    def test_powered_by_line(self):
        html = _read("static/index.html")
        self.assertIn('id="powered-by"', html)
        # The brand name in the line is the wordmark: "Noel" plain,
        # "Chauffer" in the gold span (standing rule).
        m = re.search(r'<p id="powered-by">(.*?)</p>', html, re.S)
        self.assertIsNotNone(m, "powered-by line")
        self.assertIn('<span class="wordmark">Noel <span>Chauffer</span></span>',
                      m.group(1))
        css = _read("static/css/customer.css")
        body = _rule(css, "#powered-by .wordmark")
        self.assertIn("color: var(--ink);", body)


class CustomerAppWhiteTest(unittest.TestCase):
    """Customer app: white background, black booking form. The
    website background and the driver app are untouched."""

    def test_white_canvas_black_form(self):
        css = _read("static/css/customer-app.css")
        body = _rule(css, "body")
        self.assertIn("background: #ffffff;", body)
        phone = _rule(css, ".phone")
        self.assertIn("background: var(--white);", phone)
        screen = _rule(css, ".screen")
        self.assertIn("background: var(--white);", screen)
        self.assertIn("color-scheme: light;", screen)
        self.assertNotIn("linear-gradient(180deg, #101012", screen)
        card = _rule(css, "#ca-booking-card")
        self.assertIn("background: var(--black);", card)
        self.assertIn("color-scheme: dark;", card)
        # The heading inside the black card stays white.
        self.assertIn("color: var(--white);",
                      _rule(css, "#ca-booking-card h2"))
        # Headings on the white screen are dark ink.
        self.assertIn("color: var(--ink);", _rule(css, ".screen h2"))
        # The header stays black (white Noel + gold Chauffer).
        head = _rule(css, ".app-head")
        self.assertIn("background: var(--black);", head)
        # The tab bar stays black too.
        self.assertIn("background: var(--black);",
                      _rule(css, ".tabbar"))

    def test_app_powered_by_line(self):
        html = _read("static/customer-app.html")
        self.assertIn('id="ca-powered-by"', html)
        m = re.search(r'<p id="ca-powered-by">(.*?)</p>', html, re.S)
        self.assertIsNotNone(m, "app powered-by line")
        self.assertIn('<span class="brand">Noel <span>Chauffer</span></span>',
                      m.group(1))
        css = _read("static/css/customer-app.css")
        body = _rule(css, "#ca-powered-by .brand span")
        self.assertIn("color: var(--wordmark-gold);", body)
        self.assertIn("linear-gradient(105deg", body)
        self.assertIn("#F6E27A", body)

    def test_website_background_unchanged(self):
        css = _read("static/css/customer.css")
        # The website keeps its own page background; nothing in this
        # batch turns the website white.
        self.assertNotIn("body { background: #ffffff;", css)
        self.assertNotIn("background: #ffffff;\n  color: var(--ink);",
                         css)


class GoldenChaufferTest(unittest.TestCase):
    """Standing rule: "Chauffer" is always the same bright gold
    (#D4AF37 with the sheen) on the website, the customer app and
    the driver app. "Noel" stays plain."""

    def test_bright_gold_everywhere(self):
        for rel in ("static/css/customer.css",
                    "static/css/customer-app.css",
                    "static/css/driver.css"):
            css = _read(rel)
            self.assertIn("--wordmark-gold: #D4AF37;", css, rel)

    def test_powered_by_uses_wordmark_gold(self):
        css = _read("static/css/customer.css")
        # The powered-by line's inner span picks up the gold from
        # the .wordmark span rule.
        body = _rule(css, ".wordmark span")
        self.assertIn("color: var(--wordmark-gold);", body)
        self.assertIn("linear-gradient(105deg", body)
        self.assertIn("#F6E27A", body)

    def test_driver_app_untouched(self):
        # The driver app is out of this batch entirely.
        import subprocess
        out = subprocess.check_output(
            ["git", "diff", "--name-only"],
            cwd=REPO_DIR, text=True)
        changed = set(out.split())
        self.assertNotIn("static/css/driver.css", changed)
        self.assertNotIn("static/driver.html", changed)
        self.assertNotIn("static/js/driver.js", changed)


class MyRidesByEmailTest(unittest.TestCase):
    """Signed-in customers see their own rides by email; the phone
    lookup stays for older rides."""

    def test_website_history_by_email(self):
        js = _read("static/js/ride-history.js")
        self.assertIn("/api/customers/me", js)
        self.assertIn("/api/bookings?email=", js)
        self.assertIn("/api/bookings?phone=", js)
        for rel in ("static/index.html",
                    "static/your-ride-history.html"):
            html = _read(rel)
            self.assertIn('id="history-signedin"', html, rel)

    def test_app_my_rides_by_email(self):
        js = _read("static/js/customer-app.js")
        self.assertIn("loadHistoryByEmail", js)
        self.assertIn("refreshHistorySignin", js)
        self.assertIn("/api/bookings?email=", js)
        self.assertIn("/api/bookings?phone=", js)
        self.assertIn('if (name === "rides") refreshHistorySignin();', js)
        html = _read("static/customer-app.html")
        self.assertIn('id="ca-history-signedin"', html)


if __name__ == "__main__":
    unittest.main()
