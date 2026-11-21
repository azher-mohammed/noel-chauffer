"""USA-only maps and place search (owner order 2026-11-21 ~03:44 EST:
"sirf US, haan USA ka map hi rehna" — only the USA map should remain;
he reported France and other countries showing up around
pickup/drop-off).

Root cause: Nominatim calls already carry countrycodes=us, but the
Photon fallback (_photon_items) had no country restriction at all —
and Nominatim is blocked/throttled from Render's egress IP, so in
production the Photon fallback is the live path and it answered
worldwide. Covered here:
- _photon_items sends the USA bbox and drops every feature whose
  countrycode is not "us" (missing counts as not-US);
- _geocode_query's Photon path never resolves a non-US address;
- _parse_place (the shared choke point for search_places and the
  terminal lookup) drops non-US items;
- a France query returns no suggestions / no coordinates, never a
  made-up US match;
- the Leaflet live maps (website + customer app) are bounded to the
  USA with maxBounds, dark CARTO tiles unchanged.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-usa-only-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    _tmpdir, "noel-usa-only.db"
)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "usa-only-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

PHOTON_MIXED = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [2.3522, 48.8566]},
            "properties": {"name": "Paris", "osm_key": "place",
                           "osm_value": "city", "city": "Paris",
                           "country": "France", "countrycode": "FR"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [13.4050, 52.5200]},
            "properties": {"name": "Berlin", "osm_key": "place",
                           "osm_value": "city", "city": "Berlin",
                           "country": "Germany", "countrycode": "DE"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-74.0060, 40.7128]},
            "properties": {"name": "New York", "osm_key": "place",
                           "osm_value": "city", "city": "New York",
                           "state": "New York", "country": "United States",
                           "countrycode": "US"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
            "properties": {"name": "Nowhere", "osm_key": "place",
                           "osm_value": "city"},
        },
    ],
}

PHOTON_FRANCE_ONLY = {
    "type": "FeatureCollection",
    "features": [PHOTON_MIXED["features"][0]],
}

PHOTON_US_ONLY = {
    "type": "FeatureCollection",
    "features": [PHOTON_MIXED["features"][2]],
}


class UsaOnlyTestCase(unittest.TestCase):
    def setUp(self):
        geo_module._search_cache.clear()
        geo_module._geocode_cache.clear()
        geo_module._geocode_address_cache.clear()


class TestPhotonUsaOnly(UsaOnlyTestCase):
    def test_photon_drops_non_us_features_and_sends_usa_bbox(self):
        urls = []

        def fake_get(url):
            urls.append(url)
            return PHOTON_MIXED

        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=fake_get):
            items = geo_module._photon_items("Paris", 5)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["display_name"].split(",")[0], "New York")
        self.assertEqual(items[0]["address"]["country_code"], "us")
        photon_urls = [u for u in urls if "photon.komoot.io" in u]
        self.assertEqual(len(photon_urls), 1)
        self.assertIn("bbox=", photon_urls[0])
        self.assertIn("-171.79,18.91,-66.95,71.36", photon_urls[0])

    def test_photon_all_non_us_returns_empty(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=PHOTON_FRANCE_ONLY):
            self.assertEqual(geo_module._photon_items("Paris", 5), [])


class TestParsePlaceUsaOnly(UsaOnlyTestCase):
    def test_parse_place_drops_non_us(self):
        fr = {
            "display_name": "Paris, France", "lat": "48.8566",
            "lon": "2.3522",
            "address": {"country": "France", "country_code": "fr"},
        }
        self.assertIsNone(geo_module._parse_place(fr))

    def test_parse_place_keeps_us(self):
        us = {
            "display_name": "New York, New York, United States",
            "lat": "40.7128", "lon": "-74.0060",
            "address": {"country": "United States", "country_code": "us"},
        }
        parsed = geo_module._parse_place(us)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[0]["display_name"], us["display_name"])


class TestSearchAndGeocodeUsaOnly(UsaOnlyTestCase):
    def _routed(self, photon_payload):
        def fake_get(url):
            if "photon.komoot.io" in url:
                return photon_payload
            raise urllib.error.URLError("nominatim blocked")
        return fake_get

    def test_search_france_returns_no_suggestions(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(PHOTON_FRANCE_ONLY)):
            self.assertEqual(geo_module.search_places("Paris, France"), [])

    def test_search_us_still_works_via_photon(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(PHOTON_US_ONLY)):
            results = geo_module.search_places("New York")
        self.assertEqual(len(results), 1)
        self.assertIn("New York", results[0]["display_name"])

    def test_geocode_france_returns_no_coords(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(PHOTON_FRANCE_ONLY)):
            coords, details, errored = geo_module._geocode_query(
                "Paris, France")
        self.assertIsNone(coords)
        self.assertFalse(errored)

    def test_geocode_us_still_works_via_photon(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(PHOTON_US_ONLY)):
            coords, details, errored = geo_module._geocode_query("New York")
        self.assertFalse(errored)
        self.assertAlmostEqual(coords[0], 40.7128, places=3)
        self.assertAlmostEqual(coords[1], -74.0060, places=3)


class TestMapsUsaOnly(UsaOnlyTestCase):
    def test_live_maps_bounded_to_usa(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in ("static/js/customer.js", "static/js/customer-app.js"):
            with open(os.path.join(root, name), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("maxBounds", text, name)
            self.assertIn("maxBoundsViscosity", text, name)
            # USA bounds: south/north latitudes and west/east
            # longitudes covering the continental US + Alaska + Hawaii.
            self.assertIn("18.9", text, name)
            self.assertIn("71.4", text, name)
            self.assertIn("-171.8", text, name)
            self.assertIn("-66.9", text, name)
            # Dark CARTO tiles and zoom behaviour unchanged.
            self.assertIn("basemaps.cartocdn.com/dark_all", text, name)
            self.assertIn("setView([lat, lng], 14)", text, name)


if __name__ == "__main__":
    unittest.main()
