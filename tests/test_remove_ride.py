"""Tests for the owner-only removal of ONE ride (owner decision
2026-11-19, voice call): the owner can remove an individual booking
from the dashboard or the owner app.

POST /api/owner/bookings/<id>/remove (owner session + PIN
re-confirmation in the JSON body) removes that one booking plus its
chat messages, booking events, emergency cancel records, driver
referral credits, payments, decline exclusions and outbox messages.
Referral codes stay valid (their link to the deleted booking is
detached, not deleted) and drivers with their documents are
untouched — the other rides stay exactly as they were.

The dashboard shows a "Remove" button on each ride row and the owner
app shows one on each ride card; both open a PIN prompt first and
the PIN is checked server-side. A missing or wrong PIN deletes
nothing.

Run:  python -m unittest discover -s tests -v
"""


import io
import os
import re
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-clear-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "clear.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "clear-secret-key"
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
        "card_cvc": "123", "card_name": "Clear Rides Customer"}
PHOTO_BYTES = photo_factory.VALID_PROFILE_PHOTO


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def read_app(rel):
    """Read a file from the owner app repo (separate checkout)."""
    with open(os.path.join(os.path.expanduser(
            "~/workspace/noel-chauffer-owner-app"), rel),
            encoding="utf-8") as fh:
        return fh.read()


class ClearRidesCase(unittest.TestCase):
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
        phone = f"+1555007{self._driver_seq:04d}"
        # Remember the DMV bytes: the clear test asserts the kept
        # document still holds exactly what was uploaded.
        self._dmv_bytes = photo_factory.doc_photo()
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Clear Driver {self._driver_seq}", "phone": phone,
            "email": f"cd{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"C{self._driver_seq:05d}",
            "state": "New York", "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_tlc_license": "2030-01-01",
            "expiry_fh1_insurance": "2030-01-01",
            "expiry_registration": "2030-01-01",
            "expiry_inspection": "2030-01-01",
            "expiry_vehicle_permit": "2030-01-01",
            "expiry_vehicle_registration": "2030-01-01",
            "expiry_insurance_card": "2030-01-01",
            "profile_photo": (io.BytesIO(PHOTO_BYTES), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(self._dmv_bytes), "dmv.jpg"),
            "doc_tlc_license": (io.BytesIO(photo_factory.doc_photo()), "tlc.jpg"),
            "doc_fh1": (io.BytesIO(photo_factory.doc_photo()), "fh1.jpg"),
            "doc_registration": (io.BytesIO(photo_factory.doc_photo()), "reg.jpg"),
            "doc_inspection": (io.BytesIO(photo_factory.doc_photo()), "insp.jpg"),
            "doc_vehicle_permit": (io.BytesIO(photo_factory.doc_photo()), "permit.jpg"),
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def signin(self, email, phone):
        """Compulsory customer sign-in (owner 2026-11-22): payment
        needs a sign-in with the booking's email. Signs in
        once per email per test — the session persists for later
        bookings and payments in the same test."""
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Clear Rides Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "clear@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking = resp.get_json()["booking"]
        booking["phone"] = payload["phone"]
        if "@" in (payload.get("email") or "") and payload.get("phone"):
            self.signin(payload["email"], payload["phone"])
        return booking

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def owner_login(self, client=None):
        resp = (client or self.client).post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def counts(self):
        db = app_module.db
        with app_module.app.app_context():
            return {
                "bookings": db.session.query(app_module.Booking).count(),
                "chat_messages": db.session.query(app_module.ChatMessage).count(),
                "booking_events": db.session.query(app_module.BookingEvent).count(),
                "payments": db.session.query(app_module.Payment).count(),
                "booking_exclusions": db.session.query(app_module.BookingExclusion).count(),
                "outbox_messages": db.session.query(app_module.OutboxMessage).count(),
                "referral_codes": db.session.query(app_module.ReferralCode).count(),
                "drivers": db.session.query(app_module.Driver).count(),
                "driver_documents": db.session.query(app_module.DriverDocument).count(),
            }

    def seed_rides(self):
        """One driver, two paid bookings: one accepted with a chat
        exchange, one declined (exclusion row). Returns (driver, token)."""
        driver, token = self.register_driver()
        first = self.book()
        self.assertEqual(self.pay(first["id"]).status_code, 200)
        resp = self.client.post(
            f"/api/drivers/me/offers/{first['id']}/accept", json={},
            headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/drivers/me/trip/{first['id']}/messages",
                                json={"text": "On my way."},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/bookings/{first['id']}/messages",
                                json={"phone": first["phone"], "text": "At arrivals."})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        second = self.book(time="15:00")
        self.assertEqual(self.pay(second["id"]).status_code, 200)
        resp = self.client.post(
            f"/api/drivers/me/offers/{second['id']}/decline", json={},
            headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return driver, token, first, second

    # -- auth ---------------------------------------------------------------
    def test_remove_requires_owner_login(self):
        resp = self.client.post("/api/owner/bookings/1/remove", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 401)
        # A logged-out session is rejected too.
        self.owner_login()
        self.client.post("/api/owner/logout", json={})
        resp = self.client.post("/api/owner/bookings/1/remove", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 401)

    # -- PIN re-confirmation (owner decision 2026-11-19) ------------------
    def test_remove_requires_pin_even_when_logged_in(self):
        driver, token, first, second = self.seed_rides()
        self.assertEqual(self.counts()["bookings"], 2)
        self.owner_login()
        # No PIN at all: rejected, nothing deleted.
        resp = self.client.post(
            f"/api/owner/bookings/{first['id']}/remove", json={})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(self.counts()["bookings"], 2)
        # Wrong PIN: rejected, nothing deleted.
        resp = self.client.post(
            f"/api/owner/bookings/{first['id']}/remove", json={"pin": "0000"})
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Wrong PIN", resp.get_data(as_text=True))
        self.assertEqual(self.counts()["bookings"], 2)
        # Correct PIN: proceeds.
        resp = self.client.post(
            f"/api/owner/bookings/{first['id']}/remove", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["removed"])
        self.assertEqual(self.counts()["bookings"], 1)

    def test_remove_rejects_get(self):
        self.owner_login()
        resp = self.client.get("/api/owner/bookings/1/remove")
        self.assertEqual(resp.status_code, 405)

    def test_remove_unknown_booking_404(self):
        self.owner_login()
        resp = self.client.post("/api/owner/bookings/999999/remove",
                                json={"pin": "9999"})
        self.assertEqual(resp.status_code, 404)

    # -- deletion -----------------------------------------------------------
    def test_remove_one_ride_keeps_the_other_and_the_driver(self):
        driver, token, first, second = self.seed_rides()
        before = self.counts()
        self.assertEqual(before["bookings"], 2)
        self.assertEqual(before["chat_messages"], 2)
        self.assertEqual(before["payments"], 2)
        self.assertEqual(before["booking_exclusions"], 1)
        self.owner_login()
        resp = self.client.post(
            f"/api/owner/bookings/{first['id']}/remove", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        deleted = resp.get_json()["deleted"]
        self.assertEqual(deleted["bookings"], 1)
        self.assertEqual(deleted["chat_messages"], 2)
        self.assertEqual(deleted["payments"], 1)
        after = self.counts()
        self.assertEqual(after["bookings"], 1)
        self.assertEqual(after["chat_messages"], 0)
        self.assertEqual(after["payments"], 1)
        self.assertEqual(after["booking_exclusions"], 1)
        # The other ride and the driver are untouched.
        with app_module.app.app_context():
            kept = app_module.db.session.get(app_module.Booking, second["id"])
            self.assertIsNotNone(kept)
            kept_driver = app_module.db.session.get(
                app_module.Driver, driver["id"])
            self.assertIsNotNone(kept_driver)
            self.assertEqual(len(kept_driver.documents), 6)
        # The referral code of the removed ride stays valid, detached.
        self.assertEqual(after["referral_codes"], 2)
        with app_module.app.app_context():
            codes = app_module.ReferralCode.query.all()
            self.assertTrue(all(c.issued_booking_id != first["id"] for c in codes))

    # -- dashboard + owner app ----------------------------------------------
    def test_remove_button_present_in_dashboard_and_app(self):
        js = read("static/js/owner.js")
        self.assertIn("/api/owner/bookings/", js)
        self.assertIn("/remove", js)
        self.assertIn("pin-confirm-modal", js)
        self.assertIn("pin: pin", js)
        app_js = read_app("src/api/client.ts")
        self.assertIn("removeBooking", app_js)
        self.assertIn("bookings/", app_js)
        rides_tsx = read_app("src/app/(tabs)/rides.tsx")
        self.assertIn("Remove", rides_tsx)


if __name__ == "__main__":
    unittest.main()
