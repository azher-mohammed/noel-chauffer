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
)

D = Decimal


class TestOneWay(unittest.TestCase):
    def test_18_miles_no_toll_no_referral(self):
        r = compute_one_way(D("18.0"))
        self.assertEqual(r["total"], D("160.60"))
        self.assertEqual(r["driver_earnings"], D("72.00"))
        self.assertEqual(r["gratuity"], D("14.60"))
        self.assertEqual(r["booking_fee"], D("20"))
        self.assertEqual(r["profit"], D("88.60"))

    def test_18_miles_with_referral(self):
        r = compute_one_way(D("18.0"), referral=True)
        # Exactly $20 off the FINAL total (gratuity still on the full subtotal).
        self.assertEqual(r["total"], D("140.60"))
        self.assertEqual(r["gratuity"], D("14.60"))
        self.assertEqual(r["driver_earnings"], D("72.00"))

    def test_18_miles_with_toll(self):
        r = compute_one_way(D("18.0"), toll=D("18.50"))
        self.assertEqual(r["total"], D("180.95"))
        self.assertEqual(r["driver_earnings"], D("90.50"))

    def test_35_mile_trial_example(self):
        # Trial figures: customer $291.50, driver $140, profit $151.50, no toll.
        r = compute_one_way(D("35.0"))
        self.assertEqual(r["total"], D("291.50"))
        self.assertEqual(r["driver_earnings"], D("140.00"))
        self.assertEqual(r["profit"], D("151.50"))


class TestHourly(unittest.TestCase):
    def test_3_hours(self):
        r = compute_hourly(3)
        self.assertEqual(r["total"], D("270.00"))
        self.assertEqual(r["driver_earnings"], D("150.00"))
        self.assertEqual(r["booking_fee"], D("0.00"))
        self.assertEqual(r["gratuity"], D("0.00"))


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
