"""Tests for the USA place search used by booking-form autocomplete.

Endpoint: GET /api/places/search?q=<text>&limit=5
Backed by Nominatim (no API key), restricted to the USA via
countrycodes=us, with full address details. The endpoint always
returns 200: an empty query, bad input, or an upstream failure all
yield an empty results list, so the form keeps working as plain
text. Results carry address text + coordinates only — never any
fare, miles, or pricing data.

Run:  python -m unittest discover -s tests -v

Airport terminals: when a result is an airport (aeroway/aerodrome),
viewbox-bounded Nominatim searches for "Terminal", "Arrivals" and
"Departures" around the airport are merged in directly below the
airport, from live OpenStreetMap data. The fixtures below mirror real
Nominatim responses observed for JFK (terminal roadways, AirTrain
stops, a construction site, parking, a bus stop, a distant freight
terminal) so the filter rules are tested against realistic noise.
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
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}


class PlacesTestCase(unittest.TestCase):
    def setUp(self):
        geo_module._search_cache.clear()
        geo_module._terminal_cache.clear()
        self.client = app_module.app.test_client()
        self.urls = []

    def _capture(self, payload):
        def fake_get(url):
            self.urls.append(url)
            return payload
        return fake_get

    def _routed(self, base_payload, terminal_payloads, fail_bounded=False):
        """Mock _http_get_json: base search -> base_payload, bounded
        terminal searches -> terminal_payloads[q], optionally failing."""
        def fake_get(url):
            self.urls.append(url)
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if params.get("bounded") == ["1"]:
                if fail_bounded:
                    raise urllib.error.URLError("terminal lookup down")
                return terminal_payloads.get(params["q"][0], [])
            return base_payload
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
        self.assertEqual(set(first.keys()),
                         {"display_name", "lat", "lon", "address", "airport", "kind"})
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
        # Nominatim answers empty, so the Photon fallback is also
        # consulted (2 upstream calls); the Nominatim request itself
        # must still be the USA-only search.
        nom_urls = [u for u in self.urls
                    if "nominatim.openstreetmap.org" in u]
        self.assertEqual(len(nom_urls), 1)
        params = urllib.parse.parse_qs(urllib.parse.urlparse(nom_urls[0]).query)
        self.assertEqual(params["countrycodes"], ["us"])
        self.assertEqual(params["addressdetails"], ["1"])
        self.assertEqual(params["format"], ["json"])
        self.assertEqual(params["limit"], ["5"])
        self.assertEqual(params["q"], ["JFK"])
        self.assertIn("nominatim.openstreetmap.org/search", nom_urls[0])

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
        # any non-empty query. Nominatim answers empty here, so the
        # Photon fallback is consulted too (2 upstream calls).
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture([])):
            resp = self.client.get("/api/places/search?q=ab")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self.urls), 2)


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


class TestAirportTerminals(PlacesTestCase):
    # JFK aerodrome at its real coordinates; the airport is deliberately
    # second in the base results to prove detection is not position-based.
    JFK_BASE = [
        {
            "place_id": 200,
            "class": "railway",
            "type": "station",
            "display_name": "JFK Airport AirTrain Station, Queens, New York, United States",
            "lat": "40.6410",
            "lon": "-73.7800",
            "address": {"county": "Queens", "state": "New York",
                        "country": "United States", "country_code": "us"},
        },
        {
            "place_id": 201,
            "class": "aeroway",
            "type": "aerodrome",
            "display_name": "John F. Kennedy International Airport, Queens, New York, United States",
            "lat": "40.6413111",
            "lon": "-73.7803273",
            "address": {"county": "Queens", "state": "New York",
                        "country": "United States", "country_code": "us"},
        },
    ]

    def _terminal(self, name, cls, typ, lat, lon):
        return {
            "class": cls, "type": typ, "display_name": name,
            "lat": str(lat), "lon": str(lon),
            "address": {"county": "Queens", "state": "New York",
                        "country": "United States", "country_code": "us"},
        }

    def _terminal_payloads(self):
        t = self._terminal
        return {
            "Terminal": [
                # Construction segment first: must not shadow the real one.
                t("Terminal 4 Departures, Queens, New York, United States",
                  "highway", "construction", 40.6435, -73.7823),
                t("Terminal 4 Departures, Queens, New York, United States",
                  "highway", "tertiary", 40.6435, -73.7823),
                t("Terminal 4 Arrivals, Queens, New York, United States",
                  "highway", "tertiary", 40.6436, -73.7824),
                t("Terminal 4, Queens, New York, United States",
                  "railway", "station", 40.6437, -73.7825),  # AirTrain stop
                t("JFK Terminal 6, Queens, New York, United States",
                  "landuse", "construction", 40.6440, -73.7830),  # not open
                t("Terminal 7 Parking, Queens, New York, United States",
                  "amenity", "parking", 40.6450, -73.7840),
                t("Terminal 4, Queens, New York, United States",
                  "highway", "bus_stop", 40.6438, -73.7826),
                t("Red Hook Terminal, Brooklyn, New York, United States",
                  "landuse", "industrial", 40.6790, -74.0120),  # freight
                t("Newark Liberty Terminal, Newark, New Jersey, United States",
                  "highway", "tertiary", 40.6895, -74.1745),  # ~35 km away
            ],
            "Arrivals": [
                t("Terminal 1 Arrivals, Queens, New York, United States",
                  "highway", "tertiary", 40.6445, -73.7855),
                t("Terminal 5 Arrivals, Queens, New York, United States",
                  "highway", "tertiary", 40.6430, -73.7800),
                # Duplicate name, different postcode: dedup keeps one.
                t("Terminal 4 Arrivals, Queens, New York, 11430, United States",
                  "highway", "tertiary", 40.6436, -73.7824),
            ],
            "Departures": [
                t("Terminal 1 Departures, Queens, New York, United States",
                  "highway", "tertiary", 40.6446, -73.7856),
                t("Terminal 5 Departures, Queens, New York, United States",
                  "highway", "tertiary", 40.6431, -73.7801),
            ],
        }

    def _names(self, results):
        return [item["display_name"].split(",")[0] for item in results]

    def test_airport_query_merges_terminals_below_airport(self):
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=self._routed(self.JFK_BASE, self._terminal_payloads())):
            resp = self.client.get("/api/places/search?q=JFK")
        self.assertEqual(resp.status_code, 200)
        results = resp.get_json()["results"]
        self.assertEqual(
            self._names(results),
            ["John F. Kennedy International Airport",
             "Terminal 1 Arrivals", "Terminal 1 Departures",
             "Terminal 4 Arrivals", "Terminal 4 Departures",
             "Terminal 5 Arrivals", "Terminal 5 Departures",
             "JFK Airport AirTrain Station"])
        # Every entry keeps the exact public shape, no pricing fields.
        # "kind" is the suggestion type for the booking form's icon
        # and flight-number field (Blacklane-style, owner 2026-11-22).
        for item in results:
            self.assertEqual(set(item.keys()),
                             {"display_name", "lat", "lon", "address", "airport", "kind"})
            self.assertFalse(FORBIDDEN_KEYS & set(item.keys()))
            self.assertFalse(FORBIDDEN_KEYS & set(item["address"].keys()))
            self.assertNotIn("class", item)
            self.assertNotIn("type", item)

    def test_bounded_queries_use_viewbox_around_airport(self):
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=self._routed(self.JFK_BASE, self._terminal_payloads())):
            geo_module.search_places("JFK")
        bounded = [u for u in self.urls if "bounded=1" in u]
        self.assertEqual(len(bounded), 3)
        queries = set()
        for url in bounded:
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            queries.add(params["q"][0])
            self.assertEqual(params["countrycodes"], ["us"])
            self.assertEqual(params["addressdetails"], ["1"])
            self.assertEqual(params["limit"], ["25"])
            left, top, right, bottom = [float(v) for v in params["viewbox"][0].split(",")]
            # Viewbox is airport coords +/- 0.06 degrees.
            self.assertAlmostEqual(left, -73.7803273 - 0.06, places=3)
            self.assertAlmostEqual(right, -73.7803273 + 0.06, places=3)
            self.assertAlmostEqual(top, 40.6413111 + 0.06, places=3)
            self.assertAlmostEqual(bottom, 40.6413111 - 0.06, places=3)
        self.assertEqual(queries, {"Terminal", "Arrivals", "Departures"})

    def test_non_airport_query_makes_no_bounded_calls(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture(NOMINATIM_OK)):
            results = geo_module.search_places("180 Green")
        self.assertEqual(len(results), 2)
        self.assertEqual([u for u in self.urls if "bounded" in u], [])

    def test_terminal_lookup_failure_falls_back_to_base_results(self):
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=self._routed(self.JFK_BASE, {}, fail_bounded=True)):
            resp = self.client.get("/api/places/search?q=JFK")
        self.assertEqual(resp.status_code, 200)
        results = resp.get_json()["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(self._names(results),
                         ["JFK Airport AirTrain Station",
                          "John F. Kennedy International Airport"])

    def test_empty_terminal_results_keep_base_results(self):
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=self._routed(self.JFK_BASE, {})):
            results = geo_module.search_places("JFK")
        self.assertEqual(len(results), 2)

    def test_terminal_cache_shared_across_queries_for_same_airport(self):
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=self._routed(self.JFK_BASE, self._terminal_payloads())):
            first = geo_module.search_places("JFK")
            second = geo_module.search_places("Kennedy Airport")
        self.assertEqual(first, second)
        # Base search ran twice (different queries), terminal lookup once.
        self.assertEqual(len(self.urls), 5)
        self.assertEqual(len([u for u in self.urls if "bounded=1" in u]), 3)

    def test_airport_flag_on_results(self):
        # Only the airport itself is flagged; terminals and street
        # addresses are not, so the booking form can tell them apart.
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=self._routed(self.JFK_BASE, self._terminal_payloads())):
            results = geo_module.search_places("JFK")
        flags = {item["display_name"].split(",")[0]: item["airport"]
                 for item in results}
        self.assertIs(flags["John F. Kennedy International Airport"], True)
        self.assertIs(flags["JFK Airport AirTrain Station"], False)
        self.assertIs(flags["Terminal 4 Arrivals"], False)
        self.assertIs(flags["Terminal 1 Departures"], False)
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._capture(NOMINATIM_OK)):
            plain = geo_module.search_places("180 Green")
        self.assertTrue(all(item["airport"] is False for item in plain))

    def test_terminal_lookup_never_raises(self):
        def boom(url):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if params.get("bounded") == ["1"]:
                raise RuntimeError("boom")
            return self.JFK_BASE
        with mock.patch.object(geo_module, "_http_get_json", side_effect=boom):
            results = geo_module.search_places("JFK")
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
