"""Tests for driver route options: Google Maps AND Waze.

Owner decision 2026-11-16 (voice call): the driver gets two route
options on the offer card and the trip screen — "Google Maps" and
"Waze" — instead of the single "View route map" link. The Google URL
(route_url) is unchanged; the Waze URL (route_waze_url) navigates to
the dropoff (or the pickup when there is no dropoff).

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-routes-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "routes.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "routes-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class RouteUrlCase(unittest.TestCase):
    def test_google_url_with_dropoff(self):
        booking = SimpleNamespace(pickup="JFK Airport", dropoff="Times Square, New York")
        self.assertEqual(
            app_module.route_url_for(booking),
            "https://www.google.com/maps/dir/?api=1"
            "&origin=JFK+Airport&destination=Times+Square%2C+New+York")

    def test_google_url_without_dropoff(self):
        booking = SimpleNamespace(pickup="Central Park, New York", dropoff="")
        self.assertEqual(
            app_module.route_url_for(booking),
            "https://www.google.com/maps/search/?api=1&query=Central+Park%2C+New+York")

    def test_waze_url_with_dropoff(self):
        booking = SimpleNamespace(pickup="JFK Airport", dropoff="Times Square, New York")
        self.assertEqual(
            app_module.waze_url_for(booking),
            "https://waze.com/ul?q=Times+Square%2C+New+York&navigate=yes")

    def test_waze_url_without_dropoff(self):
        booking = SimpleNamespace(pickup="Central Park, New York", dropoff="")
        self.assertEqual(
            app_module.waze_url_for(booking),
            "https://waze.com/ul?q=Central+Park%2C+New+York&navigate=yes")

    def test_waze_url_present_in_driver_payloads(self):
        source = read("app.py")
        self.assertEqual(source.count('"route_waze_url": waze_url_for('), 3,
                         "offers list, active-trip, and accept payloads")

    def test_driver_js_renders_both_links(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("Google Maps ↗", driver_js)
        self.assertIn("Waze ↗", driver_js)
        self.assertIn("route_waze_url", driver_js)
        self.assertIn("route_url: b.route_url", driver_js)
        self.assertIn("route_waze_url: b.route_waze_url", driver_js)
        self.assertNotIn("View route map", driver_js)

    def test_driver_css_spaces_route_links(self):
        css = read("static/css/driver.css")
        self.assertIn(".route-link + .route-link", css)


if __name__ == "__main__":
    unittest.main()
