"""Tests for compulsory driver documents at registration.

Owner decision 2026-11-17 (voice call, his dictation): "Compulsory
documents un log upload karna hi zaroori hai. Nahi to registration
nahi hoga." — drivers MUST upload every compulsory document, or
registration does not happen. Refinement in the same call: "Agar woh
document miss kar raha hai to missing document bol ke batana." — when
a driver is missing a document, the app must TELL him by saying
"missing document", naming each missing item by its exact label.

Scope is completion only (uploaded or not), NOT verification: no
genuineness / duplicate / hash / OCR checks (deferred by the owner,
"abhi nahi", 2026-11-16). The gate applies to registrations
completing after deploy; drivers registered before this change are
not blocked retroactively.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
import uuid

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-compdocs-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "compdocs-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# multipart field name -> exact user-visible label, in form order.
FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_tlc_license", "TLC License", "tlc.png"),
    ("doc_fh1", "FH-1 Insurance Card", "fh1.png"),
    ("doc_registration", "Commercial Vehicle Registration", "reg.png"),
    ("doc_inspection", "NYS DMV Inspection", "insp.png"),
    ("doc_vehicle_permit", "TLC-for-hire Vehicle Permit", "permit.png"),
]


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class CompulsoryDocumentsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, files):
        self._seq += 1
        data = {
            "name": "Comp Driver", "phone": f"+1555006{self._seq:04d}",
            "email": "comp@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"CD{self._seq:05d}",
            "state": "New York", "bank_account_number": "123456789", "bank_routing_number": "021000021",
        }
        data.update(files)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    def all_files(self, omit=()):
        files = {}
        for field, _label, fname in FIELDS:
            if field in omit:
                continue
            # The profile photo must be a real portrait image
            # (server shape/size rules); other docs accept any bytes.
            data = (photo_factory.VALID_PROFILE_PHOTO
                    if field == "profile_photo" else b"fake doc")
            files[field] = (io.BytesIO(data), fname)
        return files

    # -- server gate ---------------------------------------------------------
    def test_missing_each_document_rejected_and_named(self):
        # Every single missing item blocks registration and is named.
        for field, label, _fname in FIELDS:
            with self.subTest(field=field):
                resp = self.register(self.all_files(omit={field}))
                self.assertEqual(resp.status_code, 400,
                                 resp.get_data(as_text=True)[:200])
                error = resp.get_json()["error"]
                self.assertIn("Missing document", error)
                self.assertIn(label, error, "missing item must be named: %s" % label)

    def test_missing_all_documents_lists_every_item(self):
        resp = self.register({})
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        error = resp.get_json()["error"]
        self.assertTrue(error.startswith("Missing document: "), error)
        for _field, label, _fname in FIELDS:
            self.assertIn(label, error, label)
        # Listed in form order: Profile Picture first, DMV driving license second.
        self.assertLess(error.index("Profile Picture"), error.index("DMV driving license"))

    def test_missing_two_documents_lists_both(self):
        resp = self.register(self.all_files(omit={"doc_tlc_license", "doc_inspection"}))
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("TLC License", error)
        self.assertIn("NYS DMV Inspection", error)
        self.assertNotIn("Profile Picture", error)
        self.assertNotIn("DMV driving license", error)

    def test_rejection_creates_no_driver_record(self):
        # The gate runs before anything is stored: a rejected attempt
        # leaves no driver row behind (no partial registration).
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 0)
        resp = self.register(self.all_files(omit={"doc_fh1"}))
        self.assertEqual(resp.status_code, 400)
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 0)
        resp = self.client.post("/api/drivers/me/lookup",
                                json={"phone": "+15550060001"})
        self.assertEqual(resp.status_code, 404)

    def test_all_documents_present_registers(self):
        resp = self.register(self.all_files())
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        docs = resp.get_json()["driver"]["docs"]
        self.assertEqual(len(docs), 7)
        self.assertTrue(all(v == "completed" for v in docs.values()), str(docs))

    def test_fh1_pdf_still_accepted(self):
        files = self.all_files()
        files["doc_fh1"] = (io.BytesIO(b"%PDF- fake"), "fh1.pdf")
        resp = self.register(files)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["driver"]["docs"]["fh1_insurance"], "completed")

    def test_invalid_file_still_rejected_before_missing_check(self):
        # A present-but-invalid upload keeps its own error (PDF for a
        # photo-only item), rather than being reported as missing.
        files = self.all_files(omit={"doc_inspection"})
        files["doc_dmv_license"] = (io.BytesIO(b"%PDF- fake"), "license.pdf")
        resp = self.register(files)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("doc_dmv_license", resp.get_json()["error"])

    # -- no retroactive blocking ---------------------------------------------
    def test_legacy_driver_without_documents_still_works(self):
        # A driver registered before the gate (no uploads at all) must
        # keep signing in and going available exactly as before.
        with app_module.app.app_context():
            driver = app_module.Driver(
                name="Legacy Driver", phone="+15550009999", email="legacy@test.com",
                car_model="Cadillac CT6", car_year=2023, vehicle_class="sedan",
                car_colour="Black", plate="LEGACY1",
                bank_encrypted=app_module.encrypt_bank("123456789", "021000021"),
                bank_last4="6789", token=uuid.uuid4().hex)
            app_module.db.session.add(driver)
            app_module.db.session.commit()
            driver_id = driver.id
        resp = self.client.post("/api/drivers/me/lookup", json={"phone": "+15550009999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        token = resp.get_json()["token"]
        resp = self.client.get("/api/drivers/me", headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        docs = resp.get_json()["driver"]["docs"]
        self.assertEqual(docs["dmv_license"], "missing")
        resp = self.client.post("/api/drivers/me/availability", json={"available": True},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            driver = app_module.Driver.query.get(driver_id)
            self.assertTrue(driver.available)

    # -- client gate -----------------------------------------------------------
    def test_client_gate_names_missing_documents(self):
        driver_js = read("static/js/driver.js")
        # The gate runs in the submit handler before the request is built.
        gate = driver_js.index("Missing document: ")
        submit = driver_js.index('addEventListener("submit"')
        fetch = driver_js.index("/api/drivers/register", submit)
        self.assertLess(submit, gate)
        self.assertLess(gate, fetch)
        self.assertIn("missingDocs.join", driver_js)
        self.assertIn("Please upload all required documents to complete registration.",
                      driver_js)
        # The form is not cleared on rejection: no reset in the gate path.
        self.assertNotIn("register-form\" reset", driver_js)

    def test_registration_form_states_documents_are_required(self):
        html = read("static/driver.html")
        self.assertIn("All 7 items are required", html)
        self.assertIn("registration cannot be completed until every document is uploaded",
                      html)

    def test_server_labels_match_client_labels(self):
        # One wording everywhere: server DOC_LABELS == client DOC_LABELS.
        driver_js = read("static/js/driver.js")
        for doc_type, label in app_module.DOC_LABELS.items():
            self.assertIn('"%s"' % label, driver_js, label)
        self.assertEqual(list(app_module.DOC_LABELS), app_module.DOC_TYPES)


if __name__ == "__main__":
    unittest.main()
