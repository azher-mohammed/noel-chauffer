"""Tests for the driver car-model dropdown (decided 2026-11-16).

- The dropdown list is the transcribed Uber Black list (132 models,
  23 makes) from UBER_BLACK_LIST.md, plus the TEMPORARY "Tesla Model 3"
  owner-trial exception. Model Y and the other NOT-eligible models
  stay out.
- Model year floor: 2022 or newer ("2022 se rakhna"), up to the
  current year + 1. The server rejects unlisted models and old years.
- Registration with a listed model + valid year works end to end, and
  the year is stored on the driver record.
- Driver rows created before the year field existed (car_year NULL)
  still load fine.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import re
import sys
import tempfile
import unittest
from datetime import date

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-carmodels-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "carmodels.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "carmodels-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
import car_models as car_models_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Full display names that must NEVER be offered.
EXCLUDED = ["Tesla Model Y", "Cadillac CT5", "Cadillac CT4",
            "Genesis G80", "Genesis G70", "Lexus ES",
            "BMW 3 Series", "Jaguar XF"]


def models_from_source_file():
    """Parse UBER_BLACK_LIST.md the way it is written: '- Make: a, b'."""
    expected, makes = set(), set()
    path = os.path.join(REPO_DIR, "UBER_BLACK_LIST.md")
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("## NOT eligible"):
                break
            m = re.match(r"^- ([A-Za-z][A-Za-z -]*?): (.+)$", line.strip())
            if not m:
                continue
            make, rest = m.group(1), m.group(2)
            makes.add(make)
            for raw in rest.split(", "):
                name = (raw.replace(" (SUV)", "")
                        .replace(" (SF Bay Area only)", "").strip())
                expected.add("%s %s" % (make, name))
    return expected, makes


class CarModelsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    # -- helpers ---------------------------------------------------------
    def register(self, car_model="Cadillac Escalade", car_year="2023", **overrides):
        self._seq += 1
        data = {
            "name": "Car Model Driver", "phone": f"+1555003{self._seq:04d}",
            "email": "cm@test.com",
            "car_model": car_model, "car_year": car_year,
            "car_colour": "Black", "plate": f"C{self._seq:05d}",
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
        data.update(overrides)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    # -- list completeness -------------------------------------------------
    def test_module_matches_source_file_exactly(self):
        expected, makes = models_from_source_file()
        self.assertEqual(len(expected), 132, "source file must list 132 models")
        self.assertEqual(len(makes), 23, "source file must list 23 makes")
        got = set(car_models_module.uber_black_models())
        self.assertEqual(got, expected)

    def test_endpoint_serves_132_plus_temporary_model_3(self):
        resp = self.client.get("/api/car-models")
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        models = payload["models"]
        self.assertEqual(len(models), 133)
        self.assertEqual(len(set(models)), 133, "no duplicate models")
        self.assertEqual(models, sorted(models), "sorted for the dropdown")
        self.assertIn("Tesla Model 3", models)
        expected, _ = models_from_source_file()
        self.assertTrue(expected <= set(models))

    def test_excluded_models_absent(self):
        models = set(self.client.get("/api/car-models").get_json()["models"])
        for name in EXCLUDED:
            self.assertNotIn(name, models, name)

    def test_year_bounds(self):
        payload = self.client.get("/api/car-models").get_json()
        self.assertEqual(payload["min_year"], 2022)
        self.assertEqual(payload["max_year"], date.today().year + 1)

    # -- server validation ---------------------------------------------------
    def test_year_floor_2021_rejected_2022_accepted(self):
        resp = self.register(car_year="2021")
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertIn("2022", resp.get_json()["error"])
        resp = self.register(car_year="2022")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])

    def test_year_too_new_rejected(self):
        resp = self.register(car_year=str(date.today().year + 2))
        self.assertEqual(resp.status_code, 400)

    def test_year_missing_or_not_a_number_rejected(self):
        self._seq += 1
        data = {
            "name": "No Year", "phone": f"+1555003{self._seq:04d}",
            "email": "ny@test.com", "car_model": "Cadillac Escalade",
            "car_colour": "Black", "plate": "NY0001",
            "state": "New York", "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_tlc_license": "2030-01-01",
            "expiry_fh1_insurance": "2030-01-01",
            "expiry_registration": "2030-01-01",
            "expiry_inspection": "2030-01-01",
            "expiry_vehicle_permit": "2030-01-01",
            "expiry_vehicle_registration": "2030-01-01",
            "expiry_insurance_card": "2030-01-01",
        }
        resp = self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 400)
        resp = self.register(car_year="twenty-three")
        self.assertEqual(resp.status_code, 400)

    def test_unlisted_model_rejected(self):
        for bad in ("Tesla Model Y", "Toyota Camry", "Cadillac CT5", "X"):
            resp = self.register(car_model=bad)
            self.assertEqual(resp.status_code, 400, bad)
        resp = self.register(car_model="  ")
        self.assertEqual(resp.status_code, 400)

    def test_model_3_temporary_exception_accepted(self):
        resp = self.register(car_model="Tesla Model 3", car_year="2023")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])

    def test_model_whitespace_trimmed(self):
        resp = self.register(car_model="  Cadillac Escalade  ")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["driver"]["car_model"], "Cadillac Escalade")

    # -- happy path + storage --------------------------------------------------
    def test_registration_stores_model_and_year(self):
        resp = self.register(car_model="Lincoln Navigator", car_year="2024")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["car_model"], "Lincoln Navigator")
        self.assertEqual(driver["car_year"], 2024)
        token = resp.get_json()["token"]
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": token}).get_json()["driver"]
        self.assertEqual(me["car_model"], "Lincoln Navigator")
        self.assertEqual(me["car_year"], 2024)
        # Owner list carries the year; the "car" label format is unchanged.
        self.client.post("/api/owner/login", json={"pin": "9999"})
        rows = self.client.get("/api/owner/drivers").get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["car"], "Lincoln Navigator (Black)")
        self.assertEqual(rows[0]["car_year"], 2024)

    def test_driver_row_without_year_still_loads(self):
        # Rows created before the car_year column existed have NULL.
        with app_module.app.app_context():
            driver = app_module.Driver(
                name="Legacy Driver", phone="+15550009990",
                email="legacy@test.com", car_model="Cadillac Escalade",
                car_year=None, car_colour="Black", plate="LEG001",
                token="legacy-token-123")
            app_module.db.session.add(driver)
            app_module.db.session.commit()
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": "legacy-token-123"})
        self.assertEqual(me.status_code, 200)
        self.assertIsNone(me.get_json()["driver"]["car_year"])
        self.client.post("/api/owner/login", json={"pin": "9999"})
        rows = self.client.get("/api/owner/drivers").get_json()
        self.assertEqual(rows[0]["car"], "Cadillac Escalade (Black)")
        self.assertIsNone(rows[0]["car_year"])

    # -- frontend wiring ---------------------------------------------------------
    def test_driver_form_has_dropdown_and_year_select(self):
        with open(os.path.join(REPO_DIR, "static", "driver.html"),
                  encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn('id="car-model-list"', html)
        self.assertIn('id="reg-car-year"', html)
        self.assertIn("2022 or newer", html)
        # No more free-text placeholder for the model.
        self.assertNotIn("e.g. Cadillac Escalade", html)
        with open(os.path.join(REPO_DIR, "static", "js", "driver.js"),
                  encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn("/api/car-models", js)
        self.assertIn('fd.append("car_year"', js)


if __name__ == "__main__":
    unittest.main()
