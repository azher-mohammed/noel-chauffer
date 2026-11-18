"""Tests for the Rochester, Syracuse, and Yonkers, NY city-specific
document overrides.

Owner decision 2026-11-17 night ("Haan bhai every city ka wahan ke
rules"): every city in the picker gets its own local rules,
verified from official sources only. These are the THIRD, FOURTH,
and FIFTH city-specific lists (after Dallas and Buffalo). Zero NYC
TLC items on any of them: TLC is New York City only.

Rochester — Municipal Code Chapter 108, Articles II-IV, plus the
City Clerk permits page: City of Rochester Taxicab Driver's
License, Taxicab License Certificate (hack plate certificate),
Proof of Insurance. No FH-1/ACORD form name is named (none
imported); inspections are evidenced by stickers, so no
inspection-report slot. Owner-review note ON: the two-hour
training session (no certificate named), the DMV abstract, and
the employment-eligibility OR-alternative are ungated, and the
regime is a taxicab regime under General Municipal Law §181 with
no separate livery license found (Buffalo precedent; the
legal-scope question is open, not settled).

Syracuse — Business Licensing Guide 2025 (Central Permit
Office): Taxi (Hack) License, Ground Transportation License,
Proof of For-Hire Insurance (the guide's exact wording — NOT
FH-1). Owner-review note ON: the Medical Certification Form is
held for an owner decision (same as the other medical items),
and fingerprint receipt / title / photographs are ungated
inputs. No inspection document is named in the guide — none
invented. Airport-authority requirements are airport-only and
are not imported.

Yonkers — Westchester County Taxi and Limousine Commission
For-Hire Rules v4.2 (June 17, 2022), expressly covering livery /
black car / limousine: WCTLC For-Hire Driver Permit, WCTLC
For-Hire Vehicle Permit, Proof of Adequate Insurance (NOT
FH-1/ACORD), Defensive Driving Course Proof of Completion (a
named certificate). WCTLC is a DIFFERENT commission from NYC
TLC — never label its items NYC TLC. Owner-review note ON
(required): the Social Security card OR SSA correspondence is
held (OR-alternative + privacy flag — owner decision required),
the City of Yonkers city-license / Class B overlap is unresolved
(the city license is NOT gated silently), and base-station
affiliation is a structural gap.

Albany keeps the state-list fallback: the city REPEALED its
taxicab licensing article in 2024 (Ordinance 2.21.24). New York
city itself keeps the 7-doc state list, re-verified item by item
from official NYC TLC sources. Long Island runs on the NY state
TLC list by explicit owner decision — no county overrides, no
code change; the "Other city" fallback already does this.

No background check anywhere (owner declined it outright), no
age/experience gate, no document count anywhere ("Quantity
nahi").

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-upstate-ny-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "upstate-ny-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROCHESTER_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_vehicle_registration", "Vehicle Registration", "reg.png"),
    ("doc_rochester_taxi_driver_license", "City of Rochester Taxicab Driver License", "roch.png"),
    ("doc_rochester_hack_certificate", "Taxicab License Certificate (Hack Plate Certificate)", "hack.png"),
    ("doc_rochester_insurance", "Proof of Insurance", "ins.png"),
]
SYRACUSE_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_vehicle_registration", "Vehicle Registration", "reg.png"),
    ("doc_syracuse_hack_license", "Taxi (Hack) License", "syr.png"),
    ("doc_syracuse_ground_transportation", "Ground Transportation License", "gt.png"),
    ("doc_syracuse_for_hire_insurance", "Proof of For-Hire Insurance", "ins.png"),
]
YONKERS_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_vehicle_registration", "Vehicle Registration", "reg.png"),
    ("doc_wctlc_driver_permit", "WCTLC For-Hire Driver Permit", "wcd.png"),
    ("doc_wctlc_vehicle_permit", "WCTLC For-Hire Vehicle Permit", "wcv.png"),
    ("doc_wctlc_insurance", "Proof of Adequate Insurance", "ins.png"),
    ("doc_wctlc_defensive_driving", "Defensive Driving Course Proof of Completion", "dd.png"),
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
# NYC-only doc types: none of these may appear in any upstate list.
NYC_ONLY_TYPES = ("tlc_license", "fh1_insurance", "registration",
                  "inspection", "vehicle_permit")
# NYC-only labels: none of these wordings may appear in any upstate
# list. (Yonkers labels contain "WCTLC", which includes the letters
# TLC — so the check is on the exact NYC wordings, not the
# substring.)
NYC_ONLY_LABELS = ("TLC License", "TLC-for-hire Vehicle Permit",
                   "FH-1 Insurance Card", "NYS DMV Inspection",
                   "Commercial Vehicle Registration")

NEW_TYPES = (
    "rochester_taxi_driver_license", "rochester_hack_certificate",
    "rochester_insurance", "syracuse_hack_license",
    "syracuse_ground_transportation", "syracuse_for_hire_insurance",
    "wctlc_driver_permit", "wctlc_vehicle_permit", "wctlc_insurance",
    "wctlc_defensive_driving",
)


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class UpstateNYDocumentsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, fields, city=None, omit=(), extra=None):
        self._seq += 1
        data = {
            "name": "Upstate Driver", "phone": f"+1555023{self._seq:04d}",
            "email": "upstate@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"UP{self._seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
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
                        if field == "profile_photo" else b"fake doc")
            data[field] = (io.BytesIO(filedata), fname)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    # -- endpoint -------------------------------------------------------------
    def test_city_requirements_cover_five_overrides(self):
        payload = self.client.get("/api/states").get_json()
        overrides = payload["city_requirements"]
        self.assertEqual(set(overrides),
                         {"Texas", "New York", "Alabama", "Florida",
                          "Louisiana", "Mississippi", "North Carolina",
                          "South Carolina", "Tennessee", "Illinois",
                          "Indiana", "Minnesota", "Missouri", "Nebraska",
                          "Ohio", "Wisconsin", "Maine", "Massachusetts",
                          "New Jersey", "Pennsylvania", "Arkansas", "Idaho",
                          "Nevada", "Oklahoma", "Utah", "Wyoming"})
        self.assertEqual(set(overrides["Texas"]),
                         {"Dallas", "Austin", "Houston", "San Antonio"})
        self.assertEqual(set(overrides["New York"]),
                         {"Buffalo", "Rochester", "Syracuse", "Yonkers"})
        rochester = overrides["New York"]["Rochester"]
        self.assertEqual(rochester["docs"], app_module.ROCHESTER_DOC_TYPES)
        self.assertEqual(rochester["docs"], [
            "profile_picture", "dmv_license", "vehicle_registration",
            "rochester_taxi_driver_license", "rochester_hack_certificate",
            "rochester_insurance"])
        self.assertTrue(rochester["local_note"])
        syracuse = overrides["New York"]["Syracuse"]
        self.assertEqual(syracuse["docs"], app_module.SYRACUSE_DOC_TYPES)
        self.assertEqual(syracuse["docs"], [
            "profile_picture", "dmv_license", "vehicle_registration",
            "syracuse_hack_license", "syracuse_ground_transportation",
            "syracuse_for_hire_insurance"])
        self.assertTrue(syracuse["local_note"])
        yonkers = overrides["New York"]["Yonkers"]
        self.assertEqual(yonkers["docs"], app_module.YONKERS_DOC_TYPES)
        self.assertEqual(yonkers["docs"], [
            "profile_picture", "dmv_license", "vehicle_registration",
            "wctlc_driver_permit", "wctlc_vehicle_permit",
            "wctlc_insurance", "wctlc_defensive_driving"])
        self.assertTrue(yonkers["local_note"])
        # Dallas and Buffalo unchanged.
        self.assertEqual(overrides["Texas"]["Dallas"]["docs"],
                         app_module.DALLAS_DOC_TYPES)
        self.assertFalse(overrides["Texas"]["Dallas"]["local_note"])
        self.assertEqual(overrides["New York"]["Buffalo"]["docs"],
                         app_module.BUFFALO_DOC_TYPES)
        self.assertTrue(overrides["New York"]["Buffalo"]["local_note"])

    def test_upstate_lists_have_zero_nyc_tlc_items(self):
        for doc_types in (app_module.ROCHESTER_DOC_TYPES,
                          app_module.SYRACUSE_DOC_TYPES,
                          app_module.YONKERS_DOC_TYPES):
            for nyc_type in NYC_ONLY_TYPES:
                self.assertNotIn(nyc_type, doc_types)
            labels = " | ".join(app_module.ALL_DOC_LABELS[t]
                                for t in doc_types)
            for nyc_label in NYC_ONLY_LABELS:
                self.assertNotIn(nyc_label, labels)
            hints = " ".join(app_module.DOC_HINTS[t] for t in doc_types)
            for nyc_label in NYC_ONLY_LABELS:
                self.assertNotIn(nyc_label, hints)
        # Rochester and Syracuse labels contain no TLC at all.
        for doc_types in (app_module.ROCHESTER_DOC_TYPES,
                          app_module.SYRACUSE_DOC_TYPES):
            labels = " ".join(app_module.ALL_DOC_LABELS[t]
                              for t in doc_types)
            self.assertNotIn("TLC", labels)
        # Yonkers labels name WCTLC — a different commission — and
        # never bare NYC TLC.
        yonkers_labels = " ".join(app_module.ALL_DOC_LABELS[t]
                                  for t in app_module.YONKERS_DOC_TYPES)
        self.assertIn("WCTLC", yonkers_labels)

    def test_no_fh1_no_inspection_report_no_ssn_no_medical_slots(self):
        # FH-1 is named by none of the three sources.
        for doc_types in (app_module.ROCHESTER_DOC_TYPES,
                          app_module.SYRACUSE_DOC_TYPES,
                          app_module.YONKERS_DOC_TYPES):
            self.assertNotIn("fh1_insurance", doc_types)
            labels = " ".join(app_module.ALL_DOC_LABELS[t]
                              for t in doc_types)
            self.assertNotIn("FH-1", labels)
        # No inspection-report slot: Rochester inspections are
        # stickers, Syracuse names no inspection document, Yonkers
        # inspections are stickers.
        for doc_types in (app_module.ROCHESTER_DOC_TYPES,
                          app_module.SYRACUSE_DOC_TYPES,
                          app_module.YONKERS_DOC_TYPES):
            for doc_type in doc_types:
                self.assertNotIn("inspection", doc_type)
        # Yonkers SSN OR-alternative is held for an owner decision;
        # Syracuse medical form is held likewise. Neither is a slot.
        self.assertNotIn("dc_ssc", app_module.YONKERS_DOC_TYPES)
        self.assertNotIn("dc_medical_form", app_module.SYRACUSE_DOC_TYPES)
        self.assertNotIn("wa_medical_certificate",
                         app_module.SYRACUSE_DOC_TYPES)
        # No background check of any kind.
        for doc_types in (app_module.ROCHESTER_DOC_TYPES,
                          app_module.SYRACUSE_DOC_TYPES,
                          app_module.YONKERS_DOC_TYPES):
            self.assertNotIn("background_check", doc_types)
            labels = " ".join(app_module.ALL_DOC_LABELS[t]
                              for t in doc_types)
            self.assertNotIn("Background", labels)

    def test_new_docs_carry_labels_hints_fields(self):
        payload = self.client.get("/api/states").get_json()
        docs = payload["documents"]
        expected = {
            "rochester_taxi_driver_license":
                "City of Rochester Taxicab Driver License",
            "rochester_hack_certificate":
                "Taxicab License Certificate (Hack Plate Certificate)",
            "rochester_insurance": "Proof of Insurance",
            "syracuse_hack_license": "Taxi (Hack) License",
            "syracuse_ground_transportation": "Ground Transportation License",
            "syracuse_for_hire_insurance": "Proof of For-Hire Insurance",
            "wctlc_driver_permit": "WCTLC For-Hire Driver Permit",
            "wctlc_vehicle_permit": "WCTLC For-Hire Vehicle Permit",
            "wctlc_insurance": "Proof of Adequate Insurance",
            "wctlc_defensive_driving":
                "Defensive Driving Course Proof of Completion",
        }
        for doc_type, label in expected.items():
            self.assertEqual(docs[doc_type]["label"], label, doc_type)
            self.assertTrue(docs[doc_type]["hint"], doc_type)
            self.assertEqual(docs[doc_type]["field"],
                             app_module.FIELD_FOR_DOC_TYPE[doc_type])
            self.assertEqual(docs[doc_type]["accept"], "image/*",
                             "only FH-1 accepts PDF")

    def test_state_lists_unchanged_by_upstate_overrides(self):
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
            app_module.required_docs_for("New York", "Rochester"),
            app_module.ROCHESTER_DOC_TYPES)
        self.assertEqual(
            app_module.required_docs_for("New York", "Syracuse"),
            app_module.SYRACUSE_DOC_TYPES)
        self.assertEqual(
            app_module.required_docs_for("New York", "Yonkers"),
            app_module.YONKERS_DOC_TYPES)
        # Albany, New York city, "Other city", and no city keep the
        # NYC state list.
        for city in ("New York", "Albany", "Other city", None):
            with self.subTest(city=city):
                self.assertEqual(
                    app_module.required_docs_for("New York", city),
                    app_module.DOC_TYPES)
        self.assertTrue(app_module.local_note_for("New York", "Rochester"))
        self.assertTrue(app_module.local_note_for("New York", "Syracuse"))
        self.assertTrue(app_module.local_note_for("New York", "Yonkers"))
        self.assertFalse(app_module.local_note_for("New York", "Albany"))
        self.assertFalse(app_module.local_note_for("New York", "New York"))
        self.assertFalse(app_module.local_note_for("New York", None))
        # Minnesota's Rochester is a different city with its OWN
        # list (Midwest batch): the (state, city) key keeps the two
        # Rochesters apart.
        self.assertEqual(
            app_module.required_docs_for("Minnesota", "Rochester"),
            app_module.ROCHESTER_MN_DOC_TYPES)
        self.assertNotEqual(
            app_module.required_docs_for("Minnesota", "Rochester"),
            app_module.required_docs_for("New York", "Rochester"))
        self.assertNotEqual(
            app_module.required_docs_for("Minnesota", "Rochester"),
            app_module.required_docs_for_state("Minnesota"))

    # -- registration gate ----------------------------------------------------
    def test_rochester_registration_succeeds_and_stores_city(self):
        resp = self.register("New York", ROCHESTER_FIELDS, city="Rochester")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["state"], "New York")
        self.assertEqual(driver["city"], "Rochester")
        self.assertEqual(set(driver["docs"]), set(app_module.ROCHESTER_DOC_TYPES))

    def test_syracuse_registration_succeeds_and_stores_city(self):
        resp = self.register("New York", SYRACUSE_FIELDS, city="Syracuse")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["city"], "Syracuse")
        self.assertEqual(set(driver["docs"]), set(app_module.SYRACUSE_DOC_TYPES))

    def test_yonkers_registration_succeeds_and_stores_city(self):
        resp = self.register("New York", YONKERS_FIELDS, city="Yonkers")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["city"], "Yonkers")
        self.assertEqual(set(driver["docs"]), set(app_module.YONKERS_DOC_TYPES))

    def test_rochester_missing_hack_certificate_rejected_by_name(self):
        resp = self.register("New York", ROCHESTER_FIELDS, city="Rochester",
                             omit=("doc_rochester_hack_certificate",))
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Missing document: Taxicab License Certificate "
                      "(Hack Plate Certificate)", error)
        self.assertNotIn("TLC", error)

    def test_syracuse_missing_ground_transportation_rejected_by_name(self):
        resp = self.register("New York", SYRACUSE_FIELDS, city="Syracuse",
                             omit=("doc_syracuse_ground_transportation",))
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Missing document: Ground Transportation License",
                      error)
        self.assertNotIn("TLC", error)

    def test_yonkers_missing_driver_permit_rejected_by_name(self):
        resp = self.register("New York", YONKERS_FIELDS, city="Yonkers",
                             omit=("doc_wctlc_driver_permit",))
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Missing document: WCTLC For-Hire Driver Permit",
                      error)
        self.assertNotIn("TLC License", error)

    def test_nyc_docs_rejected_for_each_upstate_city(self):
        cases = [
            ("Rochester", "City of Rochester Taxicab Driver License"),
            ("Syracuse", "Taxi (Hack) License"),
            ("Yonkers", "WCTLC For-Hire Driver Permit"),
        ]
        for city, named_item in cases:
            with self.subTest(city=city):
                resp = self.register("New York", NY_FIELDS, city=city)
                self.assertEqual(resp.status_code, 400)
                error = resp.get_json()["error"]
                self.assertIn(named_item, error)
                self.assertIn("Vehicle Registration", error)
                self.assertNotIn("TLC License", error)
                self.assertNotIn("FH-1", error)

    # -- client wiring ----------------------------------------------------------
    def test_client_maps_carry_upstate_labels_and_fields(self):
        js = read("static/js/driver.js")
        labels = [
            "City of Rochester Taxicab Driver License",
            "Taxicab License Certificate (Hack Plate Certificate)",
            "Proof of Insurance",
            "Taxi (Hack) License",
            "Ground Transportation License",
            "Proof of For-Hire Insurance",
            "WCTLC For-Hire Driver Permit",
            "WCTLC For-Hire Vehicle Permit",
            "Proof of Adequate Insurance",
            "Defensive Driving Course Proof of Completion",
        ]
        for label in labels:
            self.assertIn('"%s"' % label, js, label)
        for doc_type in NEW_TYPES:
            self.assertIn('"%s"' % doc_type, js, doc_type)
            self.assertIn('"doc_%s"' % doc_type, js, doc_type)
        owner_js = read("static/js/owner.js")
        for label in labels:
            self.assertIn('"%s"' % label, owner_js, label)
        for doc_type in NEW_TYPES:
            self.assertIn('key: "%s"' % doc_type, owner_js, doc_type)

    def test_no_background_check_strings_in_client(self):
        js = read("static/js/driver.js")
        self.assertNotIn("background check", js.lower())
        self.assertNotIn("background_check", js.lower())


if __name__ == "__main__":
    unittest.main()
