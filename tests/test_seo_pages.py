"""Tests for the full SEO page set (owner decision 2026-11-20: full SEO
of all 8 companies in the competitor audit, on our website).

24 new pages on top of the 3 airport pages: Teterboro, 8 area pages,
6 route pages, 4 service pages, a guides hub and 4 guides. Each page
follows the JFK/LGA airport-page pattern (keyword title, meta
description, canonical, Service + LocalBusiness + FAQPage JSON-LD,
internal links, "Last updated: 20 November 2026") with Noel's own
text — no copied text, no copied prices.

These tests pin:
- Every new route returns 200 with its keyword title, canonical,
  FAQPage JSON-LD (5-8 questions matching the visible FAQ headings)
  and LocalBusiness JSON-LD.
- NO "$" character anywhere in any new page, or in the fixed
  JFK/LaGuardia/Newark pages (owner order 2026-11-20: all prices
  removed, bookings paused). No invented reviews or ratings.
- The guides are long (800+ words of body text each).
- sitemap.xml lists 31 URLs; the homepage links to the airport,
  area and guide pages; /owner stays noindexed and out of the sitemap.

Run:  python -m unittest tests.test_seo_pages tests.test_bookings_paused -v
"""

import json
import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-seo-pages-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "seo-pages-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# path -> (title, h1 fragment)
PAGES = {
    "/teterboro-airport-transfers": (
        "Teterboro Airport Transfers — Private Jet Chauffeur Service | Noel Chauffer",
        "Teterboro Airport",
    ),
    "/manhattan-car-service": (
        "Manhattan Car Service — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "Manhattan",
    ),
    "/brooklyn-car-service": (
        "Brooklyn Car Service — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "Brooklyn",
    ),
    "/queens-car-service": (
        "Queens Car Service — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "Queens",
    ),
    "/long-island-car-service": (
        "Long Island Car Service — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "Long Island",
    ),
    "/westchester-car-service": (
        "Westchester Car Service — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "Westchester",
    ),
    "/new-jersey-car-service": (
        "New Jersey Car Service — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "New Jersey",
    ),
    "/connecticut-car-service": (
        "Connecticut Car Service — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "Connecticut",
    ),
    "/hamptons-car-service": (
        "Hamptons Car Service — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "Hamptons",
    ),
    "/jfk-to-times-square": (
        "JFK to Times Square — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "JFK to",
    ),
    "/jfk-to-manhattan": (
        "JFK to Manhattan — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "JFK to",
    ),
    "/laguardia-to-manhattan": (
        "LaGuardia to Manhattan — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "LaGuardia to",
    ),
    "/newark-to-manhattan": (
        "Newark to Manhattan — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "Newark to",
    ),
    "/valley-stream-to-jfk": (
        "Valley Stream to JFK — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "Valley Stream to",
    ),
    "/jfk-to-brooklyn": (
        "JFK to Brooklyn — Luxury Chauffeur &amp; Black Car | Noel Chauffer",
        "JFK to",
    ),
    "/hourly-chauffeur-service": (
        "Hourly Chauffeur Service — Luxury Black Car by the Hour | Noel Chauffer",
        "Hourly",
    ),
    "/corporate-car-service": (
        "Corporate Car Service — Business Chauffeur Service | Noel Chauffer",
        "Corporate",
    ),
    "/wedding-car-service": (
        "Wedding Car Service — Luxury Chauffeur for Your Wedding Day | Noel Chauffer",
        "Wedding",
    ),
    "/point-to-point-car-service": (
        "Point to Point Car Service — One-Way Chauffeur Rides | Noel Chauffer",
        "Point to Point",
    ),
    "/guides": (
        "Guides — Chauffeur, Airport &amp; Black Car Guides | Noel Chauffer",
        "Noel Chauffer",
    ),
    "/guides/jfk-vs-laguardia-vs-newark": (
        "JFK vs LaGuardia vs Newark — Which Airport Is Best? | Noel Chauffer",
        "JFK vs LaGuardia",
    ),
    "/guides/black-car-vs-uber-black": (
        "Black Car vs Uber Black — What Is the Difference? | Noel Chauffer",
        "Black Car",
    ),
    "/guides/jfk-terminal-pickup-guide": (
        "JFK Terminal Pickup Guide — Where to Meet Your Chauffeur | Noel Chauffer",
        "JFK Terminal",
    ),
    "/guides/how-much-is-a-black-car-in-nyc": (
        "How Much Is a Black Car in NYC? What Affects Your Fare | Noel Chauffer",
        "How Much Is a",
    ),
}

FIXED_AIRPORT_FILES = (
    "static/jfk-airport-transfers.html",
    "static/laguardia-airport-transfers.html",
    "static/newark-airport-transfers.html",
)

GUIDES = (
    "/guides/jfk-vs-laguardia-vs-newark",
    "/guides/black-car-vs-uber-black",
    "/guides/jfk-terminal-pickup-guide",
    "/guides/how-much-is-a-black-car-in-nyc",
)


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def jsonld_blocks(html):
    """All parsed JSON-LD blocks on the page."""
    blocks = []
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        blocks.append(json.loads(m.group(1)))
    return blocks


def faq_jsonld(html):
    for data in jsonld_blocks(html):
        if data.get("@type") == "FAQPage":
            return data
    return None


class SeoPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config["TESTING"] = True
        cls.client = app_module.app.test_client()

    # -- routes serve the pages --------------------------------------------
    def test_routes_return_200_with_keyword_title(self):
        for path, (title, h1) in PAGES.items():
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)
            html = resp.get_data(as_text=True)
            self.assertIn("<title>" + title + "</title>", html, path)
            self.assertIn(h1, html, path)

    # -- SEO head: description, canonical, index,follow, LocalBusiness -----
    def test_seo_head_tags_and_local_business(self):
        for path, (title, _h1) in PAGES.items():
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn('<meta name="description" content="', html, path)
            canonical = "https://noelchauffer.com" + path
            self.assertIn(
                '<link rel="canonical" href="' + canonical + '">', html, path
            )
            self.assertIn(
                '<meta name="robots" content="index, follow">', html, path
            )
            self.assertIn(
                '<meta property="og:url" content="' + canonical + '">',
                html,
                path,
            )
            self.assertIn("Last updated: 20 November 2026", html, path)
            types = [b.get("@type") for b in jsonld_blocks(html)]
            self.assertIn("LocalBusiness", types, path)
            local = [b for b in jsonld_blocks(html) if b.get("@type") == "LocalBusiness"][0]
            self.assertEqual(local["telephone"], "+1-929-385-7597", path)
            self.assertIn("180 Green Acres Road", json.dumps(local), path)

    # -- FAQPage JSON-LD matches the visible FAQ -----------------------------
    def test_faq_jsonld_matches_visible_faq(self):
        for path in PAGES:
            html = self.client.get(path).get_data(as_text=True)
            faq = faq_jsonld(html)
            self.assertIsNotNone(faq, path)
            questions = faq["mainEntity"]
            self.assertGreaterEqual(len(questions), 5, path)
            self.assertLessEqual(len(questions), 8, path)
            visible = re.findall(
                r'<div class="faq-item">\s*<h3>(.*?)</h3>', html
            )
            self.assertEqual(len(visible), len(questions), path)
            for q in questions:
                self.assertEqual(q["@type"], "Question", path)
                self.assertIn(q["name"], visible, path)
                self.assertIn(q["acceptedAnswer"]["text"], html, path)

    # -- no prices, no invented reviews --------------------------------------
    def test_no_dollar_sign_anywhere(self):
        for path in list(PAGES) + [
            "/jfk-airport-transfers",
            "/laguardia-airport-transfers",
            "/newark-airport-transfers",
        ]:
            html = self.client.get(path).get_data(as_text=True)
            self.assertNotIn("$", html, path)
        for rel in FIXED_AIRPORT_FILES:
            self.assertNotIn("$", read(rel), rel)

    def test_no_invented_reviews_or_ratings(self):
        for path in PAGES:
            html = self.client.get(path).get_data(as_text=True)
            for banned in ("stars", "5.0", "4.9", "375 reviews", "49 reviews"):
                self.assertNotIn(banned, html, path)

    # -- live rules on every page ---------------------------------------------
    def test_live_rules_present(self):
        for path in PAGES:
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn("60 minutes of free waiting", html, path)
            self.assertIn(
                "Bookings are currently paused while we update our prices",
                html,
                path,
            )

    # -- internal links ---------------------------------------------------------
    def test_internal_links(self):
        for path in PAGES:
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn('href="/"', html, path)  # booking
            # At least one guide/area/airport link beyond booking.
            self.assertTrue(
                any(
                    other in html
                    for other in (
                        "/guides/", "/jfk-airport-transfers",
                        "/laguardia-airport-transfers",
                        "/newark-airport-transfers",
                        "/manhattan-car-service",
                    )
                ),
                path,
            )

    # -- guides are long ---------------------------------------------------------
    def test_guides_are_long(self):
        for path in GUIDES:
            html = self.client.get(path).get_data(as_text=True)
            text = re.sub(r"<[^>]+>", " ", html)
            words = len(text.split())
            self.assertGreaterEqual(words, 800, "%s has %d words" % (path, words))

    # -- sitemap ------------------------------------------------------------------
    def test_sitemap_lists_all_pages(self):
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        root = ET.fromstring(resp.get_data(as_text=True))
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [el.text for el in root.findall("s:url/s:loc", ns)]
        self.assertEqual(len(locs), 31)
        for path in list(PAGES) + [
            "/jfk-airport-transfers",
            "/laguardia-airport-transfers",
            "/newark-airport-transfers",
        ]:
            self.assertIn("https://noelchauffer.com" + path, locs, path)
        for old in ("https://noelchauffer.com/",
                    "https://noelchauffer.com/driver",
                    "https://noelchauffer.com/app",
                    "https://noelchauffer.com/privacy"):
            self.assertIn(old, locs)
        self.assertNotIn("https://noelchauffer.com/owner", locs)

    # -- homepage links + owner still noindexed ----------------------------------
    def test_homepage_links_to_new_pages(self):
        html = self.client.get("/").get_data(as_text=True)
        for path in ("/jfk-airport-transfers", "/laguardia-airport-transfers",
                     "/newark-airport-transfers", "/teterboro-airport-transfers",
                     "/manhattan-car-service", "/brooklyn-car-service",
                     "/guides", "/guides/jfk-vs-laguardia-vs-newark"):
            self.assertIn('href="' + path + '"', html, path)
        self.assertIn(
            "Bookings are paused while we update our prices", html
        )

    def test_owner_still_noindexed(self):
        owner = self.client.get("/owner")
        self.assertEqual(owner.status_code, 200)
        self.assertIn(
            '<meta name="robots" content="noindex, nofollow">',
            owner.get_data(as_text=True),
        )


if __name__ == "__main__":
    unittest.main()
