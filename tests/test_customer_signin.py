"""Tests for compulsory EMAIL-ONLY customer sign-in (owner decision
2026-11-22, voice call): after "View options" / "Choose your
experience", before the booking can proceed to payment, the
customer MUST sign in. Sign-in is email only — one email field +
Continue, NO password, NO Google/Apple/Facebook. A 6-digit
one-time code goes to that email via the existing Resend setup
(from support@noelchauffer.com); the customer types the code back.
Phone number is compulsory too: it is collected with the email at
the sign-in step, and the booking cannot proceed without it.

Server rules pinned here:
- POST /api/customers/signin/request needs a valid email AND a
  phone number; at most 5 codes per email per hour; only the
  latest code works; the code never appears in any response.
- POST /api/customers/signin/verify: single-use, 10-minute expiry,
  5 wrong guesses lock that code; success signs the browser in
  (Flask session) so later bookings skip the code step.
- POST /api/bookings/<id>/contact refuses (401) unless the browser
  is signed in with the SAME email; phone is compulsory there.
- POST /api/bookings/<id>/pay (and /pay/confirm) refuse (401)
  unless the browser is signed in with the booking's email and the
  booking has a phone number.
- GET /api/bookings?email=... returns a signed-in customer's own
  rides; the old phone lookup still works unchanged.

The code travels by email: tests read it from the outbox row, the
same place a real customer reads it from their inbox.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from datetime import timedelta

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
    def request_code(self, email=EMAIL, phone=PHONE):
        return self.client.post("/api/customers/signin/request",
                                json={"email": email, "phone": phone})

    def read_code(self, email=EMAIL):
        """The code as the customer sees it: in the emailed outbox row."""
        with app_module.app.app_context():
            row = (app_module.OutboxMessage.query
                   .filter_by(recipient=email, channel="email")
                   .order_by(app_module.OutboxMessage.id.desc()).first())
        self.assertIsNotNone(row, "no sign-in email was queued")
        match = re.search(r"(\d{6})", row.body or "")
        self.assertIsNotNone(match, "no 6-digit code in the email: %r" % row.body)
        return match.group(1)

    def signin(self, email=EMAIL, phone=PHONE):
        resp = self.request_code(email, phone)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        code = self.read_code(email)
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": email, "code": code})
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

    # -- code request ----------------------------------------------------
    def test_request_needs_email_and_phone(self):
        self.assertEqual(self.request_code(email="").status_code, 400)
        self.assertEqual(self.request_code(email="not-an-email").status_code, 400)
        self.assertEqual(self.request_code(phone="").status_code, 400)
        self.assertEqual(self.request_code(phone="123").status_code, 400)
        resp = self.request_code()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("sent"))
        # The code is NEVER in the response.
        self.assertNotIn("code", resp.get_json())

    def test_request_rate_limited_per_hour(self):
        for _ in range(5):
            self.assertEqual(self.request_code().status_code, 200)
        self.assertEqual(self.request_code().status_code, 429)

    def test_only_latest_code_works(self):
        self.request_code()
        first = self.read_code()
        self.request_code()
        second = self.read_code()
        self.assertNotEqual(first, second)
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": EMAIL, "code": first})
        self.assertEqual(resp.status_code, 401)
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": EMAIL, "code": second})
        self.assertEqual(resp.status_code, 200)

    # -- code verify ------------------------------------------------------
    def test_verify_wrong_code_then_right_code(self):
        self.request_code()
        code = self.read_code()
        wrong = "000000" if code != "000000" else "111111"
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": EMAIL, "code": wrong})
        self.assertEqual(resp.status_code, 401)
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": EMAIL, "code": code})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["signed_in"])
        self.assertEqual(resp.get_json()["email"], EMAIL)
        self.assertEqual(resp.get_json()["phone"], PHONE)

    def test_code_is_single_use(self):
        self.signin()
        code = self.read_code()
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": EMAIL, "code": code})
        self.assertEqual(resp.status_code, 401)

    def test_five_wrong_guesses_lock_the_code(self):
        self.request_code()
        code = self.read_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(self.client.post(
                "/api/customers/signin/verify",
                json={"email": EMAIL, "code": wrong}).status_code, 401)
        # Even the right code no longer works after 5 wrong guesses.
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": EMAIL, "code": code})
        self.assertEqual(resp.status_code, 401)

    def test_expired_code_rejected(self):
        self.request_code()
        code = self.read_code()
        with app_module.app.app_context():
            row = (app_module.CustomerSigninCode.query
                   .filter_by(email=EMAIL).order_by(
                       app_module.CustomerSigninCode.id.desc()).first())
            row.expires_at = app_module.utcnow() - timedelta(minutes=1)
            app_module.db.session.commit()
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": EMAIL, "code": code})
        self.assertEqual(resp.status_code, 401)

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
        # Second booking, same browser: no new code needed.
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
