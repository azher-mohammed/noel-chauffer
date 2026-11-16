"""Tests for the driver flight-track link (free option).

Owner decision 2026-11-16 (voice call): the driver gets a "Track flight"
link on the trip screen — free, no flight-data API — but ONLY when the
pickup is at an airport, so the driver can check when the flight lands.
For drop-offs to the airport (or any non-airport pickup) no link appears.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pricing import is_airport_pickup  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class FlightTrackLinkCase(unittest.TestCase):
    def test_airport_pickup_flag_in_both_trip_payloads(self):
        source = read("app.py")
        self.assertEqual(
            source.count('"airport_pickup": is_airport_pickup(booking.pickup),'), 2,
            "active-trip and accept payloads only, not the offers list")

    def test_airport_detection(self):
        self.assertTrue(is_airport_pickup("John F. Kennedy International Airport, Terminal 4"))
        self.assertTrue(is_airport_pickup("LaGuardia Airport"))
        self.assertFalse(is_airport_pickup("Times Square, New York"))
        self.assertFalse(is_airport_pickup("180 Green Acres Road, Valley Stream"))

    def test_driver_js_renders_track_link_only_for_airport_pickups(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("Track flight ↗", driver_js)
        self.assertIn("airport_pickup: b.airport_pickup", driver_js)
        self.assertIn("if (t.airport_pickup) {", driver_js)
        self.assertIn("google.com/search?q=", driver_js)
        self.assertIn("flight status", driver_js)

    def test_driver_css_styles_track_link(self):
        css = read("static/css/driver.css")
        self.assertIn(".flight-track-link", css)


if __name__ == "__main__":
    unittest.main()
