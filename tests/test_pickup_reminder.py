"""Tests for the 1-hour pickup reminder (owner decision 2026-11-18,
voice call): 1 hour before pickup, remind the ASSIGNED driver that his
ride is about to start — in-app notification, email, and SMS to his
phone number.

HONEST LIMIT: no messaging service is connected. The email and SMS
are written to the owner-dashboard outbox only and are NOT actually
sent (the dashboard shows each row as Queued until an email is
confirmed delivered). Only the in-app banner actually reaches the
driver, and only while he has the app open. These tests pin the
pipeline (check + idempotent record + outbox entries + in-app
payload) and the content rule — never miles, fare, or total.

Rules pinned here:
- Fires once per acceptance (pickup_reminder_sent_at flag); repeated
  runs add nothing. The flag resets when the booking goes back to
  "offered" (driver cancel) or a new driver accepts, so the next
  driver gets his own reminder.
- Fires only when pickup is within the next hour (and not past).
- Fires only for status "accepted" with an assigned driver: never for
  "offered", never once the trip has started (en_route+), never when
  cancelled/completed/no-show.
- Content: pickup time + addresses only. The driver-facing payload
  carries no money or distance field at all.
- Scheduling without new infrastructure: the check runs from the
  driver app's pickup-reminder poll, the active-trip fetch, and the
  owner dashboard trigger; a bearer-secret cron endpoint exists for
  fully automatic firing later (documented, unset by default).

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-reminder-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "reminder.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "reminder-secret-key"
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
        "card_cvc": "123", "card_name": "Reminder Customer"}
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def _ny_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.now(timezone.utc)


class PickupReminderCase(unittest.TestCase):
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
            "name": f"Reminder Driver {self._driver_seq}", "phone": phone,
            "email": f"rd{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"R{self._driver_seq:05d}",
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
        return body["driver"], body["token"]

    def book(self, **extra):
        self._phone_seq += 1
        self._last_customer_phone = f"+1555006{self._phone_seq:04d}"
        payload = {
            "customer_name": "Reminder Customer",
            "phone": self._last_customer_phone,
            "email": "reminder@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        resp = self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def accept(self, token, booking_id):
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def trip_event(self, token, booking_id, event):
        return self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                json={"event": event},
                                headers={"X-Driver-Token": token})

    def pickup_offset(self, minutes):
        """(date, time) strings for a pickup `minutes` from now (NY)."""
        when = _ny_now() + timedelta(minutes=minutes)
        return when.strftime("%Y-%m-%d"), when.strftime("%H:%M")

    def accepted_booking(self, minutes, **extra):
        """A paid + accepted booking with pickup `minutes` from now.
        Returns (booking, driver, token)."""
        date, time = self.pickup_offset(minutes)
        booking = self.book(date=date, time=time, **extra)
        self.pay(booking["id"])
        driver, token = self.register_driver()
        self.accept(token, booking["id"])
        return booking, driver, token

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def run_reminders_as_owner(self):
        self.owner_login()
        return self.client.post("/api/owner/run-pickup-reminders", json={})

    def outbox_for(self, booking_id):
        with app_module.app.app_context():
            return [(m.channel, m.recipient, m.body)
                    for m in app_module.OutboxMessage.query
                    .filter_by(booking_id=booking_id).all()]

    def reminder_outbox_for(self, booking_id):
        """Only the 1-hour reminder entries: booking/payment/accept
        already queue customer outbox messages for the same booking."""
        return [(c, r, b) for c, r, b in self.outbox_for(booking_id)
                if b.startswith("Noel Chauffer: your ride starts in about an hour.")]

    def booking_row(self, booking_id):
        with app_module.app.app_context():
            b = app_module.db.session.get(app_module.Booking, booking_id)
            app_module.db.session.expunge(b)
            return b

    def events_for(self, booking_id):
        with app_module.app.app_context():
            return [e.type for e in app_module.BookingEvent.query
                    .filter_by(booking_id=booking_id).all()]

    # -- firing rules ------------------------------------------------------
    def test_fires_once_within_window(self):
        booking, driver, _token = self.accepted_booking(45)
        resp = self.run_reminders_as_owner()
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["reminded"], [booking["id"]])
        outbox = self.reminder_outbox_for(booking["id"])
        # One SMS + one email, both to the driver, nothing else.
        self.assertEqual(sorted(c for c, _r, _b in outbox), ["email", "sms"])
        self.assertIsNotNone(self.booking_row(booking["id"]).pickup_reminder_sent_at)
        self.assertIn("pickup_reminder", self.events_for(booking["id"]))
        # Second run: idempotent — nothing new is queued.
        resp = self.run_reminders_as_owner()
        self.assertEqual(resp.get_json()["reminded"], [])
        self.assertEqual(len(self.reminder_outbox_for(booking["id"])), 2)
        self.assertEqual(self.events_for(booking["id"]).count("pickup_reminder"), 1)

    def test_does_not_fire_more_than_an_hour_out(self):
        booking, _d, _t = self.accepted_booking(61)
        resp = self.run_reminders_as_owner()
        self.assertEqual(resp.get_json()["reminded"], [])
        self.assertEqual(self.reminder_outbox_for(booking["id"]), [])
        self.assertIsNone(self.booking_row(booking["id"]).pickup_reminder_sent_at)

    def test_fires_at_window_edge(self):
        booking, _d, _t = self.accepted_booking(60)
        resp = self.run_reminders_as_owner()
        self.assertEqual(resp.get_json()["reminded"], [booking["id"]])

    def test_does_not_fire_after_pickup_time(self):
        booking, _d, _t = self.accepted_booking(-10)
        resp = self.run_reminders_as_owner()
        self.assertEqual(resp.get_json()["reminded"], [])
        self.assertEqual(self.reminder_outbox_for(booking["id"]), [])

    def test_requires_accepted_driver(self):
        # Paid but still "offered" — no driver assigned, no reminder.
        date, time = self.pickup_offset(30)
        booking = self.book(date=date, time=time)
        self.pay(booking["id"])
        resp = self.run_reminders_as_owner()
        self.assertEqual(resp.get_json()["reminded"], [])

    def test_not_after_trip_started(self):
        booking, _d, token = self.accepted_booking(30)
        resp = self.trip_event(token, booking["id"], "en_route")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.run_reminders_as_owner()
        self.assertEqual(resp.get_json()["reminded"], [])
        self.assertEqual(self.reminder_outbox_for(booking["id"]), [])

    def test_not_after_cancel_or_completion(self):
        # Cancelled by the customer: no reminder.
        booking, _d, _t = self.accepted_booking(30)
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": self._last_customer_phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(self.booking_row(booking["id"]).status, "cancelled")
        self.assertEqual(self.run_reminders_as_owner().get_json()["reminded"], [])
        # Terminal statuses set directly: the gate is on status alone.
        for status in ("completed", "no_show"):
            booking2, _d2, _t2 = self.accepted_booking(30)
            with app_module.app.app_context():
                b = app_module.db.session.get(app_module.Booking, booking2["id"])
                b.status = status
                app_module.db.session.commit()
            self.assertEqual(self.run_reminders_as_owner().get_json()["reminded"], [])
            self.assertEqual(self.reminder_outbox_for(booking2["id"]), [])

    # -- content rule ------------------------------------------------------
    def test_content_is_pickup_time_and_addresses_only(self):
        booking, driver, _t = self.accepted_booking(45)
        self.run_reminders_as_owner()
        outbox = self.reminder_outbox_for(booking["id"])
        self.assertEqual(len(outbox), 2)
        row = self.booking_row(booking["id"])
        for _channel, _recipient, body in outbox:
            self.assertIn(booking["date"], body)
            self.assertIn(booking["time"], body)
            self.assertIn("JFK Airport", body)
            self.assertIn("Times Square, New York", body)
            # No money, no distance, ever.
            self.assertNotIn("$", body)
            self.assertNotIn(str(row.fare_total), body)
            self.assertNotIn(str(row.driver_earnings), body)
            self.assertNotIn("18.0", body)
            self.assertNotIn("mile", body.lower())

    def test_hourly_reminder_has_no_dropoff(self):
        date, time = self.pickup_offset(30)
        booking = self.book(date=date, time=time, ride_type="hourly",
                            hours=3, dropoff="")
        self.pay(booking["id"])
        _driver, token = self.register_driver()
        self.accept(token, booking["id"])
        self.run_reminders_as_owner()
        outbox = self.reminder_outbox_for(booking["id"])
        self.assertEqual(len(outbox), 2)
        for _c, _r, body in outbox:
            self.assertIn("JFK Airport", body)
            self.assertNotIn("Drop-off", body)

    def test_outbox_recipients_are_the_driver(self):
        booking, driver, _t = self.accepted_booking(45)
        self.run_reminders_as_owner()
        by_channel = {c: r for c, r, _b in self.reminder_outbox_for(booking["id"])}
        self.assertEqual(by_channel["sms"], driver["phone"])
        self.assertEqual(by_channel["email"], driver["email"])

    # -- flag reset --------------------------------------------------------
    def test_flag_resets_on_cancel_and_reaccept(self):
        # Driver A accepts 3 hours out (cancel allowed), a reminder is
        # simulated as queued, then A cancels: the flag must clear so
        # the next driver gets his own reminder.
        booking, _da, token_a = self.accepted_booking(180)
        with app_module.app.app_context():
            b = app_module.db.session.get(app_module.Booking, booking["id"])
            b.pickup_reminder_sent_at = datetime.now(timezone.utc)
            app_module.db.session.commit()
        resp = self.trip_event(token_a, booking["id"], "cancel")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        row = self.booking_row(booking["id"])
        self.assertEqual(row.status, "offered")
        self.assertIsNone(row.pickup_reminder_sent_at)
        # Driver B accepts; move the pickup into the window and the
        # reminder fires for B (and only B).
        _db, token_b = self.register_driver()
        self.accept(token_b, booking["id"])
        date, time = self.pickup_offset(30)
        with app_module.app.app_context():
            b = app_module.db.session.get(app_module.Booking, booking["id"])
            b.date = date
            b.time = time
            app_module.db.session.commit()
        self.assertEqual(self.run_reminders_as_owner().get_json()["reminded"],
                         [booking["id"]])
        by_channel = {c: r for c, r, _b in self.reminder_outbox_for(booking["id"])}
        self.assertEqual(by_channel["sms"], _db["phone"])

    # -- driver endpoint (in-app banner payload) ---------------------------
    def test_driver_endpoint_returns_reminder_in_window(self):
        booking, _d, token = self.accepted_booking(30)
        resp = self.client.get("/api/drivers/me/pickup-reminder",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        rem = resp.get_json()["reminder"]
        self.assertIsNotNone(rem)
        self.assertEqual(rem["booking_id"], booking["id"])
        self.assertEqual(rem["date"], booking["date"])
        self.assertEqual(rem["time"], booking["time"])
        self.assertEqual(rem["pickup"], "JFK Airport")
        self.assertEqual(rem["dropoff"], "Times Square, New York")
        # No money or distance field reaches the driver, ever.
        self.assertEqual(set(rem), {"booking_id", "date", "time",
                                    "pickup", "dropoff", "ride_type"})
        # The poll also queued the reminder (best-effort piggyback).
        self.assertEqual(len(self.reminder_outbox_for(booking["id"])), 2)

    def test_driver_endpoint_returns_null_outside_window(self):
        _b, _d, token = self.accepted_booking(120)
        resp = self.client.get("/api/drivers/me/pickup-reminder",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.get_json()["reminder"])

    def test_driver_endpoint_requires_driver_auth(self):
        resp = self.client.get("/api/drivers/me/pickup-reminder")
        self.assertEqual(resp.status_code, 401)

    def test_active_trip_fetch_triggers_check(self):
        booking, _d, token = self.accepted_booking(30)
        resp = self.client.get("/api/drivers/me/active-trip",
                               headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self.reminder_outbox_for(booking["id"])), 2)

    # -- owner endpoint auth ----------------------------------------------
    def test_owner_endpoint_requires_owner_session(self):
        resp = self.client.post("/api/owner/run-pickup-reminders", json={})
        self.assertEqual(resp.status_code, 401)

    def test_owner_endpoint_accepts_bearer_cron_secret(self):
        booking, _d, _t = self.accepted_booking(30)
        with mock.patch.dict(os.environ, {"PICKUP_REMINDER_CRON_SECRET": "cron-secret-1"}):
            resp = self.client.post(
                "/api/owner/run-pickup-reminders", json={},
                headers={"Authorization": "Bearer cron-secret-1"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json()["reminded"], [booking["id"]])
            # Wrong secret: rejected.
            resp = self.client.post(
                "/api/owner/run-pickup-reminders", json={},
                headers={"Authorization": "Bearer wrong-secret"})
            self.assertEqual(resp.status_code, 401)

    def test_bearer_auth_disabled_without_secret(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PICKUP_REMINDER_CRON_SECRET", None)
            resp = self.client.post(
                "/api/owner/run-pickup-reminders", json={},
                headers={"Authorization": "Bearer anything"})
            self.assertEqual(resp.status_code, 401)

    # -- client wiring (static) -------------------------------------------
    def test_driver_app_banner_and_polling_wiring(self):
        html = read("static/driver.html")
        self.assertEqual(html.count('id="trip-reminder-banner"'), 1)
        self.assertIn('class="reminder-banner hidden" id="trip-reminder-banner"',
                      html)
        css = read("static/css/driver.css")
        self.assertIn(".reminder-banner", css)
        driver_js = read("static/js/driver.js")
        self.assertIn("Your ride starts in about an hour", driver_js)
        self.assertIn('fetch("/api/drivers/me/pickup-reminder"', driver_js)
        self.assertIn("function refreshPickupReminder()", driver_js)
        self.assertIn("function startReminderPolling()", driver_js)
        self.assertIn("function stopReminderPolling()", driver_js)
        # Started when the trip renders, stopped when the trip ends.
        render = driver_js[driver_js.index("function renderTrip()"):]
        render = render[:render.index("/* ---------- Arrival")]
        self.assertIn("startReminderPolling();", render)
        end = driver_js[driver_js.index("function endTrip()"):]
        end = end[:end.index("/* ---------- Location sharing")]
        self.assertIn("stopReminderPolling();", end)
        self.assertIn('hide($("trip-reminder-banner"));', end)

    def test_reminder_banner_chimes_once_on_first_appearance(self):
        # The banner must sound when it first appears: ONE burst of
        # the existing offer chime (playOfferTone, which unlocks
        # audio and fails silently like the offer path). Repeat
        # 30-second polls while the banner is already showing for
        # the same booking must stay silent; hiding the banner
        # resets, so a later (new) reminder chimes once again.
        driver_js = read("static/js/driver.js")
        self.assertIn("reminderChimedBookingId: null", driver_js)
        refresh = driver_js[driver_js.index("function refreshPickupReminder()"):]
        refresh = refresh[:refresh.index("function startReminderPolling()")]
        # Exactly one tone call in the refresh path, guarded by the
        # hidden->shown transition and the per-booking chimed id.
        self.assertEqual(refresh.count("playOfferTone();"), 1)
        self.assertIn('banner.classList.contains("hidden")', refresh)
        self.assertIn("state.reminderChimedBookingId !== rem.booking_id",
                      refresh)
        self.assertIn("state.reminderChimedBookingId = rem.booking_id",
                      refresh)
        # The hide branches reset the chimed id so a later reminder
        # can chime again.
        self.assertGreaterEqual(
            refresh.count("state.reminderChimedBookingId = null"), 2)
        # One burst only — never the repeating 30-second offer loop.
        self.assertNotIn("startOfferTone", refresh)
        self.assertNotIn("setInterval", refresh)

    def test_owner_dashboard_triggers_check_on_load(self):
        owner_js = read("static/js/owner.js")
        self.assertIn('fetch("/api/owner/run-pickup-reminders"', owner_js)
        self.assertIn("function runPickupReminders()", owner_js)
        enter = owner_js[owner_js.index("function enterDashboard"):]
        enter = enter[:enter.index("function runPickupReminders()")]
        self.assertIn("runPickupReminders();", enter)


if __name__ == "__main__":
    unittest.main()
