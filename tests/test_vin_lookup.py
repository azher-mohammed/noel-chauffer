"""Tests for the FREE VIN lookup (NHTSA vPIC, owner decision
2026-11-24, "Pehle sirf VIN free wala banao" — VIN only first, no
paid plate API).

POST /api/vin-lookup decodes a 17-character VIN with the free
NHTSA vPIC API (no key): year, make, model, body type and trim.
Colour is NEVER returned — a VIN does not encode it. The decoded
values fill in the driver registration form (year + model, only
when the model matches the eligible list); the VIN and decoded
body type are stored on the Driver and shown in Profile.

The vPIC call is always MOCKED in these tests — no live NHTSA call
is ever made from a test.

Run:  python -m unittest discover -s tests -v
"""

import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import URLError

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-vinlookup-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "vinlookup-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Public NHTSA docs example VIN (2022 Chevrolet Tahoe) — the same
# VIN used to verify the live vPIC response shape while building.
EXAMPLE_VIN = "1GNSKNKDXNR253093"

VPIC_TAHOE = {
    "Count": 1,
    "Message": "Results returned successfully.",
    "SearchCriteria": "VIN(s): 1GNSKNKDXNR253093",
    "Results": [{
        "ErrorCode": "0",
        "ErrorText": "0 - VIN decoded clean. Check Digit (9th position) is correct",
        "ModelYear": "2022",
        "Make": "CHEVROLET",
        "Model": "Tahoe",
        "BodyClass": "Sport Utility Vehicle [SUV]/Multipurpose Vehicle [MPV]",
        "Trim": "LT",
    }],
}


class _FakeVPICResponse:
    """Minimal urlopen stand-in: a context manager with .read()."""

    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _vpic_payload(**overrides):
    """VPIC_TAHOE with the first result's fields overridden."""
    import copy
    payload = copy.deepcopy(VPIC_TAHOE)
    payload["Results"][0].update(overrides)
    return payload


class VinLookupCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    # -- validate_vin -------------------------------------------------------
    def test_validate_vin_accepts_valid_and_normalizes(self):
        vin, error = app_module.validate_vin("1gnsknkdxnr253093")
        self.assertIsNone(error)
        self.assertEqual(vin, EXAMPLE_VIN)

    def test_validate_vin_rejects_short_long_and_forbidden_letters(self):
        for bad in ("ABC", "1GNSKNKDXNR2530930",  # too short / too long
                    "1GNSKNKDXNR25309I",  # I is never in a VIN
                    "1GNSKNKDXNR25309O",  # O is never in a VIN
                    "1GNSKNKDXNR25309Q",  # Q is never in a VIN
                    "1GNSKNKDXNR25309!"):  # not a letter or digit
            with self.subTest(bad=bad):
                vin, error = app_module.validate_vin(bad)
                self.assertIsNone(vin)
                self.assertTrue(error)

    # -- POST /api/vin-lookup (vPIC mocked) ---------------------------------
    def _lookup(self, vin, fake=None):
        if fake is None:
            fake = _FakeVPICResponse(VPIC_TAHOE)
        with mock.patch.object(app_module.urllib_request, "urlopen",
                               return_value=fake) as patched:
            resp = self.client.post("/api/vin-lookup", json={"vin": vin})
            return resp, patched

    def test_lookup_decodes_year_make_model_body_type_trim(self):
        resp, patched = self._lookup(EXAMPLE_VIN)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["vin"], EXAMPLE_VIN)
        self.assertEqual(data["year"], 2022)
        self.assertEqual(data["make"], "CHEVROLET")
        self.assertEqual(data["model"], "Tahoe")
        # BodyClass "Sport Utility Vehicle [SUV]/Multipurpose Vehicle
        # [MPV]" shortens to its first segment.
        self.assertEqual(data["body_type"], "Sport Utility Vehicle [SUV]")
        self.assertEqual(data["trim"], "LT")
        # Colour is never in a VIN decode.
        self.assertNotIn("colour", data)
        self.assertNotIn("color", data)

    def test_lookup_sends_custom_user_agent(self):
        calls = []

        def _capture(req, timeout=None):
            calls.append(req)
            return _FakeVPICResponse(VPIC_TAHOE)

        with mock.patch.object(app_module.urllib_request, "urlopen",
                               side_effect=_capture):
            resp = self.client.post("/api/vin-lookup",
                                    json={"vin": EXAMPLE_VIN})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].get_header("User-agent"), "NoelChauffer/1.0")

    def test_lookup_rejects_bad_vin_without_calling_vpic(self):
        for bad in ("SHORT", "", "1GNSKNKDXNR25309I"):
            with self.subTest(bad=bad):
                with mock.patch.object(app_module.urllib_request, "urlopen") as patched:
                    resp = self.client.post("/api/vin-lookup", json={"vin": bad})
                self.assertEqual(resp.status_code, 400)
                patched.assert_not_called()
        resp = self.client.post("/api/vin-lookup", json={})
        self.assertEqual(resp.status_code, 400)

    def test_lookup_nhtsa_error_code_is_a_clear_error(self):
        resp, _ = self._lookup(
            EXAMPLE_VIN,
            fake=_FakeVPICResponse(_vpic_payload(ErrorCode="1", ErrorText="1 - VIN decoded clean. Check Digit (9th position) is incorrect")))
        self.assertEqual(resp.status_code, 422)
        self.assertIn("could not be decoded", resp.get_json()["error"])

    def test_lookup_missing_fields_is_a_clear_error(self):
        resp, _ = self._lookup(
            EXAMPLE_VIN,
            fake=_FakeVPICResponse(_vpic_payload(ModelYear="", Make="", Model="")))
        self.assertEqual(resp.status_code, 422)
        self.assertIn("could not be decoded", resp.get_json()["error"])

    def test_lookup_upstream_failure_is_a_clear_error(self):
        with mock.patch.object(app_module.urllib_request, "urlopen",
                               side_effect=URLError("no route")):
            resp = self.client.post("/api/vin-lookup", json={"vin": EXAMPLE_VIN})
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Could not look up", resp.get_json()["error"])
        # A payload that is not JSON at all is the same 502, never a crash.
        bad = _FakeVPICResponse.__new__(_FakeVPICResponse)
        bad.read = lambda: b"not json"
        bad.__enter__ = lambda s: s
        bad.__exit__ = lambda *a: False
        with mock.patch.object(app_module.urllib_request, "urlopen",
                               return_value=bad):
            resp = self.client.post("/api/vin-lookup", json={"vin": EXAMPLE_VIN})
        self.assertEqual(resp.status_code, 502)

    # -- registration stores vin + body type --------------------------------
    def _register(self, extra=None, state="Alaska"):
        """Register with the state's own document list (Alaska is on
        the generic list: profile picture, licence, registration,
        insurance card). Returns the response."""
        self._seq += 1
        data = {
            "name": "VIN Driver", "phone": f"+1555022{self._seq:04d}",
            "email": f"vindriver{self._seq}@test.com", "state": state,
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"VN{self._seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_vehicle_registration": "2030-01-01",
            "expiry_insurance_card": "2030-01-01",
        }
        if extra:
            data.update(extra)
        for doc_type in app_module.required_docs_for_state(state):
            field = app_module.FIELD_FOR_DOC_TYPE[doc_type]
            filedata = (photo_factory.VALID_PROFILE_PHOTO
                        if field == "profile_photo" else photo_factory.doc_photo())
            data[field] = (io.BytesIO(filedata), field + ".png")
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    def test_registration_saves_vin_and_body_type_and_profile_shows_them(self):
        resp = self._register(extra={"vin": EXAMPLE_VIN,
                                     "vehicle_body_type": "Sport Utility Vehicle [SUV]"})
        self.assertEqual(resp.status_code, 201, resp.get_json())
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["vin"], EXAMPLE_VIN)
        self.assertEqual(driver["vehicle_body_type"], "Sport Utility Vehicle [SUV]")
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": resp.get_json()["token"]})
        self.assertEqual(me.status_code, 200)
        profile = me.get_json()["driver"]
        self.assertEqual(profile["vin"], EXAMPLE_VIN)
        self.assertEqual(profile["vehicle_body_type"], "Sport Utility Vehicle [SUV]")

    def test_registration_without_vin_stores_nothing(self):
        resp = self._register()
        self.assertEqual(resp.status_code, 201, resp.get_json())
        driver = resp.get_json()["driver"]
        self.assertIsNone(driver["vin"])
        self.assertIsNone(driver["vehicle_body_type"])

    def test_registration_rejects_bad_vin(self):
        resp = self._register(extra={"vin": "SHORT"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("VIN", resp.get_json()["error"])

    def test_registration_body_type_without_vin_is_dropped(self):
        resp = self._register(extra={"vehicle_body_type": "Sedan"})
        self.assertEqual(resp.status_code, 201, resp.get_json())
        self.assertIsNone(resp.get_json()["driver"]["vehicle_body_type"])

    def test_registration_vin_never_bypasses_the_model_allowlist(self):
        # A VIN for a Tahoe does not make an ineligible model
        # registerable: the allowlist still decides.
        resp = self._register(extra={"vin": EXAMPLE_VIN,
                                     "car_model": "Honda Civic"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not eligible", resp.get_json()["error"])

    # -- the driver app wires the lookup in ---------------------------------
    def test_driver_app_has_vin_field_lookup_button_and_wiring(self):
        with open(os.path.join(REPO_DIR, "static", "driver.html")) as f:
            html = f.read()
        self.assertIn('id="reg-vin"', html)
        self.assertIn('id="vin-lookup-btn"', html)
        self.assertIn('id="vin-note"', html)
        with open(os.path.join(REPO_DIR, "static", "js", "driver.js")) as f:
            js = f.read()
        self.assertIn("/api/vin-lookup", js)
        self.assertIn("initVinLookup", js)
        self.assertIn('fd.append("vin", vin)', js)
        self.assertIn("vehicle_body_type", js)
        # Profile shows the stored VIN and body type.
        self.assertIn('esc(d.vin)', js)
        self.assertIn('esc(d.vehicle_body_type)', js)
        with open(os.path.join(REPO_DIR, "static", "css", "driver.css")) as f:
            css = f.read()
        self.assertIn(".vin-row", css)


if __name__ == "__main__":
    unittest.main()
