"""Tests for the up-front NJ return toll (owner decision 2026-11-16).

The rule: a trip from New York to New Jersey carries a $16.79 toll
estimate from booking creation — the Port Authority return crossing
(Holland Tunnel / Lincoln Tunnel / George Washington Bridge), E-ZPass
peak rate, verified 2026-11-16. The estimate is added up front, like
Uber, so the customer is charged it in the single total and the
driver sees the separate Toll line on the offer card BEFORE
accepting. All other trips start at a $0 toll; the owner can still
adjust the toll afterwards in the dashboard (not on completed rides).

Why up front: the owner-set toll after booking lost the race — test
Booking #14 was accepted and completed within 74 seconds of creation,
before the toll could be set, and completed rides reject toll changes
(409). The estimate must therefore exist at creation time.

State detection: the geocoder address/state field first (read from
the cache populated by geocode(), no second upstream request), with
the address display text as fallback when the state is unavailable.

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
_tmpdir = tempfile.mkdtemp(prefix="noel-nj-toll-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "nj-toll-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules): sedan total $162.00, driver $95.00 (10-20 slab) before toll.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
import pricing  # noqa: E402
from pricing import estimate_return_toll  # noqa: E402

JFK_DISPLAY = "Terminal 1, JFK Access Road, Queens, New York, 11430, United States"
JERSEY_CITY_DISPLAY = "Jersey City, Hudson County, New Jersey, United States"
EWR_DISPLAY = "Newark Liberty International Airport, Newark, Essex County, New Jersey, United States"
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "NJ Toll Customer"}


def approx(a, b):
    return a is not None and abs(float(a) - float(b)) < 0.005


class EstimateReturnTollCase(unittest.TestCase):
    """The pure helper: geocoder state first, display text fallback."""

    def test_geocoder_states_ny_to_nj(self):
        self.assertEqual(estimate_return_toll("New York", "New Jersey"),
                         Decimal("16.79"))

    def test_geocoder_state_codes_and_case(self):
        self.assertEqual(estimate_return_toll("NY", "NJ"), Decimal("16.79"))
        self.assertEqual(estimate_return_toll("US-NY", "US-NJ"), Decimal("16.79"))
        self.assertEqual(estimate_return_toll("  new york ", "NEW JERSEY"),
                         Decimal("16.79"))

    def test_same_state_is_zero(self):
        self.assertEqual(estimate_return_toll("New York", "New York"),
                         Decimal("0.00"))
        self.assertEqual(estimate_return_toll("New Jersey", "New Jersey"),
                         Decimal("0.00"))

    def test_nj_to_ny_is_zero(self):
        # Only NY -> NJ carries the return-crossing estimate; the
        # reverse direction is $0 at creation (owner may adjust).
        self.assertEqual(estimate_return_toll("New Jersey", "New York"),
                         Decimal("0.00"))

    def test_other_states_are_zero(self):
        self.assertEqual(estimate_return_toll("New York", "Pennsylvania"),
                         Decimal("0.00"))
        self.assertEqual(estimate_return_toll("Connecticut", "New Jersey"),
                         Decimal("0.00"))
        self.assertEqual(estimate_return_toll(None, None), Decimal("0.00"))

    def test_display_text_fallback_ny_to_nj(self):
        self.assertEqual(
            estimate_return_toll(None, None, JFK_DISPLAY, JERSEY_CITY_DISPLAY),
            Decimal("16.79"))

    def test_display_text_fallback_abbreviations(self):
        self.assertEqual(
            estimate_return_toll(None, None, "Times Square, New York, NY",
                                 "Newark, NJ"),
            Decimal("16.79"))

    def test_display_text_fallback_ny_to_ny(self):
        self.assertEqual(
            estimate_return_toll(None, None, "JFK Airport",
                                 "Times Square, New York"),
            Decimal("0.00"))

    def test_display_text_fallback_nj_to_nj(self):
        # "Newark" must not read as New York.
        self.assertEqual(
            estimate_return_toll(None, None, EWR_DISPLAY, JERSEY_CITY_DISPLAY),
            Decimal("0.00"))

    def test_bare_place_names_are_never_guessed(self):
        # No state evidence anywhere: $0, never invented from a city name.
        self.assertEqual(
            estimate_return_toll(None, None, "JFK", "Jersey City"),
            Decimal("0.00"))

    def test_mixed_state_and_text(self):
        self.assertEqual(
            estimate_return_toll("New York", None, "JFK Airport",
                                 JERSEY_CITY_DISPLAY),
            Decimal("16.79"))
        self.assertEqual(
            estimate_return_toll(None, "New Jersey", JFK_DISPLAY, "Jersey City"),
            Decimal("16.79"))

    def test_geocoder_state_wins_over_text(self):
        # A stale or odd display string never overrides the geocoder.
        self.assertEqual(
            estimate_return_toll("New Jersey", "New York",
                                 JFK_DISPLAY, JERSEY_CITY_DISPLAY),
            Decimal("0.00"))


class GeocodeStateCase(unittest.TestCase):
    """geocode_state reads the cache populated by geocode(); never fetches."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        self._saved_coords = dict(geo_module._geocode_cache)
        self._saved_address = dict(geo_module._geocode_address_cache)
        geo_module._geocode_cache.clear()
        geo_module._geocode_address_cache.clear()

    def tearDown(self):
        geo_module._geocode_cache.clear()
        geo_module._geocode_cache.update(self._saved_coords)
        geo_module._geocode_address_cache.clear()
        geo_module._geocode_address_cache.update(self._saved_address)

    def test_state_available_after_geocode_without_second_request(self):
        payload = [{"lat": "40.7178", "lon": "-74.0431",
                    "address": {"state": "New Jersey", "city": "Jersey City"}}]
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=payload) as fetch:
            self.assertEqual(geo_module.geocode("Jersey City, NJ"),
                             (40.7178, -74.0431))
            self.assertEqual(geo_module.geocode_state("Jersey City, NJ"),
                             "New Jersey")
            self.assertEqual(fetch.call_count, 1)

    def test_state_falls_back_to_iso_code(self):
        payload = [{"lat": "40.6413", "lon": "-73.7781",
                    "address": {"ISO3166-2-lvl4": "US-NY"}}]
        with mock.patch.object(geo_module, "_http_get_json",
                               return_value=payload):
            geo_module.geocode("JFK Airport")
            self.assertEqual(geo_module.geocode_state("JFK Airport"), "US-NY")

    def test_uncached_address_returns_none_without_fetching(self):
        def boom(url):
            raise AssertionError("geocode_state must never fetch")
        with mock.patch.object(geo_module, "_http_get_json", side_effect=boom):
            self.assertIsNone(geo_module.geocode_state("Somewhere, NY"))

    def test_failed_geocode_caches_no_state(self):
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=RuntimeError("down")):
            self.assertIsNone(geo_module.geocode("Jersey City, NJ"))
            self.assertIsNone(geo_module.geocode_state("Jersey City, NJ"))


# These tests pin the legacy $9/$10 totals as fixtures (the return-
# toll mechanics are engine-independent); the live engine is
# Blacklane by default since the owner flip (2026-11-20).
@mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"})
class NjReturnTollBookingCase(unittest.TestCase):
    """End to end: quote, stored booking, and offer payload agree."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0
        self._saved_address = dict(geo_module._geocode_address_cache)
        geo_module._geocode_address_cache.clear()

    def tearDown(self):
        geo_module._geocode_address_cache.clear()
        geo_module._geocode_address_cache.update(self._saved_address)

    # -- helpers ---------------------------------------------------------
    def register_driver(self):
        self._driver_seq += 1
        phone = f"+1555007{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"NJ Driver {self._driver_seq}", "phone": phone,
            "email": f"nj{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"N{self._driver_seq:05d}",
            "state": "New York", "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_tlc_license": "2030-01-01",
            "expiry_fh1_insurance": "2030-01-01",
            "expiry_registration": "2030-01-01",
            "expiry_inspection": "2030-01-01",
            "expiry_vehicle_permit": "2030-01-01",
            "expiry_vehicle_registration": "2030-01-01",
            "expiry_insurance_card": "2030-01-01",
            "profile_photo": (io.BytesIO(photo_factory.VALID_PROFILE_PHOTO), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(photo_factory.doc_photo()), "license.png"),
            "doc_tlc_license": (io.BytesIO(photo_factory.doc_photo()), "tlc.png"),
            "doc_fh1": (io.BytesIO(photo_factory.doc_photo()), "fh1.png"),
            "doc_registration": (io.BytesIO(photo_factory.doc_photo()), "reg.png"),
            "doc_inspection": (io.BytesIO(photo_factory.doc_photo()), "insp.png"),
            "doc_vehicle_permit": (io.BytesIO(photo_factory.doc_photo()), "permit.png"),
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "NJ Toll Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "njtoll@test.com",
            "pickup": JFK_DISPLAY, "dropoff": JERSEY_CITY_DISPLAY,
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
    def test_nj_trip_quote_and_booking_carry_toll(self):
        booking = self.book()
        # 18.0 mi sedan: $162.00 fare + $16.79 toll = $178.79.
        # SUV: $180.00 + $16.79 = $196.79. No tax, no gratuity.
        self.assertTrue(approx(booking["total"], "178.79"), booking)
        self.assertTrue(approx(booking["class_totals"]["sedan"], "178.79"), booking)
        self.assertTrue(approx(booking["class_totals"]["suv"], "196.79"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "16.79"))
        # The customer GET shows NO totals while prices are paused.
        got = self.client.get(f"/api/bookings/{booking['id']}").get_json()["booking"]
        self.assertNotIn("total", got)
        self.assertNotIn("class_totals", got)

    def test_nj_trip_class_switch_keeps_toll(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/vehicle-class",
                                json={"vehicle_class": "suv"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        switched = resp.get_json()["booking"]
        self.assertTrue(approx(switched["total"], "196.79"), switched)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "16.79"))
        self.assertTrue(approx(self.pay(booking["id"]).get_json()["payment"]["amount"],
                               "196.79"))

    def test_ny_to_ny_trip_gets_zero_toll(self):
        booking = self.book(pickup="JFK Airport",
                            dropoff="Times Square, New York")
        self.assertTrue(approx(booking["total"], "162.00"), booking)
        self.assertTrue(approx(booking["class_totals"]["sedan"], "162.00"), booking)
        self.assertTrue(approx(booking["class_totals"]["suv"], "180.00"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "0.00"))

    def test_nj_to_nj_trip_gets_zero_toll(self):
        booking = self.book(pickup=EWR_DISPLAY, dropoff=JERSEY_CITY_DISPLAY)
        self.assertTrue(approx(booking["total"], "162.00"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "0.00"))

    def test_geocoder_state_path_with_bare_names(self):
        # Bare names carry no state text, so only the geocoder state
        # cache can produce the estimate — seed it as geocode() would.
        geo_module._geocode_address_cache["jfk"] = {"state": "New York"}
        geo_module._geocode_address_cache["jersey city"] = {"state": "New Jersey"}
        booking = self.book(pickup="JFK", dropoff="Jersey City")
        self.assertTrue(approx(self.stored_toll(booking["id"]), "16.79"))
        self.assertTrue(approx(booking["total"], "178.79"), booking)

    def test_hourly_ride_unaffected(self):
        booking = self.book(ride_type="hourly", hours=2, dropoff="",
                            pickup="Central Park, New York")
        self.assertTrue(approx(booking["total"], "180.00"), booking)
        self.assertTrue(approx(self.stored_toll(booking["id"]), "0.00"))

    # -- driver offer payload (before accept) ------------------------------
    def test_offer_payload_carries_no_upfront_toll_or_earnings(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        offers = self.offers(token)
        self.assertEqual(len(offers), 1)
        # The $16.79 toll is stored (see stored_toll below) but hidden
        # from the driver while prices are paused.
        self.assertNotIn("toll", offers[0])
        self.assertNotIn("earnings", offers[0])
        self.assertTrue(approx(self.stored_toll(booking["id"]), "16.79"))
        forbidden = {"miles", "fare", "total", "gratuity", "tax", "profit"}
        self.assertFalse(forbidden & set(offers[0]))

    def test_owner_can_still_adjust_upfront_toll(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/toll",
                                json={"toll": 20.00})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        offers = self.offers(token)
        self.assertNotIn("toll", offers[0])
        self.assertNotIn("earnings", offers[0])
        self.assertTrue(approx(self.stored_toll(booking["id"]), "20.00"))


if __name__ == "__main__":
    unittest.main()
