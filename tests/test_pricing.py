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
    driver_cancel_locked,
    free_waiting_minutes,
    is_airport_pickup,
    waiting_charge,
    waiting_time_elapsed,
)

D = Decimal


class TestOneWay(unittest.TestCase):
    def test_18_miles_sedan_no_toll_no_referral(self):
        # fare $162.00, no gratuity, no tax: total = fare = $162.00.
        r = compute_one_way(D("18.0"))
        self.assertEqual(r["vehicle_class"], "sedan")
        self.assertEqual(r["fare"], D("162.00"))
        self.assertEqual(r["gratuity"], D("0.00"))
        self.assertEqual(r["tax"], D("0.00"))
        self.assertEqual(r["booking_fee"], D("0"))
        self.assertEqual(r["total"], D("162.00"))
        self.assertEqual(r["driver_earnings"], D("95.00"))
        self.assertEqual(r["profit"], D("67.00"))

    def test_18_miles_suv(self):
        # fare $180.00, no gratuity, no tax: total = fare = $180.00.
        r = compute_one_way(D("18.0"), vehicle_class="suv")
        self.assertEqual(r["vehicle_class"], "suv")
        self.assertEqual(r["fare"], D("180.00"))
        self.assertEqual(r["gratuity"], D("0.00"))
        self.assertEqual(r["tax"], D("0.00"))
        self.assertEqual(r["total"], D("180.00"))
        self.assertEqual(r["driver_earnings"], D("130.00"))
        self.assertEqual(r["profit"], D("50.00"))

    def test_18_miles_with_referral_is_five_percent_off(self):
        # Referral: a new customer's first booking with a valid code
        # gets 5% off the total (owner decision 2026-11-18). Driver
        # pay is unchanged; the discount comes out of profit only.
        r = compute_one_way(D("18.0"), referral=True)
        self.assertEqual(r["referral_discount"], D("8.10"))
        self.assertEqual(r["total"], D("153.90"))
        self.assertEqual(r["gratuity"], D("0.00"))
        self.assertEqual(r["driver_earnings"], D("95.00"))
        self.assertEqual(r["profit"], D("58.90"))

    def test_18_miles_with_toll(self):
        # Toll passes through to the driver: total and driver
        # earnings both rise by exactly the toll; gratuity/tax
        # stay $0.00.
        r = compute_one_way(D("18.0"), toll=D("18.50"))
        self.assertEqual(r["total"], D("180.50"))
        self.assertEqual(r["driver_earnings"], D("113.50"))
        self.assertEqual(r["tax"], D("0.00"))

    def test_35_mile_sedan(self):
        # fare $315.00, no gratuity, no tax: total = fare = $315.00.
        # Driver $140.00 is the 30-40 mile slab (owner decision 2026-11-20).
        r = compute_one_way(D("35.0"))
        self.assertEqual(r["total"], D("315.00"))
        self.assertEqual(r["driver_earnings"], D("140.00"))
        self.assertEqual(r["profit"], D("175.00"))

    def test_invalid_class_rejected(self):
        with self.assertRaises(ValueError):
            compute_one_way(D("10.0"), vehicle_class="luxury")


class TestHourly(unittest.TestCase):
    # Blacklane-style hourly (owner decision 2026-11-20, "same same
    # Blacklane jaisa"): per-class rates from the live Blacklane quote
    # 2026-11-20 — 2-hour totals Business $218.32, SUV $269.46,
    # First $343.31; driver Business $60/hr, SUV $70/hr, First $90/hr.
    def test_2_hours_per_class(self):
        self.assertEqual(compute_hourly(2, "sedan")["total"], D("218.32"))
        self.assertEqual(compute_hourly(2, "sedan")["driver_earnings"], D("120.00"))
        self.assertEqual(compute_hourly(2, "suv")["total"], D("269.46"))
        self.assertEqual(compute_hourly(2, "suv")["driver_earnings"], D("140.00"))
        self.assertEqual(compute_hourly(2, "first")["total"], D("343.31"))
        self.assertEqual(compute_hourly(2, "first")["driver_earnings"], D("180.00"))

    def test_3_hours_per_class(self):
        self.assertEqual(compute_hourly(3, "sedan")["total"], D("327.48"))
        self.assertEqual(compute_hourly(3, "sedan")["driver_earnings"], D("180.00"))
        self.assertEqual(compute_hourly(3, "suv")["total"], D("404.19"))
        self.assertEqual(compute_hourly(3, "suv")["driver_earnings"], D("210.00"))
        self.assertEqual(compute_hourly(3, "first")["total"], D("514.97"))
        self.assertEqual(compute_hourly(3, "first")["driver_earnings"], D("270.00"))

    def test_all_in_no_separate_lines(self):
        r = compute_hourly(2, "sedan")
        self.assertEqual(r["booking_fee"], D("0.00"))
        self.assertEqual(r["gratuity"], D("0.00"))
        self.assertEqual(r["tax"], D("0.00"))
        self.assertEqual(r["toll"], D("0.00"))
        self.assertEqual(r["vehicle_class"], "sedan")
        self.assertEqual(r["miles_included"], D("50"))
        self.assertEqual(compute_hourly(3, "sedan")["miles_included"], D("75"))
        self.assertNotIn("km_included", r)

    def test_default_class_is_sedan(self):
        self.assertEqual(compute_hourly(2)["total"], D("218.32"))

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            compute_hourly(2, "luxury")


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

    def test_hourly_24_hour_window(self):
        # Blacklane-style hourly (owner decision 2026-11-20): free
        # cancellation up to 24 hours before pickup. Pickup 2030-06-01
        # 12:00 New York = 16:00 UTC.
        now = datetime(2030, 5, 31, 15, 0, tzinfo=timezone.utc)  # 25h before
        self.assertTrue(cancellation_refundable("2030-06-01", "12:00", now=now, free_cancel_hours=24))
        now = datetime(2030, 5, 31, 17, 0, tzinfo=timezone.utc)  # 23h before
        self.assertFalse(cancellation_refundable("2030-06-01", "12:00", now=now, free_cancel_hours=24))
        # The same 23-hours-before moment is still free on the 1-hour
        # one-way window.
        self.assertTrue(cancellation_refundable("2030-06-01", "12:00", now=now))


class TestDriverCancelLocked(unittest.TestCase):
    # Owner rule 2026-11-17: an accepted ride cannot be cancelled once
    # pickup is within 2 hours. Pickup 2030-06-01 12:00 New York =
    # 16:00 UTC (EDT), same clock basis as the other time gates.
    def test_more_than_two_hours_before_is_not_locked(self):
        now = datetime(2030, 6, 1, 13, 59, tzinfo=timezone.utc)  # 09:59 EDT
        self.assertFalse(driver_cancel_locked("2030-06-01", "12:00", now=now))

    def test_exactly_two_hours_before_is_locked(self):
        # Boundary: exactly 2 hours before pickup counts as within.
        now = datetime(2030, 6, 1, 14, 0, tzinfo=timezone.utc)  # 10:00 EDT
        self.assertTrue(driver_cancel_locked("2030-06-01", "12:00", now=now))

    def test_under_two_hours_is_locked(self):
        now = datetime(2030, 6, 1, 14, 1, tzinfo=timezone.utc)  # 10:01 EDT
        self.assertTrue(driver_cancel_locked("2030-06-01", "12:00", now=now))
        now = datetime(2030, 6, 1, 15, 30, tzinfo=timezone.utc)  # 30 min before
        self.assertTrue(driver_cancel_locked("2030-06-01", "12:00", now=now))

    def test_pickup_in_the_past_is_locked(self):
        now = datetime(2030, 6, 1, 16, 30, tzinfo=timezone.utc)  # 30 min after pickup
        self.assertTrue(driver_cancel_locked("2030-06-01", "12:00", now=now))

    def test_naive_now_treated_as_utc(self):
        self.assertTrue(driver_cancel_locked("2030-06-01", "12:00",
                                              now=datetime(2030, 6, 1, 15, 0)))
        self.assertFalse(driver_cancel_locked("2030-06-01", "12:00",
                                               now=datetime(2030, 6, 1, 13, 0)))

    def test_now_defaults_to_current_time(self):
        # A pickup far in the future is not locked; one far in the
        # past is — deterministic whatever the real clock says.
        self.assertFalse(driver_cancel_locked("2030-06-01", "12:00"))
        self.assertTrue(driver_cancel_locked("2020-01-01", "12:00"))


if __name__ == "__main__":
    unittest.main()
