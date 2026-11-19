"""Tests for the owner-only "Remove all drivers" function (owner
decision 2026-11-17, voice call): Azher asked to remove every
currently registered driver ("jitne bhi") so everyone re-registers
fresh with the new state selector.

TEMPORARY, testing only: delete this file along with the endpoint and
the dashboard button before real launch. The removal is only ever a
manual, owner-PIN-confirmed test reset — never automatic. Ride
history is KEPT: bookings stay (only their driver links are
detached), and payments, chat messages, booking events, outbox
messages and referral codes are untouched — driver ride records are
retained for a minimum of one year.

POST /api/owner/clear-drivers (PIN auth via the owner session) deletes
ALL Driver rows plus every DriverDocument row (ORM cascade) and every
BookingExclusion row, and NULLs Booking.accepted_driver_id /
assigned_driver_id. A removed driver's phone number becomes free to
register again.

The owner dashboard shows a "Remove all drivers" button only after
login, guarded by a confirm() dialog; on success it shows the
returned counts and refreshes the lists (including drivers).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-clear-drivers-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "clear-drivers.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "clear-drivers-secret-key"
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
        "card_cvc": "123", "card_name": "Clear Drivers Customer"}
PHOTO_BYTES = photo_factory.VALID_PROFILE_PHOTO


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class ClearDriversCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, phone=None):
        self._driver_seq += 1
        phone = phone or f"+1555009{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Clear Driver {self._driver_seq}", "phone": phone,
            "email": f"cd{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"D{self._driver_seq:05d}",
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
            "doc_dmv_license": (io.BytesIO(photo_factory.doc_photo()), "dmv.jpg"),
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

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Clear Drivers Customer",
            "phone": f"+1555010{self._phone_seq:04d}",
            "email": "clear-drivers@test.com",
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

    def seed_drivers_and_rides(self):
        """Two drivers, three paid bookings: one accepted by driver 1
        (with a chat exchange), one declined by driver 2 (exclusion
        row), one owner-assigned to driver 2. Returns the pieces."""
        driver1, token1 = self.register_driver()
        driver2, token2 = self.register_driver()
        first = self.book()
        self.assertEqual(self.pay(first["id"]).status_code, 200)
        resp = self.client.post(
            f"/api/drivers/me/offers/{first['id']}/accept", json={},
            headers={"X-Driver-Token": token1})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/drivers/me/trip/{first['id']}/messages",
                                json={"text": "On my way."},
                                headers={"X-Driver-Token": token1})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/bookings/{first['id']}/messages",
                                json={"phone": first["phone"], "text": "At arrivals."})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        second = self.book(time="15:00")
        self.assertEqual(self.pay(second["id"]).status_code, 200)
        resp = self.client.post(
            f"/api/drivers/me/offers/{second['id']}/decline", json={},
            headers={"X-Driver-Token": token2})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        third = self.book(time="18:00")
        self.assertEqual(self.pay(third["id"]).status_code, 200)
        self.owner_login()
        resp = self.client.post(f"/api/owner/bookings/{third['id']}/assign",
                                json={"driver_id": driver2["id"]})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return driver1, token1, driver2, token2, first, second, third

    # -- auth ---------------------------------------------------------------
    def test_clear_requires_owner_login(self):
        resp = self.client.post("/api/owner/clear-drivers", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 401)
        # A logged-out session is rejected too.
        self.owner_login()
        self.client.post("/api/owner/logout", json={})
        resp = self.client.post("/api/owner/clear-drivers", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 401)

    # -- PIN re-confirmation (owner decision 2026-11-19) ------------------
    def test_clear_requires_pin_even_when_logged_in(self):
        self.seed_drivers_and_rides()
        self.assertEqual(self.counts()["drivers"], 2)
        self.owner_login()
        # No PIN at all: rejected, nothing removed.
        resp = self.client.post("/api/owner/clear-drivers", json={})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(self.counts()["drivers"], 2)
        # Wrong PIN: rejected, nothing removed.
        resp = self.client.post("/api/owner/clear-drivers", json={"pin": "0000"})
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Wrong PIN", resp.get_data(as_text=True))
        self.assertEqual(self.counts()["drivers"], 2)
        # Correct PIN: proceeds.
        resp = self.client.post("/api/owner/clear-drivers", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.counts()["drivers"], 0)

    def test_clear_rejects_get(self):
        self.owner_login()
        resp = self.client.get("/api/owner/clear-drivers")
        self.assertEqual(resp.status_code, 405)

    # -- deletion -----------------------------------------------------------
    def test_clear_removes_drivers_and_unlinks_but_keeps_rides(self):
        driver1, token1, driver2, token2, first, second, third = \
            self.seed_drivers_and_rides()
        with app_module.app.app_context():
            doc_id = app_module.DriverDocument.query.first().id
            fare_before = str(app_module.db.session.get(
                app_module.Booking, first["id"]).fare_total)
        before = self.counts()
        self.assertEqual(before["drivers"], 2)
        self.assertEqual(before["driver_documents"], 12)
        self.assertEqual(before["booking_exclusions"], 1)
        self.assertEqual(before["bookings"], 3)
        self.assertEqual(before["chat_messages"], 2)
        self.assertEqual(before["payments"], 3)
        self.assertGreater(before["booking_events"], 0)
        self.assertGreater(before["outbox_messages"], 0)
        self.assertEqual(before["referral_codes"], 3)

        self.owner_login()
        resp = self.client.post("/api/owner/clear-drivers", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertTrue(body["cleared"])
        deleted = body["deleted"]
        self.assertEqual(deleted["drivers"], 2)
        self.assertEqual(deleted["documents"], 12)
        self.assertEqual(deleted["booking_exclusions"], 1)
        # One accepted booking + one assigned booking unlinked.
        self.assertEqual(deleted["bookings_unlinked"], 2)

        after = self.counts()
        self.assertEqual(after["drivers"], 0)
        self.assertEqual(after["driver_documents"], 0)
        self.assertEqual(after["booking_exclusions"], 0)
        # Ride history is KEPT, untouched apart from the driver links.
        self.assertEqual(after["bookings"], 3)
        self.assertEqual(after["chat_messages"], 2)
        self.assertEqual(after["payments"], 3)
        self.assertEqual(after["booking_events"], before["booking_events"])
        self.assertEqual(after["outbox_messages"], before["outbox_messages"])
        self.assertEqual(after["referral_codes"], 3)
        with app_module.app.app_context():
            for booking_id in (first["id"], second["id"], third["id"]):
                row = app_module.db.session.get(app_module.Booking, booking_id)
                self.assertIsNone(row.accepted_driver_id)
                self.assertIsNone(row.assigned_driver_id)
            self.assertEqual(str(app_module.db.session.get(
                app_module.Booking, first["id"]).fare_total), fare_before)
            self.assertIsNone(app_module.db.session.get(
                app_module.Driver, driver1["id"]))
            self.assertIsNone(app_module.db.session.get(
                app_module.Driver, driver2["id"]))
        # Old driver tokens no longer work; owner lists show no drivers.
        resp = self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token1})
        self.assertEqual(resp.status_code, 401)
        resp = self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token2})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(self.client.get("/api/owner/drivers").get_json(), [])
        # Old document files and profile photos are gone too.
        self.assertEqual(self.client.get(f"/api/owner/documents/{doc_id}").status_code, 404)
        self.assertEqual(
            self.client.get(f"/api/owner/drivers/{driver1['id']}/photo").status_code, 404)
        # Bookings are still listed for the owner, with no driver shown.
        rows = self.client.get("/api/owner/bookings").get_json()
        self.assertEqual(len(rows), 3)

    def test_clear_is_idempotent_on_empty_db(self):
        self.owner_login()
        resp = self.client.post("/api/owner/clear-drivers", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        deleted = resp.get_json()["deleted"]
        self.assertEqual(deleted["drivers"], 0)
        self.assertEqual(deleted["documents"], 0)
        self.assertEqual(deleted["booking_exclusions"], 0)
        self.assertEqual(deleted["bookings_unlinked"], 0)
        resp = self.client.post("/api/owner/clear-drivers", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["cleared"])

    def test_re_registration_with_same_phone_succeeds(self):
        driver, token = self.register_driver(phone="+15550110000")
        self.owner_login()
        self.assertEqual(self.client.post("/api/owner/clear-drivers", json={"pin": "9999"}).status_code, 200)
        # The freed phone number registers again, as a brand-new driver
        # (new token; SQLite may reuse the row id, so the token — not
        # the id — proves it is a fresh registration).
        driver2, token2 = self.register_driver(phone="+15550110000")
        self.assertNotEqual(token2, token)
        resp = self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token2})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])
        drivers = self.client.get("/api/owner/drivers").get_json()
        self.assertEqual(len(drivers), 1)
        self.assertEqual(drivers[0]["phone"], "+15550110000")

    # -- dashboard button -----------------------------------------------------
    def test_dashboard_button_present_only_after_login(self):
        html = read("static/owner.html")
        gate = html.index('id="pin-gate"')
        dash = html.index('id="dashboard"')
        button = html.index('id="clear-drivers-btn"')
        self.assertIn("Remove all drivers", html)
        # The button lives inside the post-login dashboard, not the PIN gate,
        # next to the Clear all rides button.
        self.assertGreater(button, dash)
        self.assertGreater(dash, gate)
        self.assertGreater(button, html.index('id="clear-rides-btn"'))
        js = read("static/js/owner.js")
        self.assertIn("/api/owner/clear-drivers", js)
        self.assertIn("clear-drivers-btn", js)
        # PIN re-confirmation (owner decision 2026-11-19): the clear
        # button no longer uses a bare confirm() — tapping it opens a
        # PIN prompt first and the PIN is sent with the request for a
        # server-side check.
        self.assertNotIn("Remove ALL drivers?", js)
        self.assertIn("pin-confirm-modal", js)
        self.assertIn("pin-confirm-input", js)
        self.assertIn("pin: pin", js)
        # On success the handler shows the returned counts and refreshes
        # the lists, including the driver list.
        self.assertIn("window.alert(", js)
        self.assertIn("loadDrivers()", js)


if __name__ == "__main__":
    unittest.main()
