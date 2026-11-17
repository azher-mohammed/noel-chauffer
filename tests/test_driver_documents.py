"""Tests for the driver document list order and the single
"DMV driving license" document item.

Owner decision 2026-11-16 (emphatic): the two near-identical items
("Driver's License" + "DMV driving licence") merge into ONE item
labeled exactly "DMV driving license". US spelling "license",
"driving" not "driver". NYS DMV Inspection stays a separate item.

Owner decision 2026-11-16 (later the same day): Profile Picture is
FIRST at the top of the document list everywhere, with the DMV
driving license second. Registration previews have a remove option,
and the profile picture preview shows passport-style (a cropped face
frame, not the whole photo).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-docmerge-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "docmerge.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "docmerge-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPECTED_DOC_TYPES = ["profile_picture", "dmv_license", "tlc_license",
                      "fh1_insurance", "registration", "inspection",
                      "vehicle_permit"]

# Strings that must not appear anywhere user-visible (or in the doc
# plumbing at all, except inside this test file itself).
FORBIDDEN = ["Driver's License", "DMV driver license", "licence",
             "doc_drivers_license", "drivers_license",
             "DMV driving licence", "driver's license"]


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class DmvDrivingLicenseCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    def register(self, files=None, **overrides):
        self._seq += 1
        data = {
            "name": "Doc Driver", "phone": f"+1555004{self._seq:04d}",
            "email": "doc@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": f"D{self._seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
        }
        data.update(overrides)
        if files:
            data.update(files)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    def all_files(self):
        # All 7 compulsory uploads (owner decision 2026-11-17).
        return {
            "profile_photo": (io.BytesIO(b"fake jpg"), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(b"fake png"), "license.png"),
            "doc_tlc_license": (io.BytesIO(b"fake png"), "tlc.png"),
            "doc_fh1": (io.BytesIO(b"fake png"), "fh1.png"),
            "doc_registration": (io.BytesIO(b"fake png"), "reg.png"),
            "doc_inspection": (io.BytesIO(b"fake png"), "insp.png"),
            "doc_vehicle_permit": (io.BytesIO(b"fake png"), "permit.png"),
        }

    # -- labels -------------------------------------------------------------
    def test_profile_picture_first_dmv_second(self):
        html = read("static/driver.html")
        self.assertEqual(html.count("DMV driving license"), 2,
                         "label + hint must each carry the exact phrase once")
        self.assertIn("Photo of your DMV driving license, straight and fully visible.", html)
        # Profile Picture first, DMV driving license second, before all others.
        first_doc = html.index("Profile Picture")
        second_doc = html.index("DMV driving license")
        self.assertLess(first_doc, second_doc)
        for other in ("TLC License", "FH-1 Insurance Card",
                      "Commercial Vehicle Registration", "NYS DMV Inspection",
                      "TLC-for-hire Vehicle Permit"):
            self.assertLess(second_doc, html.index(other), other)
        self.assertEqual(html.count("doc-name"), 7, "exactly 7 document items")

    def test_no_forbidden_strings_in_user_visible_files(self):
        for rel in ("static/driver.html", "static/js/driver.js",
                    "static/js/owner.js", "static/NOTES.md", "app.py"):
            text = read(rel)
            for bad in FORBIDDEN:
                self.assertNotIn(bad, text, "%s in %s" % (bad, rel))

    def test_nys_dmv_inspection_still_present(self):
        for rel in ("static/driver.html", "static/js/driver.js", "static/js/owner.js"):
            self.assertIn("NYS DMV Inspection", read(rel), rel)

    # -- ordering in code ------------------------------------------------------
    def test_doc_order_in_code(self):
        self.assertEqual(app_module.DOC_TYPES, EXPECTED_DOC_TYPES)
        self.assertNotIn("doc_drivers_license", app_module.DOC_FIELD_MAP)
        self.assertEqual(app_module.DOC_FIELD_MAP["doc_dmv_license"], "dmv_license")
        driver_js = read("static/js/driver.js")
        fields = driver_js[driver_js.index("var FILE_FIELDS"):driver_js.index("];", driver_js.index("var FILE_FIELDS"))]
        self.assertIn('"profile_photo"', fields.split(",")[0])
        self.assertIn('"doc_dmv_license"', fields.split(",")[1])
        self.assertNotIn("doc_drivers_license", fields)
        owner_js = read("static/js/owner.js")
        doc_types = owner_js[owner_js.index("var DOC_TYPES"):owner_js.index("];", owner_js.index("var DOC_TYPES"))]
        self.assertIn('"profile_picture"', doc_types.split("{")[1])
        self.assertIn('"dmv_license"', doc_types.split("{")[2])
        self.assertIn('label: "DMV driving license"', doc_types)

    # -- API behaviour -----------------------------------------------------------
    def test_docs_status_has_seven_types(self):
        resp = self.register(files=self.all_files())
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        docs = resp.get_json()["driver"]["docs"]
        self.assertEqual(set(docs), set(EXPECTED_DOC_TYPES))
        # JSON keys arrive alphabetically; dmv_license sorts first, and
        # DOC_TYPES order in code (asserted separately) drives the UI.
        self.assertEqual(list(docs)[0], "dmv_license")
        self.assertTrue(all(v == "completed" for v in docs.values()),
                        "all 7 compulsory uploads present -> all completed")

    def test_dmv_license_upload_completes_the_item(self):
        resp = self.register(files=self.all_files())
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        docs = resp.get_json()["driver"]["docs"]
        self.assertEqual(docs["dmv_license"], "completed")

    def test_old_field_name_is_ignored(self):
        # The removed duplicate field no longer maps to any doc type.
        files = self.all_files()
        files["doc_drivers_license"] = (io.BytesIO(b"fake png"), "license.png")
        resp = self.register(files=files)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        docs = resp.get_json()["driver"]["docs"]
        self.assertEqual(docs["dmv_license"], "completed")
        self.assertNotIn("drivers_license", docs)

    def test_preview_has_remove_option_and_passport_frame(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("Remove photo", driver_js)
        self.assertIn("Remove file", driver_js)
        # The remove control clears the file input so nothing uploads.
        self.assertIn('input.value = ""', driver_js)
        self.assertIn("passport-preview", driver_js)
        css = read("static/css/driver.css")
        self.assertIn("passport-preview", css)
        self.assertIn("object-fit: cover", css)


if __name__ == "__main__":
    unittest.main()
