"""Tests for the /owner PIN gate being server-side (owner decision
2026-11-23, voice call): a browser live-check 2026-11-23 ~03:33 EST
found the PIN screen was only a visual overlay — scrolling without
entering the PIN revealed the full dashboard (summary figures,
bookings table, drivers, bank details).

Root cause (reproduced in a fresh session): the server session never
expired — session["owner"] = True with no timestamp and no lifetime
— and owner.js auto-logged-in on page load (checkSession fetched
/api/owner/summary and opened the dashboard whenever a session
cookie existed). A browser that had logged in once stayed logged in
forever.

Fix, pinned here:
1. The owner session is timestamped at login and expires 8 hours
   later, absolute (OWNER_SESSION_MAX_AGE_SECONDS, default 28800).
   A session with no timestamp no longer counts.
2. The dashboard never auto-logs-in on page load: every visit
   starts at the PIN gate; the dashboard only opens after the PIN
   is typed and checked server-side.
3. Every owner data endpoint returns 401 without a valid session,
   and the served /owner page contains no booking/driver/bank data.

The address on /owner appears ONLY inside ride records as
pickup/drop-off (test booking data) — that is booking data, NOT a
published address, and is deliberately NOT removed.

Run:  python -m unittest discover -s tests -v
"""


import os
import sys
import tempfile
import time
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-pin-gate-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "pin-gate-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


OWNER_GET_ENDPOINTS = [
    "/api/owner/summary",
    "/api/owner/bookings",
    "/api/owner/bookings/1",
    "/api/owner/payouts",
    "/api/owner/alerts",
    "/api/owner/outbox",
    "/api/owner/support-messages",
    "/api/owner/driver-referrals",
    "/api/owner/document-flags",
    "/api/owner/expiring-documents",
    "/api/owner/drivers",
]

OWNER_POST_ENDPOINTS = [
    ("/api/owner/bookings/1/toll", {"toll": 5}),
    ("/api/owner/bookings/1/assign", {"driver_id": 1}),
    ("/api/owner/payouts/mark-paid", {"driver_id": 1, "start": "2026-11-16", "end": "2026-11-22"}),
    ("/api/owner/run-pickup-reminders", {}),
    ("/api/owner/run-expiry-alerts", {}),
    ("/api/owner/clear-rides", {"pin": "9999"}),
    ("/api/owner/clear-drivers", {"pin": "9999"}),
    ("/api/owner/drivers/1/remove", {"pin": "9999"}),
    ("/api/owner/bookings/1/remove", {"pin": "9999"}),
]


class OwnerPinGateCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()

    def _login(self, client=None, pin="9999"):
        client = client or self.client
        resp = client.post("/api/owner/login", json={"pin": pin})
        self.assertEqual(resp.status_code, 200, resp.get_json())
        return resp

    # -- fresh session: nothing is served ----------------------------------
    def test_fresh_session_all_owner_get_endpoints_401(self):
        for url in OWNER_GET_ENDPOINTS:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 401, url)

    def test_fresh_session_all_owner_post_endpoints_401(self):
        for url, body in OWNER_POST_ENDPOINTS:
            resp = self.client.post(url, json=body)
            self.assertEqual(resp.status_code, 401, url)

    def test_wrong_pin_401(self):
        resp = self.client.post("/api/owner/login", json={"pin": "0000"})
        self.assertEqual(resp.status_code, 401)

    def test_served_owner_page_contains_no_data(self):
        # Real-looking booking + driver data exists in the database…
        with app_module.app.app_context():
            b = app_module.Booking(
                customer_name="Pin Gate Customer", phone="929-385-7597",
                email="pingate.customer@example.com",
                pickup="180 Green Acres Road, East Valley Stream",
                dropoff="Times Square, New York",
                date="2026-11-23", time="12:00", ride_type="one_way",
                fare_total=154.78, driver_earnings=80.00,
                status="awaiting_payment")
            app_module.db.session.add(b)
            d = app_module.Driver(
                name="Pin Gate Driver", phone="929-555-0101",
                email="pingate.driver@example.com", car_model="Tesla Model 3",
                car_colour="White", plate="T100506C", token="pin-gate-token")
            app_module.db.session.add(d)
            app_module.db.session.commit()
        # …but a fresh session gets only the empty shell, no data.
        resp = self.client.get("/owner")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertNotIn("pingate.customer@example.com", html)
        self.assertNotIn("pingate.driver@example.com", html)
        self.assertNotIn("929-385-7597", html)
        self.assertNotIn("929-555-0101", html)
        self.assertNotIn("T100506C", html)
        self.assertNotIn("@", html)

    # -- a valid login still works ------------------------------------------
    def test_login_then_endpoints_200(self):
        self._login()
        for url in OWNER_GET_ENDPOINTS:
            # /bookings/1 does not exist in the fresh DB; require_owner
            # runs first, so an authed call reaches the handler (404),
            # never a 401.
            resp = self.client.get(url)
            self.assertNotEqual(resp.status_code, 401, url)
        resp = self.client.get("/api/owner/summary")
        self.assertEqual(resp.status_code, 200)

    # -- sessions expire: 8 hours, absolute --------------------------------
    def test_session_max_age_is_eight_hours(self):
        self.assertEqual(app_module.OWNER_SESSION_MAX_AGE_SECONDS, 28800)

    def test_session_without_timestamp_does_not_count(self):
        # Sessions from before the expiry was added carry only the
        # flag — they no longer open the dashboard.
        with self.client.session_transaction() as sess:
            sess["owner"] = True
        resp = self.client.get("/api/owner/summary")
        self.assertEqual(resp.status_code, 401)

    def test_expired_session_401(self):
        self._login()
        self.assertEqual(self.client.get("/api/owner/summary").status_code, 200)
        with self.client.session_transaction() as sess:
            sess["owner_authed_at"] = int(time.time()) - 28801
        resp = self.client.get("/api/owner/summary")
        self.assertEqual(resp.status_code, 401)

    def test_fresh_session_within_lifetime_200(self):
        self._login()
        with self.client.session_transaction() as sess:
            sess["owner_authed_at"] = int(time.time()) - 60
        resp = self.client.get("/api/owner/summary")
        self.assertEqual(resp.status_code, 200)

    def test_logout_clears_session(self):
        self._login()
        self.assertEqual(self.client.get("/api/owner/summary").status_code, 200)
        resp = self.client.post("/api/owner/logout")
        self.assertEqual(resp.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertNotIn("owner", sess)
            self.assertNotIn("owner_authed_at", sess)
        self.assertEqual(self.client.get("/api/owner/summary").status_code, 401)

    # -- the page never auto-logs-in -----------------------------------------
    def test_no_auto_login_on_page_load(self):
        js = read("static/js/owner.js")
        # "checkSession" survives only in the comment explaining why
        # auto-login was removed — no call to it anywhere.
        self.assertEqual(js.count("checkSession"), 1)
        self.assertIn("backToPinGate", js)
        html = read("static/owner.html")
        self.assertIn('<div class="hidden" id="dashboard">', html)


if __name__ == "__main__":
    unittest.main()
