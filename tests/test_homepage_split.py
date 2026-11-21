"""Homepage split (owner decision 2026-11-21, voice calls 08:59-09:02 EST).

The homepage had too much written on it ("Website ki jo page hai iske
andar bahut zyada likha hua dikh raha hai"). Each homepage section now
has its own separate page, linked from the homepage by its heading:

- /airport-pickups, /your-rides-in-your-pocket, /experience,
  /why-ride-with-noel-chauffer, /three-ways-to-ride,
  /cancellation-and-waiting, /frequently-asked-questions,
  /our-company, /contacts, /your-ride-history

Each page holds only that section's existing content, wording exactly
as-is. The homepage is short: hero + booking form + clickable
headings. "Your ride history" STAYS as a homepage link but opens on
its own page when clicked (owner clarification, recorded in MEMORY.md
2026-11-21 — this supersedes the 09:00 EST removal order in the
original brief). Its phone-lookup wiring moved verbatim from
customer.js into static/js/ride-history.js, because customer.js is
loaded only by the homepage and wires the booking form unguarded.
The "Your rides in your pocket" page shows the official Google Play
and App Store badges, both linking to the browser customer app at
/app (the native apps are not on either store yet, so no store URLs).

Run:  python -m unittest discover -s tests -v
"""

import json
import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-homepage-split-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "homepage-split-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
INDEX = REPO_DIR / "static" / "index.html"

# route -> (file, heading, unique content fragment from that section)
PAGES = {
    "/airport-pickups": (
        "airport-pickups.html",
        "Airport pickups, without the rush.",
        "at the right terminal at JFK, LaGuardia or Newark",
    ),
    "/your-rides-in-your-pocket": (
        "your-rides-in-your-pocket.html",
        "Your rides, in your pocket.",
        "No download, just open and go.",
    ),
    "/experience": (
        "experience.html",
        "Sit back and enjoy the ride.",
        "Sit back and enjoy the ride.",
    ),
    "/why-ride-with-noel-chauffer": (
        "why-ride-with-noel-chauffer.html",
        "Why ride with Noel Chauffer",
        "Professional chauffeurs",
    ),
    "/three-ways-to-ride": (
        "three-ways-to-ride.html",
        "Three ways to ride",
        "Flying in or out of JFK, LaGuardia, Newark, LAX, ORD or MIA?",
    ),
    "/cancellation-and-waiting": (
        "cancellation-and-waiting.html",
        "Cancellation &amp; waiting",
        "Free cancellation if you cancel more than 1 hour before pickup.",
    ),
    "/frequently-asked-questions": (
        "frequently-asked-questions.html",
        "Frequently asked questions",
        "How do I book a ride?",
    ),
    "/our-company": (
        "our-company.html",
        "Our company",
        "Noel Chauffer is a premium chauffeur service",
    ),
    "/contacts": (
        "contacts.html",
        "Contacts",
        "support@noelchauffer.com",
    ),
    "/your-ride-history": (
        "your-ride-history.html",
        "Your ride history",
        "Enter the phone number you booked with to see your past rides.",
    ),
}


class HomepageSplitTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.home = INDEX.read_text(encoding="utf-8")

    def test_each_new_page_returns_200_and_carries_its_section(self):
        for route, (file, heading, fragment) in PAGES.items():
            with self.subTest(route=route):
                res = self.client.get(route)
                self.assertEqual(res.status_code, 200, route)
                html = res.get_data(as_text=True)
                self.assertIn(heading, html, route)
                self.assertIn(fragment, html, route)
                # Same file the route serves, word for word.
                self.assertEqual(
                    html, (REPO_DIR / "static" / file).read_text(encoding="utf-8")
                )
                # Page head: title + canonical + footer, like the other
                # SEO pages.
                self.assertIn("<title>", html, route)
                self.assertIn(
                    f'href="https://noelchauffer.com{route}"', html, route
                )
                self.assertIn("site-footer", html, route)
                self.assertNotIn("top-strip", html, route)

    def test_homepage_links_to_all_ten_pages_by_heading(self):
        for route, (_file, heading, _fragment) in PAGES.items():
            with self.subTest(route=route):
                self.assertIn(f'<a href="{route}">{heading}</a>', self.home, route)
        # No section is reached by an in-page anchor any more.
        for anchor in ["#airports", "#why", "#ride-types", "#policy", "#faq",
                       "#company", "#contacts", "#experience", "#app-band"]:
            self.assertNotIn(f'href="{anchor}"', self.home, anchor)

    def test_homepage_no_longer_carries_the_moved_section_bodies(self):
        # The bodies moved; only the heading links stay.
        for body in [
            "Professional chauffeurs",
            "Flying in or out of JFK, LaGuardia, Newark, LAX, ORD or MIA?",
            "Free cancellation if you cancel more than 1 hour before pickup.",
            # FAQ visible heading (the bare phrase also appears in the
            # support-chat quick-question chips, which stay on the
            # homepage — the <h3> form is the FAQ body).
            "<h3>How do I book a ride?</h3>",
            "Noel Chauffer is a premium chauffeur service",
            "at the right terminal at JFK, LaGuardia or Newark",
            "No download, just open and go.",
            "Enter the phone number you booked with to see your past rides.",
            "Do you offer black car service in New York City?",
        ]:
            self.assertNotIn(body, self.home, body)
        # FAQ schema moved with the FAQ section.
        self.assertNotIn("FAQPage", self.home)
        # Homepage still has the booking form, the chat widget and the
        # footer — only the long sections left.
        self.assertIn('id="booking-form"', self.home)
        self.assertIn('id="support-chat-panel"', self.home)
        self.assertIn('id="chat-fab"', self.home)
        self.assertIn("site-footer", self.home)

    def test_ride_history_has_its_own_page(self):
        # Owner clarification (MEMORY.md 2026-11-21): "Your ride history"
        # STAYS as a homepage link but opens on its own page when clicked.
        # The homepage keeps only the heading link + nav link; the form
        # lives on the page.
        res = self.client.get("/your-ride-history")
        self.assertEqual(res.status_code, 200)
        page = res.get_data(as_text=True)
        self.assertIn("<h2>Your ride history</h2>", page)
        self.assertIn('id="history-form"', page)
        self.assertIn('id="history-phone"', page)
        self.assertIn('id="history-results"', page)
        self.assertIn("/static/js/ride-history.js", page)
        self.assertIn('<a href="/your-ride-history">Your ride history</a>', self.home)
        self.assertIn('<a href="/your-ride-history">Ride history</a>', self.home)
        for needle in [
            'id="history-form"',
            'id="history-phone"',
            "Enter the phone number you booked with to see your past rides.",
        ]:
            self.assertNotIn(needle, self.home, needle)
        # The lookup wiring moved out of customer.js into ride-history.js
        # (customer.js is loaded only by the homepage and wires the
        # booking form unguarded, so it cannot run on the history page).
        js = (REPO_DIR / "static" / "js" / "customer.js").read_text(encoding="utf-8")
        self.assertNotIn("history-form", js)
        history_js = (REPO_DIR / "static" / "js" / "ride-history.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('history-form', history_js)
        self.assertIn('/api/bookings?phone=', history_js)
        for helper in ["function esc(", "function rideLabel(", "function whenLabel(",
                       "function statusLabel("]:
            self.assertIn(helper, history_js, helper)

    def test_faq_json_ld_lives_on_the_faq_page(self):
        faq = (REPO_DIR / "static" / "frequently-asked-questions.html").read_text(
            encoding="utf-8"
        )
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', faq, re.S
        )
        schemas = [json.loads(b) for b in blocks]
        faq_schema = next(s for s in schemas if s.get("@type") == "FAQPage")
        questions = [q["name"] for q in faq_schema["mainEntity"]]
        self.assertGreater(len(questions), 10)
        for question in questions:
            self.assertIn(f"<h3>{question}</h3>", faq, question)

    def test_store_badges_link_to_the_browser_app(self):
        app_page = (
            REPO_DIR / "static" / "your-rides-in-your-pocket.html"
        ).read_text(encoding="utf-8")
        # Both official badges, side by side, next to "Open the app".
        self.assertIn('href="/app">Open the app</a>', app_page)
        self.assertIn("/static/img/google-play-badge.png", app_page)
        self.assertIn("/static/img/app-store-badge.svg", app_page)
        self.assertIn('alt="Get it on Google Play"', app_page)
        self.assertIn('alt="Download on the App Store"', app_page)
        # Both badges link to the browser app at /app — the native apps
        # are not on either store yet, so no store URLs anywhere.
        badge_links = re.findall(
            r'<a href="([^"]+)"><img src="/static/img/(?:google-play-badge\.png|app-store-badge\.svg)"',
            app_page,
        )
        self.assertEqual(badge_links, ["/app", "/app"])
        self.assertTrue((REPO_DIR / "static" / "img" / "google-play-badge.png").exists())
        self.assertTrue((REPO_DIR / "static" / "img" / "app-store-badge.svg").exists())
        for page in (REPO_DIR / "static").glob("*.html"):
            text = page.read_text(encoding="utf-8")
            self.assertNotIn("play.google.com", text, page.name)
            self.assertNotIn("apps.apple.com", text, page.name)

    def test_sitemap_lists_the_ten_new_pages(self):
        tree = ET.parse(REPO_DIR / "static" / "sitemap.xml")
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [e.text for e in tree.getroot().findall("s:url/s:loc", ns)]
        self.assertEqual(len(locs), 41)
        for route in PAGES:
            self.assertIn(f"https://noelchauffer.com{route}", locs, route)

    def test_each_new_page_has_no_duplicate_ids(self):
        for _route, (file, _heading, _fragment) in PAGES.items():
            with self.subTest(file=file):
                html = (REPO_DIR / "static" / file).read_text(encoding="utf-8")
                ids = re.findall(r'id="([^"]+)"', html)
                self.assertEqual(len(ids), len(set(ids)), file)


if __name__ == "__main__":
    unittest.main()
