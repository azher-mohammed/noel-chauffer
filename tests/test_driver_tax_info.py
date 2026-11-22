"""Tests for the driver TAX info page — display only.

Owner decision (2026-11-20, voice call): "dikhane wala" — an info page
like Uber's driver-app tax page, NOT a fillable form. The page shows:

- 1099 tax forms available by January 31, 2027
- State filing deadline April 15, 2027
- 1099-K and/or 1099-NEC, each explained in one plain line
- IRS 1099-NEC threshold $2,000 for tax year 2026 (raised from $600)
- The logged-in driver's own total earnings for 2026 (read-only)
- The note that the actual 1099 is issued by Noel/Siahsolutions Inc
  and the app files nothing

Rules enforced here: NO fillable fields, NO SSN/TIN collection, NO
document upload, NO IRS filing. The driver response carries earnings
amounts only — never miles, fares, or totals.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-tax-info-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "tax-info-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles -> driver $95.00 (10-20 slab).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

D = Decimal
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}


def _utc(y, mo, d, h=15, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class TaxInfoApiCase(unittest.TestCase):
    """In-process API tests with a fresh DB per test."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0

    # -- helpers ---------------------------------------------------------
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

    def signin(self, email, phone):
        """Compulsory customer sign-in (owner 2026-11-22): payment
        needs a sign-in with the booking's email."""
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def complete_ride(self, token):
        payload = {
            "customer_name": "Tax Customer", "phone": "+15550009999",
            "email": "cust@test.com", "pickup": "JFK Airport",
            "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking_id = resp.get_json()["booking"]["id"]
        # Payment comes BEFORE dispatch: pay first, then the driver
        # accepts, then the trip runs stage by stage.
        self.signin(payload["email"], payload["phone"])
        resp = self.client.post(f"/api/bookings/{booking_id}/pay", json={
            "card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Tax Customer"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        for event in ("en_route", "arrived", "start", "complete"):
            resp = self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                    json={"event": event},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")
        return booking_id

    def backdate_completion(self, booking_id, completed_at):
        with app_module.app.app_context():
            booking = app_module.db.session.get(app_module.Booking, booking_id)
            booking.completed_at = completed_at
            app_module.db.session.commit()

    def tax_info(self, token=None):
        headers = {"X-Driver-Token": token} if token else {}
        return self.client.get("/api/drivers/me/tax-info", headers=headers)

    # -- auth ------------------------------------------------------------
    def test_tax_info_requires_driver_token(self):
        resp = self.tax_info()
        self.assertEqual(resp.status_code, 401)
        resp = self.tax_info(token="bad-token")
        self.assertEqual(resp.status_code, 401)

    # -- static facts ------------------------------------------------------
    def test_tax_info_static_facts_for_new_driver(self):
        _driver, token = self.register_driver()
        resp = self.tax_info(token)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["tax_year"], 2026)
        self.assertEqual(body["forms_available_by"], "2027-01-31")
        self.assertEqual(body["state_filing_deadline"], "2027-04-15")
        self.assertEqual(D(str(body["nec_threshold"])), D("2000.00"))
        codes = [f["code"] for f in body["forms"]]
        self.assertEqual(codes, ["1099-NEC", "1099-K"])
        nec = body["forms"][0]
        self.assertIn("independent contractor", nec["description"])
        self.assertIn("$2,000", nec["description"])
        self.assertIn("card or payment network", body["forms"][1]["description"])
        self.assertIn("Siahsolutions Inc", body["issuer"])
        self.assertIn("does not file", body["filing_note"])
        self.assertNotIn("earnings_year", body)
        self.assertEqual(body["completed_rides_year"], 0)

    # -- year earnings -------------------------------------------------------
    def test_tax_info_counts_only_2026_completed_rides(self):
        _driver, token = self.register_driver()
        b1 = self.complete_ride(token)   # one-way: driver $95.00 (10-20 slab)
        b2 = self.complete_ride(token)   # one-way: driver $95.00 (10-20 slab)
        b3 = self.complete_ride(token)   # one-way: driver $95.00 (10-20 slab)
        self.backdate_completion(b1, _utc(2026, 11, 20))
        self.backdate_completion(b2, _utc(2026, 12, 31))
        self.backdate_completion(b3, _utc(2025, 12, 20))  # previous year: excluded
        body = self.tax_info(token).get_json()
        self.assertNotIn("earnings_year", body)
        self.assertEqual(body["completed_rides_year"], 2)

    def test_tax_info_excludes_other_driver_and_unfinished_rides(self):
        _driver, token = self.register_driver()
        _other, other_token = self.register_driver()
        mine = self.complete_ride(token)
        theirs = self.complete_ride(other_token)
        self.backdate_completion(mine, _utc(2026, 11, 20))
        self.backdate_completion(theirs, _utc(2026, 11, 21))
        # An offered-but-never-completed booking for me.
        payload = {
            "customer_name": "Tax Customer", "phone": "+15550009999",
            "email": "cust@test.com", "pickup": "JFK Airport",
            "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201)
        body = self.tax_info(token).get_json()
        self.assertNotIn("earnings_year", body)
        self.assertEqual(body["completed_rides_year"], 1)

    def test_tax_info_excludes_refunded_rides(self):
        _driver, token = self.register_driver()
        b1 = self.complete_ride(token)
        self.backdate_completion(b1, _utc(2026, 11, 20))
        with app_module.app.app_context():
            payment = app_module.Payment.query.filter_by(booking_id=b1).first()
            self.assertIsNotNone(payment)
            payment.status = "refunded"
            app_module.db.session.commit()
        body = self.tax_info(token).get_json()
        self.assertNotIn("earnings_year", body)
        self.assertEqual(body["completed_rides_year"], 0)

    # -- driver privacy ------------------------------------------------------
    def test_tax_info_response_has_no_fare_fields(self):
        _driver, token = self.register_driver()
        self.complete_ride(token)
        resp = self.tax_info(token)
        body = resp.get_json()
        self.assertFalse(set(body) & FORBIDDEN_KEYS, str(body))
        for form in body["forms"]:
            self.assertFalse(set(form) & FORBIDDEN_KEYS, str(form))
        # The customer fare total must never appear in the driver response.
        self.assertNotIn("162.00", resp.get_data(as_text=True))


class TaxInfoPageCase(unittest.TestCase):
    """The driver app page: Tax info screen exists, display only."""

    def test_driver_page_has_tax_info_screen_with_key_facts(self):
        html = read("static/driver.html")
        self.assertIn('id="screen-tax"', html)
        self.assertIn("Tax info", html)
        self.assertIn("January 31, 2027", html)
        self.assertIn("April 15, 2027", html)
        self.assertIn("$2,000", html)
        self.assertIn("1099-NEC", html)
        self.assertIn("1099-K", html)
        self.assertIn("Siahsolutions Inc", html)
        self.assertIn('data-screen="tax"', html)
        self.assertIn("tax-earnings-2026", html)

    def test_tax_screen_has_no_fillable_fields(self):
        html = read("static/driver.html")
        match = re.search(r'<section[^>]*id="screen-tax"[^>]*>(.*?)</section>',
                          html, re.DOTALL)
        self.assertIsNotNone(match, "screen-tax section not found")
        section = match.group(1)
        for tag in ("<input", "<textarea", "<select", "<form", "ssn", "SSN",
                    "type=\"file\"", "upload"):
            self.assertNotIn(tag, section, f"tax screen must not contain {tag!r}")

    def test_driver_js_loads_tax_info(self):
        js = read("static/js/driver.js")
        self.assertIn('"tax"', js)
        self.assertIn("/api/drivers/me/tax-info", js)
        self.assertIn("loadTaxInfo", js)


if __name__ == "__main__":
    unittest.main()
