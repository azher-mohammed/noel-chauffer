"""Tests for driver document verification: duplicate-file hashes,
photo sanity, and expiry dates.

Owner decisions 2026-11-19 (voice call):
- Duplicate check ("haan na", after asking how verification would
  work; the earlier "abhi nahi" deferral is lifted): the same file
  bytes on another driver, or in two slots of one registration, are
  rejected. Deterministic SHA-256 of the raw bytes; no OCR, no
  background check, no new required document.
- Expiry ("expiry ka aap khud padhna chahiye"; "agar driver expire
  wala laga diya to masla ho jayega"): the driver types the expiry
  date printed on the document; an expired document is REJECTED at
  registration, and the driver is told clearly to upload a fresh,
  valid one. OCR was investigated and not used (Render is a native
  Python Blueprint with no Tesseract binary; Azure AI Vision would
  need a new resource + key) — typed dates are deterministic and
  need no new key, cost or deploy change.

Scope: duplicate detection covers DriverDocument uploads only (the
profile photo has no document row and gets its own shape/size/blank
checks). Existing drivers are never blocked retroactively: rows
stored before file_hash/expires_on existed read as NULL.

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
_tmpdir = tempfile.mkdtemp(prefix="noel-docverify-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "docverify.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "docverify-secret-key"
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
    "inspection", "vehicle_permit", "vehicle_registration", "insurance_card",
]
FUTURE = "2030-01-01"


def _today_ny():
    from datetime import datetime

    return datetime.now(ZoneInfo("America/New_York")).date()


def _solid_jpeg(width, height, color):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="JPEG")
    return buf.getvalue()


class DocumentVerificationCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    # -- helpers ------------------------------------------------------------
    def files_for(self, overrides=None):
        """Distinct valid document photos per slot, plus the raw bytes
        (needed to assert stored hashes)."""
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
            "name": "Verify Driver",
            "phone": phone or f"+1555090{self._seq:04d}",
            "email": email or f"verify{self._seq}@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"V{self._seq:05d}",
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

    # -- happy path ---------------------------------------------------------
    def test_normal_registration_stores_hash_and_expiry(self):
        files, raw = self.files_for()
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        driver_id = resp.get_json()["driver"]["id"]
        with app_module.app.app_context():
            docs = app_module.DriverDocument.query.filter_by(
                driver_id=driver_id).all()
            self.assertEqual(len(docs), 6)
            by_type = {d.doc_type: d for d in docs}
            for field, doc_type in NY_DOC_FIELDS:
                self.assertEqual(
                    by_type[doc_type].file_hash,
                    hashlib.sha256(raw[field]).hexdigest(), doc_type)
                self.assertEqual(
                    by_type[doc_type].expires_on, date(2030, 1, 1), doc_type)

    def test_fh1_pdf_accepted_and_hashed(self):
        pdf = photo_factory.doc_pdf()
        files, _raw = self.files_for(
            overrides={"doc_fh1": (pdf, "fh1.pdf")})
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            doc = app_module.DriverDocument.query.filter_by(
                doc_type="fh1_insurance").first()
            self.assertEqual(doc.file_hash, hashlib.sha256(pdf).hexdigest())
            self.assertEqual(doc.expires_on, date(2030, 1, 1))

    # -- duplicates ---------------------------------------------------------
    def test_duplicate_across_drivers_rejected(self):
        files_a, raw_a = self.files_for()
        resp = self.register(files=files_a)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        # A second driver reuses driver A's DMV license photo; every
        # other slot is a fresh photo.
        files_b, _raw_b = self.files_for()
        files_b["doc_dmv_license"] = (
            io.BytesIO(raw_a["doc_dmv_license"]), "license.png")
        resp = self.register(files=files_b)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.get_json()["error"],
            "This document photo was already used for another driver "
            "account. Please upload your own document.")
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 1)

    def test_duplicate_across_doc_types_rejected(self):
        files_a, raw_a = self.files_for()
        self.assertEqual(self.register(files=files_a).status_code, 201)
        # A's license photo reused as B's TLC license photo.
        files_b, _raw_b = self.files_for()
        files_b["doc_tlc_license"] = (
            io.BytesIO(raw_a["doc_dmv_license"]), "tlc.png")
        resp = self.register(files=files_b)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already used for another driver account",
                      resp.get_json()["error"])

    def test_same_file_in_two_slots_rejected(self):
        shared = photo_factory.doc_photo()
        files, _raw = self.files_for(overrides={
            "doc_dmv_license": (shared, "license.png"),
            "doc_tlc_license": (shared, "tlc.png"),
        })
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("DMV driving license", error)
        self.assertIn("TLC License", error)
        self.assertIn("is the same as", error)
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 0)

    # -- photo sanity -------------------------------------------------------
    def test_blank_photo_rejected(self):
        white = _solid_jpeg(800, 600, "white")
        files, _raw = self.files_for(
            overrides={"doc_dmv_license": (white, "license.png")})
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("looks blank or unreadable", resp.get_json()["error"])
        self.assertIn("DMV driving license", resp.get_json()["error"])

    def test_blank_black_photo_rejected(self):
        black = _solid_jpeg(800, 600, "black")
        files, _raw = self.files_for(
            overrides={"doc_inspection": (black, "insp.png")})
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("looks blank or unreadable", resp.get_json()["error"])

    def test_tiny_photo_rejected(self):
        tiny = photo_factory.jpeg(100, 100)
        files, _raw = self.files_for(
            overrides={"doc_registration": (tiny, "reg.png")})
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("too small", resp.get_json()["error"])

    def test_unreadable_photo_rejected(self):
        files, _raw = self.files_for(overrides={
            "doc_dmv_license": (b"not an image at all", "license.png")})
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("could not be read", resp.get_json()["error"])

    def test_blank_profile_photo_rejected(self):
        white = _solid_jpeg(400, 500, "white")
        files, _raw = self.files_for()
        files["profile_photo"] = (io.BytesIO(white), "photo.jpg")
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("looks blank or unreadable", resp.get_json()["error"])

    # -- expiry -------------------------------------------------------------
    def test_expired_document_rejected(self):
        yesterday = (_today_ny() - timedelta(days=1)).isoformat()
        resp = self.register(expiry={"expiry_dmv_license": yesterday,
                                     "expiry_tlc_license": FUTURE,
                                     "expiry_fh1_insurance": FUTURE,
                                     "expiry_registration": FUTURE,
                                     "expiry_inspection": FUTURE,
                                     "expiry_vehicle_permit": FUTURE})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.get_json()["error"],
            "Your DMV driving license is expired — please upload a new, "
            "valid one.")
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 0)

    def test_expiry_today_accepted(self):
        today = _today_ny().isoformat()
        expiry = {f"expiry_{t}": FUTURE for t in EXPIRY_DOC_TYPES}
        expiry["expiry_dmv_license"] = today
        resp = self.register(expiry=expiry)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])

    def test_missing_expiry_rejected(self):
        resp = self.register(omit_expiry=["dmv_license"])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.get_json()["error"],
            "Please enter the expiry date for your DMV driving license.")

    def test_invalid_expiry_rejected(self):
        resp = self.register(expiry={"expiry_dmv_license": "not-a-date",
                                     "expiry_tlc_license": FUTURE,
                                     "expiry_fh1_insurance": FUTURE,
                                     "expiry_registration": FUTURE,
                                     "expiry_inspection": FUTURE,
                                     "expiry_vehicle_permit": FUTURE})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.get_json()["error"],
            "Please enter a valid expiry date for your DMV driving license.")

    def test_non_expiring_doc_types_need_no_expiry(self):
        # Profile Picture has no expiry; nothing else is required.
        resp = self.register()
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])

    # -- existing drivers unaffected ----------------------------------------
    def test_existing_drivers_unaffected(self):
        # A driver stored before file_hash/expires_on existed: NULLs
        # on his documents, no hash, no expiry — he keeps signing in
        # and working exactly as before.
        with app_module.app.app_context():
            driver = app_module.Driver(
                name="Legacy Driver", phone="+15550001111",
                email="legacy@test.com", car_model="Cadillac Escalade",
                car_year=2023, car_colour="Black", plate="LEGACY1",
                state="New York",
                profile_photo=photo_factory.VALID_PROFILE_PHOTO,
                bank_last4="6789", token="legacy-token")
            app_module.db.session.add(driver)
            app_module.db.session.flush()
            app_module.db.session.add(app_module.DriverDocument(
                driver_id=driver.id, doc_type="dmv_license",
                file=photo_factory.doc_photo(), mime="image/jpeg",
                original_name="license.png"))
            app_module.db.session.commit()
        resp = self.client.post("/api/drivers/me/lookup",
                                json={"phone": "+15550001111"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        # And a brand-new registration with different documents works.
        self.assertEqual(self.register().status_code, 201)

    # -- owner visibility ---------------------------------------------------
    def test_owner_drivers_show_expiries(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        self.owner_login()
        drivers = self.client.get("/api/owner/drivers").get_json()
        self.assertEqual(len(drivers), 1)
        expiries = drivers[0]["doc_expiries"]
        self.assertEqual(expiries["dmv_license"], FUTURE)
        self.assertEqual(expiries["fh1_insurance"], FUTURE)

    def test_flags_visible_to_owner(self):
        files_a, raw_a = self.files_for()
        self.assertEqual(self.register(files=files_a).status_code, 201)
        files_b, _raw_b = self.files_for()
        files_b["doc_dmv_license"] = (
            io.BytesIO(raw_a["doc_dmv_license"]), "license.png")
        resp = self.register(files=files_b)
        self.assertEqual(resp.status_code, 400)
        # Flags are owner-only.
        self.assertEqual(
            self.client.get("/api/owner/document-flags").status_code, 401)
        self.owner_login()
        flags = self.client.get("/api/owner/document-flags").get_json()["flags"]
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["reason"], "duplicate_other_driver")
        self.assertEqual(flags[0]["doc_label"], "DMV driving license")
        self.assertEqual(flags[0]["phone"], "+15550900002")

    def test_states_endpoint_marks_expiry_docs(self):
        states = self.client.get("/api/states").get_json()
        self.assertTrue(states["documents"]["dmv_license"]["has_expiry"])
        self.assertTrue(states["documents"]["fh1_insurance"]["has_expiry"])
        self.assertFalse(states["documents"]["profile_picture"]["has_expiry"])


if __name__ == "__main__":
    unittest.main()
