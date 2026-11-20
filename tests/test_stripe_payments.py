"""Tests for Uber-like live Stripe payments (owner decision 2026-11-20,
"Uber jaisa bana do").

Live path (fake Stripe backend, tests/stripe_fake.py — no network, no
keys, no real charge):
- /pay authorizes a hold (PaymentIntent, manual capture) with a
  Stripe.js PaymentMethod id; raw card numbers are rejected.
- Saved cards (Stripe Customer + PaymentMethod; brand/last4 only).
- 3-D Secure: requires_action -> /pay/confirm -> authorized.
- Ride end captures the final fare automatically; a final fare above
  the hold is topped up off-session; free cancel releases the hold;
  late cancel / no-show captures the full fare.
- Driver payout setup (Connect onboarding link; bank details go to
  Stripe only) and instant cash-out at 1.5% to a linked debit card.
- Bank routing + account numbers are COMPULSORY and validated
  (owner decision 2026-11-20): a driver cannot complete payout setup
  — or receive a weekly payout — without a valid pair.

Test mode (no Stripe keys configured — the live path is BLOCKED while
the merchant Stripe account is disabled): the pre-existing fake
authorization keeps bookings working, exactly as before this build.

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
_tmpdir = tempfile.mkdtemp(prefix="noel-stripe-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "stripe.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "stripe-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
# No STRIPE_* keys here on purpose: the live-path tests install the
# fake, the test-mode tests assert the unconfigured behaviour.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles: total $162.00,
# driver $95.00 (10-20 slab).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
import stripe_fake  # noqa: E402

PM = "pm_test_4242"
PM_DECLINE = "pm_test_decline"
PM_ACTION = "pm_test_action"
RAW_CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Stripe Customer"}


def approx(a, b):
    return a is not None and abs(float(a) - float(b)) < 0.005


# These tests pin the legacy $9/$10 totals as fixtures (the Stripe
# authorize/capture mechanics are engine-independent); the live
# engine is Blacklane by default since the owner flip (2026-11-20).
@mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"})
class StripeLiveCase(unittest.TestCase):
    """Live path with the fake Stripe backend installed."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0
        stripe_fake.install()
        stripe_fake.reset()

    def tearDown(self):
        stripe_fake.reset()
        stripe_fake.uninstall()

    # -- helpers ---------------------------------------------------------
    def register_driver(self, **overrides):
        self._driver_seq += 1
        phone = f"+1555011{self._driver_seq:04d}"
        data = {
            "name": f"Stripe Driver {self._driver_seq}", "phone": phone,
            "email": f"sd{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"S{self._driver_seq:05d}",
            "state": "New York", "bank_account_number": "123456789",
            "bank_routing_number": "021000021",
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
        }
        data.update(overrides)
        resp = self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")
        return resp

    def register_driver_ok(self):
        resp = self.register_driver()
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Stripe Customer",
            "phone": f"+1555012{self._phone_seq:04d}",
            "email": "stripe@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id, **body):
        return self.client.post(f"/api/bookings/{booking_id}/pay",
                                json=body or {"payment_method_id": PM})

    def phone_of(self, booking_id):
        with app_module.app.app_context():
            return app_module.db.session.get(
                app_module.Booking, booking_id).phone

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)

    def owner_detail(self, booking_id):
        self.owner_login()
        return self.client.get(f"/api/owner/bookings/{booking_id}").get_json()

    def drive_to_completed(self, token, booking_id, waiting_minutes=0,
                           extra_miles=None):
        self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                         headers={"X-Driver-Token": token})
        for event in ("en_route", "arrived", "start"):
            resp = self.client.post(
                f"/api/drivers/me/trip/{booking_id}/event",
                json={"event": event}, headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")
        payload = {"event": "complete", "waiting_minutes": waiting_minutes}
        if extra_miles is not None:
            payload["extra_miles"] = extra_miles
        resp = self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                json=payload, headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200,
                         f"complete: {resp.get_data(as_text=True)[:200]}")
        return resp.get_json()

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

    # -- publishable key --------------------------------------------------
    def test_publishable_key_configured_with_fake(self):
        resp = self.client.get("/api/stripe/publishable-key")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIs(body["configured"], True)
        self.assertEqual(body["publishable_key"], "pk_test_fake")

    # -- /pay live path -----------------------------------------------------
    def test_pay_authorizes_hold_and_saves_card(self):
        booking = self.book()
        resp = self.pay(booking["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:300])
        body = resp.get_json()
        payment = body["payment"]
        self.assertEqual(payment["status"], "authorized")
        self.assertIs(payment["test"], False)
        self.assertEqual(payment["last4"], "4242")
        self.assertEqual(payment["brand"], "visa")
        self.assertTrue(payment["stripe_payment_intent_id"].startswith("pi_fake_"))
        self.assertTrue(approx(payment["amount"], "162.00"))
        self.assertEqual(body["booking"]["status"], "offered")
        self.assertIsNotNone(body["saved_card"])
        self.assertEqual(body["saved_card"]["last4"], "4242")
        # Saved card is listed for this phone.
        cards = self.client.get("/api/customers/cards",
                                query_string={"phone": self.phone_of(booking["id"])}).get_json()["cards"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["last4"], "4242")

    def test_pay_without_save_card_does_not_save(self):
        booking = self.book()
        resp = self.pay(booking["id"], payment_method_id=PM, save_card=False)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.get_json()["saved_card"])
        cards = self.client.get("/api/customers/cards",
                                query_string={"phone": self.phone_of(booking["id"])}).get_json()["cards"]
        self.assertEqual(cards, [])

    def test_pay_same_card_twice_saves_once(self):
        b1 = self.book()
        self.assertEqual(self.pay(b1["id"]).status_code, 200)
        phone = self.phone_of(b1["id"])
        # Same customer, same card, second booking: the saved-card
        # row must be reused, never re-inserted (unique constraint).
        b2 = self.book(phone=phone)
        resp = self.pay(b2["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        cards = self.client.get("/api/customers/cards",
                                query_string={"phone": phone}).get_json()["cards"]
        self.assertEqual(len(cards), 1)

    def test_pay_with_saved_card(self):
        b1 = self.book()
        self.assertEqual(self.pay(b1["id"]).status_code, 200)
        phone = self.phone_of(b1["id"])
        card_id = self.client.get("/api/customers/cards",
                                  query_string={"phone": phone}).get_json()["cards"][0]["id"]
        b2 = self.book(phone=phone)
        resp = self.pay(b2["id"], saved_card_id=card_id)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["payment"]["status"], "authorized")

    def test_pay_saved_card_wrong_phone_rejected(self):
        b1 = self.book()
        self.assertEqual(self.pay(b1["id"]).status_code, 200)
        card_id = self.client.get(
            "/api/customers/cards",
            query_string={"phone": self.phone_of(b1["id"])}).get_json()["cards"][0]["id"]
        b2 = self.book()
        resp = self.pay(b2["id"], saved_card_id=card_id)
        self.assertEqual(resp.status_code, 404)

    def test_pay_rejects_raw_card_numbers(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay", json=dict(RAW_CARD))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("secure card form", resp.get_json()["error"])
        got = self.client.get(f"/api/bookings/{booking['id']}").get_json()["booking"]
        self.assertEqual(got["status"], "awaiting_payment")

    def test_pay_rejects_bad_payment_method(self):
        booking = self.book()
        resp = self.pay(booking["id"], payment_method_id="not-a-pm")
        self.assertEqual(resp.status_code, 400)
        resp = self.pay(booking["id"])
        self.assertEqual(resp.status_code, 200)

    def test_pay_declined_keeps_booking_unpaid(self):
        booking = self.book()
        resp = self.pay(booking["id"], payment_method_id=PM_DECLINE)
        self.assertEqual(resp.status_code, 502)
        self.assertIn("declined", resp.get_json()["error"])
        got = self.client.get(f"/api/bookings/{booking['id']}").get_json()["booking"]
        self.assertEqual(got["status"], "awaiting_payment")
        # A good card still works afterwards.
        resp = self.pay(booking["id"])
        self.assertEqual(resp.status_code, 200)

    def test_pay_requires_action_then_confirm(self):
        booking = self.book()
        resp = self.pay(booking["id"], payment_method_id=PM_ACTION)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIs(body["needs_action"], True)
        self.assertTrue(body["client_secret"].endswith("_secret"))
        self.assertEqual(body["booking"]["status"], "awaiting_payment")
        pi_id = body["payment_intent_id"]
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay/confirm",
                                json={"payment_intent_id": pi_id})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertEqual(body["payment"]["status"], "authorized")
        self.assertEqual(body["booking"]["status"], "offered")

    def test_pay_confirm_wrong_booking_rejected(self):
        b1 = self.book()
        resp = self.pay(b1["id"], payment_method_id=PM_ACTION)
        pi_id = resp.get_json()["payment_intent_id"]
        b2 = self.book()
        resp = self.client.post(f"/api/bookings/{b2['id']}/pay/confirm",
                                json={"payment_intent_id": pi_id})
        self.assertEqual(resp.status_code, 409)

    def test_double_pay_rejected_live(self):
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.pay(booking["id"])
        self.assertEqual(resp.status_code, 409)

    # -- saved cards ---------------------------------------------------------
    def test_save_list_delete_card(self):
        phone = "+15550129999"
        resp = self.client.post("/api/customers/cards",
                                json={"phone": phone, "payment_method_id": PM})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        card = resp.get_json()["card"]
        self.assertEqual(card["brand"], "visa")
        self.assertEqual(card["last4"], "4242")
        # Saving the same card again is idempotent.
        resp = self.client.post("/api/customers/cards",
                                json={"phone": phone, "payment_method_id": PM})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["card"]["id"], card["id"])
        resp = self.client.delete(f"/api/customers/cards/{card['id']}",
                                  query_string={"phone": phone})
        self.assertEqual(resp.status_code, 200)
        cards = self.client.get("/api/customers/cards",
                                query_string={"phone": phone}).get_json()["cards"]
        self.assertEqual(cards, [])

    def test_delete_card_wrong_phone_rejected(self):
        phone = "+15550129998"
        resp = self.client.post("/api/customers/cards",
                                json={"phone": phone, "payment_method_id": PM})
        card_id = resp.get_json()["card"]["id"]
        resp = self.client.delete(f"/api/customers/cards/{card_id}",
                                  query_string={"phone": "+15550120000"})
        self.assertEqual(resp.status_code, 404)

    # -- capture at ride end ---------------------------------------------------
    def test_complete_captures_final_fare(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.drive_to_completed(token, booking["id"], waiting_minutes=0)
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["status"], "completed")
        payment = detail["payments"][0]
        self.assertEqual(payment["status"], "captured")
        self.assertTrue(approx(payment["captured_amount"], "162.00"))
        self.assertTrue(approx(payment["amount"], "162.00"))

    def test_complete_above_hold_tops_up(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        # 75 waiting minutes = $15 waiting on top of the $162 hold.
        self.drive_to_completed(token, booking["id"], waiting_minutes=75)
        detail = self.owner_detail(booking["id"])
        payment = detail["payments"][0]
        self.assertEqual(payment["status"], "captured")
        self.assertTrue(approx(payment["captured_amount"], "177.00"), payment)

    def test_complete_with_extra_miles_tops_up(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.drive_to_completed(token, booking["id"], extra_miles=2)
        detail = self.owner_detail(booking["id"])
        payment = detail["payments"][0]
        self.assertEqual(payment["status"], "captured")
        # 2 extra miles at $9/mi = $18 over the $162 hold.
        self.assertTrue(approx(payment["captured_amount"], "180.00"), payment)

    def test_partial_capture_below_hold(self):
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        with app_module.app.app_context():
            b = app_module.db.session.get(app_module.Booking, booking["id"])
            ok, note = app_module._settle_booking_payment(b, "100.00")
            app_module.db.session.commit()
        self.assertIs(ok, True)
        detail = self.owner_detail(booking["id"])
        payment = detail["payments"][0]
        self.assertEqual(payment["status"], "captured")
        self.assertTrue(approx(payment["captured_amount"], "100.00"), payment)

    # -- cancel / no-show --------------------------------------------------------
    def test_free_cancel_releases_hold_live(self):
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": self.phone_of(booking["id"])})
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.get_json()["refund"], True)
        self.assertIs(resp.get_json()["refund_pending"], False)
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["payments"][0]["status"], "refunded")

    def test_late_cancel_captures_full_fare_live(self):
        try:
            from zoneinfo import ZoneInfo
            soon = datetime.now(ZoneInfo("America/New_York")) + timedelta(minutes=30)
        except Exception:
            soon = datetime.now(timezone.utc) + timedelta(minutes=30)
        booking = self.book(date=soon.strftime("%Y-%m-%d"),
                            time=soon.strftime("%H:%M"))
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": self.phone_of(booking["id"])})
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.get_json()["refund"], False)
        self.assertIs(resp.get_json()["charge_kept"], True)
        detail = self.owner_detail(booking["id"])
        payment = detail["payments"][0]
        self.assertEqual(payment["status"], "captured")
        self.assertTrue(approx(payment["captured_amount"], "162.00"), payment)

    def test_no_show_captures_full_fare_live(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                         headers={"X-Driver-Token": token})
        self.move_pickup(booking["id"], 120)  # pickup 2 hours ago
        for event in ("en_route", "arrived", "no_show"):
            resp = self.client.post(
                f"/api/drivers/me/trip/{booking['id']}/event",
                json={"event": event}, headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["status"], "no_show")
        payment = detail["payments"][0]
        self.assertEqual(payment["status"], "captured")
        self.assertTrue(approx(payment["captured_amount"], "162.00"), payment)

    def test_driver_cancel_keeps_hold_live(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                         headers={"X-Driver-Token": token})
        resp = self.client.post(f"/api/drivers/me/trip/{booking['id']}/event",
                                json={"event": "cancel"},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["payments"][0]["status"], "authorized")

    # -- bank validation (compulsory routing + account) -------------------------
    def test_register_rejects_bad_routing_checksum(self):
        resp = self.register_driver(bank_routing_number="123456789")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Routing number", resp.get_json()["error"])

    def test_register_rejects_short_routing(self):
        resp = self.register_driver(bank_routing_number="02100")
        self.assertEqual(resp.status_code, 400)

    def test_register_rejects_bad_account_number(self):
        resp = self.register_driver(bank_account_number="12AB")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Bank account number", resp.get_json()["error"])

    def test_register_rejects_missing_bank_fields(self):
        resp = self.register_driver(bank_account_number="")
        self.assertEqual(resp.status_code, 400)
        resp = self.register_driver(bank_routing_number="")
        self.assertEqual(resp.status_code, 400)

    # -- driver payout setup + instant payout ------------------------------------
    def test_payout_setup_status_before_onboarding(self):
        _, token = self.register_driver_ok()
        resp = self.client.get("/api/drivers/me/payout-setup",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIs(body["connect_account"], False)
        self.assertIs(body["bank_on_file"], True)
        self.assertEqual(body["bank_masked"], "••••6789")
        self.assertIs(body["weekly_payout_available"], True)
        self.assertIs(body["instant_payout_available"], False)
        self.assertIs(body["debit_card_linked"], False)
        self.assertTrue(approx(body["instant_payout_fee_rate"], "0.015"))

    def test_payout_setup_onboarding_link(self):
        _, token = self.register_driver_ok()
        resp = self.client.post("/api/drivers/me/payout-setup",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertIn("connect.stripe.com", body["onboarding_url"])
        self.assertIs(body["connect_account"], True)
        # After onboarding the fake reports payouts enabled + a debit card.
        resp = self.client.get("/api/drivers/me/payout-setup",
                               headers={"X-Driver-Token": token})
        body = resp.get_json()
        self.assertIs(body["payouts_enabled"], True)
        self.assertIs(body["debit_card_linked"], True)
        self.assertEqual(body["debit_cards"][0]["last4"], "9876")
        self.assertIs(body["instant_payout_available"], True)

    def test_payout_link_card(self):
        _, token = self.register_driver_ok()
        resp = self.client.post("/api/drivers/me/payout-setup/link-card",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("connect.stripe.com", resp.get_json()["onboarding_url"])

    def test_instant_payout_no_earnings(self):
        _, token = self.register_driver_ok()
        self.client.post("/api/drivers/me/payout-setup",
                         headers={"X-Driver-Token": token})
        resp = self.client.post("/api/drivers/me/instant-payout",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("No unpaid earnings", resp.get_json()["error"])

    def test_instant_payout_happy_path(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.drive_to_completed(token, booking["id"], waiting_minutes=0)
        self.client.post("/api/drivers/me/payout-setup",
                         headers={"X-Driver-Token": token})
        resp = self.client.post("/api/drivers/me/instant-payout",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:300])
        body = resp.get_json()
        payout = body["instant_payout"]
        # Driver earnings $95.00 (10-20 slab); 1.5% fee $1.43; driver receives $93.57.
        self.assertTrue(approx(payout["amount"], "95.00"), payout)
        self.assertTrue(approx(payout["fee"], "1.43"), payout)
        self.assertTrue(approx(payout["net"], "93.57"), payout)
        self.assertTrue(approx(body["driver_receives"], "93.57"))
        self.assertEqual(payout["booking_ids"], [booking["id"]])
        # The ride is marked paid, so the weekly cycle never pays twice.
        earnings = self.client.get("/api/drivers/me/earnings",
                                   headers={"X-Driver-Token": token}).get_json()
        self.assertIs(earnings["rides"][0]["payout_paid"], True)
        # A second cash-out finds nothing left.
        resp = self.client.post("/api/drivers/me/instant-payout",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 409)

    def test_instant_payout_needs_debit_card(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.drive_to_completed(token, booking["id"], waiting_minutes=0)
        self.client.post("/api/drivers/me/payout-setup",
                         headers={"X-Driver-Token": token})
        stripe_fake.DEBIT_CARD_LINKED = False
        resp = self.client.post("/api/drivers/me/instant-payout",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("debit card", resp.get_json()["error"])

    def test_instant_payout_needs_payouts_enabled(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.drive_to_completed(token, booking["id"], waiting_minutes=0)
        self.client.post("/api/drivers/me/payout-setup",
                         headers={"X-Driver-Token": token})
        stripe_fake.CONNECT_PAYOUTS_ENABLED = False
        resp = self.client.post("/api/drivers/me/instant-payout",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("not enabled", resp.get_json()["error"])

    def test_instant_payout_failure_marks_nothing_paid(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.drive_to_completed(token, booking["id"], waiting_minutes=0)
        self.client.post("/api/drivers/me/payout-setup",
                         headers={"X-Driver-Token": token})
        stripe_fake.PAYOUT_FAIL = True
        resp = self.client.post("/api/drivers/me/instant-payout",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 502)
        earnings = self.client.get("/api/drivers/me/earnings",
                                   headers={"X-Driver-Token": token}).get_json()
        self.assertIs(earnings["rides"][0]["payout_paid"], False)

    def test_instant_payout_needs_setup_first(self):
        _, token = self.register_driver_ok()
        resp = self.client.post("/api/drivers/me/instant-payout",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("Set up payouts", resp.get_json()["error"])

    # -- weekly payout gate ---------------------------------------------------------
    def test_mark_paid_blocked_without_bank(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.drive_to_completed(token, booking["id"], waiting_minutes=0)
        # Strip the driver's bank details: payout setup is incomplete.
        with app_module.app.app_context():
            driver = app_module.Driver.query.filter_by(token=token).first()
            driver.bank_encrypted = None
            driver.bank_last4 = None
            app_module.db.session.commit()
            driver_id = driver.id
        self.owner_login()
        resp = self.client.post("/api/owner/payouts/mark-paid",
                                json={"driver_id": driver_id, "week_index": 0})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("payout setup", resp.get_json()["error"])

    def test_mark_paid_allowed_with_bank(self):
        _, token = self.register_driver_ok()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.drive_to_completed(token, booking["id"], waiting_minutes=0)
        with app_module.app.app_context():
            driver = app_module.Driver.query.filter_by(token=token).first()
            driver_id = driver.id
        self.owner_login()
        resp = self.client.post("/api/owner/payouts/mark-paid",
                                json={"driver_id": driver_id, "week_index": 0})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])


class StripeTestModeCase(unittest.TestCase):
    """No Stripe keys configured: the pre-existing test-mode fake
    authorization keeps bookings working (live activation is BLOCKED
    while the merchant Stripe account is disabled)."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    def book(self):
        self._phone_seq += 1
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Test Customer",
            "phone": f"+1555013{self._phone_seq:04d}",
            "email": "testmode@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way"})
        self.assertEqual(resp.status_code, 201)
        return resp.get_json()["booking"]

    def test_publishable_key_reports_test_mode(self):
        resp = self.client.get("/api/stripe/publishable-key")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIs(body["configured"], False)
        self.assertIs(body["test_mode"], True)
        self.assertIsNone(body["publishable_key"])

    def test_pay_test_mode_still_works(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json=dict(RAW_CARD))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertIs(body["test_mode"], True)
        payment = body["payment"]
        self.assertEqual(payment["status"], "succeeded")
        self.assertIs(payment["test"], True)
        self.assertEqual(payment["last4"], "4242")
        self.assertEqual(body["booking"]["status"], "offered")

    def test_pay_test_mode_validation(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json={"card_number": "4242424242424242"})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json={**RAW_CARD, "card_number": "123"})
        self.assertEqual(resp.status_code, 400)

    def test_payout_setup_unconfigured(self):
        # No driver token: 401 comes before the Stripe check.
        resp = self.client.post("/api/drivers/me/payout-setup")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
