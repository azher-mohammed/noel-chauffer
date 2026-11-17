"""Tests for the embedded driver-app map (offer card + trip screen).

Owner request 2026-11-17 (voice call, "is pe map de sakte"): the driver
job card gets a small embedded map, and the trip screen the same map
larger. Free stack only — Leaflet + OpenStreetMap, the same as the
customer live map; coordinates and route geometry come from the server
(existing geo.py helpers, cached), never geocoded in the browser.

Rules enforced here:
- Markers say exactly 'Pick up' / 'Drop off'; hourly rides have no
  drop-off, so only the pickup marker shows.
- The driver map payload carries endpoints + route shape ONLY — no
  miles, fare, or any money figure, in offers, accept, or active-trip.
- The route line is decimated so the polled offers payload stays small.
- Polling never rebuilds maps: offer maps are created once per card
  and removed only when the offers signature changes; the trip map is
  reused for the same trip.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-drivermap-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "drivermap-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules): JFK coords -> Times Square coords.
PICKUP = (40.6413, -73.7781)
DROPOFF = (40.7580, -73.9855)
geo_module.distance_miles = lambda p, d: (18.0, PICKUP, DROPOFF)  # noqa: E731

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Map Customer"}
GEOMETRY = [(40.6413, -73.7781), (40.7000, -73.9000), (40.7580, -73.9855)]


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def warm_route_cache(geometry=GEOMETRY, miles=18.0):
    key = geo_module._route_key(PICKUP[0], PICKUP[1], DROPOFF[0], DROPOFF[1])
    geo_module._route_cache[key] = (miles, list(geometry))


class DriverMapApiCase(unittest.TestCase):
    def setUp(self):
        self._saved_routes = dict(geo_module._route_cache)
        self._saved_geocode = dict(geo_module._geocode_cache)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    def tearDown(self):
        geo_module._route_cache.clear()
        geo_module._route_cache.update(self._saved_routes)
        geo_module._geocode_cache.clear()
        geo_module._geocode_cache.update(self._saved_geocode)

    # -- helpers ---------------------------------------------------------
    def register_driver(self):
        self._driver_seq += 1
        phone = f"+1555007{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Map Driver {self._driver_seq}", "phone": phone,
            "email": f"md{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"M{self._driver_seq:05d}",
            "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(b"\xff\xd8\xff fake"), "photo.jpg"),
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Map Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "map@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def offers(self, token):
        return self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token}).get_json()

    # -- offers payload ---------------------------------------------------
    def test_offers_carry_map_endpoints_and_route_only(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        warm_route_cache()
        offers = self.offers(token)
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertFalse(FORBIDDEN_KEYS & set(offer), offer)
        self.assertIn("map", offer)
        # Endpoints + route shape only — exactly these three keys.
        self.assertEqual(set(offer["map"]), {"pickup", "dropoff", "route"})
        self.assertEqual(offer["map"]["pickup"], [PICKUP[0], PICKUP[1]])
        self.assertEqual(offer["map"]["dropoff"], [DROPOFF[0], DROPOFF[1]])
        self.assertEqual(offer["map"]["route"], [list(p) for p in GEOMETRY])

    def test_map_route_decimated_to_cap_endpoints_kept(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        long_geometry = [
            (40.6413 + i * 0.0001, -73.7781 - i * 0.0002) for i in range(1000)
        ]
        warm_route_cache(geometry=long_geometry)
        offers = self.offers(token)
        route = offers[0]["map"]["route"]
        self.assertEqual(len(route), app_module._MAP_GEOMETRY_MAX_POINTS)
        self.assertEqual(route[0], list(long_geometry[0]))
        self.assertEqual(route[-1], list(long_geometry[-1]))

    def test_cold_cache_means_no_route_line_and_no_fetch(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        geo_module._route_cache.clear()
        # Cache-only contract (same as toll estimation): a cold cache
        # means markers only, and polling offers must never fetch
        # upstream — fetching here could change toll estimation for
        # bookings created later in the same process.
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=AssertionError("must not fetch")):
            offers = self.offers(token)
        self.assertEqual(offers[0]["map"]["pickup"], [PICKUP[0], PICKUP[1]])
        self.assertEqual(offers[0]["map"]["dropoff"], [DROPOFF[0], DROPOFF[1]])
        self.assertIsNone(offers[0]["map"]["route"])

    def test_hourly_map_has_pickup_only(self):
        _, token = self.register_driver()
        booking = self.book(ride_type="hourly", hours=3, dropoff="")
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        # Hourly creation stores no coords: the cached server-side
        # geocode fallback supplies the pickup point.
        with mock.patch.object(geo_module, "geocode", return_value=PICKUP):
            offers = self.offers(token)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["map"]["pickup"], [PICKUP[0], PICKUP[1]])
        self.assertIsNone(offers[0]["map"]["dropoff"])
        self.assertIsNone(offers[0]["map"]["route"])

    def test_map_degrades_to_nulls_when_no_coords(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            row.pickup_lat = row.pickup_lng = None
            row.dropoff_lat = row.dropoff_lng = None
            app_module.db.session.commit()
        with mock.patch.object(geo_module, "geocode", return_value=None):
            resp = self.client.get("/api/drivers/me/offers",
                                   headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()[0]["map"],
                         {"pickup": None, "dropoff": None, "route": None})

    # -- accept + active-trip payloads ------------------------------------
    def test_accept_and_active_trip_carry_map(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        warm_route_cache()
        resp = self.client.post(
            f"/api/drivers/me/offers/{booking['id']}/accept",
            headers={"X-Driver-Token": token}, json={})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        accepted = resp.get_json()["booking"]
        self.assertFalse(FORBIDDEN_KEYS & set(accepted), accepted)
        self.assertEqual(accepted["map"]["pickup"], [PICKUP[0], PICKUP[1]])
        self.assertEqual(accepted["map"]["dropoff"], [DROPOFF[0], DROPOFF[1]])
        self.assertEqual(accepted["map"]["route"], [list(p) for p in GEOMETRY])
        resp = self.client.get("/api/drivers/me/active-trip",
                               headers={"X-Driver-Token": token})
        active = resp.get_json()["booking"]
        self.assertFalse(FORBIDDEN_KEYS & set(active), active)
        self.assertEqual(active["map"], accepted["map"])

    # -- helper units ------------------------------------------------------
    def test_decimate_keeps_short_geometry_and_rejects_degenerate(self):
        self.assertEqual(
            app_module._decimate_geometry([(1.0, 2.0), (3.0, 4.0)], 400),
            [[1.0, 2.0], [3.0, 4.0]])
        self.assertIsNone(app_module._decimate_geometry(None, 400))
        self.assertIsNone(app_module._decimate_geometry([(1.0, 2.0)], 400))
        self.assertIsNone(app_module._decimate_geometry([], 400))

    def test_map_helper_is_cache_only_and_never_fetches(self):
        source = read("app.py")
        start = source.index("def driver_map_data(booking):")
        helper = source[start:source.index("\n\n\n", start)]
        # Cache-only geometry: route_geometry reads the cache that
        # booking creation warmed; the helper never fetches upstream
        # and never touches a miles value.
        self.assertIn("geo_module.route_geometry(", helper)
        self.assertNotIn("route_miles", helper)
        self.assertNotIn("_http_get_json", helper)
        self.assertIn(
            'return {"pickup": pickup, "dropoff": dropoff, "route": route}',
            helper)


class DriverMapStaticCase(unittest.TestCase):
    def test_driver_page_includes_leaflet_like_customer_page(self):
        driver_html = read("static/driver.html")
        index_html = read("static/index.html")
        css = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        js = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        self.assertIn(css, index_html)
        self.assertIn(js, index_html)
        self.assertIn(css, driver_html)
        self.assertIn(js, driver_html)
        # Leaflet loads before the driver script that uses it.
        self.assertLess(driver_html.index(js),
                        driver_html.index("/static/js/driver.js"))
        self.assertIn('id="trip-map"', driver_html)

    def test_driver_js_marker_labels_exact_and_permanent(self):
        driver_js = read("static/js/driver.js")
        self.assertIn('bindTooltip("Pick up"', driver_js)
        self.assertIn('bindTooltip("Drop off"', driver_js)
        self.assertIn("permanent: true", driver_js)

    def test_drop_off_marker_only_when_dropoff_present(self):
        driver_js = read("static/js/driver.js")
        helper = driver_js[driver_js.index("function initTripMap"):]
        helper = helper[:helper.index("function removeOfferMaps")]
        self.assertLess(helper.index('"Pick up"'), helper.index("if (dropoff)"))
        self.assertLess(helper.index("if (dropoff)"), helper.index('"Drop off"'))

    def test_driver_js_osm_tiles_and_attribution(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("https://tile.openstreetmap.org/{z}/{x}/{y}.png", driver_js)
        self.assertIn("© OpenStreetMap contributors", driver_js)
        self.assertIn("L.polyline", driver_js)

    def test_offer_and_trip_maps_wired_to_api_map_data(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("initTripMap(mapEl, o.map)", driver_js)
        self.assertIn("initTripMap(el, t.map)", driver_js)
        self.assertIn("map: b.map || null", driver_js)
        self.assertIn('<div class="offer-map"></div>', driver_js)

    def test_offer_maps_removed_only_on_signature_change(self):
        driver_js = read("static/js/driver.js")
        render = driver_js[driver_js.index("function renderOffers"):]
        render = render[:render.index("function respondToOffer")]
        # Unchanged polls return early, before any map teardown.
        self.assertLess(render.index("if (sig === state.lastOffersSig) return;"),
                        render.index("removeOfferMaps();"))
        self.assertLess(render.index("removeOfferMaps();"),
                        render.index('box.innerHTML = "";'))
        self.assertIn("state.offerMaps[offerId(o)] = offerMap", render)

    def test_trip_map_reused_for_same_trip(self):
        driver_js = read("static/js/driver.js")
        self.assertIn("state.tripMapId === t.id", driver_js)
        self.assertIn("state.tripMap.remove()", driver_js)
        self.assertIn("renderTripMap(t)", driver_js)

    def test_map_css_present(self):
        css = read("static/css/driver.css")
        self.assertIn(".offer-map", css)
        self.assertIn("height: 170px", css)
        self.assertIn(".trip-map", css)
        self.assertIn("height: 240px", css)
        self.assertIn(".map-marker-label", css)


if __name__ == "__main__":
    unittest.main()
