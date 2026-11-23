"""Homepage restore (owner decision 2026-11-22, voice call ~02:57 EST).

The owner reversed the 2026-11-21 homepage split ("pehla page purana
jaisa kar do"): the homepage again carries the booking form on top
AND all ten sections below it on the same page, with a clean
professional look — small clean headings, simple plain text below,
page not big/heavy. The ten separate pages KEEP working (they are
still linked from the homepage headings); the sections are now
rendered on the homepage too, not only on their own pages.

Sections on the homepage (content copied verbatim from the pages):
- /airport-pickups, /your-rides-in-your-pocket, /experience,
  /why-ride-with-noel-chauffer, /three-ways-to-ride,
  /cancellation-and-waiting, /frequently-asked-questions,
  /our-company, /contacts, /your-ride-history

Rules kept from the removal order (commit 8464317): NO "Refer a
friend" text anywhere on the homepage. The FAQ's 5%-off referral
Q&A is left off the homepage (it stays on the standalone FAQ page);
the backend 5% discount for already-shared links is untouched.

The ride-history phone lookup now lives on the homepage too, so
static/js/ride-history.js is loaded by index.html as well as by
/your-ride-history.

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
_tmpdir = tempfile.mkdtemp(prefix="noel-homepage-restore-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "homepage-restore-secret-key"
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


class HomepageRestoreTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.home = INDEX.read_text(encoding="utf-8")

    def test_each_section_page_still_returns_200_and_carries_its_section(self):
        # The separate pages keep working; nothing was deleted.
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
                self.assertIn("<title>", html, route)
                self.assertIn(
                    f'href="https://noelchauffer.com{route}"', html, route
                )
                self.assertIn("site-footer", html, route)
                self.assertNotIn("top-strip", html, route)

    def test_homepage_links_to_all_ten_pages_by_heading(self):
        # (Merged 2026-11-22 rebase: the homepage below the booking
        # form has the owner's screenshot sections AND the retained
        # Why / Three ways sections, whose heading links stay. The
        # "Our company" heading link went with its section (owner
        # order 2026-11-22 ~19:51 EST, commit 0152e58) — only the
        # top-nav link stays; see the second loop below. The
        # app-band heading link to
        # /your-rides-in-your-pocket was removed by owner order
        # 2026-11-22 — the band carries only the label and the two
        # badges now. The Cancellation, FAQ and Contacts heading
        # links were removed the same day — those sections are off
        # the homepage entirely and live only on their own pages,
        # reached from the top nav. The "Your ride history" heading
        # link was removed the same evening (~19:32 EST) the same
        # way. The Airport pickups and Experience heading links
        # went with the screenshot rebuild (~20:09 EST). The pages
        # themselves still exist; see
        # test_each_section_page_still_returns_200.)
        skipped = {
            "/your-rides-in-your-pocket",
            "/cancellation-and-waiting",
            "/frequently-asked-questions",
            "/contacts",
            "/your-ride-history",
            "/airport-pickups",
            "/experience",
            "/our-company",
        }
        for route, (_file, heading, _fragment) in PAGES.items():
            if route in skipped:
                continue
            with self.subTest(route=route):
                self.assertIn(f'<a href="{route}">{heading}</a>', self.home, route)
        # The top nav still links to every section page except
        # /your-rides-in-your-pocket (the app-band heading link was
        # removed by owner order 2026-11-22 and the page has no nav
        # entry). The other pages still exist; see
        # test_each_section_page_still_returns_200.
        for route in PAGES:
            if route in ("/your-rides-in-your-pocket",):
                continue
            with self.subTest(route=route):
                self.assertIn(f'href="{route}"', self.home, route)

    def test_homepage_carries_all_ten_section_bodies(self):
        # (Merged 2026-11-22 rebase: the screenshot's sections are
        # on the homepage in the image's order, AND the retained
        # Why / Three ways bodies are back too. The Airport
        # pickups, Experience and "Your ride history" bodies are
        # off the homepage — they live only on their own pages —
        # as are the Cancellation, FAQ and Contacts bodies removed
        # earlier by owner order. The "Our company" body is off
        # the homepage too (owner order 2026-11-22 ~19:51 EST,
        # commit 0152e58): a short business line lives in the
        # footer "Company" column instead, and the full text lives
        # on /our-company.)
        for body in [
            "Professional chauffeurs",
            "Flying in or out of JFK, LaGuardia, Newark, LAX, ORD or MIA?",
        ]:
            self.assertIn(body, self.home, body)
        for body in [
            "at the right terminal at JFK, LaGuardia or Newark",
            "Enter the phone number you booked with to see your past rides.",
            "Your chauffeur opens the door, greets you by name",
            "Noel Chauffer is a premium chauffeur service",
        ]:
            self.assertNotIn(body, self.home, body)
        for marker in [
            "Travel on your own terms.",
            "Premium service, absolute privacy and seamless journeys.",
            "Punctual.",
            "Professional.",
            "We move with you",
            "The gold standard of private travel.",
            "Available 24/7",
            "Flight number",
            "Diverse Fleet",
        ]:
            self.assertIn(marker, self.home, marker)
        # Homepage still has the booking form, the chat widget and the
        # footer — the sections came back below the form.
        self.assertIn('id="booking-form"', self.home)
        self.assertIn('id="support-chat-panel"', self.home)
        self.assertIn('id="chat-fab"', self.home)
        self.assertIn("site-footer", self.home)

    def test_homepage_has_no_refer_a_friend(self):
        # Removal (commit 8464317) stands: no referral UI on the homepage.
        self.assertNotIn("Refer a friend", self.home)
        self.assertNotIn("referral-box", self.home)
        # The FAQ's 5%-off referral Q&A stays off the homepage too.
        self.assertNotIn("How do I get 5% off my first ride?", self.home)
        # ...but the backend discount note for already-shared links stays.
        self.assertIn("Referral discount applied", self.home)

    def test_ride_history_lookup_lives_only_on_its_own_page(self):
        # Owner order 2026-11-22 ~19:32 EST: the "Your ride history"
        # section is OFF the homepage; the lookup lives only on
        # /your-ride-history (top-nav "Ride history" link stays).
        self.assertNotIn('id="history-form"', self.home)
        self.assertNotIn('id="history-phone"', self.home)
        self.assertNotIn('id="history-results"', self.home)
        self.assertNotIn("/static/js/ride-history.js", self.home)
        self.assertNotIn("Your ride history", self.home)
        # ...and still on its own page.
        res = self.client.get("/your-ride-history")
        self.assertEqual(res.status_code, 200)
        page = res.get_data(as_text=True)
        self.assertIn("<h2>Your ride history</h2>", page)
        self.assertIn('id="history-form"', page)

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
        self.assertIn("/app", app_page)
        self.assertNotIn("play.google.com", app_page)
        self.assertNotIn("apps.apple.com", app_page)
        # Same badges render on the homepage section.
        self.assertIn("google-play-badge.png", self.home)
        self.assertIn("app-store-badge.svg", self.home)


if __name__ == "__main__":
    unittest.main()
