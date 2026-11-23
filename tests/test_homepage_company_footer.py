"""Footer "Company" column — owner orders, voice call 2026-11-23
~00:21-00:24 EST.

The short business line added to the footer 2026-11-22 (commit 0152e58)
is now GONE, by the owner's word:
- "Drive with us" link REMOVED from the footer (the /driver page stays
  live; the top-nav "Drive with us" link on the other pages stays).
- Footer "App" link REMOVED entirely (owner order 2026-11-23
  ~04:53 EST). The app-band badges and the /app page itself are
  untouched.
- A new "Terms" footer column (heading links to /terms) carries the
  "Privacy Policy" link under it (owner order 2026-11-23 ~04:54 EST).
  The "Company" column is now just its heading link.
- The footer about-line "Premium chauffeur service across the USA.
  On-time pickups, calm and comfortable rides." is REMOVED completely,
  with its HTML comment and its CSS rule.
- The "Company" heading is now a LINK to the separate /our-company
  page, which carries the full company details.
- The "Our company" SECTION stays off the homepage entirely, and the
  top-nav "Our company" link stays.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="noel-company-footer-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "t.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "company-footer-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
INDEX = (REPO_DIR / "static" / "index.html").read_text()
CSS = (REPO_DIR / "static" / "css" / "customer.css").read_text()
FOOTER = re.search(
    r'<nav class="footer-cols"[^>]*>(.*?)</nav>', INDEX, re.S
).group(1)

OLD_COMPANY_LINE = (
    "Premium chauffeur service across the USA. "
    "On-time pickups, calm and comfortable rides."
)
OLD_PARAGRAPH_TAIL = "Every ride is prepared, so you can just step in and relax."


def _col_block(heading):
    # FOOTER is the nav's inner HTML (no </nav> inside it), so the
    # column runs to the next <h3> or the end of the footer. The Company
    # heading is a link to /our-company, so the text may sit in an <a>.
    m = re.search(
        r"<h3[^>]*>(?:<a[^>]*>)?" + re.escape(heading)
        + r"(?:</a>)?</h3>(.*?)(?:<h3[^>]*>|$)",
        FOOTER,
        re.S,
    )
    assert m, f"footer column {heading!r} not found"
    return m.group(1)


class TestHomepageCompanyFooter(unittest.TestCase):
    def test_company_section_off_homepage(self):
        self.assertNotIn('id="company"', INDEX)
        self.assertNotIn('<section class="section company"', INDEX)
        self.assertNotIn(
            '<h2><a href="/our-company">Our company</a></h2>', INDEX
        )
        # The old homepage paragraph is gone from the homepage too.
        self.assertNotIn(
            "Noel Chauffer is a premium chauffeur service in the USA.",
            INDEX,
        )
        self.assertNotIn(OLD_PARAGRAPH_TAIL, INDEX)

    def test_footer_about_line_removed_completely(self):
        # Owner order 2026-11-23: the whole line goes, not just a word.
        self.assertNotIn(OLD_COMPANY_LINE, INDEX)
        self.assertNotIn("Premium chauffeur service across the USA", INDEX)
        self.assertNotIn("footer-about", INDEX)
        self.assertNotIn("Our company line (owner 2026-11-22)", INDEX)

    def test_footer_company_links(self):
        company = _col_block("Company")
        # "Drive with us" is gone from the footer entirely.
        self.assertNotIn("Drive with us", company)
        self.assertNotIn('href="/driver"', company)
        # Owner order 2026-11-23 ~04:53 EST: the "App" link is gone
        # from the Company column entirely, and "Privacy Policy"
        # moved under the new "Terms" column.
        self.assertNotIn('href="/#app-band"', company)
        self.assertNotIn(">App</a>", company)
        self.assertNotIn('href="/privacy"', company)
        terms = _col_block("Terms")
        self.assertIn('href="/privacy"', terms)
        self.assertNotIn('href="/#app-band"', terms)

    def test_company_heading_links_to_our_company(self):
        self.assertRegex(
            FOOTER,
            r'<h3><a href="/our-company" data-i18n="foot.company">Company</a></h3>',
        )

    def test_footer_column_order_unchanged(self):
        headings = re.findall(r"<h3[^>]*>(.*?)</h3>", FOOTER)
        self.assertEqual(
            headings,
            ["Airport transfers", "Where we drive", "Guides",
             "Services",
             '<a href="/our-company" data-i18n="foot.company">Company</a>',
             '<a href="/terms" data-i18n="foot.terms">Terms</a>'],
        )

    def test_nav_company_link_stays(self):
        nav = INDEX.split("</nav>")[0]
        self.assertRegex(nav, r'<a href="/our-company"[^>]*>Our company</a>')

    def test_footer_about_style_removed_heading_link_styled(self):
        # The dead .footer-about rule goes with the paragraph.
        self.assertNotIn(".footer-about", CSS)
        # The heading link inherits the heading look (white, 15px).
        self.assertIn(".footer-col h3 a", CSS)
        self.assertIn("color: inherit", CSS)

    def test_our_company_page_keeps_full_original_text(self):
        res = app_module.app.test_client().get("/our-company")
        self.assertEqual(res.status_code, 200)
        page = res.get_data(as_text=True)
        self.assertIn("<h2>Our company</h2>", page)
        self.assertIn(
            "Noel Chauffer is a premium chauffeur service in the USA.",
            page,
        )
        self.assertIn(OLD_PARAGRAPH_TAIL, page)

    def test_our_company_page_has_good_details(self):
        # Owner order 2026-11-23 ~00:23 EST: clicking "Company" opens
        # a page with good details about the company — all facts
        # already on the site, nothing invented.
        res = app_module.app.test_client().get("/our-company")
        page = res.get_data(as_text=True)
        for heading in ("What we do", "Airport transfers",
                        "How a ride works", "What to expect",
                        "Cancellation and waiting"):
            self.assertIn(f"<h3>{heading}</h3>", page)
        self.assertIn("City-to-city rides", page)
        self.assertIn("JFK, LaGuardia, Newark, LAX, ORD or MIA", page)
        self.assertIn("choose your class and pay by card", page)
        self.assertIn("Professional chauffeurs", page)
        self.assertIn("Recent high-end cars", page)
        self.assertIn("Free cancellation if you cancel more than 1 hour",
                      page)
        self.assertIn("Available 24/7", page)


if __name__ == "__main__":
    unittest.main()
