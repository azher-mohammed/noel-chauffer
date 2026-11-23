"""Tests for the driver route 'Pick up' / 'Drop off' labels.

Owner decision 2026-11-17 (voice call): looking at a job card showing
'Terminal 1 Arrivals, Queens ... -> Stamford...', the owner asked for
small labels written beside each address inside the app so pickup vs
drop-off is obvious at a glance. Explicitly NOT a pickup note — just
the words beside the addresses, on the offer card and the trip screen.
Hourly rides have no drop-off, so only the pickup label shows.

Owner decision 2026-11-23 (voice call, with a screenshot of the
offers list): the two addresses still ran together on one line
('Pick up <addr> -> Drop off <addr>'), so pickup and drop-off are
now two separate blocks — each leg its own block with a down arrow
on its own line between them. Full address text is kept for both.

Run:  python -m unittest discover -s tests -v
"""

import os
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class RouteLabelsCase(unittest.TestCase):
    def test_driver_js_has_exact_label_strings(self):
        driver_js = read("static/js/driver.js")
        self.assertIn('<span class="route-label">Pick up</span>', driver_js)
        self.assertIn('<span class="route-label">Drop off</span>', driver_js)

    def test_route_helper_used_by_offer_card_and_trip_screen(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("function routeHtml(pickup, dropoff)", driver_js)
        # Both route render paths go through the shared helper.
        self.assertIn("routeHtml(o.pickup, o.dropoff)", driver_js)
        self.assertIn("routeHtml(t.pickup, t.dropoff)", driver_js)

    def test_drop_off_label_only_when_dropoff_present(self):
        driver_js = read("static/js/driver.js")
        helper = driver_js[driver_js.index("function routeHtml"):]
        helper = helper[:helper.index("}\n", helper.index("if (dropoff)")) + 2]
        self.assertIn("if (dropoff)", helper)
        # The pickup label is unconditional; the drop-off label is
        # inside the conditional, so hourly rides show pickup only.
        self.assertLess(helper.index("Pick up"), helper.index("if (dropoff)"))
        self.assertLess(helper.index("if (dropoff)"), helper.index("Drop off"))

    def test_route_legs_are_separate_blocks_with_arrow_between(self):
        driver_js = read("static/js/driver.js")
        helper = driver_js[driver_js.index("function routeHtml"):]
        helper = helper[:helper.index("}\n", helper.index("if (dropoff)")) + 2]
        # Each leg is its own block; the inline '->' separator is gone.
        self.assertIn('<div class="route-leg">', helper)
        self.assertIn('<div class="route-sep"', helper)
        self.assertIn("↓", helper)
        self.assertNotIn("→", helper)
        # Addresses are still escaped, full text kept.
        self.assertIn('esc(pickup || "")', helper)
        self.assertIn("esc(dropoff)", helper)

    def test_route_label_css_present_and_not_uppercased(self):
        css = read("static/css/driver.css")
        self.assertIn(".route-label", css)
        rule = css[css.index(".route-label"):]
        rule = rule[:rule.index("}")]
        self.assertIn("font-size: 12px", rule)
        self.assertNotIn("text-transform", rule)

    def test_route_legs_and_separator_have_block_css(self):
        css = read("static/css/driver.css")
        self.assertIn(".route-leg", css)
        self.assertIn(".route-sep", css)
        leg_rule = css[css.index(".route-leg"):]
        leg_rule = leg_rule[:leg_rule.index("}")]
        self.assertIn("display: block", leg_rule)
        sep_rule = css[css.index(".route-sep"):]
        sep_rule = sep_rule[:sep_rule.index("}")]
        self.assertIn("display: block", sep_rule)


if __name__ == "__main__":
    unittest.main()
