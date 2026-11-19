"""Tests for the fast-map work (owner report 2026-11-18: autocomplete
"bahut slow", "JFK marte hi niche jaldi aajana").

Covered here:
- keep-alive reuse in geo._http_get_json (one connection per host per
  thread, stale-connection retry once, no retry on HTTP errors, proxy
  tunnel support with the target Host header);
- the committed popular-places snapshot (seeded JFK etc. answer with
  zero upstream calls);
- the Photon fallback (Nominatim request failure only — never on a
  genuine "no match" empty list), for search and for geocoding;
- the background popular-places refresh (replace only on non-empty
  live results, 1.1s pacing);
- the OSRM route cache (repeat route = no second upstream call);
- the CARTO dark tile layer in the customer site + customer app;
- render.yaml: threaded gunicorn + NOEL_SEARCH_WARMUP=1.

Run:  python -m unittest discover -s tests -v
"""

import http.client
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-places-speed-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "speed.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "speed-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402
import app as app_module  # noqa: E402

NOMINATIM_JFK = [
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

PHOTON_JFK = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-73.7801, 40.6670]},
            "properties": {"name": "JFK Expressway", "osm_key": "highway",
                           "osm_value": "motorway", "city": "Queens",
                           "state": "New York", "country": "United States",
                           "countrycode": "US"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-73.7793734, 40.6429479]},
            "properties": {"name": "John F. Kennedy International Airport",
                           "osm_key": "aeroway", "osm_value": "aerodrome",
                           "city": "Queens", "state": "New York",
                           "country": "United States", "countrycode": "US"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-73.7801, 40.6670]},
            "properties": {"name": "JFK Expressway", "osm_key": "highway",
                           "osm_value": "motorway", "city": "Queens",
                           "state": "New York", "country": "United States",
                           "countrycode": "US"},
        },
    ],
}

OSRM_ROUTE = {
    "routes": [{"distance": 29093.4,
                "geometry": {"coordinates": [[-73.7781, 40.6413],
                                             [-73.9855, 40.7580]]}}],
}


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status = status
        self.reason = "OK" if status == 200 else "Error"
        self._payload = payload if payload is not None else {"ok": True}

    def getheaders(self):
        return []

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class FakeConnection:
    """Records putrequest/putheader/endheaders/getresponse calls."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.requests = []
        self.response = FakeResponse()
        self.tunnel = None
        self.closed = False

    def set_tunnel(self, host, port=None, headers=None):
        self.tunnel = (host, port, headers)

    def putrequest(self, method, url, skip_host=False, **kwargs):
        self.requests.append(("putrequest", method, url, skip_host))

    def putheader(self, header, value):
        self.requests.append(("putheader", header, value))

    def endheaders(self, *args, **kwargs):
        self.requests.append(("endheaders",))

    def getresponse(self):
        self.requests.append(("getresponse",))
        return self.response

    def request(self, *args, **kwargs):  # pragma: no cover - not used
        raise AssertionError("raw request() must not be used")


class SpeedTestCase(unittest.TestCase):
    def setUp(self):
        geo_module._search_cache.clear()
        geo_module._terminal_cache.clear()
        geo_module._route_cache.clear()
        geo_module._geocode_cache.clear()
        self._saved_snapshot_flag = geo_module._SNAPSHOT_LOADED
        self._saved_refresh_started = geo_module._refresh_started
        self.client = app_module.app.test_client()

    def tearDown(self):
        geo_module._search_cache.clear()
        geo_module._terminal_cache.clear()
        geo_module._route_cache.clear()
        geo_module._geocode_cache.clear()
        geo_module._SNAPSHOT_LOADED = self._saved_snapshot_flag
        geo_module._refresh_started = self._saved_refresh_started
        # Drop any thread-local connections created by the tests.
        if hasattr(geo_module._tls, "connections"):
            del geo_module._tls.connections


class TestKeepAlive(SpeedTestCase):
    def _patch_conn(self, responses):
        """Patch HTTPSConnection to serve canned responses in order."""
        created = []

        def factory(*args, **kwargs):
            conn = FakeConnection(*args, **kwargs)
            if responses:
                conn.response = responses.pop(0)
            created.append(conn)
            return conn

        patcher = mock.patch.object(
            http.client, "HTTPSConnection", side_effect=factory)
        patcher.start()
        self.addCleanup(patcher.stop)
        proxy_patcher = mock.patch.object(
            geo_module, "_proxy_for", return_value=None)
        proxy_patcher.start()
        self.addCleanup(proxy_patcher.stop)
        return created

    def test_reuses_one_connection_per_host(self):
        created = self._patch_conn([FakeResponse(), FakeResponse()])
        geo_module._http_get_json(
            "https://nominatim.openstreetmap.org/search?format=json&q=JFK")
        geo_module._http_get_json(
            "https://nominatim.openstreetmap.org/search?format=json&q=LGA")
        self.assertEqual(len(created), 1)
        # 2 calls x (putrequest + 2 putheader + endheaders + getresponse)
        self.assertEqual(len(created[0].requests), 10)

    def test_stale_connection_retried_once_on_fresh_connection(self):
        stale = FakeConnection()
        stale.getresponse = mock.Mock(
            side_effect=http.client.RemoteDisconnected(
                "Remote end closed connection without response"))
        created = []

        def factory(*args, **kwargs):
            conn = stale if not created else FakeConnection(*args, **kwargs)
            created.append(conn)
            return conn

        with mock.patch.object(http.client, "HTTPSConnection",
                               side_effect=factory), \
                mock.patch.object(geo_module, "_proxy_for",
                                  return_value=None):
            result = geo_module._http_get_json(
                "https://nominatim.openstreetmap.org/search?format=json&q=JFK")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(created), 2)

    def test_http_error_is_not_retried(self):
        created = self._patch_conn([FakeResponse(status=403)])
        with self.assertRaises(urllib.error.HTTPError):
            geo_module._http_get_json(
                "https://nominatim.openstreetmap.org/search?format=json&q=JFK")
        self.assertEqual(len(created), 1)

    def test_proxy_tunnel_uses_target_host_header(self):
        created = self._patch_conn([FakeResponse()])
        proxy = ("proxy.example", 3128, "Basic dGVzdDp0ZXN0")
        with mock.patch.object(geo_module, "_proxy_for",
                               return_value=proxy):
            geo_module._http_get_json(
                "https://router.project-osrm.org/route/v1/driving/0,0;1,1")
        conn = created[0]
        self.assertEqual(conn.args[0], "proxy.example")
        self.assertEqual(conn.tunnel[0], "router.project-osrm.org")
        self.assertEqual(conn.tunnel[1], 443)
        self.assertEqual(conn.tunnel[2]["Proxy-Authorization"],
                         "Basic dGVzdDp0ZXN0")
        hosts = [rest[1] for kind, *rest in conn.requests
                 if kind == "putheader" and rest[0] == "Host"]
        self.assertEqual(hosts, ["router.project-osrm.org"])
        # The OSRM ';' separator must survive url parsing.
        put = [r for r in conn.requests if r[0] == "putrequest"][0]
        self.assertIn("0,0;1,1", put[2])

    def test_osrm_route_uses_keep_alive(self):
        created = self._patch_conn([FakeResponse(payload=OSRM_ROUTE),
                                    FakeResponse(payload=OSRM_ROUTE)])
        first = geo_module.route_miles(40.6413, -73.7781, 40.7580, -73.9855)
        second = geo_module.route_miles(40.6413, -73.7781, 40.7580, -73.9855)
        self.assertEqual(first, second)
        self.assertEqual(len(created), 1)


class TestSnapshot(SpeedTestCase):
    def test_snapshot_seeds_jfk_without_upstream_call(self):
        geo_module._SNAPSHOT_LOADED = False
        geo_module.load_places_snapshot()
        self.assertIn(("jfk", 5), geo_module._search_cache)
        first = geo_module._search_cache[("jfk", 5)][0]
        self.assertTrue(first["display_name"].startswith(
            "John F. Kennedy International Airport"))
        self.assertTrue(first["airport"])
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=AssertionError("upstream must not be called")):
            results = geo_module.search_places("JFK")
        self.assertEqual(results[0]["display_name"], first["display_name"])
        self.assertTrue(any("Terminal 1" in r["display_name"]
                            for r in results))

    def test_snapshot_covers_all_popular_queries(self):
        geo_module._SNAPSHOT_LOADED = False
        geo_module.load_places_snapshot()
        missing = [q for q in geo_module._POPULAR_SEARCH_QUERIES
                   if (q.lower(), 5) not in geo_module._search_cache]
        self.assertEqual(missing, [])

    def test_snapshot_endpoint_is_fast_and_complete(self):
        geo_module._SNAPSHOT_LOADED = False
        geo_module.load_places_snapshot()
        resp = self.client.get("/api/places/search?q=Times%20Square&limit=5")
        self.assertEqual(resp.status_code, 200)
        results = resp.get_json()["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["display_name"].split(",")[0],
                         "Times Square")

    def test_missing_snapshot_file_never_raises(self):
        geo_module._SNAPSHOT_LOADED = False
        with mock.patch.object(geo_module, "_SNAPSHOT_PATH",
                               "/nonexistent/places.json"):
            geo_module.load_places_snapshot()  # must not raise
        self.assertEqual(geo_module._search_cache, {})

    def test_warmup_thread_not_started_in_tests(self):
        # NOEL_SEARCH_WARMUP is unset in tests: importing the app must
        # never start the background refresh thread.
        self.assertFalse(geo_module._refresh_started)


class TestPhotonFallback(SpeedTestCase):
    def _routed(self, nominatim_exc=True, photon_payload=None):
        def fake_get(url):
            if "photon.komoot.io" in url:
                if photon_payload is None:
                    raise urllib.error.URLError("photon down")
                return photon_payload
            if nominatim_exc:
                raise urllib.error.URLError("nominatim blocked")
            return NOMINATIM_JFK
        return fake_get

    def test_search_falls_back_to_photon_airport_first(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(
                                   photon_payload=PHOTON_JFK)):
            results = geo_module.search_places("JFK")
        self.assertTrue(results[0]["display_name"].startswith(
            "John F. Kennedy International Airport"))
        self.assertTrue(results[0]["airport"])
        names = [r["display_name"].split(",")[0] for r in results]
        self.assertEqual(names.count("JFK Expressway"), 1)

    def test_search_photon_failure_returns_empty_list(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(photon_payload=None)):
            self.assertEqual(geo_module.search_places("JFK"), [])

    def test_search_no_match_does_not_call_photon(self):
        urls = []

        def fake_get(url):
            urls.append(url)
            if "photon.komoot.io" in url:
                raise AssertionError("Photon must not be called on no-match")
            return []  # Nominatim answered: genuine no match
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=fake_get):
            self.assertEqual(geo_module.search_places("zzzqqq"), [])
        self.assertEqual(len(urls), 1)
        self.assertIn("nominatim.openstreetmap.org", urls[0])

    def test_geocode_falls_back_to_photon(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=self._routed(
                                   photon_payload=PHOTON_JFK)):
            coords, details, errored = geo_module._geocode_query("JFK")
        self.assertFalse(errored)
        # Photon ranked the airport first, so geocode lands on it.
        self.assertAlmostEqual(coords[0], 40.6429479, places=3)
        self.assertAlmostEqual(coords[1], -73.7793734, places=3)
        self.assertEqual(details.get("state"), "New York")


class TestRefresh(SpeedTestCase):
    def test_refresh_replaces_on_live_and_restores_on_failure(self):
        geo_module._SNAPSHOT_LOADED = False
        geo_module.load_places_snapshot()
        snapshot_jfk = geo_module._search_cache[("jfk", 5)]
        sleeps = []

        def fake_search(query, limit):
            if query == "JFK":
                return [{"display_name": "Fresh JFK, New York",
                         "lat": 40.64, "lon": -73.78, "address": {},
                         "airport": True}]
            return []  # every other query: live failure

        geo_module.refresh_popular_places(
            search_fn=fake_search, sleep_fn=sleeps.append)
        self.assertEqual(
            geo_module._search_cache[("jfk", 5)][0]["display_name"],
            "Fresh JFK, New York")
        # Failed queries keep their snapshot values.
        self.assertEqual(geo_module._search_cache[("jfk", 5)][0]["display_name"],
                         "Fresh JFK, New York")
        self.assertEqual(
            geo_module._search_cache[("times square", 5)][0]["display_name"]
            .split(",")[0], "Times Square")
        self.assertEqual(len(sleeps),
                         len(geo_module._POPULAR_SEARCH_QUERIES))

    def test_refresh_never_raises(self):
        def boom(query, limit):
            raise RuntimeError("boom")
        geo_module.refresh_popular_places(search_fn=boom, sleep_fn=lambda s: None)


class TestRouteCache(SpeedTestCase):
    def test_repeat_route_makes_one_upstream_call(self):
        urls = []

        def fake_get(url):
            urls.append(url)
            return OSRM_ROUTE
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=fake_get):
            first = geo_module.route_miles(40.6413, -73.7781,
                                           40.7580, -73.9855)
            second = geo_module.route_miles(40.6413, -73.7781,
                                            40.7580, -73.9855)
            geometry = geo_module.route_geometry(40.6413, -73.7781,
                                                 40.7580, -73.9855)
        self.assertEqual(first, second)
        self.assertEqual(len(urls), 1)
        self.assertEqual(geometry, [(40.6413, -73.7781), (40.7580, -73.9855)])


class TestTilesAndDeploy(SpeedTestCase):
    def test_carto_dark_tiles_in_customer_js(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in ("static/js/customer.js", "static/js/customer-app.js"):
            with open(os.path.join(root, name), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("basemaps.cartocdn.com/dark_all", text, name)
            self.assertIn("© OpenStreetMap contributors © CARTO", text, name)
            self.assertNotIn("tile.openstreetmap.org", text, name)

    def test_render_uses_threaded_gunicorn_and_warmup(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "render.yaml"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("gunicorn app:app --workers 1 --threads 2", text)
        self.assertIn("NOEL_SEARCH_WARMUP", text)


if __name__ == "__main__":
    unittest.main()
