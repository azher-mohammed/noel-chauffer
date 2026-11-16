"""Unit tests for Noel Chauffer pricing — the verified cases from the spec.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pricing import (  # noqa: E402
    cancellation_refundable,
    compute_hourly,
    compute_one_way,
    free_waiting_minutes,
    is_airport_pickup,
    waiting_charge,
    waiting_time_elapsed,
)

D = Decimal


class TestOneWay(unittest.TestCase):
    def test_18_miles_sedan_no_toll_no_referral(self):
        # fare $198.00 + gratuity $19.80 + tax $17.57 = $235.37.
        r = compute_one_way(D("18.0"))
        self.assertEqual(r["vehicle_class"], "sedan")
        self.assertEqual(r["fare"], D("198.00"))
        self.assertEqual(r["gratuity"], D("19.80"))
        self.assertEqual(r["tax"], D("17.57"))
        self.assertEqual(r["booking_fee"], D("0"))
        self.assertEqual(r["total"], D("235.37"))
        self.assertEqual(r["driver_earnings"], D("72.00"))
        self.assertEqual(r["profit"], D("145.80"))

    def test_18_miles_suv(self):
        # fare $216.00 + gratuity $21.60 + tax $19.17 = $256.77.
        r = compute_one_way(D("18.0"), vehicle_class="suv")
        self.assertEqual(r["vehicle_class"], "suv")
        self.assertEqual(r["fare"], D("216.00"))
        self.assertEqual(r["gratuity"], D("21.60"))
        self.assertEqual(r["tax"], D("19.17"))
        self.assertEqual(r["total"], D("256.77"))
        self.assertEqual(r["driver_earnings"], D("126.00"))
        self.assertEqual(r["profit"], D("111.60"))

    def test_18_miles_with_referral_is_no_discount_for_now(self):
        # Referral codes are accepted but give a $0 discount for now
        # (the old $20-fee waiver is dead: there is no fee). TBD.
        r = compute_one_way(D("18.0"), referral=True)
        self.assertEqual(r["total"], D("235.37"))
        self.assertEqual(r["gratuity"], D("19.80"))
        self.assertEqual(r["driver_earnings"], D("72.00"))

    def test_18_miles_with_toll(self):
        # Toll passes through untaxed: tax stays $17.57, total and
        # driver earnings both rise by exactly the toll.
        r = compute_one_way(D("18.0"), toll=D("18.50"))
        self.assertEqual(r["total"], D("253.87"))
        self.assertEqual(r["driver_earnings"], D("90.50"))
        self.assertEqual(r["tax"], D("17.57"))

    def test_35_mile_sedan(self):
        # fare $385.00 + gratuity $38.50 + tax $34.17 = $457.67.
        r = compute_one_way(D("35.0"))
        self.assertEqual(r["total"], D("457.67"))
        self.assertEqual(r["driver_earnings"], D("140.00"))
        self.assertEqual(r["profit"], D("283.50"))

    def test_invalid_class_rejected(self):
        with self.assertRaises(ValueError):
            compute_one_way(D("10.0"), vehicle_class="luxury")


class TestHourly(unittest.TestCase):
    def test_3_hours(self):
        r = compute_hourly(3)
        self.assertEqual(r["total"], D("270.00"))
        self.assertEqual(r["driver_earnings"], D("150.00"))
        self.assertEqual(r["booking_fee"], D("0.00"))
        self.assertEqual(r["gratuity"], D("0.00"))
        self.assertEqual(r["tax"], D("0.00"))
        self.assertIsNone(r["vehicle_class"])


class TestWaiting(unittest.TestCase):
    def test_airport_heuristic(self):
        for text in ("JFK Airport", "LaGuardia Airport", "Newark Liberty Intl", "EWR Terminal B", "LGA"):
            self.assertTrue(is_airport_pickup(text), text)
        self.assertFalse(is_airport_pickup("123 Main Street"))
        self.assertEqual(free_waiting_minutes("JFK Airport"), 60)
        self.assertEqual(free_waiting_minutes("123 Main Street"), 15)

    def test_75_minutes_at_airport(self):
        self.assertEqual(waiting_charge("JFK Airport", 75), D("15.00"))

    def test_within_free_allowance(self):
        self.assertEqual(waiting_charge("JFK Airport", 60), D("0.00"))
        self.assertEqual(waiting_charge("123 Main Street", 15), D("0.00"))

    def test_non_airport_overage(self):
        self.assertEqual(waiting_charge("123 Main Street", 20), D("5.00"))


class TestWaitingTimeElapsed(unittest.TestCase):
    # Pickup 2030-06-01 12:00 New York = 16:00 UTC (EDT).
    def test_regular_pickup_15_minutes(self):
        self.assertFalse(waiting_time_elapsed(
            "2030-06-01", "12:00", "123 Main Street",
            now=datetime(2030, 6, 1, 16, 14, tzinfo=timezone.utc)))
        # Boundary: exactly 15 minutes after pickup counts as elapsed.
        self.assertTrue(waiting_time_elapsed(
            "2030-06-01", "12:00", "123 Main Street",
            now=datetime(2030, 6, 1, 16, 15, tzinfo=timezone.utc)))
        self.assertTrue(waiting_time_elapsed(
            "2030-06-01", "12:00", "123 Main Street",
            now=datetime(2030, 6, 1, 16, 16, tzinfo=timezone.utc)))

    def test_airport_pickup_60_minutes(self):
        self.assertFalse(waiting_time_elapsed(
            "2030-06-01", "12:00", "JFK Airport",
            now=datetime(2030, 6, 1, 16, 59, tzinfo=timezone.utc)))
        self.assertTrue(waiting_time_elapsed(
            "2030-06-01", "12:00", "JFK Airport",
            now=datetime(2030, 6, 1, 17, 0, tzinfo=timezone.utc)))
        self.assertTrue(waiting_time_elapsed(
            "2030-06-01", "12:00", "JFK Airport",
            now=datetime(2030, 6, 1, 17, 1, tzinfo=timezone.utc)))

    def test_naive_now_treated_as_utc(self):
        self.assertTrue(waiting_time_elapsed(
            "2030-06-01", "12:00", "123 Main Street",
            now=datetime(2030, 6, 1, 16, 15)))
        self.assertFalse(waiting_time_elapsed(
            "2030-06-01", "12:00", "123 Main Street",
            now=datetime(2030, 6, 1, 16, 14)))

    def test_now_defaults_to_current_time(self):
        # A pickup far in the future has not elapsed; one far in the
        # past has — deterministic whatever the real clock says.
        self.assertFalse(waiting_time_elapsed("2030-06-01", "12:00", "123 Main Street"))
        self.assertTrue(waiting_time_elapsed("2020-01-01", "12:00", "JFK Airport"))


class TestCancellation(unittest.TestCase):
    def test_more_than_one_hour_before_is_free(self):
        # Pickup 2030-06-01 12:00 New York; "now" 2 hours before (UTC).
        now = datetime(2030, 6, 1, 14, 0, tzinfo=timezone.utc)  # 10:00 EDT
        self.assertTrue(cancellation_refundable("2030-06-01", "12:00", now=now))

    def test_one_hour_or_less_keeps_full_price(self):
        now = datetime(2030, 6, 1, 15, 0, tzinfo=timezone.utc)  # 11:00 EDT, exactly 1h before
        self.assertFalse(cancellation_refundable("2030-06-01", "12:00", now=now))
        now = datetime(2030, 6, 1, 15, 30, tzinfo=timezone.utc)  # 30 min before
        self.assertFalse(cancellation_refundable("2030-06-01", "12:00", now=now))


if __name__ == "__main__":
    unittest.main()
