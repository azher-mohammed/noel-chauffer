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
  mi it extends with the last segment's slope.
- Customer total in Blacklane mode is base + fees ONLY — the map toll
  is NOT added to what the customer pays (Blacklane's own quote has
  no separate toll line); the driver still gets the map toll in his
  pay, so it comes out of Noel's profit in Blacklane mode.
- First Class: CUSTOMER fare only. Driver pay is TBD (owner decision
  pending) — the engine returns driver_earnings/profit None, class
  selection refuses First Class, and a First Class booking is never
  offered to or accepted by any driver.
- Gating: NOEL_PRICING=blacklane switches the fare computation;
  default (unset/anything else) is the legacy $9/$10 formula. Live
  pricing is unchanged until the owner flips the flag.

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
        # point exactly and the fee rules rebuild the sheet total.
        cases = [
            (1.08, "Rockefeller Center", "sedan", "129.32"),
            (1.08, "Rockefeller Center", "suv", "198.81"),
            (1.08, "Rockefeller Center", "first", "212.81"),
            (8.90, "Rego Park", "sedan", "150.44"),
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
        # are their rung-1 bases.
        self.assertEqual(base_fare("sedan", D("0.5")), D("112.97"))
        self.assertEqual(base_fare("sedan", D("0")), D("112.97"))
        self.assertEqual(base_fare("suv", D("0.5")), D("175.37"))
        self.assertEqual(base_fare("first", D("0.5")), D("187.93"))
        r = compute_blacklane_one_way(D("0.5"), "sedan",
                                      "Times Square", "Rockefeller Center")
        self.assertEqual(r["total"], D("129.32"))

    def test_interpolation_between_rungs(self):
        # 25.5 mi sits between the 24.97-mi and 25.94-mi rungs.
        self.assertEqual(base_fare("sedan", D("25.5")), D("195.67"))
        # Above the top rung the base extends with the last segment.
        self.assertEqual(base_fare("sedan", D("105")), D("440.56"))

    def test_first_class_driver_pay_is_tbd(self):
        r = compute_blacklane_one_way(D("10"), "first",
                                      "Times Square", "Rockefeller Center")
        self.assertEqual(r["total"], D("272.92"))
        self.assertIsNone(r["driver_earnings"])
        self.assertIsNone(r["profit"])
        self.assertTrue(r["first_class_driver_pay_tbd"])
        for cls in ("sedan", "suv"):
            got = compute_blacklane_one_way(
                D("10"), cls, "Times Square", "Rockefeller Center")
            self.assertIsNotNone(got["driver_earnings"], cls)
            self.assertIsNotNone(got["profit"], cls)
            self.assertFalse(got["first_class_driver_pay_tbd"], cls)

    def test_driver_pay_keeps_legacy_rates_plus_toll(self):
        # Sedan $4/mi, SUV $7/mi + the map toll (toll is NOT in the
        # customer total, but the driver still gets it).
        r = compute_blacklane_one_way(D("17.9"), "sedan",
                                      "JFK Airport", "Times Square",
                                      toll=D("7.46"))
        self.assertEqual(r["driver_earnings"], D("79.06"))
        self.assertEqual(r["total"], D("193.87"))
        self.assertEqual(r["profit"], D("114.81"))
        s = compute_blacklane_one_way(D("17.9"), "suv",
                                      "JFK Airport", "Times Square",
                                      toll=D("7.46"))
        self.assertEqual(s["driver_earnings"], D("132.76"))

    def test_referral_discount_comes_off_the_total_only(self):
        r = compute_blacklane_one_way(D("1.08"), "sedan",
                                      "Times Square", "Rockefeller Center",
                                      referral=True)
        self.assertEqual(r["referral_discount"], D("6.47"))
        self.assertEqual(r["total"], D("122.85"))
        self.assertEqual(r["driver_earnings"], D("4.32"))

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
        totals = blacklane_class_totals(
            D("1.08"), "Times Square", "Rockefeller Center")
        self.assertEqual(totals, {"sedan": D("129.32"),
                                  "suv": D("198.81"),
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
        # like the other booking-flow test modules do.
        self._saved_bookings_paused = app_module.BOOKINGS_PAUSED
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
                         71.60 + legacy_sedan["toll"])
        # Blacklane-style: interpolated base $167.79 + fees $26.08.
        black_sedan = body["blacklane"]["sedan"]
        self.assertEqual(black_sedan["base"], 167.79)
        self.assertEqual(black_sedan["total"], 193.87)
        self.assertEqual(black_sedan["fees"]["airport_access"], 3.50)
        self.assertEqual(black_sedan["fees"]["ny_congestion"], 2.75)
        self.assertEqual(black_sedan["fees"]["mta_congestion"], 0.75)
        self.assertEqual(black_sedan["fees"]["sales_tax"], 14.89)
        self.assertEqual(black_sedan["fees"]["black_car_fee"], 4.19)
        # First Class: customer fare only, driver pay TBD.
        black_first = body["blacklane"]["first"]
        self.assertIsNotNone(black_first["total"])
        self.assertIsNone(black_first["driver_earnings"])
        self.assertIsNone(black_first["profit"])
        self.assertTrue(black_first["first_class_driver_pay_tbd"])
        self.assertIn("TBD", body["first_class_driver_pay"])

    def test_preview_class_filter_first(self):
        resp = self.client.get("/api/fare-preview", query_string={
            "pickup": "JFK Airport Terminal 1", "dropoff": "Times Square",
            "class": "first"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["legacy"], {})
        self.assertEqual(set(body["blacklane"]), {"first"})

    def test_preview_unresolvable_address_is_400(self):
        geo_module.distance_miles = lambda p, d: (None, None, None)  # noqa: E731
        resp = self.client.get("/api/fare-preview", query_string={
            "pickup": "Nowhere Street 1", "dropoff": "Times Square"})
        self.assertEqual(resp.status_code, 400)

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
        self.assertFalse(booking["first_class_bookable"])
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            self.assertEqual(row.fare, D("167.79"))
            self.assertEqual(row.tax, D("14.89"))
            self.assertEqual(row.driver_earnings, D("71.60") + row.toll)

    def test_select_first_class_refused_in_blacklane_mode(self):
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "blacklane"}):
            booking = self.book()
            resp = self.client.post(
                f"/api/bookings/{booking['id']}/vehicle-class",
                json={"vehicle_class": "first"})
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn("driver rate", resp.get_json()["error"])
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            self.assertEqual(row.vehicle_class, "sedan")

    def test_select_first_class_invalid_in_legacy_mode(self):
        booking = self.book()
        resp = self.client.post(
            f"/api/bookings/{booking['id']}/vehicle-class",
            json={"vehicle_class": "first"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("must be sedan or suv", resp.get_json()["error"])

    def test_first_class_booking_never_dispatched(self):
        _, token = self.register_driver("Cadillac Escalade")
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        # A First Class row must never reach drivers, even if one
        # somehow exists in the database (defense in depth: the raw
        # column is checked, not the sedan-fallback helper).
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

    def test_recompute_first_class_raises(self):
        booking = self.book()
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            row.vehicle_class = "first"
            with self.assertRaises(ValueError):
                app_module.recompute_booking_fare(row)
            app_module.db.session.rollback()


if __name__ == "__main__":
    unittest.main()
