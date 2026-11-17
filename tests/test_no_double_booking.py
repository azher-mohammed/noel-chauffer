"""Tests for the no-double-booking rule, offline offers, and the chat
box position on the driver trip screen.

Owner decisions 2026-11-16 (voice call):
- A driver who has accepted a job must not get a second job at the
  same time. A new job reaches him only when its pickup falls AFTER
  the accepted ride's time + duration + buffer ends ("time difference
  dekh lena", "duration bhi rehna chahiye"). Applies whether the
  driver is available or offline ("pehla wala option").
- Drivers who are offline still SEE job offers, and may accept one
  if they want the pickup ("jo offline bhi hai unko job dikhna
  chahiye", "agar wo pick up karna chah rahe to kar sakte hain").
- "Chat with your customer" belongs at the BOTTOM of the trip
  screen, under the trip stages and action buttons.

Duration estimate used by the rule: one-way rides take miles / 30 mph
(at least 30 minutes); hourly rides take the booked hours; a 30-minute
buffer follows every ride. The geo stub below makes every one-way ride
18.0 miles, so a one-way busy window is 36 + 30 = 66 minutes.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-nodouble-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "nodouble-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "No Double Customer"}


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class NoDoubleBookingCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, available=False, car_model="Cadillac CT6"):
        """Registers a driver; by default stays OFFLINE (available False),
        so the offline-offers behaviour is what every test exercises
        unless it opts into going available."""
        self._driver_seq += 1
        phone = f"+1555005{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"NoDouble Driver {self._driver_seq}", "phone": phone,
            "email": f"nd{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
            "plate": f"N{self._driver_seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(b"\xff\xd8\xff fake"), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(b"fake png"), "license.png"),
            "doc_tlc_license": (io.BytesIO(b"fake png"), "tlc.png"),
            "doc_fh1": (io.BytesIO(b"fake png"), "fh1.png"),
            "doc_registration": (io.BytesIO(b"fake png"), "reg.png"),
            "doc_inspection": (io.BytesIO(b"fake png"), "insp.png"),
            "doc_vehicle_permit": (io.BytesIO(b"fake png"), "permit.png"),
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        if available:
            self.client.post("/api/drivers/me/availability", json={"available": True},
                             headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "No Double Customer",
            "phone": f"+1555006{self._phone_seq:04d}",
            "email": "nodouble@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        resp = self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return resp

    def offers(self, token):
        return self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token}).get_json()

    def offer_ids(self, token):
        return [o["booking_id"] for o in self.offers(token)]

    def accept(self, token, booking_id):
        return self.client.post(
            f"/api/drivers/me/offers/{booking_id}/accept",
            headers={"X-Driver-Token": token})

    def complete_booking(self, booking_id):
        """Mark a booking completed directly: a finished trip must free
        the driver for jobs at the same time again."""
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking_id)
            row.status = "completed"
            app_module.db.session.commit()

    # -- offline drivers see (and can take) jobs --------------------------
    def test_offline_driver_sees_offers(self):
        _, token = self.register_driver(available=False)
        booking = self.book()
        self.pay(booking["id"])
        self.assertIn(booking["id"], self.offer_ids(token))

    def test_offline_driver_can_accept(self):
        _, token = self.register_driver(available=False)
        booking = self.book()
        self.pay(booking["id"])
        resp = self.accept(token, booking["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    # -- the time-difference rule ------------------------------------------
    def test_overlapping_offer_hidden_after_accept(self):
        # 18 miles -> busy 12:00 + 66 min = until 13:06.
        _, token = self.register_driver()
        first = self.book(time="12:00")
        overlap = self.book(time="12:30")
        later = self.book(time="14:00")
        for b in (first, overlap, later):
            self.pay(b["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        ids = self.offer_ids(token)
        self.assertNotIn(overlap["id"], ids)
        self.assertIn(later["id"], ids)

    def test_overlapping_accept_rejected_even_by_direct_call(self):
        _, token = self.register_driver()
        first = self.book(time="12:00")
        overlap = self.book(time="12:30")
        self.pay(first["id"])
        self.pay(overlap["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        resp = self.accept(token, overlap["id"])
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])

    def test_non_overlapping_accept_allowed(self):
        _, token = self.register_driver()
        first = self.book(time="12:00")
        later = self.book(time="14:00")
        self.pay(first["id"])
        self.pay(later["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        resp = self.accept(token, later["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_hourly_ride_blocks_for_its_hours_plus_buffer(self):
        # 3-hour ride at 10:00 -> busy until 13:30.
        _, token = self.register_driver()
        hourly = self.book(ride_type="hourly", hours=3, time="10:00",
                           dropoff="")
        overlap = self.book(time="13:00")
        later = self.book(time="14:00")
        for b in (hourly, overlap, later):
            self.pay(b["id"])
        self.assertEqual(self.accept(token, hourly["id"]).status_code, 200)
        ids = self.offer_ids(token)
        self.assertNotIn(overlap["id"], ids)
        self.assertIn(later["id"], ids)

    def test_completed_trip_frees_the_driver(self):
        _, token = self.register_driver()
        first = self.book(time="12:00")
        overlap = self.book(time="12:30")
        self.pay(first["id"])
        self.pay(overlap["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        self.assertNotIn(overlap["id"], self.offer_ids(token))
        self.complete_booking(first["id"])
        self.assertIn(overlap["id"], self.offer_ids(token))
        resp = self.accept(token, overlap["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_owner_cannot_assign_overlapping_ride(self):
        driver, token = self.register_driver()
        first = self.book(time="12:00")
        overlap = self.book(time="12:30")
        later = self.book(time="14:00")
        for b in (first, overlap, later):
            self.pay(b["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(f"/api/owner/bookings/{overlap['id']}/assign",
                                json={"driver_id": driver["id"]})
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/owner/bookings/{later['id']}/assign",
                                json={"driver_id": driver["id"]})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_busy_window_maths(self):
        # Unit-level: the window itself, including the JFK-from-far
        # case (a long ride blocks a long window).
        with app_module.app.app_context():
            short = app_module.Booking(date="2030-06-01", time="12:00",
                                       ride_type="one_way")
            short.miles = 18.0
            start, end = app_module._booking_busy_window(short)
            self.assertEqual((end - start).total_seconds(), 66 * 60)
            long_ride = app_module.Booking(date="2030-06-01", time="12:00",
                                           ride_type="one_way")
            long_ride.miles = 60.0
            start, end = app_module._booking_busy_window(long_ride)
            self.assertEqual((end - start).total_seconds(), 150 * 60)
            hourly = app_module.Booking(date="2030-06-01", time="12:00",
                                        ride_type="hourly")
            hourly.hours = 3
            start, end = app_module._booking_busy_window(hourly)
            self.assertEqual((end - start).total_seconds(), 210 * 60)

    # -- frontend: chat at the bottom, offers while offline ----------------
    def test_chat_box_is_at_the_bottom_of_the_trip_screen(self):
        html = read("static/driver.html")
        trip_start = html.index('id="screen-trip"')
        trip_end = html.index('id="screen-earnings"')
        trip = html[trip_start:trip_end]
        chat_at = trip.index('id="trip-chat"')
        self.assertGreater(chat_at, trip.index('id="stage-list"'))
        self.assertGreater(chat_at, trip.index('id="trip-next-btn"'))
        self.assertGreater(chat_at, trip.index('id="trip-cancel-btn"'))

    def test_driver_js_polls_offers_without_availability_gate(self):
        driver_js = read("static/js/driver.js")
        self.assertIn('if (!$("screen-home").classList.contains("hidden") && !state.trip)',
                      driver_js)
        self.assertIn("even while you are offline", driver_js)
        self.assertIn('document.addEventListener("pointerdown", unlockAudio)',
                      driver_js)


if __name__ == "__main__":
    unittest.main()
