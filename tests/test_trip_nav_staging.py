"""Tests that the driver trip screen shows NO Google Maps / Waze links.

Owner decision 2026-11-20 (voice call: "mere ko achha nahi dikh
raha, nikal do" — the links at the top of the driver trip screen):
the Google Maps ↗ / Waze ↗ links at the top of the trip screen
("Current trip", above the stage buttons) are REMOVED. Only the
screen is touched — the offer-card links stay, and the navigation
chooser that pops on "Head to pickup" / "Start trip" stays and
still navigates to the staged destination (pickup until picked up,
then drop-off), via tripNavDestination.

Run:  python -m unittest discover -s tests -v
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def extract_function(source, signature):
    """Extract a top-level `function NAME(...) {...}` body from JS
    source by balanced-brace scanning. The extracted helpers contain
    no braces inside strings, so a plain counter is exact."""
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unbalanced braces in " + signature)


class TripNavStagingCase(unittest.TestCase):
    def test_destination_helper_keys_off_stage_index(self):
        # tripNavDestination still exists: the navigation chooser
        # reuses it to pick pickup vs drop-off.
        driver_js = read("static/js/driver.js")
        self.assertIn(
            "function tripNavDestination(stageIndex, pickup, dropoff)", driver_js)
        helper = extract_function(
            driver_js, "function tripNavDestination(stageIndex, pickup, dropoff)")
        # Before pickup (stages 0-2) -> the pickup; from stage 3
        # (picked up) on -> the drop-off.
        self.assertIn("if (stageIndex < 3) return pickup || null;", helper)
        self.assertIn("return dropoff || null;", helper)
        self.assertLess(helper.index("stageIndex < 3"),
                        helper.index("return dropoff"))

    def test_trip_screen_has_no_top_route_links(self):
        # Owner 2026-11-20: no Google Maps / Waze links at the top
        # of the trip screen. The helper that built them, the
        # renderer that wrote them into the page, and the container
        # element are all gone.
        driver_js = read("static/js/driver.js")
        self.assertNotIn("tripNavLinksHtml", driver_js)
        self.assertNotIn("renderTripNavLinks", driver_js)
        self.assertNotIn("trip-route-link", driver_js)
        html = read("static/driver.html")
        self.assertNotIn('id="trip-route-link"', html)
        # Neither the trip render nor the stage render may call the
        # removed renderer.
        render_trip = driver_js[driver_js.index("function renderTrip()"):]
        render_trip = render_trip[:render_trip.index("/* ---------- Arrival")]
        self.assertNotIn("renderTripNavLinks", render_trip)
        stages = driver_js[driver_js.index("function renderStages()"):]
        stages = stages[:stages.index("function refreshNoShowButton()")]
        self.assertNotIn("renderTripNavLinks", stages)

    def test_offer_card_links_unchanged(self):
        driver_js = read("static/js/driver.js")
        offers = driver_js[driver_js.index("function renderOffers"):]
        offers = offers[:offers.index("function respondToOffer")]
        self.assertIn('esc(o.route_url)', offers)
        self.assertIn('esc(o.route_waze_url)', offers)

    def test_chooser_still_uses_staged_destination(self):
        # The chooser is now the driver's only navigation route, so
        # it must still stage pickup vs drop-off.
        driver_js = read("static/js/driver.js")
        helper = extract_function(driver_js, "function maybeShowNavChooser(advancedStage)")
        self.assertIn(
            "tripNavDestination(state.stageIndex, t.pickup, t.dropoff)", helper)

    @unittest.skipUnless(shutil.which("node"), "node required to execute the JS helpers")
    def test_staged_destination_executes_correctly(self):
        """Run the REAL tripNavDestination from driver.js under node:
        every stage, one-way and hourly."""
        driver_js = read("static/js/driver.js")
        dest_fn = extract_function(
            driver_js, "function tripNavDestination(stageIndex, pickup, dropoff)")
        harness = "\n".join([dest_fn, _NODE_DRIVER])
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(harness)
            path = fh.name
        try:
            proc = subprocess.run(["node", path], capture_output=True,
                                  text=True, timeout=30)
        finally:
            os.unlink(path)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(result["failed"], [], str(result))
        self.assertEqual(result["passed"], 6)


_NODE_DRIVER = """
var failures = [];
var passed = 0;
function check(name, cond, detail) {
  if (cond) { passed++; }
  else { failures.push(name + (detail ? ": " + detail : "")); }
}
var PICKUP = "Terminal 1 Arrivals, Queens, NY 11430";
var DROPOFF = "Stamford, CT";
check("stage 0 destination is the pickup",
  tripNavDestination(0, PICKUP, DROPOFF) === PICKUP);
check("stage 1 destination is the pickup",
  tripNavDestination(1, PICKUP, DROPOFF) === PICKUP);
check("stage 2 destination is the pickup",
  tripNavDestination(2, PICKUP, DROPOFF) === PICKUP);
check("stage 3 destination is the drop-off",
  tripNavDestination(3, PICKUP, DROPOFF) === DROPOFF);
// Hourly: no drop-off. Before pickup the destination is the
// pickup; after pickup there is nothing to navigate to.
check("hourly before pickup goes to the pickup",
  tripNavDestination(0, "Central Park, New York", "") === "Central Park, New York");
check("hourly after pickup has no destination",
  tripNavDestination(3, "Central Park, New York", "") === null &&
  tripNavDestination(3, "Central Park, New York", null) === null);
console.log(JSON.stringify({passed: passed, failed: failures}));
"""


if __name__ == "__main__":
    unittest.main()
