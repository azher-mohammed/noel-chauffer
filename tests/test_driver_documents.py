"""Tests for the single "DMV driving license" document item.

Owner decision 2026-11-16 (emphatic): the two near-identical items
("Driver's License" + "DMV driving licence") merge into ONE item
labeled exactly "DMV driving license", FIRST at the top of the
document list everywhere. US spelling "license", "driving" not
"driver". NYS DMV Inspection stays a separate item.

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

EXPECTED_DOC_TYPES = ["dmv_license", "profile_picture", "tlc_license",
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

    # -- labels -------------------------------------------------------------
    def test_label_exactly_once_in_form_and_first(self):
        html = read("static/driver.html")
        self.assertEqual(html.count("DMV driving license"), 2,
                         "label + hint must each carry the exact phrase once")
        self.assertIn("Photo of your DMV driving license, straight and fully visible.", html)
        # First document item: before Profile Picture and every other doc.
        first_doc = html.index("DMV driving license")
        for other in ("Profile Picture", "TLC License", "FH-1 Insurance Card",
                      "Commercial Vehicle Registration", "NYS DMV Inspection",
                      "TLC-for-hire Vehicle Permit"):
            self.assertLess(first_doc, html.index(other), other)
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
        self.assertIn('"doc_dmv_license"', fields.split(",")[0])
        self.assertNotIn("doc_drivers_license", fields)
        owner_js = read("static/js/owner.js")
        doc_types = owner_js[owner_js.index("var DOC_TYPES"):owner_js.index("];", owner_js.index("var DOC_TYPES"))]
        self.assertIn('"dmv_license"', doc_types.split("{")[1])
        self.assertIn('label: "DMV driving license"', doc_types)

    # -- API behaviour -----------------------------------------------------------
    def test_docs_status_has_seven_types_dmv_first(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        docs = resp.get_json()["driver"]["docs"]
        self.assertEqual(set(docs), set(EXPECTED_DOC_TYPES))
        # JSON keys arrive alphabetically; dmv_license sorts first, and
        # DOC_TYPES order in code (asserted separately) drives the UI.
        self.assertEqual(list(docs)[0], "dmv_license")
        self.assertEqual(docs["dmv_license"], "missing")

    def test_dmv_license_upload_completes_the_item(self):
        resp = self.register(files={
            "doc_dmv_license": (io.BytesIO(b"fake png"), "license.png")})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        docs = resp.get_json()["driver"]["docs"]
        self.assertEqual(docs["dmv_license"], "completed")

    def test_old_field_name_is_ignored(self):
        # The removed duplicate field no longer maps to any doc type.
        resp = self.register(files={
            "doc_drivers_license": (io.BytesIO(b"fake png"), "license.png")})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        docs = resp.get_json()["driver"]["docs"]
        self.assertEqual(docs["dmv_license"], "missing")
        self.assertNotIn("drivers_license", docs)


if __name__ == "__main__":
    unittest.main()
