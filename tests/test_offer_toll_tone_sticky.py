"""Tests for the driver offer card: toll line, new-offer tone, sticky job.

Owner decisions 2026-11-16 (voice call):
 - While prices are paused (owner decision 2026-11-20) the driver job
  card shows NO toll line and NO earnings: pickup, drop-off and time
  only. The toll math itself is unchanged (see test_pricing_split_matches_card)
  and the owner still sees the toll on the booking detail.
- When a ride/job arrives, the driver hears a tone so he knows a job
  came in. The tone repeats the chime pattern for 30 seconds and
  stops when he accepts/declines, when the offer disappears, or when
  the 30 seconds are up. Offer IDs already alerted to are kept in
  localStorage, so a page refresh never re-rings an old offer — and
  a genuinely new offer rings even on the first poll after a
  refresh (the old "prime on first poll" gate hid the tone).
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
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "offer-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules): sedan total $162.00, driver $72.00 before toll.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
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
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
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
    def test_offers_carry_no_toll_or_earnings(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.set_toll(booking["id"], 16.00)
        offers = self.offers(token)
        self.assertEqual(len(offers), 1)
        self.assertNotIn("toll", offers[0])
        self.assertNotIn("earnings", offers[0])
        self.assertFalse(FORBIDDEN_KEYS & set(offers[0]))
        # The toll is still stored and visible to the owner.
        detail = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertTrue(approx(detail["toll"], "16.00"), detail)

    def test_no_toll_means_no_toll_or_earnings_in_offers(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        offers = self.offers(token)
        self.assertEqual(len(offers), 1)
        self.assertNotIn("toll", offers[0])
        self.assertNotIn("earnings", offers[0])

    def test_accept_and_active_trip_carry_no_toll_or_earnings(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.set_toll(booking["id"], 16.00)
        resp = self.client.post(
            f"/api/drivers/me/offers/{booking['id']}/accept",
            headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        accepted = resp.get_json()["booking"]
        self.assertNotIn("toll", accepted)
        self.assertNotIn("earnings", accepted)
        trip = self.client.get(
            "/api/drivers/me/active-trip",
            headers={"X-Driver-Token": token}).get_json()["booking"]
        self.assertNotIn("toll", trip)
        self.assertNotIn("earnings", trip)
        # The toll is still stored and visible to the owner.
        detail = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertTrue(approx(detail["toll"], "16.00"), detail)

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
    def test_driver_js_renders_no_toll_line_or_earnings(self):
        driver_js = read("static/js/driver.js")
        self.assertNotIn("toll-line", driver_js)
        self.assertNotIn('pickNumber(o, ["toll"])', driver_js)
        self.assertNotIn("toll: pickNumber(b, [\"toll\"])", driver_js)
        self.assertNotIn("if (toll > 0)", driver_js)
        self.assertNotIn("if (tripToll > 0)", driver_js)
        self.assertNotIn("baseEarnings", driver_js)
        self.assertNotIn("tripBase", driver_js)
        self.assertIn("Amounts are hidden while prices are being updated.", driver_js)

    def test_driver_js_rings_for_new_offers_only(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("playOfferTone", driver_js)
        self.assertIn("unlockAudio", driver_js)
        self.assertIn("AudioContext", driver_js)
        self.assertIn("seenOfferIds", driver_js)
        self.assertIn("vibrate", driver_js)
        # The refresh bug: the old "prime on first poll" gate meant an
        # offer already on screen after a refresh never rang. It must
        # stay gone; the persisted seen set replaces it.
        self.assertNotIn("offersPrimed", driver_js)

    def test_driver_js_tone_rings_30_seconds_and_stops(self):
        driver_js = read("static/js/driver.js")
        # A repeating 30-second alert, not one short beep.
        self.assertIn("TONE_DURATION_MS = 30000", driver_js)
        self.assertIn("TONE_REPEAT_MS", driver_js)
        self.assertIn("startOfferTone", driver_js)
        self.assertIn("stopOfferTone", driver_js)
        self.assertIn("toneStopAt", driver_js)
        self.assertIn("toneOfferIds", driver_js)
        self.assertIn("Date.now() + TONE_DURATION_MS", driver_js)
        # The ring repeats on an interval and ends on its own.
        self.assertIn("setInterval(function ()", driver_js)
        self.assertIn("if (Date.now() >= state.toneStopAt) { stopOfferTone(); return; }", driver_js)
        # Stops the moment the driver answers: accept and decline
        # alike, without waiting for the next poll.
        start = driver_js.index("function respondToOffer")
        end = driver_js.index("/* ---------- Trip screen", start)
        self.assertIn("stopOfferTone();", driver_js[start:end])
        # Stops when every offer being rung for has disappeared.
        self.assertIn("if (!anyLeft) stopOfferTone();", driver_js)
        # A second new offer while ringing extends the window instead
        # of stacking a second interval.
        self.assertIn("if (state.toneTimer) return;", driver_js)

    def test_driver_js_persists_seen_offers_across_refresh(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("SEEN_OFFERS_KEY", driver_js)
        self.assertIn("loadSeenOfferIds", driver_js)
        self.assertIn("saveSeenOfferIds", driver_js)
        self.assertIn("clearSeenOfferIds", driver_js)
        self.assertIn("localStorage.getItem(SEEN_OFFERS_KEY)", driver_js)
        self.assertIn("localStorage.setItem(SEEN_OFFERS_KEY", driver_js)
        # Loaded before the first poll, so a genuinely new offer rings
        # on the first poll after a refresh.
        self.assertIn("loadSeenOfferIds();", driver_js)
        self.assertIn("startOfferTone(freshIds)", driver_js)
        # The stored set is bounded so it cannot grow forever.
        self.assertIn("MAX_SEEN_OFFERS", driver_js)
        # Signing out clears the stored set: a different driver on the
        # same device must hear fresh offers.
        start = driver_js.index("reset-driver-btn")
        self.assertIn("clearSeenOfferIds();", driver_js[start:start + 400])

    def test_driver_js_keeps_cards_put_while_unchanged(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("lastOffersSig", driver_js)
        self.assertIn("if (sig === state.lastOffersSig) return;", driver_js)

    def test_driver_css_styles_toll_line(self):
        css = read("static/css/driver.css")
        self.assertIn(".toll-line", css)


if __name__ == "__main__":
    unittest.main()
