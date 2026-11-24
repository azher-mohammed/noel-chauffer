"""Driver dashboard website (owner order, voice call 2026-11-24
~01:46 EST, go-ahead "Haan, dashboard banao" ~01:54 EST): a separate
driver dashboard website, SIMPLE, exactly like the driver app —
jobs + earnings + driver app badges ONLY.

Rules pinned here:
- GET /driver-dashboard -> 200 with the sign-in form for a signed-out
  visitor. The page shows Sign in, Jobs and Earnings, and the two
  driver app badges (Google Play + App Store, 48px, one row), both
  linking to /driver — the working driver app, because the driver app
  has no store listing yet (STORE_URL placeholders in the native app;
  swap the hrefs to the real store URLs when it is published).
- NOTHING else on the page: no Documents, Profile, Tax info, Refer,
  registration or chat text anywhere.
- The page is a wider desktop-friendly column (max-width 880px),
  not the driver app's 430px phone frame, same branding.
- The script reuses the driver app's sign-in token key
  (noel_driver_token) so a driver signed in on /driver stays signed
  in here, and only calls the driver endpoints: signin,
  forgot-password, /api/drivers/me, offers (+ accept/decline),
  active-trip, availability, earnings.
- A job offer shows pickup, drop-off and time only — no amounts.
  Earnings are the driver's own pay only: the script never renders
  a customer payment figure or miles, and never calls a customer
  endpoint.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock  # noqa: F401  (kept for parity with sibling suites)

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-driver-dashboard-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "driver-dashboard-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
PAGE = (REPO_DIR / "static" / "driver-dashboard.html").read_text()
JS = (REPO_DIR / "static" / "js" / "driver-dashboard.js").read_text()
DRIVER_CSS = (REPO_DIR / "static" / "css" / "driver.css").read_text()
DASHBOARD_CSS = (REPO_DIR / "static" / "css" / "driver-dashboard.css").read_text()

ALLOWED_ENDPOINTS = {
    "/api/drivers/me/signin",
    "/api/drivers/me/forgot-password",
    "/api/drivers/me",
    "/api/drivers/me/offers",
    "/api/drivers/me/active-trip",
    "/api/drivers/me/availability",
    "/api/drivers/me/earnings",
}


def _rule(css, selector):
    return " ".join(
        m.group(1)
        for m in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    )


class DriverDashboardPageCase(unittest.TestCase):
    def test_route_returns_200_with_signin_jobs_earnings_and_badges(self):
        client = app_module.app.test_client()
        resp = client.get("/driver-dashboard")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("Sign in", body)
        self.assertIn("Jobs", body)
        self.assertIn("Earnings", body)
        self.assertIn('href="/driver"><img src="/static/img/google-play-badge.png"', body)
        self.assertIn('href="/driver"><img src="/static/img/app-store-badge.svg"', body)
        # The served page IS the dashboard file, not the "not built yet" stub.
        self.assertIn("Driver dashboard", body)
        self.assertNotIn("not built yet", body)

    def test_page_has_no_out_of_scope_sections(self):
        for banned in ("Documents", "Profile", "Tax info", "Refer",
                       "registration", "chat", "New driver registration"):
            self.assertNotIn(banned, PAGE, "page must not carry %r" % banned)

    def test_badges_equal_height_on_one_row(self):
        self.assertEqual(PAGE.count('height="48"'), 2)
        badges = _rule(DASHBOARD_CSS, ".store-badges")
        self.assertIn("display: flex", badges)
        self.assertIn("align-items: center", badges)
        img = _rule(DASHBOARD_CSS, ".store-badges img")
        self.assertIn("height: 48px", img)
        self.assertIn("display: block", img)

    def test_dashboard_is_wider_than_the_phone_frame(self):
        dash = _rule(DASHBOARD_CSS, ".dashboard")
        self.assertIn("max-width: 880px", dash)
        phone = _rule(DRIVER_CSS, ".phone")
        self.assertIn("max-width: 430px", phone)

    def test_driver_app_stylesheet_carries_no_dashboard_rules(self):
        # The dashboard's own rules live in driver-dashboard.css; the
        # driver app's stylesheet stays untouched by this change.
        self.assertNotIn(".dashboard", DRIVER_CSS)
        self.assertNotIn(".store-badges", DRIVER_CSS)

    def test_js_shares_the_driver_app_token_key(self):
        self.assertIn('"noel_driver_token"', JS)

    def test_js_calls_only_driver_endpoints(self):
        urls = re.findall(r'"(/api/[^"]+)"', JS)
        self.assertTrue(urls, "expected fetch URLs in the dashboard script")
        for url in urls:
            self.assertTrue(
                url in ALLOWED_ENDPOINTS or url.startswith("/api/drivers/me/offers/"),
                "unexpected endpoint %r" % url,
            )

    def test_js_never_renders_customer_payment_figures(self):
        self.assertNotIn("fare", JS.lower())
        self.assertNotIn("miles", JS.lower())
        self.assertNotIn("/api/customers", JS)
        self.assertNotIn("total_fare", JS)

    def test_js_polls_offers_every_five_seconds(self):
        self.assertIn("setInterval", JS)
        self.assertIn("5000", JS)


if __name__ == "__main__":
    unittest.main()
