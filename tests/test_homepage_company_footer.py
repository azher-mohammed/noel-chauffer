"""Homepage "Our company" section moved into the footer
(owner order, voice call 2026-11-22 ~19:49-19:54 EST).

- The "Our company" SECTION is off the homepage entirely.
- Its place: the footer "Company" column carries a short
  business line, written in short classy English, few words,
  few lines, clear on first read (owner: "ekdum classy
  English", "business tone, not flowery", "padhte hi samajh
  mein aaya wala"):
  "Premium chauffeur service across the USA. On-time pickups,
  calm and comfortable rides."
  It is NOT a copy of the old homepage paragraph.
- The separate /our-company page keeps the full original
  text, and the top-nav "Our company" link stays.
- Footer column order and the Company links are unchanged.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="noel-company-footer-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
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

COMPANY_LINE = (
    "Premium chauffeur service across the USA. "
    "On-time pickups, calm and comfortable rides."
)
OLD_PARAGRAPH_TAIL = "Every ride is prepared, so you can just step in and relax."


def _col_block(heading):
    # FOOTER is the nav's inner HTML (no </nav> inside it), so the
    # column runs to the next <h3> or the end of the footer.
    m = re.search(
        r"<h3>" + re.escape(heading) + r"</h3>(.*?)(?:<h3>|$)",
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

    def test_footer_company_column_carries_short_business_line(self):
        company = _col_block("Company")
        self.assertIn(COMPANY_LINE, company)
        # Short: two short sentences, no long paragraph.
        self.assertLessEqual(len(COMPANY_LINE.split()), 15)
        # The Company links are unchanged.
        for href in ("/driver", "/app", "/privacy"):
            self.assertIn(f'href="{href}"', company)

    def test_footer_column_order_unchanged(self):
        headings = re.findall(r"<h3>(.*?)</h3>", FOOTER)
        self.assertEqual(
            headings,
            ["Airport transfers", "Where we drive", "Guides",
             "Services", "Company"],
        )

    def test_nav_company_link_stays(self):
        nav = INDEX.split("</nav>")[0]
        self.assertIn('<a href="/our-company">Our company</a>', nav)

    def test_footer_about_styled(self):
        self.assertIn(".footer-col .footer-about", CSS)
        self.assertIn("color: #cfcfcf", CSS)

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


if __name__ == "__main__":
    unittest.main()
