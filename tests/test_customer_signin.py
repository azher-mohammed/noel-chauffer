"""Tests for compulsory EMAIL-ONLY customer sign-in (owner decision
2026-11-22, voice call, corrected the same day: NO CODES — "Nahi
bhai, no codes"): after "View options" / "Choose your experience",
before the booking can proceed to payment, the customer MUST sign
in. Sign-in is email only — one email field + Continue, NO
password, NO Google/Apple/Facebook, NO code emailed, NO code typed
back. The customer types their email (and phone number, which is
compulsory too) and taps Continue — that is the whole sign-in.
Signed-in customers stay signed in (Flask session) for later
bookings.

Server rules pinned here:
- POST /api/customers/signin needs a valid email AND a phone
  number; success signs the browser in (Flask session) so later
  bookings skip the sign-in step. It sends NO email and stores
  NO code anywhere.
- POST /api/bookings/<id>/contact refuses (401) unless the browser
  is signed in with the SAME email; phone is compulsory there.
- POST /api/bookings/<id>/pay (and /pay/confirm) refuse (401)
  unless the browser is signed in with the booking's email and the
  booking has a phone number.
- GET /api/bookings?email=... returns a signed-in customer's own
  rides; the old phone lookup still works unchanged.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-signin-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "signin-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402

EMAIL = "rider@example.com"
PHONE = "+1 929-385-7597"
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Signin Customer"}


class CustomerSigninCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def signin(self, email=EMAIL, phone=PHONE):
        """Email + Continue only (owner 2026-11-22: NO CODES) — one
        POST signs the browser in; nothing is emailed, no code is
        typed back."""
        resp = self.client.post("/api/customers/signin",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return resp.get_json()

    def book(self, email=EMAIL, phone=PHONE, name="Signin Customer"):
        """One-way booking created WITH contact, like the booking form
        submits it (hourly-style up-front contact)."""
        resp = self.client.post("/api/bookings", json={
            "customer_name": name, "phone": phone, "email": email,
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way"})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def book_without_contact(self):
        resp = self.client.post("/api/bookings", json={
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way"})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    # -- sign-in ---------------------------------------------------------
    def test_signin_needs_email_and_phone(self):
        self.assertEqual(self.client.post(
            "/api/customers/signin",
            json={"email": "", "phone": PHONE}).status_code, 400)
        self.assertEqual(self.client.post(
            "/api/customers/signin",
            json={"email": "not-an-email", "phone": PHONE}).status_code, 400)
        self.assertEqual(self.client.post(
            "/api/customers/signin",
            json={"email": EMAIL, "phone": ""}).status_code, 400)
        self.assertEqual(self.client.post(
            "/api/customers/signin",
            json={"email": EMAIL, "phone": "123"}).status_code, 400)
        body = self.signin()
        self.assertTrue(body["signed_in"])
        self.assertEqual(body["email"], EMAIL)
        self.assertEqual(body["phone"], PHONE)

    def test_signin_sends_no_email_and_stores_no_code(self):
        """Owner 2026-11-22: NO CODES — sign-in must not email
        anything and must not create any code row."""
        self.signin()
        with app_module.app.app_context():
            self.assertEqual(app_module.OutboxMessage.query.count(), 0)
            self.assertFalse(hasattr(app_module, "CustomerSigninCode"))

    def test_signin_normalizes_email(self):
        body = self.signin(email="  Rider@Example.COM  ")
        self.assertEqual(body["email"], EMAIL)
        resp = self.client.get("/api/customers/me")
        self.assertEqual(resp.get_json()["email"], EMAIL)

    def test_me_and_signout(self):
        resp = self.client.get("/api/customers/me")
        self.assertFalse(resp.get_json()["signed_in"])
        self.signin()
        resp = self.client.get("/api/customers/me")
        self.assertTrue(resp.get_json()["signed_in"])
        self.assertEqual(resp.get_json()["email"], EMAIL)
        resp = self.client.post("/api/customers/signout")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(self.client.get("/api/customers/me").get_json()["signed_in"])

    # -- the gate: contact ----------------------------------------------
    def test_contact_needs_matching_signin(self):
        booking = self.book_without_contact()
        # No sign-in at all.
        resp = self.client.post(f"/api/bookings/{booking['id']}/contact",
                                json={"customer_name": "Signin Customer",
                                      "phone": PHONE, "email": EMAIL})
        self.assertEqual(resp.status_code, 401)
        # Signed in as someone else.
        self.signin(email="other@example.com", phone="+1 212-555-0100")
        resp = self.client.post(f"/api/bookings/{booking['id']}/contact",
                                json={"customer_name": "Signin Customer",
                                      "phone": PHONE, "email": EMAIL})
        self.assertEqual(resp.status_code, 401)
        # Signed in with the booking's email: contact saves.
        self.signin()
        resp = self.client.post(f"/api/bookings/{booking['id']}/contact",
                                json={"customer_name": "Signin Customer",
                                      "phone": PHONE, "email": EMAIL})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_contact_still_needs_phone(self):
        booking = self.book_without_contact()
        self.signin()
        resp = self.client.post(f"/api/bookings/{booking['id']}/contact",
                                json={"customer_name": "Signin Customer",
                                      "phone": "", "email": EMAIL})
        self.assertEqual(resp.status_code, 400)

    # -- the gate: payment ----------------------------------------------
    def test_pay_needs_matching_signin(self):
        booking = self.book()
        # No sign-in: payment is refused even with a valid card.
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay", json=CARD)
        self.assertEqual(resp.status_code, 401)
        # Signed in as someone else: still refused.
        self.signin(email="other@example.com", phone="+1 212-555-0100")
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay", json=CARD)
        self.assertEqual(resp.status_code, 401)
        # Signed in with the booking's email: payment goes through.
        self.signin()
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay", json=CARD)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["booking"]["status"], "offered")

    def test_signin_survives_for_next_booking(self):
        self.signin()
        first = self.book()
        resp = self.client.post(f"/api/bookings/{first['id']}/pay", json=CARD)
        self.assertEqual(resp.status_code, 200)
        # Second booking, same browser: no new sign-in needed.
        self._phone_seq += 1
        second = self.book()
        resp = self.client.post(f"/api/bookings/{second['id']}/pay", json=CARD)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    # -- My Rides ---------------------------------------------------------
    def test_history_by_signed_in_email_and_by_phone(self):
        self.signin()
        booking = self.book()
        self.client.post(f"/api/bookings/{booking['id']}/pay", json=CARD)
        resp = self.client.get("/api/bookings", query_string={"email": EMAIL})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()), 1)
        self.assertEqual(resp.get_json()[0]["id"], booking["id"])
        # Phone lookup still works exactly as before.
        resp = self.client.get("/api/bookings", query_string={"phone": PHONE})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()), 1)
        # Email lookup without a matching sign-in is refused.
        other = self.client  # same client, signed in as EMAIL
        resp = other.get("/api/bookings", query_string={"email": "other@example.com"})
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
