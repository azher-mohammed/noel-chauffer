"""Footer address removal — owner order, main chat 2026-11-23 ~01:36 EST
("Footer se address nikal do").

- The home address "180 Green Acres Road, East Valley Stream, NY 11581"
  is OUT of every footer on the site (homepage + all section pages).
- The phone number (929-385-7597) and email (support@noelchauffer.com)
  STAY in the footer exactly as before.

SUPERSEDED scope, owner order voice call 2026-11-23 ~02:52-02:54 EST
("mere ko address nahi chahiye bhai", "app pe bhi nahi dikhna",
"na driver app pe na kahin") — the address is now OUT of EVERYWHERE:
- /contacts page (its footer line was the only place left) — gone.
- The /privacy page body — gone.
- The JSON-LD "streetAddress" structured data on the service pages —
  the whole LocalBusiness "address" object is gone.
- The customer app and driver app never carried the address (verified:
  no "180 Green Acres" / "East Valley Stream" / "11581" in either file).

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="noel-footer-address-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "footer-address-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
from blacklane_pricing import compute_blacklane_one_way  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
STATIC = REPO_DIR / "static"
ADDRESS = "180 Green Acres Road, East Valley Stream, NY 11581"


def _footer_block(html):
    m = re.search(r"<footer[^>]*>(.*?)</footer>", html, re.S)
    assert m, "no <footer> block found"
    return m.group(1)


class TestFooterAddressRemoved(unittest.TestCase):
    def test_no_address_in_any_footer(self):
        for path in sorted(STATIC.rglob("*.html")):
            html = path.read_text()
            if "<footer" not in html:
                continue  # customer app / driver / owner have no footer
            with self.subTest(page=str(path.relative_to(STATIC))):
                footer = _footer_block(html)
                self.assertNotIn("180 Green Acres", footer)
                self.assertNotIn("East Valley Stream", footer)

    def test_phone_and_email_still_in_every_footer(self):
        # privacy.html's own footer never carried the phone/email
        # line (it is just wordmark + tagline + Privacy link), so it
        # is excluded here; every other footer keeps phone + email.
        for path in sorted(STATIC.rglob("*.html")):
            html = path.read_text()
            if "<footer" not in html or path.name == "privacy.html":
                continue
            with self.subTest(page=str(path.relative_to(STATIC))):
                footer = _footer_block(html)
                self.assertIn("929-385-7597", footer)
                self.assertIn("support@noelchauffer.com", footer)

    def test_contacts_page_live_has_no_address(self):
        client = app_module.app.test_client()
        r = client.get("/contacts")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertNotIn("180 Green Acres", html)
        self.assertNotIn("East Valley Stream", html)
        self.assertNotIn("11581", html)
        self.assertIn("929-385-7597", html)
        self.assertIn("support@noelchauffer.com", html)

    def test_homepage_footer_live_has_no_address(self):
        client = app_module.app.test_client()
        r = client.get("/")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertNotIn("180 Green Acres", _footer_block(html))
        self.assertIn("929-385-7597", _footer_block(html))
        self.assertIn("support@noelchauffer.com", _footer_block(html))

    def test_no_address_anywhere_live(self):
        # Owner order 2026-11-23 ~02:52 EST: the address is nowhere —
        # website, customer app, driver app, contacts, privacy.
        client = app_module.app.test_client()
        for route in ("/", "/app", "/driver", "/contacts", "/privacy",
                      "/brooklyn-car-service"):
            with self.subTest(route=route):
                r = client.get(route)
                self.assertEqual(r.status_code, 200)
                html = r.get_data(as_text=True)
                self.assertNotIn("180 Green Acres", html)
                self.assertNotIn("East Valley Stream", html)
                self.assertNotIn("11581", html)


class TestAddressRemovedOutsideFooter(unittest.TestCase):
    def test_json_ld_street_address_removed(self):
        # The whole LocalBusiness "address" object is gone from every
        # service page; phone + email stay in the structured data.
        import json

        for path in sorted(STATIC.rglob("*.html")):
            html = path.read_text()
            if '"@type": "LocalBusiness"' not in html:
                continue
            with self.subTest(page=str(path.relative_to(STATIC))):
                self.assertNotIn('"streetAddress"', html)
                self.assertNotIn("180 Green Acres", html)
                blocks = [
                    json.loads(m.group(1)) for m in re.finditer(
                        r'<script type="application/ld\+json">(.*?)</script>',
                        html, re.S)
                ]
                local = [b for b in blocks
                         if b.get("@type") == "LocalBusiness"]
                self.assertEqual(len(local), 1)
                local = local[0]
                self.assertNotIn("address", local)
                self.assertEqual(local["telephone"], "+1-929-385-7597")
                self.assertEqual(local["email"], "support@noelchauffer.com")

    def test_privacy_body_address_removed(self):
        # The privacy page body no longer names the address; phone and
        # email stay.
        html = (STATIC / "privacy.html").read_text()
        self.assertNotIn(ADDRESS, html)
        self.assertNotIn("180 Green Acres", html)
        self.assertIn("929-385-7597", html)
        self.assertIn("support@noelchauffer.com", html)

    def test_fares_unchanged(self):
        # JFK -> Times Square, 17.9 mi, $7.46 toll: the footer change
        # must not touch pricing.
        r = compute_blacklane_one_way(D("17.9"), "sedan",
                                      "JFK Airport", "Times Square",
                                      toll=D("7.46"))
        self.assertEqual(r["total"], D("201.33"))
        self.assertEqual(r["driver_earnings"], D("102.46"))


if __name__ == "__main__":
    unittest.main()
