"""Tests for flat driver pay by distance slab (owner decision
2026-11-20, voice call ~04:25 EST: "abhi ye kar do live"; FINAL RULE
~04:32 EST: the 30-40 slab is the base and every slab after it is
+$20 per class, to 400 miles; 1-5 slab added ~06:35-06:37 EST the
same day: Business $80, SUV $80, First $100).

Settled rules under test:
- Driver pay is FLAT per ride by distance band, per class — NOT per
  mile. Slab picked by miles: <= 5 -> 1-5, <= 10 -> 5-10, <= 20 ->
  10-20, and so on to <= 400 -> 390-400. Values are the owner's
  dictated numbers (draft sheet driver-pay-slabs-draft.xlsx,
  verified 2026-11-20, plus the 1-5 slab he dictated later).
- Toll is added on top of the slab amount, same as before.
- Hourly rides stay $50/hour — slabs apply only to distance rides.
- Rides OVER 400 miles have no slab: booking creation and the fare
  preview refuse them with HTTP 400; nothing is invented.
- Customer pricing: legacy $9/$10 per mile untouched; the Blacklane
  engine now has the owner's flat $100 (Business) / $130 (SUV) at
  1-10 miles and slab driver pay — still gated, not flipped;
  bookings stay paused.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from unittest import mock
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-slabs-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "slabs.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "slabs-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

import app as app_module  # noqa: E402
from pricing import (  # noqa: E402
    DRIVER_PAY_MAX_MILES,
    DRIVER_PAY_SLABS,
    compute_hourly,
    compute_one_way,
    driver_slab_pay,
)

D = Decimal

# The full verified table from the draft sheet (upper bound miles,
# Business, SUV, First). 1-5 through 30-40 are the owner's dictated
# numbers (the 1-5 slab: Business $80, SUV $80, First $100, owner
# decision 2026-11-20 ~06:35-06:37 EST); from 40-50 on, every slab
# is +$20 per class over the previous one (30-40 is the base).
FULL_TABLE = [
    (5, 80, 80, 100),
    (10, 80, 90, 110), (20, 95, 130, 150), (30, 125, 160, 190),
    (40, 140, 160, 200), (50, 160, 180, 220), (60, 180, 200, 240),
    (70, 200, 220, 260), (80, 220, 240, 280), (90, 240, 260, 300),
    (100, 260, 280, 320), (110, 280, 300, 340), (120, 300, 320, 360),
    (130, 320, 340, 380), (140, 340, 360, 400), (150, 360, 380, 420),
    (160, 380, 400, 440), (170, 400, 420, 460), (180, 420, 440, 480),
    (190, 440, 460, 500), (200, 460, 480, 520), (210, 480, 500, 540),
    (220, 500, 520, 560), (230, 520, 540, 580), (240, 540, 560, 600),
    (250, 560, 580, 620), (260, 580, 600, 640), (270, 600, 620, 660),
    (280, 620, 640, 680), (290, 640, 660, 700), (300, 660, 680, 720),
    (310, 680, 700, 740), (320, 700, 720, 760), (330, 720, 740, 780),
    (340, 740, 760, 800), (350, 760, 780, 820), (360, 780, 800, 840),
    (370, 800, 820, 860), (380, 820, 840, 880), (390, 840, 860, 900),
    (400, 860, 880, 920),
]


class TestSlabTable(unittest.TestCase):
    def test_table_has_41_slabs_to_400_miles(self):
        self.assertEqual(len(DRIVER_PAY_SLABS), 41)
        self.assertEqual(DRIVER_PAY_MAX_MILES, D("400"))
        self.assertEqual(DRIVER_PAY_SLABS[-1][0], D("400"))

    def test_every_slab_matches_the_owner_table(self):
        for upper, business, suv, first in FULL_TABLE:
            miles = D(str(upper))
            self.assertEqual(driver_slab_pay(miles, "sedan"), D(business), upper)
            self.assertEqual(driver_slab_pay(miles, "suv"), D(suv), upper)
            self.assertEqual(driver_slab_pay(miles, "first"), D(first), upper)

    def test_boundaries_are_inclusive_on_the_upper_end(self):
        # miles <= bound belongs to that slab; just past it moves up.
        # The 1-5 / 5-10 split (owner decision 2026-11-20 ~06:35 EST):
        # at 5.0 SUV is $80 and First $100; at 5.1 they are $90/$110.
        self.assertEqual(driver_slab_pay(D("5.0"), "suv"), D("80"))
        self.assertEqual(driver_slab_pay(D("5.1"), "suv"), D("90"))
        self.assertEqual(driver_slab_pay(D("5.0"), "first"), D("100"))
        self.assertEqual(driver_slab_pay(D("5.1"), "first"), D("110"))
        self.assertEqual(driver_slab_pay(D("10.0"), "sedan"), D("80"))
        self.assertEqual(driver_slab_pay(D("10.1"), "sedan"), D("95"))
        self.assertEqual(driver_slab_pay(D("20.0"), "suv"), D("130"))
        self.assertEqual(driver_slab_pay(D("20.1"), "suv"), D("160"))
        self.assertEqual(driver_slab_pay(D("30.0"), "first"), D("190"))
        self.assertEqual(driver_slab_pay(D("30.1"), "first"), D("200"))
        self.assertEqual(driver_slab_pay(D("40.0"), "sedan"), D("140"))
        self.assertEqual(driver_slab_pay(D("40.1"), "sedan"), D("160"))
        self.assertEqual(driver_slab_pay(D("140.0"), "first"), D("400"))
        self.assertEqual(driver_slab_pay(D("140.1"), "first"), D("420"))
        self.assertEqual(driver_slab_pay(D("400.0"), "sedan"), D("860"))

    def test_mid_slab_rides_pay_the_flat_slab_amount(self):
        # 2.0 mi: 1-5 slab (Business $80, SUV $80, First $100).
        self.assertEqual(driver_slab_pay(D("2.0"), "sedan"), D("80"))
        self.assertEqual(driver_slab_pay(D("2.0"), "suv"), D("80"))
        self.assertEqual(driver_slab_pay(D("2.0"), "first"), D("100"))
        # 7.3 mi (home -> JFK) and 10.0 mi: 5-10 slab, same pay
        # whatever the exact miles inside the slab.
        for miles in ("7.3", "10.0"):
            self.assertEqual(driver_slab_pay(D(miles), "sedan"), D("80"), miles)
            self.assertEqual(driver_slab_pay(D(miles), "suv"), D("90"), miles)
            self.assertEqual(driver_slab_pay(D(miles), "first"), D("110"), miles)
        # 25 mi: 20-30 slab.
        self.assertEqual(driver_slab_pay(D("25.0"), "sedan"), D("125"))
        self.assertEqual(driver_slab_pay(D("25.0"), "suv"), D("160"))
        self.assertEqual(driver_slab_pay(D("25.0"), "first"), D("190"))
        # 250 mi: 240-250 slab (generated tail, +$20 a slab).
        self.assertEqual(driver_slab_pay(D("250.0"), "sedan"), D("560"))
        self.assertEqual(driver_slab_pay(D("250.0"), "suv"), D("580"))
        self.assertEqual(driver_slab_pay(D("250.0"), "first"), D("620"))

    def test_suv_equal_at_20_30_and_30_40_is_the_owner_numbers(self):
        # SUV is $160 at BOTH 20-30 and 30-40 — the owner's own
        # dictated numbers; equal is fine, do NOT "fix" it.
        self.assertEqual(driver_slab_pay(D("25.0"), "suv"), D("160"))
        self.assertEqual(driver_slab_pay(D("35.0"), "suv"), D("160"))

    def test_toll_is_added_on_top_of_the_slab(self):
        r = compute_one_way(D("18.0"), toll=D("18.50"))
        self.assertEqual(r["driver_earnings"], D("113.50"))
        self.assertEqual(r["total"], D("180.50"))
        r = compute_one_way(D("20.0"), toll=D("16.00"), vehicle_class="suv")
        self.assertEqual(r["driver_earnings"], D("146.00"))
        # Profit still total - driver earnings.
        self.assertEqual(r["profit"], r["total"] - r["driver_earnings"])

    def test_hourly_rides_pay_per_class_hourly_rate(self):
        # Blacklane-style hourly (owner decision 2026-11-20): driver
        # Business $60/hr, SUV $70/hr, First $90/hr — slabs are
        # one-way distance rides only.
        r = compute_hourly(3, "sedan")
        self.assertEqual(r["driver_earnings"], D("180.00"))
        self.assertEqual(r["total"], D("327.48"))
        self.assertEqual(compute_hourly(3, "suv")["driver_earnings"], D("210.00"))
        self.assertEqual(compute_hourly(3, "first")["driver_earnings"], D("270.00"))

    def test_over_400_miles_has_no_slab(self):
        with self.assertRaises(ValueError):
            driver_slab_pay(D("400.1"), "sedan")
        with self.assertRaises(ValueError):
            driver_slab_pay(D("500.0"), "suv")
        with self.assertRaises(ValueError):
            compute_one_way(D("450.0"))
        with self.assertRaises(ValueError):
            driver_slab_pay(D("10.0"), "luxury")
        with self.assertRaises(ValueError):
            driver_slab_pay(D("-1.0"), "sedan")

    def test_customer_fare_still_per_mile(self):
        # Customer pricing untouched: $9/mi sedan, $10/mi SUV.
        self.assertEqual(compute_one_way(D("18.0"))["fare"], D("162.00"))
        self.assertEqual(
            compute_one_way(D("18.0"), vehicle_class="suv")["fare"], D("180.00"))
        self.assertEqual(compute_one_way(D("380.0"))["fare"], D("3420.00"))


class SlabApiCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._orig_distance_miles = geo_module.distance_miles
        self._phone_seq = 0

    def tearDown(self):
        geo_module.distance_miles = self._orig_distance_miles

    def stub_miles(self, miles):
        geo_module.distance_miles = lambda p, d, **kw: (  # noqa: E731
            miles, (40.6413, -73.7781), (40.7580, -73.9855))

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Slab Customer",
            "phone": f"+1555007{self._phone_seq:04d}",
            "email": "slab@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        return self.client.post("/api/bookings", json=payload)

    def test_booking_over_400_miles_is_refused_400(self):
        self.stub_miles(450.0)
        resp = self.book()
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:300])
        self.assertIn("400 miles", resp.get_json()["error"])
        with app_module.app.app_context():
            self.assertEqual(app_module.Booking.query.count(), 0)

    def test_booking_at_exactly_400_miles_uses_the_last_slab(self):
        self.stub_miles(400.0)
        # Legacy customer total ($9/mi) is the fixture here; the slab
        # driver pay is the point of the test.
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"}):
            resp = self.book()
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        booking = resp.get_json()["booking"]
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            self.assertEqual(row.driver_earnings, D("860.00"))
            self.assertEqual(row.fare_total, D("3600.00"))

    def test_booking_at_380_miles_pays_the_370_380_slab(self):
        self.stub_miles(380.0)
        # Legacy customer total ($9/mi) is the fixture here; the slab
        # driver pay is the point of the test.
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"}):
            resp = self.book()
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:300])
        booking = resp.get_json()["booking"]
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking["id"])
            self.assertEqual(row.driver_earnings, D("820.00"))
            self.assertEqual(row.fare_total, D("3420.00"))

    def test_fare_preview_over_400_miles_is_refused_400(self):
        self.stub_miles(450.0)
        resp = self.client.get("/api/fare-preview", query_string={
            "pickup": "JFK Airport", "dropoff": "Times Square, New York"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("400 miles", resp.get_json()["error"])

    def test_fare_preview_at_380_miles_shows_slab_driver_pay(self):
        self.stub_miles(380.0)
        resp = self.client.get("/api/fare-preview", query_string={
            "pickup": "JFK Airport", "dropoff": "Times Square, New York"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:300])
        body = resp.get_json()
        self.assertEqual(body["miles"], 380.0)
        self.assertEqual(body["legacy"]["sedan"]["driver_earnings"], 820.00)
        self.assertEqual(body["legacy"]["sedan"]["total"], 3420.00)


if __name__ == "__main__":
    unittest.main()
