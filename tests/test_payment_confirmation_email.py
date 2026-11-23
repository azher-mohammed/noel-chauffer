"""Tests for the payment confirmation email (owner decision, voice call
2026-11-23 ~02:45 EST, "abhi filhaal email pe karna" — EMAIL ONLY for
now, no SMS).

The bug the owner reported ("aisa kuch bhi nahi aa raha"): when a
customer paid, NO confirmation arrived anywhere. Payment success —
test mode and the live authorize path — recorded the Payment row and
the "payment_received" event and sent the booking to drivers, but
queued no email at all. Only the earlier "booking received" message
(telling the customer to complete payment) ever went out.

Rules pinned here:
- On a successful payment (test-mode /pay, live /pay, live
  /pay/confirm after 3-D Secure), exactly ONE confirmation email is
  queued to the customer's booking email (from support@noelchauffer.com
  via the existing Resend path), with pickup, drop-off, date/time,
  class and total paid. Only facts already on the booking.
- The payment adds NO SMS row: SMS stays outbox-only and the owner
  deferred all SMS work.
- Idempotent: marking the same booking paid again (helper called
  twice, or a second /pay) sends no second confirmation email.
- A declined / failed payment sends no confirmation email.
- Test-mode emails say so ("no real charge was made"); live ones do
  not.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-pay-confirm-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "payconfirm-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
# No STRIPE_* keys here on purpose: the test-mode case asserts the
# unconfigured behaviour; the live case installs the fake.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (Blacklane
# pricing applies; the tests read the booking's own fare_total
# rather than hardcoding a total).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import stripe_fake  # noqa: E402

PM = "pm_test_4242"
PM_ACTION = "pm_test_action"
PM_DECLINE = "pm_test_decline"
RAW_CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Pay Confirm Tester"}
EMAIL = "payconfirm@test.com"


def confirmation_rows(booking_id):
    """Email outbox rows for a booking that are payment confirmations."""
    with app_module.app.app_context():
        return (app_module.OutboxMessage.query
                .filter_by(channel="email", booking_id=booking_id)
                .filter(app_module.OutboxMessage.body.startswith(
                    app_module.PAYMENT_CONFIRMATION_PREFIX))
                .order_by(app_module.OutboxMessage.id).all())


def outbox_counts(booking_id):
    with app_module.app.app_context():
        rows = (app_module.OutboxMessage.query
                .filter_by(booking_id=booking_id).all())
        return {"email": sum(1 for r in rows if r.channel == "email"),
                "sms": sum(1 for r in rows if r.channel == "sms")}


class _BaseCase(unittest.TestCase):
    def signin(self, email, phone):
        """Compulsory customer sign-in (owner 2026-11-22): payment
        needs a sign-in with the booking's email."""
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def book(self):
        self._phone_seq += 1
        phone = f"+1555014{self._phone_seq:04d}"
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Pay Confirm Customer",
            "phone": phone,
            "email": EMAIL,
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way"})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        self.signin(EMAIL, phone)
        return resp.get_json()["booking"]


class PaymentConfirmationTestModeCase(_BaseCase):
    """No Stripe keys configured: the pre-existing test-mode fake
    authorization keeps bookings working."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._phone_seq = 0

    def test_pay_sends_exactly_one_confirmation_email(self):
        booking = self.book()
        # Booking creation already queued one email + one SMS
        # ("booking received"); the payment must add exactly one
        # email and no SMS.
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json=dict(RAW_CARD))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertIs(resp.get_json()["test_mode"], True)
        self.assertEqual(resp.get_json()["booking"]["status"], "offered")
        rows = confirmation_rows(booking["id"])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.recipient, EMAIL)
        self.assertIn("JFK Airport", row.body)
        self.assertIn("Times Square, New York", row.body)
        self.assertIn("2030-06-01", row.body)
        self.assertIn("12:00", row.body)
        self.assertIn("Business Class", row.body)
        # The total is the booking's own fare_total (Blacklane
        # pricing at 18 mocked miles), not a hardcoded figure.
        with app_module.app.app_context():
            total = app_module.db.session.get(
                app_module.Booking, booking["id"]).fare_total
        self.assertIn(f"Total paid: ${total}", row.body)
        self.assertIn("no real charge was made", row.body)
        counts = outbox_counts(booking["id"])
        self.assertEqual(counts, {"email": 2, "sms": 1})

    def test_confirmation_email_subject(self):
        booking = self.book()
        with mock.patch.object(app_module, "send_email",
                               return_value="sent") as fake_send:
            resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                    json=dict(RAW_CARD))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        payment_calls = [c for c in fake_send.call_args_list
                         if c.args[0] == EMAIL
                         and "payment received" in c.args[1]]
        self.assertEqual(len(payment_calls), 1)
        self.assertIn("booking #%d" % booking["id"], payment_calls[0].args[1])

    def test_second_pay_and_second_helper_call_send_no_duplicate(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json=dict(RAW_CARD))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(confirmation_rows(booking["id"])), 1)
        # A second /pay is rejected (no longer awaiting_payment).
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json=dict(RAW_CARD))
        self.assertEqual(resp.status_code, 409)
        # Calling the helper again directly also sends nothing.
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            app_module._send_payment_confirmation_email(row, test=True)
            app_module.db.session.commit()
        self.assertEqual(len(confirmation_rows(booking["id"])), 1)

    def test_failed_pay_sends_no_confirmation(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json={"card_number": "4242424242424242"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(confirmation_rows(booking["id"]), [])


class PaymentConfirmationLiveCase(_BaseCase):
    """Live path with the fake Stripe backend installed."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._phone_seq = 0
        stripe_fake.install()
        stripe_fake.reset()

    def tearDown(self):
        stripe_fake.reset()
        stripe_fake.uninstall()

    def test_live_pay_sends_confirmation_email_no_sms(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json={"payment_method_id": PM})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["payment"]["status"], "authorized")
        rows = confirmation_rows(booking["id"])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.recipient, EMAIL)
        with app_module.app.app_context():
            total = app_module.db.session.get(
                app_module.Booking, booking["id"]).fare_total
        self.assertIn(f"Total paid: ${total}", row.body)
        self.assertIn("Business Class", row.body)
        self.assertNotIn("no real charge", row.body)
        counts = outbox_counts(booking["id"])
        self.assertEqual(counts, {"email": 2, "sms": 1})

    def test_live_pay_confirm_after_3ds_sends_confirmation_once(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json={"payment_method_id": PM_ACTION})
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.get_json()["needs_action"], True)
        # No confirmation yet: the hold is NOT in place.
        self.assertEqual(confirmation_rows(booking["id"]), [])
        pi_id = resp.get_json()["payment_intent_id"]
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay/confirm",
                                json={"payment_intent_id": pi_id})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["payment"]["status"], "authorized")
        self.assertEqual(len(confirmation_rows(booking["id"])), 1)

    def test_live_declined_pay_sends_no_confirmation(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json={"payment_method_id": PM_DECLINE})
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(confirmation_rows(booking["id"]), [])


if __name__ == "__main__":
    unittest.main()
