"""Tests for the 18 Midwest city-specific document overrides.

Owner decision 2026-11-17 night ("Haan bhai every city ka wahan ke
rules"): every city in the picker gets its own local rules,
verified from official sources only. The Midwest batch is the
third implementation batch (after the NY batch and the Southeast
batch): Chicago, Rockford, Springfield (IL); Evansville,
Indianapolis (IN); Minneapolis, Rochester, Saint Paul (MN);
Columbia, Independence, Jefferson City, Kansas City, Saint Louis
(MO); Lincoln (NE); Columbus (OH); Kenosha, Madison, Milwaukee
(WI).

Three banked cities were DROPPED at build-time re-verification
and keep the state-list fallback: Fort Wayne, IN (Ch. 116 is a
taxi-only stale chapter, no issuance confirmed), Sioux Falls, SD
(no driver-license name, form, or limousine scope verified), and
Toledo, OH (the cited section is the low-speed-vehicle chapter;
the real chapter's text could not be retrieved). See the ledger
CITY_RESEARCH.md.

Held for owner decisions (NOT slots): Kansas City's physical-exam
copy and Social Security / work-authorization proof, Saint Louis'
physical exam results and Social Security / work-eligibility
proof, Springfield IL's Social Security card photocopy, and
Indianapolis' Social Security / work-authorization card — same
privacy handling as the DC SSN slot and the other medical items.
The owner-review note stays ON for Springfield IL, Indianapolis,
Minneapolis, Rochester MN, Columbia, Independence, Jefferson
City, Kansas City, Saint Louis, Lincoln, Columbus, and Kenosha
(held items, gaps the gate cannot express, unretrieved
checklists, or flagged livery scope — see the per-city comments
in app.py and the ledger).

Columbus was re-verified at build time from the City License
Section page and the current VFH Driver Application (08-27-26):
the Certified Ohio BMV Driver Abstract (within 30 days) is a
named requirement for new or expired applicants, so it is gated
alongside the license. The Experience Columbus Insider
accreditation is Professional-license-only (conditional, not
gated); the BCI background check is never built.

No background check anywhere (owner declined it outright), no
age/experience gate, no document count anywhere ("Quantity
nahi"). Kansas City, MO keeps its list on the Missouri side
only — Kansas City, KS falls back to the Kansas state list and
must never inherit the Missouri regime. Bismarck, ND stays on
fallback (dormant regime — coordinator decision, see the ledger).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-midwest-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "midwest-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE = ["profile_picture", "dmv_license", "vehicle_registration"]

# (state, city) -> (expected doc list, owner-review note on?)
EXPECTED = {
    ("Illinois", "Chicago"): (BASE + ["chicago_chauffeur_license",
                                      "chicago_livery_vehicle_license",
                                      "chicago_insurance_certificate"], False),
    ("Illinois", "Rockford"): (BASE + ["rockford_taxi_driver_license"], False),
    ("Illinois", "Springfield"): (BASE + ["springfield_il_taxi_driver_license"], True),
    ("Indiana", "Evansville"): (BASE + ["evansville_taxi_driver_license"], False),
    ("Indiana", "Indianapolis"): (BASE + ["indianapolis_operator_license",
                                          "indianapolis_training_certificate",
                                          "indianapolis_bmv_record"], True),
    ("Minnesota", "Minneapolis"): (BASE + ["minneapolis_taxi_driver_license",
                                           "minneapolis_training_certificate"], True),
    ("Minnesota", "Rochester"): (BASE + ["rochester_mn_taxi_driver_license"], True),
    ("Minnesota", "Saint Paul"): (BASE + ["saint_paul_taxi_driver_license",
                                          "saint_paul_training_proof"], False),
    ("Missouri", "Columbia"): (BASE + ["columbia_chauffeur_license"], True),
    ("Missouri", "Independence"): (BASE + ["independence_vehicle_driver_permit"], True),
    ("Missouri", "Jefferson City"): (BASE + ["jefferson_city_taxi_driver_permit",
                                             "jefferson_city_driving_record"], True),
    ("Missouri", "Kansas City"): (BASE + ["kansas_city_driver_certificate",
                                          "kansas_city_operating_record"], True),
    ("Missouri", "Saint Louis"): (BASE + ["saint_louis_mtc_license",
                                          "saint_louis_driver_history"], True),
    ("Nebraska", "Lincoln"): (BASE + ["lincoln_taxi_driver_license"], True),
    ("Ohio", "Columbus"): (BASE + ["columbus_vfh_license",
                                   "columbus_bmv_abstract"], True),
    ("Wisconsin", "Kenosha"): (BASE + ["kenosha_taxi_driver_license"], True),
    ("Wisconsin", "Madison"): (BASE + ["madison_ppv_permit"], False),
    ("Wisconsin", "Milwaukee"): (BASE + ["milwaukee_ppv_license"], False),
}

LABELS = {
    "chicago_chauffeur_license": "Restricted Livery Public Chauffeur License (Chicago)",
    "chicago_livery_vehicle_license": "Livery Vehicle License (Chicago)",
    "chicago_insurance_certificate": "Commercial Insurance Certificate (Chicago)",
    "rockford_taxi_driver_license": "Taxi Cab Driver License (Rockford)",
    "springfield_il_taxi_driver_license": "Taxicab Driver License (Springfield, IL)",
    "evansville_taxi_driver_license": "City of Evansville Taxicab Driver License",
    "indianapolis_operator_license": "Operator License (Indianapolis)",
    "indianapolis_training_certificate": "Taxi Training Course Certificate (Indianapolis)",
    "indianapolis_bmv_record": "Certified BMV Driving Record (Within 10 Days)",
    "minneapolis_taxi_driver_license": "Taxi Driver License (Minneapolis)",
    "minneapolis_training_certificate": "Taxi Driver Training Certificate (Minneapolis)",
    "rochester_mn_taxi_driver_license": "Taxicab Driver License (Rochester, MN)",
    "saint_paul_taxi_driver_license": "Taxicab Driver License (Saint Paul)",
    "saint_paul_training_proof": "Taxicab Driver Training Course Completion Proof",
    "columbia_chauffeur_license": "Chauffeur License (Columbia)",
    "independence_vehicle_driver_permit": "Vehicle Driver Permit (Independence)",
    "jefferson_city_taxi_driver_permit": "Taxi Driver Permit (Jefferson City)",
    "jefferson_city_driving_record": "Certified Driving Record (Missouri DOR)",
    "kansas_city_driver_certificate": "Vehicle-for-Hire Driver Certificate (Kansas City)",
    "kansas_city_operating_record": "State Operating Record (Missouri)",
    "saint_louis_mtc_license": "MTC Driver License (Saint Louis)",
    "saint_louis_driver_history": "Missouri Driver History Report (Within 10 Days)",
    "lincoln_taxi_driver_license": "Taxicab Driver License (Lincoln)",
    "kenosha_taxi_driver_license": "Taxi Driver License (Kenosha)",
    "madison_ppv_permit": "Public Passenger Vehicle Driver Permit (Madison)",
    "milwaukee_ppv_license": "Public Passenger Vehicle Driver License (Milwaukee)",
    "columbus_vfh_license": "Vehicle for Hire Driver License (Columbus)",
    "columbus_bmv_abstract": "Certified Ohio BMV Driver Abstract (Within 30 Days)",
}

# Fallback cities in the same states: they keep their state list.
# Fort Wayne, Sioux Falls, and Toledo are the build-time drops;
# Kansas City, KS must never inherit the Missouri regime;
# Bismarck stays fallback (dormant regime).
FALLBACK_CITIES = [
    ("Illinois", "Aurora"),
    ("Indiana", "Fort Wayne"),
    ("Minnesota", "Duluth"),
    ("Missouri", "Springfield"),
    ("Kansas", "Kansas City"),
    ("Nebraska", "Omaha"),
    ("Ohio", "Toledo"),
    ("Ohio", "Cleveland"),
    ("South Dakota", "Sioux Falls"),
    ("Wisconsin", "Racine"),
    ("North Dakota", "Bismarck"),
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


class MidwestDocumentsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, fields, city=None, omit=()):
        self._seq += 1
        data = {
            "name": "Midwest Driver", "phone": f"+1555034{self._seq:04d}",
            "email": f"midwest{self._seq}@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"MW{self._seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
        }
        if state is not None:
            data["state"] = state
        if city is not None:
            data["city"] = city
        for field, _label, fname in fields:
            if field in omit:
                continue
            filedata = (photo_factory.VALID_PROFILE_PHOTO
                        if field == "profile_photo" else b"fake doc")
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
        self.assertEqual(set(overrides["Texas"]),
                         {"Dallas", "Austin", "Houston", "San Antonio"})
        self.assertEqual(set(overrides["New York"]),
                         {"Buffalo", "Rochester", "Syracuse", "Yonkers"})
        self.assertEqual(set(overrides["Illinois"]),
                         {"Chicago", "Rockford", "Springfield"})
        self.assertEqual(set(overrides["Indiana"]),
                         {"Evansville", "Indianapolis"})
        self.assertEqual(set(overrides["Minnesota"]),
                         {"Minneapolis", "Rochester", "Saint Paul"})
        self.assertEqual(set(overrides["Missouri"]),
                         {"Columbia", "Independence", "Jefferson City",
                          "Kansas City", "Saint Louis"})
        self.assertEqual(set(overrides["Nebraska"]), {"Lincoln"})
        self.assertEqual(set(overrides["Ohio"]), {"Columbus"})
        self.assertEqual(set(overrides["Wisconsin"]),
                         {"Kenosha", "Madison", "Milwaukee"})
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

    def test_dropped_cities_have_no_override(self):
        for key in (("Indiana", "Fort Wayne"),
                    ("South Dakota", "Sioux Falls"),
                    ("Ohio", "Toledo")):
            self.assertNotIn(key, app_module.CITY_DOC_REQUIREMENTS)
        for doc_type in app_module.FIELD_FOR_DOC_TYPE:
            self.assertNotIn("toledo", doc_type)
            self.assertNotIn("fort_wayne", doc_type)
            self.assertNotIn("sioux_falls", doc_type)

    def test_state_lists_unchanged_by_midwest_overrides(self):
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
        # Kansas City, KS must not inherit the Missouri list.
        self.assertNotEqual(
            app_module.required_docs_for("Kansas", "Kansas City"),
            app_module.required_docs_for("Missouri", "Kansas City"))
        # Rochester, MN is a different list from Rochester, NY.
        self.assertNotEqual(
            app_module.required_docs_for("Minnesota", "Rochester"),
            app_module.required_docs_for("New York", "Rochester"))

    # -- registration gate ----------------------------------------------------
    def test_each_midwest_city_registers_with_its_own_docs(self):
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
            ("Illinois", "Chicago", "doc_chicago_chauffeur_license",
             "Restricted Livery Public Chauffeur License (Chicago)"),
            ("Missouri", "Kansas City", "doc_kansas_city_driver_certificate",
             "Vehicle-for-Hire Driver Certificate (Kansas City)"),
            ("Missouri", "Saint Louis", "doc_saint_louis_driver_history",
             "Missouri Driver History Report (Within 10 Days)"),
            ("Ohio", "Columbus", "doc_columbus_bmv_abstract",
             "Certified Ohio BMV Driver Abstract (Within 30 Days)"),
            ("Indiana", "Indianapolis", "doc_indianapolis_bmv_record",
             "Certified BMV Driving Record (Within 10 Days)"),
            ("Minnesota", "Minneapolis", "doc_minneapolis_training_certificate",
             "Taxi Driver Training Certificate (Minneapolis)"),
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
        # A Kansas City, MO driver with only the Missouri state-list
        # documents is told the city items by name — never asked for
        # an SSN card, a physical exam, or any other held item.
        state_docs = app_module.required_docs_for_state("Missouri")
        resp = self.register("Missouri", fields_for(state_docs),
                             city="Kansas City")
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Vehicle-for-Hire Driver Certificate (Kansas City)",
                      error)
        self.assertIn("State Operating Record (Missouri)", error)
        self.assertNotIn("Social Security", error)
        self.assertNotIn("Physical", error)

    # -- client wiring ----------------------------------------------------------
    def test_client_maps_carry_midwest_labels_and_fields(self):
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
