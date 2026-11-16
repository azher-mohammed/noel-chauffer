"""Tests for the driver offer card: toll line, new-offer tone, sticky job.

Owner decisions 2026-11-16 (voice call):
- The toll shows as a SEPARATE line on the driver job card, under the
  earnings, and only when a toll applies ("agar toll laga to").
  Earnings from the API include the toll; the card shows the driving
  pay on its own and the toll on its own line.
- When a ride/job arrives, the driver hears a tone so he knows a job
  came in. The tone rings once per new offer.
- The job must NOT disappear until the driver accepts it: no expiry,
  and the card does not rebuild while the driver is looking at it.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-offer-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "offer.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "offer-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules): sedan total $235.37, driver $72.00 before toll.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import pricing  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Offer Card Customer"}


def approx(a, b):
    return a is not None and abs(float(a) - float(b)) < 0.005


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class OfferTollToneCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self):
        self._driver_seq += 1
        phone = f"+1555003{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Offer Driver {self._driver_seq}", "phone": phone,
            "email": f"od{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"O{self._driver_seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(b"\xff\xd8\xff fake"), "photo.jpg"),
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Offer Card Customer",
            "phone": f"+1555004{self._phone_seq:04d}",
            "email": "offer@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def set_toll(self, booking_id, toll):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(f"/api/owner/bookings/{booking_id}/toll",
                                json={"toll": toll})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def offers(self, token):
        return self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token}).get_json()

    # -- toll in driver payloads ------------------------------------------
    def test_offers_carry_toll_and_earnings_include_it(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.set_toll(booking["id"], 16.00)
        offers = self.offers(token)
        self.assertEqual(len(offers), 1)
        self.assertTrue(approx(offers[0]["toll"], "16.00"), offers[0])
        # 18 miles x $4 sedan rate = $72 driving pay + $16 toll.
        self.assertTrue(approx(offers[0]["earnings"], "88.00"), offers[0])
        self.assertFalse(FORBIDDEN_KEYS & set(offers[0]))

    def test_no_toll_means_zero_toll_in_offers(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        offers = self.offers(token)
        self.assertEqual(len(offers), 1)
        self.assertTrue(approx(offers[0]["toll"], "0.00"), offers[0])
        self.assertTrue(approx(offers[0]["earnings"], "72.00"), offers[0])

    def test_toll_in_accept_and_active_trip_payloads(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.set_toll(booking["id"], 16.00)
        resp = self.client.post(
            f"/api/drivers/me/offers/{booking['id']}/accept",
            headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        accepted = resp.get_json()["booking"]
        self.assertTrue(approx(accepted["toll"], "16.00"), accepted)
        trip = self.client.get(
            "/api/drivers/me/active-trip",
            headers={"X-Driver-Token": token}).get_json()["booking"]
        self.assertTrue(approx(trip["toll"], "16.00"), trip)
        self.assertTrue(approx(trip["earnings"], "88.00"), trip)

    def test_pricing_split_matches_card(self):
        # The example card: 20-mile SUV, $140 driving pay + $16 toll.
        result = pricing.compute_one_way(20, toll=16, vehicle_class="suv")
        self.assertEqual(float(result["driver_earnings"]), 156.00)
        self.assertEqual(float(result["driver_earnings"] - result["toll"]), 140.00)

    # -- the job stays until the driver accepts -----------------------------
    def test_old_offer_still_listed_until_accepted(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        # Age the booking 3 hours: no expiry may hide it.
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            row.created_at = datetime.now(timezone.utc) - timedelta(hours=3)
            app_module.db.session.commit()
        offers = self.offers(token)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["booking_id"], booking["id"])
        # Accepting removes it from the offers list.
        resp = self.client.post(
            f"/api/drivers/me/offers/{booking['id']}/accept",
            headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.offers(token), [])

    # -- frontend rendering ---------------------------------------------------
    def test_driver_js_renders_toll_line_only_when_toll_applies(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("toll-line", driver_js)
        self.assertIn('pickNumber(o, ["toll"])', driver_js)
        self.assertIn("toll: pickNumber(b, [\"toll\"])", driver_js)
        self.assertIn("if (toll > 0)", driver_js)
        self.assertIn("if (tripToll > 0)", driver_js)
        self.assertIn("baseEarnings", driver_js)
        self.assertIn("tripBase", driver_js)

    def test_driver_js_rings_for_new_offers_only(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("playOfferTone", driver_js)
        self.assertIn("unlockAudio", driver_js)
        self.assertIn("AudioContext", driver_js)
        self.assertIn("seenOfferIds", driver_js)
        self.assertIn("offersPrimed", driver_js)
        self.assertIn("vibrate", driver_js)

    def test_driver_js_keeps_cards_put_while_unchanged(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("lastOffersSig", driver_js)
        self.assertIn("if (sig === state.lastOffersSig) return;", driver_js)

    def test_driver_css_styles_toll_line(self):
        css = read("static/css/driver.css")
        self.assertIn(".toll-line", css)


if __name__ == "__main__":
    unittest.main()
