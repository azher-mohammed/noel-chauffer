"""Tests for the driver welcome email.

Owner order (2026-11-25, voice call — he approved the text with
"Okay very good"): when a driver registers, he gets a warm welcome
email ONCE. Approved text, kept verbatim:

    Welcome to Noel Chauffer! Thank you for joining us as a
    chauffeur. Driver app kholein aur jab taiyar hon to online ho
    jayein apni pehli ride ke liye.

Before this build, registration sent no email at all — and SMS
never reaches a phone (outbox-only, Resend is email-only), so the
email is the only channel that reaches the driver.

Rules pinned here:
- The EMAIL (plain text AND its HTML part) carries the heading
  "Welcome to Noel Chauffer!" and the owner's approved lines,
  nothing else: no amounts, no booking details, no links, no
  referral text.
- The HTML follows the same professional layout as the receipt /
  chauffeur / booking-received / thank-you emails: Noel Chauffer
  letterhead ("Noel " + gold "Chauffeur"), heading, the welcome
  lines.
- Subject is "Welcome to Noel Chauffer". The sender stays the
  Resend default (info@noelchauffer.com since 2026-11-23).
- It fires ONCE per driver: the welcome_email_sent flag on the
  driver row is the guard, and a prior welcome row in the outbox
  for the same email address is the second guard — a driver who
  re-registers (even after the old driver row was removed) never
  gets a second welcome.
- Registration itself is unchanged: same 201 response, same
  driver JSON, same token, no SMS row queued.
- No other email is touched: receipt, chauffeur, booking-received,
  thank-you and invoice are unchanged by registration.

Run:  python -m unittest tests.test_driver_welcome_email -v
"""

import io
import os
import sys
import tempfile
import unittest
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------

_tmpdir = tempfile.mkdtemp(prefix="noel-chauffeur-driver-welcome-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "driver-welcome.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "driver-welcome-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import email_sender as email_sender_module  # noqa: E402
import photo_factory  # noqa: E402

WELCOME_HEADING = "Welcome to Noel Chauffer!"
WELCOME_LINE_1 = "Thank you for joining us as a chauffeur."
WELCOME_LINE_2 = ("Driver app kholein aur jab taiyar hon to online "
                  "ho jayein apni pehli ride ke liye.")


class DriverWelcomeEmailCase(unittest.TestCase):
    """In-process API tests with a fresh DB per test."""

    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        # Capture every attempted Resend send (subject + body), so the
        # subject can be pinned without a real send.
        self._send_mock = mock.MagicMock(return_value="sent")
        self._send_patch = mock.patch.object(
            app_module, "send_email", self._send_mock)
        self._send_patch.start()
        self.addCleanup(self._send_patch.stop)

    # -- helpers ---------------------------------------------------------

    def register_driver(self, phone=None, email=None):
        self._driver_seq += 1
        seq = self._driver_seq
        phone = phone or f"+1555000{seq:04d}"
        data = {
            "name": f"Test Driver {seq}", "phone": phone,
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"T{seq:05d}",
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
        }
        if email is not None:
            data["email"] = email
        resp = self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()

    def welcome_rows(self, recipient=None):
        with app_module.app.app_context():
            query = app_module.OutboxMessage.query.filter_by(channel="email").filter(
                app_module.OutboxMessage.body.like(WELCOME_HEADING + "%"))
            if recipient is not None:
                query = query.filter_by(recipient=recipient)
            return query.all()

    def outbox_rows(self):
        with app_module.app.app_context():
            return app_module.OutboxMessage.query.all()

    def driver_row(self, driver_id):
        with app_module.app.app_context():
            return app_module.db.session.get(app_module.Driver, driver_id)

    # -- the format itself -------------------------------------------------

    def test_text_and_html_carry_approved_welcome(self):
        text = app_module.driver_welcome_email_text()
        self.assertTrue(text.startswith(WELCOME_HEADING))
        self.assertIn(WELCOME_LINE_1, text)
        self.assertIn(WELCOME_LINE_2, text)
        self.assertEqual(text, WELCOME_HEADING + "\n\n" + WELCOME_LINE_1 + " " + WELCOME_LINE_2)

        html = app_module.driver_welcome_email_html()
        self.assertIn("Noel ", html)
        self.assertIn('<span style="color:#D4AF37;">Chauffeur</span>', html)
        self.assertIn(WELCOME_HEADING, html)
        self.assertIn(WELCOME_LINE_1, html)
        self.assertIn(WELCOME_LINE_2, html)

    # -- the real registration flow -----------------------------------------

    def test_registration_queues_welcome_email_once(self):
        body = self.register_driver(email="d1@test.com")
        driver_id = body["driver"]["id"]

        rows = self.welcome_rows("d1@test.com")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.body, app_module.driver_welcome_email_text())
        self.assertEqual(row.html_body, app_module.driver_welcome_email_html())
        # Registration queues nothing else: no SMS, no other email.
        self.assertEqual(len(self.outbox_rows()), 1)

        # The sent flag is set on the driver row.
        self.assertTrue(self.driver_row(driver_id).welcome_email_sent)

        # The Resend send went to the driver's email with the
        # welcome subject and the default sender.
        send = self._send_mock.call_args
        self.assertIsNotNone(send, "no Resend call carried the welcome email")
        args, _kwargs = send
        self.assertEqual(args[0], "d1@test.com")
        self.assertEqual(args[1], "Welcome to Noel Chauffer")
        self.assertEqual(email_sender_module.DEFAULT_FROM,
                         "Noel Chauffer <info@noelchauffer.com>")

    def test_helper_is_idempotent_for_same_driver(self):
        """Calling the welcome send twice for the same driver queues
        only one email — the flag guard."""
        body = self.register_driver(email="d2@test.com")
        driver_id = body["driver"]["id"]
        self.assertEqual(len(self.welcome_rows("d2@test.com")), 1)
        with app_module.app.app_context():
            driver = app_module.db.session.get(app_module.Driver, driver_id)
            self.assertFalse(app_module.send_driver_welcome_email(driver))
            app_module.db.session.commit()
        self.assertEqual(len(self.welcome_rows("d2@test.com")), 1)
        self.assertEqual(len(self.outbox_rows()), 1)

    def test_reregistration_gets_no_second_welcome(self):
        """A driver who re-registers — same email, after the old
        driver row was removed — never gets a second welcome. The
        flag dies with the old row, so the outbox guard must catch
        it."""
        self.register_driver(phone="+15550001001", email="again@test.com")
        self.assertEqual(len(self.welcome_rows("again@test.com")), 1)
        # Owner removes the driver (the row is gone; the outbox row
        # survives, exactly as in production).
        with app_module.app.app_context():
            driver = app_module.Driver.query.filter_by(
                email="again@test.com").first()
            app_module.db.session.delete(driver)
            app_module.db.session.commit()
        # Same person registers again, same phone and email.
        self.register_driver(phone="+15550001001", email="again@test.com")
        self.assertEqual(len(self.welcome_rows("again@test.com")), 1)
        self.assertEqual(len(self.outbox_rows()), 1)

    def test_no_email_without_address(self):
        """A registration with no email on file gets no welcome —
        there is nowhere to send it."""
        self.register_driver(email=None)
        self.assertEqual(self.welcome_rows(), [])
        self.assertEqual(self.outbox_rows(), [])


if __name__ == "__main__":
    unittest.main()
