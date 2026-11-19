"""Tests for the daily owner summary email (owner decision 2026-11-19,
"rozana summary bhej do"): every morning at 09:00 America/New_York
the owner gets one short email covering the previous day
(midnight-midnight NY time) — rides completed, gross collected,
profit, driver owed, new driver registrations, documents expiring
soon, emergency cancels, and active/upcoming rides.

Numbers come straight from the production database, never from
Gmail. Trigger is POST /api/cron/daily-summary with
Authorization: Bearer <DAILY_SUMMARY_CRON_SECRET> (or the owner
session); {"dry_run": true} returns the summary JSON and sends NO
email.

Run:  python -m unittest discover -s tests -v
"""

import os
import secrets
import sys
import tempfile
import unittest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from unittest import mock
from zoneinfo import ZoneInfo

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-daily-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "daily-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

NY = ZoneInfo("America/New_York")
SECRET = "daily-test-secret"
OWNER_TO = "m.azherahmed1@gmail.com"


def ny_dt(day, hour=12, minute=0):
    """Aware UTC datetime for a New York wall time on `day`."""
    return datetime.combine(day, time(hour, minute), tzinfo=NY).astimezone(timezone.utc)


class DailySummaryCase(unittest.TestCase):
    def setUp(self):
        os.environ["DAILY_SUMMARY_CRON_SECRET"] = SECRET
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._seq = 0
        self.today = app_module._today_ny()
        self.yesterday = self.today - timedelta(days=1)

    def tearDown(self):
        os.environ.pop("DAILY_SUMMARY_CRON_SECRET", None)

    # -- seed helpers ------------------------------------------------------
    def make_driver(self, name, created_day=None):
        self._seq += 1
        with app_module.app.app_context():
            d = app_module.Driver(
                name=name, phone=f"+1555010{self._seq:04d}",
                email=f"d{self._seq}@test.com",
                car_model="Cadillac CT6", car_colour="Black",
                plate=f"D{self._seq:05d}",
                token=secrets.token_hex(16),
                created_at=ny_dt(created_day or self.yesterday, 10),
            )
            app_module.db.session.add(d)
            app_module.db.session.commit()
            return d.id

    def make_booking(self, status="completed", completed_day=None,
                     fare="100.00", driver_pay="40.00", waiting="0.00",
                     payout_paid=False, customer="Daily Customer"):
        self._seq += 1
        with app_module.app.app_context():
            b = app_module.Booking(
                customer_name=customer, phone=f"+1555020{self._seq:04d}",
                email="daily@test.com", pickup="JFK Airport",
                dropoff="Times Square, New York",
                date=(completed_day or self.yesterday).isoformat(),
                time="12:00", ride_type="one_way", status=status,
                fare_total=Decimal(fare), driver_earnings=Decimal(driver_pay),
                waiting_charge=Decimal(waiting), payout_paid=payout_paid,
                completed_at=(ny_dt(completed_day, 15)
                              if completed_day and status == "completed" else None),
                created_at=ny_dt(completed_day or self.yesterday, 9),
            )
            app_module.db.session.add(b)
            app_module.db.session.commit()
            return b.id

    def pay(self, booking_id, amount, status="succeeded"):
        with app_module.app.app_context():
            app_module.db.session.add(app_module.Payment(
                booking_id=booking_id, amount=Decimal(amount),
                status=status, test=True,
                stripe_test_id=f"pi_test_daily_{booking_id}"))
            app_module.db.session.commit()

    def make_cancel(self, booking_id, created_day, driver_name="Daily Driver"):
        with app_module.app.app_context():
            app_module.db.session.add(app_module.EmergencyCancel(
                booking_id=booking_id, driver_name=driver_name,
                reason="car_breakdown",
                reason_label="Car breakdown or accident",
                judgment="genuine", flagged=False,
                created_at=ny_dt(created_day, 11)))
            app_module.db.session.commit()

    def make_doc(self, driver_id, expires_on, doc_type="dmv_license"):
        with app_module.app.app_context():
            app_module.db.session.add(app_module.DriverDocument(
                driver_id=driver_id, doc_type=doc_type,
                file=b"fake-bytes", mime="image/jpeg",
                original_name="dmv.jpg", expires_on=expires_on))
            app_module.db.session.commit()

    def summary(self, day=None):
        with app_module.app.app_context():
            return app_module.compute_daily_summary(day)

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def call_endpoint(self, headers=None, json_body=None, query=None):
        return self.client.post("/api/cron/daily-summary",
                                json=json_body or {},
                                query_string=query or {},
                                headers=headers or {})

    def bearer(self):
        return {"Authorization": "Bearer " + SECRET}

    # -- computation --------------------------------------------------------
    def test_yesterday_totals_only(self):
        # Two completed yesterday, both paid: gross 162 + 210 = 372,
        # driver share 72 + 90 = 162, profit 210, owed 162.
        a = self.make_booking(fare="162.00", driver_pay="72.00",
                              completed_day=self.yesterday)
        self.pay(a, "162.00")
        b = self.make_booking(fare="200.00", driver_pay="90.00",
                              waiting="10.00", completed_day=self.yesterday)
        self.pay(b, "210.00")
        # Completed two days ago: excluded. Completed today: excluded.
        old = self.make_booking(fare="500.00", driver_pay="200.00",
                                completed_day=self.yesterday - timedelta(days=1))
        self.pay(old, "500.00")
        self.make_booking(fare="300.00", driver_pay="120.00",
                          completed_day=self.today)
        # Offered (not completed): excluded.
        self.make_booking(status="offered", completed_day=None)
        s = self.summary()
        self.assertEqual(s["date"], self.yesterday.isoformat())
        self.assertEqual(s["rides_completed"], 2)
        self.assertEqual(s["gross"], 372.00)
        self.assertEqual(s["profit"], 210.00)
        self.assertEqual(s["driver_owed_yesterday"], 162.00)
        self.assertEqual(s["driver_owed_total"], 162.00 + 200.00 + 120.00)

    def test_refunded_ride_counts_but_pays_nothing(self):
        a = self.make_booking(fare="162.00", driver_pay="72.00",
                              completed_day=self.yesterday)
        self.pay(a, "162.00", status="refunded")
        s = self.summary()
        self.assertEqual(s["rides_completed"], 1)
        self.assertEqual(s["gross"], 0.00)
        self.assertEqual(s["profit"], 0.00)
        self.assertEqual(s["driver_owed_yesterday"], 0.00)

    def test_unpaid_ride_counts_gross_zero_but_driver_owed(self):
        # Completed + paid on paper but no Payment row (e.g. pay
        # recorded elsewhere): no gross, driver share still owed.
        self.make_booking(fare="162.00", driver_pay="72.00",
                          completed_day=self.yesterday)
        s = self.summary()
        self.assertEqual(s["rides_completed"], 1)
        self.assertEqual(s["gross"], 0.00)
        self.assertEqual(s["driver_owed_yesterday"], 72.00)

    def test_payout_paid_ride_not_owed(self):
        a = self.make_booking(fare="100.00", driver_pay="40.00",
                              payout_paid=True, completed_day=self.yesterday)
        self.pay(a, "100.00")
        s = self.summary()
        self.assertEqual(s["gross"], 100.00)
        self.assertEqual(s["profit"], 60.00)
        self.assertEqual(s["driver_owed_yesterday"], 0.00)
        self.assertEqual(s["driver_owed_total"], 0.00)

    def test_new_drivers_and_cancels(self):
        self.make_driver("Yesterday Driver", self.yesterday)
        self.make_driver("Old Driver", self.yesterday - timedelta(days=3))
        b = self.make_booking(completed_day=self.yesterday)
        self.make_cancel(b, self.yesterday)
        self.make_cancel(b, self.yesterday - timedelta(days=2))
        s = self.summary()
        self.assertEqual(s["new_drivers_count"], 1)
        self.assertEqual(s["new_drivers"][0]["name"], "Yesterday Driver")
        self.assertEqual(s["emergency_cancels_count"], 1)
        self.assertEqual(s["emergency_cancels"][0]["judgment"], "genuine")

    def test_documents_expiring_soon(self):
        d = self.make_driver("Doc Driver", self.yesterday)
        self.make_doc(d, self.today + timedelta(days=5))
        self.make_doc(d, self.today + timedelta(days=30),
                      doc_type="tlc_license")  # too far: out
        s = self.summary()
        self.assertEqual(len(s["documents_expiring_soon"]), 1)
        self.assertEqual(s["documents_expiring_soon"][0]["days_left"], 5)
        self.make_doc(d, self.today - timedelta(days=1),
                      doc_type="fh1_insurance")  # expired: in
        s = self.summary()
        self.assertEqual(len(s["documents_expiring_soon"]), 2)

    def test_active_rides(self):
        self.make_booking(status="offered", completed_day=None)
        self.make_booking(status="accepted", completed_day=None)
        self.make_booking(status="completed", completed_day=self.yesterday)
        self.make_booking(status="cancelled", completed_day=None)
        s = self.summary()
        self.assertEqual(s["active_rides_count"], 2)
        self.assertEqual({r["status"] for r in s["active_rides"]},
                         {"offered", "accepted"})

    def test_explicit_day_argument(self):
        day = self.yesterday - timedelta(days=1)
        self.make_booking(fare="50.00", driver_pay="20.00",
                          completed_day=day)
        s = self.summary(day)
        self.assertEqual(s["rides_completed"], 1)
        self.assertEqual(self.summary()["rides_completed"], 0)

    # -- email format --------------------------------------------------------
    def test_email_format_has_the_numbers(self):
        a = self.make_booking(fare="162.00", driver_pay="72.00",
                              completed_day=self.yesterday)
        self.pay(a, "162.00")
        self.make_driver("Mail Driver", self.yesterday)
        subject, body = app_module.format_daily_summary_email(self.summary())
        self.assertIn("daily summary", subject)
        self.assertIn(self.yesterday.strftime("%b %d, %Y"), subject)
        self.assertIn("Rides completed: 1", body)
        self.assertIn("Gross collected: $162.00", body)
        self.assertIn("Profit: $90.00", body)
        self.assertIn("Driver owed (kal ki rides): $72.00", body)
        self.assertIn("Mail Driver", body)
        self.assertIn("Emergency cancels: 0", body)

    # -- endpoint auth + dry run ---------------------------------------------
    def test_endpoint_requires_auth(self):
        resp = self.call_endpoint(json_body={"dry_run": True})
        self.assertEqual(resp.status_code, 401)
        resp = self.call_endpoint(
            headers={"Authorization": "Bearer wrong-secret"},
            json_body={"dry_run": True})
        self.assertEqual(resp.status_code, 401)

    def test_owner_session_can_dry_run(self):
        self.owner_login()
        resp = self.call_endpoint(json_body={"dry_run": True})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["dry_run"])

    def test_dry_run_sends_nothing(self):
        self.make_booking(completed_day=self.yesterday)
        with mock.patch.object(app_module, "send_email") as send:
            resp = self.call_endpoint(headers=self.bearer(),
                                      json_body={"dry_run": True})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertTrue(body["dry_run"])
        self.assertFalse(body["sent"])
        self.assertEqual(body["summary"]["rides_completed"], 1)
        send.assert_not_called()

    def test_dry_run_via_query_param(self):
        with mock.patch.object(app_module, "send_email") as send:
            resp = self.call_endpoint(headers=self.bearer(),
                                      query={"dry_run": "1"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["dry_run"])
        send.assert_not_called()

    def test_real_run_sends_email_to_owner(self):
        self.make_booking(completed_day=self.yesterday)
        with mock.patch.object(app_module, "send_email",
                               return_value=app_module.EMAIL_SENT) as send:
            resp = self.call_endpoint(headers=self.bearer(), json_body={})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertTrue(body["sent"])
        self.assertEqual(body["email_status"], app_module.EMAIL_SENT)
        send.assert_called_once()
        args = send.call_args.args
        self.assertEqual(args[0], OWNER_TO)
        self.assertIn("daily summary", args[1])
        self.assertIn("Rides completed: 1", args[2])

    def test_bad_date_rejected(self):
        resp = self.call_endpoint(headers=self.bearer(),
                                  json_body={"date": "not-a-date"})
        self.assertEqual(resp.status_code, 400)

    def test_date_override_summarises_that_day(self):
        day = self.yesterday - timedelta(days=1)
        self.make_booking(completed_day=day)
        with mock.patch.object(app_module, "send_email"):
            resp = self.call_endpoint(
                headers=self.bearer(),
                json_body={"dry_run": True, "date": day.isoformat()})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["summary"]["rides_completed"], 1)


if __name__ == "__main__":
    unittest.main()
