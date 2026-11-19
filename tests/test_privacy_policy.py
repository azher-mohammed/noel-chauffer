"""Privacy policy page (owner decision 2026-11-19, voice call).

App Store Connect requires a privacy policy URL at submission, and
https://noelchauffer.com/privacy was 404. GET /privacy serves the
policy page in the site's black-and-gold style, and the homepage
footer links to it.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-privacy-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "privacy-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
INDEX = REPO_DIR / "static" / "index.html"


class PrivacyPolicyPageTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_privacy_returns_200(self):
        res = self.client.get("/privacy")
        self.assertEqual(res.status_code, 200)

    def test_privacy_has_key_sections(self):
        res = self.client.get("/privacy")
        html = res.get_data(as_text=True)
        self.assertIn("Privacy Policy", html)
        self.assertIn("19 November 2026", html)
        self.assertIn("Noel Chauffer", html)
        self.assertIn("Azher Mohammed", html)
        self.assertIn("180 Green Acres Road", html)
        self.assertIn("929-385-7597", html)
        self.assertIn("support@noelchauffer.com", html)
        self.assertIn("What we collect from customers", html)
        self.assertIn("What we collect from drivers", html)
        self.assertIn("How we use your information", html)
        self.assertIn("How long we keep it", html)
        self.assertIn("at least 1 year", html)
        self.assertIn("TEST MODE", html)
        self.assertIn("We do not sell your data", html)

    def test_homepage_footer_links_to_privacy(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn('href="/privacy"', html)


if __name__ == "__main__":
    unittest.main()
