"""Tests for the Uber-style plate format check in driver registration.

Owner decision 2026-11-17 (widget tap, "Format check laga do"):
registration validates the typed plate number, client-side and
server-side, with one generic US rule — spaces and dashes ignored,
2-8 letters or digits, stored uppercase with spaces/dashes removed.
No per-state patterns (nothing invented). The customer plate display
stays exactly as-is: the owner picked the format check ONLY and did
not pick the bigger customer display.

Existing drivers are never blocked retroactively: sign-in, /me, Go
available and already-stored plates (whatever their format) keep
working untouched. No migration, no backfill, no re-validation of
stored plates.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import secrets
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-platefmt-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "platefmt-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NY_FIELDS = [
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


class PlateFormatCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, plate, phone=None):
        self._seq += 1
        data = {
            "name": "Plate Driver", "phone": phone or f"+1555022{self._seq:04d}",
            "email": "plate@test.com", "state": "New York",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": plate,
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_tlc_license": "2030-01-01",
            "expiry_fh1_insurance": "2030-01-01",
            "expiry_registration": "2030-01-01",
            "expiry_inspection": "2030-01-01",
            "expiry_vehicle_permit": "2030-01-01",
            "expiry_vehicle_registration": "2030-01-01",
            "expiry_insurance_card": "2030-01-01",
        }
        for field, _label, fname in NY_FIELDS:
            filedata = (photo_factory.VALID_PROFILE_PHOTO
                        if field == "profile_photo" else photo_factory.doc_photo())
            data[field] = (io.BytesIO(filedata), fname)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    # -- server rule ---------------------------------------------------------
    def test_validate_plate_accepts_plain_plate(self):
        plate, error = app_module.validate_plate("T12345")
        self.assertEqual(plate, "T12345")
        self.assertIsNone(error)

    def test_validate_plate_normalizes_lowercase_to_uppercase(self):
        plate, error = app_module.validate_plate("abc123")
        self.assertEqual(plate, "ABC123")
        self.assertIsNone(error)

    def test_validate_plate_strips_dashes_and_spaces(self):
        plate, _ = app_module.validate_plate("ABC-1234")
        self.assertEqual(plate, "ABC1234")
        plate, _ = app_module.validate_plate("ABC 1234")
        self.assertEqual(plate, "ABC1234")
        plate, _ = app_module.validate_plate("  a-b 1 ")
        self.assertEqual(plate, "AB1")

    def test_validate_plate_length_bounds(self):
        plate, error = app_module.validate_plate("AB")
        self.assertEqual(plate, "AB")
        self.assertIsNone(error)
        plate, error = app_module.validate_plate("ABCDEFGH")
        self.assertEqual(plate, "ABCDEFGH")
        self.assertIsNone(error)
        _plate, error = app_module.validate_plate("A")
        self.assertEqual(error, app_module.PLATE_ERROR)
        _plate, error = app_module.validate_plate("ABCDEFGHI")
        self.assertEqual(error, app_module.PLATE_ERROR)

    def test_validate_plate_rejects_special_characters(self):
        for bad in ("AB!123", "AB.C12", "AB_123", "AB#1", "AB/123"):
            _plate, error = app_module.validate_plate(bad)
            self.assertEqual(error, app_module.PLATE_ERROR, bad)

    def test_validate_plate_rejects_empty_and_blank(self):
        for bad in ("", "   ", None, "--  --"):
            _plate, error = app_module.validate_plate(bad)
            self.assertEqual(error, app_module.PLATE_ERROR, repr(bad))

    def test_validate_plate_rejects_non_ascii_letters(self):
        _plate, error = app_module.validate_plate("AB\xc912")
        self.assertEqual(error, app_module.PLATE_ERROR)

    # -- server gate ---------------------------------------------------------
    def test_registration_with_lowercase_dashed_plate_stores_normalized(self):
        resp = self.register("t12-345")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["plate"], "T12345")
        with app_module.app.app_context():
            stored = app_module.Driver.query.one()
            self.assertEqual(stored.plate, "T12345")

    def test_registration_with_invalid_plate_is_rejected_and_stores_nothing(self):
        resp = self.register("AB!1", phone="+15550229999")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], app_module.PLATE_ERROR)
        with app_module.app.app_context():
            self.assertEqual(app_module.Driver.query.count(), 0)
        # The phone was not consumed: the same driver can register
        # again with a valid plate.
        resp = self.register("AB1234", phone="+15550229999")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])

    def test_registration_with_short_plate_is_rejected(self):
        resp = self.register("Z")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], app_module.PLATE_ERROR)

    def test_registration_with_long_plate_is_rejected(self):
        resp = self.register("ABCDEFGHI")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], app_module.PLATE_ERROR)

    def test_duplicate_phone_still_reports_409_before_plate_check(self):
        # A duplicate phone keeps its 409 even when the plate in the
        # duplicate request would itself fail the format check.
        resp = self.register("T12345", phone="+15550228888")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        resp = self.register("Z", phone="+15550228888")
        self.assertEqual(resp.status_code, 409)

    # -- no retroactive blocking ---------------------------------------------
    def test_legacy_driver_with_unformatted_plate_still_works(self):
        # A driver registered before the check, with a stored plate
        # that would fail the new rule, must keep signing in, going
        # available, and seeing the plate exactly as stored.
        with app_module.app.app_context():
            driver = app_module.Driver(
                name="Legacy Plate", phone="+15550227777", email="legacy@test.com",
                car_model="Cadillac CT6", car_year=2023, vehicle_class="sedan",
                car_colour="Black", plate="OLD PLATE!",
                bank_encrypted=app_module.encrypt_bank("123456789", "021000021"),
                bank_last4="6789", token=secrets.token_hex(16))
            app_module.db.session.add(driver)
            app_module.db.session.commit()
            driver_id = driver.id
        resp = self.client.post("/api/drivers/me/lookup", json={"phone": "+15550227777"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        token = resp.get_json()["token"]
        resp = self.client.get("/api/drivers/me", headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["driver"]["plate"], "OLD PLATE!")
        resp = self.client.post("/api/drivers/me/availability", json={"available": True},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            driver = app_module.Driver.query.get(driver_id)
            self.assertTrue(driver.available)
            self.assertEqual(driver.plate, "OLD PLATE!")

    # -- client wiring --------------------------------------------------------
    def test_client_validates_plate_with_same_wording_as_server(self):
        driver_js = read("static/js/driver.js")
        self.assertIn(app_module.PLATE_ERROR, driver_js)
        self.assertIn("function normalizePlate", driver_js)
        self.assertIn("function plateError", driver_js)
        self.assertIn("/^[A-Z0-9]{2,8}$/", driver_js)
        self.assertIn("plate = normalizePlate(plate);", driver_js)

    def test_client_uppercases_plate_as_driver_types(self):
        driver_js = read("static/js/driver.js")
        self.assertIn('$("reg-plate").addEventListener("input"', driver_js)
        self.assertIn("field.value.toUpperCase()", driver_js)

    def test_plate_field_and_customer_display_unchanged(self):
        # The registration field itself is untouched, and the
        # customer-side plate display stays exactly as-is (the owner
        # picked the format check only, not the bigger display).
        driver_html = read("static/driver.html")
        self.assertIn('<label for="reg-plate">Plate number</label>', driver_html)
        self.assertIn('<input id="reg-plate" type="text" required>', driver_html)
        customer_js = read("static/js/customer.js")
        self.assertIn('$("driver-plate").textContent = b.driver.plate || "";',
                      customer_js)


if __name__ == "__main__":
    unittest.main()
