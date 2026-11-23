"""Language switcher (owner order, voice call 2026-11-22 ~21:11 EST,
"Yes Spanish, French, Arabic jo bhi tum languages daal sakte ho
build kar sakte kar do", refined ~21:11 EST: the picker must open as
a SCROLL-DOWN DROPDOWN with ALL languages; refined ~21:12 EST: the
dropdown must be TYPEABLE / SEARCHABLE — type to filter the list).

Pinned here:
- The translation dictionary in static/js/i18n.js is complete: every
  key has all 8 languages (en, es, fr, ar, pt, ur, hi, bn), no empty
  values, no duplicate keys.
- Every data-i18n / data-i18n-ph / data-i18n-aria key used in
  index.html, customer-app.html and your-ride-history.html exists in
  the dictionary; every T("key", ...) call in customer.js,
  customer-app.js and ride-history.js does too.
- i18n.js is served and loaded by all three pages; each page carries
  its picker slot (menu / app header / history header); the old plain
  "English (US)" menu item is gone.
- The choice persists under localStorage key "noel-language".
- Arabic is right-to-left: its LANGS entry is dir "rtl", applyLanguage
  sets document dir, and both customer CSS files carry html[dir="rtl"]
  rules. The picker dropdown + search styles exist in both CSS files.
- Fares are untouched (JFK -> Times Square Business driver $102.46).

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="noel-lang-switcher-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "lang-switcher-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
from blacklane_pricing import compute_blacklane_one_way  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
I18N_JS = (REPO_DIR / "static" / "js" / "i18n.js").read_text()
INDEX = (REPO_DIR / "static" / "index.html").read_text()
APP_HTML = (REPO_DIR / "static" / "customer-app.html").read_text()
HISTORY_HTML = (REPO_DIR / "static" / "your-ride-history.html").read_text()
CUSTOMER_JS = (REPO_DIR / "static" / "js" / "customer.js").read_text()
CUSTOMER_APP_JS = (REPO_DIR / "static" / "js" / "customer-app.js").read_text()
HISTORY_JS = (REPO_DIR / "static" / "js" / "ride-history.js").read_text()
CUSTOMER_CSS = (REPO_DIR / "static" / "css" / "customer.css").read_text()
APP_CSS = (REPO_DIR / "static" / "css" / "customer-app.css").read_text()

LANGS = {"en", "es", "fr", "ar", "pt", "ur", "hi", "bn"}


def _dictionary():
    """Parse NOEL_I18N["key"] = { "en": "...", ... }; blocks."""
    blocks = re.findall(
        r'NOEL_I18N\["([^"]+)"\] = \{(.*?)\};', I18N_JS, re.S
    )
    out = {}
    for key, body in blocks:
        assert key not in out, f"duplicate dictionary key {key!r}"
        langs = {}
        # Pairs may share a line ("en": "...", "es": "...", ...) so
        # scan the whole block, not line by line.
        for code, value in re.findall(
            r'"([a-z]{2})":\s*"((?:[^"\\]|\\.)*)"', body
        ):
            assert code not in langs, (
                f"duplicate language {code!r} in key {key!r}"
            )
            langs[code] = value
        out[key] = langs
    return out


DICT = _dictionary()


class TestDictionaryComplete(unittest.TestCase):
    def test_every_key_has_all_eight_languages(self):
        self.assertGreater(len(DICT), 300, "dictionary looks truncated")
        for key, langs in DICT.items():
            with self.subTest(key=key):
                self.assertEqual(set(langs), LANGS, key)
                for code, value in langs.items():
                    self.assertTrue(value.strip(), f"{key}[{code}] is empty")

    def test_langs_list_has_all_eight_with_arabic_rtl(self):
        m = re.search(
            r'\{ code: "ar", label: "Arabic", native: "العربية", dir: "rtl" \}',
            I18N_JS,
        )
        self.assertIsNotNone(m, "Arabic LANGS entry must be dir rtl")
        for code in sorted(LANGS):
            self.assertIn(f'code: "{code}"', I18N_JS, code)

    def test_no_placeholder_english_in_translations(self):
        # A translated value must not be the bare key name or empty.
        for key, langs in DICT.items():
            for code, value in langs.items():
                if code == "en":
                    continue
                self.assertNotEqual(value.strip(), key, f"{key}[{code}]")


class TestHtmlKeysResolve(unittest.TestCase):
    def test_every_data_i18n_key_exists(self):
        used = set()
        for html in (INDEX, APP_HTML, HISTORY_HTML):
            used |= set(re.findall(r'data-i18n="([^"]+)"', html))
            used |= set(re.findall(r'data-i18n-ph="([^"]+)"', html))
            used |= set(re.findall(r'data-i18n-aria="([^"]+)"', html))
        missing = sorted(k for k in used if k not in DICT)
        self.assertEqual(missing, [], f"HTML keys missing from dictionary: {missing}")

    def test_every_t_call_key_exists(self):
        for name, src in (("customer.js", CUSTOMER_JS),
                          ("customer-app.js", CUSTOMER_APP_JS),
                          ("ride-history.js", HISTORY_JS)):
            used = set(re.findall(r'\bT\("([^"]+)",', src))
            missing = sorted(k for k in used if k not in DICT)
            self.assertEqual(missing, [], f"{name} T() keys missing: {missing}")

    def test_t_helper_present_in_all_three_js_files(self):
        for name, src in (("customer.js", CUSTOMER_JS),
                          ("customer-app.js", CUSTOMER_APP_JS),
                          ("ride-history.js", HISTORY_JS)):
            self.assertIn("function T(key, fallback, vars)", src, name)

    def test_class_names_stay_english(self):
        # Product names are never translated: the class labels stay
        # English in the JS, and no dictionary key renames them.
        self.assertIn(
            'var CLASS_LABELS = { sedan: "Business Class", '
            'suv: "Business SUV", first: "First Class" }',
            CUSTOMER_JS,
        )
        self.assertNotIn("class.business_name", DICT)


class TestPickerServed(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_i18n_js_served(self):
        resp = self.client.get("/static/js/i18n.js")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("noel-language", body)
        self.assertIn("buildPicker", body)
        self.assertIn("NoelI18n", body)

    def test_website_has_picker_slot_and_script(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("/static/js/i18n.js", body)
        self.assertIn('id="menu-lang-slot"', body)
        self.assertNotIn(
            '<span class="menu-link menu-plain">English (US)</span>', body
        )

    def test_customer_app_has_picker_slot_and_script(self):
        resp = self.client.get("/app")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("/static/js/i18n.js", body)
        self.assertIn('id="app-lang-slot"', body)

    def test_history_page_has_picker_slot_and_script(self):
        resp = self.client.get("/your-ride-history")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("/static/js/i18n.js", body)
        self.assertIn('id="history-lang-slot"', body)
        self.assertIn("/static/js/ride-history.js", body)


class TestPersistenceAndRtl(unittest.TestCase):
    def test_persistence_key(self):
        self.assertIn('STORAGE_KEY = "noel-language"', I18N_JS)
        self.assertIn("localStorage", I18N_JS)

    def test_apply_language_sets_dir(self):
        self.assertIn('document.documentElement.setAttribute("dir", entry.dir)',
                      I18N_JS)
        self.assertIn('document.documentElement.setAttribute("lang", entry.code)',
                      I18N_JS)

    def test_dropdown_is_scroll_down_with_search(self):
        # The picker builds a dropdown under the button (not a modal or
        # a separate page) with a search input that filters live.
        self.assertIn("noel-lang-dropdown", I18N_JS)
        self.assertIn("noel-lang-search", I18N_JS)
        self.assertIn('search.addEventListener("input"', I18N_JS)
        self.assertIn("renderList(search.value)", I18N_JS)

    def test_picker_styles_in_both_css_files(self):
        for name, css in (("customer.css", CUSTOMER_CSS),
                          ("customer-app.css", APP_CSS)):
            for cls in (".noel-lang-picker", ".noel-lang-btn",
                        ".noel-lang-dropdown", ".noel-lang-search",
                        ".noel-lang-list", ".noel-lang-item"):
                self.assertIn(cls, css, f"{cls} missing in {name}")

    def test_rtl_rules_in_both_css_files(self):
        for name, css in (("customer.css", CUSTOMER_CSS),
                          ("customer-app.css", APP_CSS)):
            self.assertIn('html[dir="rtl"]', css, name)

    def test_language_change_event_fired_and_handled(self):
        self.assertIn("noel-language-changed", I18N_JS)
        self.assertIn("noel-language-changed", CUSTOMER_JS)
        self.assertIn("noel-language-changed", CUSTOMER_APP_JS)
        self.assertIn("paintClassDetails()", CUSTOMER_JS)
        self.assertIn("paintClassBreakdown()", CUSTOMER_JS)


class TestFaresUnchanged(unittest.TestCase):
    def test_jfk_to_times_square_driver_pay_exact(self):
        r = compute_blacklane_one_way(D("17.9"), "sedan",
                                      "JFK Airport", "Times Square",
                                      toll=D("7.46"))
        self.assertEqual(r["driver_earnings"], D("102.46"))


if __name__ == "__main__":
    unittest.main()
