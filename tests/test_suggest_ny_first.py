"""Tests for state-first address suggestions (owner 2026-11-22):
"agar main New York se book kar raha hoon to pehle New York ke
batana chahiye; agar main New Jersey pe hoon to New Jersey ka aana
chahiye" — nearest-first from the customer's location, other states
below, never removed, never locked to one state.

The reported defect (verified live in the browser 2026-11-22
~18:53 EST): typing "180 green acres" returned 5 suggestions and
NOT ONE was the owner's own address — Pittsboro NC, Mercer County
WV (the same entry THREE times), Pearl MS. The fixtures below are
that exact live Nominatim answer (coordinates and display names
copied verbatim).

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-suggest-ny-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "suggest.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "suggest-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402
import app as app_module  # noqa: E402

# Live Nominatim answer for "180 green acres" (2026-11-22): the
# owner's New York address is NOT in it, and the West Virginia
# entry arrives three times as three OSM objects.
NOMINATIM_180_GREEN_ACRES = [
    {
        "display_name": "180, Green Acres, Pittsboro, Chatham County, "
                        "North Carolina, 27312, United States",
        "lat": "35.6765285", "lon": "-79.2809763",
        "address": {"country": "United States", "country_code": "us",
                    "county": "Chatham County", "house_number": "180",
                    "postcode": "27312", "road": "Green Acres",
                    "state": "North Carolina", "town": "Pittsboro"},
    },
    {
        "display_name": "180, Green Acres, Mercer County, West "
                        "Virginia, 24739, United States",
        "lat": "37.3793351", "lon": "-81.0323569",
        "address": {"country": "United States", "country_code": "us",
                    "county": "Mercer County", "house_number": "180",
                    "postcode": "24739", "road": "Green Acres",
                    "state": "West Virginia"},
    },
    {
        "display_name": "180, Green Acres, Pearl, Rankin County, "
                        "Mississippi, 39208, United States",
        "lat": "32.3074099", "lon": "-90.045107",
        "address": {"country": "United States", "country_code": "us",
                    "county": "Rankin County", "house_number": "180",
                    "postcode": "39208", "road": "Green Acres",
                    "state": "Mississippi", "town": "Pearl"},
    },
    {
        "display_name": "180, Green Acres, Mercer County, West "
                        "Virginia, 24739, United States",
        "lat": "37.3806308", "lon": "-81.0272394",
        "address": {"country": "United States", "country_code": "us",
                    "county": "Mercer County", "house_number": "180",
                    "postcode": "24739", "road": "Green Acres",
                    "state": "West Virginia"},
    },
    {
        "display_name": "180, Green Acres, Mercer County, West "
                        "Virginia, 24739, United States",
        "lat": "37.3814124", "lon": "-81.030126",
        "address": {"country": "United States", "country_code": "us",
                    "county": "Mercer County", "house_number": "180",
                    "postcode": "24739", "road": "Green Acres",
                    "state": "West Virginia"},
    },
]

# The owner's address, exactly as the committed snapshot holds it.
NY_DISPLAY = ("180, Green Acres Road, Green Acres Mall, Green Acres, "
              "Village of Valley Stream, Town of Hempstead, Nassau "
              "County, New York, 11581, United States")
NY_LAT, NY_LON = 40.6600991, -73.7160402

# Same query with a New Jersey match added (Cherry Hill), for the
# "in New Jersey, New Jersey first" check.
MIXED_WITH_NJ = [
    NOMINATIM_180_GREEN_ACRES[0],  # Pittsboro NC
    {
        "display_name": "180, Green Acres, Cherry Hill, Camden "
                        "County, New Jersey, 08003, United States",
        "lat": "39.93", "lon": "-75.03",
        "address": {"country": "United States", "country_code": "us",
                    "county": "Camden County", "house_number": "180",
                    "postcode": "08003", "road": "Green Acres",
                    "state": "New Jersey", "town": "Cherry Hill"},
    },
    {
        "display_name": NY_DISPLAY,
        "lat": str(NY_LAT), "lon": str(NY_LON),
        "address": {"country": "United States", "country_code": "us",
                    "county": "Nassau County", "house_number": "180",
                    "postcode": "11581", "road": "Green Acres Road",
                    "state": "New York",
                    "town": "Village of Valley Stream"},
    },
]

# New York City (the default bias) and Trenton NJ (a NJ bias point).
NYC_LAT, NYC_LON = 40.7128, -74.0060
TRENTON_LAT, TRENTON_LON = 40.2206, -74.7597


class SuggestNyFirstTestCase(unittest.TestCase):
    def setUp(self):
        geo_module._search_cache.clear()
        geo_module._terminal_cache.clear()
        self.client = app_module.app.test_client()

    def _names(self, results):
        return [r["display_name"] for r in results]


class TestNyFirst(SuggestNyFirstTestCase):
    def test_180_green_acres_returns_ny_first(self):
        # The reported defect, verbatim: upstream has no NY result
        # at all, yet the owner's address must come first.
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=NOMINATIM_180_GREEN_ACRES):
            results = geo_module.search_places("180 green acres")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["display_name"], NY_DISPLAY)
        self.assertEqual(results[0]["address"]["state"], "New York")
        self.assertEqual(results[0]["address"]["postcode"], "11581")

    def test_no_duplicate_suggestions(self):
        # The West Virginia entry arrived three times live.
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=NOMINATIM_180_GREEN_ACRES):
            results = geo_module.search_places("180 green acres")
        names = self._names(results)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(
            names.count("180, Green Acres, Mercer County, West Virginia, "
                        "24739, United States"), 1)

    def test_other_states_still_present_below(self):
        # Other states are NOT removed — they rank below the local one.
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=NOMINATIM_180_GREEN_ACRES):
            results = geo_module.search_places("180 green acres")
        states = [r["address"]["state"] for r in results]
        self.assertEqual(states[0], "New York")
        self.assertIn("North Carolina", states)
        self.assertIn("West Virginia", states)
        self.assertIn("Mississippi", states)

    def test_ranking_follows_bias_point(self):
        # Same upstream list, different bias: the nearest result wins.
        # From the West Virginia coords the WV entry is nearest.
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=NOMINATIM_180_GREEN_ACRES):
            results = geo_module.search_places(
                "180 green acres", 5, 37.3793, -81.0324)
        self.assertEqual(results[0]["address"]["state"], "West Virginia")
        # And the default (no location) is New York City.
        geo_module._search_cache.clear()
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=NOMINATIM_180_GREEN_ACRES):
            results = geo_module.search_places("180 green acres")
        self.assertEqual(results[0]["address"]["state"], "New York")

    def test_nj_bias_ranks_nj_first(self):
        # "Agar main New Jersey pe hoon to New Jersey ka aana chahiye."
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=MIXED_WITH_NJ):
            nj_first = geo_module.search_places(
                "180 green acres", 5, TRENTON_LAT, TRENTON_LON)
        self.assertEqual(nj_first[0]["address"]["state"], "New Jersey")
        self.assertIn("Cherry Hill", nj_first[0]["display_name"])
        # Same list from New York City: the New York match is nearest.
        geo_module._search_cache.clear()
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=MIXED_WITH_NJ):
            ny_first = geo_module.search_places(
                "180 green acres", 5, NYC_LAT, NYC_LON)
        self.assertEqual(ny_first[0]["address"]["state"], "New York")
        self.assertIn("New Jersey",
                      [r["address"]["state"] for r in ny_first],
                      "other states stay in the list, below")

    def test_nominatim_request_carries_bias_viewbox(self):
        urls = []
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=lambda url: urls.append(url) or []):
            geo_module.search_places("180 green acres")
        nom = [u for u in urls if "nominatim" in u]
        self.assertEqual(len(nom), 1)
        params = urllib.parse.parse_qs(urllib.parse.urlparse(nom[0]).query)
        # Default bias is New York City: viewbox around it.
        self.assertEqual(params["viewbox"],
                         ["-75.506000,41.712800,-72.506000,39.712800"])
        self.assertEqual(params["countrycodes"], ["us"])

    def test_photon_fallback_carries_bias_lat_lon(self):
        urls = []

        def fake_get(url):
            urls.append(url)
            if "photon.komoot.io" in url:
                return {"type": "FeatureCollection", "features": []}
            return []  # Nominatim: no match -> Photon consulted

        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=fake_get):
            geo_module.search_places("180 green acres", 5, 40.2, -74.7)
        photon = [u for u in urls if "photon" in u]
        self.assertEqual(len(photon), 1)
        self.assertIn("lat=40.200000", photon[0])
        self.assertIn("lon=-74.700000", photon[0])


class TestSnapshotSubsetMatch(SuggestNyFirstTestCase):
    def test_partial_house_address_matches_snapshot(self):
        hit = geo_module._snapshot_subset_match("180 green acres")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["display_name"], NY_DISPLAY)
        self.assertEqual(hit["address"]["postcode"], "11581")

    def test_no_digit_means_no_snapshot_match(self):
        self.assertIsNone(geo_module._snapshot_subset_match("green acres"))
        self.assertIsNone(geo_module._snapshot_subset_match("valley stream"))

    def test_single_word_never_matches(self):
        self.assertIsNone(geo_module._snapshot_subset_match("180"))

    def test_terminal_number_matches_its_snapshot(self):
        hit = geo_module._snapshot_subset_match("terminal 1")
        self.assertIsNotNone(hit)
        self.assertIn("Terminal 1", hit["display_name"])


class TestEndpointBias(SuggestNyFirstTestCase):
    def test_endpoint_accepts_lat_lon(self):
        urls = []
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=lambda url: urls.append(url) or []):
            resp = self.client.get(
                "/api/places/search?q=180%20green%20acres"
                "&lat=40.2206&lon=-74.7597")
        self.assertEqual(resp.status_code, 200)
        nom = [u for u in urls if "nominatim" in u]
        self.assertEqual(len(nom), 1)
        # Trenton NJ bias: viewbox centred on Trenton, not NYC.
        self.assertIn("viewbox=-76.259700,41.220600,-73.259700,39.220600",
                      nom[0])

    def test_endpoint_bad_coords_fall_back_to_nyc(self):
        urls = []
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=lambda url: urls.append(url) or []):
            resp = self.client.get(
                "/api/places/search?q=180%20green%20acres"
                "&lat=abc&lon=999")
        self.assertEqual(resp.status_code, 200)
        nom = [u for u in urls if "nominatim" in u]
        self.assertEqual(len(nom), 1)
        self.assertIn("viewbox=-75.506000,41.712800,-72.506000,39.712800",
                      nom[0])

    def test_bias_is_part_of_cache_key(self):
        # Same query, different bias: separate cache entries, so a
        # New York ranking is never served to a New Jersey customer.
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=MIXED_WITH_NJ):
            ny = geo_module.search_places(
                "180 green acres", 5, NYC_LAT, NYC_LON)
            nj = geo_module.search_places(
                "180 green acres", 5, TRENTON_LAT, TRENTON_LON)
        self.assertEqual(ny[0]["address"]["state"], "New York")
        self.assertEqual(nj[0]["address"]["state"], "New Jersey")
        self.assertEqual(
            len(geo_module._search_cache), 2)


if __name__ == "__main__":
    unittest.main()
