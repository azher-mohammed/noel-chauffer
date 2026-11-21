"""Exact per-mile fares: typed text must resolve to the true place, and an
unresolvable address must never be priced on an invented distance.

Regression for the live 2026-11-17 booking NOEL-9TR127: the pickup was
typed as "JFK Terminal 1 Arrivals" (no suggestion picked) and priced at
$106.99 — exactly 10.0 miles — because Nominatim returns no result for
that phrase and distance_miles silently substituted a 10-mile default.
The true road distance JFK Terminal 1 -> Times Square is ~18 miles.

Rules pinned here:
- A picked suggestion's coordinates are priced as-is (never re-resolved
  from text), so the fare is for exactly the place the customer picked.
- Typed text that Nominatim cannot match is retried once without
  standalone "arrivals"/"departures" words ("JFK Terminal 1 Arrivals"
  -> "JFK Terminal 1"), so terminal phrasing resolves to the terminal.
- Geocode failures and empty results are never cached: a transient
  outage must not poison the process cache.
- If either address still cannot be resolved, distance_miles returns
  miles=None and booking creation is rejected with a clear error —
  there is no default-miles fallback anywhere in the fare path.

Run:  python -m unittest discover -s tests -v
"""

import importlib
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-exact-miles-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "exact-miles-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402
from pricing import compute_one_way  # noqa: E402

import app as app_module  # noqa: E402

# Other test modules replace geo.distance_miles with a fixed 18.0-mile
# stub at import time; these tests need the REAL implementation, so it
# is restored (via reload) in setUp and the stub re-installed in
# tearDown, keeping every other module's expectations intact whatever
# the run order.
_STUB_MILES = (18.0, (40.6413, -73.7781), (40.7580, -73.9855))


def _restore_real_distance_miles():
    importlib.reload(geo_module)


def _install_stub_distance_miles():
    geo_module.distance_miles = lambda p, d: _STUB_MILES  # noqa: E731


def _terminal_payload(lat, lon):
    return [{"lat": str(lat), "lon": str(lon),
             "address": {"state": "New York", "city": "New York"}}]


TERMINAL_1 = (40.6430714, -73.7890699)
TERMINAL_1_ARRIVALS = (40.6434795, -73.7900299)
TIMES_SQUARE = (40.7570095, -73.9859724)
ARRIVALS_DISPLAY = ("Terminal 1 Arrivals, Queens, Queens County, New York, "
                    "11430, United States")


class _CacheGuard(unittest.TestCase):
    """Save/restore the geo caches around each test."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        self._saved_coords = dict(geo_module._geocode_cache)
        self._saved_address = dict(geo_module._geocode_address_cache)
        self._saved_routes = dict(geo_module._route_cache)
        geo_module._geocode_cache.clear()
        geo_module._geocode_address_cache.clear()
        geo_module._route_cache.clear()

    def tearDown(self):
        geo_module._geocode_cache.clear()
        geo_module._geocode_cache.update(self._saved_coords)
        geo_module._geocode_address_cache.clear()
        geo_module._geocode_address_cache.update(self._saved_address)
        geo_module._route_cache.clear()
        geo_module._route_cache.update(self._saved_routes)


class GeocodeRetryCase(_CacheGuard):
    """Terminal phrasing retries without arrivals/departures words."""

    def test_terminal_phrase_retries_and_resolves(self):
        calls = []

        def fetch(url):
            calls.append(url)
            if "JFK%20Terminal%201%20Arrivals" in url:
                return []
            if "JFK%20Terminal%201" in url:
                return _terminal_payload(*TERMINAL_1)
            raise AssertionError("unexpected URL: " + url)

        with mock.patch.object(geo_module, "_http_get_json", side_effect=fetch):
            self.assertEqual(geo_module.geocode("JFK Terminal 1 Arrivals"),
                             TERMINAL_1)
        # 3 calls: Nominatim "JFK Terminal 1 Arrivals" (empty) ->
        # Photon fallback (also empty) -> strip-retry "JFK Terminal 1".
        self.assertEqual(len(calls), 3)

    def test_lookup_is_usa_only(self):
        seen = []

        def fetch(url):
            seen.append(url)
            return _terminal_payload(*TERMINAL_1)

        with mock.patch.object(geo_module, "_http_get_json", side_effect=fetch):
            geo_module.geocode("JFK Terminal 1")
        self.assertTrue(seen)
        for url in seen:
            self.assertIn("countrycodes=us", url)

    def test_no_retry_when_first_query_matches(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=_terminal_payload(*TERMINAL_1)) as fetch:
            self.assertEqual(geo_module.geocode("JFK Terminal 1"), TERMINAL_1)
            self.assertEqual(fetch.call_count, 1)

    def test_no_retry_on_request_error(self):
        # A request error must not trigger the arrivals/departures
        # strip-retry. The Photon fallback (a different provider, one
        # extra call) still runs — it is not the strip-retry.
        urls = []

        def fetch(url):
            urls.append(url)
            raise RuntimeError("down")

        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=fetch):
            self.assertIsNone(geo_module.geocode("JFK Terminal 1 Arrivals"))
        nominatim_urls = [u for u in urls
                          if "nominatim.openstreetmap.org" in u]
        self.assertEqual(len(nominatim_urls), 1)
        self.assertIn("JFK%20Terminal%201%20Arrivals", nominatim_urls[0])
        photon_urls = [u for u in urls if "photon.komoot.io" in u]
        self.assertEqual(len(photon_urls), 1)


class GeocodeCacheCase(_CacheGuard):
    """Failures and empty results are never cached; successes are."""

    def test_failures_are_not_cached(self):
        calls = {"n": 0}

        def fetch(url):
            calls["n"] += 1
            # Each failing geocode now makes 2 upstream calls (Nominatim
            # + the Photon fallback), so the first 4 fail and the 5th
            # succeeds.
            if calls["n"] <= 4:
                raise RuntimeError("down")
            return _terminal_payload(*TERMINAL_1)

        with mock.patch.object(geo_module, "_http_get_json", side_effect=fetch):
            self.assertIsNone(geo_module.geocode("JFK Terminal 1"))
            self.assertIsNone(geo_module.geocode("JFK Terminal 1"))
            # A later success must still get through: no poisoned miss.
            self.assertEqual(geo_module.geocode("JFK Terminal 1"), TERMINAL_1)
        self.assertEqual(calls["n"], 5)

    def test_empty_results_are_not_cached(self):
        # Each empty geocode now makes 2 upstream calls (Nominatim
        # empty -> Photon fallback, also empty), and neither result
        # is cached, so a repeat still goes upstream.
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=[]) as fetch:
            self.assertIsNone(geo_module.geocode("Nowhere Street 1"))
            self.assertIsNone(geo_module.geocode("Nowhere Street 1"))
            self.assertEqual(fetch.call_count, 4)

    def test_success_is_cached(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=_terminal_payload(*TERMINAL_1)) as fetch:
            self.assertEqual(geo_module.geocode("JFK Terminal 1"), TERMINAL_1)
            self.assertEqual(geo_module.geocode("JFK Terminal 1"), TERMINAL_1)
            self.assertEqual(fetch.call_count, 1)


class DistanceMilesCase(_CacheGuard):
    """distance_miles: no invented miles, coords used as-is."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        super().setUp()
        _restore_real_distance_miles()

    def tearDown(self):
        _install_stub_distance_miles()
        super().tearDown()

    def test_unresolvable_side_returns_no_miles(self):
        def fake_geocode(address):
            return None if "Arrivals" in address else TIMES_SQUARE

        with mock.patch.object(geo_module, "geocode", side_effect=fake_geocode):
            miles, pc, dc = geo_module.distance_miles(
                "JFK Terminal 1 Arrivals", "Times Square, New York")
        self.assertIsNone(miles)
        self.assertIsNone(pc)
        self.assertEqual(dc, TIMES_SQUARE)

    def test_supplied_coords_skip_geocoding(self):
        def boom(address):
            raise AssertionError("geocode must not run when coords are given")

        with mock.patch.object(geo_module, "geocode", side_effect=boom):
            with mock.patch.object(geo_module, "_fetch_route",
                                   return_value=(17.9, None)):
                miles, pc, dc = geo_module.distance_miles(
                    "JFK Terminal 1 Arrivals", "Times Square, New York",
                    pickup_coords=TERMINAL_1_ARRIVALS,
                    dropoff_coords=TIMES_SQUARE)
        self.assertEqual(miles, 17.9)
        self.assertEqual(pc, TERMINAL_1_ARRIVALS)
        self.assertEqual(dc, TIMES_SQUARE)

    def test_invalid_coords_fall_back_to_geocoding(self):
        seen = []

        def fake_geocode(address):
            seen.append(address)
            return TERMINAL_1 if "JFK" in address else TIMES_SQUARE

        with mock.patch.object(geo_module, "geocode", side_effect=fake_geocode):
            with mock.patch.object(geo_module, "_fetch_route",
                                   return_value=(17.9, None)):
                miles, _pc, _dc = geo_module.distance_miles(
                    "JFK Terminal 1", "Times Square, New York",
                    pickup_coords="garbage", dropoff_coords=(999.0, 0.0))
        self.assertEqual(miles, 17.9)
        self.assertEqual(seen, ["JFK Terminal 1", "Times Square, New York"])


class BookingExactMilesCase(unittest.TestCase):
    """End to end: rejection on unresolvable text, coords priced as-is."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        _restore_real_distance_miles()
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()

    def tearDown(self):
        _install_stub_distance_miles()
        geo_module._geocode_cache.clear()
        geo_module._geocode_address_cache.clear()
        geo_module._route_cache.clear()

    def _payload(self, **extra):
        payload = {
            "customer_name": "Exact Miles", "phone": "+15550001111",
            "email": "exact@test.com", "pickup": "JFK Terminal 1 Arrivals",
            "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        return payload

    def test_unresolvable_address_rejected_without_booking(self):
        def fake_geocode(address):
            return None if "Arrivals" in address else TIMES_SQUARE

        with mock.patch.object(geo_module, "geocode", side_effect=fake_geocode):
            resp = self.client.post("/api/bookings", json=self._payload())
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True))
        self.assertIn("suggestions", resp.get_json()["error"])
        with app_module.app.app_context():
            self.assertEqual(app_module.Booking.query.count(), 0)

    def test_picked_suggestion_coords_price_without_any_lookup(self):
        def boom(*args, **kwargs):
            raise AssertionError("no upstream lookup may run with coords")

        expected = round(
            geo_module.haversine_miles(
                TERMINAL_1_ARRIVALS[0], TERMINAL_1_ARRIVALS[1],
                TIMES_SQUARE[0], TIMES_SQUARE[1]) * 1.3, 1)
        with mock.patch.object(geo_module, "_http_get_json", side_effect=boom):
            with mock.patch.object(geo_module, "geocode", side_effect=boom):
                resp = self.client.post("/api/bookings", json=self._payload(
                    pickup_lat=TERMINAL_1_ARRIVALS[0],
                    pickup_lng=TERMINAL_1_ARRIVALS[1],
                    dropoff_lat=TIMES_SQUARE[0],
                    dropoff_lng=TIMES_SQUARE[1]))
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        with app_module.app.app_context():
            booking = app_module.Booking.query.first()
            self.assertEqual(float(booking.miles), expected)
            self.assertEqual(booking.pickup_lat, TERMINAL_1_ARRIVALS[0])
            self.assertEqual(booking.pickup_lng, TERMINAL_1_ARRIVALS[1])
            self.assertEqual(booking.dropoff_lat, TIMES_SQUARE[0])
            self.assertEqual(booking.dropoff_lng, TIMES_SQUARE[1])

    def test_invalid_coords_ignored_and_text_resolves(self):
        def fake_geocode(address):
            return TERMINAL_1 if "JFK" in address else TIMES_SQUARE

        with mock.patch.object(geo_module, "geocode", side_effect=fake_geocode):
            with mock.patch.object(geo_module, "_fetch_route",
                                   return_value=(17.9, None)):
                resp = self.client.post("/api/bookings", json=self._payload(
                    pickup_lat=999.0, pickup_lng=0.0))
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        with app_module.app.app_context():
            booking = app_module.Booking.query.first()
            self.assertEqual(float(booking.miles), 17.9)


class PricingTotalsCase(unittest.TestCase):
    """Known totals at exactly 18.0 miles (JFK -> Times Square scale)."""

    def test_totals_without_toll(self):
        sedan = compute_one_way(Decimal("18.0"), toll=Decimal("0"))
        suv = compute_one_way(Decimal("18.0"), toll=Decimal("0"),
                              vehicle_class="suv")
        self.assertEqual(sedan["total"], Decimal("162.00"))
        self.assertEqual(suv["total"], Decimal("180.00"))

    def test_totals_with_midtown_tunnel_toll(self):
        sedan = compute_one_way(Decimal("18.0"), toll=Decimal("7.46"))
        suv = compute_one_way(Decimal("18.0"), toll=Decimal("7.46"),
                              vehicle_class="suv")
        self.assertEqual(sedan["total"], Decimal("169.46"))
        self.assertEqual(suv["total"], Decimal("187.46"))


class TypedTextMatchesSuggestionCase(_CacheGuard):
    """Typed terminal phrasing resolves to (essentially) the suggestion."""

    def test_display_name_and_typed_phrase_both_resolve(self):
        def fetch(url):
            if "JFK%20Terminal%201%20Arrivals" in url:
                return []
            if "Arrivals%2C%20Queens" in url:
                return _terminal_payload(*TERMINAL_1_ARRIVALS)
            if "JFK%20Terminal%201" in url:
                return _terminal_payload(*TERMINAL_1)
            raise AssertionError("unexpected URL: " + url)

        with mock.patch.object(geo_module, "_http_get_json", side_effect=fetch):
            suggestion_coords = geo_module.geocode(ARRIVALS_DISPLAY)
            typed_coords = geo_module.geocode("JFK Terminal 1 Arrivals")
        self.assertEqual(suggestion_coords, TERMINAL_1_ARRIVALS)
        self.assertIsNotNone(typed_coords)
        # The retry resolves to the terminal building, a short walk
        # from the arrivals roadway point — the same place, not a
        # fallback and not a different match.
        self.assertLess(abs(typed_coords[0] - suggestion_coords[0]), 0.01)
        self.assertLess(abs(typed_coords[1] - suggestion_coords[1]), 0.01)


if __name__ == "__main__":
    unittest.main()
