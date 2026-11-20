"""Tests for the driver payout schedule.

Settled rule (owner, 2026-11-16, clarified the same day): every
the following week the driver gets seven days' money. Each week's
accounting is separate, and the money comes after two weeks. Trips
tally in 7-day weeks anchored at 2026-11-16 (week 0 = Nov 16-22,
2026), and each week's payout comes due 7 days after the week
starts: week 0 due Nov 23, 2026; week 1 (Nov 23-29) due Nov 30,
2026; week 2 (Nov 30-Dec 6) due Dec 7, 2026. Due dates fall 7
days apart, so every trip is paid 1-7 days after it happens.
completed, non-refunded trip belongs to the week containing its
completion date (America/New_York); the owner marks a week paid.

Covers: week grouping incl. boundary dates, due dates, mark-paid
behavior, owed math (paid trips excluded), refunded exclusion, and
driver-side privacy (earnings amounts only).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from unittest import mock
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-payouts-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "payouts.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "payouts-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles -> driver $95.00 (10-20 slab).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
from payouts import ANCHOR, PAYOUT_INTERVAL_DAYS, WEEK_DAYS, completion_date, week_bounds, week_for  # noqa: E402

D = Decimal
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}


def _utc(y, mo, d, h=15, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


class TestWeekMath(unittest.TestCase):
    def test_anchor_and_lengths(self):
        self.assertEqual(ANCHOR, date(2026, 11, 16))
        self.assertEqual(WEEK_DAYS, 7)
        self.assertEqual(PAYOUT_INTERVAL_DAYS, 7)

    def test_week_zero_boundaries(self):
        w = week_for(date(2026, 11, 16))
        self.assertEqual((w["index"], w["start"], w["end"], w["due_date"]),
                         (0, date(2026, 11, 16), date(2026, 11, 22), date(2026, 11, 23)))
        w = week_for(date(2026, 11, 22))
        self.assertEqual(w["index"], 0)
        self.assertEqual(w["due_date"], date(2026, 11, 23))

    def test_week_one_boundaries(self):
        w = week_for(date(2026, 11, 23))
        self.assertEqual((w["index"], w["start"], w["end"], w["due_date"]),
                         (1, date(2026, 11, 23), date(2026, 11, 29), date(2026, 11, 30)))
        self.assertEqual(week_for(date(2026, 11, 29))["index"], 1)

    def test_week_two_boundaries(self):
        w = week_for(date(2026, 11, 30))
        self.assertEqual((w["index"], w["start"], w["end"], w["due_date"]),
                         (2, date(2026, 11, 30), date(2026, 12, 6), date(2026, 12, 7)))
        self.assertEqual(week_for(date(2026, 12, 6))["index"], 2)

    def test_every_week_is_7_days_and_due_dates_fall_7_days_apart(self):
        prev_due = None
        for i in range(0, 30):
            w = week_bounds(i)
            self.assertEqual((w["end"] - w["start"]).days, 6)
            # due = week start + 7 days: a trip on the first day of the
            # week is paid 7 days later, one on the last day 1 day
            # later — the lag never grows.
            self.assertEqual(w["due_date"], w["start"] + timedelta(days=7))
            self.assertEqual((w["due_date"] - w["end"]).days, 1)
            if prev_due is not None:
                self.assertEqual((w["due_date"] - prev_due).days, 7)
            prev_due = w["due_date"]
            self.assertEqual(week_for(w["start"])["index"], i)
            self.assertEqual(week_for(w["end"])["index"], i)

    def test_weeks_are_contiguous(self):
        for i in range(0, 10):
            self.assertEqual(week_bounds(i)["end"] + timedelta(days=1),
                             week_bounds(i + 1)["start"])

    def test_date_before_anchor_lands_on_same_grid(self):
        w = week_for(date(2026, 11, 15))
        self.assertEqual((w["index"], w["start"], w["end"], w["due_date"]),
                         (-1, date(2026, 11, 9), date(2026, 11, 15), date(2026, 11, 16)))

    def test_completion_date_uses_new_york(self):
        # 02:00 UTC on Nov 30 is 21:00 EST on Nov 29 -> week 1.
        self.assertEqual(completion_date(_utc(2026, 11, 30, 2, 0)), date(2026, 11, 29))
        self.assertEqual(week_for(completion_date(_utc(2026, 11, 30, 2, 0)))["index"], 1)
        # 06:00 UTC on Nov 30 is 01:00 EST on Nov 30 -> week 2.
        self.assertEqual(completion_date(_utc(2026, 11, 30, 6, 0)), date(2026, 11, 30))
        self.assertEqual(week_for(completion_date(_utc(2026, 11, 30, 6, 0)))["index"], 2)

    def test_completion_date_naive_read_as_utc_and_fallback(self):
        naive = datetime(2026, 11, 30, 2, 0)  # no tzinfo -> UTC
        self.assertEqual(completion_date(naive), date(2026, 11, 29))
        created = _utc(2026, 11, 20, 15, 0)
        self.assertEqual(completion_date(None, created), date(2026, 11, 20))


# These tests pin the legacy $9/$10 totals as fixtures (the payout
# mechanics are engine-independent); the live engine is Blacklane
# by default since the owner flip (2026-11-20).
@mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"})
class PayoutApiCase(unittest.TestCase):
    """In-process API tests with a fresh DB per test."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self):
        self._driver_seq += 1
        phone = f"+1555000{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Test Driver {self._driver_seq}", "phone": phone,
            "email": f"d{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"T{self._driver_seq:05d}",
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

    def complete_ride(self, token, ride_type="one_way", hours=None):
        payload = {
            "customer_name": "Payout Customer", "phone": "+15550009999",
            "email": "cust@test.com", "pickup": "JFK Airport",
            "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": ride_type,
        }
        if ride_type == "hourly":
            payload["hours"] = hours
            payload.pop("dropoff")
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking_id = resp.get_json()["booking"]["id"]
        # Payment comes BEFORE dispatch: pay first, then the driver
        # accepts, then the trip runs stage by stage.
        resp = self.client.post(f"/api/bookings/{booking_id}/pay", json={
            "card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Payout Customer"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        for event in ("en_route", "arrived", "start", "complete"):
            resp = self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                    json={"event": event},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")
        return booking_id

    def backdate_completion(self, booking_id, completed_at):
        with app_module.app.app_context():
            booking = app_module.db.session.get(app_module.Booking, booking_id)
            booking.completed_at = completed_at
            app_module.db.session.commit()

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)

    def owner_summary(self):
        return self.client.get("/api/owner/summary").get_json()

    # -- grouping / due dates --------------------------------------------
    def test_earnings_grouped_by_week_with_due_dates(self):
        _driver, token = self.register_driver()
        b1 = self.complete_ride(token)
        b2 = self.complete_ride(token)
        self.backdate_completion(b1, _utc(2026, 11, 20))   # week 0
        self.backdate_completion(b2, _utc(2026, 12, 1))    # week 2
        resp = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token})
        body = resp.get_json()
        self.assertEqual(body["completed_rides"], 2)
        self.assertNotIn("total_earnings", body)
        weeks = body["weeks"]
        self.assertEqual(len(weeks), 2)
        # Newest week first.
        self.assertEqual(weeks[0]["index"], 2)
        self.assertEqual((weeks[0]["start"], weeks[0]["end"], weeks[0]["due_date"]),
                         ("2026-11-30", "2026-12-06", "2026-12-07"))
        self.assertEqual(weeks[0]["ride_count"], 1)
        self.assertNotIn("total_earnings", weeks[0])
        self.assertEqual(weeks[0]["status"], "unpaid")
        self.assertIs(weeks[0]["paid"], False)
        self.assertEqual(weeks[1]["index"], 0)
        self.assertEqual((weeks[1]["start"], weeks[1]["end"], weeks[1]["due_date"]),
                         ("2026-11-16", "2026-11-22", "2026-11-23"))
        self.assertEqual(weeks[1]["ride_count"], 1)
        # Per-ride list is kept, with week + payout info per ride.
        rides = {r["id"]: r for r in body["rides"]}
        self.assertEqual(rides[b1]["week_start"], "2026-11-16")
        self.assertEqual(rides[b1]["week_end"], "2026-11-22")
        self.assertEqual(rides[b1]["due_date"], "2026-11-23")
        self.assertEqual(rides[b1]["payout_status"], "unpaid")
        self.assertIs(rides[b1]["payout_paid"], False)
        self.assertEqual(rides[b2]["week_start"], "2026-11-30")
        self.assertEqual(rides[b2]["due_date"], "2026-12-07")
        self.assertNotIn("earnings", rides[b1])
        # The same money is still visible to the owner: $95 in each week.
        self.owner_login()
        payouts = self.client.get("/api/owner/payouts").get_json()
        by_week = {p["index"]: p for p in payouts}
        self.assertEqual(D(str(by_week[0]["total_earnings"])), D("95.00"))
        self.assertEqual(D(str(by_week[2]["total_earnings"])), D("95.00"))

    def test_multiple_rides_sum_in_one_week(self):
        _driver, token = self.register_driver()
        b1 = self.complete_ride(token)                    # one-way: $95.00
        b2 = self.complete_ride(token, ride_type="hourly", hours=3)  # $150.00
        self.backdate_completion(b1, _utc(2026, 11, 17))
        self.backdate_completion(b2, _utc(2026, 11, 20))
        body = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(len(body["weeks"]), 1)
        self.assertEqual(body["weeks"][0]["ride_count"], 2)
        self.assertNotIn("total_earnings", body["weeks"][0])
        self.owner_login()
        payouts = self.client.get("/api/owner/payouts").get_json()
        self.assertEqual(D(str(payouts[0]["total_earnings"])), D("245.00"))

    def test_boundary_completion_dates_split_weeks(self):
        _driver, token = self.register_driver()
        # Nov 29 21:00 EST (Nov 30 02:00 UTC) -> week 1; Nov 30 01:00 EST -> week 2.
        b1 = self.complete_ride(token)
        b2 = self.complete_ride(token)
        self.backdate_completion(b1, _utc(2026, 11, 30, 2, 0))
        self.backdate_completion(b2, _utc(2026, 11, 30, 6, 0))
        body = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token}).get_json()
        self.assertEqual([w["index"] for w in body["weeks"]], [2, 1])

    def test_driver_earnings_response_has_no_fare_fields(self):
        _driver, token = self.register_driver()
        self.complete_ride(token)
        resp = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token})
        body = resp.get_json()
        for week in body["weeks"]:
            self.assertFalse(set(week) & FORBIDDEN_KEYS, str(week))
        for ride in body["rides"]:
            self.assertFalse(set(ride) & FORBIDDEN_KEYS, str(ride))
        # The customer fare total must never appear in the driver response.
        self.assertNotIn("162.00", resp.get_data(as_text=True))

    # -- mark-paid --------------------------------------------------------
    def test_mark_paid_requires_owner_pin(self):
        driver, token = self.register_driver()
        self.complete_ride(token)
        fresh = app_module.app.test_client()  # no owner session
        resp = fresh.post("/api/owner/payouts/mark-paid",
                          json={"driver_id": driver["id"], "week_index": 0})
        self.assertEqual(resp.status_code, 401)
        resp = fresh.get("/api/owner/payouts")
        self.assertEqual(resp.status_code, 401)

    def test_mark_paid_flow_and_idempotency(self):
        driver, token = self.register_driver()
        b1 = self.complete_ride(token)
        self.backdate_completion(b1, _utc(2026, 11, 20))
        self.owner_login()
        resp = self.client.post("/api/owner/payouts/mark-paid",
                                json={"driver_id": driver["id"], "week_index": 0})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        payout = resp.get_json()["payout"]
        self.assertTrue(payout["paid"])
        self.assertEqual(payout["status"], "paid")
        self.assertEqual(payout["marked"], 1)
        self.assertEqual(payout["due_date"], "2026-11-23")
        # Driver view now shows the week paid.
        body = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(body["weeks"][0]["status"], "paid")
        self.assertTrue(body["rides"][0]["payout_paid"])
        # Marking again is a harmless no-op.
        resp = self.client.post("/api/owner/payouts/mark-paid",
                                json={"driver_id": driver["id"], "week_index": 0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["payout"]["marked"], 0)
        self.assertTrue(resp.get_json()["payout"]["paid"])

    def test_mark_paid_validation_errors(self):
        driver, token = self.register_driver()
        self.complete_ride(token)
        self.owner_login()
        resp = self.client.post("/api/owner/payouts/mark-paid", json={})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post("/api/owner/payouts/mark-paid",
                                json={"driver_id": 99999, "week_index": 0})
        self.assertEqual(resp.status_code, 404)
        resp = self.client.post("/api/owner/payouts/mark-paid",
                                json={"driver_id": driver["id"], "week_index": 99})
        self.assertEqual(resp.status_code, 404)

    def test_late_completion_into_paid_week_stays_unpaid(self):
        driver, token = self.register_driver()
        b1 = self.complete_ride(token)
        self.backdate_completion(b1, _utc(2026, 11, 20))
        self.owner_login()
        self.client.post("/api/owner/payouts/mark-paid",
                         json={"driver_id": driver["id"], "week_index": 0})
        # A second trip completed later, dated inside the same week.
        b2 = self.complete_ride(token)
        self.backdate_completion(b2, _utc(2026, 11, 21))
        body = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token}).get_json()
        week0 = [w for w in body["weeks"] if w["index"] == 0][0]
        self.assertEqual(week0["status"], "unpaid")
        self.assertEqual(week0["ride_count"], 2)
        self.assertNotIn("total_earnings", week0)
        self.assertEqual(D(str(self.owner_summary()["driver_owed"])), D("95.00"))

    # -- owed math ---------------------------------------------------------
    def test_owed_counts_only_unpaid_completed_trips(self):
        driver, token = self.register_driver()
        b1 = self.complete_ride(token)
        b2 = self.complete_ride(token)
        self.backdate_completion(b1, _utc(2026, 11, 20))   # week 0
        self.backdate_completion(b2, _utc(2026, 12, 1))    # week 2
        self.owner_login()
        summary = self.owner_summary()
        self.assertEqual(D(str(summary["driver_owed"])), D("190.00"))
        self.assertEqual(D(str(summary["profit"])),
                         D(str(summary["gross"])) - D(str(summary["driver_owed"])))
        self.client.post("/api/owner/payouts/mark-paid",
                         json={"driver_id": driver["id"], "week_index": 0})
        summary = self.owner_summary()
        self.assertEqual(D(str(summary["driver_owed"])), D("95.00"))
        self.assertEqual(D(str(summary["profit"])),
                         D(str(summary["gross"])) - D("95.00"))
        self.client.post("/api/owner/payouts/mark-paid",
                         json={"driver_id": driver["id"], "week_index": 2})
        self.assertEqual(D(str(self.owner_summary()["driver_owed"])), D("0.00"))

    def test_uncompleted_and_kept_price_trips_do_not_count_as_owed(self):
        driver, token = self.register_driver()
        # Awaiting payment, never sent to drivers: no earnings owed.
        self.client.post("/api/bookings", json={
            "customer_name": "Waiting", "phone": "+15550001122", "email": "w@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way"})
        # Kept-price cancellation (pickup within an hour): fare kept, but
        # the trip never completed, so nothing is owed to the driver.
        try:
            from zoneinfo import ZoneInfo
            soon = datetime.now(ZoneInfo("America/New_York")) + timedelta(minutes=30)
        except Exception:
            soon = datetime.now(timezone.utc) + timedelta(minutes=30)
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Soon", "phone": "+15550003333", "email": "s@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": soon.strftime("%Y-%m-%d"), "time": soon.strftime("%H:%M"),
            "ride_type": "one_way"})
        soon_id = resp.get_json()["booking"]["id"]
        self.client.post(f"/api/bookings/{soon_id}/pay", json={
            "card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Soon"})
        self.client.post(f"/api/drivers/me/offers/{soon_id}/accept",
                         headers={"X-Driver-Token": token})
        resp = self.client.post(f"/api/bookings/{soon_id}/cancel",
                                json={"phone": "+15550003333"})
        self.assertTrue(resp.get_json()["charge_kept"])
        self.owner_login()
        summary = self.owner_summary()
        self.assertEqual(D(str(summary["driver_owed"])), D("0.00"))
        # Gross still includes the kept payment.
        self.assertEqual(D(str(summary["gross"])), D("162.00"))

    def test_refunded_completed_trip_is_excluded(self):
        _driver, token = self.register_driver()
        booking_id = self.complete_ride(token)
        with app_module.app.app_context():
            payment = app_module.Payment.query.filter_by(booking_id=booking_id).first()
            payment.status = "refunded"
            app_module.db.session.commit()
        body = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": token}).get_json()
        self.assertEqual(body["completed_rides"], 0)
        self.assertEqual(body["weeks"], [])
        self.assertNotIn("total_earnings", body)
        self.owner_login()
        self.assertEqual(D(str(self.owner_summary()["driver_owed"])), D("0.00"))
        payouts = self.client.get("/api/owner/payouts").get_json()
        self.assertEqual(payouts, [])

    def test_completed_at_recorded_and_row_flags_payout(self):
        driver, token = self.register_driver()
        booking_id = self.complete_ride(token)
        self.owner_login()
        detail = self.client.get(f"/api/owner/bookings/{booking_id}").get_json()
        self.assertIsNotNone(detail["completed_at"])
        self.assertIs(detail["payout_paid"], False)
        rows = self.client.get("/api/owner/bookings").get_json()
        self.assertIs(rows[0]["payout_paid"], False)
        payouts = self.client.get("/api/owner/payouts").get_json()
        self.assertEqual(len(payouts), 1)
        resp = self.client.post("/api/owner/payouts/mark-paid",
                                json={"driver_id": driver["id"],
                                      "week_index": payouts[0]["index"]})
        self.assertEqual(resp.status_code, 200)
        payouts = self.client.get("/api/owner/payouts").get_json()
        self.assertTrue(payouts[0]["paid"])

    # -- owner payouts endpoint --------------------------------------------
    def test_owner_payouts_groups_per_driver_per_week(self):
        d1, t1 = self.register_driver()
        d2, t2 = self.register_driver()
        b1 = self.complete_ride(t1)
        b2 = self.complete_ride(t1)
        b3 = self.complete_ride(t2)
        self.backdate_completion(b1, _utc(2026, 11, 20))
        self.backdate_completion(b2, _utc(2026, 12, 1))
        self.backdate_completion(b3, _utc(2026, 11, 21))
        self.owner_login()
        payouts = self.client.get("/api/owner/payouts").get_json()
        self.assertEqual(len(payouts), 3)
        by_key = {(p["driver_id"], p["index"]): p for p in payouts}
        w0_d1 = by_key[(d1["id"], 0)]
        self.assertEqual(w0_d1["driver_name"], d1["name"])
        self.assertEqual(w0_d1["due_date"], "2026-11-23")
        self.assertEqual(D(str(w0_d1["total_earnings"])), D("95.00"))
        self.assertEqual(w0_d1["status"], "unpaid")
        self.assertEqual([r["id"] for r in w0_d1["rides"]], [b1])
        w2_d1 = by_key[(d1["id"], 2)]
        self.assertEqual(w2_d1["due_date"], "2026-12-07")
        w0_d2 = by_key[(d2["id"], 0)]
        self.assertEqual(w0_d2["driver_name"], d2["name"])
        self.assertEqual(D(str(w0_d2["total_earnings"])), D("95.00"))


if __name__ == "__main__":
    unittest.main()
