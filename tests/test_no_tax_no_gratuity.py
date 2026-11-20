"""No tax, no gratuity anywhere on a new booking (owner orders 2026-11-17).

"Tax nikal doh mere ismein se" + "10 percent gratuity bhi nikal doh
mere": every new booking, both classes, all routes, prices as
total = fare + toll ONLY. This module proves the removal across ALL
surfaces a booking touches:

- the "Choose your experience" quote (class_totals),
- the payment charge,
- the stored booking record / customer view,
- the customer invoice (single total, no tax/gratuity keys),
- the owner dashboard per-ride breakdown and summary,
- the extra-distance addition at completion,
- the customer-facing and owner-dashboard static files.

Rides booked before the removal keep their stored tax/gratuity
values; history is not rewritten (that behaviour is covered by the
stored-column reads in app.py, not re-tested here).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from unittest import mock
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-notax-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "notax.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "notax-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the
# other API test modules): sedan total $162.00, SUV total $180.00.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
import pricing  # noqa: E402

D = Decimal
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "No Tax Customer"}


def approx(a, b):
    return a is not None and abs(float(a) - float(b)) < 0.005


# These tests pin the legacy $9/$10 totals as fixtures (the
# no-tax/no-gratuity mechanics are engine-independent); the live
# engine is Blacklane by default since the owner flip (2026-11-20).
@mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"})
class NoTaxNoGratuityCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._phone_seq = 0
        self._driver_seq = 0

    # -- helpers ---------------------------------------------------------
    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "No Tax Customer",
            "phone": f"+1555007{self._phone_seq:04d}",
            "email": "notax@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)

    def register_driver(self, car_model):
        self._driver_seq += 1
        phone = f"+1555008{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"No Tax Driver {self._driver_seq}", "phone": phone,
            "email": f"nt{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
            "plate": f"N{self._driver_seq:05d}",
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

    def drive_to_completion(self, booking_id, token, **complete_kw):
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        for event in ("en_route", "arrived", "start"):
            resp = self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                    json={"event": event},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                json={"event": "complete", **complete_kw},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return resp

    # -- pricing core ------------------------------------------------------
    def test_pricing_core_has_no_tax_no_gratuity(self):
        for miles in ("5.0", "10.0", "17.9", "18.0", "39.9"):
            for cls in ("sedan", "suv"):
                for toll in ("0.00", "7.46", "16.79"):
                    r = pricing.compute_one_way(D(miles), toll=D(toll), vehicle_class=cls)
                    self.assertEqual(r["tax"], D("0.00"), (miles, cls, toll))
                    self.assertEqual(r["gratuity"], D("0.00"), (miles, cls, toll))
                    self.assertEqual(r["total"], r["fare"] + D(toll), (miles, cls, toll))
                    self.assertEqual(r["profit"], r["total"] - r["driver_earnings"])
        extra = pricing.compute_extra_distance(D("5"), "sedan")
        self.assertEqual(extra, {"miles": D("5.0"), "fare": D("45.00"),
                                 "gratuity": D("0.00"), "tax": D("0.00"),
                                 "total": D("45.00"), "driver_addition": D("20.00"),
                                 "vehicle_class": "sedan"})

    # -- quote -> charge -> stored record -> owner breakdown ----------------
    def test_full_booking_flow_sedan_and_suv(self):
        for vehicle_class, total, fare, driver, profit in (
                ("sedan", "162.00", "162.00", "95.00", "67.00"),
                ("suv", "180.00", "180.00", "130.00", "50.00")):
            booking = self.book()
            # Quote: both class totals are fare-only totals.
            self.assertTrue(approx(booking["class_totals"]["sedan"], "162.00"), booking)
            self.assertTrue(approx(booking["class_totals"]["suv"], "180.00"), booking)
            if vehicle_class == "suv":
                resp = self.client.post(f"/api/bookings/{booking['id']}/vehicle-class",
                                        json={"vehicle_class": "suv"})
                self.assertEqual(resp.status_code, 200)
                booking = resp.get_json()["booking"]
            self.assertTrue(approx(booking["total"], total), booking)
            # Charge: the payment amount is the same fare-only total.
            resp = self.pay(booking["id"])
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(approx(resp.get_json()["payment"]["amount"], total),
                            resp.get_json())
            # Owner breakdown: stored tax/gratuity are $0.00, profit is
            # total - driver with no tax subtracted.
            self.owner_login()
            row = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
            self.assertTrue(approx(row["fare"], fare), row)
            self.assertTrue(approx(row["tax"], "0.00"), row)
            self.assertTrue(approx(row["gratuity"], "0.00"), row)
            self.assertTrue(approx(row["customer_total"], total), row)
            self.assertTrue(approx(row["driver_earnings"], driver), row)
            self.assertTrue(approx(row["profit"], profit), row)

    def test_owner_summary_collects_zero_tax(self):
        _, sedan_token = self.register_driver("Cadillac CT6")
        _, suv_token = self.register_driver("Cadillac Escalade")
        sedan = self.book()
        self.assertEqual(self.pay(sedan["id"]).status_code, 200)
        self.drive_to_completion(sedan["id"], sedan_token)
        suv = self.book()
        self.client.post(f"/api/bookings/{suv['id']}/vehicle-class",
                         json={"vehicle_class": "suv"})
        self.assertEqual(self.pay(suv["id"]).status_code, 200)
        self.drive_to_completion(suv["id"], suv_token)
        self.owner_login()
        summary = self.client.get("/api/owner/summary").get_json()
        self.assertTrue(approx(summary["gross"], "342.00"), summary)
        self.assertTrue(approx(summary["tax_collected"], "0.00"), summary)
        self.assertTrue(approx(summary["driver_owed"], "225.00"), summary)
        self.assertTrue(approx(summary["profit"], "117.00"), summary)

    # -- invoice + extra distance -------------------------------------------
    def test_invoice_and_extra_distance_have_no_tax_no_gratuity(self):
        _, token = self.register_driver("Cadillac CT6")
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.drive_to_completion(booking["id"], token, extra_miles=5)
        got = self.client.get(f"/api/bookings/{booking['id']}").get_json()["booking"]
        # Customer view: no invoice while prices are paused.
        self.assertIsNone(got["invoice"])
        # Owner row: extra miles raised fare/driver only; tax/gratuity
        # stayed $0.00; profit $207 - $115 = $92. The owner invoice still
        # carries the single total: fare $162 + extra fare $45 = $207.
        self.owner_login()
        row = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        invoice = row["invoice"]
        self.assertIsNotNone(invoice)
        self.assertTrue(approx(invoice["total"], "207.00"), invoice)
        self.assertTrue(approx(invoice["extra_distance_charge"], "45.00"), invoice)
        self.assertNotIn("tax", invoice)
        self.assertNotIn("gratuity", invoice)
        self.assertTrue(approx(row["fare"], "207.00"), row)
        self.assertTrue(approx(row["tax"], "0.00"), row)
        self.assertTrue(approx(row["gratuity"], "0.00"), row)
        self.assertTrue(approx(row["driver_earnings"], "115.00"), row)
        self.assertTrue(approx(row["profit"], "92.00"), row)

    # -- static files --------------------------------------------------------
    def test_no_tax_or_gratuity_copy_in_customer_and_owner_files(self):
        with open(os.path.join(REPO_DIR, "static", "index.html"),
                  encoding="utf-8") as fh:
            index = fh.read()
        with open(os.path.join(REPO_DIR, "static", "js", "customer.js"),
                  encoding="utf-8") as fh:
            customer_js = fh.read()
        self.assertNotIn("tax included", index)
        self.assertNotIn("tax included", customer_js)
        self.assertNotIn("gratuity", index)
        self.assertNotIn("gratuity", customer_js)
        with open(os.path.join(REPO_DIR, "static", "owner.html"),
                  encoding="utf-8") as fh:
            owner_html = fh.read()
        with open(os.path.join(REPO_DIR, "static", "js", "owner.js"),
                  encoding="utf-8") as fh:
            owner_js = fh.read()
        self.assertNotIn("Tax collected", owner_html)
        self.assertNotIn("sum-tax", owner_html)
        self.assertNotIn("sum-tax", owner_js)
        self.assertNotIn("Gratuity", owner_html)
        self.assertNotIn("gratuity", owner_js)


if __name__ == "__main__":
    unittest.main()
