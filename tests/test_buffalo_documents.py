"""Tests for the Buffalo, NY city-specific document override.

Owner decision 2026-11-17 night ("Buffalo ku tlc nahi chaiye"):
TLC is New York City only, so a Buffalo driver must NOT see TLC
documents. Buffalo is the SECOND city-specific list (after Dallas),
from the City of Buffalo's OFFICIAL taxi/livery requirements
(Office of Licenses, buffalony.gov): licensed as a City of
Buffalo Taxi Driver, copy of NYS vehicle registration, certificate
of automobile liability insurance, vehicle inspection report.

Left out of the gate, with the owner-review note KEPT ON for
Buffalo: the worker's compensation / exemption certificate (an
OR-alternative — Form CE-200 when exclusively owner-operated, a
certificate otherwise — which the gate cannot express), the MV 289
taxi-plate certification (a process, not a document), and the
license fees (not a document). No background check of any kind
(owner declined it outright), no proof-of-residency slot (the city
source does not name it), no document count anywhere ("Quantity
nahi").

The New York STATE list stays the NYC 7-doc list byte-unchanged.
Rochester, Syracuse, and Yonkers have since gained their own
city-specific lists (tests/test_upstate_ny_documents.py); Albany
and New York city itself still fall back to the state list —
Albany because the city repealed its taxicab licensing article
in 2024, New York because the state list IS the NYC list.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-buffalo-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "buffalo-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BUFFALO_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_buffalo_taxi_driver_license", "City of Buffalo Taxi Driver License", "buffalo.png"),
    ("doc_vehicle_registration", "Vehicle Registration", "reg.png"),
    ("doc_buffalo_insurance_certificate", "Certificate of Automobile Liability Insurance", "ins.png"),
    ("doc_buffalo_inspection_report", "Vehicle Inspection Report", "insp.png"),
]
NY_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_tlc_license", "TLC License", "tlc.png"),
    ("doc_fh1", "FH-1 Insurance Card", "fh1.png"),
    ("doc_registration", "Commercial Vehicle Registration", "reg.png"),
    ("doc_inspection", "NYS DMV Inspection", "insp.png"),
    ("doc_vehicle_permit", "TLC-for-hire Vehicle Permit", "permit.png"),
]
# NYC-only items: none of these may appear in the Buffalo list.
NYC_ONLY_TYPES = ("tlc_license", "fh1_insurance", "registration",
                  "inspection", "vehicle_permit")


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class BuffaloDocumentsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, fields, city=None, omit=(), extra=None):
        self._seq += 1
        data = {
            "name": "Buffalo Driver", "phone": f"+1555022{self._seq:04d}",
            "email": "buffalo@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"BF{self._seq:05d}",
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
        if state is not None:
            data["state"] = state
        if city is not None:
            data["city"] = city
        if extra:
            data.update(extra)
        for field, _label, fname in fields:
            if field in omit:
                continue
            filedata = (photo_factory.VALID_PROFILE_PHOTO
                        if field == "profile_photo" else photo_factory.doc_photo())
            data[field] = (io.BytesIO(filedata), fname)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    # -- endpoint -------------------------------------------------------------
    def test_new_york_cities_include_buffalo(self):
        payload = self.client.get("/api/states").get_json()
        self.assertEqual(payload["cities"]["New York"],
                         ["Albany", "Buffalo", "New York", "Rochester",
                          "Syracuse", "Yonkers", "Other city"])

    def test_city_requirements_cover_dallas_and_buffalo(self):
        payload = self.client.get("/api/states").get_json()
        overrides = payload["city_requirements"]
        self.assertEqual(set(overrides),
                         {"Texas", "New York", "Alabama", "Florida",
                          "Louisiana", "Mississippi", "North Carolina",
                          "South Carolina", "Tennessee", "Illinois",
                          "Indiana", "Minnesota", "Missouri", "Nebraska",
                          "Ohio", "Wisconsin", "Maine", "Massachusetts",
                          "New Jersey", "Pennsylvania", "Arkansas", "Idaho",
                          "Nevada", "Oklahoma", "Utah", "Wyoming",
                          "Oregon"})
        self.assertEqual(set(overrides["Texas"]),
                         {"Dallas", "Austin", "Houston", "San Antonio"})
        self.assertEqual(set(overrides["New York"]),
                         {"Buffalo", "Rochester", "Syracuse", "Yonkers"})
        buffalo = overrides["New York"]["Buffalo"]
        self.assertEqual(buffalo["docs"], app_module.BUFFALO_DOC_TYPES)
        self.assertEqual(buffalo["docs"], [
            "profile_picture", "dmv_license",
            "buffalo_taxi_driver_license", "vehicle_registration",
            "buffalo_insurance_certificate", "buffalo_inspection_report"])
        # The owner-review note STAYS ON for Buffalo: the city source
        # names the worker's compensation / exemption certificate,
        # which the gate cannot express (OR-alternative).
        self.assertTrue(buffalo["local_note"])
        # Dallas unchanged, note still off.
        dallas = overrides["Texas"]["Dallas"]
        self.assertEqual(dallas["docs"], app_module.DALLAS_DOC_TYPES)
        self.assertFalse(dallas["local_note"])

    def test_buffalo_list_has_zero_tlc_items(self):
        docs = app_module.BUFFALO_DOC_TYPES
        for nyc_type in NYC_ONLY_TYPES:
            self.assertNotIn(nyc_type, docs)
        labels = " ".join(app_module.ALL_DOC_LABELS[t] for t in docs)
        self.assertNotIn("TLC", labels)
        hints = " ".join(app_module.DOC_HINTS[t] for t in docs)
        self.assertNotIn("TLC", hints)

    def test_buffalo_docs_carry_labels_hints_fields(self):
        payload = self.client.get("/api/states").get_json()
        docs = payload["documents"]
        self.assertEqual(docs["buffalo_taxi_driver_license"]["label"],
                         "City of Buffalo Taxi Driver License")
        self.assertEqual(docs["buffalo_insurance_certificate"]["label"],
                         "Certificate of Automobile Liability Insurance")
        self.assertEqual(docs["buffalo_inspection_report"]["label"],
                         "Vehicle Inspection Report")
        for doc_type in ("buffalo_taxi_driver_license",
                         "buffalo_insurance_certificate",
                         "buffalo_inspection_report"):
            self.assertTrue(docs[doc_type]["hint"], doc_type)
            self.assertEqual(docs[doc_type]["field"],
                             app_module.FIELD_FOR_DOC_TYPE[doc_type])
            self.assertEqual(docs[doc_type]["accept"], "image/*",
                             "only FH-1 accepts PDF")

    def test_no_background_check_or_proof_of_residency_slot(self):
        # The owner declined the background check; the city source
        # does not name proof of residency, so neither is a slot.
        self.assertNotIn("background_check", app_module.BUFFALO_DOC_TYPES)
        self.assertNotIn("dc_residency", app_module.BUFFALO_DOC_TYPES)
        labels = " ".join(app_module.ALL_DOC_LABELS[t]
                          for t in app_module.BUFFALO_DOC_TYPES)
        self.assertNotIn("Background", labels)
        self.assertNotIn("Residency", labels)

    def test_state_lists_unchanged_by_buffalo_override(self):
        # NY keeps the NYC 7-doc list byte-unchanged; NJ unchanged;
        # every state's list is exactly its own.
        payload = self.client.get("/api/states").get_json()
        reqs = payload["requirements"]
        self.assertEqual(reqs["New York"]["docs"], app_module.DOC_TYPES)
        self.assertFalse(reqs["New York"]["local_note"])
        self.assertEqual(reqs["New Jersey"]["docs"], app_module.NJ_DOC_TYPES)
        self.assertFalse(reqs["New Jersey"]["local_note"])
        for state in app_module.US_STATES:
            self.assertEqual(reqs[state]["docs"],
                             app_module.required_docs_for_state(state))

    def test_no_count_or_quantity_in_city_payload(self):
        payload = self.client.get("/api/states").get_json()
        for req in payload["city_requirements"].values():
            for city_req in req.values():
                self.assertNotIn("count", city_req)
                self.assertNotIn("quantity", city_req)

    # -- effective list rule --------------------------------------------------
    def test_required_docs_for_effective_list(self):
        self.assertEqual(
            app_module.required_docs_for("New York", "Buffalo"),
            app_module.BUFFALO_DOC_TYPES)
        # New York city itself, Albany, and "Other city" keep the
        # NYC state list. (Rochester, Syracuse, and Yonkers have
        # their own lists now — pinned in
        # tests/test_upstate_ny_documents.py.)
        for city in ("New York", "Albany", "Other city", None):
            with self.subTest(city=city):
                self.assertEqual(
                    app_module.required_docs_for("New York", city),
                    app_module.DOC_TYPES)
        self.assertTrue(app_module.local_note_for("New York", "Buffalo"))
        self.assertFalse(app_module.local_note_for("New York", "New York"))
        self.assertFalse(app_module.local_note_for("New York", "Albany"))
        self.assertFalse(app_module.local_note_for("New York", None))

    # -- registration gate ----------------------------------------------------
    def test_buffalo_registration_with_all_docs_succeeds_and_stores_city(self):
        resp = self.register("New York", BUFFALO_FIELDS, city="Buffalo")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["state"], "New York")
        self.assertEqual(driver["city"], "Buffalo")
        self.assertEqual(set(driver["docs"]), set(app_module.BUFFALO_DOC_TYPES))

    def test_buffalo_registration_missing_taxi_license_rejected_by_name(self):
        resp = self.register("New York", BUFFALO_FIELDS, city="Buffalo",
                             omit=("doc_buffalo_taxi_driver_license",))
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Missing document: City of Buffalo Taxi Driver License",
                      error)
        self.assertNotIn("TLC", error)

    def test_buffalo_registration_with_nyc_docs_is_rejected(self):
        # The 7 NYC documents do not satisfy Buffalo: the gate asks
        # for the Buffalo items by name, never for TLC items.
        resp = self.register("New York", NY_FIELDS, city="Buffalo")
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("City of Buffalo Taxi Driver License", error)
        self.assertIn("Vehicle Registration", error)
        self.assertIn("Certificate of Automobile Liability Insurance", error)
        self.assertIn("Vehicle Inspection Report", error)
        self.assertNotIn("TLC", error)

    def test_albany_falls_back_to_ny_state_list(self):
        # Albany repealed its taxicab licensing article in 2024, so
        # it adds no city-specific document and keeps the state list.
        resp = self.register("New York", NY_FIELDS, city="Albany")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["city"], "Albany")
        self.assertEqual(set(driver["docs"]), set(app_module.DOC_TYPES))

    def test_new_york_city_keeps_nyc_list(self):
        resp = self.register("New York", BUFFALO_FIELDS, city="New York")
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("TLC License", error)
        self.assertIn("TLC-for-hire Vehicle Permit", error)

    # -- client wiring ----------------------------------------------------------
    def test_client_maps_carry_buffalo_labels_and_fields(self):
        js = read("static/js/driver.js")
        for label in ("City of Buffalo Taxi Driver License",
                      "Certificate of Automobile Liability Insurance",
                      "Vehicle Inspection Report"):
            self.assertIn('"%s"' % label, js)
        for field in ("doc_buffalo_taxi_driver_license",
                      "doc_buffalo_insurance_certificate",
                      "doc_buffalo_inspection_report"):
            self.assertIn('"%s"' % field, js)
        for doc_type in ("buffalo_taxi_driver_license",
                         "buffalo_insurance_certificate",
                         "buffalo_inspection_report"):
            self.assertIn('"%s"' % doc_type, js)
        owner_js = read("static/js/owner.js")
        for label in ("City of Buffalo Taxi Driver License",
                      "Certificate of Automobile Liability Insurance"):
            self.assertIn('"%s"' % label, owner_js)
        for doc_type in ("buffalo_taxi_driver_license",
                         "buffalo_insurance_certificate",
                         "buffalo_inspection_report"):
            self.assertIn('key: "%s"' % doc_type, owner_js)

    def test_no_background_check_strings_in_client(self):
        js = read("static/js/driver.js")
        self.assertNotIn("background check", js.lower())
        self.assertNotIn("background_check", js.lower())


if __name__ == "__main__":
    unittest.main()
