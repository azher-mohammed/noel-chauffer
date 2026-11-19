"""Tests for driver document expiry enforcement: 10-day advance alert
for all documents + registration deactivated on expiry, auto-reactivate
on re-upload.

Owner decisions 2026-11-19 (voice call):
- Ten-day advance alert ("poore documents ki expiry 10 din pehle hi
  karna", "ten days before"): every document with a stored expiry date
  alerts once when its expiry comes within 10 days — in-app notice,
  SMS + email via the outbox, owner-dashboard event. One alert per
  document per expiry (expiry_alert_sent_at flag); re-upload with a
  different expiry resets the flag.
- Expiry = registration deactivated ("jaisa expire ho jayega phir bhi
  document hai to uska band kar dena... registration band kar dena,
  phir wo registration paper upload karega, phir active karna"): a
  driver with any stored expiry date in the past is blocked — cannot
  go available, gets no offers — until he re-uploads that document
  with a valid future expiry date, at which point the block lifts
  automatically. Sign-in still works while blocked (same as the 48h
  fault suspension), so the driver sees the notice and can re-upload.
- Only a STORED expiry date can block: documents with no expiry on
  file (rows created before the verification build) are never blocked
  retroactively.
- No OCR: the driver still types the expiry date (see
  test_document_verification.py); the stored typed date is the source
  of truth for alerts and blocking.

Run:  python -m unittest discover -s tests -v
"""

import hashlib
import io
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from zoneinfo import ZoneInfo

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-expiry-alerts-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "expiry-alerts-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
from PIL import Image  # noqa: E402

NY_DOC_FIELDS = [
    ("doc_dmv_license", "dmv_license"),
    ("doc_tlc_license", "tlc_license"),
    ("doc_fh1", "fh1_insurance"),
    ("doc_registration", "registration"),
    ("doc_inspection", "inspection"),
    ("doc_vehicle_permit", "vehicle_permit"),
]
EXPIRY_DOC_TYPES = [
    "dmv_license", "tlc_license", "fh1_insurance", "registration",
    "inspection", "vehicle_permit",
]
FUTURE = "2030-01-01"


def _today_ny():
    from datetime import datetime

    return datetime.now(ZoneInfo("America/New_York")).date()


def _solid_jpeg(width, height, color):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="JPEG")
    return buf.getvalue()


class ExpiryAlertsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    # -- helpers ------------------------------------------------------------
    def files_for(self, overrides=None):
        files, raw = {}, {}
        files["profile_photo"] = (
            io.BytesIO(photo_factory.VALID_PROFILE_PHOTO), "photo.jpg")
        for field, _doc_type in NY_DOC_FIELDS:
            data = photo_factory.doc_photo()
            raw[field] = data
            files[field] = (io.BytesIO(data), field + ".png")
        if overrides:
            for field, (data, fname) in overrides.items():
                raw[field] = data
                files[field] = (io.BytesIO(data), fname)
        return files, raw

    def register(self, files=None, raw=None, phone=None, email=None,
                 expiry=None, omit_expiry=()):
        self._seq += 1
        data = {
            "name": "Expiry Driver",
            "phone": phone or f"+1555080{self._seq:04d}",
            "email": email or f"expiry{self._seq}@test.com",
            "password": "secret123",
            "password_confirm": "secret123",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"E{self._seq:05d}",
            "state": "New York",
            "bank_account_number": "123456789",
            "bank_routing_number": "021000021",
        }
        use_expiry = dict(expiry) if expiry is not None else {
            f"expiry_{t}": FUTURE for t in EXPIRY_DOC_TYPES}
        for t in omit_expiry:
            use_expiry.pop(f"expiry_{t}", None)
        data.update(use_expiry)
        if files is None:
            files, raw = self.files_for()
        data.update(files)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def driver_headers(self, token):
        return {"X-Driver-Token": token}

    def set_expiry(self, driver_id, doc_type, expires_on):
        """Set a stored expiry date directly (registration rejects
        past dates, so expiry itself is simulated this way)."""
        with app_module.app.app_context():
            doc = app_module.DriverDocument.query.filter_by(
                driver_id=driver_id, doc_type=doc_type).first()
            self.assertIsNotNone(doc, f"no doc row for {doc_type}")
            doc.expires_on = expires_on
            app_module.db.session.commit()

    def clear_expiry(self, driver_id, doc_type):
        self.set_expiry(driver_id, doc_type, None)

    def run_alerts(self):
        with app_module.app.app_context():
            return app_module.run_expiry_alerts()

    def outbox_counts(self):
        with app_module.app.app_context():
            rows = app_module.OutboxMessage.query.all()
        sms = [r for r in rows if r.channel == "sms"]
        email = [r for r in rows if r.channel == "email"]
        return sms, email

    # -- 10-day alert -------------------------------------------------------
    def test_alert_fires_once_inside_window_all_types(self):
        soon = (_today_ny() + timedelta(days=5)).isoformat()
        expiry = {f"expiry_{t}": soon for t in EXPIRY_DOC_TYPES}
        resp = self.register(expiry=expiry)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        alerted = self.run_alerts()
        self.assertEqual(len(alerted), 6)
        self.assertEqual(
            sorted(a["doc_type"] for a in alerted), sorted(EXPIRY_DOC_TYPES))
        sms, email = self.outbox_counts()
        self.assertEqual(len(sms), 6)
        self.assertEqual(len(email), 6)
        self.assertIn("DMV driving license", sms[0].body)
        # Idempotent: a second run alerts nothing.
        self.assertEqual(self.run_alerts(), [])
        sms, email = self.outbox_counts()
        self.assertEqual(len(sms), 6)
        self.assertEqual(len(email), 6)

    def test_no_alert_beyond_10_days(self):
        resp = self.register()  # all expiries 2030
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self.run_alerts(), [])
        sms, email = self.outbox_counts()
        self.assertEqual(sms, [])
        self.assertEqual(email, [])

    def test_alert_boundary_10_days(self):
        in_10 = (_today_ny() + timedelta(days=10)).isoformat()
        in_11 = (_today_ny() + timedelta(days=11)).isoformat()
        expiry = {f"expiry_{t}": FUTURE for t in EXPIRY_DOC_TYPES}
        expiry["expiry_dmv_license"] = in_10
        expiry["expiry_tlc_license"] = in_11
        resp = self.register(expiry=expiry)
        self.assertEqual(resp.status_code, 201)
        alerted = self.run_alerts()
        self.assertEqual([a["doc_type"] for a in alerted], ["dmv_license"])

    def test_already_inside_window_alerts_immediately(self):
        tomorrow = (_today_ny() + timedelta(days=1)).isoformat()
        expiry = {f"expiry_{t}": FUTURE for t in EXPIRY_DOC_TYPES}
        expiry["expiry_registration"] = tomorrow
        resp = self.register(expiry=expiry)
        self.assertEqual(resp.status_code, 201)
        alerted = self.run_alerts()
        self.assertEqual(len(alerted), 1)
        self.assertEqual(alerted[0]["doc_type"], "registration")
        self.assertEqual(alerted[0]["days_left"], 1)

    def test_expired_doc_alerts_once_expired_wording(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        driver_id = resp.get_json()["driver"]["id"]
        self.set_expiry(driver_id, "dmv_license",
                        _today_ny() - timedelta(days=1))
        alerted = self.run_alerts()
        self.assertEqual(len(alerted), 1)
        self.assertEqual(alerted[0]["days_left"], -1)
        sms, _email = self.outbox_counts()
        self.assertEqual(len(sms), 1)
        self.assertIn("expired", sms[0].body)
        self.assertIn("DMV driving license", sms[0].body)
        self.assertEqual(self.run_alerts(), [])

    def test_alert_covers_generic_expiry_types_too(self):
        # A non-NY document type that stores an expiry (e.g. a generic
        # vehicle registration) is alerted the same way.
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        driver_id = resp.get_json()["driver"]["id"]
        with app_module.app.app_context():
            app_module.db.session.add(app_module.DriverDocument(
                driver_id=driver_id, doc_type="vehicle_registration",
                file=b"generic-reg", mime="image/png",
                original_name="reg.png",
                file_hash=hashlib.sha256(b"generic-reg").hexdigest(),
                expires_on=_today_ny() + timedelta(days=3)))
            app_module.db.session.commit()
        alerted = self.run_alerts()
        self.assertEqual([a["doc_type"] for a in alerted],
                         ["vehicle_registration"])
        self.assertEqual(alerted[0]["days_left"], 3)

    def test_driver_me_exposes_expiry_fields(self):
        in_5 = (_today_ny() + timedelta(days=5)).isoformat()
        expiry = {f"expiry_{t}": FUTURE for t in EXPIRY_DOC_TYPES}
        expiry["expiry_tlc_license"] = in_5
        resp = self.register(expiry=expiry)
        self.assertEqual(resp.status_code, 201)
        token = resp.get_json()["token"]
        me = self.client.get("/api/drivers/me",
                             headers=self.driver_headers(token))
        self.assertEqual(me.status_code, 200)
        d = me.get_json()["driver"]
        self.assertFalse(d["expiry_blocked"])
        self.assertEqual(d["expired_docs"], [])
        self.assertEqual(len(d["expiring_docs"]), 1)
        self.assertEqual(d["expiring_docs"][0]["doc_type"], "tlc_license")
        self.assertEqual(d["expiring_docs"][0]["days_left"], 5)
        self.assertEqual(d["doc_expiries"]["tlc_license"], in_5)
        self.assertIn("dmv_license", d["expiry_doc_types"])

    # -- expiry = registration deactivated ----------------------------------
    def test_expired_blocks_availability_offers_accept(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        driver_id = resp.get_json()["driver"]["id"]
        token = resp.get_json()["token"]
        self.set_expiry(driver_id, "dmv_license",
                        _today_ny() - timedelta(days=1))
        # Cannot go available (409, names the document).
        r = self.client.post("/api/drivers/me/availability",
                             json={"available": True},
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 409)
        self.assertIn("DMV driving license", r.get_json()["error"])
        self.assertIn("paused", r.get_json()["error"])
        # Going offline is still allowed.
        r = self.client.post("/api/drivers/me/availability",
                             json={"available": False},
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 200)
        # No offers.
        r = self.client.get("/api/drivers/me/offers",
                            headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), [])
        # Direct accept must fail too (defense in depth).
        r = self.client.post("/api/drivers/me/offers/999999/accept",
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 409)
        self.assertIn("paused", r.get_json()["error"])
        # driver_me reports the block.
        me = self.client.get("/api/drivers/me",
                             headers=self.driver_headers(token))
        d = me.get_json()["driver"]
        self.assertTrue(d["expiry_blocked"])
        self.assertEqual(len(d["expired_docs"]), 1)
        self.assertEqual(d["expired_docs"][0]["doc_type"], "dmv_license")

    def test_signin_works_while_blocked(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        driver_id = resp.get_json()["driver"]["id"]
        email = resp.get_json()["driver"]["email"]
        self.set_expiry(driver_id, "tlc_license",
                        _today_ny() - timedelta(days=2))
        r = self.client.post("/api/drivers/me/signin",
                             json={"email": email, "password": "secret123"})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:200])
        self.assertIn("token", r.get_json())
        me = self.client.get(
            "/api/drivers/me",
            headers=self.driver_headers(r.get_json()["token"]))
        self.assertTrue(me.get_json()["driver"]["expiry_blocked"])

    def test_no_expiry_on_file_not_blocked(self):
        # Legacy driver: documents stored before the verification
        # build have no expiry on file — never blocked retroactively,
        # and never alerted.
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        driver_id = resp.get_json()["driver"]["id"]
        token = resp.get_json()["token"]
        with app_module.app.app_context():
            for doc in app_module.DriverDocument.query.filter_by(
                    driver_id=driver_id).all():
                doc.expires_on = None
            app_module.db.session.commit()
        self.assertEqual(self.run_alerts(), [])
        r = self.client.post("/api/drivers/me/availability",
                             json={"available": True},
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 200)
        me = self.client.get("/api/drivers/me",
                             headers=self.driver_headers(token))
        self.assertFalse(me.get_json()["driver"]["expiry_blocked"])

    # -- re-upload reactivates ----------------------------------------------
    def test_reupload_unblocks(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        driver_id = resp.get_json()["driver"]["id"]
        token = resp.get_json()["token"]
        self.set_expiry(driver_id, "dmv_license",
                        _today_ny() - timedelta(days=1))
        me = self.client.get("/api/drivers/me",
                             headers=self.driver_headers(token))
        self.assertTrue(me.get_json()["driver"]["expiry_blocked"])
        # Re-upload the expired document with a fresh photo + future date.
        new_photo = photo_factory.doc_photo()
        data = {
            "doc_type": "dmv_license",
            "expiry_dmv_license": FUTURE,
            "document": (io.BytesIO(new_photo), "license-new.png"),
        }
        r = self.client.post("/api/drivers/me/documents", data=data,
                             content_type="multipart/form-data",
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        self.assertFalse(r.get_json()["expiry_blocked"])
        # Availability works again.
        r = self.client.post("/api/drivers/me/availability",
                             json={"available": True},
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 200)

    def test_reupload_resets_alert_flag_only_on_changed_expiry(self):
        in_5 = (_today_ny() + timedelta(days=5)).isoformat()
        in_6 = (_today_ny() + timedelta(days=6)).isoformat()
        expiry = {f"expiry_{t}": FUTURE for t in EXPIRY_DOC_TYPES}
        expiry["expiry_dmv_license"] = in_5
        resp = self.register(expiry=expiry)
        self.assertEqual(resp.status_code, 201)
        token = resp.get_json()["token"]
        self.assertEqual(len(self.run_alerts()), 1)
        # Re-upload with a LATER expiry: flag resets, new alert fires.
        data = {"doc_type": "dmv_license", "expiry_dmv_license": in_6,
                "document": (io.BytesIO(photo_factory.doc_photo()),
                             "license-v2.png")}
        r = self.client.post("/api/drivers/me/documents", data=data,
                             content_type="multipart/form-data",
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        alerted = self.run_alerts()
        self.assertEqual(len(alerted), 1)
        self.assertEqual(alerted[0]["expires_on"], in_6)
        # Re-upload with the SAME expiry: flag stays set, no re-alert.
        data = {"doc_type": "dmv_license", "expiry_dmv_license": in_6,
                "document": (io.BytesIO(photo_factory.doc_photo()),
                             "license-v3.png")}
        r = self.client.post("/api/drivers/me/documents", data=data,
                             content_type="multipart/form-data",
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.run_alerts(), [])

    def test_reupload_same_bytes_same_type_allowed(self):
        files, raw = self.files_for()
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 201)
        token = resp.get_json()["token"]
        data = {"doc_type": "dmv_license", "expiry_dmv_license": FUTURE,
                "document": (io.BytesIO(raw["doc_dmv_license"]),
                             "license.png")}
        r = self.client.post("/api/drivers/me/documents", data=data,
                             content_type="multipart/form-data",
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])

    def test_reupload_rejects_duplicate_other_driver(self):
        files_a, raw_a = self.files_for()
        resp_a = self.register(files=files_a)
        self.assertEqual(resp_a.status_code, 201)
        resp_b = self.register()
        self.assertEqual(resp_b.status_code, 201)
        token_b = resp_b.get_json()["token"]
        data = {"doc_type": "dmv_license", "expiry_dmv_license": FUTURE,
                "document": (io.BytesIO(raw_a["doc_dmv_license"]),
                             "license.png")}
        r = self.client.post("/api/drivers/me/documents", data=data,
                             content_type="multipart/form-data",
                             headers=self.driver_headers(token_b))
        self.assertEqual(r.status_code, 400)
        self.assertIn("already used for another driver",
                      r.get_json()["error"])

    def test_reupload_rejects_expired_date(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        token = resp.get_json()["token"]
        yesterday = (_today_ny() - timedelta(days=1)).isoformat()
        data = {"doc_type": "dmv_license", "expiry_dmv_license": yesterday,
                "document": (io.BytesIO(photo_factory.doc_photo()),
                             "license.png")}
        r = self.client.post("/api/drivers/me/documents", data=data,
                             content_type="multipart/form-data",
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 400)
        self.assertIn("is expired", r.get_json()["error"])

    def test_reupload_rejects_unknown_type(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        token = resp.get_json()["token"]
        data = {"doc_type": "profile_picture",
                "document": (io.BytesIO(photo_factory.doc_photo()),
                             "photo.png")}
        r = self.client.post("/api/drivers/me/documents", data=data,
                             content_type="multipart/form-data",
                             headers=self.driver_headers(token))
        self.assertEqual(r.status_code, 400)

    # -- owner endpoints ------------------------------------------------------
    def test_owner_expiring_documents_endpoint(self):
        in_4 = (_today_ny() + timedelta(days=4)).isoformat()
        expiry = {f"expiry_{t}": FUTURE for t in EXPIRY_DOC_TYPES}
        expiry["expiry_inspection"] = in_4
        resp = self.register(expiry=expiry)
        self.assertEqual(resp.status_code, 201)
        driver_id = resp.get_json()["driver"]["id"]
        self.set_expiry(driver_id, "registration",
                        _today_ny() - timedelta(days=1))
        # Unauthenticated: 401.
        anon = app_module.app.test_client()
        r = anon.get("/api/owner/expiring-documents")
        self.assertEqual(r.status_code, 401)
        self.owner_login()
        r = self.client.get("/api/owner/expiring-documents")
        self.assertEqual(r.status_code, 200)
        rows = r.get_json()["documents"]
        by_type = {row["doc_type"]: row for row in rows}
        self.assertIn("inspection", by_type)
        self.assertIn("registration", by_type)
        self.assertEqual(by_type["inspection"]["status"], "expiring_soon")
        self.assertEqual(by_type["inspection"]["days_left"], 4)
        self.assertEqual(by_type["registration"]["status"], "expired")
        self.assertEqual(by_type["registration"]["days_left"], -1)
        self.assertFalse(by_type["inspection"]["alert_sent"])

    def test_run_expiry_alerts_endpoint_auth(self):
        # No owner session and no cron secret configured in tests.
        anon = app_module.app.test_client()
        r = anon.post("/api/owner/run-expiry-alerts", json={})
        self.assertEqual(r.status_code, 401)
        self.owner_login()
        r = self.client.post("/api/owner/run-expiry-alerts", json={})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"alerted": []})


if __name__ == "__main__":
    unittest.main()
