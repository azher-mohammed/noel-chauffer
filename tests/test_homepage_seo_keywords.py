"""Homepage SEO keywords: black car service + JFK airport transfers.

Owner decision 2026-11-18: the two best customer keywords are
"black car service NYC" and "JFK airport transfer". They must appear in
the page title, the meta description, the Service schema and the FAQ
(both the visible section and the FAQPage JSON-LD), so Google can match
the page to those searches.
"""
import json
import re
import unittest
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "static" / "index.html"


class HomepageSeoKeywordsTest(unittest.TestCase):
    def setUp(self):
        self.html = INDEX.read_text(encoding="utf-8")

    def test_title_has_best_keywords(self):
        title = re.search(r"<title>([^<]*)", self.html).group(1)
        self.assertIn("Black Car Service", title)
        self.assertIn("JFK Airport Transfers", title)

    def test_description_has_best_keywords(self):
        desc = re.search(
            r'<meta name="description" content="([^"]*)"', self.html
        ).group(1)
        self.assertIn("black car service", desc)
        self.assertIn("JFK airport transfers", desc)

    def test_service_schema_has_best_keywords(self):
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.html,
            re.S,
        )
        schemas = [json.loads(b) for b in blocks]
        service = next(s for s in schemas if s.get("@type") == "Service")
        self.assertIn("Black car service", service["serviceType"])
        self.assertIn("JFK airport transfers", service["description"])

    def test_faq_covers_best_keywords(self):
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.html,
            re.S,
        )
        schemas = [json.loads(b) for b in blocks]
        faq = next(s for s in schemas if s.get("@type") == "FAQPage")
        questions = [q["name"] for q in faq["mainEntity"]]
        self.assertIn(
            "Do you offer black car service in New York City?", questions
        )
        self.assertIn("Do you do JFK airport transfers?", questions)
        # Visible FAQ must match the schema, so users see what Google reads.
        self.assertIn(
            "<h3>Do you offer black car service in New York City?</h3>",
            self.html,
        )
        self.assertIn("<h3>Do you do JFK airport transfers?</h3>", self.html)


if __name__ == "__main__":
    unittest.main()
