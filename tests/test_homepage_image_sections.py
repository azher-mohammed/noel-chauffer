"""Homepage below the booking form matches the owner's screenshot
exactly (owner order, voice call 2026-11-22 ~20:09 EST: "chalo theek
hai karo").

Spec image: workspace/user/files/274AC966-630D-4976-B0F9-552684D23B41-photo-66B9CE5F-35A9-488F-839B-0EA831224AD8.jpg
(read at 8x/16x — the screenshot is only 127px wide, so the small
text was read from enlarged crops).

Sections below the form, in the image's order:
1. "Travel on your own terms." + "Premium service, absolute privacy
   and seamless journeys."
2. "Punctual. Professional." — car-interior photo beside the heading,
   "Our hand-selected chauffeurs prioritise your schedule, route and
   comfort, ensuring you arrive refreshed for what matters." and a
   "Learn more" button. (The image says "Punctual", not "Personal",
   and the button says "Learn more", not "Book now".)
3. "We move with you" — light-blue band with the two store badges.
4. Airport meet-and-greet photo.
5. "The gold standard of private travel." + the same chauffeur line
   + three cards: "Available 24/7" / "Flight number" /
   "Diverse Fleet". (The image's middle card says "Flight Tracking",
   but the site has no live flight tracking yet — the repo's
   test_flights guard forbids that claim in the UI — so the card
   is labelled "Flight number", the real feature: add it when you
   book and the chauffeur adjusts to your schedule.)

The booking form is untouched. The footer keeps its live column
order (Airport transfers, Where we drive, Guides, Services,
Company) — the image shows the old footer layout because the
screenshot is a stale render; the footer is NOT reverted.

The old below-form sections "The experience", "Airport pickups",
"Our company" and "Your ride history" are gone from the homepage
(their separate pages still exist, reached from the top nav). The
Why / Three ways sections were RETAINED on the homepage. The
"Our company" section went off the homepage with the footer move
(commit 0152e58, owner 2026-11-22 ~19:51 EST): a short business
line lives in the footer "Company" column instead, and the
top-nav "Our company" link stays.

Run:  python -m unittest discover -s tests -v
"""

import re
import unittest
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
CSS = (REPO_DIR / "static" / "css" / "customer.css").read_text()
INDEX = (REPO_DIR / "static" / "index.html").read_text()


def _rule(selector):
    return " ".join(
        m.group(1)
        for m in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    )


class TestHomepageImageSections(unittest.TestCase):
    def test_new_sections_present_in_image_order(self):
        markers = [
            "Travel on your own terms.",
            "Punctual.",
            "Professional.",
            "We move with you",
            "The gold standard of private travel.",
            "Available 24/7",
            ">Flight number</h3>",  # h3 carries data-i18n now
            "Diverse Fleet",
        ]
        positions = [INDEX.index(m) for m in markers]
        self.assertEqual(positions, sorted(positions), markers)

    def test_image_wording_exact(self):
        self.assertIn(
            "Premium service, absolute privacy and seamless journeys.",
            INDEX,
        )
        self.assertIn(
            "Our hand-selected chauffeurs prioritise your schedule, route and comfort, ensuring you arrive refreshed for what matters.",
            INDEX,
        )
        self.assertIn(
            "Our hand-selected chauffeurs prioritise your schedule, route, and comfort, ensuring you arrive refreshed for what matters.",
            INDEX,
        )
        self.assertIn("Book anytime, anywhere.", INDEX)
        self.assertIn("We adjust to your schedule.", INDEX)
        self.assertIn("From executive sedans to spacious SUVs.", INDEX)

    def test_old_sections_gone_from_homepage(self):
        for gone in [
            'id="airports"',
            'id="experience"',
            'id="history"',
            "Airport pickups, without the rush.",
            "Sit back and enjoy the ride.",
            "Your ride history",
            "Enter the phone number you booked with to see your past rides.",
            'id="history-form"',
            'id="history-phone"',
            "history-results",
            'id="company"',
            "Noel Chauffer is a premium chauffeur service",
        ]:
            self.assertNotIn(gone, INDEX, gone)
        # Why / Three ways sections were RETAINED on the homepage
        # by the 2026-11-22 rebase (see the module docstring);
        # their heading links to the separate pages stay too.
        # The "Our company" SECTION is gone (footer move, commit
        # 0152e58) — only the top-nav link stays.
        for kept in [
            'id="why"',
            'id="ride-types"',
            "Why ride with Noel Chauffer",
            "Three ways to ride",
        ]:
            self.assertIn(kept, INDEX, kept)
        self.assertRegex(INDEX, r'<a href="/our-company"[^>]*>Our company</a>')

    def test_photos_reused_once_each(self):
        # Interior photo beside "Punctual. Professional."; airport
        # meet-and-greet photo above the gold-standard heading.
        self.assertEqual(INDEX.count("cabin.jpg"), 1)
        self.assertEqual(INDEX.count("airport.jpg"), 1)
        self.assertIn('src="/static/img/cabin.jpg"', INDEX)
        self.assertIn('src="/static/img/airport.jpg"', INDEX)

    def test_learn_more_goes_to_why_ride_page(self):
        self.assertRegex(
            INDEX,
            r'<a class="btn-ghost" href="/why-ride-with-noel-chauffer"[^>]*>Learn more</a>',
        )

    def test_app_band_heading_and_badges(self):
        self.assertIn(">We move with you</h2>", INDEX)  # h2 carries data-i18n="home.move" now
        self.assertIn('href="/app"><img src="/static/img/google-play-badge.png"', INDEX)
        self.assertIn('href="/app"><img src="/static/img/app-store-badge.svg"', INDEX)
        self.assertNotIn("Open the app", INDEX)
        self.assertNotIn("Your rides, in your pocket", INDEX)
        self.assertNotIn("Book your ride, follow your chauffeur", INDEX)
        self.assertEqual(INDEX.count('height="48"'), 2)

    def test_bands_and_cards_use_pale_blue(self):
        self.assertIn("var(--sky-soft)", _rule(".travel-terms"))
        self.assertIn("var(--sky-soft)", _rule(".move-band"))
        self.assertIn("var(--sky-soft)", _rule(".gold-card"))

    def test_booking_form_and_footer_untouched(self):
        self.assertIn('id="booking-form"', INDEX)
        self.assertIn('id="bk-pickup"', INDEX)
        self.assertIn('id="class-signin"', INDEX)
        self.assertIn("site-footer", INDEX)
        # Live footer column order (commit ed4ce3e) stands, plus the Terms
        # column added after Company (footer + /terms page, owner
        # 2026-11-23: "Terms" links to /terms, "Privacy Policy" under it).
        # The Company heading is a link to /our-company (owner
        # 2026-11-23), so the heading text may sit inside an <a>.
        cols = re.findall(
            r"<h3[^>]*>(?:<a[^>]*>)?([^<]+)(?:</a>)?</h3>",
            INDEX.split("footer-cols")[1],
        )
        self.assertEqual(
            cols,
            ["Airport transfers", "Where we drive", "Guides", "Services", "Company", "Terms"],
        )
        # Top-nav Ride history link stays.
        self.assertRegex(INDEX, r'<a href="/your-ride-history"[^>]*>Ride history</a>')


if __name__ == "__main__":
    unittest.main()
