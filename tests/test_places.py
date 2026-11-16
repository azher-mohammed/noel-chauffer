"""Tests for the USA place search used by booking-form autocomplete.

Endpoint: GET /api/places/search?q=<text>&limit=5
Backed by Nominatim (no API key), restricted to the USA via
countrycodes=us, with full address details. The endpoint always
returns 200: an empty query, bad input, or an upstream failure all
yield an empty results list, so the form keeps working as plain
text. Results carry address text + coordinates only — never any
fare, miles, or pricing data.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-places-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "places.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "places-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402
import app as app_module  # noqa: E402

NOMINATIM_OK = [
    {
        "place_id": 1,
        "display_name": "180, Green Acres Road, East Valley Stream, Nassau County, New York, 11581, United States",
        "lat": "40.670123",
        "lon": "-73.708456",
        "address": {
            "house_number": "180",
            "road": "Green Acres Road",
            "village": "East Valley Stream",
            "county": "Nassau County",
            "state": "New York",
            "postcode": "11581",
            "country": "United States",
            "country_code": "us",
        },
    },
    {
        "place_id": 2,
        "display_name": "Green Acres Mall, Sunrise Highway, Valley Stream, Nassau County, New York, 11581, United States",
        "lat": "40.667",
        "lon": "-73.71",
        "address": {
            "road": "Sunrise Highway",
            "village": "Valley Stream",
            "state": "New York",
            "postcode": "11581",
            "country": "United States",
            "country_code": "us",
        },
    },
]

FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit"}


class PlacesTestCase(unittest.TestCase):
    def setUp(self):
        geo_module._search_cache.clear()
        self.client = app_module.app.test_client()
        self.urls = []

    def _capture(self, payload):
        def fake_get(url):
            self.urls.append(url)
            return payload
        return fake_get


class TestPlaceSearchEndpoint(PlacesTestCase):
    def test_returns_usa_results_with_full_details(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture(NOMINATIM_OK)):
            resp = self.client.get("/api/places/search?q=180%20Green")
        self.assertEqual(resp.status_code, 200)
        results = resp.get_json()["results"]
        self.assertEqual(len(results), 2)
        first = results[0]
        self.assertEqual(set(first.keys()), {"display_name", "lat", "lon", "address"})
        self.assertEqual(first["display_name"], NOMINATIM_OK[0]["display_name"])
        self.assertIsInstance(first["lat"], float)
        self.assertIsInstance(first["lon"], float)
        self.assertAlmostEqual(first["lat"], 40.670123)
        self.assertAlmostEqual(first["lon"], -73.708456)
        self.assertEqual(first["address"]["house_number"], "180")
        self.assertEqual(first["address"]["road"], "Green Acres Road")
        self.assertEqual(first["address"]["state"], "New York")
        self.assertEqual(first["address"]["postcode"], "11581")
        self.assertEqual(first["address"]["country"], "United States")

    def test_request_restricted_to_usa_with_address_details(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture([])):
            self.client.get("/api/places/search?q=JFK&limit=5")
        self.assertEqual(len(self.urls), 1)
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.urls[0]).query)
        self.assertEqual(params["countrycodes"], ["us"])
        self.assertEqual(params["addressdetails"], ["1"])
        self.assertEqual(params["format"], ["json"])
        self.assertEqual(params["limit"], ["5"])
        self.assertEqual(params["q"], ["JFK"])
        self.assertIn("nominatim.openstreetmap.org/search", self.urls[0])

    def test_empty_query_returns_empty_list_without_upstream_call(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture(NOMINATIM_OK)):
            for query in ("", "   ", None):
                url = "/api/places/search" if query is None else \
                    "/api/places/search?q=" + urllib.parse.quote(query)
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.get_json(), {"results": []})
        self.assertEqual(self.urls, [])

    def test_limit_clamping(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture([])):
            cases = [("limit=99", "10"), ("limit=0", "1"),
                     ("limit=-3", "1"), ("limit=abc", "5"), ("", "5")]
            for qs, expected in cases:
                geo_module._search_cache.clear()
                url = "/api/places/search?q=x" + ("&" + qs if qs else "")
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200)
                params = urllib.parse.parse_qs(
                    urllib.parse.urlparse(self.urls[-1]).query)
                self.assertEqual(params["limit"], [expected], qs)

    def test_upstream_error_returns_empty_list_never_500(self):
        def boom(url):
            raise urllib.error.URLError("nominatim down")
        with mock.patch.object(geo_module, "_http_get_json", side_effect=boom):
            resp = self.client.get("/api/places/search?q=180%20Green")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"results": []})

    def test_malformed_entries_skipped(self):
        payload = [
            {"display_name": "No coords here", "address": {}},
            {"display_name": "Bad lat", "lat": "not-a-number", "lon": "-73.7", "address": {}},
            "not-a-dict",
            NOMINATIM_OK[1],
            {"lat": "40.1", "lon": "-73.1", "address": {}},  # no display_name
        ]
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture(payload)):
            resp = self.client.get("/api/places/search?q=Green")
        results = resp.get_json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["display_name"], NOMINATIM_OK[1]["display_name"])

    def test_non_list_upstream_payload_returns_empty_list(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture({"error": "oops"})):
            resp = self.client.get("/api/places/search?q=Green")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"results": []})

    def test_no_pricing_or_privacy_fields_in_results(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture(NOMINATIM_OK)):
            resp = self.client.get("/api/places/search?q=180%20Green")
        for item in resp.get_json()["results"]:
            self.assertFalse(FORBIDDEN_KEYS & set(item.keys()))
            self.assertFalse(FORBIDDEN_KEYS & set(item["address"].keys()))

    def test_short_query_still_queries_server_side(self):
        # The 3-character minimum lives in the browser; the server answers
        # any non-empty query.
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture([])):
            resp = self.client.get("/api/places/search?q=ab")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self.urls), 1)


class TestSearchPlacesUnit(PlacesTestCase):
    def test_empty_and_blank_query_never_calls_upstream(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture(NOMINATIM_OK)):
            self.assertEqual(geo_module.search_places(""), [])
            self.assertEqual(geo_module.search_places("   "), [])
            self.assertEqual(geo_module.search_places(None), [])
        self.assertEqual(self.urls, [])

    def test_exception_returns_empty_list(self):
        def boom(url):
            raise RuntimeError("boom")
        with mock.patch.object(geo_module, "_http_get_json", side_effect=boom):
            self.assertEqual(geo_module.search_places("JFK"), [])

    def test_repeated_query_served_from_cache(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture(NOMINATIM_OK)):
            first = geo_module.search_places("180 Green")
            second = geo_module.search_places("180 Green")
        self.assertEqual(len(self.urls), 1)
        self.assertEqual(first, second)
        # Mutating a returned copy must not poison the cache.
        second[0]["address"]["state"] = "CHANGED"
        self.assertEqual(geo_module.search_places("180 Green")[0]["address"]["state"],
                         "New York")


if __name__ == "__main__":
    unittest.main()
