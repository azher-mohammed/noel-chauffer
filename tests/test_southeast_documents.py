"""Tests for the 16 Southeast city-specific document overrides.

Owner decision 2026-11-17 night ("Haan bhai every city ka wahan ke
rules"): every city in the picker gets its own local rules,
verified from official sources only. The Southeast batch is the
second implementation batch (after the NY batch): Birmingham,
Huntsville, Mobile, Montgomery (AL); Miami, Orlando, Tallahassee,
Tampa (FL); Baton Rouge, New Orleans (LA); Biloxi, Gulfport (MS);
Charlotte, Durham (NC); Charleston (SC); Nashville (TN).

The five thin ones (Birmingham, Mobile, Montgomery, Tallahassee,
Durham) were re-verified by the coordinator before build; the
Durham New Driver Permit Checklist was retrieved in full. Held
for owner decisions (NOT slots): Birmingham's health and welfare
certificate (a physician's certificate), Durham's Physician's
Statement and Social Security Card, Charlotte's SSN card,
Charleston's Signed Medical Statement — same privacy handling as
the DC SSN slot and the other medical items. The owner-review
note stays ON for Birmingham, Huntsville, Montgomery, Miami,
Tallahassee, Charlotte, Durham, Charleston, and Nashville (held
items, OR-alternatives, unretrieved supporting documents, or
unverified currency — see the per-city comments in app.py and
the ledger CITY_RESEARCH.md).

No background check anywhere (owner declined it outright), no
age/experience gate, no document count anywhere ("Quantity
nahi"). Biloxi and Gulfport share ONE document type (the MVFHA
Driver Permit, from the same Harrison County interlocal
Authority) — not two cities copying each other.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-southeast-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "southeast-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE = ["profile_picture", "dmv_license", "vehicle_registration"]

# (state, city) -> (expected doc list, owner-review note on?)
EXPECTED = {
    ("Alabama", "Birmingham"): (BASE + ["birmingham_operator_permit"], True),
    ("Alabama", "Huntsville"): (BASE + ["huntsville_chauffeur_license"], True),
    ("Alabama", "Mobile"): (BASE + ["mobile_chauffeur_license"], False),
    ("Alabama", "Montgomery"): (BASE + ["montgomery_chauffeur_license"], True),
    ("Florida", "Miami"): (BASE + ["miami_chauffeur_registration"], True),
    ("Florida", "Orlando"): (BASE + ["orlando_driver_permit",
                                     "orlando_insurance"], False),
    ("Florida", "Tallahassee"): (BASE + ["tallahassee_driver_permit"], True),
    ("Florida", "Tampa"): (BASE + ["tampa_pvdl", "tampa_transcript"], False),
    ("Louisiana", "Baton Rouge"): (BASE + ["baton_rouge_chauffeur_license",
                                           "baton_rouge_driving_record",
                                           "baton_rouge_clearance"], False),
    ("Louisiana", "New Orleans"): (BASE + ["new_orleans_driver_permit",
                                           "new_orleans_mvr"], False),
    ("Mississippi", "Biloxi"): (BASE + ["mvfha_driver_permit"], False),
    ("Mississippi", "Gulfport"): (BASE + ["mvfha_driver_permit"], False),
    ("North Carolina", "Charlotte"): (BASE + ["charlotte_pvh_permit",
                                              "charlotte_driving_record"], True),
    ("North Carolina", "Durham"): (BASE + ["durham_pvfh_permit"], True),
    ("South Carolina", "Charleston"): (BASE + ["charleston_chauffeur_license",
                                               "charleston_driving_record"], True),
    ("Tennessee", "Nashville"): (BASE + ["nashville_opvh_permit",
                                         "nashville_mvr"], True),
}

LABELS = {
    "birmingham_operator_permit": "City of Birmingham Operator's Permit",
    "huntsville_chauffeur_license": "City of Huntsville Chauffeur License",
    "mobile_chauffeur_license": "City of Mobile Chauffeur License",
    "montgomery_chauffeur_license": "City of Montgomery Chauffeur License",
    "miami_chauffeur_registration": "Miami-Dade Chauffeur Registration",
    "orlando_driver_permit": "City of Orlando Driver Permit",
    "orlando_insurance": "Certificate of Insurance (City as Additional Insured)",
    "tallahassee_driver_permit": "City of Tallahassee Driver Permit",
    "tampa_pvdl": "Public Vehicle Driver License (Hillsborough County)",
    "tampa_transcript": "Seven-Year Driver License Transcript",
    "baton_rouge_chauffeur_license": "City of Baton Rouge Chauffeur License",
    "baton_rouge_driving_record": "Official Driving Record",
    "baton_rouge_clearance": "Clearance Certificate",
    "new_orleans_driver_permit": "CPNC Driver Permit (New Orleans)",
    "new_orleans_mvr": "Certified MVR (Within 30 Days)",
    "mvfha_driver_permit": "MVFHA Driver Permit",
    "charlotte_pvh_permit": "PVH Driver Permit (Charlotte)",
    "charlotte_driving_record": "Driving Record",
    "durham_pvfh_permit": "PVFH Driver Permit (Durham)",
    "charleston_chauffeur_license": "Chauffeur License (Charleston)",
    "charleston_driving_record": "Certified 10-Year Driving Record",
    "nashville_opvh_permit": "MTLC OPVH Driver Permit",
    "nashville_mvr": "Motor Vehicle Record (Within 30 Days)",
}

# Fallback cities in the same states: they keep their state list.
FALLBACK_CITIES = [
    ("Alabama", "Tuscaloosa"),
    ("Florida", "Jacksonville"),
    ("Louisiana", "Shreveport"),
    ("Mississippi", "Jackson"),
    ("North Carolina", "Raleigh"),
    ("South Carolina", "Columbia"),
    ("Tennessee", "Memphis"),
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


class SoutheastDocumentsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, fields, city=None, omit=()):
        self._seq += 1
        data = {
            "name": "Southeast Driver", "phone": f"+1555024{self._seq:04d}",
            "email": f"southeast{self._seq}@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"SE{self._seq:05d}",
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
    def test_city_requirements_cover_all_overrides(self):
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
        self.assertEqual(set(overrides["Alabama"]),
                         {"Birmingham", "Huntsville", "Mobile", "Montgomery"})
        self.assertEqual(set(overrides["Florida"]),
                         {"Miami", "Orlando", "Tallahassee", "Tampa"})
        self.assertEqual(set(overrides["Louisiana"]),
                         {"Baton Rouge", "New Orleans"})
        self.assertEqual(set(overrides["Mississippi"]),
                         {"Biloxi", "Gulfport"})
        self.assertEqual(set(overrides["North Carolina"]),
                         {"Charlotte", "Durham"})
        self.assertEqual(set(overrides["South Carolina"]), {"Charleston"})
        self.assertEqual(set(overrides["Tennessee"]), {"Nashville"})
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

    def test_state_lists_unchanged_by_southeast_overrides(self):
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
        # Biloxi and Gulfport share the MVFHA type by design.
        self.assertEqual(app_module.BILOXI_DOC_TYPES,
                         app_module.GULFPORT_DOC_TYPES)

    # -- registration gate ----------------------------------------------------
    def test_each_southeast_city_registers_with_its_own_docs(self):
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
            ("Alabama", "Birmingham", "doc_birmingham_operator_permit",
             "City of Birmingham Operator's Permit"),
            ("North Carolina", "Charlotte", "doc_charlotte_pvh_permit",
             "PVH Driver Permit (Charlotte)"),
            ("North Carolina", "Durham", "doc_durham_pvfh_permit",
             "PVFH Driver Permit (Durham)"),
            ("Tennessee", "Nashville", "doc_nashville_opvh_permit",
             "MTLC OPVH Driver Permit"),
            ("Florida", "Tampa", "doc_tampa_transcript",
             "Seven-Year Driver License Transcript"),
            ("Louisiana", "Baton Rouge", "doc_baton_rouge_clearance",
             "Clearance Certificate"),
        ]
        for state, city, omit_field, label in cases:
            with self.subTest(city=city):
                docs, _note = EXPECTED[(state, city)]
                resp = self.register(state, fields_for(docs), city=city,
                                     omit=(omit_field,))
                self.assertEqual(resp.status_code, 400)
                self.assertIn("Missing document: %s" % label,
                              resp.get_json()["error"])

    def test_state_list_docs_do_not_satisfy_city_override(self):
        # A Charlotte driver with only the North Carolina state-list
        # documents is told the city items by name — never asked for
        # an SSN card or any other held item.
        state_docs = app_module.required_docs_for_state("North Carolina")
        resp = self.register("North Carolina", fields_for(state_docs),
                             city="Charlotte")
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("PVH Driver Permit (Charlotte)", error)
        self.assertIn("Driving Record", error)
        self.assertNotIn("Social Security", error)

    # -- client wiring ----------------------------------------------------------
    def test_client_maps_carry_southeast_labels_and_fields(self):
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
