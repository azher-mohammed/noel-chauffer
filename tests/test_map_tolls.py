"""Tests for automatic map-based toll estimation (owner decision 2026-11-17).

The rule: the toll follows the actual route, Uber-style. Every tolled
crossing the route polyline passes through is charged at the verified
E-ZPass rate (Port Authority $16.79 entering New York only; MTA $7.46
both directions), PLUS the $16.79 return toll on New York -> New
Jersey trips (the outbound Hudson crossing westbound is free, so
there is no double-counting). When no route geometry is available the
Hudson toll is compulsory: ANY trip between New York and New Jersey
in EITHER direction carries $16.79.

Named examples from the owner, as explicit cases: Midtown Tunnel and
RFK Bridge are TOLLED; Queensboro Bridge is FREE ($0).

All geometries here are FIXTURES — no live OSRM calls in unit tests.
The gates themselves were validated against 24 real OSRM routes
before this module was written.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-map-tolls-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "map-tolls-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules): sedan total $192.58, driver $72.00 before toll.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
from pricing import estimate_upfront_toll  # noqa: E402
from tolls import detect_crossing_tolls  # noqa: E402

JFK_DISPLAY = "Terminal 1, JFK Access Road, Queens, New York, 11430, United States"
JERSEY_CITY_DISPLAY = "Jersey City, Hudson County, New Jersey, United States"
EWR_DISPLAY = "Newark Liberty International Airport, Newark, Essex County, New Jersey, United States"
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Map Toll Customer"}


def approx(a, b):
    return a is not None and abs(float(a) - float(b)) < 0.005


# --- fixture geometries: (lat, lng) pairs in travel order -------------------
# Each fixture crosses its gate cleanly through (not just touching it),
# following the real road centerlines the gates were placed on.

# Queens -> Manhattan via the Queens-Midtown Tunnel (TOLLED $7.46).
MIDTOWN_TUNNEL = [(40.7416, -73.9510), (40.7430, -73.9610), (40.7475, -73.9710)]
# Queens -> Manhattan via the Queensboro Bridge (FREE $0): crosses the
# East River north of the Midtown Tunnel gate.
QUEENSBORO_BRIDGE = [(40.7480, -73.9480), (40.7520, -73.9560), (40.7550, -73.9650)]
# Queensboro Bridge, then south on Roosevelt Island Main Street (FREE):
# must NOT trip the Midtown Tunnel gate.
QUEENSBORO_MAIN_ST = [(40.7480, -73.9480), (40.7520, -73.9560),
                      (40.7530, -73.9540), (40.7450, -73.9530)]
# RFK Bridge, Queens leg (TOLLED $7.46).
RFK_QUEENS = [(40.7740, -73.9220), (40.7800, -73.9270), (40.7860, -73.9300)]
# RFK Bridge, Bronx leg (TOLLED $7.46).
RFK_BRONX = [(40.7960, -73.9210), (40.8030, -73.9145), (40.8070, -73.9080)]
# RFK Bridge, both legs in one trip: ONE toll, not two.
RFK_BOTH = RFK_QUEENS + [(40.7960, -73.9210)] + RFK_BRONX[1:]
# Holland Tunnel eastbound, entering New York (TOLLED $16.79).
HOLLAND_EAST = [(40.7270, -74.0280), (40.7255, -74.0150), (40.7240, -74.0080)]
# Holland Tunnel westbound, leaving New York (FREE $0).
HOLLAND_WEST = list(reversed(HOLLAND_EAST))
# Lincoln Tunnel eastbound (TOLLED $16.79).
LINCOLN_EAST = [(40.7620, -74.0100), (40.7590, -74.0000), (40.7570, -73.9930)]
# George Washington Bridge eastbound (TOLLED $16.79) and westbound (FREE).
GWB_EAST = [(40.8540, -73.9650), (40.8510, -73.9500), (40.8490, -73.9430)]
GWB_WEST = list(reversed(GWB_EAST))
# Hugh L. Carey Tunnel (TOLLED $7.46 both directions).
CAREY_TUNNEL = [(40.6830, -74.0060), (40.6960, -74.0135), (40.7040, -74.0150)]
# Whitestone Bridge (TOLLED $7.46).
WHITESTONE = [(40.7970, -73.8260), (40.8030, -73.8300), (40.8080, -73.8330)]
# Throgs Neck Bridge (TOLLED $7.46).
THROGS_NECK = [(40.8000, -73.7940), (40.8100, -73.7945), (40.8160, -73.7980)]
# Verrazzano-Narrows Bridge (TOLLED $7.46).
VERRAZZANO = [(40.6120, -74.0310), (40.6050, -74.0470), (40.6020, -74.0600)]
# Bayonne Bridge, New Jersey -> New York, travelling WEST (TOLLED
# $16.79: Staten Island lies west of Bayonne, so entering New York
# means travelling west here). The reverse is FREE.
BAYONNE_WEST = [(40.6540, -74.1340), (40.6440, -74.1415), (40.6330, -74.1455)]
BAYONNE_EAST = list(reversed(BAYONNE_WEST))
# Goethals Bridge eastbound (TOLLED $16.79).
GOETHALS_EAST = [(40.6320, -74.1920), (40.6285, -74.1840), (40.6255, -74.1780)]
# Outerbridge Crossing eastbound (TOLLED $16.79).
OUTERBRIDGE_EAST = [(40.5250, -74.2440), (40.5254, -74.2300), (40.5210, -74.2260)]
# Near misses: cross a gate's longitude/latitude OUTSIDE the gate
# segment — must stay $0.
NEAR_MISS_SOUTH_OF_HOLLAND = [(40.7180, -74.0250), (40.7180, -74.0150),
                              (40.7180, -74.0050)]
NEAR_MISS_QUEENS_SHORE = [(40.7480, -73.9550), (40.7440, -73.9520),
                          (40.7400, -73.9500)]
# JFK -> Jersey City via the Midtown Tunnel, then the Holland Tunnel
# WESTBOUND (free): route toll $7.46 only; the $16.79 return toll is
# added by the estimator, not by geometry — no double-counting.
MIDTOWN_THEN_HOLLAND_WEST = [
    (40.7416, -73.9510), (40.7430, -73.9610), (40.7475, -73.9710),
    (40.7240, -74.0080), (40.7255, -74.0150), (40.7270, -74.0280),
]


class DetectionCase(unittest.TestCase):
    """Gate-segment intersection on fixture geometries."""

    def assert_detect(self, geometry, total, names):
        got_total, got_names = detect_crossing_tolls(geometry)
        self.assertEqual(got_total, Decimal(total), geometry)
        self.assertEqual(got_names, names, geometry)

    def test_midtown_tunnel_is_tolled(self):
        self.assert_detect(MIDTOWN_TUNNEL, "7.46", ["Queens-Midtown Tunnel"])

    def test_rfk_bridge_is_tolled_queens_leg(self):
        self.assert_detect(RFK_QUEENS, "7.46", ["RFK Bridge"])

    def test_rfk_bridge_is_tolled_bronx_leg(self):
        self.assert_detect(RFK_BRONX, "7.46", ["RFK Bridge"])

    def test_rfk_bridge_both_legs_count_once(self):
        # One toll covers all RFK spans.
        self.assert_detect(RFK_BOTH, "7.46", ["RFK Bridge"])

    def test_queensboro_bridge_is_free(self):
        self.assert_detect(QUEENSBORO_BRIDGE, "0.00", [])

    def test_queensboro_then_roosevelt_main_st_is_free(self):
        # Driving south on Roosevelt Island Main Street must not trip
        # the Midtown Tunnel gate.
        self.assert_detect(QUEENSBORO_MAIN_ST, "0.00", [])

    def test_holland_tunnel_eastbound_tolled_westbound_free(self):
        self.assert_detect(HOLLAND_EAST, "16.79", ["Holland Tunnel"])
        self.assert_detect(HOLLAND_WEST, "0.00", [])

    def test_lincoln_tunnel_eastbound_tolled(self):
        self.assert_detect(LINCOLN_EAST, "16.79", ["Lincoln Tunnel"])

    def test_gwb_eastbound_tolled_westbound_free(self):
        self.assert_detect(GWB_EAST, "16.79", ["George Washington Bridge"])
        self.assert_detect(GWB_WEST, "0.00", [])

    def test_carey_tunnel_tolled_both_directions(self):
        self.assert_detect(CAREY_TUNNEL, "7.46", ["Hugh L. Carey Tunnel"])
        self.assert_detect(list(reversed(CAREY_TUNNEL)), "7.46",
                           ["Hugh L. Carey Tunnel"])

    def test_whitestone_bridge_tolled(self):
        self.assert_detect(WHITESTONE, "7.46", ["Whitestone Bridge"])

    def test_throgs_neck_bridge_tolled(self):
        self.assert_detect(THROGS_NECK, "7.46", ["Throgs Neck Bridge"])

    def test_verrazzano_bridge_tolled(self):
        self.assert_detect(VERRAZZANO, "7.46", ["Verrazzano-Narrows Bridge"])

    def test_bayonne_bridge_westbound_tolled_eastbound_free(self):
        # Entering New York across the Bayonne Bridge means
        # travelling west (Staten Island lies west of Bayonne).
        self.assert_detect(BAYONNE_WEST, "16.79", ["Bayonne Bridge"])
        self.assert_detect(BAYONNE_EAST, "0.00", [])

    def test_goethals_bridge_eastbound_tolled(self):
        self.assert_detect(GOETHALS_EAST, "16.79", ["Goethals Bridge"])

    def test_outerbridge_crossing_eastbound_tolled(self):
        self.assert_detect(OUTERBRIDGE_EAST, "16.79", ["Outerbridge Crossing"])

    def test_multiple_crossings_sum(self):
        route = VERRAZZANO + BAYONNE_WEST
        self.assert_detect(route, "24.25",
                           ["Verrazzano-Narrows Bridge", "Bayonne Bridge"])

    def test_near_misses_are_free(self):
        self.assert_detect(NEAR_MISS_SOUTH_OF_HOLLAND, "0.00", [])
        self.assert_detect(NEAR_MISS_QUEENS_SHORE, "0.00", [])

    def test_empty_and_degenerate_geometry(self):
        self.assert_detect(None, "0.00", [])
        self.assert_detect([], "0.00", [])
        self.assert_detect([(40.7580, -73.9855)], "0.00", [])


class EstimateUpfrontTollCase(unittest.TestCase):
    """The shared helper: geometry tolls + return toll + fallback."""

    def test_geometry_midtown_ny_to_ny(self):
        self.assertEqual(
            estimate_upfront_toll("New York", "New York", geometry=MIDTOWN_TUNNEL),
            Decimal("7.46"))

    def test_geometry_queensboro_ny_to_ny_is_zero(self):
        self.assertEqual(
            estimate_upfront_toll("New York", "New York",
                                  geometry=QUEENSBORO_BRIDGE),
            Decimal("0.00"))

    def test_geometry_ny_to_nj_keeps_return_toll(self):
        # Free route + return toll: $16.79, from the return leg only.
        self.assertEqual(
            estimate_upfront_toll("New York", "New Jersey",
                                  geometry=QUEENSBORO_BRIDGE),
            Decimal("16.79"))

    def test_geometry_ny_to_nj_no_double_count(self):
        # Midtown Tunnel ($7.46) + Holland westbound ($0) + return
        # toll ($16.79) = $24.25. The Hudson crossing is charged
        # once, as the return leg — never twice.
        self.assertEqual(
            estimate_upfront_toll("New York", "New Jersey",
                                  geometry=MIDTOWN_THEN_HOLLAND_WEST),
            Decimal("24.25"))

    def test_geometry_nj_to_ny_holland_eastbound(self):
        # Outbound Hudson crossing eastbound: geometry toll only, no
        # return toll (the return leg goes back to New Jersey).
        self.assertEqual(
            estimate_upfront_toll("New Jersey", "New York",
                                  geometry=HOLLAND_EAST),
            Decimal("16.79"))

    def test_geometry_nj_to_ny_free_route_is_zero(self):
        # Geometry available and no tolled crossing: $0. The
        # compulsory fallback applies only when geometry is missing.
        self.assertEqual(
            estimate_upfront_toll("New Jersey", "New York",
                                  geometry=QUEENSBORO_BRIDGE),
            Decimal("0.00"))

    def test_fallback_no_geometry_ny_to_nj(self):
        self.assertEqual(
            estimate_upfront_toll("New York", "New Jersey"), Decimal("16.79"))

    def test_fallback_no_geometry_nj_to_ny(self):
        # Extended rule: the Hudson toll is compulsory in EITHER
        # direction when the map is not connected.
        self.assertEqual(
            estimate_upfront_toll("New Jersey", "New York"), Decimal("16.79"))

    def test_fallback_no_geometry_same_state_is_zero(self):
        self.assertEqual(
            estimate_upfront_toll("New York", "New York"), Decimal("0.00"))
        self.assertEqual(
            estimate_upfront_toll("New Jersey", "New Jersey"), Decimal("0.00"))

    def test_fallback_no_geometry_other_states_are_zero(self):
        self.assertEqual(
            estimate_upfront_toll("New York", "Pennsylvania"), Decimal("0.00"))
        self.assertEqual(
            estimate_upfront_toll("Connecticut", "New Jersey"), Decimal("0.00"))
        self.assertEqual(estimate_upfront_toll(None, None), Decimal("0.00"))

    def test_fallback_empty_geometry_list(self):
        self.assertEqual(
            estimate_upfront_toll("New York", "New Jersey", geometry=[]),
            Decimal("16.79"))

    def test_fallback_display_text_both_directions(self):
        self.assertEqual(
            estimate_upfront_toll(None, None, JFK_DISPLAY, JERSEY_CITY_DISPLAY),
            Decimal("16.79"))
        self.assertEqual(
            estimate_upfront_toll(None, None, EWR_DISPLAY,
                                  "Times Square, New York, NY"),
            Decimal("16.79"))

    def test_state_codes_and_case(self):
        self.assertEqual(
            estimate_upfront_toll("US-NY", "US-NJ"), Decimal("16.79"))
        self.assertEqual(
            estimate_upfront_toll("  new jersey ", "NEW YORK"), Decimal("16.79"))

    def test_bare_place_names_are_never_guessed(self):
        self.assertEqual(
            estimate_upfront_toll(None, None, "JFK", "Jersey City"),
            Decimal("0.00"))


class RouteGeometryCase(unittest.TestCase):
    """route_geometry is cache-only; route_miles warms the cache."""

    def setUp(self):
        self._saved = dict(geo_module._route_cache)
        geo_module._route_cache.clear()

    def tearDown(self):
        geo_module._route_cache.clear()
        geo_module._route_cache.update(self._saved)

    def test_uncached_coords_return_none_without_fetching(self):
        def boom(url):
            raise AssertionError("route_geometry must never fetch")
        with mock.patch.object(geo_module, "_http_get_json", side_effect=boom):
            self.assertIsNone(
                geo_module.route_geometry(40.6413, -73.7781, 40.7580, -73.9855))

    def test_route_miles_populates_geometry_from_same_call(self):
        payload = {"routes": [{"distance": 28968.192, "geometry": {"coordinates": [
            [-73.7781, 40.6413], [-73.9, 40.7], [-73.9855, 40.7580]]}}]}
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=payload) as fetch:
            self.assertEqual(
                geo_module.route_miles(40.6413, -73.7781, 40.7580, -73.9855),
                18.0)
            self.assertEqual(
                geo_module.route_geometry(40.6413, -73.7781, 40.7580, -73.9855),
                [(40.6413, -73.7781), (40.7, -73.9), (40.7580, -73.9855)])
            # Second call is served from the cache: no second fetch.
            self.assertEqual(
                geo_module.route_miles(40.6413, -73.7781, 40.7580, -73.9855),
                18.0)
            self.assertEqual(fetch.call_count, 1)

    def test_osrm_failure_falls_back_with_no_geometry(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=RuntimeError("down")):
            miles = geo_module.route_miles(40.6413, -73.7781, 40.7580, -73.9855)
            expected = round(
                geo_module.haversine_miles(40.6413, -73.7781,
                                           40.7580, -73.9855) * 1.3, 1)
            self.assertEqual(miles, expected)
            self.assertIsNone(
                geo_module.route_geometry(40.6413, -73.7781, 40.7580, -73.9855))


class MapTollBookingCase(unittest.TestCase):
    """End to end: quote, stored booking, and offer payload agree."""

    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0
        self._saved_address = dict(geo_module._geocode_address_cache)
        self._saved_routes = dict(geo_module._route_cache)
        geo_module._geocode_address_cache.clear()
        geo_module._route_cache.clear()

    def tearDown(self):
        geo_module._geocode_address_cache.clear()
        geo_module._geocode_address_cache.update(self._saved_address)
        geo_module._route_cache.clear()
        geo_module._route_cache.update(self._saved_routes)

    # -- helpers ---------------------------------------------------------
    def seed_geometry(self, geometry):
        """Seed the route cache as route_miles would after a live call."""
        key = geo_module._route_key(40.6413, -73.7781, 40.7580, -73.9855)
        geo_module._route_cache[key] = (18.0, geometry)

    def register_driver(self):
        self._driver_seq += 1
        phone = f"+1555009{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Map Driver {self._driver_seq}", "phone": phone,
            "email": f"map{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"M{self._driver_seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(photo_factory.VALID_PROFILE_PHOTO), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(b"fake png"), "license.png"),
            "doc_tlc_license": (io.BytesIO(b"fake png"), "tlc.png"),
            "doc_fh1": (io.BytesIO(b"fake png"), "fh1.png"),
            "doc_registration": (io.BytesIO(b"fake png"), "reg.png"),
            "doc_inspection": (io.BytesIO(b"fake png"), "insp.png"),
            "doc_vehicle_permit": (io.BytesIO(b"fake png"), "permit.png"),
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Map Toll Customer",
            "phone": f"+1555006{self._phone_seq:04d}",
            "email": "maptoll@test.com",
            "pickup": JFK_DISPLAY, "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def stored_toll(self, booking_id):
        with app_module.app.app_context():
            booking = app_module.db.session.get(app_module.Booking, booking_id)
            return booking.toll

    def offers(self, token):
        return self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token}).get_json()

    # -- quote + stored booking -------------------------------------------
    def test_midtown_route_quote_and_booking_carry_toll(self):
        self.seed_geometry(MIDTOWN_TUNNEL)
        booking = self.book()
        # 18.0 mi sedan: $162.00 + $16.20 + $14.38 + $7.46 = $200.04.
        # SUV: $180.00 + $18.00 + $15.98 + $7.46 = $221.44.
        self.assertTrue(approx(booking["total"], "200.04"), booking)
        self.assertTrue(approx(booking["class_totals"]["sedan"], "200.04"), booking)
        self.assertTrue(approx(booking["class_totals"]["suv"], "221.44"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "7.46"))
        got = self.client.get(f"/api/bookings/{booking['id']}").get_json()["booking"]
        self.assertTrue(approx(got["total"], "200.04"), got)
        self.assertTrue(approx(got["class_totals"]["suv"], "221.44"), got)

    def test_queensboro_route_quote_has_zero_toll(self):
        self.seed_geometry(QUEENSBORO_BRIDGE)
        booking = self.book()
        self.assertTrue(approx(booking["total"], "192.58"), booking)
        self.assertTrue(approx(booking["class_totals"]["sedan"], "192.58"), booking)
        self.assertTrue(approx(booking["class_totals"]["suv"], "213.98"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "0.00"))

    def test_rfk_route_quote_carries_toll(self):
        self.seed_geometry(RFK_QUEENS)
        booking = self.book()
        self.assertTrue(approx(booking["total"], "200.04"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "7.46"))

    def test_nj_trip_route_toll_plus_return_no_double_count(self):
        self.seed_geometry(MIDTOWN_THEN_HOLLAND_WEST)
        booking = self.book(dropoff=JERSEY_CITY_DISPLAY)
        # $7.46 route toll + $16.79 return toll = $24.25.
        # Sedan: $162.00 + $16.20 + $14.38 + $24.25 = $216.83.
        # SUV: $180.00 + $18.00 + $15.98 + $24.25 = $238.23.
        self.assertTrue(approx(booking["total"], "216.83"), booking)
        self.assertTrue(approx(booking["class_totals"]["sedan"], "216.83"), booking)
        self.assertTrue(approx(booking["class_totals"]["suv"], "238.23"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "24.25"))

    def test_no_geometry_nj_to_ny_falls_back_to_return_toll(self):
        # No seeded geometry (OSRM failure): the compulsory fallback
        # charges the Hudson toll in EITHER direction.
        booking = self.book(pickup=EWR_DISPLAY, dropoff="Times Square, New York")
        self.assertTrue(approx(booking["total"], "209.37"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "16.79"))

    def test_no_geometry_ny_to_ny_stays_zero(self):
        booking = self.book()
        self.assertTrue(approx(booking["total"], "192.58"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "0.00"))

    def test_hourly_ride_unaffected_by_geometry(self):
        self.seed_geometry(MIDTOWN_TUNNEL)
        booking = self.book(ride_type="hourly", hours=2, dropoff="",
                            pickup="Central Park, New York")
        self.assertTrue(approx(booking["total"], "180.00"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "0.00"))

    # -- driver offer payload (before accept) ------------------------------
    def test_offer_payload_carries_map_toll(self):
        _, token = self.register_driver()
        self.seed_geometry(MIDTOWN_TUNNEL)
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        offers = self.offers(token)
        self.assertEqual(len(offers), 1)
        # 18 miles x $4 sedan rate = $72 driving pay + $7.46 toll.
        self.assertTrue(approx(offers[0]["toll"], "7.46"), offers[0])
        self.assertTrue(approx(offers[0]["earnings"], "79.46"), offers[0])
        forbidden = {"miles", "fare", "total", "gratuity", "tax", "profit"}
        self.assertFalse(forbidden & set(offers[0]))

    def test_owner_can_still_adjust_map_toll(self):
        _, token = self.register_driver()
        self.seed_geometry(MIDTOWN_TUNNEL)
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/toll",
                                json={"toll": 12.00})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        offers = self.offers(token)
        self.assertTrue(approx(offers[0]["toll"], "12.00"), offers[0])
        self.assertTrue(approx(offers[0]["earnings"], "84.00"), offers[0])
        self.assertTrue(approx(self.stored_toll(booking["id"]), "12.00"))


if __name__ == "__main__":
    unittest.main()
