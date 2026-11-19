"""Tests for the 15 South Central/Mountain city-specific document overrides.

Owner decision 2026-11-17 night ("Haan bhai every city ka wahan ke
rules"): every city in the picker gets its own local rules,
verified from official sources only. The South Central/Mountain
batch is the fifth implementation batch (after the NY, Southeast,
Midwest, and Northeast batches): Little Rock, Springdale (AR);
Boise, Idaho Falls (ID); Oklahoma City, Tulsa (OK); Austin,
Houston, San Antonio (TX); St. George (UT); Cheyenne, Gillette
(WY); Henderson, Las Vegas, North Las Vegas (NV).

Norman, OK was banked but DROPPED at build-time re-verification
(live Municode text unretrievable; unresolved Ch. 13 to Ch. 20
renumbering question) and keeps the state-list fallback. Denver,
CO stays on the state-list fallback (current Ch. 55 text
unretrievable). See the ledger CITY_RESEARCH.md.

Tulsa was re-verified at build time from the live Business
Licensing page and the chauffeur new application: the MVR Report
(within 30 days) is required for NEW applications too, so it is
gated alongside the Chauffeur License. Gillette was verified from
the current posted Ch. 19 text read end to end. St. George is
gated on official city checklists + the 2024 issuance register;
the verbatim code text was not retrieved, so the owner-review
note stays ON for the code-text gap.

Held for owner decisions (NOT slots): Oklahoma City's driver
medical certification, Tulsa's SSN card + physical exam form,
and Gillette's SSN-adjacent application input — same privacy
handling as the DC SSN slot and the other medical items. The
owner-review note stays ON for Idaho Falls (Operator OR Owner
alternative), Oklahoma City, Tulsa, Austin (conditional
defensive-driving proof), San Antonio (training-certificate
question), St. George, Gillette, and the three Clark County
cities (livery-scope question: the county license is evidenced
for TNC drivers only).

Uber cross-check (owner instruction 2026-11-18): Uber city pages
were retrieved in full only for Las Vegas (MATCH on the Clark
County item, TNC framing only), Houston, San Antonio, Tulsa, and
Oklahoma City; for the other cities only the generic Uber
template page was retrieved (partial evidence — recorded in the
ledger, not treated as proof Uber has no requirement). The Las
Vegas vehicle inspection form is NOT built (in-person step;
flagged per the registration-ease rule). The Houston For Hire
Permit named by Uber reads vehicle-level and Black-only, so it is
NOT a driver slot. Proof of residency (Uber template boilerplate)
is NOT added to any city list.

No background check anywhere (owner declined it outright), no
age/experience gate, no document count anywhere ("Quantity
nahi"). The three Clark County cities share ONE county-level
item. Denver stays fallback; Norman stays fallback.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-south-central-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "south-central-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE = ["profile_picture", "dmv_license", "vehicle_registration"]

# (state, city) -> (expected doc list, owner-review note on?)
EXPECTED = {
    ("Arkansas", "Little Rock"): (BASE + ["little_rock_gt_driver_permit"], False),
    ("Arkansas", "Springdale"): (BASE + ["springdale_taxi_driver_permit"], False),
    ("Idaho", "Boise"): (BASE + ["boise_cts_driver_license"], False),
    ("Idaho", "Idaho Falls"): (BASE + ["idaho_falls_operator_license"], True),
    ("Oklahoma", "Oklahoma City"): (BASE + ["okc_vfh_driver_permit"], True),
    ("Oklahoma", "Tulsa"): (BASE + ["tulsa_chauffeur_license", "tulsa_mvr"], True),
    ("Texas", "Austin"): (BASE + ["austin_chauffeur_permit"], True),
    ("Texas", "Houston"): (BASE + ["houston_vfh_driver_license"], False),
    ("Texas", "San Antonio"): (BASE + ["san_antonio_driver_permit"], True),
    ("Utah", "St. George"): (BASE + ["st_george_for_hire_permit"], True),
    ("Wyoming", "Cheyenne"): (BASE + ["cheyenne_pt_driver_permit"], False),
    ("Wyoming", "Gillette"): (BASE + ["gillette_pt_driver_permit"], True),
    ("Nevada", "Henderson"): (BASE + ["clark_county_business_license"], True),
    ("Nevada", "Las Vegas"): (BASE + ["clark_county_business_license"], True),
    ("Nevada", "North Las Vegas"): (BASE + ["clark_county_business_license"], True),
}

LABELS = {
    "little_rock_gt_driver_permit": "Ground Transportation Service Driver Permit (Little Rock)",
    "springdale_taxi_driver_permit": "Taxicab Driver Permit (Springdale)",
    "boise_cts_driver_license": "Commercial Transportation Service Driver License (Boise)",
    "idaho_falls_operator_license": "Public Transportation Operator License (Idaho Falls)",
    "okc_vfh_driver_permit": "Vehicle-for-Hire Driver Permit (Oklahoma City)",
    "tulsa_chauffeur_license": "City of Tulsa Chauffeur License",
    "tulsa_mvr": "MVR Report (Within 30 Days)",
    "austin_chauffeur_permit": "Chauffeur Permit (Austin)",
    "houston_vfh_driver_license": "City-Issued Vehicle-for-Hire Driver License (Houston)",
    "san_antonio_driver_permit": "City of San Antonio Driver Permit (Vehicles for Hire)",
    "st_george_for_hire_permit": "For-Hire Driver Permit (St. George)",
    "cheyenne_pt_driver_permit": "Public Transportation Driver Permit (Cheyenne)",
    "gillette_pt_driver_permit": "Public Transportation Driver Permit (Gillette)",
    "clark_county_business_license": "Clark County Business License",
}

# Fallback cities in the same states: they keep their state list.
# Norman is the build-time drop; Denver stays fallback.
FALLBACK_CITIES = [
    ("Arkansas", "Fayetteville"),
    ("Idaho", "Meridian"),
    ("Nevada", "Reno"),
    ("Nevada", "Sparks"),
    ("Oklahoma", "Norman"),
    ("Oklahoma", "Broken Arrow"),
    ("Texas", "Fort Worth"),
    ("Utah", "Salt Lake City"),
    ("Utah", "Provo"),
    ("Wyoming", "Casper"),
    ("Colorado", "Denver"),
]


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def fields_for(doc_types):
    fields = []
    for doc_type in doc_types:
        field = app_module.FIELD_FOR_DOC_TYPE[doc_type]
        fields.append((field, LABELS.get(doc_type, doc_type),
                       "%s.png" % doc_type))
    return fields


class SouthCentralDocumentsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, fields, city=None, omit=()):
        self._seq += 1
        data = {
            "name": "South Central Driver", "phone": f"+1555036{self._seq:04d}",
            "email": f"southcentral{self._seq}@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"SC{self._seq:05d}",
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
        for field, _label, fname in fields:
            if field in omit:
                continue
            filedata = (photo_factory.VALID_PROFILE_PHOTO
                        if field == "profile_photo" else photo_factory.doc_photo())
            data[field] = (io.BytesIO(filedata), fname)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    # -- endpoint -------------------------------------------------------------
    def test_city_requirements_cover_all_62_overrides(self):
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
        self.assertEqual(set(overrides["Arkansas"]),
                         {"Little Rock", "Springdale"})
        self.assertEqual(set(overrides["Idaho"]),
                         {"Boise", "Idaho Falls"})
        self.assertEqual(set(overrides["Oklahoma"]),
                         {"Oklahoma City", "Tulsa"})
        self.assertEqual(set(overrides["Texas"]),
                         {"Dallas", "Austin", "Houston", "San Antonio"})
        self.assertEqual(set(overrides["Utah"]), {"St. George"})
        self.assertEqual(set(overrides["Wyoming"]),
                         {"Cheyenne", "Gillette"})
        self.assertEqual(set(overrides["Nevada"]),
                         {"Henderson", "Las Vegas", "North Las Vegas"})
        total = sum(len(cities) for cities in overrides.values())
        self.assertEqual(total, 62)
        for (state, city), (docs, note) in EXPECTED.items():
            with self.subTest(state=state, city=city):
                got = overrides[state][city]
                self.assertEqual(got["docs"], docs)
                self.assertEqual(got["local_note"], note)
                self.assertEqual(
                    got["docs"],
                    app_module.CITY_DOC_REQUIREMENTS[(state, city)])

    def test_new_docs_carry_labels_hints_fields(self):
        payload = self.client.get("/api/states").get_json()
        docs = payload["documents"]
        for doc_type, label in LABELS.items():
            with self.subTest(doc_type=doc_type):
                self.assertEqual(docs[doc_type]["label"], label)
                self.assertTrue(docs[doc_type]["hint"])
                self.assertEqual(docs[doc_type]["field"],
                                 app_module.FIELD_FOR_DOC_TYPE[doc_type])
                self.assertEqual(docs[doc_type]["accept"], "image/*",
                                 "only FH-1 accepts PDF")

    def test_no_background_ssn_or_medical_slots(self):
        for (state, city), (docs, _note) in EXPECTED.items():
            with self.subTest(state=state, city=city):
                self.assertNotIn("background_check", docs)
                self.assertNotIn("dc_ssc", docs)
                self.assertNotIn("dc_medical_form", docs)
                self.assertNotIn("wa_medical_certificate", docs)
                self.assertNotIn("ne_medical_certificate", docs)
                labels = " ".join(app_module.ALL_DOC_LABELS[t] for t in docs)
                self.assertNotIn("Background", labels)
                self.assertNotIn("Social Security", labels)
                self.assertNotIn("Medical", labels)
                self.assertNotIn("Physician", labels)
                self.assertNotIn("Health", labels)

    def test_no_inspection_or_residency_slots(self):
        # The Las Vegas inspection form and Uber-template proof of
        # residency are NOT slots in any South Central list.
        for (state, city), (docs, _note) in EXPECTED.items():
            with self.subTest(state=state, city=city):
                labels = " ".join(app_module.ALL_DOC_LABELS[t] for t in docs)
                self.assertNotIn("Inspection", labels)
                self.assertNotIn("Residency", labels)

    def test_dropped_cities_have_no_override(self):
        for key in (("Oklahoma", "Norman"), ("Colorado", "Denver")):
            self.assertNotIn(key, app_module.CITY_DOC_REQUIREMENTS)
        for doc_type in app_module.FIELD_FOR_DOC_TYPE:
            self.assertNotIn("norman", doc_type)
            self.assertNotIn("denver", doc_type)
            self.assertNotIn("herdic", doc_type)

    def test_state_lists_unchanged_by_south_central_overrides(self):
        payload = self.client.get("/api/states").get_json()
        reqs = payload["requirements"]
        self.assertEqual(reqs["New York"]["docs"], app_module.DOC_TYPES)
        self.assertEqual(reqs["New Jersey"]["docs"], app_module.NJ_DOC_TYPES)
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
        for (state, city), (docs, note) in EXPECTED.items():
            with self.subTest(state=state, city=city):
                self.assertEqual(app_module.required_docs_for(state, city),
                                 docs)
                self.assertEqual(app_module.local_note_for(state, city), note)
        for state, city in FALLBACK_CITIES:
            with self.subTest(state=state, city=city):
                self.assertEqual(
                    app_module.required_docs_for(state, city),
                    app_module.required_docs_for_state(state))
        # The three Clark County cities share ONE county-level list.
        self.assertEqual(
            app_module.required_docs_for("Nevada", "Henderson"),
            app_module.required_docs_for("Nevada", "Las Vegas"))
        self.assertEqual(
            app_module.required_docs_for("Nevada", "Las Vegas"),
            app_module.required_docs_for("Nevada", "North Las Vegas"))
        # Dallas keeps its own list; the other Texas cities differ.
        self.assertNotEqual(
            app_module.required_docs_for("Texas", "Austin"),
            app_module.required_docs_for("Texas", "Dallas"))
        self.assertNotEqual(
            app_module.required_docs_for("Texas", "Houston"),
            app_module.required_docs_for("Texas", "Dallas"))

    # -- registration gate ----------------------------------------------------
    def test_each_south_central_city_registers_with_its_own_docs(self):
        for (state, city), (docs, _note) in EXPECTED.items():
            with self.subTest(state=state, city=city):
                resp = self.register(state, fields_for(docs), city=city)
                self.assertEqual(resp.status_code, 201,
                                 resp.get_data(as_text=True)[:300])
                driver = resp.get_json()["driver"]
                self.assertEqual(driver["state"], state)
                self.assertEqual(driver["city"], city)
                self.assertEqual(set(driver["docs"]), set(docs))

    def test_missing_permit_rejected_by_name(self):
        cases = [
            ("Oklahoma", "Tulsa", "doc_tulsa_mvr",
             "MVR Report (Within 30 Days)"),
            ("Oklahoma", "Tulsa", "doc_tulsa_chauffeur_license",
             "City of Tulsa Chauffeur License"),
            ("Oklahoma", "Oklahoma City", "doc_okc_vfh_driver_permit",
             "Vehicle-for-Hire Driver Permit (Oklahoma City)"),
            ("Texas", "Austin", "doc_austin_chauffeur_permit",
             "Chauffeur Permit (Austin)"),
            ("Nevada", "Las Vegas", "doc_clark_county_business_license",
             "Clark County Business License"),
            ("Utah", "St. George", "doc_st_george_for_hire_permit",
             "For-Hire Driver Permit (St. George)"),
        ]
        for state, city, omit_field, label in cases:
            with self.subTest(city=city, field=omit_field):
                docs, _note = EXPECTED[(state, city)]
                resp = self.register(state, fields_for(docs), city=city,
                                     omit=(omit_field,))
                self.assertEqual(resp.status_code, 400)
                self.assertIn("Missing document: %s" % label,
                              resp.get_json()["error"])

    def test_state_list_docs_do_not_satisfy_city_override(self):
        # A Tulsa driver with only the Oklahoma state-list documents
        # is told both city items by name — never asked for an SSN
        # card, a physical exam, or any other held item.
        state_docs = app_module.required_docs_for_state("Oklahoma")
        resp = self.register("Oklahoma", fields_for(state_docs),
                             city="Tulsa")
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("City of Tulsa Chauffeur License", error)
        self.assertIn("MVR Report (Within 30 Days)", error)
        self.assertNotIn("Social Security", error)
        self.assertNotIn("Physical", error)
        # A Las Vegas driver with only the Nevada state-list
        # documents is told the county item by name.
        state_docs = app_module.required_docs_for_state("Nevada")
        resp = self.register("Nevada", fields_for(state_docs),
                             city="Las Vegas")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Clark County Business License",
                      resp.get_json()["error"])

    # -- client wiring ----------------------------------------------------------
    def test_client_maps_carry_south_central_labels_and_fields(self):
        js = read("static/js/driver.js")
        for doc_type, label in LABELS.items():
            self.assertIn('"%s"' % label, js, label)
            self.assertIn('"%s"' % doc_type, js, doc_type)
            self.assertIn('"doc_%s"' % doc_type, js, doc_type)
        owner_js = read("static/js/owner.js")
        for doc_type, label in LABELS.items():
            self.assertIn('"%s"' % label, owner_js, label)
            self.assertIn('key: "%s"' % doc_type, owner_js, doc_type)

    def test_no_background_check_strings_in_client(self):
        js = read("static/js/driver.js")
        self.assertNotIn("background check", js.lower())
        self.assertNotIn("background_check", js.lower())


if __name__ == "__main__":
    unittest.main()
