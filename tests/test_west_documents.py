"""Tests for the West/Pacific batch: Portland, OR only.

Owner decision 2026-11-17 night ("Haan bhai every city ka wahan ke
rules"): every city in the picker gets its own local rules,
verified from official sources only. The West/Pacific batch is
the sixth and last implementation batch (after the NY, Southeast,
Midwest, Northeast, and South Central/Mountain batches): Portland,
OR alone.

Anchorage, Fairbanks, and Juneau, AK were banked but DROPPED at
build-time re-verification (operative code text unretrievable in
all three — Municode 403s; Juneau limousine coverage unproven
from Juneau sources) and keep the state-list fallback. The
Municipality of Anchorage Limousine Permit is vehicle-level and
is never a driver slot. See the ledger CITY_RESEARCH.md.

Portland was verified at build time from current City Code
§16.40.370(A) (certification) and §16.40.370(H) (business
license); the LPT regime (§16.40.670) imposes the identical two
requirements. The code calls it certification via a
company-submitted driver list, so the label says certification.
Training/testing is process (no named certificate); the ASE
inspection is conditional and vehicle-level. The FASTTRACK portal
checklist itself is login-gated and unretrieved, so the
owner-review note stays ON.

Uber cross-check (owner instruction 2026-11-18): Uber Portland
pages MATCH the business license (free; upload artifact is the
Certificate of Compliance, named in the slot hint) but name a
display-only TNC for-hire permit instead of the certification —
a regime difference, flagged in the ledger; the certification
stands on the verbatim code text. The Uber-named vehicle
inspection form is NOT built (in-person step; flagged per the
registration-ease rule). Generic vehicle insurance is NOT added
(Uber US-wide upload, not a Portland-named document).

No background check anywhere (owner declined it outright), no
age/experience gate, no document count anywhere ("Quantity
nahi"). Portland, OR keeps its own list — never confuse it with
Portland, ME.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-west-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "west-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE = ["profile_picture", "dmv_license", "vehicle_registration"]

# (state, city) -> (expected doc list, owner-review note on?)
EXPECTED = {
    ("Oregon", "Portland"): (BASE + ["portland_or_certification",
                                     "portland_or_business_license"], True),
}

LABELS = {
    "portland_or_certification": "Executive Town Car Driver Certification (Portland)",
    "portland_or_business_license": "City of Portland Business License",
}

# Fallback cities: they keep their state list. Anchorage,
# Fairbanks, and Juneau are the build-time drops.
FALLBACK_CITIES = [
    ("Oregon", "Eugene"),
    ("Oregon", "Salem"),
    ("Alaska", "Anchorage"),
    ("Alaska", "Fairbanks"),
    ("Alaska", "Juneau"),
    ("Washington", "Seattle"),
    ("California", "Los Angeles"),
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


class WestDocumentsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, fields, city=None, omit=()):
        self._seq += 1
        data = {
            "name": "West Driver", "phone": f"+1555037{self._seq:04d}",
            "email": "west@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"WE{self._seq:05d}",
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
        self.assertEqual(set(overrides["Oregon"]), {"Portland"})
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
        # The business-license hint names Uber's upload artifact.
        self.assertIn("Certificate of Compliance",
                      docs["portland_or_business_license"]["hint"])

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

    def test_no_inspection_or_tnc_permit_slots(self):
        # The Uber-named inspection form and the TNC for-hire
        # permit are NOT slots in the Portland list.
        for (state, city), (docs, _note) in EXPECTED.items():
            with self.subTest(state=state, city=city):
                labels = " ".join(app_module.ALL_DOC_LABELS[t] for t in docs)
                self.assertNotIn("Inspection", labels)
                self.assertNotIn("TNC", labels)
                self.assertNotIn("tnc", " ".join(docs))

    def test_dropped_cities_have_no_override(self):
        for key in (("Alaska", "Anchorage"), ("Alaska", "Fairbanks"),
                    ("Alaska", "Juneau")):
            self.assertNotIn(key, app_module.CITY_DOC_REQUIREMENTS)
        self.assertTrue(all(state != "Alaska"
                            for state, _ in app_module.CITY_DOC_REQUIREMENTS))
        for doc_type in app_module.FIELD_FOR_DOC_TYPE:
            self.assertNotIn("anchorage", doc_type)
            self.assertNotIn("fairbanks", doc_type)
            self.assertNotIn("juneau", doc_type)

    def test_state_lists_unchanged_by_west_overrides(self):
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
        # Portland, OR is a different list from Portland, ME.
        self.assertNotEqual(
            app_module.required_docs_for("Oregon", "Portland"),
            app_module.required_docs_for("Maine", "Portland"))

    # -- registration gate ----------------------------------------------------
    def test_portland_registers_with_its_own_docs(self):
        for (state, city), (docs, _note) in EXPECTED.items():
            with self.subTest(state=state, city=city):
                resp = self.register(state, fields_for(docs), city=city)
                self.assertEqual(resp.status_code, 201,
                                 resp.get_data(as_text=True)[:300])
                driver = resp.get_json()["driver"]
                self.assertEqual(driver["state"], state)
                self.assertEqual(driver["city"], city)
                self.assertEqual(set(driver["docs"]), set(docs))

    def test_missing_item_rejected_by_name(self):
        cases = [
            ("doc_portland_or_certification",
             "Executive Town Car Driver Certification (Portland)"),
            ("doc_portland_or_business_license",
             "City of Portland Business License"),
        ]
        docs, _note = EXPECTED[("Oregon", "Portland")]
        for omit_field, label in cases:
            with self.subTest(field=omit_field):
                resp = self.register("Oregon", fields_for(docs),
                                     city="Portland", omit=(omit_field,))
                self.assertEqual(resp.status_code, 400)
                self.assertIn("Missing document: %s" % label,
                              resp.get_json()["error"])

    def test_state_list_docs_do_not_satisfy_city_override(self):
        # A Portland driver with only the Oregon state-list
        # documents is told both city items by name.
        state_docs = app_module.required_docs_for_state("Oregon")
        resp = self.register("Oregon", fields_for(state_docs),
                             city="Portland")
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Executive Town Car Driver Certification (Portland)",
                      error)
        self.assertIn("City of Portland Business License", error)

    # -- client wiring ----------------------------------------------------------
    def test_client_maps_carry_west_labels_and_fields(self):
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
