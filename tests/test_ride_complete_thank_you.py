"""Tests for the ride-complete thank-you email.

Owner order (2026-11-25 ~22:31 EST, voice call — he said "Yes" to
sending it by email, separate mail): when a ride completes, the
customer gets a short thank-you note — "Thanks again, please ride
with us again."

Before this build, completion only queued an SMS — "Noel Chauffer:
thank you for riding with us. Your ride is complete." — and SMS
never reaches a phone (outbox-only, Resend is email-only), so the
thank-you effectively never reached the customer. The email is the
note the customer actually receives.

Rules pinned here:
- The EMAIL (plain text AND its HTML part) carries the heading
  "Thank you for riding with us." and the line "Thanks again,
  please ride with us again." — the owner's words. Nothing else:
  no amounts, no booking details, no links, no referral text.
- The HTML follows the same professional layout as the receipt /
  chauffeur / booking-received emails: Noel Chauffer letterhead
  ("Noel " + gold "Chauffeur"), heading, the thank-you line.
- The SMS stays BYTE-IDENTICAL. The subject stays the default
  "Noel Chauffer". The sender stays the Resend default
  (info@noelchauffer.com since 2026-11-23).
- The invoice email, receipt email, chauffeur email and
  booking-received email are untouched: completion adds no
  receipt/invoice row.
- It fires on every completed ride — one-way and hourly (the
  completion branch is shared).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------

_tmpdir = tempfile.mkdtemp(prefix="noel-chauffeur-ride-complete-thank-you-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "ride-complete-thank-you.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "ride-complete-thank-you-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import email_sender as email_sender_module  # noqa: E402
import photo_factory  # noqa: E402

SMS_THANK_YOU = ("Noel Chauffer: thank you for riding with us. "
                 "Your ride is complete.")
THANK_YOU_LINE = "Thanks again, please ride with us again."


class RideCompleteThankYouCase(unittest.TestCase):
    """In-process API tests with a fresh DB per test."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        # Capture every attempted Resend send (subject + body), so the
        # default subject can be pinned without a real send.
        self._send_mock = mock.MagicMock(return_value="sent")
        self._send_patch = mock.patch.object(
            app_module, "send_email", self._send_mock)
        self._send_patch.start()
        self.addCleanup(self._send_patch.stop)

    # -- helpers ---------------------------------------------------------

    def register_driver(self):
        self._driver_seq += 1
        phone = f"+1555000{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Test Driver {self._driver_seq}", "phone": phone,
            "email": f"d{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"T{self._driver_seq:05d}",
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
        needs a sign-in with the booking's email."""
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def create_and_pay(self, token, ride_type="one_way", hours=None):
        payload = {
            "customer_name": "Thank You Customer", "phone": "+15550009999",
            "email": "cust@test.com", "pickup": "JFK Airport",
            "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": ride_type,
        }
        if ride_type == "hourly":
            payload["hours"] = hours
            payload["vehicle_class"] = "sedan"
            payload.pop("dropoff")
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking_id = resp.get_json()["booking"]["id"]
        # Payment comes BEFORE dispatch: pay first, then the driver
        # accepts, then the trip runs stage by stage.
        self.signin(payload["email"], payload["phone"])
        resp = self.client.post(f"/api/bookings/{booking_id}/pay", json={
            "card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Thank You Customer"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return booking_id

    def drive_to(self, token, booking_id, *events):
        for event in events:
            resp = self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                    json={"event": event},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")

    def outbox_rows(self, booking_id, channel=None):
        with app_module.app.app_context():
            query = app_module.OutboxMessage.query.filter_by(booking_id=booking_id)
            if channel:
                query = query.filter_by(channel=channel)
            return query.all()

    def complete_ride(self, token, ride_type="one_way", hours=None):
        """Book, pay, accept and drive a ride to completion; returns
        (booking_id, rows added by the complete event alone)."""
        booking_id = self.create_and_pay(token, ride_type, hours)
        self.drive_to(token, booking_id, "en_route", "arrived", "start")
        before = {(r.channel, r.body) for r in self.outbox_rows(booking_id)}
        self.drive_to(token, booking_id, "complete")
        after = self.outbox_rows(booking_id)
        new_rows = [r for r in after if (r.channel, r.body) not in before]
        return booking_id, new_rows

    # -- the builders ------------------------------------------------------

    def test_builders_carry_only_the_thank_you(self):
        text = app_module.ride_complete_thank_you_text()
        self.assertEqual(text, "Thank you for riding with us.\n\n"
                               "Thanks again, please ride with us again.")
        html = app_module.ride_complete_thank_you_html()
        self.assertIn("Noel ", html)
        self.assertIn('<span style="color:#D4AF37;">Chauffeur</span>', html)
        self.assertIn("Thank you for riding with us.", html)
        self.assertIn(THANK_YOU_LINE, html)
        # Nothing else: no amounts, no booking details, no links.
        for blob in (text, html):
            self.assertNotIn("$", blob)
            self.assertNotIn("http", blob)
            self.assertNotIn("NC-", blob)
            self.assertNotIn("NCL-", blob)

    # -- the real driver flow ----------------------------------------------

    def test_completion_sends_thank_you_email_one_way(self):
        _driver, token = self.register_driver()
        booking_id, new_rows = self.complete_ride(token)
        # The complete event adds exactly one SMS + one email.
        self.assertEqual(
            sorted((r.channel for r in new_rows)), ["email", "sms"])
        sms = [r for r in new_rows if r.channel == "sms"][0]
        email = [r for r in new_rows if r.channel == "email"][0]
        # The SMS is byte-identical to before.
        self.assertEqual(sms.body, SMS_THANK_YOU)
        # The email carries the heading + the owner's line, text + HTML.
        self.assertEqual(email.body, app_module.ride_complete_thank_you_text())
        self.assertIn("Thank you for riding with us.", email.body)
        self.assertIn(THANK_YOU_LINE, email.body)
        self.assertIn(THANK_YOU_LINE, email.html_body or "")
        self.assertIn('<span style="color:#D4AF37;">Chauffeur</span>',
                      email.html_body or "")
        self.assertEqual(email.recipient, "cust@test.com")
        # The email went out with the default subject + sender.
        send = None
        for call in self._send_mock.call_args_list:
            args, _kwargs = call
            if args[2] == email.body:
                send = args
        self.assertIsNotNone(send, "no Resend call carried the thank-you email")
        self.assertEqual(send[1], "Noel Chauffer")
        self.assertEqual(email_sender_module.DEFAULT_FROM,
                         "Noel Chauffer <info@noelchauffer.com>")

    def test_completion_sends_thank_you_email_hourly(self):
        _driver, token = self.register_driver()
        booking_id, new_rows = self.complete_ride(token, "hourly", hours=2)
        self.assertEqual(
            sorted((r.channel for r in new_rows)), ["email", "sms"])
        email = [r for r in new_rows if r.channel == "email"][0]
        self.assertIn(THANK_YOU_LINE, email.body)
        self.assertIn(THANK_YOU_LINE, email.html_body or "")
        sms = [r for r in new_rows if r.channel == "sms"][0]
        self.assertEqual(sms.body, SMS_THANK_YOU)

    def test_completion_adds_no_receipt_or_invoice_row(self):
        """Completion adds only the thank-you pair: no second
        receipt, no invoice row — the receipt email stays the one
        queued at payment time."""
        _driver, token = self.register_driver()
        booking_id, new_rows = self.complete_ride(token)
        for row in new_rows:
            self.assertNotIn(app_module.PAYMENT_CONFIRMATION_PREFIX, row.body)
            self.assertNotIn("NCL-", row.body)
            self.assertNotIn("invoice", row.body.lower())
        with app_module.app.app_context():
            receipts = [r for r in self.outbox_rows(booking_id, channel="email")
                        if r.body.startswith(app_module.PAYMENT_CONFIRMATION_PREFIX)]
        self.assertEqual(len(receipts), 1, "the receipt must stay the single pay-time row")


if __name__ == "__main__":
    unittest.main()
