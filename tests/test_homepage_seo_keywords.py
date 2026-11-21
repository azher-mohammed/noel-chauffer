"""Homepage SEO keywords: black car service + JFK airport transfers.

Owner decision 2026-11-18: the two best customer keywords are
"black car service NYC" and "JFK airport transfer". They must appear in
the page title, the meta description, the Service schema and the FAQ
(both the visible section and the FAQPage JSON-LD), so Google can match
the page to those searches.

Owner decision 2026-11-19 ("to ye sab daalo"): add the five keywords
that were still missing — "LaGuardia airport transfer", "Newark airport
transfer", "luxury car service New York", "car service NYC" and
"airport car service" — as new FAQ entries (visible + JSON-LD) and in
the Airport Transfers card, naming LaGuardia and Newark alongside JFK.
No prices anywhere on the page (owner rule).

Owner decision 2026-11-19 (voice call, "Yes" to Los Angeles, Chicago,
Miami): add the top-3-city keywords — "black car service Los Angeles"
and "LAX airport transfer", "chauffeur service Chicago" and "ORD
airport transfer", "luxury car service Miami" and "MIA airport
transfer" — as three more FAQ entries (visible + JSON-LD) and in the
Airport Transfers card, naming LAX, ORD and MIA alongside the NYC
airports.

Owner decision 2026-11-21 (homepage split): the FAQ, the Airport
Transfers card and the "Three ways to ride" card moved off the homepage
onto their own pages (/frequently-asked-questions,
/three-ways-to-ride, /airport-pickups). The keyword coverage tests
below read those pages now — the keywords still live on the site,
where the content lives. Title, description and Service schema stay
on the homepage.
"""
import json
import re
import unittest
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "static" / "index.html"
FAQ = Path(__file__).resolve().parent.parent / "static" / "frequently-asked-questions.html"
THREEWAYS = Path(__file__).resolve().parent.parent / "static" / "three-ways-to-ride.html"
AIRPORTS = Path(__file__).resolve().parent.parent / "static" / "airport-pickups.html"


class HomepageSeoKeywordsTest(unittest.TestCase):
    def setUp(self):
        self.html = INDEX.read_text(encoding="utf-8")
        self.faq_html = FAQ.read_text(encoding="utf-8")
        self.threeways_html = THREEWAYS.read_text(encoding="utf-8")
        self.airports_html = AIRPORTS.read_text(encoding="utf-8")

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
        # JFK airport transfers are covered as part of the three-airport
        # list ("JFK, LaGuardia and Newark airport transfers").
        self.assertIn("JFK", service["description"])
        self.assertIn("airport transfers", service["description"])

    def test_faq_covers_best_keywords(self):
        # FAQ lives on its own page since the 2026-11-21 homepage split.
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.faq_html,
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
            self.faq_html,
        )
        self.assertIn("<h3>Do you do JFK airport transfers?</h3>", self.faq_html)

    def test_faq_covers_new_airport_keywords(self):
        # FAQ lives on its own page since the 2026-11-21 homepage split.
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.faq_html,
            re.S,
        )
        schemas = [json.loads(b) for b in blocks]
        faq = next(s for s in schemas if s.get("@type") == "FAQPage")
        questions = [q["name"] for q in faq["mainEntity"]]
        new_questions = [
            "Do you do LaGuardia airport transfers?",
            "Do you do Newark airport transfers?",
            "Do you offer luxury car service in New York?",
        ]
        for question in new_questions:
            self.assertIn(question, questions)
            # Visible FAQ must match the schema, so users see what Google reads.
            self.assertIn(f"<h3>{question}</h3>", self.faq_html)

    def test_faq_page_contains_new_keywords(self):
        # Keywords live in the FAQ answers on the FAQ page now.
        lowered = self.faq_html.lower()
        for keyword in [
            "laguardia airport transfer",
            "newark airport transfer",
            "luxury car service new york",
            "car service nyc",
            "airport car service",
        ]:
            self.assertIn(keyword, lowered, keyword)

    def test_airport_transfers_card_names_all_airports(self):
        # Cards moved off the homepage in the 2026-11-21 split.
        self.assertIn(
            "Flying in or out of JFK, LaGuardia, Newark, LAX, ORD or MIA?",
            self.threeways_html,
        )
        self.assertIn(
            "at the right terminal at JFK, LaGuardia or Newark", self.airports_html
        )

    def test_faq_covers_top_three_city_keywords(self):
        # FAQ lives on its own page since the 2026-11-21 homepage split.
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.faq_html,
            re.S,
        )
        schemas = [json.loads(b) for b in blocks]
        faq = next(s for s in schemas if s.get("@type") == "FAQPage")
        questions = [q["name"] for q in faq["mainEntity"]]
        new_questions = [
            "Do you do LAX airport transfers?",
            "Do you do ORD airport transfers?",
            "Do you do MIA airport transfers?",
        ]
        for question in new_questions:
            self.assertIn(question, questions)
            # Visible FAQ must match the schema, so users see what Google reads.
            self.assertIn(f"<h3>{question}</h3>", self.faq_html)

    def test_faq_page_contains_top_three_city_keywords(self):
        # Keywords live in the FAQ answers on the FAQ page now.
        lowered = self.faq_html.lower()
        for keyword in [
            "black car service los angeles",
            "lax airport transfer",
            "chauffeur service chicago",
            "ord airport transfer",
            "luxury car service miami",
            "mia airport transfer",
        ]:
            self.assertIn(keyword, lowered, keyword)

    def test_service_schema_names_all_airports(self):
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>',
            self.html,
            re.S,
        )
        schemas = [json.loads(b) for b in blocks]
        service = next(s for s in schemas if s.get("@type") == "Service")
        self.assertIn("Luxury car service", service["serviceType"])
        self.assertIn("LaGuardia and Newark airport transfers",
                      service["description"])


if __name__ == "__main__":
    unittest.main()
