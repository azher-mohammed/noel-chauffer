"""Headings cleanup (owner orders, voice call 2026-11-21 ~20:15 EST).

1. Homepage section headings must be CLEANER and slightly SMALLER
   (~15-20% smaller, still clearly readable as headings), with no
   underline (rule kept from commit 039a99a).
2. The text below the headings must be SIMPLE, plain wording — same
   facts, no complicated phrasing.
3. The page must NOT look very big ("ye page mere ko bahut bada nahi
   dikhna") — tighter section spacing makes the homepage compact.

Sizes (before -> after):
  .section h2          32px -> 26px, weight 500
  .airport-body h2     30px -> 25px, weight 500
  .app-band h2         36px -> 29px, weight 500
  .section padding     56px top -> 36px top
  .app-band-inner      64px -> 44px (36px on mobile)

Heading texts, links, button colour (#5b9bd5), the light-gold
"Chauffeur" wordmark and the white driver app are unchanged.

Run:  python -m unittest discover -s tests -v
"""

import re
import unittest
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
CSS = (REPO_DIR / "static" / "css" / "customer.css").read_text()
INDEX = (REPO_DIR / "static" / "index.html").read_text()

SIMPLE_COPY = {
    "static/airport-pickups.html": [
        "Add your flight number when you book.",
        "You get 60 minutes of free waiting time.",
    ],
    "static/why-ride-with-noel-chauffer.html": [
        "Polite, experienced drivers who know the roads and respect your time.",
        "Clean, comfortable, recent cars, ready for every ride.",
        "arrives on time, every time.",
    ],
    "static/experience.html": [
        "From booking to arrival, every detail is looked after.",
        "carries your luggage at pickup and drop-off.",
        "so your phone is full when you arrive.",
    ],
    "static/three-ways-to-ride.html": [
        "Add your flight number when you book, and take your time",
        "book by the hour.",
    ],
    "static/cancellation-and-waiting.html": [
        "After that, the ride is marked as a no-show.",
    ],
    "static/frequently-asked-questions.html": [
        "choose your ride, and pay by card.",
        "you do not get a refund.",
        "It is the car service NYC customers book for airport transfers, point-to-point rides and hourly hire.",
        "We also send the details to your phone and email.",
    ],
    "static/our-company.html": [
        "from booking to arrival.",
        "so you can just step in and relax.",
    ],
    "static/contacts.html": [
        "We reply within 24 hours.",
        "please add your pickup date and time.",
    ],
    "static/your-rides-in-your-pocket.html": [
        "No download, just open and go.",
    ],
}

# Wordy phrasing the owner asked to simplify away — must be gone.
GONE_PHRASES = [
    "so a slow baggage line never becomes a worry",
    "Experienced, courteous drivers",
    "arrives in good time, every time",
    "From the moment you book to the moment you arrive",
    "carries your luggage at both ends",
    "so you arrive with a full battery",
    "go where the day takes you",
    "before a ride is marked as a no-show",
    "choose your experience, and pay by card",
    "The details are also sent to your phone and email",
    "so you can simply step in and relax",
    "The team replies within 24 hours. For anything about a ride",
]


def _rule(selector):
    """Return the body of the first CSS rule matching selector, or ''."""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    return m.group(1) if m else ""


class TestHeadingsClean(unittest.TestCase):
    def test_section_h2_smaller_and_lighter(self):
        rule = _rule(".section h2")
        self.assertIn("font-size: 26px", rule)
        self.assertIn("font-weight: 500", rule)
        self.assertNotIn("font-size: 32px", rule)

    def test_airport_body_h2_smaller_and_lighter(self):
        rule = _rule(".section .airport-body h2")
        self.assertIn("font-size: 25px", rule)
        self.assertIn("font-weight: 500", rule)
        self.assertNotIn("font-size: 30px", rule)

    def test_app_band_h2_smaller_and_lighter(self):
        rule = _rule(".app-band h2")
        self.assertIn("font-size: 29px", rule)
        self.assertIn("font-weight: 500", rule)
        self.assertNotIn("font-size: 36px", rule)

    def test_headings_still_have_no_underline(self):
        # Rule from commit 039a99a — homepage heading links look like
        # plain clean headings, never link-blue, never underlined.
        self.assertIn(
            ".section h2 a, .app-band h2 a { color: inherit; text-decoration: none; }",
            CSS,
        )

    def test_section_spacing_tighter_so_page_looks_compact(self):
        self.assertIn("padding: 36px 20px 6px;", _rule(".section"))
        self.assertNotIn("padding: 56px 20px 8px;", CSS)
        self.assertIn("padding: 44px 20px;", _rule(".app-band-inner"))
        self.assertNotIn("padding: 64px 20px;", CSS)
        self.assertIn("margin: 0 0 18px;", _rule(".section .intro"))

    def test_heading_texts_and_links_unchanged(self):
        # (The app-band heading "Your rides, in your pocket." was
        # removed from the homepage by owner order 2026-11-22; its
        # separate page keeps it. The Cancellation, FAQ and Contacts
        # headings were removed the same day, and "Your ride history"
        # the same evening (~19:32 EST) — those sections are off
        # the homepage entirely and live only on their own pages.
        # The "Our company" heading was removed the same way by
        # owner order 2026-11-22 ~19:51 EST — the section is off
        # the homepage and a short business line lives in the
        # footer "Company" column instead; the /our-company page
        # keeps the full text.)
        for text, href in [
            ("Airport pickups, without the rush.", "/airport-pickups"),
            ("Sit back and enjoy the ride.", "/experience"),
            ("Why ride with Noel Chauffer", "/why-ride-with-noel-chauffer"),
            ("Three ways to ride", "/three-ways-to-ride"),
        ]:
            self.assertIn(f'<h2><a href="{href}">{text}</a></h2>', INDEX)

    def test_button_colour_and_wordmark_untouched(self):
        self.assertIn("#5b9bd5", CSS)  # very light blue buttons
        self.assertNotIn("#0b5fff", CSS)
        self.assertNotIn("#004fe0", CSS)

    def test_simple_copy_present_on_section_pages(self):
        for rel, fragments in SIMPLE_COPY.items():
            html = (REPO_DIR / rel).read_text()
            for frag in fragments:
                self.assertIn(frag, html, f"{frag!r} missing from {rel}")

    def test_wordy_phrasing_gone(self):
        pages = [REPO_DIR / rel for rel in SIMPLE_COPY]
        for phrase in GONE_PHRASES:
            for page in pages:
                self.assertNotIn(
                    phrase, page.read_text(), f"{phrase!r} still in {page.name}"
                )


if __name__ == "__main__":
    unittest.main()
