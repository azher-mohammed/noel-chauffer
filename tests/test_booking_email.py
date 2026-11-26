"""Tests for the booking-received email ("your booking has been
received").

Owner order (2026-11-25 ~19:44 EST, screenshot of the email): "Jo
mail aata hai booking ka, step by step details rehna" — the mail
the customer gets when a booking is created must come step by
step, every detail on its own line, like the payment receipt
(2026-11-23) and the chauffeur-assigned email (2026-11-23/24).
The old email was one single paragraph:

    Noel Chauffer: booking received for 2026-11-26 at 00:20, John F.
    Kennedy International Airport, JFK Access Road, Queens, Queens
    County, New York, 11430, United States to Central Terminal
    Drive, Queens, Queens County, New York, 11371, United States.
    Your total is $163.80. Complete your card payment to confirm
    your ride — your chauffeur will be assigned right after payment,
    and we will message you the chauffeur's details once a driver
    accepts.

Rules pinned here:
- The EMAIL (plain text AND its HTML part) is step-by-step, the
  same professional layout as the payment receipt: heading,
  divider, every detail on its own line with labels aligned in one
  column, divider, the total set apart on its own, then the payment
  instruction as a closing line. Lines, in order: Date, Time, From,
  To, Class, Total.
- The drop-off ("To") is labelled "To", like the chauffeur email.
  Hourly rides have no drop-off, so the "To" row is omitted rather
  than printed blank.
- The SMS keeps the old one-paragraph text (the owner complained
  about the mail, not the text message).
- The subject stays the default "Noel Chauffer". The sender stays
  the Resend default (info@noelchauffer.com since 2026-11-23).
- Nothing else changes: the payment receipt, the chauffeur-assigned
  email and the invoice email are untouched.

Run:  python -m unittest discover -s tests -v
"""

import io  # noqa: F401  (kept for parity with the sibling email tests)
import os
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------

_tmpdir = tempfile.mkdtemp(prefix="noel-chauffeur-booking-email-")
os.environ["DATABASE_URL"] = (
    "sqlite:///" + os.path.join(_tmpdir, "booking-email.db"))
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "booking-email-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import email_sender as email_sender_module  # noqa: E402

EMAIL = "booking@test.com"
PHONE = "+15550008888"


def field_value(lines, label):
    """The value on the 'Label: value' line, or None."""
    for line in lines:
        if line.startswith(label + ":"):
            return line.split(":", 1)[1].strip()
    return None


def one_way_booking(**overrides):
    """A one-way booking namespace with the fields the email builders read."""
    booking = SimpleNamespace(
        date="2026-11-26", time="00:20",
        pickup=("John F. Kennedy International Airport, JFK Access Road, "
                "Queens, Queens County, New York, 11430, United States"),
        dropoff=("Central Terminal Drive, Queens, Queens County, "
                 "New York, 11371, United States"),
        ride_type="one_way", vehicle_class="sedan", fare_total="163.80")
    booking.__dict__.update(overrides)
    return booking


class BookingEmailCase(unittest.TestCase):
    """In-process API tests with a fresh DB per test."""

    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        # Capture every attempted Resend send (subject + body), so the
        # default subject can be pinned without a real send.
        self._send_mock = mock.MagicMock(return_value="sent")
        self._send_patch = mock.patch.object(
            app_module, "send_email", self._send_mock)
        self._send_patch.start()
        self.addCleanup(self._send_patch.stop)

    # -- helpers ---------------------------------------------------------

    def _booking_payload(self):
        return {
            "customer_name": "Booking Customer", "phone": PHONE,
            "email": EMAIL, "pickup": "JFK Airport",
            "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }

    def _hourly_payload(self):
        return {
            "customer_name": "Booking Customer", "phone": PHONE,
            "email": EMAIL, "pickup": "JFK Airport",
            "date": "2030-06-01", "time": "12:00", "ride_type": "hourly",
            "hours": 2, "vehicle_class": "sedan",
        }

    def make_booking(self, payload):
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]["id"]

    def outbox_rows(self, booking_id, channel=None):
        with app_module.app.app_context():
            query = app_module.OutboxMessage.query.filter_by(booking_id=booking_id)
            if channel:
                query = query.filter_by(channel=channel)
            return query.all()

    def booking_email_send(self):
        """The (recipient, subject, body, html) of the Resend call
        carrying the step-by-step booking email, or None."""
        for call in self._send_mock.call_args_list:
            args, kwargs = call
            body = args[2] if len(args) > 2 else kwargs.get("body", "")
            if body.startswith(app_module.BOOKING_RECEIVED_HEADING):
                return args, kwargs
        return None

    # -- the format itself -------------------------------------------------

    def test_text_is_step_by_step(self):
        text = app_module.booking_received_email_text(one_way_booking())
        lines = text.split("\n")
        self.assertEqual(lines[0], "Your booking has been received.")
        self.assertEqual(lines[1], "-" * 40)
        self.assertEqual(field_value(lines, "Date"), "2026-11-26")
        self.assertEqual(field_value(lines, "Time"), "00:20")
        self.assertEqual(field_value(lines, "From"),
                         "John F. Kennedy International Airport, JFK Access Road, "
                         "Queens, Queens County, New York, 11430, United States")
        self.assertEqual(field_value(lines, "To"),
                         "Central Terminal Drive, Queens, Queens County, "
                         "New York, 11371, United States")
        self.assertEqual(field_value(lines, "Class"), "Business Class")
        self.assertEqual(field_value(lines, "Total"), "$163.80")
        # Rows in order: Date, Time, From, To, Class, Total.
        order = ["Date:", "Time:", "From:", "To:", "Class:", "Total:"]
        positions = [next(i for i, l in enumerate(lines)
                          if l.startswith(label)) for label in order]
        self.assertEqual(positions, sorted(positions))
        # The total is set apart: a divider sits right above it.
        total_idx = next(i for i, l in enumerate(lines) if l.startswith("Total:"))
        self.assertEqual(lines[total_idx - 1], "-" * 40)
        # The payment instruction is the closing line, not a row.
        self.assertTrue(lines[-1].startswith("Complete your card payment"))
        self.assertIn("your ride will be sent to our chauffeurs right after "
                      "payment", lines[-1])
        self.assertIn("we will message you the chauffeur's details once "
                      "a driver accepts", lines[-1])
        # Labels aligned in one column: every value starts at the
        # same character position.
        expected = {
            "Date": "2026-11-26", "Time": "00:20",
            "From": ("John F. Kennedy International Airport, JFK Access Road, "
                     "Queens, Queens County, New York, 11430, United States"),
            "To": ("Central Terminal Drive, Queens, Queens County, "
                   "New York, 11371, United States"),
            "Class": "Business Class", "Total": "$163.80",
        }
        value_starts = {line.index(value) for line in lines
                        for label, value in expected.items()
                        if line.startswith(label + ":")}
        self.assertEqual(len(value_starts), 1)
        # The old single-paragraph form is gone from the email.
        self.assertNotIn("booking received for", text)

    def test_html_has_same_rows(self):
        html = app_module.booking_received_email_html(one_way_booking())
        self.assertIn("Noel ", html)
        self.assertIn('<span style="color:#D4AF37;">Chauffeur</span>', html)
        self.assertIn("Your booking has been received.", html)
        for label, value in (("Date", "2026-11-26"),
                             ("Time", "00:20"),
                             ("From", "John F. Kennedy International Airport"),
                             ("To", "Central Terminal Drive"),
                             ("Class", "Business Class"),
                             ("Total", "$163.80")):
            self.assertIn(label, html)
            self.assertIn(value, html)
        # The total is set apart and bold.
        self.assertIn("<strong>$163.80</strong>", html)
        # The payment instruction closes the email.
        self.assertIn("Complete your card payment to confirm your ride", html)
        # "To" comes after "From" in the HTML table too.
        self.assertLess(html.index("John F. Kennedy International Airport"),
                        html.index("Central Terminal Drive"))
        self.assertNotIn("booking received for", html)

    def test_no_dropoff_means_no_to_row(self):
        """Hourly rides have no drop-off: the 'To' row is omitted
        rather than printed blank — in both the text and the HTML."""
        for dropoff in (None, ""):
            booking = one_way_booking(ride_type="hourly", dropoff=dropoff)
            text = app_module.booking_received_email_text(booking)
            self.assertNotIn("To:", text)
            html = app_module.booking_received_email_html(booking)
            self.assertNotIn(">To<", html)
        # A booking object with no dropoff attribute at all behaves
        # the same (older fixtures / hourly rows).
        booking = SimpleNamespace(date="2026-11-26", time="00:20",
                                  pickup="JFK Airport, Queens, NY",
                                  ride_type="hourly", vehicle_class="sedan",
                                  fare_total="218.32")
        self.assertNotIn("To:", app_module.booking_received_email_text(booking))

    # -- the real booking flow ----------------------------------------------

    def test_creation_queues_step_by_step_email_and_unchanged_sms(self):
        booking_id = self.make_booking(self._booking_payload())
        sms_rows = self.outbox_rows(booking_id, channel="sms")
        self.assertEqual(len(sms_rows), 1)
        sms = sms_rows[0].body
        # The SMS keeps the old one-paragraph text.
        self.assertTrue(sms.startswith(
            "Noel Chauffer: booking received for 2030-06-01 at 12:00, "
            "JFK Airport to Times Square, New York."))
        self.assertIn("Complete your card payment to confirm your ride", sms)
        sms_total = re.search(r"Your total is (\$[0-9]+\.[0-9]{2})", sms).group(1)

        email_rows = [r for r in self.outbox_rows(booking_id, channel="email")
                      if r.body.startswith(app_module.BOOKING_RECEIVED_HEADING)]
        self.assertEqual(len(email_rows), 1)
        email = email_rows[0]
        lines = email.body.split("\n")
        self.assertEqual(field_value(lines, "Date"), "2030-06-01")
        self.assertEqual(field_value(lines, "Time"), "12:00")
        self.assertEqual(field_value(lines, "From"), "JFK Airport")
        self.assertEqual(field_value(lines, "To"), "Times Square, New York")
        self.assertEqual(field_value(lines, "Class"), "Business Class")
        self.assertEqual(field_value(lines, "Total"), sms_total)
        self.assertTrue(lines[-1].startswith("Complete your card payment"))
        # The HTML part rides with the same email row.
        self.assertIn('<span style="color:#D4AF37;">Chauffeur</span>',
                      email.html_body or "")
        self.assertIn("Your booking has been received.", email.html_body or "")
        self.assertIn("<strong>%s</strong>" % sms_total, email.html_body or "")

    def test_hourly_creation_omits_to_row(self):
        booking_id = self.make_booking(self._hourly_payload())
        email_rows = [r for r in self.outbox_rows(booking_id, channel="email")
                      if r.body.startswith(app_module.BOOKING_RECEIVED_HEADING)]
        self.assertEqual(len(email_rows), 1)
        email = email_rows[0]
        self.assertNotIn("To:", email.body)
        self.assertNotIn(">To<", email.html_body or "")
        self.assertEqual(field_value(email.body.split("\n"), "From"),
                         "JFK Airport")
        self.assertEqual(field_value(email.body.split("\n"), "Class"),
                         "Business Class")
        # The SMS is still the one-paragraph form, pickup only.
        sms_rows = self.outbox_rows(booking_id, channel="sms")
        self.assertEqual(len(sms_rows), 1)
        self.assertTrue(sms_rows[0].body.startswith(
            "Noel Chauffer: booking received for 2030-06-01 at 12:00, "
            "JFK Airport."))

    # -- subject and sender ---------------------------------------------------

    def test_subject_and_sender_unchanged(self):
        """The booking-received email goes out with the default
        subject and the default Resend sender — neither was touched
        by the rebuild."""
        self.make_booking(self._booking_payload())
        send = self.booking_email_send()
        self.assertIsNotNone(send, "no Resend call carried the booking email")
        args, _kwargs = send
        self.assertEqual(args[1], "Noel Chauffer")
        self.assertEqual(email_sender_module.DEFAULT_FROM,
                         "Noel Chauffer <info@noelchauffer.com>")
        self.assertEqual(app_module.DEFAULT_EMAIL_SUBJECT, "Noel Chauffer")

    def test_sms_builder_unchanged(self):
        """booking_received_text is still the old one-paragraph
        message — the rebuild only changed the email."""
        text = app_module.booking_received_text(one_way_booking())
        self.assertTrue(text.startswith(
            "Noel Chauffer: booking received for 2026-11-26 at 00:20, "
            "John F. Kennedy International Airport, JFK Access Road, "
            "Queens, Queens County, New York, 11430, United States to "
            "Central Terminal Drive, Queens, Queens County, New York, "
            "11371, United States."))
        self.assertIn("Your total is $163.80.", text)


if __name__ == "__main__":
    unittest.main()
