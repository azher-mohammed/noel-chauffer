"""Tests for the owner dashboard Profit tab (owner decision 2026-11-23,
voice call): "owner dashboard mein ek profit wala hissa banao... khali
profit ka hissa... to mere ko idea ho jaye na, main kitna bana raha
hoon" — plus the follow-ups the same morning: profit must live in its
OWN section/tab ("profit alag, profit ke alag hisse mein na"), never
mixed into Money or Dashboard, with DAILY / WEEKLY / MONTHLY /
TILL-DATE sub-tabs ("daily ka tab kare daily ka bata dena, monthly ka
tab kare monthly ka bata dena, weekly ka tab kare weekly ka bata dena,
ELD ka tab kare ELD ka bata dena").

GET /api/owner/profit?period=<daily|weekly|monthly|tilldate> returns
that period's profit plus that period's rides (customer paid, driver
got, profit), and the totals of all four periods. Only COMPLETED rides
whose payment actually landed count: status "completed" + a Payment
with status "succeeded" (test mode) or "captured" (live Stripe) + not
refunded. Pending, awaiting-payment and cancelled rides earn nothing
yet. Per ride, profit reuses booking_profit(): fare_total + waiting -
driver_earnings - stored tax. Toll never counts as profit: it sits
inside BOTH the customer total and the driver earnings (slab pay +
toll), so it cancels out. Rides are bucketed on their completion date
(America/New_York, same rule as the daily summary and payout weeks).

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-profit-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "profit.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "profit-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

NY = ZoneInfo("America/New_York")
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ny_dt(day, hour=12, minute=0):
    """Aware UTC datetime for a New York wall time on `day`."""
    return datetime.combine(day, time(hour, minute), tzinfo=NY).astimezone(timezone.utc)


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class OwnerProfitCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0
        self.today = app_module._today_ny()

    # -- seed helpers ------------------------------------------------------
    def make_booking(self, status="completed", completed_day=None,
                     fare="200.00", driver_pay="102.46", waiting="0.00",
                     tax="0.00", toll="0.00", customer="Profit Customer"):
        self._seq += 1
        with app_module.app.app_context():
            b = app_module.Booking(
                customer_name=customer, phone=f"+1555030{self._seq:04d}",
                email="profit@test.com", pickup="JFK Airport",
                dropoff="Times Square, New York",
                date=(completed_day or self.today).isoformat(),
                time="12:00", ride_type="one_way", status=status,
                fare_total=Decimal(fare), driver_earnings=Decimal(driver_pay),
                waiting_charge=Decimal(waiting),
                fare=Decimal(fare), tax=Decimal(tax),
                toll=Decimal(toll),
                completed_at=(ny_dt(completed_day, 15)
                              if completed_day and status == "completed" else None),
                created_at=ny_dt(completed_day or self.today, 9),
            )
            app_module.db.session.add(b)
            app_module.db.session.commit()
            return b.id

    def pay(self, booking_id, amount, status="succeeded"):
        with app_module.app.app_context():
            app_module.db.session.add(app_module.Payment(
                booking_id=booking_id, amount=Decimal(amount),
                status=status, test=True,
                stripe_test_id=f"pi_test_profit_{booking_id}_{status}"))
            app_module.db.session.commit()

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def profit(self, period=None, page=None):
        qs = {}
        if period:
            qs["period"] = period
        if page:
            qs["page"] = page
        return self.client.get("/api/owner/profit", query_string=qs)

    # -- auth ---------------------------------------------------------------
    def test_profit_requires_pin(self):
        resp = self.profit()
        self.assertEqual(resp.status_code, 401)

    def test_profit_serves_after_login(self):
        self.owner_login()
        resp = self.profit()
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        data = resp.get_json()
        self.assertEqual(data["period"], "tilldate")
        self.assertEqual(data["periods"]["tilldate"]["rides"], 0)
        self.assertEqual(data["periods"]["tilldate"]["profit"], 0.0)

    # -- eligibility: only completed + paid rides count ---------------------
    def test_only_completed_paid_rides_count(self):
        # Counts: completed + succeeded payment.
        good = self.make_booking(completed_day=self.today)
        self.pay(good, "200.00")
        # Completed + captured payment (live Stripe) also counts.
        captured = self.make_booking(completed_day=self.today, customer="Captured Customer")
        self.pay(captured, "200.00", status="captured")
        # Offered ride with a succeeded payment: not completed, no profit.
        offered = self.make_booking(status="offered", completed_day=None)
        self.pay(offered, "200.00")
        # Completed ride with only an AUTHORIZED hold: money not taken yet.
        held = self.make_booking(completed_day=self.today, customer="Held Customer")
        self.pay(held, "200.00", status="authorized")
        # Completed ride with no payment at all.
        self.make_booking(completed_day=self.today, customer="Unpaid Customer")
        # Completed + paid, then REFUNDED: pays nothing.
        refunded = self.make_booking(completed_day=self.today, customer="Refunded Customer")
        self.pay(refunded, "200.00")
        self.pay(refunded, "200.00", status="refunded")
        # Cancelled ride, paid in full and kept: still not a completed ride.
        cancelled = self.make_booking(status="cancelled", completed_day=None)
        self.pay(cancelled, "200.00")

        self.owner_login()
        data = self.profit().get_json()
        till = data["periods"]["tilldate"]
        # Exactly the two paid + completed rides.
        self.assertEqual(till["rides"], 2)
        self.assertAlmostEqual(till["customer_paid"], 400.00)
        self.assertAlmostEqual(till["driver_pay"], 204.92)
        self.assertAlmostEqual(till["profit"], 195.08)
        ids = {r["id"] for r in data["rides"]}
        self.assertEqual(ids, {good, captured})

    def test_per_ride_profit_math(self):
        bid = self.make_booking(completed_day=self.today,
                                fare="200.00", driver_pay="102.46")
        self.pay(bid, "200.00")
        self.owner_login()
        rows = self.profit().get_json()["rides"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["id"], bid)
        self.assertAlmostEqual(row["customer_paid"], 200.00)
        self.assertAlmostEqual(row["driver_earnings"], 102.46)
        self.assertAlmostEqual(row["profit"], 97.54)
        self.assertEqual(row["status"], "completed")

    def test_toll_never_counts_as_profit(self):
        # JFK->Times Square with a $16.79 toll: the toll is inside BOTH
        # the customer total and the driver earnings, so profit must
        # be exactly the no-toll profit.
        bid = self.make_booking(completed_day=self.today,
                                fare="217.61", driver_pay="119.25",
                                toll="16.79")
        self.pay(bid, "217.61")
        self.owner_login()
        row = self.profit().get_json()["rides"][0]
        self.assertAlmostEqual(row["customer_paid"], 217.61)
        self.assertAlmostEqual(row["driver_earnings"], 119.25)
        self.assertAlmostEqual(row["profit"], 98.36)

    def test_waiting_charge_counts_as_profit(self):
        bid = self.make_booking(completed_day=self.today,
                                fare="200.00", driver_pay="102.46",
                                waiting="12.00")
        self.pay(bid, "200.00")
        self.owner_login()
        row = self.profit().get_json()["rides"][0]
        self.assertAlmostEqual(row["customer_paid"], 212.00)
        self.assertAlmostEqual(row["profit"], 109.54)

    # -- periods: daily / weekly / monthly / till-date ----------------------
    def test_period_buckets(self):
        # Four rides on four completion days (today, this week's Monday,
        # the day before this week, and the last day of last month —
        # some may coincide depending on the day of the week/month).
        # Expected counts are computed from the same dates, so the test
        # holds on any day it runs.
        today = self.today
        week = app_module.week_for(today)
        days = [
            today,
            week["start"],
            week["start"] - timedelta(days=1),
            date(today.year, today.month, 1) - timedelta(days=1),
        ]
        fares = ["200.00", "300.00", "400.00", "500.00"]
        made = []
        for day, fare in zip(days, fares):
            bid = self.make_booking(completed_day=day, fare=fare,
                                    driver_pay="100.00")
            self.pay(bid, fare)
            made.append((day, Decimal(fare) - Decimal("100.00")))

        self.owner_login()
        data = self.profit().get_json()
        periods = data["periods"]

        def expected(pred):
            sel = [p for d, p in made if pred(d)]
            return len(sel), float(sum(sel, Decimal("0.00")))

        n, profit = expected(lambda d: d == today)
        self.assertEqual(periods["daily"]["rides"], n)
        self.assertAlmostEqual(periods["daily"]["profit"], profit)
        n, profit = expected(lambda d: week["start"] <= d <= week["end"])
        self.assertEqual(periods["weekly"]["rides"], n)
        self.assertAlmostEqual(periods["weekly"]["profit"], profit)
        n, profit = expected(
            lambda d: d.year == today.year and d.month == today.month)
        self.assertEqual(periods["monthly"]["rides"], n)
        self.assertAlmostEqual(periods["monthly"]["profit"], profit)
        n, profit = expected(lambda d: True)
        self.assertEqual(periods["tilldate"]["rides"], n)
        self.assertAlmostEqual(periods["tilldate"]["profit"], profit)
        self.assertEqual(data["week_start"], week["start"].isoformat())
        self.assertEqual(data["week_end"], week["end"].isoformat())
        self.assertEqual(data["month_label"], today.strftime("%B %Y"))

    def test_period_param_filters_rides(self):
        b_today = self.make_booking(completed_day=self.today)
        self.pay(b_today, "200.00")
        yesterday = self.today - timedelta(days=1)
        b_old = self.make_booking(completed_day=yesterday)
        self.pay(b_old, "200.00")

        self.owner_login()
        daily = self.profit(period="daily").get_json()
        self.assertEqual(daily["period"], "daily")
        self.assertEqual(daily["total_rides"], 1)
        self.assertEqual({r["id"] for r in daily["rides"]}, {b_today})
        till = self.profit(period="tilldate").get_json()
        self.assertEqual(till["total_rides"], 2)
        # Unknown period falls back to till-date.
        unknown = self.profit(period="bogus").get_json()
        self.assertEqual(unknown["period"], "tilldate")
        self.assertEqual(unknown["total_rides"], 2)

    # -- pagination ---------------------------------------------------------
    def test_profit_rides_paginate_ten_per_page(self):
        ids = []
        for _ in range(12):
            bid = self.make_booking(completed_day=self.today)
            self.pay(bid, "200.00")
            ids.append(bid)
        self.owner_login()
        page1 = self.profit(page=1).get_json()
        self.assertEqual(len(page1["rides"]), 10)
        self.assertEqual(page1["total_rides"], 12)
        self.assertEqual(page1["pages"], 2)
        page2 = self.profit(page=2).get_json()
        self.assertEqual(len(page2["rides"]), 2)
        self.assertEqual({r["id"] for r in page1["rides"]} |
                         {r["id"] for r in page2["rides"]}, set(ids))

    # -- the tab itself ------------------------------------------------------
    def test_profit_tab_present_and_dashboard_untouched(self):
        html = read("static/owner.html")
        self.assertIn('data-tab="profit"', html)
        self.assertIn('id="tab-profit"', html)
        for sub in ("daily", "weekly", "monthly", "tilldate"):
            self.assertIn('data-profit-period="%s"' % sub, html)
        for element_id in ("profit-total", "profit-paid", "profit-driver",
                           "profit-rides", "profit-body", "profit-pager"):
            self.assertIn('id="%s"' % element_id, html)
        # "Today at a glance" on the Dashboard tab is untouched.
        self.assertIn("Today at a glance", html)
        self.assertIn('id="sum-gross"', html)
        self.assertIn('id="sum-profit"', html)

    def test_owner_js_loads_profit_tab(self):
        js = read("static/js/owner.js")
        self.assertIn('"profit"', js)
        self.assertIn("/api/owner/profit", js)
        self.assertIn("loadProfit", js)
        self.assertIn("data-profit-period", js)


if __name__ == "__main__":
    unittest.main()
