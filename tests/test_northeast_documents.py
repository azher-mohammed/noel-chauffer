"""Tests for the 7 Northeast city-specific document overrides.

Owner decision 2026-11-17 night ("Haan bhai every city ka wahan ke
rules"): every city in the picker gets its own local rules,
verified from official sources only. The Northeast batch is the
fourth implementation batch (after the NY batch, the Southeast
batch, and the Midwest batch): Portland, South Portland (ME);
Lowell, Springfield, Worcester (MA); Jersey City (NJ);
Philadelphia (PA).

Two banked cities were DROPPED at build-time re-verification
and keep the state-list fallback: Newark, NJ (no operative
Ch. 34:2 text retrievable, no Ch. 34:3 OR-alternative found, no
current issuance evidence) and Rutland, VT (no operative chapter
text or definition retrieved; the cited "Subch. 3" is a charter
power grant, not a license requirement). See the ledger
CITY_RESEARCH.md.

Portland, ME was re-verified at build time: Ch. 30 §§30-31/30-32
require a city livery driver license, and §30-17A ("Service on
Peaks Island") imposes livery licensing there — it exempts
nothing relevant. The vehicle business-license coverage in
§30-31(b) is a structural gap, so the owner-review note stays ON
for Portland.

Held for owner decisions (NOT slots): Springfield MA's
citizenship / Social Security / medical inputs and
Philadelphia's Social Security / work-authorization inputs —
same privacy handling as the DC SSN slot and the other medical
items. The owner-review note stays ON for Portland, South
Portland (unverified reciprocity exception), Springfield MA, and
Philadelphia. It stays OFF for Lowell, Worcester, and Jersey
City.

No background check anywhere (owner declined it outright), no
age/experience gate, no document count anywhere ("Quantity
nahi"). Springfield, MA keeps its own list — never confuse it
with Springfield, IL or Springfield, MO. Portland, ME keeps its
own list — never confuse it with Portland, OR. Newark, NJ falls
back to the New Jersey state list; Rutland, VT falls back to the
Vermont state list.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-northeast-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "northeast-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE = ["profile_picture", "dmv_license", "vehicle_registration"]

# (state, city) -> (expected doc list, owner-review note on?)
EXPECTED = {
    ("Maine", "Portland"): (BASE + ["portland_me_livery_license"], True),
    ("Maine", "South Portland"): (BASE + ["south_portland_taxi_driver_license"], True),
    ("Massachusetts", "Lowell"): (BASE + ["lowell_hackney_license"], False),
    ("Massachusetts", "Springfield"): (BASE + ["springfield_ma_chauffeur_license"], True),
    ("Massachusetts", "Worcester"): (BASE + ["worcester_taxi_livery_license"], False),
    ("New Jersey", "Jersey City"): (BASE + ["jersey_city_limo_driver_license"], False),
    ("Pennsylvania", "Philadelphia"): (BASE + ["philadelphia_limo_certificate"], True),
}

LABELS = {
    "portland_me_livery_license": "Portland Livery Driver License",
    "south_portland_taxi_driver_license": "South Portland Taxicab Driver License",
    "lowell_hackney_license": "Hackney License (Lowell)",
    "springfield_ma_chauffeur_license": "Chauffeur License (Springfield, MA)",
    "worcester_taxi_livery_license": "Taxi-Livery Driver License (Worcester)",
    "jersey_city_limo_driver_license": "Jersey City Limousine Driver License",
    "philadelphia_limo_certificate": "PPA Limousine Driver Certificate",
}

# Fallback cities in the same states: they keep their state list.
# Newark and Rutland are the build-time drops.
FALLBACK_CITIES = [
    ("Maine", "Bangor"),
    ("Massachusetts", "Boston"),
    ("New Jersey", "Newark"),
    ("New Jersey", "Trenton"),
    ("Pennsylvania", "Pittsburgh"),
    ("Vermont", "Rutland"),
    ("Vermont", "Burlington"),
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


class NortheastDocumentsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, fields, city=None, omit=()):
        self._seq += 1
        data = {
            "name": "Northeast Driver", "phone": f"+1555035{self._seq:04d}",
            "email": f"northeast{self._seq}@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"NE{self._seq:05d}",
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
        self.assertEqual(set(overrides["Maine"]),
                         {"Portland", "South Portland"})
        self.assertEqual(set(overrides["Massachusetts"]),
                         {"Lowell", "Springfield", "Worcester"})
        self.assertEqual(set(overrides["New Jersey"]), {"Jersey City"})
        self.assertEqual(set(overrides["Pennsylvania"]), {"Philadelphia"})
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
        for key in (("New Jersey", "Newark"), ("Vermont", "Rutland")):
            self.assertNotIn(key, app_module.CITY_DOC_REQUIREMENTS)
        for doc_type in app_module.FIELD_FOR_DOC_TYPE:
            self.assertNotIn("newark", doc_type)
            self.assertNotIn("rutland", doc_type)

    def test_state_lists_unchanged_by_northeast_overrides(self):
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
        # Springfield, MA is a different list from Springfield, IL
        # and Springfield, MO.
        self.assertNotEqual(
            app_module.required_docs_for("Massachusetts", "Springfield"),
            app_module.required_docs_for("Illinois", "Springfield"))
        self.assertNotEqual(
            app_module.required_docs_for("Massachusetts", "Springfield"),
            app_module.required_docs_for("Missouri", "Springfield"))
        # Portland, ME is a different list from Portland, OR (which
        # has its own list since the West batch).
        self.assertNotEqual(
            app_module.required_docs_for("Maine", "Portland"),
            app_module.required_docs_for("Oregon", "Portland"))

    # -- registration gate ----------------------------------------------------
    def test_each_northeast_city_registers_with_its_own_docs(self):
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
            ("Maine", "Portland", "doc_portland_me_livery_license",
             "Portland Livery Driver License"),
            ("Massachusetts", "Springfield",
             "doc_springfield_ma_chauffeur_license",
             "Chauffeur License (Springfield, MA)"),
            ("New Jersey", "Jersey City", "doc_jersey_city_limo_driver_license",
             "Jersey City Limousine Driver License"),
            ("Pennsylvania", "Philadelphia", "doc_philadelphia_limo_certificate",
             "PPA Limousine Driver Certificate"),
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
        # A Philadelphia driver with only the Pennsylvania state-list
        # documents is told the city item by name — never asked for
        # an SSN card or work-authorization proof.
        state_docs = app_module.required_docs_for_state("Pennsylvania")
        resp = self.register("Pennsylvania", fields_for(state_docs),
                             city="Philadelphia")
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("PPA Limousine Driver Certificate", error)
        self.assertNotIn("Social Security", error)
        # A Springfield, MA driver with only the Massachusetts
        # state-list documents is told the city item by name —
        # never asked for SSN or medical items.
        state_docs = app_module.required_docs_for_state("Massachusetts")
        resp = self.register("Massachusetts", fields_for(state_docs),
                             city="Springfield")
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Chauffeur License (Springfield, MA)", error)
        self.assertNotIn("Social Security", error)
        self.assertNotIn("Medical", error)

    # -- client wiring ----------------------------------------------------------
    def test_client_maps_carry_northeast_labels_and_fields(self):
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
