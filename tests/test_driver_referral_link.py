"""Tests for the driver referral link (owner decision 2026-11-18,
voice call + chat confirmation 09:35 EST).

- The driver app has a referral section on the Profile screen showing
  EXACTLY "Get $5 in cash for each ride you refer." plus the driver's
  shareable link (Copy + Share, same pattern as the customer referral
  link) and his own referral earnings.
- The referral is a LINK, not a code number: /driver?ref=CODE lands a
  signed-out friend straight in driver registration (bypassing the
  login screen), with the referrer captured. The registration form
  itself has no extra field or step.
- Noel pays the referring driver $5 for each job the referred driver
  completes, up to the referred driver's first 15 jobs (max $75).
  The new driver pays nothing. Tracking only — no money moves.
- Referral records are visible read-only in the owner dashboard.
- SEPARATE from the customer referral: different table, different
  code namespace ("DRV-" vs "NOEL-"), different link. Customer
  referral behavior is unchanged (pinned here and in
  tests/test_customer_referral_link.py).
- The login-first flow is unchanged for visits without a referral
  link (pinned in tests/test_driver_entry_flow.py).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import re
import sys
import tempfile
import unittest
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-driver-referral-")
_db_url = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["DATABASE_URL"] = _db_url
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "driver-referral-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Driver Referral Customer"}
CODE_RE = re.compile(r"^DRV-[A-Z0-9]{6}$")


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class DriverReferralCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, referral_code=None):
        self._driver_seq += 1
        data = {
            "name": f"Referral Driver {self._driver_seq}",
            "phone": f"+1555007{self._driver_seq:04d}",
            "email": f"rd{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"R{self._driver_seq:05d}",
            "state": "New York", "bank_account_number": "123456789",
            "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_tlc_license": "2030-01-01",
            "expiry_fh1_insurance": "2030-01-01",
            "expiry_registration": "2030-01-01",
            "expiry_inspection": "2030-01-01",
            "expiry_vehicle_permit": "2030-01-01",
            "expiry_vehicle_registration": "2030-01-01",
            "expiry_insurance_card": "2030-01-01",
            "profile_photo": (io.BytesIO(photo_factory.VALID_PROFILE_PHOTO), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(photo_factory.doc_photo()), "license.png"),
            "doc_tlc_license": (io.BytesIO(photo_factory.doc_photo()), "tlc.png"),
            "doc_fh1": (io.BytesIO(photo_factory.doc_photo()), "fh1.png"),
            "doc_registration": (io.BytesIO(photo_factory.doc_photo()), "reg.png"),
            "doc_inspection": (io.BytesIO(photo_factory.doc_photo()), "insp.png"),
            "doc_vehicle_permit": (io.BytesIO(photo_factory.doc_photo()), "permit.png"),
        }
        if referral_code is not None:
            data["referral_code"] = referral_code
        resp = self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def referral_view(self, token):
        resp = self.client.get("/api/drivers/me/referral",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return resp.get_json()

    def driver_row(self, driver_id):
        with app_module.app.app_context():
            d = app_module.db.session.get(app_module.Driver, driver_id)
            return dict(id=d.id, name=d.name, phone=d.phone, email=d.email,
                        referral_code=d.referral_code,
                        referred_by_driver_id=d.referred_by_driver_id)

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Driver Referral Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "driverreferral@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def complete_job(self, token, time="12:00"):
        booking = self.book(time=time)
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay", json=dict(CARD))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.post(
            f"/api/drivers/me/offers/{booking['id']}/accept",
            headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        for event in ("en_route", "arrived", "start", "complete"):
            resp = self.client.post(
                f"/api/drivers/me/trip/{booking['id']}/event",
                json={"event": event}, headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")
        return booking

    def credit_rows(self):
        with app_module.app.app_context():
            return [dict(booking_id=c.booking_id,
                         referrer_driver_id=c.referrer_driver_id,
                         referrer_name=c.referrer_name,
                         referred_driver_id=c.referred_driver_id,
                         referred_driver_name=c.referred_driver_name,
                         amount=c.amount)
                    for c in app_module.DriverReferralCredit.query.order_by(
                        app_module.DriverReferralCredit.id).all()]

    def owner_login(self, client=None):
        (client or self.client).post("/api/owner/login", json={"pin": "9999"})

    # -- codes: minted, unique, stable ------------------------------------
    def test_registration_mints_unique_referral_code(self):
        _, token_a = self.register_driver()
        _, token_b = self.register_driver()
        code_a = self.referral_view(token_a)["referral_code"]
        code_b = self.referral_view(token_b)["referral_code"]
        self.assertRegex(code_a, CODE_RE)
        self.assertRegex(code_b, CODE_RE)
        self.assertNotEqual(code_a, code_b)

    def test_referral_code_stable_across_loads(self):
        _, token = self.register_driver()
        first = self.referral_view(token)["referral_code"]
        second = self.referral_view(token)["referral_code"]
        self.assertEqual(first, second)

    def test_pre_feature_driver_gets_code_on_first_load(self):
        # A driver row with no code (registered before referral codes
        # existed) gets one minted on first referral-section load,
        # then keeps it.
        with app_module.app.app_context():
            _old_token = "old-driver-token"
            d = app_module.Driver(
                name="Old Driver", phone="+15550009999",
                email="old@test.com", car_model="Cadillac CT6",
                car_colour="Black", plate="OLD0001",
                token=_old_token,
            )
            app_module.db.session.add(d)
            app_module.db.session.commit()
            driver_id = d.id
        first = self.referral_view("old-driver-token")
        self.assertRegex(first["referral_code"], CODE_RE)
        second = self.referral_view("old-driver-token")
        self.assertEqual(first["referral_code"], second["referral_code"])
        self.assertEqual(self.driver_row(driver_id)["referral_code"],
                         first["referral_code"])

    def test_referral_endpoint_requires_driver_auth(self):
        resp = self.client.get("/api/drivers/me/referral")
        self.assertEqual(resp.status_code, 401)
        resp = self.client.get("/api/drivers/me/referral",
                               headers={"X-Driver-Token": "bogus"})
        self.assertEqual(resp.status_code, 401)

    # -- registration capture --------------------------------------------
    def test_registration_via_referral_link_stores_referrer(self):
        driver_a, token_a = self.register_driver()
        code_a = self.referral_view(token_a)["referral_code"]
        driver_b, token_b = self.register_driver(referral_code=code_a)
        row_b = self.driver_row(driver_b["id"])
        self.assertEqual(row_b["referred_by_driver_id"], driver_a["id"])
        # The referred driver gets his OWN code, distinct from the
        # referrer's, so he can refer others in turn.
        code_b = self.referral_view(token_b)["referral_code"]
        self.assertRegex(code_b, CODE_RE)
        self.assertNotEqual(code_a, code_b)
        # The referrer sees the friend in his breakdown: 0 jobs, $0.
        view_a = self.referral_view(token_a)
        self.assertEqual(len(view_a["referred_drivers"]), 1)
        friend = view_a["referred_drivers"][0]
        self.assertEqual(friend["name"], driver_b["name"])
        self.assertEqual(friend["jobs_counted"], 0)
        self.assertEqual(friend["earned"], 0)
        self.assertEqual(view_a["total_earned"], 0)
        self.assertEqual(view_a["jobs_counted"], 0)

    def test_invalid_referral_code_registers_normally(self):
        driver, _ = self.register_driver(referral_code="DRV-BOGUS1")
        self.assertIsNone(self.driver_row(driver["id"])["referred_by_driver_id"])

    def test_no_referral_code_registers_normally(self):
        driver, _ = self.register_driver()
        self.assertIsNone(self.driver_row(driver["id"])["referred_by_driver_id"])

    def test_referral_code_matching_is_case_insensitive(self):
        driver_a, token_a = self.register_driver()
        code_a = self.referral_view(token_a)["referral_code"]
        driver_b, _ = self.register_driver(referral_code=code_a.lower())
        self.assertEqual(self.driver_row(driver_b["id"])["referred_by_driver_id"],
                         driver_a["id"])

    def test_customer_code_does_not_resolve_as_driver_referrer(self):
        # Customer codes ("NOEL-...") live in a separate table and
        # namespace: presenting one at driver registration stores no
        # referrer and never blocks registration.
        booking = self.book()
        customer_code = booking["referral_code"]
        self.assertTrue(customer_code.startswith("NOEL-"))
        driver, _ = self.register_driver(referral_code=customer_code)
        self.assertIsNone(self.driver_row(driver["id"])["referred_by_driver_id"])

    # -- credit rule ------------------------------------------------------
    def test_credit_per_completed_job_first_15_only(self):
        driver_a, token_a = self.register_driver()
        code_a = self.referral_view(token_a)["referral_code"]
        driver_b, token_b = self.register_driver(referral_code=code_a)
        # 16 completed jobs: only the first 15 credit $5 each.
        for i in range(16):
            self.complete_job(token_b, time="%02d:00" % ((12 + i) % 24))
        rows = self.credit_rows()
        self.assertEqual(len(rows), 15)
        for row in rows:
            self.assertEqual(row["amount"], Decimal("5.00"))
            self.assertEqual(row["referrer_driver_id"], driver_a["id"])
            self.assertEqual(row["referred_driver_id"], driver_b["id"])
            self.assertEqual(row["referrer_name"], driver_a["name"])
            self.assertEqual(row["referred_driver_name"], driver_b["name"])
        view_a = self.referral_view(token_a)
        self.assertEqual(view_a["total_earned"], 75.00)
        self.assertEqual(view_a["jobs_counted"], 15)
        self.assertEqual(view_a["credit_per_job"], 5.00)
        self.assertEqual(view_a["max_jobs_per_driver"], 15)
        friend = view_a["referred_drivers"][0]
        self.assertEqual(friend["jobs_counted"], 15)
        self.assertEqual(friend["earned"], 75.00)

    def test_no_referrer_no_credits(self):
        _, token = self.register_driver()
        self.complete_job(token)
        self.assertEqual(self.credit_rows(), [])

    def test_self_referral_earns_nothing(self):
        driver, token = self.register_driver()
        with app_module.app.app_context():
            d = app_module.db.session.get(app_module.Driver, driver["id"])
            d.referred_by_driver_id = d.id
            app_module.db.session.commit()
        self.complete_job(token)
        self.assertEqual(self.credit_rows(), [])

    def test_referred_driver_sees_only_own_referral_view(self):
        driver_a, token_a = self.register_driver()
        code_a = self.referral_view(token_a)["referral_code"]
        _, token_b = self.register_driver(referral_code=code_a)
        self.complete_job(token_b)
        view_b = self.referral_view(token_b)
        self.assertEqual(view_b["total_earned"], 0)
        self.assertEqual(view_b["referred_drivers"], [])
        # Nothing about the referrer leaks into the referred driver's
        # own view.
        self.assertNotIn(driver_a["name"], str(view_b))

    def test_referral_earnings_not_in_ride_earnings(self):
        # Referral earnings live in the referral section only: the
        # ride-earnings endpoint is untouched by referral credits.
        driver_a, token_a = self.register_driver()
        code_a = self.referral_view(token_a)["referral_code"]
        _, token_b = self.register_driver(referral_code=code_a)
        self.complete_job(token_b)
        earn = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token_a}).get_json()
        self.assertEqual(earn["completed_rides"], 0)
        self.assertEqual(earn["total_earnings"], 0)

    # -- owner visibility --------------------------------------------------
    def test_owner_referrals_endpoint(self):
        fresh = app_module.app.test_client()
        self.assertEqual(fresh.get("/api/owner/driver-referrals").status_code, 401)
        driver_a, token_a = self.register_driver()
        code_a = self.referral_view(token_a)["referral_code"]
        driver_b, token_b = self.register_driver(referral_code=code_a)
        self.complete_job(token_b, time="12:00")
        self.complete_job(token_b, time="13:00")
        # A second friend with no completed jobs yet still shows.
        driver_c, _ = self.register_driver(referral_code=code_a)
        self.owner_login()
        resp = self.client.get("/api/owner/driver-referrals")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["total_jobs_counted"], 2)
        self.assertEqual(body["total_earned"], 10.00)
        by_name = {r["referred_driver_name"]: r for r in body["referrals"]}
        self.assertEqual(set(by_name), {driver_b["name"], driver_c["name"]})
        row_b = by_name[driver_b["name"]]
        self.assertEqual(row_b["referrer_name"], driver_a["name"])
        self.assertEqual(row_b["jobs_counted"], 2)
        self.assertEqual(row_b["earned"], 10.00)
        self.assertIsNotNone(row_b["registered_at"])
        row_c = by_name[driver_c["name"]]
        self.assertEqual(row_c["jobs_counted"], 0)
        self.assertEqual(row_c["earned"], 0)

    def test_owner_referrals_empty(self):
        self.owner_login()
        body = self.client.get("/api/owner/driver-referrals").get_json()
        self.assertEqual(body["referrals"], [])
        self.assertEqual(body["total_jobs_counted"], 0)
        self.assertEqual(body["total_earned"], 0)

    # -- test-only resets ---------------------------------------------------
    def test_clear_rides_deletes_credits_keeps_drivers(self):
        driver_a, token_a = self.register_driver()
        code_a = self.referral_view(token_a)["referral_code"]
        driver_b, token_b = self.register_driver(referral_code=code_a)
        self.complete_job(token_b)
        self.assertEqual(len(self.credit_rows()), 1)
        self.owner_login()
        resp = self.client.post("/api/owner/clear-rides", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["deleted"]["driver_referral_credits"], 1)
        self.assertEqual(self.credit_rows(), [])
        # Drivers (and the referrer link) survive a ride clear.
        self.assertEqual(self.driver_row(driver_b["id"])["referred_by_driver_id"],
                         driver_a["id"])

    def test_clear_drivers_keeps_credit_snapshots(self):
        driver_a, token_a = self.register_driver()
        code_a = self.referral_view(token_a)["referral_code"]
        _, token_b = self.register_driver(referral_code=code_a)
        self.complete_job(token_b)
        self.owner_login()
        resp = self.client.post("/api/owner/clear-drivers", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        rows = self.credit_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["referrer_name"], driver_a["name"])
        body = self.client.get("/api/owner/driver-referrals").get_json()
        self.assertEqual(len(body["referrals"]), 1)
        self.assertEqual(body["referrals"][0]["earned"], 5.00)
        self.assertIsNone(body["referrals"][0]["registered_at"])

    # -- customer referral unchanged ---------------------------------------
    def test_customer_referral_unchanged(self):
        first = self.book()
        code = first["referral_code"]
        self.assertTrue(code.startswith("NOEL-"))
        second = self.book(referral_code=code)
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, second["id"])
            self.assertEqual(row.referral_code_used, code)
        resp = self.client.post("/api/bookings", json={
            "customer_name": "X", "phone": "+15550009998",
            "email": "x@test.com", "pickup": "JFK Airport",
            "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
            "referral_code": "NOEL-BOGUS",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid referral code.", resp.get_json()["error"])

    # -- shipped UI pins -----------------------------------------------------
    def test_profile_screen_has_referral_section_with_exact_line(self):
        html = read("static/driver.html")
        profile = html[html.index('id="screen-profile"'):html.index('id="tabbar"')]
        # The owner's dictated line, verbatim.
        self.assertIn("Get $5 in cash for each ride you refer.", profile)
        for element_id in ("driver-referral-box", "driver-referral-show-btn",
                           "driver-referral-link-line",
                           "driver-referral-link-anchor",
                           "driver-referral-copy-btn",
                           "driver-referral-share-btn",
                           "driver-referral-earnings"):
            self.assertIn('id="%s"' % element_id, profile)
        self.assertIn("Refer a Friend", profile)
        self.assertIn("Copy link", profile)
        self.assertIn("Share link", profile)
        # The line appears exactly once in the whole driver app.
        self.assertEqual(html.count("Get $5 in cash for each ride you refer."), 1)

    def test_registration_form_has_no_referral_field(self):
        # Registration stays easy: no extra field or step — the
        # referrer rides along in a hidden submit field only.
        html = read("static/driver.html")
        register = html[html.index('id="screen-register"'):html.index('id="screen-home"')]
        self.assertNotIn("referral", register.lower())

    def test_driver_js_referral_link_and_section(self):
        js = read("static/js/driver.js")
        # Link format: the driver-app URL with the code as ?ref=.
        self.assertIn('"/driver?ref=" + encodeURIComponent(code)', js)
        self.assertIn('get("ref")', js)
        self.assertIn("/api/drivers/me/referral", js)
        # The referrer is captured at submit time, hidden field only.
        self.assertIn('fd.append("referral_code", state.pendingReferralCode);', js)
        # The referral section loads with the Profile screen.
        self.assertIn('if (name === "profile") { renderProfile(); loadDriverReferral(); }', js)
        # Copy + native Share wiring, same pattern as the customer link.
        self.assertIn("navigator.share", js)
        self.assertIn("driver-referral-copy-btn", js)
        self.assertIn("driver-referral-share-btn", js)
        self.assertIn("driver-referral-show-btn", js)

    def test_driver_js_referral_landing_only_when_signed_out(self):
        js = read("static/js/driver.js")
        boot = js[js.index("function boot()"):js.index("function enterApp")]
        # The referral landing lives inside the no-token branch: a
        # signed-in driver never gets routed to registration.
        no_token = boot[boot.index("if (!token) {"):]
        self.assertLess(no_token.index("referralCodeFromUrl()"),
                        no_token.index('showScreen("register")'))
        # The referrer is kept in memory only, and the query is
        # stripped so a later reload lands on sign-in as usual.
        self.assertIn("state.pendingReferralCode = referralCode;", no_token)
        self.assertIn("stripReferralFromUrl();", no_token)
        self.assertIn("pendingReferralCode: null", js)

    def test_driver_css_has_referral_styles(self):
        css = read("static/css/driver.css")
        self.assertIn("#screen-profile .referral-box", css)
        self.assertIn("#screen-profile .referral-actions", css)
        self.assertIn("#driver-referral-link-line a", css)
        self.assertIn(".referral-earn-row", css)

    def test_owner_dashboard_has_referrals_section(self):
        html = read("static/owner.html")
        self.assertIn("Driver referrals", html)
        self.assertIn('id="referrals-feed"', html)
        js = read("static/js/owner.js")
        self.assertIn("/api/owner/driver-referrals", js)
        self.assertIn("loadDriverReferrals();", js)
        self.assertIn("No driver referrals yet.", js)


if __name__ == "__main__":
    unittest.main()
