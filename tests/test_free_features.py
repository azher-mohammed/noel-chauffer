"""Tests for the free Blacklane-style features (owner decision 2026-11-16).

1. Digital name sign: the driver active-trip payload already exposes
   the customer name + airport_pickup flag; the trip screen shows a
   "Name sign" button for airport pickups opening a full-screen
   overlay with the customer's name.
2. In-app chat (no SMS, no number masking): driver and customer
   exchange plain-text messages on the trip/ride view, gated on a
   driver having accepted. Messages never carry money figures.
3. Extra distance at completion: one-way rides only; added fare
   only (no gratuity, no tax) to the customer total, driver rate
   per mile to the driver; owner dashboard shows an extra-distance
   line.
4. Dispatcher-lite: the owner can assign a paid, not-yet-accepted
   booking to one driver; it then appears only in that driver's
   offers. Default stays broadcast first-accept-wins.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from unittest import mock
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-free-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "free.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "free-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules): sedan total $162.00, driver $95.00 (10-20 slab) before toll.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
import pricing  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Free Features Customer"}


def approx(a, b):
    return a is not None and abs(float(a) - float(b)) < 0.005


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


# These tests pin the legacy $9/$10 totals as fixtures (the free-wait
# and extra-miles mechanics are engine-independent); the live engine
# is Blacklane by default since the owner flip (2026-11-20).
@mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"})
class FreeFeaturesCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, car_model="Cadillac CT6"):
        self._driver_seq += 1
        phone = f"+1555005{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Free Driver {self._driver_seq}", "phone": phone,
            "email": f"fd{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
            "plate": f"F{self._driver_seq:05d}",
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
            "customer_name": "Free Features Customer",
            "phone": f"+1555006{self._phone_seq:04d}",
            "email": "free@test.com",
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

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)

    def offers(self, token):
        return self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token}).get_json()

    def accept(self, booking_id, token):
        return self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                json={}, headers={"X-Driver-Token": token})

    def trip_event(self, booking_id, token, event, **kw):
        return self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                json={"event": event, **kw},
                                headers={"X-Driver-Token": token})

    def drive_to(self, booking_id, token, stage):
        """Run trip stages up to `stage` (en_route/arrived/start)."""
        for event in ("en_route", "arrived", "start"):
            resp = self.trip_event(booking_id, token, event)
            self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
            if event == stage:
                return

    # -- pricing: extra distance ------------------------------------------
    def test_extra_distance_sedan_math(self):
        r = pricing.compute_extra_distance(Decimal("5"), "sedan")
        self.assertEqual(r["fare"], Decimal("45.00"))
        self.assertEqual(r["gratuity"], Decimal("0.00"))
        self.assertEqual(r["tax"], Decimal("0.00"))
        self.assertEqual(r["total"], Decimal("45.00"))
        self.assertEqual(r["driver_addition"], Decimal("20.00"))

    def test_extra_distance_suv_math(self):
        r = pricing.compute_extra_distance(Decimal("5"), "suv")
        self.assertEqual(r["fare"], Decimal("50.00"))
        self.assertEqual(r["gratuity"], Decimal("0.00"))
        self.assertEqual(r["tax"], Decimal("0.00"))
        self.assertEqual(r["total"], Decimal("50.00"))
        self.assertEqual(r["driver_addition"], Decimal("30.00"))

    def test_extra_distance_zero_and_negative(self):
        r = pricing.compute_extra_distance(Decimal("0"), "sedan")
        self.assertEqual(r["total"], Decimal("0.00"))
        self.assertEqual(r["driver_addition"], Decimal("0.00"))
        with self.assertRaises(ValueError):
            pricing.compute_extra_distance(Decimal("-1"), "sedan")

    # -- name sign: payload + frontend strings ----------------------------
    def test_active_trip_exposes_customer_name_and_airport_flag(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        resp = self.client.get("/api/drivers/me/active-trip",
                               headers={"X-Driver-Token": token})
        trip = resp.get_json()["booking"]
        self.assertEqual(trip["customer_name"], "Free Features Customer")
        self.assertTrue(trip["airport_pickup"])
        self.assertEqual(trip["free_waiting_minutes"], 60)

    def test_active_trip_non_airport_flag_false(self):
        _, token = self.register_driver()
        booking = self.book(pickup="100 Main Street, White Plains")
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        resp = self.client.get("/api/drivers/me/active-trip",
                               headers={"X-Driver-Token": token})
        self.assertFalse(resp.get_json()["booking"]["airport_pickup"])

    def test_name_sign_frontend_present(self):
        html = read("static/driver.html")
        self.assertIn("trip-namesign-btn", html)
        self.assertIn("Name sign", html)
        self.assertIn("namesign-overlay", html)
        self.assertIn("namesign-name", html)
        self.assertIn("namesign-close", html)
        js = read("static/js/driver.js")
        self.assertIn("namesign", js)
        self.assertIn("airport_pickup", js)
        css = read("static/css/driver.css")
        self.assertIn(".namesign-overlay", css)
        self.assertIn(".namesign-name", css)

    # -- chat --------------------------------------------------------------
    def _accepted_booking(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        return booking, token

    def test_chat_driver_and_customer_exchange(self):
        booking, token = self._accepted_booking()
        bid = booking["id"]
        resp = self.client.post(f"/api/drivers/me/trip/{bid}/messages",
                                json={"text": "I am on my way."},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["message"]["sender"], "driver")
        resp = self.client.get(f"/api/bookings/{bid}/messages",
                               query_string={"phone": booking["phone"]})
        self.assertEqual(resp.status_code, 200)
        messages = resp.get_json()["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["text"], "I am on my way.")
        resp = self.client.post(f"/api/bookings/{bid}/messages",
                                json={"phone": booking["phone"],
                                      "text": "I am at arrivals, Terminal 4."})
        self.assertEqual(resp.status_code, 201)
        resp = self.client.get(f"/api/drivers/me/trip/{bid}/messages",
                               headers={"X-Driver-Token": token})
        messages = resp.get_json()["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1]["sender"], "customer")
        self.assertEqual(messages[1]["text"], "I am at arrivals, Terminal 4.")

    def test_chat_messages_carry_no_money_fields(self):
        booking, token = self._accepted_booking()
        self.client.post(f"/api/drivers/me/trip/{booking['id']}/messages",
                         json={"text": "Hello."},
                         headers={"X-Driver-Token": token})
        resp = self.client.get(f"/api/drivers/me/trip/{booking['id']}/messages",
                               headers={"X-Driver-Token": token})
        message = resp.get_json()["messages"][0]
        # Exact shape: the original four fields plus the two additive
        # chat-translation fields (2026-11-18). Clients that ignore
        # them see the same shape as before; still no money fields.
        self.assertEqual(set(message.keys()),
                         {"id", "sender", "text", "original_text", "translated",
                          "created_at"})
        self.assertTrue(FORBIDDEN_KEYS.isdisjoint(message.keys()))

    def test_chat_requires_acceptance_and_identity(self):
        _, token = self.register_driver()
        booking = self.book()
        # Customer: no driver accepted yet.
        resp = self.client.get(f"/api/bookings/{booking['id']}/messages",
                               query_string={"phone": booking["phone"]})
        self.assertEqual(resp.status_code, 409)
        resp = self.client.post(f"/api/bookings/{booking['id']}/messages",
                                json={"phone": booking["phone"], "text": "Hi"})
        self.assertEqual(resp.status_code, 409)
        # Driver: booking not assigned to this driver.
        resp = self.client.get(f"/api/drivers/me/trip/{booking['id']}/messages",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 403)
        # After accept, wrong phone is refused.
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        resp = self.client.get(f"/api/bookings/{booking['id']}/messages",
                               query_string={"phone": "+10000000000"})
        self.assertEqual(resp.status_code, 403)
        # A different driver cannot read the trip chat.
        _, other_token = self.register_driver()
        resp = self.client.get(f"/api/drivers/me/trip/{booking['id']}/messages",
                               headers={"X-Driver-Token": other_token})
        self.assertEqual(resp.status_code, 403)

    def test_chat_text_validation(self):
        booking, token = self._accepted_booking()
        bid = booking["id"]
        resp = self.client.post(f"/api/drivers/me/trip/{bid}/messages",
                                json={"text": "   "},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(f"/api/drivers/me/trip/{bid}/messages",
                                json={"text": "x" * 501},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(f"/api/drivers/me/trip/{bid}/messages",
                                json={},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 400)

    def test_chat_frontend_present(self):
        driver_html = read("static/driver.html")
        self.assertIn("trip-chat", driver_html)
        self.assertIn("trip-chat-messages", driver_html)
        self.assertIn("trip-chat-input", driver_html)
        self.assertIn("trip-chat-send", driver_html)
        driver_js = read("static/js/driver.js")
        self.assertIn("/messages", driver_js)
        self.assertIn("chatTimer", driver_js)
        index_html = read("static/index.html")
        self.assertIn("chat-panel", index_html)
        self.assertIn("chat-messages", index_html)
        self.assertIn("chat-send", index_html)
        customer_js = read("static/js/customer.js")
        self.assertIn("loadChatIfOpen", customer_js)
        self.assertIn("/messages", customer_js)

    # -- extra distance ----------------------------------------------------
    def test_complete_with_extra_miles_updates_everything(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        self.drive_to(booking["id"], token, "start")
        resp = self.trip_event(booking["id"], token, "complete",
                               waiting_minutes=0, extra_miles=5)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        # Driver-facing complete response gains NO new money field.
        self.assertNotIn("extra_distance_charge", resp.get_json().get("invoice", {}))
        # Customer view: no invoice and no total while prices are paused.
        resp = self.client.get(f"/api/bookings/{booking['id']}")
        got = resp.get_json()["booking"]
        self.assertIsNone(got["invoice"])
        self.assertNotIn("total", got)
        # Owner breakdown: fare/driver increased; gratuity/tax stay $0.
        self.owner_login()
        resp = self.client.get(f"/api/owner/bookings/{booking['id']}")
        row = resp.get_json()
        self.assertTrue(approx(row["fare"], "207.00"))
        self.assertTrue(approx(row["gratuity"], "0.00"))
        self.assertTrue(approx(row["tax"], "0.00"))
        self.assertTrue(approx(row["driver_earnings"], "115.00"))
        self.assertTrue(approx(row["extra_distance_charge"], "45.00"))
        self.assertTrue(approx(row["extra_miles"], "5.0"))
        self.assertTrue(approx(row["profit"], "92.00"))
        self.assertTrue(approx(row["invoice"]["extra_distance_charge"], "45.00"))

    def test_complete_without_extra_miles_unchanged(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        self.drive_to(booking["id"], token, "start")
        resp = self.trip_event(booking["id"], token, "complete", waiting_minutes=0)
        self.assertEqual(resp.status_code, 200)
        self.owner_login()
        row = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertTrue(approx(row["extra_distance_charge"], "0"))
        self.assertTrue(approx(row["extra_miles"], "0"))
        self.assertTrue(approx(row["driver_earnings"], "95.00"))

    def test_extra_miles_rejected_for_hourly_and_bad_values(self):
        _, token = self.register_driver()
        booking = self.book(ride_type="hourly", hours=2, dropoff="",
                            vehicle_class="sedan")
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        self.drive_to(booking["id"], token, "start")
        resp = self.trip_event(booking["id"], token, "complete",
                               waiting_minutes=0, extra_miles=5)
        self.assertEqual(resp.status_code, 400)
        # Negative and absurd values are rejected on one-way rides.
        _, token2 = self.register_driver()
        booking2 = self.book()
        self.assertEqual(self.pay(booking2["id"]).status_code, 200)
        self.assertEqual(self.accept(booking2["id"], token2).status_code, 200)
        self.drive_to(booking2["id"], token2, "start")
        resp = self.trip_event(booking2["id"], token2, "complete",
                               waiting_minutes=0, extra_miles=-3)
        self.assertEqual(resp.status_code, 400)
        resp = self.trip_event(booking2["id"], token2, "complete",
                               waiting_minutes=0, extra_miles=501)
        self.assertEqual(resp.status_code, 400)

    def test_extra_miles_frontend_present(self):
        html = read("static/driver.html")
        self.assertIn("extra-miles-field", html)
        self.assertIn("extra-miles", html)
        js = read("static/js/driver.js")
        self.assertIn("extra_miles", js)
        self.assertIn("extra-miles-field", js)
        owner_html = read("static/owner.html")
        self.assertIn("Extra dist.", owner_html)
        owner_js = read("static/js/owner.js")
        self.assertIn("extra_distance_charge", owner_js)

    # -- dispatcher-lite ---------------------------------------------------
    def test_assign_restricts_offers_to_one_driver(self):
        driver_a, token_a = self.register_driver()
        _, token_b = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(len(self.offers(token_a)), 1)
        self.assertEqual(len(self.offers(token_b)), 1)
        self.owner_login()
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/assign",
                                json={"driver_id": driver_a["id"]})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["booking"]["assigned_driver_id"], driver_a["id"])
        self.assertEqual(resp.get_json()["booking"]["assigned_driver_name"], driver_a["name"])
        self.assertEqual(len(self.offers(token_a)), 1)
        self.assertEqual(len(self.offers(token_b)), 0)
        # The other driver cannot accept even by calling the endpoint.
        resp = self.accept(booking["id"], token_b)
        self.assertEqual(resp.status_code, 409)
        # The assigned driver can.
        resp = self.accept(booking["id"], token_a)
        self.assertEqual(resp.status_code, 200)

    def test_assign_requires_offered_status_and_owner(self):
        driver_a, _ = self.register_driver()
        booking = self.book()
        # Not paid yet: assignment rejected.
        self.owner_login()
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/assign",
                                json={"driver_id": driver_a["id"]})
        self.assertEqual(resp.status_code, 409)
        # Without the owner session: 401.
        self.client.post("/api/owner/logout")
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/assign",
                                json={"driver_id": driver_a["id"]})
        self.assertEqual(resp.status_code, 401)

    def test_assign_validates_driver_and_class(self):
        driver_a, token_a = self.register_driver()
        _, suv_token = self.register_driver("Cadillac Escalade")
        booking = self.book()  # sedan class
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.owner_login()
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/assign",
                                json={"driver_id": 99999})
        self.assertEqual(resp.status_code, 404)
        suv_driver_id = self.client.get(
            "/api/owner/drivers").get_json()
        suv_id = [d["id"] for d in suv_driver_id if d["car_model"] == "Cadillac Escalade"][0]
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/assign",
                                json={"driver_id": suv_id})
        self.assertEqual(resp.status_code, 409)
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/assign",
                                json={"driver_id": driver_a["id"]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self.offers(suv_token)), 0)
        self.assertEqual(len(self.offers(token_a)), 1)

    def test_unassign_restores_broadcast(self):
        driver_a, token_a = self.register_driver()
        _, token_b = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.owner_login()
        self.client.post(f"/api/owner/bookings/{booking['id']}/assign",
                         json={"driver_id": driver_a["id"]})
        self.assertEqual(len(self.offers(token_b)), 0)
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/assign",
                                json={"driver_id": None})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.get_json()["booking"]["assigned_driver_id"])
        self.assertEqual(len(self.offers(token_a)), 1)
        self.assertEqual(len(self.offers(token_b)), 1)

    def test_assigned_driver_decline_clears_assignment(self):
        driver_a, token_a = self.register_driver()
        _, token_b = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.owner_login()
        self.client.post(f"/api/owner/bookings/{booking['id']}/assign",
                         json={"driver_id": driver_a["id"]})
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/decline",
                                json={}, headers={"X-Driver-Token": token_a})
        self.assertEqual(resp.status_code, 200)
        # Broadcast again: the other driver sees it now.
        self.assertEqual(len(self.offers(token_b)), 1)
        self.assertEqual(len(self.offers(token_a)), 0)  # declined: excluded
        self.owner_login()
        row = self.client.get(f"/api/owner/bookings/{booking['id']}").get_json()
        self.assertIsNone(row["assigned_driver_id"])

    def test_assign_frontend_present(self):
        owner_js = read("static/js/owner.js")
        self.assertIn("/assign", owner_js)
        self.assertIn("assigned_driver_name", owner_js)
        self.assertIn("assign-box", owner_js)
        owner_css = read("static/css/owner.css")
        self.assertIn(".assign-box", owner_css)


if __name__ == "__main__":
    unittest.main()
