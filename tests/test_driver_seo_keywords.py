"""Driver-page SEO keywords: driver recruitment.

Owner decision 2026-11-19 ("driver wale keywords banao"): add the
driver keywords that were still missing from the driver page —
"become a driver", "become a chauffeur driver", "chauffeur jobs
New York / NYC", "limo driver jobs", "black car driver jobs",
"part-time chauffeur jobs", "flexible driving jobs", "drive your own
car" — plus TLC keywords ("TLC driver jobs", "drive with a TLC
License", "TLC chauffeur jobs New York"): a TLC License is one of the
registration documents NYC drivers upload. Owner also confirmed the
top 3 cities — Los Angeles, Chicago, Miami — with driver keywords
("chauffeur driver jobs Los Angeles", "limo driver jobs Chicago",
"black car driver jobs Miami", "chauffeur driver jobs Miami"); all
three cities are in the registration picker (app.py state/city lists),
so naming them is honest. Added as a visible FAQ section with
matching FAQPage JSON-LD, using only the real offer (own car, pick
the jobs you want, register in minutes). Owner decision 2026-11-20:
the displayed driver per-mile rates ($4/$7) were removed from this
page; new prices will be added later.

Hard rules (owner): no per-mile pay figures on this page; no
benefits invented (no sign-up bonus, no guaranteed earnings, no hourly
pay claim); no customer keywords on this page (no JFK / LaGuardia /
Newark airport-transfer wording — this page recruits drivers).
"""
import json
import re
import unittest
from pathlib import Path

DRIVER = Path(__file__).resolve().parent.parent / "static" / "driver.html"

NEW_QUESTIONS = [
    "How do I become a driver with Noel Chauffer?",
    "How do I become a chauffeur driver in New York?",
    "Are these part-time chauffeur jobs?",
    "Can I drive my own car?",
    "What kind of driver jobs are these?",
    "Can I drive with a TLC license?",
    "Which cities can I drive in?",
]

NEW_KEYWORDS = [
    "become a driver",
    "become a chauffeur driver",
    "chauffeur jobs in new york city",
    "limo driver jobs",
    "black car driver jobs",
    "part-time chauffeur jobs",
    "flexible driving jobs",
    "drive your own car",
    "tlc driver jobs",
    "drive with a tlc license",
    "tlc chauffeur jobs",
    "chauffeur driver jobs in los angeles",
    "limo driver jobs in chicago",
    "black car driver jobs in miami",
    "chauffeur driver jobs in miami",
]


class DriverSeoKeywordsTest(unittest.TestCase):
    def setUp(self):
        self.html = DRIVER.read_text(encoding="utf-8")

    def _faq_schema(self):
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.html,
            re.S,
        )
        schemas = [json.loads(b) for b in blocks]
        return next(s for s in schemas if s.get("@type") == "FAQPage")

    def test_faq_covers_new_driver_questions(self):
        faq = self._faq_schema()
        questions = [q["name"] for q in faq["mainEntity"]]
        for question in NEW_QUESTIONS:
            self.assertIn(question, questions)
            # Visible FAQ must match the schema, so users see what Google reads.
            self.assertIn(f"<h3>{question}</h3>", self.html)

    def test_driver_page_contains_new_keywords(self):
        lowered = self.html.lower()
        for keyword in NEW_KEYWORDS:
            self.assertIn(keyword, lowered, keyword)

    def test_no_per_mile_rates_on_driver_page(self):
        # Owner decision 2026-11-20: remove the displayed driver
        # per-mile rates now; new prices will be added later.
        # No $4/$7 rate or "per mile" wording may appear anywhere
        # on the driver page (meta/OG/Twitter/JSON-LD/visible copy).
        for banned in ["$4", "$7", "per mile"]:
            self.assertNotIn(banned, self.html, banned)

    def test_no_customer_airport_keywords(self):
        # This page recruits drivers; it must not sell rides.
        lowered = self.html.lower()
        for phrase in ["airport transfer", "jfk", "laguardia", "newark"]:
            self.assertNotIn(phrase, lowered, phrase)

    def test_jobposting_schema_still_present(self):
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.html,
            re.S,
        )
        schemas = [json.loads(b) for b in blocks]
        job = next(s for s in schemas if s.get("@type") == "JobPosting")
        self.assertEqual(job["title"], "Chauffeur Driver")


if __name__ == "__main__":
    unittest.main()
