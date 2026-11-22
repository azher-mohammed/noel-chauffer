"""Homepage alignment (owner order, voice call 2026-11-22 ~05:51 EST).

Owner's full-page screenshot of noelchauffer.com showed the homepage
sections drifting up and down — text wandering off its line, not a
professional look. His order: "sab ek ek line mein hi aana chahiye"
— everything must come in one line each.

Fixes pinned here:
1. App band: "Open the app" button + Google Play + App Store badges
   sit in ONE straight flex row, vertically centred — the badges
   never stack or sit at different heights (before, the two badges
   were bare inline images with no layout rule at all, so they
   staggered on the text baseline).
2. Ride-type cards: equal-height flex columns; the "Learn more" link
   is pushed to the bottom of its card, so all three links sit on
   one straight line despite different text lengths.
3. Section headings: tight line-height (1.25) so a heading wrapping
   to two lines still reads as one clean block.
4. Footer columns: all headings start on one straight baseline on
   desktop; on mobile the columns stack one below the other instead
   of a ragged two-column grid.

Untouched (guarded): heading sizes (26px / 25px / 29px, per
test_headings_clean), light-blue buttons #5b9bd5, WhatsApp-green
Chat with us #25D366, referral UI stays removed, prices and the
breakdown, and the 10 separate section pages.

Run:  python -m unittest discover -s tests -v
"""

import re
import unittest
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
CSS = (REPO_DIR / "static" / "css" / "customer.css").read_text()
INDEX = (REPO_DIR / "static" / "index.html").read_text()


def _rule(selector):
    """Return all CSS rule bodies matching selector, joined.

    Some selectors are defined twice (an early base rule plus the
    later alignment block at the end of the file, which wins on
    equal specificity) — so every match counts, not just the first.
    """
    return " ".join(
        m.group(1)
        for m in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    )


class TestHomepageAlignment(unittest.TestCase):
    def test_app_actions_one_straight_row(self):
        # Button + badges wrapped in a single flex row, vertically centred.
        self.assertIn('<div class="app-actions">', INDEX)
        actions = _rule(".app-actions")
        self.assertIn("display: flex", actions)
        self.assertIn("align-items: center", actions)
        # The button and the badges live inside that one row.
        m = re.search(
            r'<div class="app-actions">(.*?)</div>\s*</div>', INDEX, re.S
        )
        self.assertIsNotNone(m, "app-actions wrapper not found")
        inner = m.group(1)
        self.assertIn('href="/app">Open the app</a>', inner)
        self.assertIn('class="store-badges"', inner)
        self.assertIn("google-play-badge.png", inner)
        self.assertIn("app-store-badge.svg", inner)

    def test_store_badges_level_with_each_other(self):
        badges = _rule(".store-badges")
        self.assertIn("display: flex", badges)
        self.assertIn("align-items: center", badges)
        # Badge links are flex boxes with no text baseline to sit on.
        link = _rule(".store-badges a")
        self.assertIn("display: flex", link)
        self.assertIn("line-height: 0", link)
        # Both badges render at the same height, as block images.
        img = _rule(".store-badges img")
        self.assertIn("display: block", img)
        self.assertIn("height: 48px", img)
        self.assertIn('height="48"', INDEX)

    def test_ride_type_links_bottom_aligned(self):
        self.assertEqual(INDEX.count('class="card-link"'), 3)
        card = _rule(".exp-card")
        self.assertIn("display: flex", card)
        self.assertIn("flex-direction: column", card)
        body = _rule(".exp-body")
        self.assertIn("display: flex", body)
        self.assertIn("flex-direction: column", body)
        self.assertIn("flex: 1", body)
        link = _rule(".exp-body .card-link")
        self.assertIn("margin-top: auto", link)

    def test_section_headings_one_clean_block(self):
        self.assertIn("line-height: 1.25", _rule(".section h2"))
        self.assertIn("line-height: 1.25", _rule(".section .airport-body h2"))
        self.assertIn("line-height: 1.25", _rule(".app-band h2"))

    def test_footer_columns_aligned(self):
        cols = _rule(".footer-cols")
        self.assertIn("align-items: start", cols)
        # Mobile: single column, one footer column below the other —
        # the old ragged two-column grid must be gone.
        mobile = re.findall(
            r"@media \(max-width: 860px\) \{\s*\.footer-cols \{([^}]*)\}",
            CSS,
        )
        self.assertTrue(mobile, "no mobile footer-cols rule found")
        self.assertIn("grid-template-columns: 1fr", mobile[-1])
        self.assertNotIn("1fr 1fr", mobile[-1])

    def test_heading_sizes_unchanged(self):
        self.assertIn("font-size: 26px", _rule(".section h2"))
        self.assertIn("font-size: 25px", _rule(".section .airport-body h2"))
        self.assertIn("font-size: 29px", _rule(".app-band h2"))

    def test_colours_referral_and_prices_untouched(self):
        self.assertIn("#5b9bd5", CSS)  # very light blue buttons
        self.assertIn("#25D366", CSS)  # WhatsApp-green Chat with us
        self.assertNotIn("Refer a friend", INDEX)
        self.assertNotIn("referral-box", INDEX)
        # Section pages still linked from the homepage headings.
        for href in [
            "/airport-pickups",
            "/your-rides-in-your-pocket",
            "/experience",
            "/why-ride-with-noel-chauffer",
            "/three-ways-to-ride",
            "/cancellation-and-waiting",
            "/frequently-asked-questions",
            "/our-company",
            "/contacts",
            "/your-ride-history",
        ]:
            self.assertIn(f'href="{href}"', INDEX)


if __name__ == "__main__":
    unittest.main()
