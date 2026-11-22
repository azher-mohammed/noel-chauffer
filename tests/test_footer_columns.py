"""Footer columns (owner order, voice call 2026-11-22 ~06:58 EST,
"abhi to kar do phir dekhta hoon main kya karna hai").

Column order (DOM order, desktop and mobile): Airport transfers,
Where we drive, Guides, Services, Company. On the mobile
two-column grid: row 1 Airport transfers | Where we drive,
row 2 Guides | Services, row 3 Company.

Where we drive lists EXACTLY: Manhattan, Brooklyn, Queens,
Long Island, Rochester, New York — first four linked, Rochester
and New York as PLAIN TEXT (no pages exist for them yet; no link
invented). Westchester, New Jersey, Connecticut and Hamptons are
dropped from the footer list per the owner's dictation — their
pages stay live at their URLs, only the footer links go.

Airport transfers, Guides, Services and Company columns are
unchanged. The footer address/phone/email line is unchanged.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="noel-footer-columns-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "footer-columns-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
from blacklane_pricing import compute_blacklane_one_way  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
INDEX = (REPO_DIR / "static" / "index.html").read_text()
FOOTER = re.search(
    r'<nav class="footer-cols"[^>]*>(.*?)</nav>', INDEX, re.S
).group(1)


def _col_block(heading):
    m = re.search(
        r"<h3>" + re.escape(heading) + r"</h3>\s*<ul>(.*?)</ul>",
        FOOTER,
        re.S,
    )
    assert m, f"footer column {heading!r} not found"
    return m.group(1)


class TestFooterColumns(unittest.TestCase):
    def test_footer_column_order(self):
        headings = re.findall(r"<h3>(.*?)</h3>", FOOTER)
        self.assertEqual(
            headings,
            ["Airport transfers", "Where we drive", "Guides",
             "Services", "Company"],
        )

    def test_where_we_drive_list_exact(self):
        items = re.findall(r"<li>(.*?)</li>", _col_block("Where we drive"), re.S)
        self.assertEqual(
            items,
            ['<a href="/manhattan-car-service">Manhattan</a>',
             '<a href="/brooklyn-car-service">Brooklyn</a>',
             '<a href="/queens-car-service">Queens</a>',
             '<a href="/long-island-car-service">Long Island</a>',
             "Rochester",
             "New York"],
        )
        # Rochester and New York are plain text — no page, no link.
        self.assertNotIn("/rochester", FOOTER)
        self.assertNotIn("/new-york-car-service", FOOTER)

    def test_dropped_places_gone_from_footer_only(self):
        for place in ("Westchester", "New Jersey", "Connecticut", "Hamptons"):
            self.assertNotIn(place, FOOTER)

    def test_other_columns_unchanged(self):
        self.assertEqual(
            re.findall(r"<li>(.*?)</li>", _col_block("Airport transfers"), re.S),
            ['<a href="/jfk-airport-transfers">JFK Airport Transfers</a>',
             '<a href="/laguardia-airport-transfers">LaGuardia Airport Transfers</a>',
             '<a href="/newark-airport-transfers">Newark Airport Transfers</a>',
             '<a href="/teterboro-airport-transfers">Teterboro Airport Transfers</a>'],
        )
        guides = _col_block("Guides")
        for href in ("/guides/jfk-vs-laguardia-vs-newark",
                     "/guides/black-car-vs-uber-black",
                     "/guides/jfk-terminal-pickup-guide",
                     "/guides/how-much-is-a-black-car-in-nyc",
                     "/guides"):
            self.assertIn(f'href="{href}"', guides)
        services = _col_block("Services")
        for href in ("/hourly-chauffeur-service", "/corporate-car-service",
                     "/wedding-car-service", "/point-to-point-car-service"):
            self.assertIn(f'href="{href}"', services)
        company = _col_block("Company")
        for href in ("/driver", "/app", "/privacy"):
            self.assertIn(f'href="{href}"', company)

    def test_footer_nap_line_unchanged(self):
        self.assertIn(
            "180 Green Acres Road, East Valley Stream, NY 11581",
            INDEX,
        )
        self.assertIn("929-385-7597", INDEX)
        self.assertIn("support@noelchauffer.com", INDEX)

    def test_dropped_city_pages_still_live(self):
        client = app_module.app.test_client()
        for route in ("/westchester-car-service", "/new-jersey-car-service",
                      "/connecticut-car-service", "/hamptons-car-service"):
            with self.subTest(route=route):
                self.assertEqual(client.get(route).status_code, 200, route)

    def test_fares_unchanged(self):
        # JFK -> Times Square, 17.9 mi, $7.46 toll: the Blacklane
        # engine figures the footer change must not touch.
        r = compute_blacklane_one_way(D("17.9"), "sedan",
                                      "JFK Airport", "Times Square",
                                      toll=D("7.46"))
        self.assertEqual(r["total"], D("201.33"))
        self.assertEqual(r["driver_earnings"], D("102.46"))


if __name__ == "__main__":
    unittest.main()
