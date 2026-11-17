"""Tests for staged driver navigation on the trip screen.

Owner report 2026-11-17 (voice call): after accepting a job (JFK
Terminal 1 -> Stamford), while heading to the pickup, the app's
navigation took him straight to the DROP-OFF (Stamford) instead of
the PICKUP first. Required (Uber-driver-style): from accept until
the customer is picked up, the Google Maps and Waze links navigate
TO THE PICKUP from the driver's current location; only after pickup
do they navigate to the drop-off. Hourly rides have no drop-off, so
after pickup the links are hidden rather than pointing anywhere.

The staging keys off the trip screen's existing stage state:
stageIndex counts completed stages (0 accepted, 1 heading to pickup,
2 arrived, 3 picked up / in progress). The offer card is untouched:
its links keep previewing the whole trip (pickup -> drop-off).

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

    def test_google_nav_url_has_destination_only_no_origin(self):
        driver_js = read("static/js/driver.js")
        helper = extract_function(
            driver_js, "function tripNavLinksHtml(stageIndex, pickup, dropoff)")
        # Destination with no origin: Google routes from the driver's
        # current location. An origin=<pickup> would show the
        # pickup->drop-off route instead — the reported bug.
        self.assertIn(
            '"https://www.google.com/maps/dir/?api=1&destination="'
            " + encodeURIComponent(dest)", helper)
        self.assertNotIn("origin=", helper)

    def test_waze_nav_url_points_at_destination(self):
        driver_js = read("static/js/driver.js")
        helper = extract_function(
            driver_js, "function tripNavLinksHtml(stageIndex, pickup, dropoff)")
        self.assertIn(
            '"https://waze.com/ul?q=" + encodeURIComponent(dest)'
            ' + "&navigate=yes"', helper)

    def test_no_links_when_no_destination(self):
        # Hourly after pickup: no drop-off, so nothing to navigate to.
        driver_js = read("static/js/driver.js")
        helper = extract_function(
            driver_js, "function tripNavLinksHtml(stageIndex, pickup, dropoff)")
        self.assertIn('if (!dest) return "";', helper)

    def test_trip_screen_uses_staged_links_and_restages_on_advance(self):
        driver_js = read("static/js/driver.js")
        # The trip screen renders the staged links...
        self.assertIn("function renderTripNavLinks()", driver_js)
        self.assertIn("tripNavLinksHtml(state.stageIndex, t.pickup, t.dropoff)",
                      driver_js)
        # ...on every trip render AND on every stage advance (the
        # stage button calls renderStages, not renderTrip, so the
        # links must re-stage there or "Start trip" would leave them
        # pointing at the pickup).
        stages = driver_js[driver_js.index("function renderStages()"):]
        stages = stages[:stages.index("function refreshNoShowButton()")]
        self.assertIn("renderTripNavLinks();", stages)
        # The trip screen no longer uses the un-staged payload URLs.
        self.assertNotIn("esc(t.route_url)", driver_js)
        self.assertNotIn("esc(t.route_waze_url)", driver_js)

    def test_offer_card_links_unchanged(self):
        driver_js = read("static/js/driver.js")
        offers = driver_js[driver_js.index("function renderOffers"):]
        offers = offers[:offers.index("function respondToOffer")]
        self.assertIn('esc(o.route_url)', offers)
        self.assertIn('esc(o.route_waze_url)', offers)

    @unittest.skipUnless(shutil.which("node"), "node required to execute the JS helpers")
    def test_staged_urls_execute_correctly(self):
        """Run the REAL helpers from driver.js under node: every
        stage, one-way and hourly, asserting the exact URLs."""
        driver_js = read("static/js/driver.js")
        esc = extract_function(driver_js, "function esc(s)")
        dest_fn = extract_function(
            driver_js, "function tripNavDestination(stageIndex, pickup, dropoff)")
        html_fn = extract_function(
            driver_js, "function tripNavLinksHtml(stageIndex, pickup, dropoff)")
        harness = "\n".join([esc, dest_fn, html_fn, _NODE_DRIVER])
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
        self.assertEqual(result["passed"], 12)


_NODE_DRIVER = """
var failures = [];
var passed = 0;
function check(name, cond, detail) {
  if (cond) { passed++; }
  else { failures.push(name + (detail ? ": " + detail : "")); }
}
function hrefs(html) {
  var out = [], m, re = /href="([^"]*)"/g;
  while ((m = re.exec(html))) out.push(m[1].replace(/&amp;/g, "&"));
  return out;
}
function expectDest(stage, pickup, dropoff, want) {
  var html = tripNavLinksHtml(stage, pickup, dropoff);
  var hs = hrefs(html);
  var google = "https://www.google.com/maps/dir/?api=1&destination=" + encodeURIComponent(want);
  var waze = "https://waze.com/ul?q=" + encodeURIComponent(want) + "&navigate=yes";
  check("stage " + stage + " links to " + want,
    hs.length === 2 && hs[0] === google && hs[1] === waze && html.indexOf("origin=") === -1,
    JSON.stringify(hs));
  check("stage " + stage + " keeps both link labels",
    html.indexOf("Google Maps") !== -1 && html.indexOf("Waze") !== -1, html);
}
var PICKUP = "Terminal 1 Arrivals, Queens, NY 11430";
var DROPOFF = "Stamford, CT";
expectDest(0, PICKUP, DROPOFF, PICKUP);
expectDest(1, PICKUP, DROPOFF, PICKUP);
expectDest(2, PICKUP, DROPOFF, PICKUP);
expectDest(3, PICKUP, DROPOFF, DROPOFF);
// Hourly: no drop-off. Before pickup the links go to the pickup;
// after pickup there is nothing to navigate to, so no links at all.
expectDest(0, "Central Park, New York", "", "Central Park, New York");
check("hourly after pickup hides links",
  tripNavLinksHtml(3, "Central Park, New York", "") === "" &&
  tripNavLinksHtml(3, "Central Park, New York", null) === "", "links rendered");
// Addresses with special characters are URL-encoded, and the & in
// the query string is HTML-escaped in the href attribute.
var tricky = tripNavLinksHtml(0, "A & B Street", "C");
check("ampersand escaped in link HTML and address encoded",
  tricky.indexOf("api=1&amp;destination=") !== -1 &&
  tricky.indexOf("A%20%26%20B%20Street") !== -1, tricky);
console.log(JSON.stringify({passed: passed, failed: failures}));
"""


if __name__ == "__main__":
    unittest.main()
