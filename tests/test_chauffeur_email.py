"""Tests for the chauffeur-assigned email ("your chauffeur is ...").

Owner order (voice call 2026-11-23 ~23:33 EST): the mail the customer
gets when a driver accepts must come line by line — chauffeur name,
phone number, car model, pickup, every detail on its own line — so
it is easy to read. The old email was one single paragraph:

    Noel Chauffer: your chauffeur is Azher mohammed (9293857597),
    Tesla Model 3 (White), plate T100506C. Pickup 2026-11-21 at 18:00
    from Times Square, New York, 10036, United States.

Rules pinned here:
- The EMAIL (plain text AND its HTML part) is step-by-step, the
  same professional layout as the payment receipt: heading, divider,
  every detail on its own line with labels aligned in one column.
  Lines, in order: Chauffeur, Phone, Car, Plate, Pickup, From, To.
- The drop-off ("To") was added 2026-11-24 by owner order ("Drop
  off bhi rehna na") — same format, HTML + plain text, right after
  From. No total: the old email never carried one. Hourly rides
  have no drop-off, so the "To" row is omitted rather than printed
  blank.
- The SMS keeps the old one-paragraph text (the owner complained
  about the mail, not the text message).
- The SMS keeps the old one-paragraph text (the owner complained
  about the mail, not the text message).
- The subject stays the default "Noel Chauffer". The sender stays
  the Resend default (info@noelchauffer.com since 2026-11-23).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-chauffeur-email-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "chauffeur-email-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

EMAIL = "chauffeur@test.com"
PHONE = "+15550009999"


def field_value(lines, label):
    """The value on the 'Label: value' line, or None."""
    for line in lines:
        if line.startswith(label + ":"):
            return line.split(":", 1)[1].strip()
    return None


class ChauffeurEmailCase(unittest.TestCase):
    """In-process API tests with a fresh DB per test."""

    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0

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

    def _booking_payload(self):
        return {
            "customer_name": "Chauffeur Customer", "phone": PHONE,
            "email": EMAIL, "pickup": "JFK Airport",
            "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }

    def make_paid_booking(self):
        resp = self.client.post("/api/bookings", json=self._booking_payload())
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking_id = resp.get_json()["booking"]["id"]
        resp = self.client.post("/api/customers/signin",
                                json={"email": EMAIL, "phone": PHONE})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/bookings/{booking_id}/pay", json={
            "card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Chauffeur Customer"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return booking_id

    def outbox_rows(self, booking_id, channel=None):
        with app_module.app.app_context():
            query = app_module.OutboxMessage.query.filter_by(booking_id=booking_id)
            if channel:
                query = query.filter_by(channel=channel)
            return query.all()

    # -- the format itself -------------------------------------------------
    def test_text_is_line_by_line(self):
        driver = SimpleNamespace(name="Azher Mohammed", phone="9293857597",
                                 car_model="Tesla Model 3", car_colour="White",
                                 plate="T100506C")
        booking = SimpleNamespace(
            date="2026-11-24", time="00:30",
            pickup=("John F. Kennedy International Airport, JFK Access Road, "
                    "Queens, Queens County, New York, 11430, United States"),
            dropoff="Times Square, New York, 10036, United States")
        text = app_module.chauffeur_assigned_text(driver, booking)
        lines = text.split("\n")
        self.assertEqual(lines[0], "Your chauffeur has been assigned.")
        self.assertEqual(lines[1], "-" * 40)
        self.assertEqual(field_value(lines, "Chauffeur"), "Azher Mohammed")
        self.assertEqual(field_value(lines, "Phone"), "9293857597")
        self.assertEqual(field_value(lines, "Car"), "Tesla Model 3 (White)")
        self.assertEqual(field_value(lines, "Plate"), "T100506C")
        self.assertEqual(field_value(lines, "Pickup"), "2026-11-24 at 00:30")
        self.assertEqual(field_value(lines, "From"),
                         "John F. Kennedy International Airport, JFK Access Road, "
                         "Queens, Queens County, New York, 11430, United States")
        self.assertEqual(field_value(lines, "To"),
                         "Times Square, New York, 10036, United States")
        # "To" is the last row, right after "From".
        self.assertLess(lines.index(next(l for l in lines
                                         if l.startswith("From:"))),
                        lines.index(next(l for l in lines
                                         if l.startswith("To:"))))
        self.assertTrue(lines[-1].startswith("To:"))
        # Labels aligned in one column: every value starts at the
        # same character position.
        expected = {
            "Chauffeur": "Azher Mohammed", "Phone": "9293857597",
            "Car": "Tesla Model 3 (White)", "Plate": "T100506C",
            "Pickup": "2026-11-24 at 00:30",
            "From": ("John F. Kennedy International Airport, JFK Access Road, "
                     "Queens, Queens County, New York, 11430, United States"),
            "To": "Times Square, New York, 10036, United States",
        }
        value_starts = {line.index(value) for line in lines[2:]
                        for label, value in expected.items()
                        if line.startswith(label + ":")}
        self.assertEqual(len(value_starts), 1)
        # The old single-paragraph form is gone from the email.
        self.assertNotIn("your chauffeur is", text)
        # Nothing invented beyond the chauffeur details + drop-off.
        self.assertNotIn("Total", text)

    def test_html_has_same_rows(self):
        driver = SimpleNamespace(name="Azher Mohammed", phone="9293857597",
                                 car_model="Tesla Model 3", car_colour="White",
                                 plate="T100506C")
        booking = SimpleNamespace(date="2026-11-24", time="00:30",
                                  pickup="JFK Airport, Queens, NY",
                                  dropoff="Times Square, New York, NY")
        html = app_module.chauffeur_assigned_html(driver, booking)
        self.assertIn("Noel ", html)
        self.assertIn('<span style="color:#D4AF37;">Chauffeur</span>', html)
        self.assertIn("Your chauffeur has been assigned.", html)
        for label, value in (("Chauffeur", "Azher Mohammed"),
                             ("Phone", "9293857597"),
                             ("Car", "Tesla Model 3 (White)"),
                             ("Plate", "T100506C"),
                             ("Pickup", "2026-11-24 at 00:30"),
                             ("From", "JFK Airport, Queens, NY"),
                             ("To", "Times Square, New York, NY")):
            self.assertIn(label, html)
            self.assertIn(value, html)
        # "To" comes after "From" in the HTML table too.
        self.assertLess(html.index("JFK Airport, Queens, NY"),
                        html.index("Times Square, New York, NY"))
        self.assertNotIn("your chauffeur is", html)
        self.assertNotIn("Total", html)

    def test_no_dropoff_means_no_to_row(self):
        """Hourly rides have no drop-off: the 'To' row is omitted
        rather than printed blank — in both the text and the HTML."""
        driver = SimpleNamespace(name="Azher Mohammed", phone="9293857597",
                                 car_model="Tesla Model 3", car_colour="White",
                                 plate="T100506C")
        for dropoff in (None, ""):
            booking = SimpleNamespace(date="2026-11-24", time="00:30",
                                      pickup="JFK Airport, Queens, NY",
                                      dropoff=dropoff)
            text = app_module.chauffeur_assigned_text(driver, booking)
            self.assertNotIn("To:", text)
            html = app_module.chauffeur_assigned_html(driver, booking)
            self.assertNotIn(">To<", html)
        # A booking object with no dropoff attribute at all behaves
        # the same (older fixtures / hourly rows).
        booking = SimpleNamespace(date="2026-11-24", time="00:30",
                                  pickup="JFK Airport, Queens, NY")
        self.assertNotIn("To:", app_module.chauffeur_assigned_text(
            driver, booking))

    # -- the real accept flow ----------------------------------------------
    def test_accept_queues_line_by_line_email_and_unchanged_sms(self):
        _driver, token = self.register_driver()
        booking_id = self.make_paid_booking()
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        sms_rows = self.outbox_rows(booking_id, channel="sms")
        sms_bodies = " ".join(r.body for r in sms_rows)
        # The SMS keeps the old one-paragraph text.
        self.assertIn("your chauffeur is Test Driver 1", sms_bodies)
        email_rows = [r for r in self.outbox_rows(booking_id, channel="email")
                      if r.body.startswith("Your chauffeur has been assigned.")]
        self.assertEqual(len(email_rows), 1)
        email = email_rows[0]
        lines = email.body.split("\n")
        self.assertEqual(field_value(lines, "Chauffeur"), "Test Driver 1")
        self.assertEqual(field_value(lines, "Phone"), "+15550000001")
        self.assertEqual(field_value(lines, "Car"), "Cadillac CT6 (Black)")
        self.assertEqual(field_value(lines, "Plate"), "T00001")
        self.assertEqual(field_value(lines, "Pickup"), "2030-06-01 at 12:00")
        self.assertEqual(field_value(lines, "From"), "JFK Airport")
        self.assertEqual(field_value(lines, "To"), "Times Square, New York")
        # "To" is the last row, right after "From".
        self.assertLess(lines.index(next(l for l in lines
                                         if l.startswith("From:"))),
                        lines.index(next(l for l in lines
                                         if l.startswith("To:"))))
        self.assertTrue(lines[-1].startswith("To:"))
        self.assertNotIn("your chauffeur is", email.body)
        # The HTML part travelled with the email row — same rows.
        self.assertIsNotNone(email.html_body)
        self.assertIn("Your chauffeur has been assigned.", email.html_body)
        self.assertIn("Test Driver 1", email.html_body)
        self.assertIn("Cadillac CT6 (Black)", email.html_body)
        self.assertIn("T00001", email.html_body)
        self.assertIn("Times Square, New York", email.html_body)
        self.assertLess(email.html_body.index("JFK Airport"),
                        email.html_body.index("Times Square, New York"))

    def test_email_subject_stays_noel_chauffer(self):
        _driver, token = self.register_driver()
        booking_id = self.make_paid_booking()
        with mock.patch.object(app_module, "send_email",
                               return_value="sent") as fake_send:
            resp = self.client.post(
                f"/api/drivers/me/offers/{booking_id}/accept",
                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        chauffeur_calls = [c for c in fake_send.call_args_list
                           if c.args[0] == EMAIL
                           and c.args[2].startswith(
                               "Your chauffeur has been assigned.")]
        self.assertEqual(len(chauffeur_calls), 1)
        self.assertEqual(chauffeur_calls[0].args[1], "Noel Chauffer")
        self.assertIn("html", chauffeur_calls[0].kwargs)
        self.assertIn("Your chauffeur has been assigned.",
                      chauffeur_calls[0].kwargs["html"])


if __name__ == "__main__":
    unittest.main()
