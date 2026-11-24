"""Tests for the 48-hour fault-suspension exemption (owner decision
2026-11-24, voice call — "mere ko aur sana ko nahi karna pause").

- Azher Mohammed (m.azherahmed1@gmail.com, ahmedazher476@gmail.com)
  and Sana Baga (sanabaga12@gmail.com) are exempt from the fault
  suspension: a fault emergency cancel by either of them still
  re-dispatches the job, but no 48-hour block is created and no
  paused notice shows.
- A suspension already on an exempt driver's record reads as
  lifted: /api/drivers/me reports suspended_until None, and the
  driver can go available, get offers and accept.
- Every other driver keeps the 48-hour fault block exactly as it
  is (covered by test_emergency_cancel.py; one boundary test here
  pins the exempt/non-exempt line).

Run:  python -m unittest discover -s tests -v
"""

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-suspension-exemption-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "suspension-exemption-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import car_models  # noqa: E402
import photo_factory  # noqa: E402

CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Suspension Exemption Customer"}

AZHER_EMAIL = "m.azherahmed1@gmail.com"
AZHER_EMAIL_2 = "ahmedazher476@gmail.com"
SANA_EMAIL = "sanabaga12@gmail.com"


def _ny_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.now(timezone.utc)


class SuspensionExemptionCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, email):
        self._driver_seq += 1
        phone = f"+1555015{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Exemption Driver {self._driver_seq}", "phone": phone,
            "email": email,
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"X{self._driver_seq:05d}",
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
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Suspension Exemption Customer",
            "phone": f"+1555016{self._phone_seq:04d}",
            "email": "suspensionexemption@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        if "@" in (payload.get("email") or "") and payload.get("phone"):
            self.signin(payload["email"], payload["phone"])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def accept(self, token, booking_id):
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def trip_event(self, token, booking_id, event, **extra):
        payload = {"event": event}
        payload.update(extra)
        return self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                json=payload,
                                headers={"X-Driver-Token": token})

    def pickup_offset(self, minutes):
        """(date, time) strings for a pickup `minutes` from now (NY)."""
        when = _ny_now() + timedelta(minutes=minutes)
        return when.strftime("%Y-%m-%d"), when.strftime("%H:%M")

    def accepted_booking(self, email, minutes_out):
        """An exempt/non-exempt driver + an accepted booking `minutes_out` from now."""
        driver, token = self.register_driver(email)
        date, time = self.pickup_offset(minutes_out)
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token, booking["id"])
        return booking, driver, token

    def me(self, token):
        return self.client.get("/api/drivers/me",
                               headers={"X-Driver-Token": token}).get_json()["driver"]

    # -- helper: the exemption shares the Model 3 / location email set ---
    def test_exemption_helper_matches_model_3_set(self):
        for email in (AZHER_EMAIL, AZHER_EMAIL_2, SANA_EMAIL):
            self.assertTrue(car_models.suspension_exempt_for(email), email)
            self.assertTrue(car_models.location_exempt_for(email), email)
            self.assertTrue(car_models.model_3_allowed_for(email), email)
        for email in ("other@test.com", "", None, "sanabaga12@gmail.co"):
            self.assertFalse(car_models.suspension_exempt_for(email), str(email))
        self.assertEqual(car_models.SUSPENSION_EXEMPT_EMAILS,
                         car_models.LOCATION_EXEMPT_EMAILS)

    # -- exempt driver: fault cancel creates NO suspension -----------------
    def test_exempt_driver_fault_cancel_creates_no_suspension(self):
        booking, _driver, token = self.accepted_booking(AZHER_EMAIL, 60)
        resp = self.trip_event(token, booking["id"], "cancel",
                               reason="other_job")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertEqual(body["booking"]["status"], "offered")
        self.assertEqual(body["emergency_cancel"]["judgment"], "fault")
        self.assertIsNone(body["emergency_cancel"]["suspended_until"])
        # The fault is still recorded for owner visibility, but with
        # no suspension attached.
        with app_module.app.app_context():
            rows = app_module.EmergencyCancel.query.filter_by(
                booking_id=booking["id"]).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].judgment, "fault")
        self.assertIsNone(rows[0].suspended_until)
        # The driver reads as unsuspended: no banner, still available.
        me = self.me(token)
        self.assertIsNone(me["suspended_until"])
        self.assertTrue(me["available"])
        resp = self.client.post("/api/drivers/me/availability",
                                json={"available": True},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        # And he still gets offers and can accept a new job.
        date, time = self.pickup_offset(120)
        booking2 = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking2["id"]).status_code, 200)
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertIn(booking2["id"], [o["booking_id"] for o in offers])
        self.accept(token, booking2["id"])

    def test_sana_exempt_too(self):
        booking, _driver, token = self.accepted_booking(SANA_EMAIL, 60)
        resp = self.trip_event(token, booking["id"], "cancel",
                               reason="dont_want")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["emergency_cancel"]["judgment"], "fault")
        self.assertIsNone(resp.get_json()["emergency_cancel"]["suspended_until"])
        self.assertIsNone(self.me(token)["suspended_until"])

    def test_exempt_second_email_also_exempt(self):
        booking, _driver, token = self.accepted_booking(AZHER_EMAIL_2, 60)
        resp = self.trip_event(token, booking["id"], "cancel",
                               reason="running_late")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["emergency_cancel"]["judgment"], "fault")
        self.assertIsNone(resp.get_json()["emergency_cancel"]["suspended_until"])

    # -- exempt driver: an EXISTING suspension reads as lifted ------------
    def test_exempt_driver_existing_suspension_reads_as_lifted(self):
        # Mimics the owner's live state: paused until Nov 26, 2026
        # 12:40 AM after a fault cancel — stored on the driver row.
        _driver, token = self.register_driver(AZHER_EMAIL)
        with app_module.app.app_context():
            row = app_module.Driver.query.filter_by(email=AZHER_EMAIL).first()
            row.suspended_until = datetime.now(timezone.utc) + timedelta(hours=48)
            row.available = False
            app_module.db.session.commit()
        # The app reports no suspension, so no paused banner shows.
        me = self.me(token)
        self.assertIsNone(me["suspended_until"])
        # He can go online immediately...
        resp = self.client.post("/api/drivers/me/availability",
                                json={"available": True},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        # ...gets offers and can accept.
        date, time = self.pickup_offset(120)
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertIn(booking["id"], [o["booking_id"] for o in offers])
        self.accept(token, booking["id"])

    # -- boundary: everyone else still gets the 48h block -----------------
    def test_nonexempt_driver_fault_cancel_still_suspends_48h(self):
        booking, _driver, token = self.accepted_booking("otherdriver@test.com", 60)
        resp = self.trip_event(token, booking["id"], "cancel",
                               reason="other_job")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertEqual(body["emergency_cancel"]["judgment"], "fault")
        self.assertIsNotNone(body["emergency_cancel"]["suspended_until"])
        end = datetime.fromisoformat(
            body["emergency_cancel"]["suspended_until"].replace("Z", "+00:00"))
        delta = end - datetime.now(timezone.utc)
        self.assertTrue(timedelta(hours=47) < delta <= timedelta(hours=48, minutes=5),
                        str(delta))
        self.assertIsNotNone(self.me(token)["suspended_until"])
        resp = self.client.post("/api/drivers/me/availability",
                                json={"available": True},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("paused", resp.get_json()["error"])
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(offers, [])


if __name__ == "__main__":
    unittest.main()
