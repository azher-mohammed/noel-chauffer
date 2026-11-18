"""Tests for the complete Uber-style per-state driver document lists.

Owner order 2026-11-17 (voice call, "complete Uber driver ke
document jaisa hi banana"): every state gets its OWN separate
document list — no merging or mixing between states — built from
the official-source research report (51 jurisdictions, 6 VERIFIED /
31 PARTIAL / 14 UNVERIFIED). New York keeps EXACTLY its 7 items and
New Jersey EXACTLY its 6. VERIFIED states (DC, Maine, Rhode Island,
Washington) carry their complete official lists. PARTIAL states
carry the generic base 4 plus ONLY officially-named extra items,
and keep the owner-review note. UNVERIFIED states and county/city-
level states (Florida, Illinois, Texas, Massachusetts) stay on the
generic base list — nothing invented, no city list applied
statewide. Process-type requirements (background checks, drug
tests, courses, exams) are never upload slots. No document count
is shown anywhere (owner decision 2026-11-17, "Quantity nahi").

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-allstates-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "allstates.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "allstates-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Expected lists, exactly as built from the research report. Keys are
# doc types; the first two are always the profile picture and the
# driving license (standing owner order).
EXPECTED = {
    "Alabama": ["profile_picture", "dmv_license", "al_certificate",
                "vehicle_registration", "al_form_e"],
    "California": ["profile_picture", "dmv_license", "ca_tcp_permit",
                   "ca_driver_statement", "ca_commercial_registration",
                   "ca_inspection_declaration", "insurance_card"],
    "Colorado": ["profile_picture", "dmv_license", "co_ll_permit",
                 "vehicle_registration", "co_inspection", "co_form_e"],
    "Connecticut": ["profile_picture", "dmv_license", "ct_livery_permit",
                    "vehicle_registration", "insurance_card"],
    "Delaware": ["profile_picture", "dmv_license", "de_certificate",
                 "de_limo_registration", "de_inspection", "insurance_card"],
    "District of Columbia": ["profile_picture", "dmv_license",
                             "dc_drivers_record", "dc_ssc", "dc_residency",
                             "dc_medical_form", "dc_face_id",
                             "dc_public_vehicle_license", "vehicle_registration",
                             "dc_inspection", "insurance_card"],
    "Georgia": ["profile_picture", "dmv_license", "ga_carrier_certificate",
                "vehicle_registration", "ga_insurance_certificate"],
    "Hawaii": ["profile_picture", "dmv_license", "hi_carrier_certificate",
               "hi_vehicle_inventory", "hi_tax_clearance",
               "vehicle_registration", "insurance_card"],
    "Kansas": ["profile_picture", "dmv_license", "ks_certificate",
               "vehicle_registration", "insurance_card"],
    "Kentucky": ["profile_picture", "dmv_license", "ky_limousine_certificate",
                 "ky_vehicle_license", "vehicle_registration", "ky_inspection",
                 "insurance_card"],
    "Maine": ["profile_picture", "dmv_license", "me_registration", "me_jb_filing"],
    "Maryland": ["profile_picture", "dmv_license", "md_for_hire_license",
                 "vehicle_registration", "md_inspection_certificate",
                 "insurance_card"],
    "Michigan": ["profile_picture", "dmv_license", "mi_carrier_license",
                 "vehicle_registration", "insurance_card"],
    "Minnesota": ["profile_picture", "dmv_license", "mn_permit",
                  "vehicle_registration", "mn_inspection", "mn_form_e"],
    "Missouri": ["profile_picture", "dmv_license", "mo_authority",
                 "vehicle_registration", "insurance_card"],
    "Nebraska": ["profile_picture", "dmv_license", "ne_medical_certificate",
                 "ne_carrier_authority", "vehicle_registration", "insurance_card"],
    "Nevada": ["profile_picture", "dmv_license", "nv_drivers_permit", "nv_cpcn",
               "vehicle_registration", "insurance_card"],
    "New Mexico": ["profile_picture", "dmv_license", "vehicle_registration",
                   "nm_inspection", "insurance_card"],
    "Ohio": ["profile_picture", "dmv_license", "oh_livery_registration",
             "insurance_card"],
    "Pennsylvania": ["profile_picture", "dmv_license", "pa_driving_history",
                     "pa_criminal_history", "pa_certificate",
                     "vehicle_registration", "pa_inspection", "pa_form_e"],
    "Rhode Island": ["profile_picture", "dmv_license", "ri_operator_license",
                     "ri_driving_record", "ri_criminal_record",
                     "vehicle_registration", "insurance_card"],
    "South Carolina": ["profile_picture", "dmv_license", "sc_driving_record",
                       "sc_charter_certificate", "sc_ls_registration", "sc_form_e"],
    "Tennessee": ["profile_picture", "dmv_license", "tn_citizenship_proof",
                  "tn_residency_proof", "vehicle_registration", "insurance_card"],
    "Virginia": ["profile_picture", "dmv_license", "va_authority", "va_title",
                 "va_for_hire_registration", "va_authority_registration",
                 "insurance_card"],
    "Washington": ["profile_picture", "dmv_license", "wa_medical_certificate",
                   "wa_driving_record", "wa_carrier_license",
                   "wa_vehicle_certificate", "wa_chauffeur_addendum",
                   "wa_fh_registration", "wa_inspection_report",
                   "wa_insurance_certificate"],
}

UNVERIFIED = ["Alaska", "Arizona", "Arkansas", "Idaho", "Montana",
              "New Hampshire", "North Carolina", "North Dakota", "Oklahoma",
              "Oregon", "South Dakota", "Vermont", "Wisconsin", "Wyoming"]

LOCAL_ONLY = ["Florida", "Illinois", "Texas", "Massachusetts"]

# States whose only state-specific requirements live ON the license
# (a license class or endorsement visible in the license photo), so
# the generic list is the honest outcome: no invented extra slot.
LICENSE_ONLY = ["Indiana", "Iowa", "Louisiana", "Mississippi", "Utah",
                "West Virginia"]

VERIFIED = ["New York", "New Jersey", "District of Columbia", "Maine",
            "Rhode Island", "Washington"]


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class AllStateListsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, omit=()):
        """Register with exactly the state's own list (minus omissions)."""
        self._seq += 1
        data = {
            "name": "All States Driver", "phone": f"+1555011{self._seq:04d}",
            "email": "allstates@test.com", "state": state,
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"AS{self._seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
        }
        for doc_type in app_module.required_docs_for_state(state):
            if doc_type in omit:
                continue
            field = app_module.FIELD_FOR_DOC_TYPE[doc_type]
            filedata = (photo_factory.VALID_PROFILE_PHOTO
                        if field == "profile_photo" else b"fake doc")
            data[field] = (io.BytesIO(filedata), field + ".png")
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    # -- every state resolves, own list, own order ----------------------------
    def test_every_state_resolves_to_nonempty_list(self):
        self.assertEqual(len(app_module.US_STATES), 51)
        for state in app_module.US_STATES:
            docs = app_module.required_docs_for_state(state)
            self.assertTrue(docs, state)
            self.assertEqual(docs[0], "profile_picture", state)
            self.assertEqual(docs[1], "dmv_license", state)
            self.assertEqual(len(docs), len(set(docs)),
                             "no duplicate item in %s" % state)

    def test_new_york_and_new_jersey_byte_unchanged(self):
        self.assertEqual(app_module.DOC_TYPES, [
            "profile_picture", "dmv_license", "tlc_license", "fh1_insurance",
            "registration", "inspection", "vehicle_permit"])
        self.assertEqual(app_module.NJ_DOC_TYPES, [
            "profile_picture", "dmv_license", "nj_qualification",
            "nj_municipal_license", "nj_limo_registration", "nj_insurance"])
        self.assertEqual(app_module.GENERIC_DOC_TYPES, [
            "profile_picture", "dmv_license", "vehicle_registration",
            "insurance_card"])
        self.assertEqual(app_module.required_docs_for_state("New York"),
                         app_module.DOC_TYPES)
        self.assertEqual(app_module.required_docs_for_state("New Jersey"),
                         app_module.NJ_DOC_TYPES)

    def test_new_lists_match_report_exactly(self):
        self.assertEqual(set(EXPECTED), set(app_module.STATE_DOC_REQUIREMENTS)
                         - {"New York", "New Jersey"})
        for state, expected in EXPECTED.items():
            with self.subTest(state=state):
                self.assertEqual(app_module.required_docs_for_state(state),
                                 expected)

    def test_unverified_states_stay_generic(self):
        self.assertEqual(len(UNVERIFIED), 14)
        for state in UNVERIFIED:
            with self.subTest(state=state):
                self.assertNotIn(state, app_module.STATE_DOC_REQUIREMENTS)
                self.assertEqual(app_module.required_docs_for_state(state),
                                 app_module.GENERIC_DOC_TYPES)

    def test_county_city_states_stay_generic_no_city_list_statewide(self):
        for state in LOCAL_ONLY:
            with self.subTest(state=state):
                self.assertNotIn(state, app_module.STATE_DOC_REQUIREMENTS)
                self.assertEqual(app_module.required_docs_for_state(state),
                                 app_module.GENERIC_DOC_TYPES)
        # No Chicago / Miami-Dade / Broward item exists in any STATE
        # list. (City lists MAY carry them: "Miami-Dade Chauffeur
        # Registration" is Miami's own city-specific item, pinned in
        # tests/test_southeast_documents.py — it must never leak
        # into the Florida state list.)
        state_types = set()
        for state in app_module.US_STATES:
            state_types.update(app_module.required_docs_for_state(state))
        labels = " ".join(app_module.ALL_DOC_LABELS[t] for t in state_types)
        for forbidden in ("Public Chauffeur", "Chauffeur's Registration",
                          "Miami-Dade", "Broward", "Chicago"):
            self.assertNotIn(forbidden, labels)

    def test_license_only_states_stay_generic(self):
        for state in LICENSE_ONLY:
            with self.subTest(state=state):
                self.assertEqual(app_module.required_docs_for_state(state),
                                 app_module.GENERIC_DOC_TYPES)

    def test_state_specific_items_never_leak_between_states(self):
        # Each state's own items appear in that state only (the shared
        # base 4 aside): no mixing between states.
        base = set(app_module.GENERIC_DOC_TYPES)
        seen = {}
        for state in app_module.US_STATES:
            for doc_type in app_module.required_docs_for_state(state):
                if doc_type in base:
                    continue
                self.assertNotIn(doc_type, seen,
                                 "%s appears in both %s and %s"
                                 % (doc_type, seen.get(doc_type), state))
                seen[doc_type] = state

    def test_every_doc_type_has_label_hint_and_field(self):
        for state in app_module.US_STATES:
            for doc_type in app_module.required_docs_for_state(state):
                with self.subTest(state=state, doc_type=doc_type):
                    self.assertIn(doc_type, app_module.ALL_DOC_LABELS)
                    self.assertTrue(app_module.ALL_DOC_LABELS[doc_type])
                    self.assertIn(doc_type, app_module.DOC_HINTS)
                    self.assertTrue(app_module.DOC_HINTS[doc_type])
                    field = app_module.FIELD_FOR_DOC_TYPE[doc_type]
                    if doc_type == "profile_picture":
                        # Special case: the profile picture comes from
                        # the profile_photo field, not DOC_FIELD_MAP.
                        self.assertEqual(field, "profile_photo")
                    else:
                        self.assertEqual(app_module.DOC_FIELD_MAP.get(field), doc_type)
        # The field map is 1:1: no two fields share a doc type.
        self.assertEqual(len(app_module.DOC_FIELD_MAP),
                         len(set(app_module.DOC_FIELD_MAP.values())))

    # -- endpoint shape ---------------------------------------------------------
    def test_states_endpoint_serves_all_lists_and_notes(self):
        payload = self.client.get("/api/states").get_json()
        self.assertEqual(payload["states"], app_module.US_STATES)
        reqs = payload["requirements"]
        self.assertEqual(set(reqs), set(app_module.US_STATES))
        for state in app_module.US_STATES:
            with self.subTest(state=state):
                self.assertEqual(reqs[state]["docs"],
                                 app_module.required_docs_for_state(state))
                self.assertEqual(reqs[state]["local_note"],
                                 state not in VERIFIED)
        self.assertEqual(set(app_module.VERIFIED_DOC_STATES), set(VERIFIED))
        docs = payload["documents"]
        self.assertEqual(set(docs), set(app_module.ALL_DOC_LABELS))
        for doc_type, spec in docs.items():
            self.assertEqual(spec["label"], app_module.ALL_DOC_LABELS[doc_type])
            self.assertEqual(spec["hint"], app_module.DOC_HINTS[doc_type])
            self.assertEqual(spec["field"], app_module.FIELD_FOR_DOC_TYPE[doc_type])
            if doc_type != "fh1_insurance":
                self.assertEqual(spec["accept"], "image/*",
                                 "only FH-1 accepts PDF: %s" % doc_type)
        self.assertIn(".pdf", docs["fh1_insurance"]["accept"])

    def test_no_count_or_quantity_in_api_or_ui(self):
        # Owner decision 2026-11-17 ("Quantity nahi"): lists show
        # documents only, no counts anywhere.
        payload = self.client.get("/api/states").get_json()
        self.assertNotIn("count", payload)
        self.assertNotIn("quantity", payload)
        for req in payload["requirements"].values():
            self.assertNotIn("count", req)
            self.assertNotIn("quantity", req)
        js = read("static/js/driver.js")
        self.assertNotIn("required.length", js)
        self.assertIn("All items are required", js)
        html = read("static/driver.html")
        self.assertIn("All items are required", html)
        self.assertNotIn("All 7 items are required", html)

    # -- the gate enforces each state's own list ---------------------------------
    def test_district_registers_with_eleven_and_names_missing_face_id(self):
        resp = self.register("District of Columbia")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["state"], "District of Columbia")
        self.assertEqual(set(driver["docs"]),
                         set(app_module.required_docs_for_state("District of Columbia")))
        resp = self.register("District of Columbia", omit={"dc_face_id"})
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("For-Hire Operators (Face ID) License", error)
        self.assertNotIn("TLC License", error)
        self.assertNotIn("MVC Letter of Qualification", error)

    def test_washington_registers_and_names_missing_inspection(self):
        resp = self.register("Washington")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        resp = self.register("Washington", omit={"wa_inspection_report"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Vehicle Inspection Report", resp.get_json()["error"])

    def test_maine_registers_with_hire_plates_and_jb_filing(self):
        resp = self.register("Maine")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        driver = resp.get_json()["driver"]
        self.assertEqual(set(driver["docs"]),
                         {"profile_picture", "dmv_license", "me_registration",
                          "me_jb_filing"})
        resp = self.register("Maine", omit={"me_jb_filing"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Insurance Certificate for For-Hire Passenger Vehicle",
                      resp.get_json()["error"])

    def test_rhode_island_names_missing_blue_card(self):
        resp = self.register("Rhode Island", omit={"ri_operator_license"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Taxi-LPMV-PMV Operator's License", resp.get_json()["error"])

    def test_california_names_missing_tcp_permit(self):
        resp = self.register("California")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        resp = self.register("California", omit={"ca_tcp_permit"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Charter-Party Carrier (TCP) Permit", resp.get_json()["error"])

    def test_pennsylvania_names_missing_form_e(self):
        resp = self.register("Pennsylvania", omit={"pa_form_e"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Form E (Insurance Filing)", resp.get_json()["error"])

    def test_illinois_registers_with_generic_no_chicago_items(self):
        resp = self.register("Illinois")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        self.assertEqual(set(resp.get_json()["driver"]["docs"]),
                         set(app_module.GENERIC_DOC_TYPES))

    def test_alaska_registers_with_generic_and_names_missing_card(self):
        resp = self.register("Alaska")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        resp = self.register("Alaska", omit={"insurance_card"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Insurance Card", resp.get_json()["error"])

    def test_every_state_registers_with_its_own_list(self):
        # One full registration per state: the gate accepts exactly
        # the state's own list, nothing more, nothing less.
        for state in app_module.US_STATES:
            with self.subTest(state=state):
                resp = self.register(state)
                self.assertEqual(resp.status_code, 201,
                                 "%s: %s" % (state, resp.get_data(as_text=True)[:200]))
                self.assertEqual(set(resp.get_json()["driver"]["docs"]),
                                 set(app_module.required_docs_for_state(state)))

    def test_profile_photo_check_applies_for_new_state(self):
        data = {
            "name": "WA Photo", "phone": "+15550119999", "email": "wap@test.com",
            "state": "Washington",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": "WAPHOTO",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(photo_factory.jpeg(500, 400)), "photo.jpg"),
        }
        for doc_type in app_module.required_docs_for_state("Washington"):
            if doc_type == "profile_picture":
                continue
            field = app_module.FIELD_FOR_DOC_TYPE[doc_type]
            data[field] = (io.BytesIO(b"fake doc"), field + ".png")
        resp = self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("portrait photo", resp.get_json()["error"])

    def test_registered_driver_under_new_list_keeps_working(self):
        resp = self.register("Washington")
        token = resp.get_json()["token"]
        me = self.client.get("/api/drivers/me", headers={"X-Driver-Token": token})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()["driver"]["state"], "Washington")
        resp = self.client.post("/api/drivers/me/availability", json={"available": True},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    # -- client wiring --------------------------------------------------------------
    def test_client_maps_cover_every_doc_type(self):
        js = read("static/js/driver.js")
        for doc_type, label in app_module.ALL_DOC_LABELS.items():
            with self.subTest(doc_type=doc_type):
                self.assertIn('"%s"' % label, js, "label missing: %s" % doc_type)
                self.assertIn('"%s"' % doc_type, js,
                              "DOC_TYPE_ORDER missing: %s" % doc_type)
                field = app_module.FIELD_FOR_DOC_TYPE[doc_type]
                self.assertIn('"%s"' % field, js, "field missing: %s" % field)
        owner_js = read("static/js/owner.js")
        for doc_type, label in app_module.ALL_DOC_LABELS.items():
            with self.subTest(doc_type=doc_type):
                self.assertIn('"%s"' % label, owner_js,
                              "owner label missing: %s" % doc_type)
                self.assertIn('key: "%s"' % doc_type, owner_js,
                              "owner key missing: %s" % doc_type)


if __name__ == "__main__":
    unittest.main()
