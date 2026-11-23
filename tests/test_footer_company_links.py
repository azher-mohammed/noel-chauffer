"""Footer "Company" column across ALL pages — owner orders, voice call
2026-11-23 ~00:21-00:24 EST.

- "Drive with us" is gone from EVERY footer that carried it (11 pages
  with the full footer). The /driver page itself stays live, and the
  top-nav "Drive with us" link on the other pages stays untouched.
- The footer "App" link is GONE from every footer (owner order
  2026-11-23 ~04:53 EST) — the app-band badges and the hamburger
  "Chauffeur hailing" link still point at /app and must NOT have
  moved.
- A new "Terms" column (heading links to /terms) carries the
  "Privacy Policy" link under it (owner order 2026-11-23 ~04:54 EST).
  The "Company" column is now just its heading link, with no list
  under it.
- The footer about-line is gone (homepage only; other footers never
  carried it).
- The "Company" heading is a link to /our-company on every footer
  that has it.
- i18n: the "foot.drive_with_us", "foot.about" and "foot.app"
  dictionary keys are intentionally LEFT in static/js/i18n.js. The
  dictionary tests only require every key to have all eight languages
  and every used key to exist; unused keys are allowed, and leaving
  them keeps the dictionary complete if the links ever come back.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="noel-footer-company-links-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "t.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "footer-company-links-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
STATIC = REPO_DIR / "static"
INDEX = (STATIC / "index.html").read_text()
I18N_JS = (STATIC / "js" / "i18n.js").read_text()

# The pages whose footer carries the full six-column block.
FULL_FOOTERS = [
    "index.html",
    "airport-pickups.html",
    "cancellation-and-waiting.html",
    "contacts.html",
    "experience.html",
    "frequently-asked-questions.html",
    "our-company.html",
    "terms.html",
    "three-ways-to-ride.html",
    "why-ride-with-noel-chauffer.html",
    "your-ride-history.html",
    "your-rides-in-your-pocket.html",
]


def _footer_block(html):
    m = re.search(r'<nav class="footer-cols"[^>]*>(.*?)</nav>', html, re.S)
    assert m, "footer-cols nav not found"
    return m.group(1)


class TestFooterCompanyLinksEverywhere(unittest.TestCase):
    def test_no_drive_with_us_in_any_footer(self):
        for name in FULL_FOOTERS:
            footer = _footer_block((STATIC / name).read_text())
            with self.subTest(page=name):
                self.assertNotIn("Drive with us", footer)
                self.assertNotIn('href="/driver"', footer)

    def test_footer_app_link_gone_everywhere(self):
        # Owner order 2026-11-23 ~04:53 EST: the "App" link is
        # removed from the Company column of every footer.
        for name in FULL_FOOTERS:
            footer = _footer_block((STATIC / name).read_text())
            with self.subTest(page=name):
                self.assertNotIn(">App</a>", footer)
                self.assertNotIn('href="/#app-band"', footer)

    def test_footer_terms_column_with_privacy_under_it(self):
        # Owner order 2026-11-23 ~04:54 EST: "Terms" is written in
        # the footer and links to /terms; "Privacy Policy" sits
        # under it. The Company column keeps only its heading.
        for name in FULL_FOOTERS:
            footer = _footer_block((STATIC / name).read_text())
            with self.subTest(page=name):
                self.assertRegex(footer, r'href="/terms"[^>]*>Terms</a>')
                self.assertIn('href="/privacy"', footer)
                self.assertLess(
                    footer.index('href="/terms"'),
                    footer.index('href="/privacy"'),
                )
                company = re.search(
                    r'<h3><a href="/our-company"[^>]*>Company</a></h3>'
                    r"(.*?)(?:<h3[^>]*>|$)",
                    footer, re.S,
                )
                assert company, f"Company column not found in {name}"
                self.assertNotIn("<ul>", company.group(1))
                self.assertNotIn(">App</a>", company.group(1))

    def test_company_heading_links_to_our_company(self):
        for name in FULL_FOOTERS:
            footer = _footer_block((STATIC / name).read_text())
            with self.subTest(page=name):
                self.assertRegex(
                    footer,
                    r'<h3><a href="/our-company"[^>]*>Company</a></h3>',
                )

    def test_no_footer_about_line_anywhere(self):
        for name in FULL_FOOTERS:
            html = (STATIC / name).read_text()
            with self.subTest(page=name):
                self.assertNotIn("footer-about", html)
                self.assertNotIn(
                    "Premium chauffeur service across the USA", html
                )

    def test_footer_nap_line_address_removed_homepage(self):
        # Owner order 2026-11-23 ~01:36 EST ("Footer se address nikal
        # do"): the home address is out of the footer. Phone and email
        # stay in the footer exactly as before.
        self.assertNotIn("180 Green Acres Road", INDEX)
        self.assertNotIn("East Valley Stream", INDEX)
        self.assertIn("929-385-7597", INDEX)
        self.assertIn("support@noelchauffer.com", INDEX)


class TestUntouchedLinks(unittest.TestCase):
    def test_top_nav_drive_with_us_stays_on_other_pages(self):
        # Only the FOOTER link goes; the header nav keeps sending
        # drivers to /driver.
        for name in ("our-company.html", "privacy.html",
                     "contacts.html"):
            html = (STATIC / name).read_text()
            with self.subTest(page=name):
                self.assertRegex(
                    html, r'href="/driver"[^>]*>Drive with us</a>'
                )

    def test_app_band_badges_still_point_at_app(self):
        # The "We move with you" badges are the downloader; they keep
        # opening /app. The footer "App" text link is gone entirely
        # (owner order 2026-11-23 ~04:53 EST) — only the badges and
        # the hamburger "Chauffeur hailing" link still go to /app.
        self.assertIn(
            'href="/app"><img src="/static/img/google-play-badge.png"',
            INDEX,
        )
        self.assertIn(
            'href="/app"><img src="/static/img/app-store-badge.svg"',
            INDEX,
        )

    def test_hamburger_chauffeur_hailing_still_points_at_app(self):
        self.assertIn(
            '<a href="/app" data-i18n="menu.chauffeur_hailing">'
            "Chauffeur hailing</a>",
            INDEX,
        )

    def test_driver_and_company_pages_still_live(self):
        client = app_module.app.test_client()
        for route in ("/driver", "/our-company"):
            with self.subTest(route=route):
                self.assertEqual(client.get(route).status_code, 200,
                                 route)

    def test_i18n_keys_left_in_place(self):
        # Unused keys are allowed by the dictionary tests; leaving them
        # keeps the dictionary complete.
        self.assertIn('"foot.drive_with_us"', I18N_JS)
        self.assertIn('"foot.about"', I18N_JS)
        self.assertIn('"foot.app"', I18N_JS)
        self.assertIn('"foot.terms"', I18N_JS)


if __name__ == "__main__":
    unittest.main()
