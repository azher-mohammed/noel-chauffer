"""Tests for the driver registration state selector and per-state
document requirements.

Owner decision 2026-11-17 (voice call, "Exactly"): the 7 registration
documents are New York City / New York only ("ye base sirf New York
City ke vaaste hai") — a driver from New Jersey or Florida cannot
register today because the form demands TLC documents. Registration
now asks for the driver's state first (searchable dropdown, states
only, alphabetical, typing a letter shows every state starting with
it, like the car-model dropdown), and the compulsory list follows the
state. New York keeps EXACTLY the original 7 items. New Jersey has
its own list, verified from official NJ sources only (MVC Letter of
Qualification, municipal license to operate, limousine registration,
$1.5M insurance certificate). Florida licensing is county-level, so
no single statewide Florida list is claimed: Florida and every other
state without a verified list use the generic base list, and the
owner reviews each application. No state-specific permit or license
name is ever invented.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
import uuid

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-statedocs-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "statedocs.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "statedocs-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NY_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_tlc_license", "TLC License", "tlc.png"),
    ("doc_fh1", "FH-1 Insurance Card", "fh1.png"),
    ("doc_registration", "Commercial Vehicle Registration", "reg.png"),
    ("doc_inspection", "NYS DMV Inspection", "insp.png"),
    ("doc_vehicle_permit", "TLC-for-hire Vehicle Permit", "permit.png"),
]
NJ_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_nj_qualification", "MVC Letter of Qualification", "qual.png"),
    ("doc_nj_municipal_license", "Municipal License to Operate", "muni.png"),
    ("doc_nj_limo_registration", "Limousine Vehicle Registration", "limo.png"),
    ("doc_nj_insurance", "Insurance Certificate", "ins.png"),
]
GENERIC_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_vehicle_registration", "Vehicle Registration", "reg.png"),
    ("doc_insurance_card", "Insurance Card", "ins.png"),
]


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class StateDocumentsCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, fields, omit=(), extra=None):
        self._seq += 1
        data = {
            "name": "State Driver", "phone": f"+1555007{self._seq:04d}",
            "email": f"state{self._seq}@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"SD{self._seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
        }
        if state is not None:
            data["state"] = state
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

    # -- states endpoint ------------------------------------------------------
    def test_states_endpoint_lists_all_states_alphabetically(self):
        resp = self.client.get("/api/states")
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        states = payload["states"]
        self.assertEqual(len(states), 51, "50 states + DC")
        self.assertEqual(states, sorted(states), "alphabetical order")
        self.assertIn("District of Columbia", states)
        self.assertIn("New York", states)
        self.assertIn("New Jersey", states)
        self.assertIn("Florida", states)
        # Typing N shows every N state, in order (owner's spec).
        n_states = [s for s in states if s.startswith("N")]
        self.assertEqual(n_states, ["Nebraska", "Nevada", "New Hampshire",
                                    "New Jersey", "New Mexico", "New York",
                                    "North Carolina", "North Dakota"])

    def test_states_endpoint_requirements_per_state(self):
        payload = self.client.get("/api/states").get_json()
        reqs = payload["requirements"]
        self.assertEqual(set(reqs), set(payload["states"]))
        self.assertEqual(reqs["New York"]["docs"], app_module.DOC_TYPES)
        self.assertFalse(reqs["New York"]["local_note"])
        self.assertEqual(reqs["New Jersey"]["docs"], app_module.NJ_DOC_TYPES)
        self.assertFalse(reqs["New Jersey"]["local_note"])
        self.assertEqual(reqs["Florida"]["docs"], app_module.GENERIC_DOC_TYPES)
        self.assertTrue(reqs["Florida"]["local_note"])
        self.assertEqual(reqs["Texas"]["docs"], app_module.GENERIC_DOC_TYPES)
        self.assertTrue(reqs["Texas"]["local_note"])
        # Every requirement starts with the profile picture, then the license.
        for state, req in reqs.items():
            self.assertEqual(req["docs"][0], "profile_picture", state)
            self.assertEqual(req["docs"][1], "dmv_license", state)

    def test_states_endpoint_documents_carry_labels_hints_fields(self):
        payload = self.client.get("/api/states").get_json()
        docs = payload["documents"]
        self.assertEqual(set(docs), set(app_module.ALL_DOC_LABELS))
        for doc_type, spec in docs.items():
            self.assertEqual(spec["label"], app_module.ALL_DOC_LABELS[doc_type])
            self.assertTrue(spec["hint"], doc_type)
            self.assertEqual(spec["field"], app_module.FIELD_FOR_DOC_TYPE[doc_type])
        self.assertIn(".pdf", docs["fh1_insurance"]["accept"])
        self.assertNotIn(".pdf", docs["dmv_license"]["accept"])
        self.assertNotIn(".pdf", docs["nj_insurance"]["accept"])

    # -- state required / validated --------------------------------------------
    def test_state_is_required(self):
        resp = self.register(None, NY_FIELDS)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["error"], "Missing required field: state.")

    def test_blank_state_is_required(self):
        resp = self.register("   ", NY_FIELDS)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], "Missing required field: state.")

    def test_unknown_state_rejected(self):
        for bad in ("Atlantis", "NY", "new york", "New York City"):
            with self.subTest(state=bad):
                resp = self.register(bad, NY_FIELDS)
                self.assertEqual(resp.status_code, 400,
                                 resp.get_data(as_text=True)[:200])
                self.assertEqual(resp.get_json()["error"],
                                 "Please choose your state from the list.")

    # -- New York: original 7, unchanged ----------------------------------------
    def test_new_york_registers_with_original_seven(self):
        resp = self.register("New York", NY_FIELDS)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["state"], "New York")
        self.assertEqual(set(driver["docs"]), set(app_module.DOC_TYPES))
        self.assertTrue(all(v == "completed" for v in driver["docs"].values()))

    def test_new_york_missing_item_names_only_that_item(self):
        resp = self.register("New York", NY_FIELDS, omit={"doc_tlc_license"})
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("TLC License", error)
        self.assertNotIn("MVC Letter of Qualification", error)
        self.assertNotIn("Insurance Card", error)
        self.assertNotIn("Vehicle Registration", error)

    def test_new_york_missing_all_lists_seven_in_order(self):
        resp = self.register("New York", [])
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertTrue(error.startswith("Missing document: "), error)
        for _field, label, _fname in NY_FIELDS:
            self.assertIn(label, error, label)
        self.assertLess(error.index("Profile Picture"), error.index("DMV driving license"))

    # -- New Jersey: verified list, no TLC needed ---------------------------------
    def test_new_jersey_registers_without_tlc_documents(self):
        resp = self.register("New Jersey", NJ_FIELDS)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["state"], "New Jersey")
        self.assertEqual(set(driver["docs"]), set(app_module.NJ_DOC_TYPES))
        self.assertTrue(all(v == "completed" for v in driver["docs"].values()))
        self.assertNotIn("tlc_license", driver["docs"])

    def test_new_jersey_missing_item_named(self):
        resp = self.register("New Jersey", NJ_FIELDS, omit={"doc_nj_insurance"})
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertEqual(
            error,
            "Missing document: Insurance Certificate. "
            "Please upload all required documents to complete registration.")
        resp = self.register("New Jersey", NJ_FIELDS, omit={"doc_nj_qualification"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("MVC Letter of Qualification", resp.get_json()["error"])

    def test_new_jersey_missing_all_lists_six_in_order(self):
        resp = self.register("New Jersey", [])
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        for _field, label, _fname in NJ_FIELDS:
            self.assertIn(label, error, label)
        self.assertNotIn("TLC License", error)
        self.assertLess(error.index("Profile Picture"), error.index("DMV driving license"))
        self.assertLess(error.index("DMV driving license"),
                        error.index("MVC Letter of Qualification"))

    # -- Florida + other states: generic base list ---------------------------------
    def test_florida_registers_with_generic_base_list(self):
        resp = self.register("Florida", GENERIC_FIELDS)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["state"], "Florida")
        self.assertEqual(set(driver["docs"]), set(app_module.GENERIC_DOC_TYPES))

    def test_florida_missing_item_named(self):
        resp = self.register("Florida", GENERIC_FIELDS, omit={"doc_insurance_card"})
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Insurance Card", error)
        self.assertNotIn("TLC License", error)
        self.assertNotIn("MVC Letter of Qualification", error)

    def test_other_state_uses_generic_base_list(self):
        resp = self.register("Texas", GENERIC_FIELDS)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        self.assertEqual(set(resp.get_json()["driver"]["docs"]),
                         set(app_module.GENERIC_DOC_TYPES))

    # -- profile-photo check applies in every state --------------------------------
    def test_profile_photo_shape_check_applies_for_new_jersey(self):
        data = {
            "name": "NJ Photo", "phone": "+15550079999", "email": "njp@test.com",
            "state": "New Jersey",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": "NJPHOTO",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(photo_factory.jpeg(500, 400)), "photo.jpg"),
        }
        for field, _label, fname in NJ_FIELDS[1:]:
            data[field] = (io.BytesIO(b"fake doc"), fname)
        resp = self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("portrait photo", resp.get_json()["error"])

    # -- state stored, visible to driver + owner ------------------------------------
    def test_state_returned_by_me_endpoint(self):
        resp = self.register("New Jersey", NJ_FIELDS)
        token = resp.get_json()["token"]
        me = self.client.get("/api/drivers/me", headers={"X-Driver-Token": token})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()["driver"]["state"], "New Jersey")

    def test_owner_drivers_list_shows_state(self):
        self.register("New Jersey", NJ_FIELDS)
        self.register("Florida", GENERIC_FIELDS)
        self.client.post("/api/owner/login", json={"pin": "9999"})
        rows = self.client.get("/api/owner/drivers").get_json()
        self.assertEqual([r["state"] for r in rows], ["New Jersey", "Florida"])

    # -- no retroactive blocking -------------------------------------------------------
    def test_legacy_driver_without_state_still_works(self):
        with app_module.app.app_context():
            driver = app_module.Driver(
                name="Legacy Driver", phone="+15550008888", email="legacy@test.com",
                car_model="Cadillac CT6", car_year=2023, vehicle_class="sedan",
                car_colour="Black", plate="LEGACY2",
                bank_encrypted=app_module.encrypt_bank("123456789", "021000021"),
                bank_last4="6789", token=uuid.uuid4().hex)
            app_module.db.session.add(driver)
            app_module.db.session.commit()
            driver_id = driver.id
        resp = self.client.post("/api/drivers/me/lookup", json={"phone": "+15550008888"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        token = resp.get_json()["token"]
        me = self.client.get("/api/drivers/me", headers={"X-Driver-Token": token})
        self.assertEqual(me.status_code, 200)
        driver_json = me.get_json()["driver"]
        # No state on file: reads as New York, the list he registered under.
        self.assertIsNone(driver_json["state"])
        self.assertEqual(set(driver_json["docs"]), set(app_module.DOC_TYPES))
        self.assertEqual(driver_json["docs"]["dmv_license"], "missing")
        resp = self.client.post("/api/drivers/me/availability", json={"available": True},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            self.assertTrue(app_module.Driver.query.get(driver_id).available)

    # -- frontend wiring ---------------------------------------------------------------
    def test_registration_form_has_state_dropdown(self):
        html = read("static/driver.html")
        self.assertIn('id="reg-state"', html)
        self.assertIn('id="state-list"', html)
        self.assertIn('id="state-note"', html)
        self.assertIn('id="docs-local-note"', html)
        self.assertIn('id="doc-items-extra"', html)
        self.assertIn("Document requirements vary by state and locality", html)
        self.assertIn("The owner reviews each application", html)
        # The New York form is untouched: all 7 items still static, in order.
        self.assertEqual(html.count("doc-name"), 7)
        self.assertLess(html.index("Profile Picture"), html.index("DMV driving license"))

    def test_driver_js_state_dropdown_and_per_state_docs(self):
        js = read("static/js/driver.js")
        self.assertIn("/api/states", js)
        self.assertIn("renderDocsForState", js)
        self.assertIn("requiredFileFields", js)
        self.assertIn("Please choose your state from the list.", js)
        self.assertIn('fd.append("state"', js)
        # Prefix filtering: one letter shows every state starting with it.
        self.assertIn("indexOf(q) === 0", js)
        # The submit handler still gates on the required uploads.
        self.assertIn("missingDocs.join", js)

    def test_server_labels_match_client_labels_for_all_doc_types(self):
        # One wording everywhere, including the new states' items: every
        # server label appears quoted in the driver app script.
        js = read("static/js/driver.js")
        for doc_type, label in app_module.ALL_DOC_LABELS.items():
            self.assertIn('"%s"' % label, js, doc_type)

    def test_owner_dashboard_shows_state_and_new_document_labels(self):
        owner_js = read("static/js/owner.js")
        for label in ("MVC Letter of Qualification", "Municipal License to Operate",
                      "Limousine Vehicle Registration", "Insurance Certificate",
                      "Vehicle Registration", "Insurance Card"):
            self.assertIn('"%s"' % label, owner_js, label)
        self.assertIn("State: ", owner_js)
        css = read("static/css/driver.css")
        self.assertIn(".state-list", css)


if __name__ == "__main__":
    unittest.main()
