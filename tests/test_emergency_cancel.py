"""Tests for the AI-judged emergency driver cancel (owner decision
2026-11-18, voice call — SUPERSEDES the 2026-11-17 deferral of the
emergency flow and the lock that blocked every cancel inside 2h).

- Inside 2 hours (including past pickups) the driver CAN cancel but
  MUST give a reason; the reason is judged automatically, server-side
  and rule-based (no external AI call). A fault judgment blocks the
  driver's app for 48 hours; a genuine emergency never blocks.
- In EVERY case the job auto re-dispatches immediately and the
  customer sees nothing about the cancel or re-dispatch.
- More than 2 hours out, cancelling is unchanged: no reason, no
  judgment, no suspension. Declining offers and the customer
  1-hour cancel rule are untouched (covered by the cancel-lock
  and pricing tests).
- Every emergency cancel is visible read-only in the owner
  dashboard detail (reason, judgment, suspension or not).

Run:  python -m unittest discover -s tests -v
"""

import io
import json
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-emergency-cancel-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "emergency-cancel-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Emergency Cancel Customer"}


def _ny_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.now(timezone.utc)


class EmergencyCancelCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self):
        self._driver_seq += 1
        phone = f"+1555005{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Emergency Driver {self._driver_seq}", "phone": phone,
            "email": f"ed{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"E{self._driver_seq:05d}",
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

    def signin(self, email, phone):
        """Compulsory customer sign-in (owner 2026-11-22): payment
        needs a sign-in with the booking's email. Signs in
        once per email per test — the session persists for later
        bookings and payments in the same test."""
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Emergency Cancel Customer",
            "phone": f"+1555006{self._phone_seq:04d}",
            "email": "emergencycancel@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        if "@" in (payload.get("email") or "") and payload.get("phone"):
            self.signin(payload["email"], payload["phone"])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def accept(self, token, booking_id):
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def trip_event(self, token, booking_id, event, **extra):
        payload = {"event": event}
        payload.update(extra)
        return self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                json=payload,
                                headers={"X-Driver-Token": token})

    def owner_detail(self, booking_id):
        self.client.post("/api/owner/login", json={"pin": "9999"})
        return self.client.get(f"/api/owner/bookings/{booking_id}").get_json()

    def pickup_offset(self, minutes):
        """(date, time) strings for a pickup `minutes` from now (NY)."""
        when = _ny_now() + timedelta(minutes=minutes)
        return when.strftime("%Y-%m-%d"), when.strftime("%H:%M")

    def move_pickup(self, booking_id, minutes):
        """Move a booking's pickup to `minutes` from now, in the DB.
        The API refuses past pickups (owner decision 2026-11-20), so
        tests that need a past pickup book in the future and move it
        back here."""
        date, time = self.pickup_offset(minutes)
        with app_module.app.app_context():
            b = app_module.db.session.get(app_module.Booking, booking_id)
            b.date = date
            b.time = time
            app_module.db.session.commit()

    def accepted_booking(self, minutes_out):
        """A driver + an accepted booking `minutes_out` from now."""
        driver, token = self.register_driver()
        date, time = self.pickup_offset(minutes_out)
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token, booking["id"])
        return booking, driver, token

    def emergency_rows(self, booking_id):
        with app_module.app.app_context():
            return [dict(reason=c.reason, judgment=c.judgment,
                         flagged=c.flagged,
                         suspended_until=c.suspended_until)
                    for c in app_module.EmergencyCancel.query.filter_by(
                        booking_id=booking_id).order_by(
                            app_module.EmergencyCancel.id).all()]

    # -- fault judgment -> 48h suspension ----------------------------------
    def test_fault_reason_inside_two_hours_suspends_48h(self):
        _, token1 = self.register_driver()
        _, token2 = self.register_driver()
        date, time = self.pickup_offset(60)
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token1, booking["id"])
        resp = self.trip_event(token1, booking["id"], "cancel",
                               reason="other_job")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.assertEqual(body["booking"]["status"], "offered")
        self.assertEqual(body["emergency_cancel"]["judgment"], "fault")
        # Suspension ends ~48 hours from now.
        end = datetime.fromisoformat(
            body["emergency_cancel"]["suspended_until"].replace("Z", "+00:00"))
        delta = end - datetime.now(timezone.utc)
        self.assertTrue(timedelta(hours=47) < delta <= timedelta(hours=48, minutes=5),
                        str(delta))
        # The job re-dispatched to the other driver, not back to the
        # driver who cancelled.
        offers2 = self.client.get("/api/drivers/me/offers",
                                  headers={"X-Driver-Token": token2}).get_json()
        self.assertIn(booking["id"], [o["booking_id"] for o in offers2])
        # Suspended driver: no offers at all.
        offers1 = self.client.get("/api/drivers/me/offers",
                                  headers={"X-Driver-Token": token1}).get_json()
        self.assertEqual(offers1, [])
        # Suspended driver: cannot go available, cannot accept.
        resp = self.client.post("/api/drivers/me/availability",
                                json={"available": True},
                                headers={"X-Driver-Token": token1})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("paused", resp.get_json()["error"])
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                                headers={"X-Driver-Token": token1})
        self.assertEqual(resp.status_code, 409)
        # Going offline is still allowed.
        resp = self.client.post("/api/drivers/me/availability",
                                json={"available": False},
                                headers={"X-Driver-Token": token1})
        self.assertEqual(resp.status_code, 200)
        # Record stored with the fault judgment.
        rows = self.emergency_rows(booking["id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reason"], "other_job")
        self.assertEqual(rows[0]["judgment"], "fault")
        self.assertFalse(rows[0]["flagged"])
        self.assertIsNotNone(rows[0]["suspended_until"])

    def test_past_pickup_fault_suspends(self):
        booking, _d, token = self.accepted_booking(30)
        self.move_pickup(booking["id"], -30)  # pickup 30 min ago
        resp = self.trip_event(token, booking["id"], "cancel",
                               reason="dont_want")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["emergency_cancel"]["judgment"], "fault")
        self.assertIsNotNone(resp.get_json()["emergency_cancel"]["suspended_until"])

    def test_en_route_emergency_cancel_genuine(self):
        booking, _d, token = self.accepted_booking(30)
        self.assertEqual(self.trip_event(token, booking["id"], "en_route").status_code, 200)
        resp = self.trip_event(token, booking["id"], "cancel", reason="medical")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["booking"]["status"], "offered")
        self.assertEqual(resp.get_json()["emergency_cancel"]["judgment"], "genuine")
        self.assertIsNone(resp.get_json()["emergency_cancel"]["suspended_until"])

    # -- genuine judgment -> no suspension ---------------------------------
    def test_genuine_reason_no_suspension(self):
        booking, _d, token = self.accepted_booking(60)
        resp = self.trip_event(token, booking["id"], "cancel", reason="breakdown")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["emergency_cancel"]["judgment"], "genuine")
        # A different offered job still reaches the driver, and he can
        # still go available: no suspension.
        other = self.book(date="2030-06-02", time="12:00")
        self.assertEqual(self.pay(other["id"]).status_code, 200)
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertIn(other["id"], [o["booking_id"] for o in offers])
        resp = self.client.post("/api/drivers/me/availability",
                                json={"available": True},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        rows = self.emergency_rows(booking["id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["judgment"], "genuine")
        self.assertIsNone(rows[0]["suspended_until"])

    # -- reason required ----------------------------------------------------
    def test_missing_reason_rejected_booking_unchanged(self):
        booking, _d, token = self.accepted_booking(60)
        resp = self.trip_event(token, booking["id"], "cancel")
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn("2 hours", resp.get_json()["error"])
        self.assertIn("reason", resp.get_json()["error"].lower())
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["status"], "accepted")
        self.assertEqual(self.emergency_rows(booking["id"]), [])

    def test_invalid_reason_rejected(self):
        booking, _d, token = self.accepted_booking(60)
        resp = self.trip_event(token, booking["id"], "cancel", reason="bogus")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self.owner_detail(booking["id"])["status"], "accepted")
        self.assertEqual(self.emergency_rows(booking["id"]), [])

    def test_other_requires_detail(self):
        booking, _d, token = self.accepted_booking(60)
        resp = self.trip_event(token, booking["id"], "cancel", reason="other")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self.owner_detail(booking["id"])["status"], "accepted")
        resp = self.trip_event(token, booking["id"], "cancel",
                               reason="other", detail="  ")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self.emergency_rows(booking["id"]), [])

    # -- "Other" free-text judgment ----------------------------------------
    def test_other_emergency_keywords_genuine(self):
        booking, _d, token = self.accepted_booking(60)
        resp = self.trip_event(token, booking["id"], "cancel",
                               reason="other",
                               detail="My car broke down on the highway")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["emergency_cancel"]["judgment"], "genuine")
        self.assertIsNone(resp.get_json()["emergency_cancel"]["suspended_until"])

    def test_other_fault_keywords_suspend(self):
        booking, _d, token = self.accepted_booking(60)
        resp = self.trip_event(token, booking["id"], "cancel",
                               reason="other",
                               detail="I got another job that pays better")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["emergency_cancel"]["judgment"], "fault")
        self.assertIsNotNone(resp.get_json()["emergency_cancel"]["suspended_until"])

    def test_other_neutral_defaults_genuine_and_flagged(self):
        booking, _d, token = self.accepted_booking(60)
        resp = self.trip_event(token, booking["id"], "cancel",
                               reason="other",
                               detail="Something unexpected came up at home")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["emergency_cancel"]["judgment"], "genuine")
        self.assertTrue(body["emergency_cancel"]["flagged"])
        self.assertIsNone(body["emergency_cancel"]["suspended_until"])
        rows = self.emergency_rows(booking["id"])
        self.assertTrue(rows[0]["flagged"])

    # -- untouched behaviour -------------------------------------------------
    def test_outside_two_hours_unchanged_no_reason_no_suspension(self):
        _, token = self.register_driver()
        booking = self.book()  # 2030 pickup: far more than 2 hours away
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token, booking["id"])
        resp = self.trip_event(token, booking["id"], "cancel")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["booking"]["status"], "offered")
        self.assertNotIn("emergency_cancel", resp.get_json())
        self.assertEqual(self.emergency_rows(booking["id"]), [])
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": token}).get_json()
        self.assertIsNone(me["driver"]["suspended_until"])

    def test_customer_sees_nothing_about_cancel_or_redispatch(self):
        booking, _d, token = self.accepted_booking(60)
        self.assertEqual(
            self.trip_event(token, booking["id"], "cancel",
                            reason="other_job").status_code, 200)
        view = self.client.get(f"/api/bookings/{booking['id']}").get_json()["booking"]
        self.assertEqual(view["status"], "offered")
        self.assertIsNone(view["driver"])
        blob = json.dumps(view).lower()
        for word in ("emergency", "suspend", "judgment", "reason", "cancel"):
            self.assertNotIn(word, blob)

    # -- owner visibility ------------------------------------------------------
    def test_owner_detail_shows_judgment_record(self):
        booking, driver1, token1 = self.accepted_booking(60)
        self.assertEqual(
            self.trip_event(token1, booking["id"], "cancel",
                            reason="running_late",
                            detail="Overslept, sorry").status_code, 200)
        detail = self.owner_detail(booking["id"])
        records = detail["emergency_cancels"]
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["driver_name"], driver1["name"])
        self.assertEqual(rec["reason"], "running_late")
        self.assertEqual(rec["reason_label"], "Running late / overslept")
        self.assertEqual(rec["detail"], "Overslept, sorry")
        self.assertEqual(rec["judgment"], "fault")
        self.assertFalse(rec["flagged"])
        self.assertIsNotNone(rec["suspended_until"])
        self.assertIsNotNone(rec["created_at"])
        # The timeline event is there too.
        types = [e["type"] for e in detail["events"]]
        self.assertIn("emergency_cancel", types)

    # -- suspension lifecycle ---------------------------------------------------
    def test_suspension_notice_on_signin_and_me(self):
        driver, token = self.register_driver()
        date, time = self.pickup_offset(60)
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token, booking["id"])
        self.assertEqual(
            self.trip_event(token, booking["id"], "cancel",
                            reason="dont_want").status_code, 200)
        # Sign-in still works and carries the notice.
        resp = self.client.post("/api/drivers/me/lookup",
                                json={"phone": driver["phone"]})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.get_json()["driver"]["suspended_until"])
        new_token = resp.get_json()["token"]
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": new_token}).get_json()
        self.assertIsNotNone(me["driver"]["suspended_until"])
        self.assertFalse(me["driver"]["available"])

    def test_suspension_auto_lifts_after_expiry(self):
        driver, token = self.register_driver()
        date, time = self.pickup_offset(60)
        booking = self.book(date=date, time=time)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.accept(token, booking["id"])
        self.assertEqual(
            self.trip_event(token, booking["id"], "cancel",
                            reason="other_job").status_code, 200)
        self.assertEqual(self.client.get(
            "/api/drivers/me/offers",
            headers={"X-Driver-Token": token}).get_json(), [])
        # Move the suspension end into the past: offers resume and
        # going available works again, with no manual step.
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Driver, driver["id"])
            row.suspended_until = datetime.now(timezone.utc) - timedelta(hours=1)
            app_module.db.session.commit()
        other = self.book(date="2030-06-02", time="12:00")
        self.assertEqual(self.pay(other["id"]).status_code, 200)
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertIn(other["id"], [o["booking_id"] for o in offers])
        resp = self.client.post("/api/drivers/me/availability",
                                json={"available": True},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)

    # -- judge rules (pure function) --------------------------------------------
    def test_judge_fixed_reasons(self):
        judge = app_module.judge_emergency_cancel
        for reason in ("breakdown", "medical", "family"):
            self.assertEqual(judge(reason, ""), ("genuine", False))
        for reason in ("other_job", "dont_want", "running_late"):
            self.assertEqual(judge(reason, ""), ("fault", False))

    def test_judge_emergency_signals_win_over_fault(self):
        # Benefit of the doubt: an emergency signal anywhere in the
        # text beats a fault signal.
        judgment, flagged = app_module.judge_emergency_cancel(
            "other", "I was running late because of a hospital emergency")
        self.assertEqual((judgment, flagged), ("genuine", False))

    def test_judge_neutral_other_defaults_genuine_flagged(self):
        self.assertEqual(
            app_module.judge_emergency_cancel("other", "unforeseen things"),
            ("genuine", True))
        self.assertEqual(app_module.SUSPENSION_HOURS, 48)

    # -- driver page / JS consistency ----------------------------------------------
    def test_reason_list_matches_driver_page(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "static", "driver.html")) as f:
            html = f.read()
        with open(os.path.join(root, "static", "js", "driver.js")) as f:
            js = f.read()
        for key, label, _judgment in app_module.EMERGENCY_CANCEL_REASONS:
            self.assertIn(f'value="{key}"', html)
            self.assertIn(label, html)
        self.assertIn("trip-cancel-reason-panel", html)
        self.assertIn("Why are you cancelling?", html)
        self.assertIn("suspension-banner", html)
        self.assertNotIn("trip-cancel-locked-note", html)
        self.assertIn("function refreshCancelButton()", js)
        self.assertIn("pickup.getTime() - Date.now() <= 2 * 60 * 60000", js)
        self.assertIn("trip-cancel-reason-panel", js)
        self.assertIn("cancel-reason-confirm", js)
        self.assertIn("suspension-banner", js)
        self.assertNotIn("trip-cancel-locked-note", js)


if __name__ == "__main__":
    unittest.main()
