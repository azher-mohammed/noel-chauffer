"""Tests for the Uber-style city picker in driver registration and the
city-specific document lists.

Owner decision 2026-11-17 (voice call, "City picker bana do, Uber
jaisa"): registration asks for the city the driver drives in, right
after the state, in the same searchable-dropdown pattern (type a
letter, see every matching city in that state, alphabetical). Uber
asks for the city at signup and varies requirements by city; Noel
keeps the state picker and adds the city picker after it.

Effective list rule: a city with a verified city-specific list
overrides its state list; every other city uses the state list
unchanged. Dallas, Texas is the FIRST city-specific list,
from Uber's official pages only (Uber Help livery article + Uber
Dallas vehicle-requirements page): license, commercial insurance,
vehicle registration, Dallas Driver Permit, City of Dallas or Fort
Worth limo permit, plus the profile picture. (Buffalo, New York
is the second — see tests/test_buffalo_documents.py.) Fort Worth was
researched and has NO city-specific list (Fort Worth licenses the
operating business, not the individual driver), so it falls back to
the Texas state list — never assume Fort Worth = Dallas. Every
state's city list ends with the "Other city" fallback, so drivers in
unlisted towns are never blocked. No background check of any kind,
no document count anywhere ("Quantity nahi").

City NAMES come from the Census Bureau's July 1, 2025 estimates as
tabulated on Wikipedia ("List of largest cities of U.S. states and
territories by population"): the five most populous incorporated
places per state, plus the capital where it is not among the five.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
import uuid

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-citypicker-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "citypicker-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DALLAS_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_vehicle_registration", "Vehicle Registration", "reg.png"),
    ("doc_dallas_commercial_insurance", "Commercial Insurance Certificate", "comm.png"),
    ("doc_dallas_driver_permit", "Dallas Driver Permit", "dallas.png"),
    ("doc_dallas_limo_permit", "City Limo Permit (Dallas / Fort Worth)", "limo.png"),
]
GENERIC_FIELDS = [
    ("profile_photo", "Profile Picture", "photo.jpg"),
    ("doc_dmv_license", "DMV driving license", "license.png"),
    ("doc_vehicle_registration", "Vehicle Registration", "reg.png"),
    ("doc_insurance_card", "Insurance Card", "ins.png"),
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


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class CityPickerCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, state, fields, city=None, omit=(), extra=None):
        self._seq += 1
        data = {
            "name": "City Driver", "phone": f"+1555011{self._seq:04d}",
            "email": "city@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"CD{self._seq:05d}",
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

    # -- cities endpoint ------------------------------------------------------
    def test_states_endpoint_serves_cities_for_every_state(self):
        payload = self.client.get("/api/states").get_json()
        cities = payload["cities"]
        self.assertEqual(set(cities), set(payload["states"]))
        for state, names in cities.items():
            with self.subTest(state=state):
                self.assertTrue(names, state)
                # "Other city" fallback last, so unlisted towns are
                # never blocked; the real names stay alphabetical.
                self.assertEqual(names[-1], "Other city", state)
                self.assertEqual(names[:-1], sorted(names[:-1]), state)
        self.assertIn("Washington, D.C.", cities["District of Columbia"])

    def test_texas_cities_include_dallas_and_fort_worth(self):
        payload = self.client.get("/api/states").get_json()
        texas = payload["cities"]["Texas"]
        self.assertEqual(texas, ["Austin", "Dallas", "Fort Worth",
                                 "Houston", "San Antonio", "Other city"])
        # Typing D shows every D city, in order (owner's spec, same
        # as the state picker).
        d_cities = [c for c in texas if c.startswith("D")]
        self.assertEqual(d_cities, ["Dallas"])

    def test_city_requirements_cover_dallas_and_buffalo(self):
        payload = self.client.get("/api/states").get_json()
        overrides = payload["city_requirements"]
        # Dallas (first) and Buffalo (second) are the city-specific
        # lists; Buffalo is pinned in tests/test_buffalo_documents.py.
        # Rochester, Syracuse, and Yonkers joined as the third,
        # fourth, and fifth (tests/test_upstate_ny_documents.py),
        # then the 16-city Southeast batch
        # (tests/test_southeast_documents.py).
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
        dallas = overrides["Texas"]["Dallas"]
        self.assertEqual(dallas["docs"], app_module.DALLAS_DOC_TYPES)
        self.assertEqual(dallas["docs"], [
            "profile_picture", "dmv_license", "vehicle_registration",
            "dallas_commercial_insurance", "dallas_driver_permit",
            "dallas_limo_permit"])
        self.assertFalse(dallas["local_note"])
        # Fort Worth has NO city-specific list: it falls back to the
        # Texas state list. Never assume Fort Worth = Dallas.
        self.assertNotIn("Fort Worth", overrides["Texas"])

    def test_dallas_docs_carry_labels_hints_fields(self):
        payload = self.client.get("/api/states").get_json()
        docs = payload["documents"]
        self.assertEqual(docs["dallas_commercial_insurance"]["label"],
                         "Commercial Insurance Certificate")
        self.assertEqual(docs["dallas_driver_permit"]["label"],
                         "Dallas Driver Permit")
        self.assertEqual(docs["dallas_limo_permit"]["label"],
                         "City Limo Permit (Dallas / Fort Worth)")
        for doc_type in ("dallas_commercial_insurance",
                         "dallas_driver_permit", "dallas_limo_permit"):
            self.assertTrue(docs[doc_type]["hint"], doc_type)
            self.assertEqual(docs[doc_type]["field"],
                             app_module.FIELD_FOR_DOC_TYPE[doc_type])
            self.assertEqual(docs[doc_type]["accept"], "image/*",
                             "only FH-1 accepts PDF")

    def test_state_lists_unchanged_by_city_picker(self):
        # NY + NJ byte-unchanged; Texas keeps the generic list and
        # the owner-review note at state level.
        payload = self.client.get("/api/states").get_json()
        reqs = payload["requirements"]
        self.assertEqual(reqs["New York"]["docs"], app_module.DOC_TYPES)
        self.assertFalse(reqs["New York"]["local_note"])
        self.assertEqual(reqs["New Jersey"]["docs"], app_module.NJ_DOC_TYPES)
        self.assertFalse(reqs["New Jersey"]["local_note"])
        self.assertEqual(reqs["Texas"]["docs"], app_module.GENERIC_DOC_TYPES)
        self.assertTrue(reqs["Texas"]["local_note"])
        for state in app_module.US_STATES:
            self.assertEqual(reqs[state]["docs"],
                             app_module.required_docs_for_state(state))

    def test_no_count_or_quantity_in_city_payload(self):
        payload = self.client.get("/api/states").get_json()
        self.assertNotIn("count", payload)
        self.assertNotIn("quantity", payload)
        for req in payload["city_requirements"].values():
            for city_req in req.values():
                self.assertNotIn("count", city_req)
                self.assertNotIn("quantity", city_req)

    # -- effective list rule --------------------------------------------------
    def test_required_docs_for_effective_list(self):
        self.assertEqual(
            app_module.required_docs_for("Texas", "Dallas"),
            app_module.DALLAS_DOC_TYPES)
        self.assertEqual(
            app_module.required_docs_for("Texas", "Fort Worth"),
            app_module.GENERIC_DOC_TYPES)
        self.assertEqual(
            app_module.required_docs_for("Texas", "Other city"),
            app_module.GENERIC_DOC_TYPES)
        self.assertEqual(
            app_module.required_docs_for("Texas", None),
            app_module.GENERIC_DOC_TYPES)
        self.assertEqual(
            app_module.required_docs_for("Texas", "Houston"),
            app_module.HOUSTON_DOC_TYPES)
        self.assertEqual(
            app_module.required_docs_for("New York", "New York"),
            app_module.DOC_TYPES)
        self.assertFalse(app_module.local_note_for("Texas", "Dallas"))
        self.assertTrue(app_module.local_note_for("Texas", "Fort Worth"))
        self.assertTrue(app_module.local_note_for("Texas", None))

    # -- registration gate ----------------------------------------------------
    def test_dallas_registration_with_all_docs_succeeds_and_stores_city(self):
        resp = self.register("Texas", DALLAS_FIELDS, city="Dallas")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["state"], "Texas")
        self.assertEqual(driver["city"], "Dallas")
        self.assertEqual(set(driver["docs"]), set(app_module.DALLAS_DOC_TYPES))

    def test_dallas_registration_missing_permit_is_rejected_by_name(self):
        resp = self.register("Texas", DALLAS_FIELDS, city="Dallas",
                             omit=("doc_dallas_driver_permit",))
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Missing document: Dallas Driver Permit", error)
        # The Dallas list has no generic insurance card: the error
        # must not ask for it.
        self.assertNotIn("Insurance Card", error)

    def test_dallas_registration_with_only_generic_docs_is_rejected(self):
        resp = self.register("Texas", GENERIC_FIELDS, city="Dallas")
        self.assertEqual(resp.status_code, 400)
        error = resp.get_json()["error"]
        self.assertIn("Commercial Insurance Certificate", error)
        self.assertIn("Dallas Driver Permit", error)
        self.assertIn("City Limo Permit (Dallas / Fort Worth)", error)

    def test_fort_worth_falls_back_to_texas_state_list(self):
        resp = self.register("Texas", GENERIC_FIELDS, city="Fort Worth")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        driver = resp.get_json()["driver"]
        self.assertEqual(driver["city"], "Fort Worth")
        self.assertEqual(set(driver["docs"]), set(app_module.GENERIC_DOC_TYPES))

    def test_other_city_falls_back_to_state_list(self):
        resp = self.register("Texas", GENERIC_FIELDS, city="Other city")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        self.assertEqual(resp.get_json()["driver"]["city"], "Other city")

    def test_unknown_city_is_rejected(self):
        resp = self.register("Texas", GENERIC_FIELDS, city="Springfield")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"],
                         "Please choose your city from the list.")

    def test_city_from_another_state_is_rejected(self):
        resp = self.register("New York", NY_FIELDS, city="Dallas")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"],
                         "Please choose your city from the list.")

    def test_no_city_keeps_state_list_backward_compatible(self):
        # Drivers registered before the city picker (and older
        # clients) send no city: the state list gates them.
        resp = self.register("New York", NY_FIELDS)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        driver = resp.get_json()["driver"]
        self.assertIsNone(driver["city"])
        self.assertEqual(set(driver["docs"]), set(app_module.DOC_TYPES))

    def test_me_endpoint_and_owner_list_carry_city(self):
        resp = self.register("Texas", DALLAS_FIELDS, city="Dallas")
        token = resp.get_json()["token"]
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": token})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()["driver"]["city"], "Dallas")
        login = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(login.status_code, 200)
        owners = self.client.get("/api/owner/drivers")
        self.assertEqual(owners.status_code, 200)
        drivers = owners.get_json()
        self.assertEqual(len(drivers), 1)
        self.assertEqual(drivers[0]["city"], "Dallas")
        self.assertEqual(drivers[0]["state"], "Texas")

    # -- client wiring ----------------------------------------------------------
    def test_driver_form_has_city_picker(self):
        html = read("static/driver.html")
        self.assertIn('id="reg-city"', html)
        self.assertIn('id="city-list"', html)
        self.assertIn("Other city", html)
        # City field sits right after the state field, before the car.
        self.assertLess(html.index('id="reg-state"'), html.index('id="reg-city"'))
        self.assertLess(html.index('id="reg-city"'), html.index('id="reg-car-model"'))
        self.assertIn("All items are required", html)

    def test_driver_js_wires_city_picker_and_effective_list(self):
        js = read("static/js/driver.js")
        self.assertIn("initCityDropdown", js)
        self.assertIn("citiesForState", js)
        self.assertIn("effectiveRequirement", js)
        self.assertIn("city_requirements", js)
        self.assertIn("Other city", js)
        self.assertIn("reg-city", js)
        # Names pinned by the state-selector tests stay.
        self.assertIn("renderDocsForState", js)
        self.assertIn("requiredFileFields", js)
        # Dallas labels + fields, and the city sent with registration.
        self.assertIn("Dallas Driver Permit", js)
        self.assertIn("City Limo Permit (Dallas / Fort Worth)", js)
        self.assertIn('fd.append("city", cityName)', js)
        # No document count anywhere ("Quantity nahi").
        self.assertNotIn("required.length", js)
        # No background check, no age/experience gate, no rating.
        self.assertNotIn("background check", js.lower())
        self.assertNotIn("background_check", js.lower())

    def test_owner_dashboard_shows_city_and_dallas_labels(self):
        js = read("static/js/owner.js")
        self.assertIn("Dallas Driver Permit", js)
        self.assertIn("City Limo Permit (Dallas / Fort Worth)", js)
        self.assertIn("Commercial Insurance Certificate", js)
        self.assertIn("City: ", js)

    def test_driver_css_styles_city_list(self):
        css = read("static/css/driver.css")
        self.assertIn(".city-list", css)


if __name__ == "__main__":
    unittest.main()
