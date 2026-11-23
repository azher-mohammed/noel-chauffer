"""Terms & Conditions page (owner orders, voice calls 2026-11-23
~04:53-04:57 EST).

- Footer "Terms" links to /terms; "Privacy Policy" sits under it.
- /terms is a real page: Terms & Conditions modelled on the
  14-section structure of Blacklane's U.S. Guest Terms (PDF sent by
  the owner), REWRITTEN in our own words for Noel Chauffer — same
  structure and coverage, Noel's name, Noel's real live rules.
- No Blacklane name, emails, or addresses anywhere; no insurance
  coverage is claimed (none is confirmed); nothing invented beyond
  the live rules and the standard legal provisions.
- Where Noel's rule differs from Blacklane's text, Noel's rule is
  what the page says (see the report in the commit message).

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-terms-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "terms-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
INDEX = (REPO_DIR / "static" / "index.html").read_text()
SITEMAP = (REPO_DIR / "static" / "sitemap.xml").read_text()


class TermsPageTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_terms_returns_200(self):
        res = self.client.get("/terms")
        self.assertEqual(res.status_code, 200)

    def test_terms_has_all_fourteen_sections(self):
        html = self.client.get("/terms").get_data(as_text=True)
        for heading in (
            "1. General Provisions",
            "2. Eligibility",
            "3. Modification of these Terms",
            "4. Arbitration Agreement",
            "5. Payment, Cancellation, and Waiting Time",
            "6. Intellectual Property",
            "7. Disclaimers",
            "8. Limitation of Liability",
            "9. Indemnity",
            "10. Force Majeure",
            "11. Term and Termination",
            "12. Choice of Law",
            "13. Choice of Forum",
            "14. Final Provisions",
        ):
            self.assertIn(heading, html, heading)

    def test_terms_states_noels_live_rules(self):
        html = self.client.get("/terms").get_data(as_text=True)
        # Payment before dispatch; unpaid bookings never dispatched.
        self.assertIn("pay by card at the time of booking", html)
        self.assertIn("only dispatched after payment", html)
        self.assertIn("Unpaid bookings are never sent to Chauffeurs", html)
        # Cancellation windows + full refund.
        self.assertIn("up to 1 hour before the scheduled pickup", html)
        self.assertIn("up to 24 hours before the scheduled pickup", html)
        self.assertIn("full refund", html)
        self.assertIn("the full fare is kept", html)
        # Waiting + no-show.
        self.assertIn("60 minutes at airport pickups", html)
        self.assertIn("15 minutes at all other pickups", html)
        self.assertIn("$1 per minute", html)
        self.assertIn("after 60 minutes of waiting at an airport pickup", html)
        self.assertIn("after 30 minutes of waiting at any other pickup", html)
        # Hourly.
        self.assertIn("minimum booking is 2 hours", html)
        self.assertIn("25 miles", html)
        # Round trip + destination change.
        self.assertIn("no round-trip booking", html.lower())
        self.assertIn("separate one-way booking", html)
        self.assertIn("cannot be changed after the booking is made", html)
        self.assertIn("cancel your booking and make a new one", html)
        # Driver assignment + tracking.
        self.assertIn("first Chauffeur to accept gets the ride", html)
        self.assertIn("name, phone number, car model", html)
        self.assertIn("live map once your Chauffeur starts heading", html)
        # Customer responsibilities.
        self.assertIn("correct pickup and drop-off addresses", html)
        self.assertIn("flight number", html)
        # Referral.
        self.assertIn("5% off their first booking", html)
        # Class capacity.
        self.assertIn("Business Class (3 passengers, 2 bags)", html)
        self.assertIn("Business SUV (5 passengers, 5 bags)", html)
        self.assertIn("First Class (3 passengers, 2 bags)", html)
        # Governing law + arbitration + liability cap.
        self.assertIn("laws of the State of New York", html)
        self.assertIn("American Arbitration Association", html)
        self.assertIn("City of New York", html)
        self.assertIn("$1,000 USD", html)
        self.assertIn("Waiver of Right to Jury Trial", html)
        self.assertIn("Waiver of Class Action", html)

    def test_terms_has_no_blacklane_and_no_insurance_claim(self):
        html = self.client.get("/terms").get_data(as_text=True)
        self.assertNotIn("Blacklane", html)
        self.assertNotIn("blacklane.com", html)
        self.assertNotIn("insurance", html.lower())
        self.assertNotIn("180 Green Acres Road", html)
        self.assertNotIn("East Valley Stream", html)
        self.assertIn("Siahsolutions Inc", html)
        self.assertIn("support@noelchauffer.com", html)
        self.assertIn("929-385-7597", html)

    def test_homepage_footer_links_to_terms(self):
        self.assertIn('href="/terms"', INDEX)
        footer = re.search(
            r'<nav class="footer-cols"[^>]*>(.*?)</nav>', INDEX, re.S
        ).group(1)
        self.assertLess(
            footer.index('href="/terms"'),
            footer.index('href="/privacy"'),
        )

    def test_sitemap_includes_terms(self):
        self.assertIn("https://noelchauffer.com/terms", SITEMAP)
        self.assertEqual(SITEMAP.count("<url>"), 42)


if __name__ == "__main__":
    unittest.main()
