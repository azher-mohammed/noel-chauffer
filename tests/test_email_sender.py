"""Tests for the Resend email sender wiring.

Owner decision 2026-11-18 ("Resend kar dena na"): queued email
messages are sent through Resend once the owner connects an account.
Until the owner completes the Resend account + domain verification +
API key steps, everything stays outbox-only, exactly as before —
and live sending is UNVERIFIED.

Rules pinned here (mocked HTTP only — never a real send, never a
real key in tests):
- No key set → no HTTP call at all, and the outbox row is still
  queued (sent_at stays NULL).
- A mocked successful send marks the row sent (sent_at set); the
  request carries the right from/to/subject/body and the key only
  in the Authorization header.
- A mocked failed send (HTTP error or exception) leaves the row
  queued and never affects the caller's response.
- SMS rows never attempt a send (Resend is email-only).
- The key never appears in logs or API responses.
- The reset email uses its own subject; other emails use the
  neutral default subject; RESEND_FROM overrides the sender.
- The owner outbox API exposes sent_at, and the dashboard shows
  Sent/Queued per row.

Run:  python -m unittest discover -s tests -v
"""

import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-sender-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "sender-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import email_sender  # noqa: E402
import photo_factory  # noqa: E402

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

FAKE_KEY = "re_test_fake_key_123"


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def ok_response(status=200):
    """A mocked urlopen return value: context manager with .status."""
    resp = mock.MagicMock()
    resp.__enter__.return_value.status = status
    return resp


def request_parts(mock_urlopen):
    """(url, headers dict, json payload) of the captured request."""
    req = mock_urlopen.call_args[0][0]
    headers = dict(req.header_items())
    payload = json.loads(req.data.decode("utf-8"))
    return req.full_url, headers, payload


class EmailSenderCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, email="sender@test.com", omit_password=False):
        self._seq += 1
        data = {
            "name": "Sender Driver", "phone": f"+1555008{self._seq:04d}",
            "email": email,
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"SN{self._seq:05d}",
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
        }
        if not omit_password:
            data["password"] = "secret123"
            data["password_confirm"] = "secret123"
        for field, fname in FIELDS:
            data[field] = (io.BytesIO(
                photo_factory.VALID_PROFILE_PHOTO
                if field == "profile_photo" else photo_factory.doc_photo()), fname)
        resp = self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.text[:300])
        return resp

    def outbox_rows(self):
        with app_module.app.app_context():
            return app_module.OutboxMessage.query.order_by(
                app_module.OutboxMessage.id).all()

    # -- unconfigured: zero HTTP, behaviour unchanged -------------------------
    def test_no_key_no_http_call(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": ""}), \
                mock.patch.object(email_sender, "urlopen") as mock_urlopen:
            result = email_sender.send_email("a@test.com", "Hi", "body")
        self.assertEqual(result, email_sender.NOT_CONFIGURED)
        mock_urlopen.assert_not_called()

    def test_no_key_row_still_queued(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": ""}), \
                mock.patch.object(email_sender, "urlopen") as mock_urlopen, \
                app_module.app.app_context():
            app_module.add_outbox("email", "a@test.com", "hello")
            app_module.db.session.commit()
        mock_urlopen.assert_not_called()
        rows = self.outbox_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].sent_at)

    def test_is_configured_follows_env(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": ""}):
            self.assertFalse(email_sender.is_configured())
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY}):
            self.assertTrue(email_sender.is_configured())

    # -- configured: mocked success -------------------------------------------
    def test_successful_send_marks_sent(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY}), \
                mock.patch.object(email_sender, "urlopen",
                                  return_value=ok_response(200)) as mock_urlopen, \
                app_module.app.app_context():
            app_module.add_outbox("email", "a@test.com", "hello body")
            app_module.db.session.commit()
        rows = self.outbox_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0].sent_at)
        url, headers, payload = request_parts(mock_urlopen)
        self.assertEqual(url, "https://api.resend.com/emails")
        self.assertEqual(headers.get("Authorization"), "Bearer " + FAKE_KEY)
        self.assertEqual(payload["from"], "Noel Chauffer <support@noelchauffer.com>")
        self.assertEqual(payload["to"], ["a@test.com"])
        self.assertEqual(payload["subject"], "Noel Chauffer")
        self.assertEqual(payload["text"], "hello body")

    def test_custom_subject_and_from_override(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY,
                                          "RESEND_FROM": "Team <team@example.com>"}), \
                mock.patch.object(email_sender, "urlopen",
                                  return_value=ok_response(200)) as mock_urlopen, \
                app_module.app.app_context():
            app_module.add_outbox("email", "a@test.com", "body",
                                  subject="Custom subject")
            app_module.db.session.commit()
        _url, _headers, payload = request_parts(mock_urlopen)
        self.assertEqual(payload["from"], "Team <team@example.com>")
        self.assertEqual(payload["subject"], "Custom subject")

    def test_reset_email_uses_reset_subject(self):
        self.register()
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY}), \
                mock.patch.object(email_sender, "urlopen",
                                  return_value=ok_response(200)) as mock_urlopen:
            resp = self.client.post("/api/drivers/me/forgot-password",
                                    json={"email": "sender@test.com"})
        self.assertEqual(resp.status_code, 200)
        _url, _headers, payload = request_parts(mock_urlopen)
        self.assertEqual(payload["subject"], "Reset your Noel Chauffer password")
        self.assertEqual(payload["to"], ["sender@test.com"])
        self.assertIn("reset your driver app password", payload["text"])
        self.assertIn("/driver?reset=", payload["text"])
        rows = self.outbox_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0].sent_at)

    def test_create_password_email_uses_create_subject(self):
        # A driver without a password hash gets the create-password
        # email (subject + body), not the reset email — owner
        # decision 2026-11-18 (Sana Baga).
        self.register(email="legacy@test.com", omit_password=True)
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY}), \
                mock.patch.object(email_sender, "urlopen",
                                  return_value=ok_response(200)) as mock_urlopen:
            resp = self.client.post("/api/drivers/me/forgot-password",
                                    json={"email": "legacy@test.com"})
        self.assertEqual(resp.status_code, 200)
        _url, _headers, payload = request_parts(mock_urlopen)
        self.assertEqual(payload["subject"],
                         "Create your Noel Chauffer driver password")
        self.assertEqual(payload["to"], ["legacy@test.com"])
        self.assertIn("create your driver app password", payload["text"])
        self.assertNotIn("reset your driver app password", payload["text"])
        self.assertIn("/driver?reset=", payload["text"])
        rows = self.outbox_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0].sent_at)

    # -- configured: mocked failure -------------------------------------------
    def test_http_error_row_stays_queued(self):
        error = HTTPError("https://api.resend.com/emails", 500, "boom", {}, io.BytesIO(b"{}"))
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY}), \
                mock.patch.object(email_sender, "urlopen", side_effect=error), \
                app_module.app.app_context():
            app_module.add_outbox("email", "a@test.com", "hello")
            app_module.db.session.commit()
        rows = self.outbox_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].sent_at)

    def test_exception_row_stays_queued_caller_unaffected(self):
        self.register()
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY}), \
                mock.patch.object(email_sender, "urlopen",
                                  side_effect=URLError("boom")):
            resp = self.client.post("/api/drivers/me/forgot-password",
                                    json={"email": "sender@test.com"})
        # The caller still gets the normal generic response.
        self.assertEqual(resp.status_code, 200)
        self.assertIn("password reset instructions", resp.get_json()["message"])
        rows = self.outbox_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].sent_at)

    def test_non_2xx_status_is_failure(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY}), \
                mock.patch.object(email_sender, "urlopen",
                                  return_value=ok_response(400)):
            result = email_sender.send_email("a@test.com", "Hi", "body")
        self.assertEqual(result, email_sender.FAILED)

    # -- SMS never touches the sender ------------------------------------------
    def test_sms_never_attempts_send(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY}), \
                mock.patch.object(email_sender, "urlopen") as mock_urlopen, \
                app_module.app.app_context():
            app_module.add_outbox("sms", "+15550001111", "hello sms")
            app_module.db.session.commit()
        mock_urlopen.assert_not_called()
        rows = self.outbox_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0].sent_at)

    # -- key secrecy ------------------------------------------------------------
    def test_key_never_in_logs(self):
        secret = "re_SECRETKEY123"
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": secret}), \
                mock.patch.object(email_sender, "urlopen",
                                  side_effect=URLError("boom")), \
                self.assertLogs("noel-chauffer.email", level="WARNING") as logs:
            email_sender.send_email("a@test.com", "Hi", "body")
        self.assertNotIn(secret, "\n".join(logs.output))

    def test_key_never_in_api_responses(self):
        self.register()
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": FAKE_KEY}), \
                mock.patch.object(email_sender, "urlopen",
                                  side_effect=URLError("boom")):
            forgot = self.client.post("/api/drivers/me/forgot-password",
                                      json={"email": "sender@test.com"})
            self.client.post("/api/owner/login", json={"pin": "9999"})
            outbox = self.client.get("/api/owner/outbox")
        self.assertNotIn(FAKE_KEY, forgot.text)
        self.assertNotIn(FAKE_KEY, outbox.text)

    # -- owner dashboard: sent state ---------------------------------------------
    def test_owner_outbox_includes_sent_at(self):
        with mock.patch.dict(os.environ, {"RESEND_API_KEY": ""}), \
                app_module.app.app_context():
            app_module.add_outbox("email", "a@test.com", "hello")
            app_module.db.session.commit()
        self.client.post("/api/owner/login", json={"pin": "9999"})
        resp = self.client.get("/api/owner/outbox")
        self.assertEqual(resp.status_code, 200)
        items = resp.get_json()
        self.assertEqual(len(items), 1)
        self.assertIn("sent_at", items[0])
        self.assertIsNone(items[0]["sent_at"])

    def test_owner_dashboard_shows_sent_queued(self):
        js = read("static/js/owner.js")
        self.assertIn("sent_at", js)
        self.assertIn('"Sent"', js)
        self.assertIn('"Queued"', js)
        html = read("static/owner.html")
        self.assertIn("Sent once delivered", html)


if __name__ == "__main__":
    unittest.main()
