"""Tests for the per-item red error highlight on driver document uploads.

Owner decision 2026-11-18 (voice call, his words): "driver ka koi
cheez fail ho rahi upload kare baad to uska error pe maloom ho jana
... wo side wala red mein kar dena" — when a document upload fails,
the driver must be able to tell WHICH item failed, so the failing
item itself turns red and shows the message inside it. Until now
every registration error went into one shared box, which never said
which document failed.

Scope is purely additive visual feedback on the registration form:
- the failing .doc-item gets a red border + light red background +
  its name in red, with the error message inside the item;
- the shared error box keeps working exactly as before, with the
  same wording;
- no validation rule, document list, label, hint, or other flow
  changes; nothing is mirrored to the native apps.

The label -> field mapping reuses the form's own DOC_LABELS (the
same labels the server's "Missing document" message uses), and the
upload-check mapping reuses the multipart field names the server
error strings start with. Both parities are pinned here.

Run:  python -m unittest discover -s tests -v
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-docerr-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "t.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "docerr-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_FIELDS = [
    "profile_photo", "doc_dmv_license", "doc_tlc_license", "doc_fh1",
    "doc_registration", "doc_inspection", "doc_vehicle_permit",
]

NY_FILES = {
    "doc_dmv_license": "license.png",
    "doc_tlc_license": "tlc.png",
    "doc_fh1": "fh1.png",
    "doc_registration": "reg.png",
    "doc_inspection": "insp.png",
    "doc_vehicle_permit": "permit.png",
}

MISSING_SUFFIX = (". Please upload all required documents to complete "
                  "registration.")


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def _extract_braced(js, start_marker):
    """Source text of the var/function starting at start_marker,
    through its matching close brace (strings in these blocks hold
    no braces)."""
    i = js.index(start_marker)
    j = js.index("{", i)
    depth = 0
    k = j
    while True:
        ch = js[k]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return js[i:k + 1]
        k += 1


class DocItemErrorHighlightCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0

    # -- red state: CSS ------------------------------------------------------
    def test_red_state_css_rules(self):
        css = read("static/css/driver.css")
        m = re.search(r"\.doc-item\.has-error \{([^}]*)\}", css)
        self.assertIsNotNone(m, "has-error item rule missing")
        self.assertIn("border-color: var(--bad)", m.group(1))
        self.assertIn("background: var(--bad-soft)", m.group(1))
        m = re.search(r"\.doc-item\.has-error \.doc-name \{([^}]*)\}", css)
        self.assertIsNotNone(m, "has-error name rule missing")
        self.assertIn("color: var(--bad)", m.group(1))
        m = re.search(r"\.doc-error \{([^}]*)\}", css)
        self.assertIsNotNone(m, "doc-error rule missing")
        self.assertIn("display: none", m.group(1))
        self.assertIn("color: var(--bad)", m.group(1))
        m = re.search(r"\.doc-item\.has-error \.doc-error \{([^}]*)\}", css)
        self.assertIsNotNone(m, "has-error doc-error rule missing")
        self.assertIn("display: block", m.group(1))

    # -- red state: markup ---------------------------------------------------
    def test_static_items_have_error_elements(self):
        html = read("static/driver.html")
        self.assertEqual(html.count('class="doc-error"'), len(STATIC_FIELDS))
        for field in STATIC_FIELDS:
            with self.subTest(field=field):
                self.assertIn('id="doc-error-%s"' % field, html)
                # The message element sits inside its own item, after
                # the preview element.
                item = html[html.index('id="doc-item-%s"' % field):]
                item = item[:item.index("</div>\n      </div>")]
                self.assertIn('id="preview-%s"' % field, item)
                self.assertIn('id="doc-error-%s"' % field, item)
                self.assertLess(item.index('id="preview-%s"' % field),
                                item.index('id="doc-error-%s"' % field))

    def test_dynamic_items_get_error_element(self):
        js = read("static/js/driver.js")
        builder = js[js.index("function ensureDocItem"):]
        builder = builder[:builder.index("function renderDocsForState")]
        self.assertIn('errorEl.className = "doc-error"', builder)
        self.assertIn('errorEl.id = "doc-error-" + field', builder)
        self.assertIn("item.appendChild(errorEl)", builder)

    # -- red state: helpers + wiring -----------------------------------------
    def test_mark_and_clear_helpers(self):
        js = read("static/js/driver.js")
        self.assertIn("function markDocItemError(field, message)", js)
        self.assertIn('item.classList.add("has-error")', js)
        self.assertIn("function clearDocItemError(field)", js)
        self.assertIn('item.classList.remove("has-error")', js)
        # Clearing walks the DOM, not the static-only FILE_FIELDS
        # list, so city-specific items clear too.
        self.assertIn('document.querySelectorAll(".doc-item.has-error")', js)

    def test_fresh_submit_clears_all_item_errors_first(self):
        js = read("static/js/driver.js")
        submit = js[js.index('("register-form").addEventListener("submit"'):]
        head = submit[:600]
        self.assertIn('err.textContent = "";', head)
        self.assertIn("clearAllDocItemErrors();", head)
        self.assertLess(head.index('err.textContent = "";'),
                        head.index("clearAllDocItemErrors();"))

    def test_missing_docs_marked_per_item(self):
        js = read("static/js/driver.js")
        block = js[js.index("var missingDocs = []"):]
        block = block[:block.index("checkProfilePhoto(")]
        self.assertIn("missingFields.push(field)", block)
        self.assertIn("markDocItemError(field, missingDocMessage(field))",
                      block)
        # The shared box keeps the exact wording it always had.
        self.assertIn('"Missing document: " + missingDocs.join(", ") +',
                      block)
        self.assertIn(MISSING_SUFFIX.strip(".") + '."', block)

    def test_profile_photo_failure_marks_its_item_on_submit(self):
        js = read("static/js/driver.js")
        self.assertIn('markDocItemError("profile_photo", photoError)', js)

    def test_profile_photo_checked_on_pick_and_cleared_on_new_pick(self):
        js = read("static/js/driver.js")
        preview = js[js.index("function bindFilePreview"):]
        preview = preview[:preview.index("FILE_FIELDS.forEach")]
        # A new pick clears the item's red state immediately.
        self.assertIn("clearDocItemError(field);", preview)
        # The passport-style check runs on pick for the profile
        # photo, with the exact client wording, and only marks when
        # the checked file is still the chosen one.
        self.assertIn('if (field === "profile_photo") {', preview)
        self.assertIn("checkProfilePhoto(file, function (photoError) {",
                      preview)
        self.assertIn("input.files[0] === file", preview)
        self.assertIn("markDocItemError(field, photoError)", preview)
        # Removing a picked file clears the item's red state too.
        self.assertIn("clearDocItemError(field);",
                      preview[preview.index("preview-remove"):])

    def test_server_error_mapping_wired_once_in_registration(self):
        js = read("static/js/driver.js")
        self.assertIn("function markDocErrorsFromServer(message, requiredFields)",
                      js)
        self.assertIn("markDocErrorsFromServer(serverError, requiredFields)",
                      js)
        self.assertEqual(js.count("markDocErrorsFromServer"), 2,
                         "mapper must be defined once and called once")
        # The shared-box fallback wording is unchanged.
        self.assertIn("Registration could not be completed. Please check "
                      "your details and try again.", js)
        self.assertIn("Could not reach the service. Please check your "
                      "connection and try again.", js)

    def test_mapper_branches_cover_all_document_errors(self):
        js = read("static/js/driver.js")
        mapper = js[js.index("function markDocErrorsFromServer"):]
        mapper = mapper[:mapper.index("$(\"register-form\")")]
        # Missing documents: label list parsed, per-item wording.
        self.assertIn('message.indexOf(missingPrefix) === 0', mapper)
        self.assertIn("parseMissingDocFields(", mapper)
        # Profile photo: every server wording starts this way.
        self.assertIn('message.indexOf("Profile photo") === 0', mapper)
        # Upload checks: the message starts with the field name.
        self.assertIn('message.indexOf(fields[i] + " ") === 0', mapper)
        # The mapper never mentions non-document errors: plate,
        # password, and network errors map to nothing.
        self.assertNotIn("plate", mapper)
        self.assertNotIn("Password", mapper)
        self.assertNotIn("Could not reach", mapper)

    def test_label_parser_uses_longest_first_matching(self):
        js = read("static/js/driver.js")
        parser = js[js.index("function parseMissingDocFields"):]
        parser = parser[:parser.index("function markDocErrorsFromServer")]
        # Longest-first: labels containing ", " must not split.
        self.assertIn("b.label.length - a.label.length", parser)
        # A shared label resolves to the current required list.
        self.assertIn("preferred", parser)
        # Unknown text stops the parse; nothing is invented.
        self.assertIn("if (!matched) break;", parser)

    # -- mapping parity: client labels == server labels ----------------------
    def test_client_labels_match_server_labels(self):
        js = read("static/js/driver.js")
        m = re.search(r"var DOC_LABELS = \{(.*?)\n  \};", js, re.S)
        js_labels = dict(re.findall(r"(\w+): \"([^\"]+)\"", m.group(1)))
        m = re.search(r"var FIELD_FOR_DOC_TYPE = \{(.*?)\n  \};", js, re.S)
        field_for = dict(re.findall(r"(\w+): \"(\w+)\"", m.group(1)))
        server = app_module.ALL_DOC_LABELS
        self.assertEqual(set(field_for), set(server))
        for doc_type, label in server.items():
            field = field_for[doc_type]
            self.assertEqual(js_labels[field], label,
                             "label mismatch for %s" % doc_type)

    # -- behavioural: the shipped JS mapping, run under node -----------------
    @unittest.skipUnless(shutil.which("node"), "node required")
    def test_server_error_mapping_behaviour(self):
        js = read("static/js/driver.js")
        parts = [
            _extract_braced(js, "var DOC_LABELS = {") + ";",
            _extract_braced(js, "function parseMissingDocFields"),
            _extract_braced(js, "function missingDocMessage"),
            _extract_braced(js, "function markDocErrorsFromServer"),
        ]
        cases = [
            # Two missing NY items: each marked, single-label wording.
            {"message": "Missing document: DMV driving license, TLC License"
                        + MISSING_SUFFIX,
             "required": STATIC_FIELDS,
             "want": ["doc_dmv_license", "doc_tlc_license"]},
            # A label containing ", " must not split.
            {"message": "Missing document: Charter-Party Carrier (TCP) "
                        "Certificate/Permit (Class A, B or P), Driver "
                        "Statement of Application (Form PL739-A)"
                        + MISSING_SUFFIX,
             "required": ["profile_photo", "doc_ca_tcp_permit",
                          "doc_ca_driver_statement", "doc_insurance_card"],
             "want": ["doc_ca_tcp_permit", "doc_ca_driver_statement"]},
            {"message": "Missing document: Taxicab Driver License "
                        "(Springfield, IL)" + MISSING_SUFFIX,
             "required": ["profile_photo",
                          "doc_springfield_il_taxi_driver_license"],
             "want": ["doc_springfield_il_taxi_driver_license"]},
            # Substring trap: "Vehicle Registration" must not match
            # "Commercial Vehicle Registration", and vice versa.
            {"message": "Missing document: Commercial Vehicle Registration"
                        + MISSING_SUFFIX,
             "required": STATIC_FIELDS,
             "want": ["doc_registration"]},
            {"message": "Missing document: Vehicle Registration"
                        + MISSING_SUFFIX,
             "required": ["profile_photo", "doc_vehicle_registration",
                          "doc_insurance_card"],
             "want": ["doc_vehicle_registration"]},
            # A label shared across states resolves to the required one.
            {"message": "Missing document: Vehicle Inspection"
                        + MISSING_SUFFIX,
             "required": ["profile_photo", "doc_pa_inspection",
                          "doc_pa_form_e"],
             "want": ["doc_pa_inspection"]},
            {"message": "Missing document: Vehicle Inspection"
                        + MISSING_SUFFIX,
             "required": ["profile_photo", "doc_co_inspection",
                          "doc_co_form_e"],
             "want": ["doc_co_inspection"]},
            # Unknown text marks nothing.
            {"message": "Missing document: Mystery Paper" + MISSING_SUFFIX,
             "required": STATIC_FIELDS,
             "want": []},
            # Profile photo: all three server wordings map.
            {"message": "Profile photo must be a portrait photo (taller "
                        "than it is wide) — please upload a passport-style "
                        "photo of your face.",
             "required": STATIC_FIELDS, "want": ["profile_photo"]},
            {"message": "Profile photo is too small — please upload a "
                        "larger, clear photo of your face (at least 300 "
                        "pixels wide).",
             "required": STATIC_FIELDS, "want": ["profile_photo"]},
            {"message": "Profile photo could not be read — please upload "
                        "a clear photo of your face.",
             "required": STATIC_FIELDS, "want": ["profile_photo"]},
            # Upload checks: the message starts with the field name.
            {"message": "doc_fh1 must be one of: .jpeg, .jpg, .pdf, .png.",
             "required": STATIC_FIELDS, "want": ["doc_fh1"]},
            {"message": "doc_dmv_license exceeds the 5MB limit.",
             "required": STATIC_FIELDS, "want": ["doc_dmv_license"]},
            {"message": "doc_registration is empty.",
             "required": STATIC_FIELDS, "want": ["doc_registration"]},
            # City-specific fields map too, not just the static list.
            {"message": "doc_buffalo_taxi_driver_license must be one of: "
                        ".jpeg, .jpg, .png, .webp.",
             "required": ["profile_photo", "doc_buffalo_taxi_driver_license"],
             "want": ["doc_buffalo_taxi_driver_license"]},
            # Non-document errors mark nothing.
            {"message": "Please enter a valid plate number (letters and "
                        "numbers only).",
             "required": STATIC_FIELDS, "want": []},
            {"message": "Password must be at least 6 characters.",
             "required": STATIC_FIELDS, "want": []},
            {"message": "Please choose your state from the list.",
             "required": STATIC_FIELDS, "want": []},
            {"message": "Registration could not be completed. Please "
                        "check your details and try again.",
             "required": STATIC_FIELDS, "want": []},
            {"message": "", "required": STATIC_FIELDS, "want": []},
        ]
        harness = (
            "var marked = [];\n"
            "function markDocItemError(field, message) {\n"
            "  marked.push([field, message]);\n}\n"
            + "\n".join(parts) + "\n"
            "var CASES = " + json.dumps(cases) + ";\n"
            "var out = [];\n"
            "CASES.forEach(function (c) {\n"
            "  marked = [];\n"
            "  markDocErrorsFromServer(c.message, c.required);\n"
            "  out.push(marked);\n});\n"
            "console.log(JSON.stringify(out));\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False) as fh:
            fh.write(harness)
            tmp = fh.name
        try:
            proc = subprocess.run(["node", tmp], capture_output=True,
                                  text=True, timeout=30)
        finally:
            os.unlink(tmp)
        self.assertEqual(proc.returncode, 0, proc.stderr[:500])
        results = json.loads(proc.stdout)
        self.assertEqual(len(results), len(cases))
        for case, marked in zip(cases, results):
            with self.subTest(message=case["message"][:60]):
                fields = [f for f, _m in marked]
                self.assertEqual(fields, case["want"])
                for field, message in marked:
                    if case["message"].startswith("Missing document: "):
                        # Per-item wording: the same sentence, one label.
                        self.assertTrue(
                            message.startswith("Missing document: "),
                            message)
                        self.assertTrue(message.endswith(MISSING_SUFFIX),
                                        message)
                        self.assertEqual(message.count("Missing document: "),
                                         1)
                    else:
                        # Single-item errors show the exact message.
                        self.assertEqual(message, case["message"])

    # -- server strings the mapping parses -----------------------------------
    def register(self, files, state="New York", **overrides):
        self._seq += 1
        data = {
            "name": "Doc Err Driver", "phone": "+1555007%04d" % self._seq,
            "email": "docerr@test.com",
            "car_model": "Cadillac Escalade", "car_year": "2023",
            "car_colour": "Black", "plate": "DE%05d" % self._seq,
            "state": state, "bank_account_number": "123456789",
            "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_tlc_license": "2030-01-01",
            "expiry_fh1_insurance": "2030-01-01",
            "expiry_registration": "2030-01-01",
            "expiry_inspection": "2030-01-01",
            "expiry_vehicle_permit": "2030-01-01",
            "expiry_vehicle_registration": "2030-01-01",
            "expiry_insurance_card": "2030-01-01",
        }
        data.update(overrides)
        data.update(files)
        return self.client.post("/api/drivers/register", data=data,
                                content_type="multipart/form-data")

    def all_ny_files(self, **replace):
        files = {"profile_photo": replace.get(
            "profile_photo",
            (io.BytesIO(photo_factory.VALID_PROFILE_PHOTO), "photo.jpg"))}
        for field, fname in NY_FILES.items():
            files[field] = replace.get(field, (io.BytesIO(photo_factory.doc_photo()), fname))
        return files

    def test_missing_message_format_with_comma_label(self):
        # California's TCP label contains ", " — the server message
        # must carry it intact so the client parser can match it.
        resp = self.register({}, state="California")
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        error = resp.get_json()["error"]
        self.assertTrue(error.startswith("Missing document: "), error)
        self.assertTrue(error.endswith(MISSING_SUFFIX), error)
        self.assertIn("Charter-Party Carrier (TCP) Certificate/Permit "
                      "(Class A, B or P)", error)

    def test_bad_extension_error_starts_with_field_name(self):
        files = self.all_ny_files(
            doc_dmv_license=(io.BytesIO(b"%PDF-1.4 fake"), "license.pdf"))
        resp = self.register(files)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        error = resp.get_json()["error"]
        self.assertTrue(error.startswith("doc_dmv_license must be one of: "),
                        error)

    def test_oversize_error_starts_with_field_name(self):
        big = b"x" * (5 * 1024 * 1024 + 1)
        files = self.all_ny_files(
            doc_registration=(io.BytesIO(big), "reg.png"))
        resp = self.register(files)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["error"],
                         "doc_registration exceeds the 5MB limit.")

    def test_empty_upload_error_starts_with_field_name(self):
        files = self.all_ny_files(
            doc_registration=(io.BytesIO(b""), "reg.png"))
        resp = self.register(files)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["error"], "doc_registration is empty.")

    def test_profile_photo_error_starts_with_profile_photo(self):
        files = self.all_ny_files(
            profile_photo=(io.BytesIO(photo_factory.jpeg(500, 400)),
                           "photo.jpg"))
        resp = self.register(files)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertTrue(resp.get_json()["error"].startswith("Profile photo"),
                        resp.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
