"""Tests for the arrival / completion proximity gates (owner decision
2026-11-17, fraud prevention).

'I have arrived' is allowed only within 100 m of the pickup
coordinates; 'Complete trip' only within 100 m of the drop-off
coordinates. Enforced server-side in the stage-advance endpoint and
client-side in the driver app (button disabled + explanation until in
range; a fresh GPS position is sent with every gated advance).

- Hourly rides have no drop-off, so their completion stays ungated.
- A booking without stored coordinates for the relevant end cannot
  be verified, so the advance is allowed (old/test rides).
- A request carrying no position is allowed: the driver app requires
  location before it sends a gated advance, so the no-position case
  is the client's to enforce; the server rejects any position it IS
  given that is out of range.
- en_route / start are never gated, and the existing stage sequence
  (advances without a position) is unaffected.

Mocked geo puts every one-way ride at 18.0 miles from JFK
(40.6413, -73.7781) to Times Square (40.7580, -73.9855). A 0.0005
degree latitude offset is ~56 m (in range); 0.001 degree is ~111 m
(out of range).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import re
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-gates-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "gates.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "gates-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules): JFK pickup, Times Square drop-off.
PICKUP = (40.6413, -73.7781)
DROPOFF = (40.7580, -73.9855)
geo_module.distance_miles = lambda p, d: (18.0, PICKUP, DROPOFF)  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Gate Test Customer"}
ARRIVED_MSG = "You must be at the pickup location to mark arrived."
COMPLETE_MSG = "You must be at the drop-off location to complete the trip."


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def near(coords, dlat=0.0005):
    return {"lat": coords[0] + dlat, "lng": coords[1]}


def at(coords):
    return {"lat": coords[0], "lng": coords[1]}


class ProximityGatesCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, car_model="Cadillac CT6", email=None):
        self._driver_seq += 1
        phone = f"+1555007{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Gate Driver {self._driver_seq}", "phone": phone,
            "email": email or f"gd{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
            "plate": f"G{self._driver_seq:05d}",
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
        """Compulsory customer sign-in (owner 2026-11-22): payment
        needs a verified sign-in with the booking's email. Signs in
        once per email per test — the session persists for later
        bookings and payments in the same test."""
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin/request",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            row = (app_module.OutboxMessage.query
                   .filter_by(recipient=email, channel="email")
                   .order_by(app_module.OutboxMessage.id.desc()).first())
        self.assertIsNotNone(row, "no sign-in email was queued")
        match = re.search(r"(\d{6})", row.body or "")
        self.assertIsNotNone(match, "no 6-digit code in the email")
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": email, "code": match.group(1)})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Gate Test Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "gates@test.com",
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

    def book_hourly(self):
        self._phone_seq += 1
        payload = {
            "customer_name": "Gate Test Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "gates@test.com",
            "pickup": "JFK Airport",
            "date": "2030-06-01", "time": "12:00",
            "ride_type": "hourly", "hours": 3, "vehicle_class": "sedan",
        }
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking = resp.get_json()["booking"]
        booking["phone"] = payload["phone"]
        if "@" in (payload.get("email") or "") and payload.get("phone"):
            self.signin(payload["email"], payload["phone"])
        return booking

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def accept(self, booking_id, token):
        return self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                json={}, headers={"X-Driver-Token": token})

    def trip_event(self, booking_id, token, event, **kw):
        return self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                json={"event": event, **kw},
                                headers={"X-Driver-Token": token})

    def accepted_trip(self, booking=None, email=None):
        _, token = self.register_driver(email=email)
        booking = booking or self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        return booking, token

    def status_of(self, booking_id, token):
        resp = self.client.get("/api/drivers/me/active-trip",
                               headers={"X-Driver-Token": token})
        trip = resp.get_json()["booking"]
        return trip["status"] if trip else None

    # -- arrived gate ------------------------------------------------------
    def test_arrived_in_range_allowed(self):
        booking, token = self.accepted_trip()
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        resp = self.trip_event(booking["id"], token, "arrived", **at(PICKUP))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(self.status_of(booking["id"], token), "arrived")

    def test_arrived_near_pickup_allowed(self):
        booking, token = self.accepted_trip()
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        resp = self.trip_event(booking["id"], token, "arrived", **near(PICKUP))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_arrived_out_of_range_rejected_then_retry_allowed(self):
        booking, token = self.accepted_trip()
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        # Driver still at the drop-off side of town: far from pickup.
        resp = self.trip_event(booking["id"], token, "arrived", **at(DROPOFF))
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn(ARRIVED_MSG, resp.get_data(as_text=True))
        self.assertEqual(self.status_of(booking["id"], token), "en_route")
        # Reaching the pickup allows the same step.
        resp = self.trip_event(booking["id"], token, "arrived", **at(PICKUP))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(self.status_of(booking["id"], token), "arrived")

    def test_arrived_111m_out_of_range_rejected(self):
        booking, token = self.accepted_trip()
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        resp = self.trip_event(booking["id"], token, "arrived", **near(PICKUP, dlat=0.001))
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn(ARRIVED_MSG, resp.get_data(as_text=True))

    def test_arrived_without_position_allowed(self):
        # No position in the request: allowed (the driver app enforces
        # the location requirement client-side); existing clients and
        # the stage sequence keep working.
        booking, token = self.accepted_trip()
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        resp = self.trip_event(booking["id"], token, "arrived")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    # -- complete gate -----------------------------------------------------
    def drive_to_start(self, booking, token):
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "arrived", **at(PICKUP)).status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "start").status_code, 200)

    def test_complete_in_range_allowed(self):
        booking, token = self.accepted_trip()
        self.drive_to_start(booking, token)
        resp = self.trip_event(booking["id"], token, "complete", **near(DROPOFF))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_complete_out_of_range_rejected(self):
        booking, token = self.accepted_trip()
        self.drive_to_start(booking, token)
        # Driver still at the pickup: far from the drop-off.
        resp = self.trip_event(booking["id"], token, "complete", **at(PICKUP))
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn(COMPLETE_MSG, resp.get_data(as_text=True))
        self.assertEqual(self.status_of(booking["id"], token), "in_progress")
        resp = self.trip_event(booking["id"], token, "complete", **at(DROPOFF))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_complete_hourly_ungated(self):
        _, token = self.register_driver()
        booking = self.book_hourly()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "arrived").status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "start").status_code, 200)
        # Hourly rides have no drop-off: a far-away position must not
        # block completion.
        resp = self.trip_event(booking["id"], token, "complete", **at(PICKUP))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_hourly_arrived_ungated_no_coords(self):
        # Hourly bookings store no coordinates, so the arrived gate
        # cannot verify and must allow the advance.
        _, token = self.register_driver()
        booking = self.book_hourly()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        resp = self.trip_event(booking["id"], token, "arrived", **at(DROPOFF))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    # -- location exemption: owner + Sana only (2026-11-20) ---------------
    # Owner decision 2026-11-20 (voice call): the location gate does
    # not apply to Azher Mohammed or Sana Baga — "I have arrived" and
    # "Complete trip" work for them without a location, and a
    # far-away position never blocks them. Every other driver keeps
    # the 100 m gate exactly as it is. The exempt set is the same
    # three emails as the Model 3 exception (car_models.py).
    def test_exempt_driver_arrived_without_position_allowed(self):
        booking, token = self.accepted_trip(email="sanabaga12@gmail.com")
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        resp = self.trip_event(booking["id"], token, "arrived")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(self.status_of(booking["id"], token), "arrived")

    def test_exempt_driver_arrived_far_position_allowed(self):
        booking, token = self.accepted_trip(email="sanabaga12@gmail.com")
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        # Sana is at the drop-off side of town: far from the pickup —
        # the gate must not block her.
        resp = self.trip_event(booking["id"], token, "arrived", **at(DROPOFF))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(self.status_of(booking["id"], token), "arrived")

    def test_exempt_driver_complete_far_position_allowed(self):
        booking, token = self.accepted_trip(email="m.azherahmed1@gmail.com")
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "arrived").status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "start").status_code, 200)
        # The owner is still at the pickup: far from the drop-off —
        # the gate must not block him.
        resp = self.trip_event(booking["id"], token, "complete", **at(PICKUP))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_exempt_driver_second_owner_email_allowed(self):
        # The owner's other email counts too (same as Model 3).
        booking, token = self.accepted_trip(email="ahmedazher476@gmail.com")
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        resp = self.trip_event(booking["id"], token, "arrived", **at(DROPOFF))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_other_driver_arrived_far_position_still_rejected(self):
        # A non-exempt driver with the same far-away position is
        # still blocked by the 100 m gate.
        booking, token = self.accepted_trip(email="other-driver@test.com")
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        resp = self.trip_event(booking["id"], token, "arrived", **at(DROPOFF))
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn(ARRIVED_MSG, resp.get_data(as_text=True))
        self.assertEqual(self.status_of(booking["id"], token), "en_route")

    def test_other_driver_complete_far_position_still_rejected(self):
        booking, token = self.accepted_trip(email="other-driver@test.com")
        self.drive_to_start(booking, token)
        resp = self.trip_event(booking["id"], token, "complete", **at(PICKUP))
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn(COMPLETE_MSG, resp.get_data(as_text=True))
        self.assertEqual(self.status_of(booking["id"], token), "in_progress")

    def test_exempt_driver_hourly_complete_ungated(self):
        # Hourly completion stays ungated for exempt drivers too.
        _, token = self.register_driver(email="sanabaga12@gmail.com")
        booking = self.book_hourly()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "arrived").status_code, 200)
        self.assertEqual(self.trip_event(booking["id"], token, "start").status_code, 200)
        resp = self.trip_event(booking["id"], token, "complete", **at(PICKUP))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_location_exempt_helper_matches_model_3_set(self):
        import car_models
        self.assertEqual(car_models.LOCATION_EXEMPT_EMAILS,
                         car_models.MODEL_3_ALLOWED_EMAILS)
        for email in ("m.azherahmed1@gmail.com", "ahmedazher476@gmail.com",
                      "sanabaga12@gmail.com", "  SanaBaga12@Gmail.com  "):
            self.assertTrue(car_models.location_exempt_for(email), email)
        for email in ("other-driver@test.com", "", None):
            self.assertFalse(car_models.location_exempt_for(email), email)

    def test_client_location_exemption_markers(self):
        js = read("static/js/driver.js")
        for marker in (
            "LOCATION_EXEMPT_EMAILS",
            "locationExempt",
            "m.azherahmed1@gmail.com",
            "ahmedazher476@gmail.com",
            "sanabaga12@gmail.com",
            "state.driver.email",
            "if (locationExempt()) return null;",
        ):
            self.assertIn(marker, js, marker)

    # -- missing-coordinates fallback --------------------------------------
    def test_missing_coordinates_fallback_allows_advance(self):
        booking, token = self.accepted_trip()
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            row.pickup_lat = None
            row.pickup_lng = None
            row.dropoff_lat = None
            row.dropoff_lng = None
            app_module.db.session.commit()
        self.assertEqual(self.trip_event(booking["id"], token, "en_route").status_code, 200)
        # Far-away positions, but nothing stored to verify against.
        resp = self.trip_event(booking["id"], token, "arrived", **at(DROPOFF))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(self.trip_event(booking["id"], token, "start").status_code, 200)
        resp = self.trip_event(booking["id"], token, "complete", **at(PICKUP))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    # -- other stages unaffected -------------------------------------------
    def test_en_route_and_start_not_gated(self):
        booking, token = self.accepted_trip()
        resp = self.trip_event(booking["id"], token, "en_route", **at(DROPOFF))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(self.trip_event(booking["id"], token, "arrived", **at(PICKUP)).status_code, 200)
        resp = self.trip_event(booking["id"], token, "start", **at(DROPOFF))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_full_sequence_without_positions_unaffected(self):
        booking, token = self.accepted_trip()
        for event in ("en_route", "arrived", "start", "complete"):
            resp = self.trip_event(booking["id"], token, event)
            self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_stage_order_still_enforced_before_gate(self):
        # Arriving before heading to pickup keeps the original 409,
        # even with an in-range position.
        booking, token = self.accepted_trip()
        resp = self.trip_event(booking["id"], token, "arrived", **at(PICKUP))
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn("Cannot mark arrived before heading to pickup.",
                      resp.get_data(as_text=True))

    # -- payloads ----------------------------------------------------------
    def test_trip_payloads_expose_coordinates_without_money_keys(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        accept = self.accept(booking["id"], token)
        self.assertEqual(accept.status_code, 200)
        trip = accept.get_json()["booking"]
        self.assertEqual((trip["pickup_lat"], trip["pickup_lng"]), PICKUP)
        self.assertEqual((trip["dropoff_lat"], trip["dropoff_lng"]), DROPOFF)
        self.assertTrue(FORBIDDEN_KEYS.isdisjoint(trip.keys()), sorted(trip.keys()))
        resp = self.client.get("/api/drivers/me/active-trip",
                               headers={"X-Driver-Token": token})
        trip = resp.get_json()["booking"]
        self.assertEqual((trip["pickup_lat"], trip["pickup_lng"]), PICKUP)
        self.assertEqual((trip["dropoff_lat"], trip["dropoff_lng"]), DROPOFF)
        self.assertTrue(FORBIDDEN_KEYS.isdisjoint(trip.keys()), sorted(trip.keys()))

    # -- client wiring -----------------------------------------------------
    def test_client_gate_markers(self):
        js = read("static/js/driver.js")
        for marker in (
            "PROXIMITY_GATE_METERS",
            "haversineMeters",
            "gateTarget",
            "refreshGateNote",
            "getFreshPosition",
            "getCurrentPosition",
            "trip-gate-note",
            ARRIVED_MSG,
            COMPLETE_MSG,
            "Location is needed to mark this step. Please allow location access and try again.",
            "extra.lat = pos.lat",
            "extra.lng = pos.lng",
            "ride_type === \"hourly\"",
        ):
            self.assertIn(marker, js, marker)
        html = read("static/driver.html")
        self.assertIn('id="trip-gate-note"', html)


if __name__ == "__main__":
    unittest.main()
