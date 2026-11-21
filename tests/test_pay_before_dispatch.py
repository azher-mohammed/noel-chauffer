"""Tests for the reversed payment flow (decided 2026-11-16, "exactly").

NEW RULE: the customer sees the single total right after the booking
form, pays by card, and ONLY then is the booking sent to drivers.
The old rule (total + payment only after a driver accepts) is dead.

- Create returns the single total immediately, status awaiting_payment.
- Unpaid bookings never appear in driver offers and cannot be accepted.
- Payment moves the booking to offered (sent to drivers); a second
  payment is rejected.
- Driver accept -> trip stages run with no second payment step.
- Free cancellation (>1h) refunds the upfront payment in full; late
  cancellation / no-show keeps the full price.
- Hourly rides follow the same flow; referral codes give 5% off a new
  customer's first one-way booking (owner decision 2026-11-18).
- Driver payloads never carry miles, fare, tax, or total anywhere.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-payflow-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "payflow.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "payflow-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules): total $162.00, driver $95.00 (10-20 slab), referral $162.00.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Pay Flow Customer"}


def approx(a, b):
    return a is not None and abs(float(a) - float(b)) < 0.005


# These tests pin the legacy $9/$10 totals as fixtures (the
# pay-before-dispatch mechanics are engine-independent); the live
# engine is Blacklane by default since the owner flip (2026-11-20).
@mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"})
class PayBeforeDispatchCase(unittest.TestCase):
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
        phone = f"+1555001{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Pay Driver {self._driver_seq}", "phone": phone,
            "email": f"pd{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"P{self._driver_seq:05d}",
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
            "customer_name": "Pay Flow Customer",
            "phone": f"+1555002{self._phone_seq:04d}",
            "email": "payflow@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id, card=None):
        return self.client.post(f"/api/bookings/{booking_id}/pay",
                                json=card or dict(CARD))

    def get_booking(self, booking_id):
        return self.client.get(f"/api/bookings/{booking_id}").get_json()["booking"]

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)

    # -- total before any driver accept ----------------------------------
    def test_create_returns_total_and_awaiting_payment(self):
        booking = self.book()
        self.assertEqual(booking["status"], "awaiting_payment")
        self.assertTrue(approx(booking["total"], "162.00"), booking)

    def test_total_hidden_before_any_driver_accept(self):
        booking = self.book()
        got = self.get_booking(booking["id"])
        self.assertNotIn("total", got)
        self.assertNotIn("class_totals", got)
        self.assertIsNone(got["driver"])
        self.assertIs(got["tracking"]["visible"], False)

    # -- unpaid bookings never reach drivers ------------------------------
    def test_unpaid_booking_never_visible_to_drivers(self):
        _, token = self.register_driver()
        booking = self.book()
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(offers, [])
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])

    # -- payment -----------------------------------------------------------
    def test_pay_validation(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay", json={
            "card_number": "4242424242424242"})
        self.assertEqual(resp.status_code, 400)
        resp = self.pay(booking["id"], card={**CARD, "card_number": "123"})
        self.assertEqual(resp.status_code, 400)
        resp = self.pay(999999)
        self.assertEqual(resp.status_code, 404)

    def test_pay_dispatches_booking(self):
        _, token = self.register_driver()
        booking = self.book()
        resp = self.pay(booking["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        payment = resp.get_json()["payment"]
        self.assertEqual(payment["status"], "succeeded")
        self.assertIs(payment["test"], True)
        self.assertEqual(payment["last4"], "4242")
        self.assertTrue(approx(payment["amount"], "162.00"))
        self.assertEqual(resp.get_json()["booking"]["status"], "offered")
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["booking_id"], booking["id"])
        self.assertNotIn("earnings", offers[0])
        self.assertNotIn("toll", offers[0])
        self.assertFalse(FORBIDDEN_KEYS & set(offers[0]))

    def test_double_pay_rejected(self):
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.pay(booking["id"])
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])

    def test_pay_on_cancelled_booking_rejected(self):
        booking = self.book()
        with app_module.app.app_context():
            phone = app_module.db.session.get(app_module.Booking, booking["id"]).phone
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": phone})
        self.assertEqual(resp.status_code, 200)
        resp = self.pay(booking["id"])
        self.assertEqual(resp.status_code, 409)

    # -- trip runs with no second payment step ------------------------------
    def test_accept_then_trip_without_second_payment(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        got = self.get_booking(booking["id"])
        self.assertEqual(got["driver"]["name"], "Pay Driver 1")
        self.assertNotIn("total", got)
        for event in ("en_route", "arrived", "start", "complete"):
            resp = self.client.post(f"/api/drivers/me/trip/{booking['id']}/event",
                                    json={"event": event, "waiting_minutes": 75}
                                    if event == "complete" else {"event": event},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")
        got = self.get_booking(booking["id"])
        self.assertEqual(got["status"], "completed")
        self.assertIsNone(got["invoice"])

    def test_driver_cancel_keeps_payment_and_redispatches(self):
        _, token1 = self.register_driver()
        _, token2 = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                         headers={"X-Driver-Token": token1})
        resp = self.client.post(f"/api/drivers/me/trip/{booking['id']}/event",
                                json={"event": "cancel"},
                                headers={"X-Driver-Token": token1})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["booking"]["status"], "offered")
        # Customer sees no total; driver details are gone again.
        got = self.get_booking(booking["id"])
        self.assertIsNone(got["driver"])
        self.assertNotIn("total", got)
        # Payment kept; the other driver sees the offer again.
        self.owner_login()
        detail = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertEqual(detail["payments"][0]["status"], "succeeded")
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token2}).get_json()
        self.assertEqual([o["booking_id"] for o in offers], [booking["id"]])
        offers1 = self.client.get("/api/drivers/me/offers",
                                  headers={"X-Driver-Token": token1}).get_json()
        self.assertEqual(offers1, [])

    # -- cancellation / refund ----------------------------------------------
    def test_free_cancel_refunds_upfront_payment(self):
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        with app_module.app.app_context():
            phone = app_module.db.session.get(app_module.Booking, booking["id"]).phone
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": phone})
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.get_json()["refund"], True)
        self.assertIs(resp.get_json()["charge_kept"], False)
        self.owner_login()
        detail = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertEqual(detail["payments"][0]["status"], "refunded")

    def test_cancel_unpaid_booking_no_refund_no_charge(self):
        booking = self.book()
        with app_module.app.app_context():
            phone = app_module.db.session.get(app_module.Booking, booking["id"]).phone
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": phone})
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.get_json()["refund"], False)
        self.assertIs(resp.get_json()["charge_kept"], False)

    def test_late_cancel_keeps_full_price(self):
        try:
            from zoneinfo import ZoneInfo
            soon = datetime.now(ZoneInfo("America/New_York")) + timedelta(minutes=30)
        except Exception:
            soon = datetime.now(timezone.utc) + timedelta(minutes=30)
        booking = self.book(date=soon.strftime("%Y-%m-%d"), time=soon.strftime("%H:%M"))
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        with app_module.app.app_context():
            phone = app_module.db.session.get(app_module.Booking, booking["id"]).phone
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": phone})
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.get_json()["refund"], False)
        self.assertIs(resp.get_json()["charge_kept"], True)
        self.owner_login()
        detail = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertEqual(detail["payments"][0]["status"], "succeeded")

    def test_no_show_keeps_full_price(self):
        _, token = self.register_driver()
        # Pickup 2 hours ago: the full 60-minute airport wait has elapsed,
        # so the no-show time gate (owner decision 2026-11-16) allows it.
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                         headers={"X-Driver-Token": token})
        self.move_pickup(booking["id"], 120)
        for event in ("en_route", "arrived", "no_show"):
            resp = self.client.post(f"/api/drivers/me/trip/{booking['id']}/event",
                                    json={"event": event},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")
        self.owner_login()
        detail = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertEqual(detail["status"], "no_show")
        self.assertEqual(detail["payments"][0]["status"], "succeeded")
        summary = self.client.get("/api/owner/summary").get_json()
        self.assertTrue(approx(summary["gross"], "162.00"), summary)

    # -- no-show time gate (owner decision 2026-11-16) -----------------------
    def past_pickup(self, minutes_ago):
        try:
            from zoneinfo import ZoneInfo
            past = datetime.now(ZoneInfo("America/New_York")) - timedelta(minutes=minutes_ago)
        except Exception:
            past = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        return past.strftime("%Y-%m-%d"), past.strftime("%H:%M")

    def move_pickup(self, booking_id, minutes_ago):
        """Move a booking's pickup to `minutes_ago` in the past, in
        the DB. The API refuses past pickups (owner decision
        2026-11-20), so tests that need a past pickup book in the
        future and move it back here."""
        date, time = self.past_pickup(minutes_ago)
        with app_module.app.app_context():
            b = app_module.db.session.get(app_module.Booking, booking_id)
            b.date = date
            b.time = time
            app_module.db.session.commit()

    def trip_event(self, token, booking_id, event):
        return self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                json={"event": event},
                                headers={"X-Driver-Token": token})

    def drive_to_arrived(self, token, booking_id):
        for event in ("en_route", "arrived"):
            resp = self.trip_event(token, booking_id, event)
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")

    def test_no_show_rejected_before_waiting_time_ends(self):
        _, token = self.register_driver()
        booking = self.book()  # 2030 pickup: the wait has not even begun
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                         headers={"X-Driver-Token": token})
        self.drive_to_arrived(token, booking["id"])
        resp = self.trip_event(token, booking["id"], "no_show")
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.owner_login()
        detail = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertEqual(detail["status"], "arrived")
        self.assertEqual(detail["payments"][0]["status"], "succeeded")

    def test_no_show_airport_requires_full_60_minutes(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                         headers={"X-Driver-Token": token})
        self.drive_to_arrived(token, booking["id"])
        self.move_pickup(booking["id"], 30)  # JFK: only 30 of 60 minutes elapsed
        resp = self.trip_event(token, booking["id"], "no_show")
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])

    def test_no_show_regular_pickup_allowed_after_15_minutes(self):
        _, token = self.register_driver()
        booking = self.book(pickup="123 Main Street")
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                         headers={"X-Driver-Token": token})
        self.drive_to_arrived(token, booking["id"])
        self.move_pickup(booking["id"], 30)  # regular pickup: 15-minute wait elapsed
        resp = self.trip_event(token, booking["id"], "no_show")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.owner_login()
        detail = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertEqual(detail["status"], "no_show")

    # -- hourly + referral follow the same flow --------------------------------
    def test_hourly_same_flow(self):
        _, token = self.register_driver()
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Hourly", "phone": "+15550009991",
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": "2030-06-04", "time": "14:00",
            "ride_type": "hourly", "hours": 3, "vehicle_class": "sedan"})
        self.assertEqual(resp.status_code, 201)
        booking = resp.get_json()["booking"]
        self.assertEqual(booking["status"], "awaiting_payment")
        self.assertTrue(approx(booking["total"], "327.48"), booking)
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(offers, [])
        resp = self.pay(booking["id"])
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(approx(resp.get_json()["payment"]["amount"], "327.48"))
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(len(offers), 1)
        self.assertNotIn("earnings", offers[0])
        self.assertNotIn("toll", offers[0])
        self.assertFalse(FORBIDDEN_KEYS & set(offers[0]))
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        for event in ("en_route", "arrived", "start", "complete"):
            resp = self.client.post(f"/api/drivers/me/trip/{booking['id']}/event",
                                    json={"event": event},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200)
        earn = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(earn["completed_rides"], 1)
        self.assertNotIn("total_earnings", earn)

    def test_referral_total_shown_and_paid(self):
        first = self.book()
        code = first["referral_code"]
        self.assertTrue(code)
        referred = self.book(referral_code=code)
        self.assertTrue(approx(referred["total"], "153.90"), referred)
        resp = self.pay(referred["id"])
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(approx(resp.get_json()["payment"]["amount"], "153.90"))

    # -- driver visibility boundary ---------------------------------------------
    def test_driver_payloads_never_carry_fare_or_miles(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertFalse(FORBIDDEN_KEYS & set(offers[0]))
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                                headers={"X-Driver-Token": token})
        trip = resp.get_json()["booking"]
        self.assertFalse(FORBIDDEN_KEYS & set(trip))
        self.assertNotIn("earnings", trip)
        self.assertNotIn("toll", trip)
        active = self.client.get("/api/drivers/me/active-trip",
                                 headers={"X-Driver-Token": token}).get_json()["booking"]
        self.assertFalse(FORBIDDEN_KEYS & set(active))

    def test_history_shows_no_total_for_unpaid_and_paid(self):
        unpaid = self.book()
        paid = self.book()
        self.assertEqual(self.pay(paid["id"]).status_code, 200)
        with app_module.app.app_context():
            phone_u = app_module.db.session.get(app_module.Booking, unpaid["id"]).phone
            phone_p = app_module.db.session.get(app_module.Booking, paid["id"]).phone
        hist_u = self.client.get("/api/bookings", query_string={"phone": phone_u}).get_json()
        self.assertEqual(len(hist_u), 1)
        self.assertNotIn("total", hist_u[0])
        hist_p = self.client.get("/api/bookings", query_string={"phone": phone_p}).get_json()
        self.assertEqual(len(hist_p), 1)
        self.assertNotIn("total", hist_p[0])

    # -- static copy matches the new flow ----------------------------------------
    def test_static_copy_matches_new_flow(self):
        with open(os.path.join(REPO_DIR, "static", "index.html"),
                  encoding="utf-8") as fh:
            index = fh.read()
        # The pay-before-dispatch copy moved with the Cancellation &
        # waiting section to its own page in the 2026-11-21 homepage
        # split (the "Payment" bullet list).
        with open(os.path.join(REPO_DIR, "static",
                               "cancellation-and-waiting.html"),
                  encoding="utf-8") as fh:
            policy = fh.read()
        with open(os.path.join(REPO_DIR, "static", "js", "customer.js"),
                  encoding="utf-8") as fh:
            customer_js = fh.read()
        for old in ("shown after your chauffeur accepts",
                    "after a chauffeur accepts",
                    "only when the API returns a number, after a chauffeur"):
            self.assertNotIn(old, index + customer_js)
        self.assertIn("You pay by card on this page, right after you book.", policy)
        self.assertIn("awaiting_payment", customer_js)
        self.assertNotIn('st === "paid"', customer_js)
        # Options page: "View options" opens the class page; the old
        # "Book a ride" label is gone everywhere user-visible.
        self.assertIn('id="book-submit">View options<', index)
        self.assertIn("Choose your experience", index)
        self.assertIn("Business Class", index)
        self.assertIn("Business SUV", index)
        self.assertNotIn("Book a ride", index)
        self.assertNotIn("Book a ride", customer_js)


class NoShowButtonGateCase(unittest.TestCase):
    """The driver app hides the no-show button until the full wait ends."""

    def test_driver_js_gates_noshow_button(self):
        with open(os.path.join(REPO_DIR, "static", "js", "driver.js"),
                  encoding="utf-8") as fh:
            driver_js = fh.read()
        self.assertIn("refreshNoShowButton", driver_js)
        self.assertIn("free_waiting_minutes", driver_js)
        self.assertIn("noShowTimer", driver_js)
        self.assertIn("30000", driver_js)

    def test_noshow_button_starts_hidden(self):
        with open(os.path.join(REPO_DIR, "static", "driver.html"),
                  encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn('class="btn-ghost hidden" type="button" id="trip-noshow-btn"', html)


if __name__ == "__main__":
    unittest.main()
