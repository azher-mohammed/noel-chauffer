"""Tests for the bookings pause — ALL prices removed, bookings stopped.

Owner decision (2026-11-20): "Sab kuch nikalo, booking bhi rok do"
(remove everything, stop bookings too). While prices are being
updated:

- POST /api/bookings (one-way and hourly) is rejected with 503 and
  stores nothing; class selection and card payment are rejected too,
  so no charge can happen.
- No $ amount or total reaches the customer or the driver: the
  booking view, history rows, offers, accept/active-trip responses,
  earnings, tax info and referral summary carry no money figures.
- The paused notice ("Bookings are paused while we update our
  prices. Please check back soon.") is on the homepage, the customer
  app and the driver app; the only $ figure left anywhere
  customer/driver-facing is the $2,000 IRS 1099-NEC threshold.
- Existing rides keep working (accept, trip stages, completion) —
  just without money shown.
- The pause changes NOTHING for the owner (dashboard money figures
  stay) and nothing in pricing.py (internal $9/$10 rates stay in
  code for the new price-list work).

This module deliberately does NOT set BOOKINGS_PAUSED=false: the
pause defaults to on, and fixtures that need a booking flip
app_module.BOOKINGS_PAUSED off and back on again.

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
# NOTE: no BOOKINGS_PAUSED=false here — the pause must be ON by default.
_tmpdir = tempfile.mkdtemp(prefix="noel-bookings-paused-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "paused.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "paused-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
from pricing import compute_one_way  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAUSED_MSG = "Bookings are paused while we update our prices. Please check back soon."
D = Decimal


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class PausedCase(unittest.TestCase):
    """In-process API tests with a fresh DB per test; pause ON."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = True
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0

    def tearDown(self):
        app_module.BOOKINGS_PAUSED = True

    # -- helpers ---------------------------------------------------------
    def _pause_off(self):
        app_module.BOOKINGS_PAUSED = False

    def _pause_on(self):
        app_module.BOOKINGS_PAUSED = True

    def register_driver(self):
        self._driver_seq += 1
        phone = f"+1555000{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Test Driver {self._driver_seq}", "phone": phone,
            "email": f"d{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"T{self._driver_seq:05d}",
            "state": "New York", "bank_account_number": "123456789", "bank_routing_number": "021000021",
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
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def _booking_payload(self, phone="+15550009999"):
        return {
            "customer_name": "Paused Customer", "phone": phone,
            "email": "cust@test.com", "pickup": "JFK Airport",
            "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }

    def make_paid_booking(self, token=None):
        """Create + pay a booking with the pause lifted, then re-pause."""
        self._pause_off()
        try:
            resp = self.client.post("/api/bookings", json=self._booking_payload())
            self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
            booking_id = resp.get_json()["booking"]["id"]
            resp = self.client.post(f"/api/bookings/{booking_id}/pay", json={
                "card_number": "4242424242424242", "card_exp": "12/30",
                "card_cvc": "123", "card_name": "Paused Customer"})
            self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        finally:
            self._pause_on()
        return booking_id

    def complete_ride(self, booking_id, token):
        for event in ("en_route", "arrived", "start", "complete"):
            resp = self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                    json={"event": event},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")

    # -- the pause itself --------------------------------------------------
    def test_pause_is_on_by_default(self):
        self.assertTrue(app_module.BOOKINGS_PAUSED)
        self.assertTrue(app_module.bookings_paused())

    def test_create_one_way_rejected_and_nothing_stored(self):
        resp = self.client.post("/api/bookings", json=self._booking_payload())
        self.assertEqual(resp.status_code, 503)
        self.assertIn("paused", resp.get_json()["error"].lower())
        with app_module.app.app_context():
            self.assertEqual(app_module.Booking.query.count(), 0)

    def test_create_hourly_rejected(self):
        payload = {"customer_name": "Paused Customer", "phone": "+15550009999",
                   "email": "cust@test.com", "pickup": "JFK Airport",
                   "date": "2030-06-01", "time": "12:00",
                   "ride_type": "hourly", "hours": 2}
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 503)
        with app_module.app.app_context():
            self.assertEqual(app_module.Booking.query.count(), 0)

    def test_vehicle_class_and_pay_blocked(self):
        booking_id = self.make_paid_booking()
        # A fresh unpaid booking for the class/pay checks.
        self._pause_off()
        try:
            resp = self.client.post("/api/bookings",
                                    json=self._booking_payload(phone="+15550008888"))
            self.assertEqual(resp.status_code, 201)
            unpaid_id = resp.get_json()["booking"]["id"]
        finally:
            self._pause_on()
        resp = self.client.post(f"/api/bookings/{unpaid_id}/vehicle-class",
                                json={"vehicle_class": "suv"})
        self.assertEqual(resp.status_code, 503)
        resp = self.client.post(f"/api/bookings/{unpaid_id}/pay", json={
            "card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Paused Customer"})
        self.assertEqual(resp.status_code, 503)
        resp = self.client.post(f"/api/bookings/{unpaid_id}/pay/confirm",
                                json={"payment_intent_id": "pi_test_123"})
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(booking_id > 0, True)  # fixture built above

    def test_instant_payout_blocked(self):
        _driver, token = self.register_driver()
        resp = self.client.post("/api/drivers/me/instant-payout",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 503)
        self.assertIn("paused", resp.get_json()["error"].lower())

    # -- no money reaches the customer --------------------------------------
    def test_get_booking_has_no_money(self):
        booking_id = self.make_paid_booking()
        resp = self.client.get(f"/api/bookings/{booking_id}")
        self.assertEqual(resp.status_code, 200)
        b = resp.get_json()["booking"]
        for key in ("total", "class_totals", "referral_discount"):
            self.assertNotIn(key, b)
        self.assertIsNone(b.get("invoice"))
        self.assertIn("pickup", b)
        self.assertIn("status", b)

    def test_history_rows_have_no_total(self):
        self.make_paid_booking()
        resp = self.client.get("/api/bookings", query_string={"phone": "+15550009999"})
        self.assertEqual(resp.status_code, 200)
        rows = resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertNotIn("total", rows[0])

    # -- no money reaches the driver ----------------------------------------
    def test_offers_have_no_earnings_or_toll(self):
        _driver, token = self.register_driver()
        booking_id = self.make_paid_booking()
        resp = self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        offers = resp.get_json()
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["booking_id"], booking_id)
        self.assertNotIn("earnings", offers[0])
        self.assertNotIn("toll", offers[0])
        self.assertIn("pickup", offers[0])
        self.assertIn("time", offers[0])

    def test_accept_and_active_trip_have_no_money(self):
        _driver, token = self.register_driver()
        booking_id = self.make_paid_booking()
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        accepted = resp.get_json()["booking"]
        self.assertNotIn("earnings", accepted)
        self.assertNotIn("toll", accepted)
        resp = self.client.get("/api/drivers/me/active-trip",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        trip = resp.get_json()["booking"]
        self.assertNotIn("earnings", trip)
        self.assertNotIn("toll", trip)

    def test_existing_ride_still_completes_without_money(self):
        _driver, token = self.register_driver()
        booking_id = self.make_paid_booking()
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.complete_ride(booking_id, token)
        with app_module.app.app_context():
            booking = app_module.db.session.get(app_module.Booking, booking_id)
            self.assertEqual(booking.status, "completed")

    def test_driver_earnings_has_no_amounts(self):
        _driver, token = self.register_driver()
        booking_id = self.make_paid_booking()
        self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                         headers={"X-Driver-Token": token})
        self.complete_ride(booking_id, token)
        resp = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertNotIn("total_earnings", body)
        self.assertEqual(body["completed_rides"], 1)
        self.assertEqual(len(body["rides"]), 1)
        self.assertNotIn("earnings", body["rides"][0])
        for week in body["weeks"]:
            self.assertNotIn("total_earnings", week)
            self.assertIn("due_date", week)
            self.assertIn("paid", week)

    def test_tax_info_keeps_threshold_drops_earnings(self):
        _driver, token = self.register_driver()
        booking_id = self.make_paid_booking()
        self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                         headers={"X-Driver-Token": token})
        self.complete_ride(booking_id, token)
        resp = self.client.get("/api/drivers/me/tax-info",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertNotIn("earnings_year", body)
        self.assertEqual(body["nec_threshold"], 2000)
        self.assertEqual(body["completed_rides_year"], 1)

    def test_driver_referral_has_no_dollar_figures(self):
        _driver, token = self.register_driver()
        resp = self.client.get("/api/drivers/me/referral",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        for key in ("credit_per_job", "total_earned"):
            self.assertNotIn(key, body)
        for row in body.get("referred_drivers", []):
            self.assertNotIn("earned", row)
        self.assertIn("referral_code", body)

    # -- owner + pricing untouched -------------------------------------------
    def test_owner_dashboard_still_sees_money(self):
        booking_id = self.make_paid_booking()
        self.assertTrue(booking_id > 0)
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.get("/api/owner/summary")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        for key in ("gross", "profit", "driver_owed"):
            self.assertIn(key, body)
        self.assertGreater(body["gross"], 0)

    def test_internal_rates_unchanged(self):
        # Customer totals unchanged; driver pay is the 0-10 slab
        # ($80/$90, owner decision 2026-11-20), not per mile.
        sedan = compute_one_way(D("10"), toll=D("0"), vehicle_class="sedan")
        self.assertEqual(sedan["total"], D("90.00"))
        self.assertEqual(sedan["driver_earnings"], D("80.00"))
        suv = compute_one_way(D("10"), toll=D("0"), vehicle_class="suv")
        self.assertEqual(suv["total"], D("100.00"))
        self.assertEqual(suv["driver_earnings"], D("90.00"))

    # -- static customer/driver surfaces --------------------------------------
    def test_static_pages_show_paused_notice_and_no_price_figures(self):
        for rel in ("static/index.html", "static/customer-app.html",
                    "static/driver.html"):
            html = read(rel)
            if rel == "static/driver.html":
                # Drivers get the amounts-hidden note, not the booking notice.
                self.assertIn("Amounts are hidden while prices are being updated.", html, rel)
            else:
                self.assertIn(PAUSED_MSG, html, rel)
            figures = re.findall(r"\$\d[\d,]*", html)
            if rel == "static/driver.html":
                # Only the IRS 1099-NEC threshold figures ($2,000, $600).
                self.assertEqual(sorted(set(figures)), ["$2,000", "$600"], rel)
            else:
                self.assertEqual(figures, [], rel)
        self.assertNotIn("single total", read("static/index.html"))
        self.assertNotIn("Your total", read("static/index.html"))
        self.assertNotIn("Your total", read("static/customer-app.html"))

    def test_customer_js_has_no_price_answers(self):
        for rel in ("static/js/customer.js", "static/js/customer-app.js"):
            js = read(rel)
            self.assertNotIn("$1/min", js, rel)
            self.assertNotIn("Your total is ready", js, rel)
            self.assertNotIn("class-total-sedan", js, rel)
            self.assertIn(PAUSED_MSG, js, rel)

    def test_driver_js_and_html_have_no_price_figures(self):
        js = read("static/js/driver.js")
        self.assertNotIn("Your earnings", js)
        self.assertNotIn("$5", js)
        html = read("static/driver.html")
        self.assertNotIn("$5", html)
        self.assertNotIn("what each job pays", html)


if __name__ == "__main__":
    unittest.main()
