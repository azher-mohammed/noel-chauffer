"""Tests for the 2-hour driver cancel lock (owner decision 2026-11-17).

- An accepted ride cannot be cancelled once pickup is within 2 hours
  (including a pickup time already past): the server answers 409 and
  the ride stays with the driver.
- More than 2 hours before pickup, cancelling works exactly as before
  and the job auto re-dispatches to the other drivers.
- Declining an offer BEFORE accepting is untouched by the lock.
- The customer 1-hour cancel/refund rule is untouched (covered by
  TestCancellation in test_pricing.py and the pay-flow tests).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-cancel-lock-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "cancel_lock.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "cancel-lock-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402

CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Cancel Lock Customer"}


def _ny_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.now(timezone.utc)


class DriverCancelLockCase(unittest.TestCase):
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
            "name": f"Lock Driver {self._driver_seq}", "phone": phone,
            "email": f"ld{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"L{self._driver_seq:05d}",
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
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Cancel Lock Customer",
            "phone": f"+1555004{self._phone_seq:04d}",
            "email": "cancellock@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def accept(self, token, booking_id):
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def trip_event(self, token, booking_id, event):
        return self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                json={"event": event},
                                headers={"X-Driver-Token": token})

    def owner_detail(self, booking_id):
        self.client.post("/api/owner/login", json={"pin": "9999"})
        return self.client.get(f"/api/owner/bookings/{booking_id}").get_json()

    def pickup_offset(self, minutes):
        """(date, time) strings for a pickup `minutes` from now (NY)."""
        when = _ny_now() + timedelta(minutes=minutes)
        return when.strftime("%Y-%m-%d"), when.strftime("%H:%M")

    # -- the lock ----------------------------------------------------------
    def test_cancel_allowed_more_than_two_hours_before_pickup(self):
        _, token = self.register_driver()
        booking = self.book()  # 2030 pickup: far more than 2 hours away
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token, booking["id"])
        resp = self.trip_event(token, booking["id"], "cancel")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["status"], "offered")

    def test_cancel_re_dispatched_to_other_drivers(self):
        _, token1 = self.register_driver()
        _, token2 = self.register_driver()
        booking = self.book()  # 2030 pickup: cancel allowed
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token1, booking["id"])
        self.assertEqual(self.trip_event(token1, booking["id"], "cancel").status_code, 200)
        # The job is back on offer for the other driver, but not for the
        # driver who cancelled it.
        offers2 = self.client.get("/api/drivers/me/offers",
                                  headers={"X-Driver-Token": token2}).get_json()
        self.assertIn(booking["id"], [o["booking_id"] for o in offers2])
        offers1 = self.client.get("/api/drivers/me/offers",
                                  headers={"X-Driver-Token": token1}).get_json()
        self.assertNotIn(booking["id"], [o["booking_id"] for o in offers1])

    def test_cancel_blocked_within_two_hours(self):
        _, token = self.register_driver()
        date, time = self.pickup_offset(60)  # 1 hour away: inside the lock
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token, booking["id"])
        resp = self.trip_event(token, booking["id"], "cancel")
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn("2 hours", resp.get_json().get("error", ""))
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["status"], "accepted")

    def test_cancel_blocked_from_en_route_within_two_hours(self):
        _, token = self.register_driver()
        date, time = self.pickup_offset(30)
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token, booking["id"])
        self.assertEqual(self.trip_event(token, booking["id"], "en_route").status_code, 200)
        resp = self.trip_event(token, booking["id"], "cancel")
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["status"], "en_route")

    def test_cancel_blocked_when_pickup_in_the_past(self):
        _, token = self.register_driver()
        date, time = self.pickup_offset(-30)  # pickup 30 minutes ago
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token, booking["id"])
        resp = self.trip_event(token, booking["id"], "cancel")
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["status"], "accepted")

    # -- untouched behaviour ----------------------------------------------
    def test_decline_before_accept_untouched(self):
        # Declining an offer is not a cancel: the lock never applies,
        # even when pickup is minutes away.
        _, token = self.register_driver()
        date, time = self.pickup_offset(15)
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/decline",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["status"], "offered")


if __name__ == "__main__":
    unittest.main()
