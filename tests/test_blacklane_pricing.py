"""Tests for the Blacklane-style base-fare pricing engine (owner order
2026-11-20, "tum bana do").

Settled rules under test:
- Fee model fitted from the Blacklane price-check workbook (158
  routes, sheet "Quotes"): black car fee 2.5% of base iff pickup in NY;
  sales tax iff both ends in NY, rate by PICKUP county (NYC 8.875%,
  Nassau 8.625%, Suffolk 8.75%); NY State congestion $2.75 iff an end
  is in Manhattan and both ends are in NY; MTA $0.75 iff an end is in
  Manhattan or (NJ-Hudson <-> NYC five boroughs); airport access
  $3.50 iff an end is JFK / LaGuardia / Newark (EWR). Total = base +
  fees. The model reproduces all 158 Business totals in the sheet.
- Base fare per class interpolates the 100-rung Times Square ladder
  (1-100 road miles); below rung 1 the base is clamped at the class
  floor (Business $112.97, SUV $175.37, First $187.93); above 100.24
  mi it extends with the last segment's slope. Ladder points carry
  sub-cent bases recovered from the sheet totals, so the engine
  reproduces all 100 rungs x 3 classes to the cent (owner hard rule
  2026-11-20: zero difference); see LadderExactCase.
- Customer total in Blacklane mode is base + fees ONLY — the map toll
  is NOT added to what the customer pays (Blacklane's own quote has
  no separate toll line); the driver still gets the map toll in his
  pay, so it comes out of Noel's profit in Blacklane mode.
- First Class: driver rate $9/mi + toll (owner decision 2026-11-20
  ~02:31 EST) — the engine prices driver pay and profit for it.
  Class selection still refuses First Class, and a First Class
  booking is never offered to or accepted by any driver: which car
  models qualify for First Class is still undecided.
- Fare preview falls back to the committed places snapshot when live
  geocoding answers nothing (Render's Nominatim answers come back
  empty): snapshot coordinates are real Nominatim data, so no
  distance is invented; a place outside the snapshot still 400s.
- Gating: NOEL_PRICING=blacklane switches the fare computation;
  default (unset/anything else) is the legacy $9/$10 formula. Live
  pricing is unchanged until the owner flips the flag.

Run:  python -m unittest discover -s tests -v
"""

import importlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from decimal import Decimal
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-blacklane-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "blacklane-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
from blacklane_pricing import (  # noqa: E402
    base_fare,
    blacklane_class_totals,
    blacklane_fees,
    classify_endpoint,
    compute_blacklane_one_way,
)
from pricing import money, pricing_mode  # noqa: E402

D = Decimal
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Blacklane Customer"}


# ---------------------------------------------------------------- pure -----
class TestBlacklaneEnginePure(unittest.TestCase):
    def test_ladder_rungs_match_sheet_totals(self):
        # (miles, dropoff, class) -> sheet total. The engine
        # interpolates the ladder, so a rung's own miles hit its
        # point exactly and the fee rules rebuild the sheet total —
        # EXCEPT at miles <= 10, where the owner overrode the
        # Blacklane total with his flat customer charge (Business
        # $100, SUV $130; owner decision 2026-11-20 ~06:38 EST).
        # First Class keeps the engine total at every distance.
        cases = [
            (1.08, "Rockefeller Center", "sedan", "100.00"),
            (1.08, "Rockefeller Center", "suv", "130.00"),
            (1.08, "Rockefeller Center", "first", "212.81"),
            (8.90, "Rego Park", "sedan", "100.00"),
            (46.95, "Lincolndale", "sedan", "318.22"),
            (100.24, "Sag Harbor Post Office", "sedan", "485.82"),
            (100.24, "Sag Harbor Post Office", "suv", "649.67"),
            (100.24, "Sag Harbor Post Office", "first", "773.74"),
        ]
        for miles, dropoff, cls, total in cases:
            r = compute_blacklane_one_way(
                D(str(miles)), cls, "Times Square", dropoff)
            self.assertEqual(r["total"], D(total), (miles, cls))
            self.assertEqual(r["vehicle_class"], cls)

    def test_fee_rules_with_known_bases(self):
        # The fee rules applied to a route's OWN quoted base rebuild
        # that route's sheet total exactly (Business breakdowns).
        cases = [
            # (pickup, dropoff, base, expected fees, expected total)
            ("JFK Airport", "Times Square", "175.91",
             {"airport_access": "3.50", "ny_congestion": "2.75",
              "mta_congestion": "0.75", "sales_tax": "15.61",
              "black_car_fee": "4.40"}, "202.92"),
            ("Times Square", "JFK Airport", "175.83",
             {"airport_access": "3.50", "ny_congestion": "2.75",
              "mta_congestion": "0.75", "sales_tax": "15.60",
              "black_car_fee": "4.40"}, "202.83"),
            ("180 Green Acres Rd, Valley Stream", "JFK Airport", "134.47",
             {"airport_access": "3.50", "ny_congestion": "0.00",
              "mta_congestion": "0.00", "sales_tax": "11.60",
              "black_car_fee": "3.36"}, "152.93"),
            ("Times Square", "Weehawken", "116.52",
             {"airport_access": "0.00", "ny_congestion": "0.00",
              "mta_congestion": "0.75", "sales_tax": "0.00",
              "black_car_fee": "2.91"}, "120.18"),
            ("Times Square", "Newark Airport (EWR)", "170.02",
             {"airport_access": "3.50", "ny_congestion": "0.00",
              "mta_congestion": "0.75", "sales_tax": "0.00",
              "black_car_fee": "4.25"}, "178.52"),
            ("Times Square", "Brooklyn Heights", "135.75",
             {"airport_access": "0.00", "ny_congestion": "2.75",
              "mta_congestion": "0.75", "sales_tax": "12.05",
              "black_car_fee": "3.39"}, "154.69"),
        ]
        for pickup, dropoff, base, fees, total in cases:
            got = blacklane_fees(classify_endpoint(pickup),
                                 classify_endpoint(dropoff), D(base))
            for key, value in fees.items():
                self.assertEqual(got[key], D(value), (pickup, dropoff, key))
            self.assertEqual(money(D(base) + got["fees_total"]),
                             D(total), (pickup, dropoff))

    def test_minimum_floor(self):
        # Rungs 1-3 all price at the Business floor; SUV/First floors
        # are their rung-1 bases. The base floor still exists, but
        # the CUSTOMER total at miles <= 10 is now the owner's flat
        # $100 (Business) / $130 (SUV) — owner decision 2026-11-20
        # ~06:38 EST.
        self.assertEqual(base_fare("sedan", D("0.5")), D("112.97"))
        self.assertEqual(base_fare("sedan", D("0")), D("112.97"))
        self.assertEqual(base_fare("suv", D("0.5")), D("175.37"))
        self.assertEqual(base_fare("first", D("0.5")), D("187.93"))
        r = compute_blacklane_one_way(D("0.5"), "sedan",
                                      "Times Square", "Rockefeller Center")
        self.assertEqual(r["total"], D("100.00"))

    def test_interpolation_between_rungs(self):
        # 25.5 mi sits between the 24.97-mi and 25.94-mi rungs.
        # base_fare returns the precise (unrounded) interpolation;
        # the cent-rounded base is what the totals are built from.
        self.assertEqual(money(base_fare("sedan", D("25.5"))), D("195.67"))
        # Above the top rung the base extends with the last segment.
        self.assertEqual(money(base_fare("sedan", D("105"))), D("440.56"))

    def test_first_class_driver_pay_is_the_slab(self):
        # First Class driver pay is the FLAT slab + toll (owner
        # decision 2026-11-20 ~06:25 EST): 10 mi -> 5-10 slab $110.
        r = compute_blacklane_one_way(D("10"), "first",
                                      "Times Square", "Rockefeller Center")
        self.assertEqual(r["total"], D("272.92"))
        self.assertEqual(r["driver_earnings"], D("110.00"))
        self.assertEqual(r["profit"], D("162.92"))
        self.assertFalse(r["first_class_driver_pay_tbd"])
        for cls, slab in (("sedan", "80.00"), ("suv", "90.00")):
            got = compute_blacklane_one_way(
                D("10"), cls, "Times Square", "Rockefeller Center")
            self.assertEqual(got["driver_earnings"], D(slab), cls)
            self.assertIsNotNone(got["profit"], cls)
            self.assertFalse(got["first_class_driver_pay_tbd"], cls)

    def test_driver_pay_is_the_slab_plus_toll(self):
        # The flat slab + the map toll (toll is NOT in the customer
        # total, but the driver still gets it). 17.9 mi -> 10-20
        # slab: sedan $95, SUV $130.
        r = compute_blacklane_one_way(D("17.9"), "sedan",
                                      "JFK Airport", "Times Square",
                                      toll=D("7.46"))
        self.assertEqual(r["driver_earnings"], D("102.46"))
        self.assertEqual(r["total"], D("193.87"))
        self.assertEqual(r["profit"], D("91.41"))
        s = compute_blacklane_one_way(D("17.9"), "suv",
                                      "JFK Airport", "Times Square",
                                      toll=D("7.46"))
        self.assertEqual(s["driver_earnings"], D("137.46"))

    def test_referral_discount_comes_off_the_total_only(self):
        # 1.08 mi sedan: flat customer total $100, so the 5%
        # referral discount is $5.00 and the total $95.00; the
        # driver keeps his slab ($80 at 1-5 mi) in full.
        r = compute_blacklane_one_way(D("1.08"), "sedan",
                                      "Times Square", "Rockefeller Center",
                                      referral=True)
        self.assertEqual(r["referral_discount"], D("5.00"))
        self.assertEqual(r["total"], D("95.00"))
        self.assertEqual(r["driver_earnings"], D("80.00"))

    def test_classify_endpoint_geocoder_details(self):
        ny_nassau = classify_endpoint(
            "180 Green Acres Rd, Valley Stream",
            {"state": "New York", "county": "Nassau County"})
        self.assertTrue(ny_nassau["in_ny"])
        self.assertEqual(ny_nassau["tax_county"], "Nassau")
        nj = classify_endpoint(
            "Ridgewood", {"state": "New Jersey", "county": "Bergen County"})
        self.assertFalse(nj["in_ny"])
        # Geocoder state wins over the text: "Ridgewood NJ" is NJ even
        # though "Ridgewood" is also a Queens neighbourhood.
        self.assertFalse(classify_endpoint("Ridgewood NJ")["in_ny"])
        self.assertTrue(classify_endpoint("Ridgewood, Queens")["in_ny"])
        # A NY county the sheet has no row for falls back to the NYC
        # rate and says so.
        westchester = classify_endpoint(
            "White Plains", {"state": "New York",
                             "county": "Westchester County"})
        self.assertTrue(westchester["in_ny"])
        self.assertTrue(westchester["tax_rate_estimated"])
        manhattan = classify_endpoint(
            "Times Square", {"state": "New York",
                             "county": "New York County"})
        self.assertTrue(manhattan["is_manhattan"])
        self.assertTrue(manhattan["is_nyc5"])

    def test_pricing_mode_flag(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NOEL_PRICING", None)
            self.assertEqual(pricing_mode(), "legacy")
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "blacklane"}):
            self.assertEqual(pricing_mode(), "blacklane")
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "BLACKLANE "}):
            self.assertEqual(pricing_mode(), "blacklane")
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "something-else"}):
            self.assertEqual(pricing_mode(), "legacy")

    def test_class_totals_include_first(self):
        # 1.08 mi: Business and SUV are the owner's flat $100/$130
        # (owner decision 2026-11-20 ~06:38 EST); First keeps the
        # engine total.
        totals = blacklane_class_totals(
            D("1.08"), "Times Square", "Rockefeller Center")
        self.assertEqual(totals, {"sedan": D("100.00"),
                                  "suv": D("130.00"),
                                  "first": D("212.81")})

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            compute_blacklane_one_way(D("10"), "limo",
                                      "Times Square", "JFK Airport")
        with self.assertRaises(ValueError):
            base_fare("limo", D("10"))


# ------------------------------------------------------------------ api -----
class BlacklaneApiCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0
        # Pause OFF for booking-flow tests (owner decision 2026-11-20):
        # the flag is read from the environment once, when app.py is
        # first imported, so in the shared-process full run another
        # module may have imported it first — flip it in-process here
        # like the other booking-flow test modules do. The attribute
        # may not exist in every branch state (the pause feature
        # landed separately), so only flip it when present.
        self._saved_bookings_paused = getattr(
            app_module, "BOOKINGS_PAUSED", None)
        if self._saved_bookings_paused is not None:
            app_module.BOOKINGS_PAUSED = False
        # Deterministic geo: every one-way ride is 17.9 miles, JFK ->
        # Times Square (legacy sedan $168.56 with the $7.46 toll; the
        # stubbed route carries no map toll, so $161.10 + $0.00).
        self._saved_distance_miles = geo_module.distance_miles
        geo_module.distance_miles = lambda p, d: (  # noqa: E731
            17.9, (40.6413, -73.7781), (40.7580, -73.9855))
        self._saved_pricing = os.environ.pop("NOEL_PRICING", None)

    def tearDown(self):
        geo_module.distance_miles = self._saved_distance_miles
        if self._saved_bookings_paused is not None:
            app_module.BOOKINGS_PAUSED = self._saved_bookings_paused
        if self._saved_pricing is None:
            os.environ.pop("NOEL_PRICING", None)
        else:
            os.environ["NOEL_PRICING"] = self._saved_pricing

    # -- helpers (same shape as test_class_pricing) ----------------------
    def register_driver(self, car_model):
        self._driver_seq += 1
        phone = f"+1555005{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Blacklane Driver {self._driver_seq}", "phone": phone,
            "email": f"bl{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
            "plate": f"B{self._driver_seq:05d}",
            "state": "New York", "bank_account_number": "123456789",
            "bank_routing_number": "021000021",
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
            "customer_name": "Blacklane Customer",
            "phone": f"+1555006{self._phone_seq:04d}",
            "email": "blacklane@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    # -- preview endpoint --------------------------------------------------
    def test_preview_returns_both_totals(self):
        resp = self.client.get("/api/fare-preview", query_string={
            "pickup": "JFK Airport Terminal 1", "dropoff": "Times Square"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertEqual(body["miles"], 17.9)
        self.assertEqual(body["pricing_mode"], "legacy")
        # Legacy: fare $161.10 + whatever map toll the stubbed route
        # carries ($0.00 with cold geocode caches).
        legacy_sedan = body["legacy"]["sedan"]
        self.assertEqual(legacy_sedan["fare"], 161.10)
        self.assertEqual(legacy_sedan["total"],
                         161.10 + legacy_sedan["toll"])
        self.assertEqual(legacy_sedan["driver_earnings"],
                         95.00 + legacy_sedan["toll"])
        # Blacklane-style: interpolated base $167.79 + fees $26.08.
        black_sedan = body["blacklane"]["sedan"]
        self.assertEqual(black_sedan["base"], 167.79)
        self.assertEqual(black_sedan["total"], 193.87)
        self.assertEqual(black_sedan["fees"]["airport_access"], 3.50)
        self.assertEqual(black_sedan["fees"]["ny_congestion"], 2.75)
        self.assertEqual(black_sedan["fees"]["mta_congestion"], 0.75)
        self.assertEqual(black_sedan["fees"]["sales_tax"], 14.89)
        self.assertEqual(black_sedan["fees"]["black_car_fee"], 4.19)
        # First Class: customer fare + driver pay at the FLAT slab
        # (owner decision 2026-11-20 ~06:25 EST). Stubbed route:
        # 17.9 mi -> 10-20 slab $150, $0.00 map toll.
        black_first = body["blacklane"]["first"]
        self.assertIsNotNone(black_first["total"])
        self.assertEqual(black_first["driver_earnings"], 150.00)
        self.assertEqual(black_first["profit"],
                         round(black_first["total"] - 150.00, 2))
        self.assertFalse(black_first["first_class_driver_pay_tbd"])
        self.assertIn("slab", body["first_class_driver_pay"])
        self.assertFalse(body["snapshot_fallback"])

    def test_preview_class_filter_first(self):
        resp = self.client.get("/api/fare-preview", query_string={
            "pickup": "JFK Airport Terminal 1", "dropoff": "Times Square",
            "class": "first"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["legacy"], {})
        self.assertEqual(set(body["blacklane"]), {"first"})
        first = body["blacklane"]["first"]
        self.assertEqual(first["driver_earnings"], 150.00)
        self.assertEqual(first["profit"],
                         round(first["total"] - 150.00, 2))
        self.assertFalse(first["first_class_driver_pay_tbd"])

    def test_preview_unresolvable_address_is_400(self):
        geo_module.distance_miles = lambda p, d: (None, None, None)  # noqa: E731
        resp = self.client.get("/api/fare-preview", query_string={
            "pickup": "Nowhere Street 1", "dropoff": "Times Square"})
        self.assertEqual(resp.status_code, 400)

    def test_preview_uses_snapshot_when_live_geocode_fails(self):
        # Live 2026-11-20: the preview 400d on JFK -> Times Square
        # because Nominatim answers empty from Render. With no
        # network at all, the snapshot fallback must still return
        # both totals (miles from the snapshot coordinates via the
        # haversine fallback, since OSRM is unreachable too).
        importlib.reload(geo_module)  # real distance_miles back
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=AssertionError("no network")):
            resp = self.client.get("/api/fare-preview", query_string={
                "pickup": "JFK Airport Terminal 1",
                "dropoff": "Times Square"})
        self.assertEqual(resp.status_code, 200,
                         resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertTrue(body["snapshot_fallback"])
        t1 = (40.6430714, -73.7890699)
        ts = (40.7570095, -73.9859724)
        expected_miles = round(
            geo_module.haversine_miles(t1[0], t1[1], ts[0], ts[1]) * 1.3, 1)
        self.assertEqual(body["miles"], expected_miles)
        # No geometry without OSRM: the map toll falls back to
        # $0.00 for a NY->NY trip, so the legacy total is $9 x miles.
        self.assertEqual(body["toll"], 0)
        self.assertEqual(body["legacy"]["sedan"]["total"],
                         round(9 * expected_miles, 2))
        # Blacklane-style total must match the engine computed from
        # the same miles with the snapshot's own details.
        direct = compute_blacklane_one_way(
            D(str(expected_miles)), "sedan",
            "JFK Airport Terminal 1", "Times Square",
            pickup_details={"state": "New York",
                            "county": "Queens County",
                            "city": "New York"},
            dropoff_details={"state": "New York",
                             "county": "New York County",
                             "city": "New York"},
            toll=D("0"))
        self.assertEqual(body["blacklane"]["sedan"]["total"],
                         float(direct["total"]))

    def test_preview_valley_stream_to_jfk_uses_snapshot_offline(self):
        # Same as the JFK -> Times Square offline test, for the
        # owner's home address: typed "East Valley Stream" matches
        # nothing in Nominatim, so only the snapshot resolves it.
        importlib.reload(geo_module)  # real distance_miles back
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=AssertionError("no network")):
            resp = self.client.get("/api/fare-preview", query_string={
                "pickup": "180 Green Acres Road, East Valley Stream, NY",
                "dropoff": "JFK Airport Terminal 1"})
        self.assertEqual(resp.status_code, 200,
                         resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertTrue(body["snapshot_fallback"])
        house = (40.6600991, -73.7160402)
        t1 = (40.6430714, -73.7890699)
        expected_miles = round(
            geo_module.haversine_miles(house[0], house[1], t1[0], t1[1]) * 1.3, 1)
        self.assertEqual(body["miles"], expected_miles)
        # No geometry without OSRM: the map toll falls back to
        # $0.00 for a NY->NY trip, so the legacy total is $9 x miles.
        self.assertEqual(body["toll"], 0)
        self.assertEqual(body["legacy"]["sedan"]["total"],
                         round(9 * expected_miles, 2))
        # Blacklane-style total must match the engine computed from
        # the same miles with the snapshot's own details (pickup in
        # Nassau County, so the sales-tax rate is Nassau's 8.625%).
        _, pickup_details = geo_module.snapshot_coords(
            "180 Green Acres Road, East Valley Stream, NY")
        _, dropoff_details = geo_module.snapshot_coords(
            "JFK Airport Terminal 1")
        direct = compute_blacklane_one_way(
            D(str(expected_miles)), "sedan",
            "180 Green Acres Road, East Valley Stream, NY",
            "JFK Airport Terminal 1",
            pickup_details=pickup_details,
            dropoff_details=dropoff_details,
            toll=D("0"))
        self.assertEqual(body["blacklane"]["sedan"]["total"],
                         float(direct["total"]))

    def test_preview_bad_class_is_400(self):
        resp = self.client.get("/api/fare-preview", query_string={
            "pickup": "JFK Airport", "dropoff": "Times Square",
            "class": "limo"})
        self.assertEqual(resp.status_code, 400)

    def test_preview_missing_address_is_400(self):
        resp = self.client.get("/api/fare-preview", query_string={
            "pickup": "JFK Airport"})
        self.assertEqual(resp.status_code, 400)

    # -- flag gating -------------------------------------------------------
    def test_booking_creation_legacy_default(self):
        booking = self.book()
        self.assertEqual(booking["total"], 161.10)
        self.assertEqual(set(booking["class_totals"]), {"sedan", "suv"})
        self.assertEqual(booking["class_totals"]["sedan"], 161.10)
        self.assertNotIn("first_class_bookable", booking)
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            self.assertEqual(row.fare, D("161.10"))
            self.assertEqual(row.tax, D("0.00"))

    def test_booking_creation_blacklane_mode(self):
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "blacklane"}):
            booking = self.book()
        self.assertEqual(booking["total"], 193.87)
        self.assertEqual(set(booking["class_totals"]),
                         {"sedan", "suv", "first"})
        self.assertEqual(booking["class_totals"]["sedan"], 193.87)
        self.assertIsNotNone(booking["class_totals"]["first"])
        self.assertTrue(booking["first_class_bookable"])
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            self.assertEqual(row.fare, D("167.79"))
            self.assertEqual(row.tax, D("14.89"))
            self.assertEqual(row.driver_earnings, D("95.00") + row.toll)

    def test_select_first_class_allowed_in_blacklane_mode(self):
        # First Class is OPEN since owner decision 2026-11-20 ~03:00 EST
        # (same models as Blacklane): selecting it stores "first" and
        # reprices the booking with the Blacklane First Class total.
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "blacklane"}):
            booking = self.book()
            first_total = booking["class_totals"]["first"]
            resp = self.client.post(
                f"/api/bookings/{booking['id']}/vehicle-class",
                json={"vehicle_class": "first"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()["booking"]
        self.assertEqual(body["vehicle_class"], "first")
        self.assertEqual(body["vehicle_class_label"], "First Class")
        self.assertEqual(body["total"], first_total)
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            self.assertEqual(row.vehicle_class, "first")

    def test_select_first_class_invalid_in_legacy_mode(self):
        # First Class exists only in Blacklane mode: the legacy
        # engine has no First Class rate to price it with.
        booking = self.book()
        resp = self.client.post(
            f"/api/bookings/{booking['id']}/vehicle-class",
            json={"vehicle_class": "first"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Blacklane rates", resp.get_json()["error"])

    def test_first_class_booking_reaches_no_non_qualifying_driver(self):
        _, token = self.register_driver("Cadillac Escalade")
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        # A First Class row reaches ONLY drivers with a First Class
        # model (owner decision 2026-11-20 ~03:00 EST) — an Escalade
        # driver never sees it and cannot accept it even by direct
        # call (defense in depth: the raw column is checked, not
        # the sedan-fallback helper).
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            self.assertEqual(row.status, "offered")
            row.vehicle_class = "first"
            app_module.db.session.commit()
        offers = self.client.get(
            "/api/drivers/me/offers",
            headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(
            [o for o in offers if o["booking_id"] == booking["id"]], [])
        resp = self.client.post(
            f"/api/drivers/me/offers/{booking['id']}/accept",
            headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn("First Class", resp.get_json()["error"])

    def test_recompute_first_class_prices_at_the_slab(self):
        # A stored First Class row reprices in Blacklane mode with
        # the FLAT slab driver pay (owner decision 2026-11-20
        # ~06:25 EST) — 17.9 mi -> 10-20 slab $150 — and, crucially,
        # with the RAW class, not the sedan-fallback helper (which
        # would price it as a sedan).
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "blacklane"}):
            booking = self.book()
            with app_module.app.app_context():
                row = app_module.db.session.get(app_module.Booking, booking["id"])
                row.vehicle_class = "first"
                app_module.recompute_booking_fare(row)
                app_module.db.session.commit()
                self.assertEqual(row.driver_earnings, D("150.00"))
                self.assertEqual(row.vehicle_class, "first")
                self.assertIsNotNone(row.fare_total)


# ------------------------------------------------- ladder exactness ------
class LadderExactCase(unittest.TestCase):
    """Owner hard rule 2026-11-20 ~02:32 EST: 'Dono mein ek rupay ka
    fark nahi aana' — ZERO difference to the cent between Blacklane's
    total and Noel's, on all 100 ladder rungs x 3 classes — with ONE
    later owner override (2026-11-20 ~06:38 EST): at miles <= 10 the
    customer pays his flat $100 (Business) / $130 (SUV) instead of
    the Blacklane total; First Class keeps the engine total. Expected
    totals come from the sheet (frozen in the fixture); the engine
    prices Times Square -> each rung's place at the rung's miles.
    The dropoff state comes from the place string (the same data
    live geocoding would supply); the pickup is always Times Square
    (Manhattan, New York County), so the tax rate is the NYC rate."""

    def test_all_100_rungs_x_3_classes_exact(self):
        fixture = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures", "blacklane_ladder_expected.json")
        with open(fixture, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(len(data["rungs"]), 100)
        ts_details = {"city": "New York", "county": "New York County",
                      "state": "New York", "country": "United States",
                      "country_code": "us"}
        state_map = {"NY": "New York", "NJ": "New Jersey",
                     "CT": "Connecticut", "PA": "Pennsylvania",
                     "MA": "Massachusetts"}
        mismatches = []
        for rung in data["rungs"]:
            place = rung["place"]
            m = re.search(
                r",\s*(New York|New Jersey|Connecticut|Pennsylvania"
                r"|Massachusetts|NY|NJ|CT|PA|MA),\s*USA\s*$", place)
            state = state_map.get(m.group(1), m.group(1)) if m else None
            self.assertIsNotNone(state, rung)
            self.assertEqual(state == "New York", rung["ny"], rung)
            dropoff_details = {"state": state}
            for cls in ("sedan", "suv", "first"):
                got = compute_blacklane_one_way(
                    D(str(rung["miles"])), cls,
                    "Times Square", place,
                    pickup_details=ts_details,
                    dropoff_details=dropoff_details,
                    toll=D("0"))
                want = D(str(rung["totals"][cls]))
                if D(str(rung["miles"])) <= D("10"):
                    # Owner flat override (2026-11-20 ~06:38 EST):
                    # Business $100, SUV $130 at miles <= 10; First
                    # keeps the sheet total.
                    if cls == "sedan":
                        want = D("100.00")
                    elif cls == "suv":
                        want = D("130.00")
                if got["total"] != want:
                    mismatches.append(
                        (rung["n"], cls, str(want), str(got["total"])))
        self.assertEqual(mismatches, [], f"{len(mismatches)} mismatches")


# ------------------------------------------------- snapshot geocoding ------
class SnapshotGeocodeCase(unittest.TestCase):
    """geo.snapshot_coords: the committed places snapshot as an offline
    geocoder for the fare preview (live 2026-11-20: the preview 400d
    on JFK -> Times Square because Nominatim answers empty from
    Render). No network is allowed in these tests at all."""

    def test_snapshot_resolves_jfk_terminal_1_without_network(self):
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=AssertionError("no network")):
            coords, details = geo_module.snapshot_coords(
                "JFK Airport Terminal 1")
        self.assertEqual(coords, (40.6430714, -73.7890699))
        self.assertEqual(details["state"], "New York")
        self.assertEqual(details["county"], "Queens County")

    def test_snapshot_resolves_times_square_without_network(self):
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=AssertionError("no network")):
            coords, details = geo_module.snapshot_coords("Times Square")
        self.assertEqual(coords, (40.7570095, -73.9859724))
        self.assertEqual(details["state"], "New York")
        self.assertEqual(details["county"], "New York County")

    def test_snapshot_longest_match_wins(self):
        # "JFK Airport Terminal 1" must resolve to Terminal 1, not
        # to the airport itself (longest matching query wins).
        coords, _ = geo_module.snapshot_coords("JFK Airport Terminal 1")
        self.assertEqual(coords, (40.6430714, -73.7890699))
        airport, _ = geo_module.snapshot_coords("JFK Airport")
        self.assertEqual(airport, (40.6429479, -73.7793734))

    def test_snapshot_unknown_place_returns_none(self):
        self.assertEqual(
            geo_module.snapshot_coords("Nowhere Street 1"), (None, None))

    def test_snapshot_resolves_owner_home_address_without_network(self):
        # The owner's typed phrasing ("East Valley Stream") matches
        # nothing in Nominatim, so the snapshot entry is keyed
        # without "East" and the subset matcher pairs them.
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=AssertionError("no network")):
            coords, details = geo_module.snapshot_coords(
                "180 Green Acres Road, East Valley Stream, NY")
        self.assertEqual(coords, (40.6600991, -73.7160402))
        self.assertEqual(details["state"], "New York")
        self.assertEqual(details["county"], "Nassau County")
        self.assertEqual(details["postcode"], "11581")

    def test_snapshot_resolves_valley_stream_town_without_network(self):
        with mock.patch.object(
                geo_module, "_http_get_json",
                side_effect=AssertionError("no network")):
            coords, details = geo_module.snapshot_coords("Valley Stream")
        self.assertEqual(coords, (40.6631362, -73.7056955))
        self.assertEqual(details["state"], "New York")
        self.assertEqual(details["county"], "Nassau County")


if __name__ == "__main__":
    unittest.main()
