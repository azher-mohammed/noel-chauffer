"""Tests for the driver navigation chooser on stage advance.

Owner request 2026-11-17 (voice call): when he taps "Head to
pickup", Maps should open directly to the pickup, with a Waze or
Google Maps option. So the two stage advances that start a leg —
"Head to pickup" (en_route) and "Start trip" (start) — pop a small
chooser offering Google Maps and Waze. The chooser opens
navigation to the PICKUP on the first and to the DROP-OFF on the
second, reusing the staged destination helper. "Arrived" and
completion never trigger it, dismissing it changes nothing (the
stage has already advanced), and hourly rides never get a drop-off
chooser because they have no drop-off. The trip-screen top links
were removed (owner 2026-11-20), so this chooser is now the
driver's only navigation route; the embedded map stays removed.
Owner order 2026-11-23 (voice call, "Not now nahi rehna"): the
chooser has NO "Not now" button — the driver picks Google Maps
or Waze (tapping outside the card still dismisses it).

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


class NavChooserCase(unittest.TestCase):
    def test_chooser_urls_are_destination_only(self):
        driver_js = read("static/js/driver.js")
        helper = extract_function(driver_js, "function navChooserUrls(dest)")
        # Destination with no origin: the app routes from the
        # driver's current location, exactly like the staged
        # navigation destination. An origin would route pickup->drop-off.
        self.assertIn(
            '"https://www.google.com/maps/dir/?api=1&destination="'
            " + encodeURIComponent(dest)", helper)
        self.assertIn(
            '"https://waze.com/ul?q=" + encodeURIComponent(dest)'
            ' + "&navigate=yes"', helper)
        self.assertNotIn("origin=", helper)

    def test_chooser_suppressed_without_destination(self):
        # Hourly after pickup: no drop-off, so no chooser at all.
        driver_js = read("static/js/driver.js")
        helper = extract_function(driver_js, "function showNavChooser(dest, title)")
        self.assertIn("if (!dest) return;", helper)

    def test_chooser_only_on_heading_and_start_transitions(self):
        driver_js = read("static/js/driver.js")
        helper = extract_function(driver_js, "function maybeShowNavChooser(advancedStage)")
        # The staged destination helper decides pickup vs drop-off,
        # so the chooser can never point at the wrong leg.
        self.assertIn(
            "tripNavDestination(state.stageIndex, t.pickup, t.dropoff)", helper)
        self.assertIn('if (advancedStage === "en_route")', helper)
        self.assertIn('showNavChooser(dest, "Navigate to pickup");', helper)
        self.assertIn('else if (advancedStage === "start")', helper)
        self.assertIn('showNavChooser(dest, "Navigate to drop-off");', helper)
        # No other stage may trigger the chooser.
        self.assertNotIn('"arrived"', helper)
        self.assertNotIn('"complete"', helper)

    def test_stage_button_triggers_chooser_after_advance(self):
        driver_js = read("static/js/driver.js")
        handler = driver_js[driver_js.index('$("trip-next-btn").addEventListener'):]
        handler = handler[:handler.index('$("trip-cancel-btn").addEventListener')]
        # The stage advances first (state + re-render), and only then
        # does the chooser appear — dismissing it cannot undo the
        # advance, and a failed save never shows it (the handler
        # returns early on !res.ok, before the increment).
        self.assertIn("state.stageIndex++;", handler)
        self.assertIn("renderStages();", handler)
        self.assertIn("maybeShowNavChooser(current);", handler)
        self.assertLess(handler.index("state.stageIndex++;"),
                        handler.index("maybeShowNavChooser(current);"))
        self.assertLess(handler.index("renderStages();"),
                        handler.index("maybeShowNavChooser(current);"))

    def test_chooser_opens_from_tap_handler(self):
        # The external URL must open from the chooser button's own
        # tap handler — a direct user gesture — or mobile browsers
        # block the popup.
        driver_js = read("static/js/driver.js")
        helper = extract_function(driver_js, "function showNavChooser(dest, title)")
        self.assertIn('$("nav-chooser-google").onclick = function ()', helper)
        self.assertIn('window.open(urls.google, "_blank", "noopener");', helper)
        self.assertIn('$("nav-chooser-waze").onclick = function ()', helper)
        self.assertIn('window.open(urls.waze, "_blank", "noopener");', helper)

    def test_chooser_dismiss_wiring(self):
        driver_js = read("static/js/driver.js")
        # Owner order 2026-11-23 ("Not now nahi rehna"): NO "Not
        # now" button and no wiring for it. Tapping outside the
        # card still dismisses, without touching the trip.
        self.assertNotIn("nav-chooser-close", driver_js)
        self.assertNotIn(
            '$("nav-chooser-close").addEventListener("click", hideNavChooser);',
            driver_js)
        self.assertIn(
            '$("nav-chooser-overlay").addEventListener("click", function (e) {',
            driver_js)
        self.assertIn(
            'if (e.target === $("nav-chooser-overlay")) hideNavChooser();',
            driver_js)
        self.assertIn("function hideNavChooser() {", driver_js)
        self.assertIn('hide($("nav-chooser-overlay"));', driver_js)

    def test_chooser_overlay_markup_and_styles(self):
        html = read("static/driver.html")
        self.assertIn('id="nav-chooser-overlay"', html)
        self.assertIn('class="nav-chooser-overlay hidden"', html)
        self.assertIn('id="nav-chooser-title"', html)
        self.assertIn('id="nav-chooser-dest"', html)
        self.assertIn('id="nav-chooser-google"', html)
        self.assertIn('id="nav-chooser-waze"', html)
        self.assertIn(">Google Maps<", html)
        self.assertIn(">Waze<", html)
        # Owner order 2026-11-23: no "Not now" button anywhere.
        self.assertNotIn('id="nav-chooser-close"', html)
        self.assertNotIn(">Not now<", html)
        css = read("static/css/driver.css")
        self.assertIn(".nav-chooser-overlay", css)
        self.assertIn(".nav-chooser-card", css)
        # The trip-screen top links are gone (owner 2026-11-20):
        # no container element in the page, no renderer in the JS.
        self.assertNotIn('id="trip-route-link"', html)
        driver_js = read("static/js/driver.js")
        self.assertNotIn("function renderTripNavLinks()", driver_js)
        self.assertNotIn("tripNavLinksHtml", driver_js)

    def test_trip_end_hides_chooser(self):
        driver_js = read("static/js/driver.js")
        end = driver_js[driver_js.index("function endTrip()"):]
        end = end[:end.index("/* ---------- Location sharing")]
        self.assertIn("hideNavChooser();", end)

    @unittest.skipUnless(shutil.which("node"), "node required to execute the JS helpers")
    def test_nav_chooser_urls_execute_correctly(self):
        """Run the REAL helpers from driver.js under node: staged
        destinations and exact app URLs, one-way and hourly."""
        driver_js = read("static/js/driver.js")
        dest_fn = extract_function(
            driver_js, "function tripNavDestination(stageIndex, pickup, dropoff)")
        urls_fn = extract_function(driver_js, "function navChooserUrls(dest)")
        harness = "\n".join([dest_fn, urls_fn, _NODE_DRIVER])
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
        self.assertEqual(result["passed"], 8)


_NODE_DRIVER = """
var failures = [];
var passed = 0;
function check(name, cond, detail) {
  if (cond) { passed++; }
  else { failures.push(name + (detail ? ": " + detail : "")); }
}
var PICKUP = "Terminal 1 Arrivals, Queens, NY 11430";
var DROPOFF = "Stamford, CT";
function expectUrls(dest, label) {
  var urls = navChooserUrls(dest);
  check(label + " Google URL is destination-only",
    urls.google === "https://www.google.com/maps/dir/?api=1&destination=" + encodeURIComponent(dest) &&
    urls.google.indexOf("origin=") === -1, urls.google);
  check(label + " Waze URL navigates to the destination",
    urls.waze === "https://waze.com/ul?q=" + encodeURIComponent(dest) + "&navigate=yes", urls.waze);
}
expectUrls(PICKUP, "pickup");
expectUrls(DROPOFF, "drop-off");
// After "Head to pickup" the staged destination is the pickup;
// after "Start trip" it is the drop-off; hourly after pickup there
// is no destination, so the chooser is suppressed.
check("stage 1 destination is the pickup",
  tripNavDestination(1, PICKUP, DROPOFF) === PICKUP);
check("stage 3 destination is the drop-off",
  tripNavDestination(3, PICKUP, DROPOFF) === DROPOFF);
check("hourly after pickup has no destination",
  tripNavDestination(3, "Central Park, New York", "") === null &&
  tripNavDestination(3, "Central Park, New York", null) === null);
// Addresses with special characters are URL-encoded.
var tricky = navChooserUrls("A & B Street");
check("ampersand encoded in both URLs",
  tricky.google.indexOf("A%20%26%20B%20Street") !== -1 &&
  tricky.waze.indexOf("A%20%26%20B%20Street") !== -1, JSON.stringify(tricky));
console.log(JSON.stringify({passed: passed, failed: failures}));
"""


if __name__ == "__main__":
    unittest.main()
