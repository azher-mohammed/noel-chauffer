"""Tests for the complete driver sign-in process: email + password
sign-in and forgot-password reset.

Owner decision 2026-11-18 (voice call): "complete sign in process
banao yaar". Before this, sign-in was phone-number lookup only — no
password existed anywhere. Registration now sets a password (with
confirmation, minimum 6 characters); only its hash is stored.
Email + password sign-in is the primary form; the phone lookup
stays visible below it so no existing driver is locked out.

Password reset (same call, "password to baar baar bhool jate hain"
— drivers keep forgetting passwords): a single-use token, stored
hashed only, 1-hour expiry, prior tokens invalidated, reset link
queued via the existing outbox (RECORDED, NOT SENT — no email
service is connected). No reset email is actually delivered until
an email service is connected; the owner shares the queued link.

Rules pinned here:
- Only the password hash is stored, never the plaintext; the hash
  never appears in any API response.
- Sign-in errors are generic: wrong password, unknown email, and
  no-password-hash all fail identically, revealing nothing.
- Email is normalized (trim + lowercase); a non-empty email already
  used by another driver is rejected at registration (409). Empty
  emails (legacy) are never blocked.
- Short / mismatched passwords are rejected at registration.
- Phone lookup behaviour is unchanged; legacy drivers without a
  hash keep signing in via phone lookup.
- Reset tokens are stored hashed only; unknown emails get the
  identical generic response as known ones; expired / used / wrong
  tokens are rejected; a successful reset sets the new hash, the
  old password stops working, the new one works, and the driver
  token rotates; issuing a new token invalidates prior ones; the
  reset link never appears in any API response.
- Sign-out already exists (Profile "Log out" clears the stored
  token); pinned statically, not rebuilt. The button was relabelled
  from "Register a different driver" to "Log out" on the owner's
  order 2026-11-18 ("log out" — he thought logout was missing
  because no button said so); behaviour is unchanged.

Run:  python -m unittest discover -s tests -v
"""

import hashlib
import io
import os
import re
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-signin-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "signin-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
from werkzeug.security import check_password_hash  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FIELDS = [
    ("profile_photo", "photo.jpg"),
    ("doc_dmv_license", "license.png"),
    ("doc_tlc_license", "tlc.png"),
    ("doc_fh1", "fh1.png"),
    ("doc_registration", "reg.png"),
    ("doc_inspection", "insp.png"),
    ("doc_vehicle_permit", "permit.png"),
]

GENERIC_SIGNIN_ERROR = "Email or password is incorrect."
GENERIC_RESET_REQUEST = ("If an account exists for that email, "
                         "password reset instructions have been sent.")
GENERIC_RESET_INVALID = "This reset link is invalid or has expired."


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class DriverSigninCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, password="secret123", confirm="secret123",
                 email=None, phone=None, extra=None, omit_password=False):
        self._seq += 1
        data = {
            "name": "Signin Driver", "phone": phone or f"+1555007{self._seq:04d}",
            "email": "signin@test.com" if email is None else email,
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"SG{self._seq:05d}",
            "state": "New York", "bank_account_number": "123456789",
            "bank_routing_number": "021000021",
        }
        if not omit_password:
            data["password"] = password
            data["password_confirm"] = confirm
        if extra:
            data.update(extra)
        for field, fname in FIELDS:
            data[field] = (io.BytesIO(
                photo_factory.VALID_PROFILE_PHOTO
                if field == "profile_photo" else b"fake doc"), fname)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    def signin(self, email, password):
        return self.client.post("/api/drivers/me/signin",
                                json={"email": email, "password": password})

    def forgot(self, email):
        return self.client.post("/api/drivers/me/forgot-password",
                                json={"email": email})

    def outbox_rows(self):
        with app_module.app.app_context():
            return app_module.OutboxMessage.query.order_by(
                app_module.OutboxMessage.id).all()

    def reset_token_from_outbox(self):
        bodies = [m.body for m in self.outbox_rows()]
        self.assertEqual(len(bodies), 1, bodies)
        match = re.search(r"/driver\?reset=(\S+)", bodies[0])
        self.assertIsNotNone(match, bodies[0])
        return match.group(1)

    # -- registration: password storage --------------------------------------
    def test_password_hash_stored_never_plaintext(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201, resp.text[:300])
        driver_id = resp.get_json()["driver"]["id"]
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Driver, driver_id)
            self.assertIsNotNone(row.password_hash)
            self.assertNotEqual(row.password_hash, "secret123")
            self.assertTrue(check_password_hash(row.password_hash, "secret123"))
            self.assertFalse(check_password_hash(row.password_hash, "wrongpass"))

    def test_hash_never_in_api_responses(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201, resp.text[:300])
        driver_id = resp.get_json()["driver"]["id"]
        token = resp.get_json()["token"]
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Driver, driver_id)
            stored_hash = row.password_hash
        self.assertNotIn("password_hash", resp.text)
        self.assertNotIn(stored_hash, resp.text)
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": token})
        self.assertEqual(me.status_code, 200)
        self.assertNotIn("password_hash", me.text)
        self.assertNotIn(stored_hash, me.text)
        self.client.post("/api/owner/login", json={"pin": "9999"})
        owners = self.client.get("/api/owner/drivers")
        self.assertEqual(owners.status_code, 200)
        self.assertNotIn("password_hash", owners.text)
        self.assertNotIn(stored_hash, owners.text)

    def test_email_normalized_lowercase(self):
        resp = self.register(email="Driver@TEST.com")
        self.assertEqual(resp.status_code, 201, resp.text[:300])
        self.assertEqual(resp.get_json()["driver"]["email"], "driver@test.com")

    def test_registration_short_password_rejected(self):
        resp = self.register(password="12345", confirm="12345")
        self.assertEqual(resp.status_code, 400, resp.text[:300])
        self.assertIn("at least 6 characters", resp.get_json()["error"])
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 0)

    def test_registration_mismatched_passwords_rejected(self):
        resp = self.register(password="secret123", confirm="different")
        self.assertEqual(resp.status_code, 400, resp.text[:300])
        self.assertIn("do not match", resp.get_json()["error"])
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 0)

    def test_registration_duplicate_email_rejected(self):
        first = self.register(email="dup@test.com")
        self.assertEqual(first.status_code, 201, first.text[:300])
        # Same email, different case and different phone: still a clash.
        second = self.register(email="DUP@test.com")
        self.assertEqual(second.status_code, 409, second.text[:300])
        self.assertIn("email", second.get_json()["error"].lower())
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 1)

    def test_registration_empty_emails_never_blocked(self):
        # Legacy path: no email at all must not trip the uniqueness rule.
        first = self.register(email="")
        self.assertEqual(first.status_code, 201, first.text[:300])
        second = self.register(email="")
        self.assertEqual(second.status_code, 201, second.text[:300])

    def test_registration_without_password_succeeds_legacy(self):
        resp = self.register(omit_password=True)
        self.assertEqual(resp.status_code, 201, resp.text[:300])
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Driver, resp.get_json()["driver"]["id"])
            self.assertIsNone(row.password_hash)

    # -- email + password sign-in --------------------------------------------
    def test_email_password_signin_success(self):
        self.register(email="driver@test.com")
        resp = self.signin("driver@test.com", "secret123")
        self.assertEqual(resp.status_code, 200, resp.text[:300])
        self.assertIn("token", resp.get_json())
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": resp.get_json()["token"]})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()["driver"]["email"], "driver@test.com")

    def test_signin_email_case_insensitive(self):
        self.register(email="driver@test.com")
        resp = self.signin("DRIVER@TEST.COM", "secret123")
        self.assertEqual(resp.status_code, 200, resp.text[:300])

    def test_signin_wrong_password_generic_error(self):
        self.register()
        resp = self.signin("signin@test.com", "wrongpass")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["error"], GENERIC_SIGNIN_ERROR)

    def test_signin_unknown_email_generic_error(self):
        self.register()
        resp = self.signin("nobody@test.com", "secret123")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["error"], GENERIC_SIGNIN_ERROR)

    def test_signin_no_hash_generic_error(self):
        self.register(omit_password=True)
        resp = self.signin("signin@test.com", "anything")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["error"], GENERIC_SIGNIN_ERROR)

    def test_signin_reissues_token_one_phone_at_a_time(self):
        self.register()
        first = self.signin("signin@test.com", "secret123")
        token1 = first.get_json()["token"]
        second = self.signin("signin@test.com", "secret123")
        token2 = second.get_json()["token"]
        self.assertNotEqual(token1, token2)
        stale = self.client.get("/api/drivers/me",
                                headers={"X-Driver-Token": token1})
        self.assertEqual(stale.status_code, 401)
        fresh = self.client.get("/api/drivers/me",
                                headers={"X-Driver-Token": token2})
        self.assertEqual(fresh.status_code, 200)

    # -- phone lookup unchanged ----------------------------------------------
    def test_phone_lookup_unchanged(self):
        resp = self.register(phone="+15550070001")
        self.assertEqual(resp.status_code, 201, resp.text[:300])
        lookup = self.client.post("/api/drivers/me/lookup",
                                  json={"phone": "+15550070001"})
        self.assertEqual(lookup.status_code, 200, lookup.text[:300])
        self.assertIn("token", lookup.get_json())

    def test_legacy_driver_without_hash_signs_in_via_phone(self):
        self.register(omit_password=True, phone="+15550070002")
        lookup = self.client.post("/api/drivers/me/lookup",
                                  json={"phone": "+15550070002"})
        self.assertEqual(lookup.status_code, 200, lookup.text[:300])
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": lookup.get_json()["token"]})
        self.assertEqual(me.status_code, 200)

    # -- forgot password / reset ----------------------------------------------
    def test_forgot_known_email_queues_outbox(self):
        self.register(email="driver@test.com")
        resp = self.forgot("driver@test.com")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["message"], GENERIC_RESET_REQUEST)
        rows = self.outbox_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].channel, "email")
        self.assertEqual(rows[0].recipient, "driver@test.com")
        self.assertIn("/driver?reset=", rows[0].body)

    def test_forgot_unknown_email_identical_response(self):
        self.register(email="driver@test.com")
        known = self.forgot("driver@test.com")
        unknown = self.forgot("nobody@test.com")
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(unknown.get_json(), known.get_json())
        # Unknown email creates nothing: one outbox row (the known one).
        self.assertEqual(len(self.outbox_rows()), 1)
        with app_module.app.app_context():
            self.assertEqual(app_module.PasswordResetToken.query.count(), 1)

    def test_forgot_driver_without_hash_creates_nothing(self):
        self.register(omit_password=True, email="legacy@test.com")
        resp = self.forgot("legacy@test.com")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["message"], GENERIC_RESET_REQUEST)
        self.assertEqual(len(self.outbox_rows()), 0)
        with app_module.app.app_context():
            self.assertEqual(app_module.PasswordResetToken.query.count(), 0)

    def test_reset_token_stored_hashed_never_plaintext(self):
        self.register()
        self.forgot("signin@test.com")
        token = self.reset_token_from_outbox()
        with app_module.app.app_context():
            rows = app_module.PasswordResetToken.query.all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].token_hash,
                             hashlib.sha256(token.encode()).hexdigest())
            self.assertNotEqual(rows[0].token_hash, token)

    def test_reset_link_never_in_api_responses(self):
        self.register()
        forgot = self.forgot("signin@test.com")
        self.assertNotIn("reset=", forgot.text)
        token = self.reset_token_from_outbox()
        reset = self.client.post("/api/drivers/me/reset-password",
                                 json={"token": token, "password": "newpass1",
                                       "password_confirm": "newpass1"})
        self.assertEqual(reset.status_code, 200, reset.text[:300])
        self.assertNotIn("reset=", reset.text)
        self.assertNotIn(token, reset.text)

    def test_reset_success_rotates_token_and_password(self):
        reg = self.register()
        old_token = reg.get_json()["token"]
        driver_id = reg.get_json()["driver"]["id"]
        self.forgot("signin@test.com")
        token = self.reset_token_from_outbox()
        reset = self.client.post("/api/drivers/me/reset-password",
                                 json={"token": token, "password": "newpass1",
                                       "password_confirm": "newpass1"})
        self.assertEqual(reset.status_code, 200, reset.text[:300])
        # Old password stops working, new one works.
        self.assertEqual(self.signin("signin@test.com", "secret123").status_code, 401)
        self.assertEqual(self.signin("signin@test.com", "newpass1").status_code, 200)
        # Old driver token no longer works (rotated).
        stale = self.client.get("/api/drivers/me",
                                headers={"X-Driver-Token": old_token})
        self.assertEqual(stale.status_code, 401)
        # Token row marked used.
        with app_module.app.app_context():
            row = app_module.PasswordResetToken.query.first()
            self.assertIsNotNone(row.used_at)
            self.assertTrue(check_password_hash(
                app_module.db.session.get(app_module.Driver, driver_id).password_hash,
                "newpass1"))

    def test_reset_token_single_use(self):
        self.register()
        self.forgot("signin@test.com")
        token = self.reset_token_from_outbox()
        first = self.client.post("/api/drivers/me/reset-password",
                                 json={"token": token, "password": "newpass1",
                                       "password_confirm": "newpass1"})
        self.assertEqual(first.status_code, 200)
        second = self.client.post("/api/drivers/me/reset-password",
                                  json={"token": token, "password": "newpass2",
                                        "password_confirm": "newpass2"})
        self.assertEqual(second.status_code, 401)
        self.assertEqual(second.get_json()["error"], GENERIC_RESET_INVALID)
        # The second attempt did not change the password.
        self.assertEqual(self.signin("signin@test.com", "newpass1").status_code, 200)
        self.assertEqual(self.signin("signin@test.com", "newpass2").status_code, 401)

    def test_reset_wrong_token_rejected_generic(self):
        self.register()
        self.forgot("signin@test.com")
        resp = self.client.post("/api/drivers/me/reset-password",
                                json={"token": "not-a-real-token",
                                      "password": "newpass1",
                                      "password_confirm": "newpass1"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["error"], GENERIC_RESET_INVALID)
        self.assertEqual(self.signin("signin@test.com", "secret123").status_code, 200)

    def test_reset_expired_token_rejected(self):
        self.register()
        self.forgot("signin@test.com")
        token = self.reset_token_from_outbox()
        with app_module.app.app_context():
            row = app_module.PasswordResetToken.query.first()
            row.expires_at = app_module.utcnow() - app_module.timedelta(hours=2)
            app_module.db.session.commit()
        resp = self.client.post("/api/drivers/me/reset-password",
                                json={"token": token, "password": "newpass1",
                                      "password_confirm": "newpass1"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["error"], GENERIC_RESET_INVALID)
        self.assertEqual(self.signin("signin@test.com", "secret123").status_code, 200)

    def test_reset_short_or_mismatched_password_rejected_token_survives(self):
        self.register()
        self.forgot("signin@test.com")
        token = self.reset_token_from_outbox()
        short = self.client.post("/api/drivers/me/reset-password",
                                 json={"token": token, "password": "12345",
                                       "password_confirm": "12345"})
        self.assertEqual(short.status_code, 400)
        self.assertIn("at least 6 characters", short.get_json()["error"])
        mismatch = self.client.post("/api/drivers/me/reset-password",
                                    json={"token": token, "password": "newpass1",
                                          "password_confirm": "otherpass"})
        self.assertEqual(mismatch.status_code, 400)
        self.assertIn("do not match", mismatch.get_json()["error"])
        # The token is still usable after validation failures.
        retry = self.client.post("/api/drivers/me/reset-password",
                                 json={"token": token, "password": "newpass1",
                                       "password_confirm": "newpass1"})
        self.assertEqual(retry.status_code, 200, retry.text[:300])

    def test_new_issue_invalidates_prior_tokens(self):
        self.register()
        self.forgot("signin@test.com")
        first_token = self.reset_token_from_outbox()
        self.forgot("signin@test.com")
        with app_module.app.app_context():
            rows = app_module.PasswordResetToken.query.order_by(
                app_module.PasswordResetToken.id).all()
            self.assertEqual(len(rows), 2)
            self.assertIsNotNone(rows[0].used_at)
            self.assertIsNone(rows[1].used_at)
        stale = self.client.post("/api/drivers/me/reset-password",
                                 json={"token": first_token, "password": "newpass1",
                                       "password_confirm": "newpass1"})
        self.assertEqual(stale.status_code, 401)
        self.assertEqual(stale.get_json()["error"], GENERIC_RESET_INVALID)
        bodies = [m.body for m in self.outbox_rows()]
        second_token = re.search(r"/driver\?reset=(\S+)", bodies[1]).group(1)
        fresh = self.client.post("/api/drivers/me/reset-password",
                                 json={"token": second_token, "password": "newpass1",
                                       "password_confirm": "newpass1"})
        self.assertEqual(fresh.status_code, 200, fresh.text[:300])

    # -- served pages: forms present, order right ------------------------------
    def test_served_driver_page_has_signin_and_reset_forms(self):
        html = read("static/driver.html")
        # Registration password fields exist.
        self.assertIn('id="reg-password"', html)
        self.assertIn('id="reg-password-confirm"', html)
        # Email+password sign-in comes FIRST, phone lookup below it.
        signin_at = html.index('id="signin-form"')
        lookup_at = html.index('id="lookup-form"')
        self.assertLess(signin_at, lookup_at)
        self.assertIn('id="signin-email"', html)
        self.assertIn('id="signin-password"', html)
        # Forgot-password link + form, and the reset form.
        self.assertIn('id="forgot-link"', html)
        self.assertIn('id="forgot-form"', html)
        self.assertIn('id="forgot-email"', html)
        self.assertIn('id="reset-block"', html)
        self.assertIn('id="reset-form"', html)
        self.assertIn('id="reset-password"', html)
        self.assertIn('id="reset-password-confirm"', html)
        # No password field may leak into a URL or log: the reset form
        # posts (no GET), and no reset token is rendered in the page.
        self.assertNotIn("?reset=", html)

    def test_served_driver_js_wires_signin_forgot_reset(self):
        js = read("static/js/driver.js")
        # Registration sends the password fields and validates them.
        self.assertIn('fd.append("password", password)', js)
        self.assertIn('fd.append("password_confirm", passwordConfirm)', js)
        self.assertIn("Password must be at least 6 characters.", js)
        self.assertIn("Passwords do not match.", js)
        # Sign-in posts to the signin endpoint and reuses the token flow.
        self.assertIn("/api/drivers/me/signin", js)
        # Forgot + reset endpoints wired; reset token read from the URL.
        self.assertIn("/api/drivers/me/forgot-password", js)
        self.assertIn("/api/drivers/me/reset-password", js)
        self.assertIn('get("reset")', js)

    def test_signout_already_exists_and_clears_token(self):
        # Profile "Log out" is the sign-out: it clears the stored
        # token and reloads to the sign-in screen. The label is
        # exactly "Log out" (owner order 2026-11-18); the old
        # "Register a different driver" wording is gone, and the
        # confirm wording and behaviour are unchanged.
        html = read("static/driver.html")
        self.assertIn('id="reset-driver-btn">Log out</button>', html)
        self.assertNotIn("Register a different driver", html)
        js = read("static/js/driver.js")
        handler = js[js.index("reset-driver-btn"):]
        self.assertIn("clearToken()", handler[:500])
        self.assertIn("Sign out this driver on this device and show registration again?",
                      handler[:500])


if __name__ == "__main__":
    unittest.main()
