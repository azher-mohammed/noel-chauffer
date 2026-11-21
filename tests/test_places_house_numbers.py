"""Tests for house numbers in address suggestions (owner report
2026-11-21: "180 Green Acres Road" lost its "180" in pickup
suggestions and "1854 Stone Ave" suggested nothing at all).

Root cause: the live path in production is the Photon fallback
(Nominatim is blocked/empty from Render's egress IP), and Photon
house/building features carry housenumber + street but NO name —
_photon_items skipped nameless features entirely, so a typed house
address suggested only its road, or nothing. The fix synthesizes
the display name from the feature's own housenumber + street, and
search_places / _geocode_query now also fall back to Photon when
Nominatim answers with an empty list (an empty Nominatim answer is
not proof the address does not exist).

Fixtures below are the real Photon responses observed live
2026-11-21 for the two reported addresses (coordinates and
properties copied verbatim; only the irrelevant extent is trimmed).

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-places-house-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "house.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "house-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402
import app as app_module  # noqa: E402

# Real Photon answer for "180 Green Acres Road, East Valley Stream,
# NY 11581" (2026-11-21): the house itself is the first feature and
# has NO name — only housenumber + street. The road features after
# it do have names.
PHOTON_PICKUP = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-73.7139, 40.6623]},
            "properties": {
                "osm_type": "N", "osm_id": 8783481500,
                "osm_key": "place", "osm_value": "house", "type": "house",
                "housenumber": "180", "street": "Green Acres Road",
                "locality": "Green Acres Mall", "district": "Green Acres",
                "city": "Valley Stream", "county": "Nassau", "state": "NY",
                "country": "United States", "postcode": "11581",
                "countrycode": "US",
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-73.7141, 40.6622]},
            "properties": {
                "osm_type": "W", "osm_id": 619429166,
                "osm_key": "highway", "osm_value": "tertiary",
                "type": "street", "name": "Green Acres Road",
                "city": "Valley Stream", "county": "Nassau",
                "state": "New York", "country": "United States",
                "postcode": "11581", "countrycode": "US",
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-73.7139, 40.6623]},
            "properties": {
                "osm_type": "W", "osm_id": 667678041,
                "osm_key": "highway", "osm_value": "tertiary",
                "type": "street", "name": "Green Acres Road South",
                "city": "Valley Stream", "county": "Nassau",
                "state": "New York", "country": "United States",
                "postcode": "11581", "countrycode": "US",
            },
        },
    ],
}

# Real Photon answer for "1854 Stone Ave, East Meadow, NY 11554"
# (2026-11-21): exactly ONE feature, the house itself, again with
# NO name — so the old code returned zero suggestions.
PHOTON_DROPOFF = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-73.5676, 40.7230]},
            "properties": {
                "osm_type": "W", "osm_id": 888513178,
                "osm_key": "building", "osm_value": "house", "type": "house",
                "housenumber": "1854", "street": "Stone Avenue",
                "city": "East Meadow", "county": "Nassau", "state": "NY",
                "country": "United States", "postcode": "11554",
                "countrycode": "US",
            },
        },
    ],
}

# A nameless house outside the USA must still be dropped (USA-only
# gate is not weakened by the name synthesis).
PHOTON_FRANCE_HOUSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [2.3522, 48.8566]},
            "properties": {
                "osm_key": "place", "osm_value": "house", "type": "house",
                "housenumber": "12", "street": "Rue de Rivoli",
                "city": "Paris", "country": "France",
                "postcode": "75001", "countrycode": "FR",
            },
        },
    ],
}


class HouseNumberTestCase(unittest.TestCase):
    def setUp(self):
        geo_module._search_cache.clear()
        geo_module._geocode_cache.clear()
        geo_module._geocode_address_cache.clear()
        self.client = app_module.app.test_client()

    def tearDown(self):
        geo_module._search_cache.clear()
        geo_module._geocode_cache.clear()
        geo_module._geocode_address_cache.clear()


class TestPhotonHouseNames(HouseNumberTestCase):
    def test_nameless_house_kept_with_synthesized_name(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=PHOTON_PICKUP):
            items = geo_module._photon_items(
                "180 Green Acres Road, East Valley Stream, NY 11581", 5)
        self.assertEqual(len(items), 3)
        first = items[0]
        self.assertTrue(
            first["display_name"].startswith("180 Green Acres Road"),
            first["display_name"])
        self.assertEqual(first["address"]["house_number"], "180")
        self.assertEqual(first["address"]["road"], "180 Green Acres Road")
        self.assertEqual(first["address"]["city"], "Valley Stream")
        self.assertEqual(first["address"]["postcode"], "11581")
        self.assertEqual(first["address"]["country_code"], "us")

    def test_single_nameless_house_is_the_only_suggestion(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=PHOTON_DROPOFF):
            items = geo_module._photon_items(
                "1854 Stone Ave, East Meadow, NY 11554", 5)
        self.assertEqual(len(items), 1)
        self.assertTrue(
            items[0]["display_name"].startswith("1854 Stone Avenue"),
            items[0]["display_name"])
        self.assertEqual(items[0]["address"]["house_number"], "1854")
        self.assertEqual(items[0]["address"]["road"], "1854 Stone Avenue")

    def test_nameless_house_outside_usa_still_dropped(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=PHOTON_FRANCE_HOUSE):
            self.assertEqual(
                geo_module._photon_items("12 Rue de Rivoli, Paris", 5), [])

    def test_nameless_feature_without_street_still_skipped(self):
        payload = {"type": "FeatureCollection", "features": [
            {"type": "Feature",
             "geometry": {"type": "Point", "coordinates": [-73.0, 40.0]},
             "properties": {"osm_key": "place", "osm_value": "house",
                            "housenumber": "9", "city": "Nowhere",
                            "country": "United States",
                            "countrycode": "US"}}]}
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=payload):
            self.assertEqual(geo_module._photon_items("9 Nowhere", 5), [])


class TestSearchFallsBackOnEmpty(HouseNumberTestCase):
    def _routed(self, photon_payload):
        """Nominatim answers with an empty list (the Render
        behaviour for ordinary streets); Photon has the house."""
        def fake_get(url):
            if "photon.komoot.io" in url:
                return photon_payload
            return []  # Nominatim: genuine-looking empty answer
        return fake_get

    def test_pickup_keeps_house_number_when_nominatim_empty(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(PHOTON_PICKUP)):
            results = geo_module.search_places(
                "180 Green Acres Road, East Valley Stream, NY 11581")
        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(
            results[0]["display_name"].startswith("180 Green Acres Road"),
            results[0]["display_name"])
        self.assertEqual(results[0]["address"]["house_number"], "180")

    def test_dropoff_suggests_when_nominatim_empty(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(PHOTON_DROPOFF)):
            results = geo_module.search_places(
                "1854 Stone Ave, East Meadow, NY 11554")
        self.assertEqual(len(results), 1)
        self.assertTrue(
            results[0]["display_name"].startswith("1854 Stone Avenue"),
            results[0]["display_name"])

    def test_both_empty_still_returns_empty_list(self):
        def fake_get(url):
            if "photon.komoot.io" in url:
                return {"type": "FeatureCollection", "features": []}
            return []
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=fake_get):
            self.assertEqual(geo_module.search_places("zzzqqq nowhere"), [])

    def test_endpoint_keeps_house_number(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(PHOTON_PICKUP)):
            resp = self.client.get(
                "/api/places/search?q=180%20Green%20Acres%20Road%2C%20"
                "East%20Valley%20Stream%2C%20NY%2011581&limit=5")
        self.assertEqual(resp.status_code, 200)
        results = resp.get_json()["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(
            results[0]["display_name"].startswith("180 Green Acres Road"))


class TestGeocodeFallsBackOnEmpty(HouseNumberTestCase):
    def test_geocode_house_when_nominatim_empty(self):
        def fake_get(url):
            if "photon.komoot.io" in url:
                return PHOTON_DROPOFF
            return []  # Nominatim matched nothing
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=fake_get):
            coords, details, errored = geo_module._geocode_query(
                "1854 Stone Ave, East Meadow, NY 11554")
        self.assertFalse(errored)
        self.assertIsNotNone(coords)
        self.assertAlmostEqual(coords[0], 40.7230, places=3)
        self.assertAlmostEqual(coords[1], -73.5676, places=3)
        self.assertEqual(details.get("house_number"), "1854")


if __name__ == "__main__":
    unittest.main()
