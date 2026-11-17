"""Tests for the owner-only "Clear all rides" function (owner decision
2026-11-17): Azher asked to clear all test rides from his driver app
and restart the same test fresh.

TEMPORARY, testing only ("filhal ke vaaste"): delete this file along
with the endpoint and the dashboard button before real launch. The
clear is only ever a manual, owner-PIN-confirmed test reset — never
automatic. Driver ride history is otherwise retained for a minimum of
one year; no automatic deletion or expiry of ride records exists.

POST /api/owner/clear-rides (PIN auth via the owner session) deletes
ALL bookings plus chat messages, booking events (alerts), payments,
decline exclusions and outbox messages. It MUST keep drivers, their
documents and profile photos untouched, and referral codes stay valid
(their link to the deleted booking is detached, not deleted).

The owner dashboard shows a "Clear all rides" button only after login,
guarded by a confirm() dialog; on success it refreshes the summary,
bookings, payouts, alerts and outbox lists.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-clear-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "clear.db")
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

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Clear Rides Customer"}
PHOTO_BYTES = b"\xff\xd8\xff clear-test photo"
DOC_BYTES = b"\xff\xd8\xff clear-test dmv license"


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class ClearRidesCase(unittest.TestCase):
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
        phone = f"+1555007{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Clear Driver {self._driver_seq}", "phone": phone,
            "email": f"cd{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"C{self._driver_seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(PHOTO_BYTES), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(DOC_BYTES), "dmv.jpg"),
            "doc_tlc_license": (io.BytesIO(DOC_BYTES), "tlc.jpg"),
            "doc_fh1": (io.BytesIO(DOC_BYTES), "fh1.jpg"),
            "doc_registration": (io.BytesIO(DOC_BYTES), "reg.jpg"),
            "doc_inspection": (io.BytesIO(DOC_BYTES), "insp.jpg"),
            "doc_vehicle_permit": (io.BytesIO(DOC_BYTES), "permit.jpg"),
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

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
    def test_clear_requires_owner_login(self):
        resp = self.client.post("/api/owner/clear-rides", json={})
        self.assertEqual(resp.status_code, 401)
        # A logged-out session is rejected too.
        self.owner_login()
        self.client.post("/api/owner/logout", json={})
        resp = self.client.post("/api/owner/clear-rides", json={})
        self.assertEqual(resp.status_code, 401)

    def test_clear_rejects_get(self):
        self.owner_login()
        resp = self.client.get("/api/owner/clear-rides")
        self.assertEqual(resp.status_code, 405)

    # -- deletion -----------------------------------------------------------
    def test_clear_deletes_rides_and_related_rows(self):
        self.seed_rides()
        before = self.counts()
        self.assertEqual(before["bookings"], 2)
        self.assertEqual(before["chat_messages"], 2)
        self.assertEqual(before["payments"], 2)
        self.assertEqual(before["booking_exclusions"], 1)
        self.assertGreater(before["booking_events"], 0)
        self.assertGreater(before["outbox_messages"], 0)
        self.assertEqual(before["referral_codes"], 2)

        self.owner_login()
        resp = self.client.post("/api/owner/clear-rides", json={})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertTrue(body["cleared"])
        deleted = body["deleted"]
        self.assertEqual(deleted["bookings"], 2)
        self.assertEqual(deleted["chat_messages"], 2)
        self.assertEqual(deleted["payments"], 2)
        self.assertEqual(deleted["booking_exclusions"], 1)
        self.assertEqual(deleted["booking_events"], before["booking_events"])
        self.assertEqual(deleted["outbox_messages"], before["outbox_messages"])
        self.assertEqual(deleted["referral_codes_detached"], 2)

        after = self.counts()
        self.assertEqual(after["bookings"], 0)
        self.assertEqual(after["chat_messages"], 0)
        self.assertEqual(after["booking_events"], 0)
        self.assertEqual(after["payments"], 0)
        self.assertEqual(after["booking_exclusions"], 0)
        self.assertEqual(after["outbox_messages"], 0)

    def test_clear_keeps_driver_documents_and_photo(self):
        driver, token, _, _ = self.seed_rides()
        self.owner_login()
        resp = self.client.post("/api/owner/clear-rides", json={})
        self.assertEqual(resp.status_code, 200)
        after = self.counts()
        self.assertEqual(after["drivers"], 1)
        self.assertEqual(after["driver_documents"], 6)
        with app_module.app.app_context():
            kept = app_module.db.session.get(app_module.Driver, driver["id"])
            self.assertIsNotNone(kept)
            self.assertEqual(kept.phone, driver["phone"])
            self.assertEqual(kept.token, token)
            self.assertEqual(kept.profile_photo, PHOTO_BYTES)
            self.assertEqual(len(kept.documents), 6)
            self.assertEqual(kept.documents[0].doc_type, "dmv_license")
            self.assertEqual(kept.documents[0].file, DOC_BYTES)
        # The driver still signs in and sees an empty offers list.
        resp = self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])
        # Owner lists are empty but the driver list still shows the driver.
        self.assertEqual(self.client.get("/api/owner/bookings").get_json(), [])
        self.assertEqual(self.client.get("/api/owner/alerts").get_json(), [])
        self.assertEqual(self.client.get("/api/owner/outbox").get_json(), [])
        drivers = self.client.get("/api/owner/drivers").get_json()
        self.assertEqual(len(drivers), 1)
        self.assertEqual(drivers[0]["phone"], driver["phone"])

    def test_clear_is_idempotent_on_empty_db(self):
        self.owner_login()
        resp = self.client.post("/api/owner/clear-rides", json={})
        self.assertEqual(resp.status_code, 200)
        deleted = resp.get_json()["deleted"]
        self.assertEqual(deleted["bookings"], 0)
        self.assertEqual(deleted["chat_messages"], 0)
        self.assertEqual(deleted["booking_events"], 0)
        self.assertEqual(deleted["payments"], 0)
        self.assertEqual(deleted["booking_exclusions"], 0)
        self.assertEqual(deleted["outbox_messages"], 0)
        resp = self.client.post("/api/owner/clear-rides", json={})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["cleared"])

    def test_referral_codes_stay_valid_after_clear(self):
        booking = self.book()
        code = booking["referral_code"]
        self.assertTrue(code)
        self.owner_login()
        self.assertEqual(self.client.post("/api/owner/clear-rides", json={}).status_code, 200)
        with app_module.app.app_context():
            row = app_module.ReferralCode.query.filter_by(code=code).first()
            self.assertIsNotNone(row)
            self.assertIsNone(row.issued_booking_id)
        # The kept code is still accepted on a fresh booking.
        fresh = self.book(referral_code=code)
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, fresh["id"])
            self.assertEqual(row.referral_code_used, code)

    # -- dashboard button -----------------------------------------------------
    def test_dashboard_button_present_only_after_login(self):
        html = read("static/owner.html")
        gate = html.index('id="pin-gate"')
        dash = html.index('id="dashboard"')
        button = html.index('id="clear-rides-btn"')
        self.assertIn("Clear all rides", html)
        # The button lives inside the post-login dashboard, not the PIN gate.
        self.assertGreater(button, dash)
        self.assertGreater(dash, gate)
        js = read("static/js/owner.js")
        self.assertIn("/api/owner/clear-rides", js)
        self.assertIn("clear-rides-btn", js)
        self.assertIn("window.confirm(", js)
        # On success the dashboard refreshes its lists.
        for loader in ("loadBookings()", "loadPayouts()", "loadAlerts()",
                       "loadOutbox()", "loadSummaryThenEnterSoft()"):
            self.assertIn(loader, js)


if __name__ == "__main__":
    unittest.main()
