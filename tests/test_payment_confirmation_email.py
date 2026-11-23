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
- Receipt format (owner 2026-11-23, "ek dum professional"): a
  step-by-step receipt, every detail on its own line, labels
  aligned in one column, divider lines, the total set apart and
  bold — in plain text AND as an HTML part (same rows). No
  gradients; the only gold is the brand wordmark and the booking
  code's NC prefix.
- Receipt number (owner 2026-11-23, my professional judgment):
  NCL-<payment year>-<payment id, six digits> — unique per
  payment, different from the booking code, stable on resend.
- Booking code (owner 2026-11-23, FINAL spec — random, never
  sequential): NC-<random 6 digits>, generated once, stored on
  the booking, checked unique (regenerate on collision); one
  booking one code, never reused. The subject carries the same
  code. Receipt-only: the website, apps and dashboard keep the
  plain booking number.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
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


def receipt_lines(row):
    return row.body.split("\n")


def field_value(lines, label):
    """The value of the 'Label:' line (labels are padded to one column)."""
    for line in lines:
        if line.startswith(label + ":"):
            return line.split(":", 1)[1].strip()
    return None


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
        lines = receipt_lines(row)
        # Step-by-step, in order, every detail on its own line.
        self.assertEqual(lines[0], "Payment received — your ride is confirmed.")
        self.assertEqual(lines[1], "-" * 40)
        self.assertEqual(field_value(lines, "Pickup"), "JFK Airport")
        self.assertEqual(field_value(lines, "Drop-off"), "Times Square, New York")
        self.assertEqual(field_value(lines, "Date"),
                         "Saturday, June 1, 2030 at 12:00 PM")
        self.assertEqual(field_value(lines, "Class"), "Business Class")
        # The total is the booking's own fare_total (Blacklane
        # pricing at 18 mocked miles), not a hardcoded figure.
        with app_module.app.app_context():
            total = app_module.db.session.get(
                app_module.Booking, booking["id"]).fare_total
        self.assertEqual(field_value(lines, "Total paid"), f"${total}")
        self.assertIn("no real charge was made", row.body)
        # Labels aligned: every field value starts in the same column.
        value_col = len("Receipt No.:") + 1
        for line in lines:
            if re.match(r"^(Receipt No|Booking|Pickup|Drop-off|Date|Class|Total paid):",
                        line):
                self.assertEqual(line[value_col - 1], " ")
                self.assertNotEqual(line[value_col], " ")
        counts = outbox_counts(booking["id"])
        self.assertEqual(counts, {"email": 2, "sms": 1})

    def test_receipt_number_and_booking_code_are_separate(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json=dict(RAW_CARD))
        self.assertEqual(resp.status_code, 200)
        row = confirmation_rows(booking["id"])[0]
        lines = receipt_lines(row)
        receipt_no = field_value(lines, "Receipt No.")
        booking_code = field_value(lines, "Booking")
        self.assertRegex(receipt_no, r"^NCL-\d{4}-\d{6}$")
        self.assertRegex(booking_code, r"^NC-\d{6}$")
        self.assertNotEqual(receipt_no, booking_code)
        # The receipt number comes from the payment row, not the booking.
        with app_module.app.app_context():
            payment = app_module._latest_payment(booking["id"])
            self.assertEqual(
                receipt_no,
                f"NCL-{payment.created_at.year}-{payment.id:06d}")
        # The booking code is stored on the booking, random — never
        # the booking id in disguise.
        with app_module.app.app_context():
            stored = app_module.db.session.get(
                app_module.Booking, booking["id"]).booking_code
        self.assertEqual(stored, booking_code)
        self.assertNotEqual(booking_code, f"NC-{booking['id']:06d}")
        self.assertNotEqual(booking_code, f"NC-{booking['id']:05d}")

    def test_booking_codes_are_random_unique_and_stable(self):
        first = self.book()
        second = self.book()
        for b in (first, second):
            resp = self.client.post(f"/api/bookings/{b['id']}/pay",
                                    json=dict(RAW_CARD))
            self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        first_code = field_value(
            receipt_lines(confirmation_rows(first["id"])[0]), "Booking")
        second_code = field_value(
            receipt_lines(confirmation_rows(second["id"])[0]), "Booking")
        self.assertRegex(first_code, r"^NC-\d{6}$")
        self.assertRegex(second_code, r"^NC-\d{6}$")
        self.assertNotEqual(first_code, second_code)
        # A resend keeps the same code: calling the helper again
        # sends nothing new and the stored code is unchanged.
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, first["id"])
            app_module._send_payment_confirmation_email(row, test=True)
            app_module.db.session.commit()
        self.assertEqual(len(confirmation_rows(first["id"])), 1)
        self.assertEqual(
            field_value(receipt_lines(confirmation_rows(first["id"])[0]),
                        "Booking"),
            first_code)

    def test_legacy_prefix_row_blocks_duplicate(self):
        # A confirmation sent in the old single-paragraph format
        # still counts: re-marking the payment must not send a
        # second (new-format) confirmation.
        booking = self.book()
        with app_module.app.app_context():
            old = app_module.OutboxMessage(
                channel="email", recipient=EMAIL,
                body=(f"{app_module.LEGACY_PAYMENT_CONFIRMATION_PREFIX}"
                      f"{booking['id']}. Your ride is confirmed."),
                booking_id=booking["id"])
            app_module.db.session.add(old)
            app_module.db.session.commit()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json=dict(RAW_CARD))
        self.assertEqual(resp.status_code, 200)
        # No NEW-format confirmation row was created; the only
        # email rows are the booking-received one and the legacy
        # confirmation that was already there.
        self.assertEqual(confirmation_rows(booking["id"]), [])
        with app_module.app.app_context():
            emails = (app_module.OutboxMessage.query
                      .filter_by(channel="email", booking_id=booking["id"])
                      .all())
        self.assertEqual(len(emails), 2)
        self.assertTrue(any(
            r.body.startswith(app_module.LEGACY_PAYMENT_CONFIRMATION_PREFIX)
            for r in emails))

    def test_html_receipt_is_professional(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay",
                                json=dict(RAW_CARD))
        self.assertEqual(resp.status_code, 200)
        row = confirmation_rows(booking["id"])[0]
        html = row.html_body
        self.assertIsNotNone(html)
        lines = receipt_lines(row)
        booking_code = field_value(lines, "Booking")
        receipt_no = field_value(lines, "Receipt No.")
        # Same facts as the plain text (the booking code is split
        # by its gold NC span in the HTML).
        self.assertIn("JFK Airport", html)
        self.assertIn("Times Square, New York", html)
        self.assertIn("Saturday, June 1, 2030 at 12:00 PM", html)
        self.assertIn(receipt_no, html)
        self.assertIn(
            '<span style="color:#D4AF37;font-weight:bold;">NC</span>-'
            + booking_code.split("-", 1)[1], html)
        self.assertIn("no real charge was made", html)
        # Professional layout: letterhead, heading, divider, table.
        self.assertIn("Noel", html)
        self.assertIn("<h1", html)
        self.assertIn("<hr", html)
        self.assertIn("<table", html)
        self.assertIn("<strong>$", html)  # total set apart and bold
        # No gradients anywhere; gold only on the brand wordmark
        # and the booking code's NC prefix.
        self.assertNotIn("linear-gradient", html)
        self.assertNotIn("radial-gradient", html)
        self.assertIn(
            '<span style="color:#D4AF37;font-weight:bold;">NC</span>-'
            + booking_code.split("-", 1)[1], html)
        self.assertIn(
            '<span style="color:#D4AF37;">Chauffeur</span>', html)
        self.assertEqual(html.count("#D4AF37"), 2)

    def test_hourly_receipt_has_hours_line_and_no_dropoff(self):
        # Hourly rides have no drop-off; the hours stay on their own line.
        with app_module.app.app_context():
            booking = app_module.Booking(
                customer_name="Hourly Tester", phone="+15550140099",
                email=EMAIL, pickup="Times Square, New York",
                dropoff="", date="2030-06-01", time="12:00",
                ride_type="hourly", hours=2, vehicle_class="sedan",
                fare_total="218.32", driver_earnings=0,
                status="awaiting_payment")
            app_module.db.session.add(booking)
            app_module.db.session.commit()
            text = app_module.payment_confirmation_text(booking, test=True)
            html = app_module.payment_confirmation_html(booking, test=True)
        lines = text.split("\n")
        self.assertEqual(field_value(lines, "Hours"), "2 hours")
        self.assertNotIn("Drop-off:", text)
        self.assertIn("Hours", html)
        self.assertIn("2 hours", html)
        self.assertNotIn("Drop-off", html)

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
        # The subject carries the booking's random NC code (plain
        # text — no colour there), the same code as the receipt body.
        row = confirmation_rows(booking["id"])[0]
        code = field_value(receipt_lines(row), "Booking")
        self.assertRegex(code, r"^NC-\d{6}$")
        self.assertIn(f"(booking {code})", payment_calls[0].args[1])
        # The HTML part travelled with the send call — the code is
        # there with its NC prefix in the gold span.
        self.assertIn("html", payment_calls[0].kwargs)
        self.assertIn(
            '<span style="color:#D4AF37;font-weight:bold;">NC</span>-'
            + code.split("-", 1)[1], payment_calls[0].kwargs["html"])

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
        self.assertEqual(field_value(receipt_lines(row), "Total paid"),
                         f"${total}")
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
