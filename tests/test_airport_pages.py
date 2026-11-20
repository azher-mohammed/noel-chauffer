"""Tests for the three SEO airport pages (owner decision 2026-11-20:
build JFK, LaGuardia and Newark airport pages like the top-ranking
competitors, specially for SEO).

Each page lives at /<slug>-airport-transfers (static HTML + a route
in app.py) and follows the competitors' per-airport page pattern
(keyword title, terminal detail, FAQ with FAQPage JSON-LD, internal
links) with Noel's own text — no copied text, no copied prices.

These tests pin:
- All three routes return 200 with the right page; /, /driver,
  /app, /privacy and /owner still serve their pages, owner still
  noindexed.
- Keyword title + meta description + canonical + index,follow on
  each page.
- FAQPage JSON-LD parses, has 8 questions, and every question
  matches a visible FAQ heading (and vice versa).
- Real terminal facts only: JFK T1/T4/T5/T7/T8; LGA A/B/C with
  the old Terminal D folded into C; EWR A/B/C.
- The live rules: 60 minutes free airport waiting, flight number
  as a separate skippable step, free cancellation more than 1 hour
  before pickup.
- NO fare or rate figures anywhere on the pages: NO $ figure at all
  (owner order 2026-11-20 — all prices removed, bookings paused);
  waiting after the free 60 minutes is described without a figure;
  no per-mile rates, no class totals, no booking fee.
- Internal links: each page links to booking (/) and to the other
  two airport pages.
- sitemap.xml lists all three airport URLs (31 URLs total after the
  full SEO page set).

Run:  python -m unittest discover -s tests -v
"""

import json
import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-airport-pages-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "airport-pages-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAGES = {
    "/jfk-airport-transfers": {
        "file": "static/jfk-airport-transfers.html",
        "title": "JFK Airport Transfers — Luxury Chauffeur &amp; Black Car Service | Noel Chauffer",
        "canonical": "https://noelchauffer.com/jfk-airport-transfers",
        "h1": "JFK Airport",
        "terminals": ["Terminal 1", "Terminal 4", "Terminal 5", "Terminal 7", "Terminal 8"],
        "others": ["/laguardia-airport-transfers", "/newark-airport-transfers"],
    },
    "/laguardia-airport-transfers": {
        "file": "static/laguardia-airport-transfers.html",
        "title": "LaGuardia Airport Transfers — Luxury Chauffeur &amp; Black Car Service | Noel Chauffer",
        "canonical": "https://noelchauffer.com/laguardia-airport-transfers",
        "h1": "LaGuardia Airport",
        "terminals": ["Terminal A", "Terminal B", "Terminal C"],
        "others": ["/jfk-airport-transfers", "/newark-airport-transfers"],
    },
    "/newark-airport-transfers": {
        "file": "static/newark-airport-transfers.html",
        "title": "Newark Airport Transfers — Luxury Chauffeur &amp; Black Car Service | Noel Chauffer",
        "canonical": "https://noelchauffer.com/newark-airport-transfers",
        "h1": "Newark Airport",
        "terminals": ["Terminal A", "Terminal B", "Terminal C"],
        "others": ["/jfk-airport-transfers", "/laguardia-airport-transfers"],
    },
}


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def faq_jsonld(html):
    """Return the parsed FAQPage JSON-LD block, or None."""
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        data = json.loads(m.group(1))
        if data.get("@type") == "FAQPage":
            return data
    return None


class AirportPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config["TESTING"] = True
        cls.client = app_module.app.test_client()

    # -- routes serve the pages --------------------------------------------
    def test_routes_return_200_with_keyword_title(self):
        for path, spec in PAGES.items():
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)
            html = resp.get_data(as_text=True)
            self.assertIn("<title>" + spec["title"] + "</title>", html, path)
            self.assertIn(spec["h1"], html, path)

    def test_other_pages_still_serve(self):
        for path, marker in (
            ("/", "Luxury rides, chauffeur-driven."),
            ("/driver", "Drive with Noel Chauffer"),
            ("/app", "Noel Chauffer"),
            ("/privacy", "Privacy"),
        ):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)
            self.assertIn(marker, resp.get_data(as_text=True), path)
        owner = self.client.get("/owner")
        self.assertEqual(owner.status_code, 200)
        self.assertIn(
            '<meta name="robots" content="noindex, nofollow">',
            owner.get_data(as_text=True),
        )

    # -- SEO head: description, canonical, index,follow --------------------
    def test_seo_head_tags(self):
        for path, spec in PAGES.items():
            html = read(spec["file"])
            self.assertIn(
                '<meta name="description" content="', html, path
            )
            self.assertIn(
                '<link rel="canonical" href="' + spec["canonical"] + '">',
                html,
                path,
            )
            self.assertIn(
                '<meta name="robots" content="index, follow">', html, path
            )
            # Open Graph URL matches the canonical.
            self.assertIn(
                '<meta property="og:url" content="' + spec["canonical"] + '">',
                html,
                path,
            )

    # -- FAQPage JSON-LD matches the visible FAQ -----------------------------
    def test_faq_jsonld_matches_visible_faq(self):
        for path, spec in PAGES.items():
            html = read(spec["file"])
            faq = faq_jsonld(html)
            self.assertIsNotNone(faq, path)
            questions = faq["mainEntity"]
            self.assertEqual(len(questions), 8, path)
            visible = re.findall(
                r'<div class="faq-item">\s*<h3>(.*?)</h3>', html
            )
            self.assertEqual(len(visible), 8, path)
            for q in questions:
                self.assertEqual(q["@type"], "Question", path)
                self.assertIn(q["name"], visible, path)
                answer = q["acceptedAnswer"]["text"]
                # The JSON-LD answer text must appear in the visible FAQ.
                self.assertIn(answer, html, path)

    # -- real terminal facts only --------------------------------------------
    def test_terminal_facts(self):
        for path, spec in PAGES.items():
            html = read(spec["file"])
            for terminal in spec["terminals"]:
                self.assertIn(terminal, html, path)
        lga = read(PAGES["/laguardia-airport-transfers"]["file"])
        # The old Terminal D is folded into C — no separate Terminal D.
        self.assertIn("old Terminal D is now part of Terminal C", lga)
        jfk = read(PAGES["/jfk-airport-transfers"]["file"])
        # No invented JFK Terminal 2/3/6 service.
        self.assertIn("Terminals 2, 3 and 6 are closed", jfk)

    # -- live rules on every page ---------------------------------------------
    def test_live_rules_present(self):
        for path, spec in PAGES.items():
            html = read(spec["file"])
            self.assertIn("60 minutes of free waiting", html, path)
            self.assertIn("waiting charges apply", html, path)
            self.assertIn("flight number is asked as a separate step", html, path)
            self.assertIn("You can skip it", html, path)
            self.assertIn(
                "Cancellation is free more than 1 hour before pickup", html, path
            )

    # -- no fare or rate figures ----------------------------------------------
    def test_no_fare_or_rate_figures(self):
        for path, spec in PAGES.items():
            html = read(spec["file"])
            figures = sorted(set(re.findall(r"\$\d[\d,]*", html)))
            # No $ figure at all (owner order 2026-11-20).
            self.assertEqual(figures, [], path)
            self.assertNotIn("$", html, path)
            for banned in ("per mile", "per-mile", "$/mi", "per hour",
                           "booking fee", "$9", "$10", "$4", "$6"):
                self.assertNotIn(banned, html, path)

    # -- internal links ---------------------------------------------------------
    def test_internal_links(self):
        for path, spec in PAGES.items():
            html = read(spec["file"])
            self.assertIn('href="/"', html, path)  # booking
            for other in spec["others"]:
                self.assertIn('href="' + other + '"', html, path)

    # -- sitemap ------------------------------------------------------------------
    def test_sitemap_lists_all_three_airport_pages(self):
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        root = ET.fromstring(resp.get_data(as_text=True))
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [el.text for el in root.findall("s:url/s:loc", ns)]
        self.assertEqual(len(locs), 31)
        for path in PAGES:
            self.assertIn("https://noelchauffer.com" + path, locs, path)
        for old in ("https://noelchauffer.com/",
                    "https://noelchauffer.com/driver",
                    "https://noelchauffer.com/app"):
            self.assertIn(old, locs)


if __name__ == "__main__":
    unittest.main()
