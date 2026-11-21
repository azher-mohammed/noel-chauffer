"""Tests for the post-booking customer view (owner decision, voice call
2026-11-18 ~19:38 EST): after a customer books a ride, ONLY that ride
stays in front of them. The booking form ("View options") must not come
back — a second, separate option ("Book another ride") is the only way
to book another ride.

The bug: after class selection, `proceedWith` did
`show($("booking-card"))` and `startTracking` never hid the form, so
the filled form with its "View options" button stayed visible next to
the ride status/payment — tapping it again re-submitted the same values
and created a DUPLICATE booking. The same pattern existed in the
customer app (Book tab reachable with the filled form).

Rules pinned here (website + customer app):
- Once a booking is created, the booking form is hidden while the ride
  is live (finding, offered, accepted, en route, arrived, on trip).
- The form submit is guarded: while a ride is live, submitting the
  form does nothing (no duplicate booking can be created).
- "Book another ride" (website thank-you block; app status view) is
  the separate option: it opens a FRESH EMPTY form (all fields cleared,
  hours back to 2, one-way tab active).
- "Book your return trip" is unchanged: swapped pickup/drop-off, date
  and time cleared, same customer.
- Cancelling a ride returns the fresh empty form (no ride is live).
- A completed/cancelled/no-show ride is terminal: the form may be used
  again (Book tab works in the app; submit guard passes).
- Restoring a ride (app: open from history) tracks it with the form
  cleared, and the Book tab redirects to the ride while it is live.
- Nothing server-side changes: booking creation, class selection,
  payment, dispatch, chat, referral are untouched.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-single-ride-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "singleride-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo (same as the other API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Single Ride Tester"}


def read(path):
    with open(os.path.join(REPO_DIR, path), encoding="utf-8") as fh:
        return fh.read()


def block(js, start, length=1500):
    i = js.index(start)
    return js[i:i + length]


class WebsiteFlowCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        self.js = read("static/js/customer.js")
        self.html = read("static/index.html")

    def test_form_hidden_once_tracking_starts(self):
        body = block(self.js, "function startTracking(booking, phone)", 1600)
        self.assertIn('hide($("booking-card"))', body,
                      "startTracking must hide the booking form")

    def test_class_continue_does_not_reshow_form(self):
        body = block(self.js, "function proceedWith(updated)", 400)
        self.assertIn('hide($("booking-card"))', body,
                      "proceedWith must keep the form hidden")
        self.assertNotIn('show($("booking-card"))', body,
                         "proceedWith must not show the form again")

    def test_submit_guarded_while_ride_live(self):
        body = block(self.js, '$("booking-form").addEventListener("submit"', 700)
        self.assertIn("if (hasActiveRide()) return;", body,
                      "form submit must be a no-op while a ride is live")

    def test_has_active_ride_terminal_statuses(self):
        body = block(self.js, "TERMINAL_RIDE_STATUSES", 300)
        for st in ("cancelled", "canceled", "completed", "no_show"):
            self.assertIn('"%s"' % st, body,
                          "terminal statuses must include %s" % st)

    def test_book_another_ride_opens_fresh_empty_form(self):
        body = block(self.js, '$("new-booking-btn").addEventListener', 900)
        self.assertIn("clearBookingForm()", body,
                      "Book another ride must clear the form")
        self.assertIn('show($("booking-card"))', body,
                      "Book another ride must show the form")
        self.assertIn("state.bookingId = null;", body,
                      "Book another ride must clear the ride state")
        form = block(self.js, "function clearBookingForm()", 1400)
        for field in ("bk-name", "bk-phone", "bk-email", "bk-pickup",
                      "bk-dropoff", "bk-date", "bk-time", "bk-referral"):
            self.assertIn('"%s"' % field, form,
                          "clearBookingForm must empty %s" % field)
        self.assertIn('$("bk-hours").value = "2";', form)
        # Passengers field removed (owner, 2026-11-20): no reference
        # to it may survive in the form JS.
        self.assertNotIn("bk-passengers", form)
        self.assertNotIn("field-passengers", form)
        self.assertIn('btn.textContent = "View options";', form)

    def test_no_passengers_field_in_booking_forms(self):
        # Passengers field removed (owner, 2026-11-20, from his
        # phone screenshot): neither the website form nor the app
        # form may carry it; the class cards still show each
        # class's capacity ("3 passengers · 2 bags").
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for rel, field in (("static/index.html", "bk-passengers"),
                           ("static/customer-app.html", "ca-passengers")):
            with open(os.path.join(repo, rel), encoding="utf-8") as fh:
                html = fh.read()
            self.assertNotIn('id="%s"' % field, html,
                             "%s must not have a passengers field" % rel)
            self.assertNotIn("field-passengers", html,
                             "%s must not have a passengers wrapper" % rel)

    def test_return_trip_unchanged_with_swapped_addresses(self):
        body = block(self.js, '$("return-trip-btn").addEventListener', 1400)
        self.assertIn('$("bk-pickup").value = b.dropoff', body)
        self.assertIn('$("bk-dropoff").value = b.pickup', body)
        self.assertIn('$("bk-date").value = "";', body)
        self.assertIn('$("bk-time").value = "";', body)
        self.assertIn('show($("booking-card"))', body,
                      "return trip must show the form")
        self.assertIn('hide($("thankyou-block"))', body,
                      "return trip must hide the thank-you block")

    def test_cancel_returns_fresh_form(self):
        body = block(self.js, '$("cancel-booking-btn").addEventListener', 2400)
        self.assertIn("clearBookingForm()", body,
                      "cancel must return a fresh empty form")
        self.assertIn('show($("booking-card"))', body)
        self.assertIn("state.bookingId = null;", body,
                      "cancel must clear the ride state")
        self.assertIn('hide($("thankyou-block"))', body,
                      "cancel must hide the stale thank-you block")

    def test_buttons_exist_with_exact_labels(self):
        self.assertIn('id="new-booking-btn">Book another ride<', self.html)
        self.assertIn('id="return-trip-btn">Book your return trip<', self.html)


class AppFlowCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        self.js = read("static/js/customer-app.js")
        self.html = read("static/customer-app.html")

    def test_book_tab_redirects_to_ride_while_live(self):
        body = block(self.js, "function showScreen(name)", 800)
        self.assertIn("hasActiveRide()", body,
                      "showScreen must check for a live ride")
        self.assertIn('name = "rides"', body,
                      "Book tab must show the live ride instead of the form")

    def test_tracking_clears_form(self):
        body = block(self.js, "function startTracking(booking, phone)", 1800)
        self.assertIn("clearBookingForm()", body,
                      "tracking a ride must clear the Book tab form")

    def test_submit_guarded_while_ride_live(self):
        body = block(self.js, '$("ca-booking-form").addEventListener("submit"', 800)
        self.assertIn("if (hasActiveRide()) return;", body,
                      "app form submit must be a no-op while a ride is live")

    def test_book_another_ride_opens_fresh_empty_form(self):
        body = block(self.js, '$("ca-new-booking-btn").addEventListener', 900)
        self.assertIn("clearBookingForm()", body,
                      "Book another ride must clear the form")
        self.assertIn('show($("ca-booking-card"))', body)
        self.assertIn("state.bookingId = null;", body)
        form = block(self.js, "function clearBookingForm()", 1400)
        for field in ("ca-name", "ca-phone", "ca-email", "ca-pickup",
                      "ca-dropoff", "ca-date", "ca-time", "ca-referral"):
            self.assertIn('"%s"' % field, form,
                          "clearBookingForm must empty %s" % field)
        self.assertIn('$("ca-hours").value = "2";', form)
        # Passengers field removed (owner, 2026-11-20): no reference
        # to it may survive in the app form JS.
        self.assertNotIn("ca-passengers", form)
        self.assertNotIn("ca-field-passengers", form)

    def test_return_trip_unchanged_with_swapped_addresses(self):
        body = block(self.js, '$("ca-return-trip-btn").addEventListener', 1400)
        self.assertIn('$("ca-pickup").value = b.dropoff', body)
        self.assertIn('$("ca-dropoff").value = b.pickup', body)
        self.assertIn('show($("ca-booking-card"))', body)

    def test_all_rides_back_clears_form(self):
        body = block(self.js, '$("ca-status-back").addEventListener', 800)
        self.assertIn("clearBookingForm()", body,
                      "going back to All rides must empty the form")

    def test_cancel_clears_ride_and_form(self):
        body = block(self.js, '$("ca-cancel-booking-btn").addEventListener', 2600)
        self.assertIn("clearBookingForm()", body)
        self.assertIn("state.bookingId = null;", body)
        self.assertIn('hide($("ca-thankyou-block"))', body)

    def test_buttons_exist_with_exact_labels(self):
        self.assertIn('id="ca-new-booking-btn">Book another ride<', self.html)
        self.assertIn('id="ca-return-trip-btn">Book your return trip<', self.html)

    def test_no_duplicate_booking_path_in_class_continue(self):
        # proceedWith in the app hands the ride to startTracking (which
        # clears the form); it must not leave the filled form behind
        # as a re-submittable duplicate.
        body = block(self.js, "function proceedWith(updated)", 400)
        self.assertIn("startTracking(updated, state.classPhone);", body)


class BookingApiStillWorksCase(unittest.TestCase):
    """No server change in this build: booking, payment, cancellation
    and re-booking must all still work through the API."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._phone_seq = 0

    def book(self, phone=None, **extra):
        if phone is None:
            self._phone_seq += 1
            phone = "+1555013%04d" % self._phone_seq
        payload = {
            "customer_name": "Single Ride Tester",
            "phone": phone,
            "email": "single@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def test_past_date_and_time_cannot_be_booked(self):
        # Owner decision 2026-11-20: a past date — or today at a
        # time already gone — is rejected, so a customer can never
        # book a ticket for a month or year that has passed.
        past = {
            "customer_name": "Past Tester",
            "phone": "+15550138888",
            "email": "past@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2020-01-01", "time": "12:00", "ride_type": "one_way",
        }
        resp = self.client.post("/api/bookings", json=past)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertIn("in the past", resp.get_json().get("error", ""))
        # Today at a time two hours ago is past too.
        now_ny = datetime.now(ZoneInfo("America/New_York"))
        past_today = dict(past)
        past_today["date"] = now_ny.strftime("%Y-%m-%d")
        past_today["time"] = (now_ny - timedelta(hours=2)).strftime("%H:%M")
        resp = self.client.post("/api/bookings", json=past_today)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertIn("in the past", resp.get_json().get("error", ""))

    def test_client_blocks_past_date_and_time(self):
        # The date picker starts at today and the submit handler
        # refuses a past date or a past time today (owner decision
        # 2026-11-20), on the website and in the app.
        for rel in ("static/js/customer.js", "static/js/customer-app.js"):
            js = read(rel)
            self.assertIn("todayNY", js, rel)
            self.assertIn("Past dates cannot be booked", js, rel)
            self.assertIn("Past times cannot be booked", js, rel)

    def test_book_pay_cancel_then_book_again(self):
        phone = "+15550139999"
        first = self.book(phone)
        self.assertTrue(first["id"])
        self.assertIn("class_totals", first)
        resp = self.client.post("/api/bookings/%s/pay" % first["id"], json=CARD)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertTrue(resp.get_json()["payment"])
        resp = self.client.post("/api/bookings/%s/cancel" % first["id"],
                                json={"phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertTrue(resp.get_json().get("refund"))
        # The customer can book again after cancelling: a new booking
        # with a new id (the fresh form the client shows).
        second = self.book(phone)
        self.assertNotEqual(second["id"], first["id"])
        self.assertEqual(second["status"], first["status"])

    def test_hourly_booking_still_works(self):
        payload = {
            "customer_name": "Single Ride Tester",
            "phone": "+15550138888",
            "email": "single@test.com",
            "pickup": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00",
            "ride_type": "hourly", "hours": 3, "vehicle_class": "sedan",
        }
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking = resp.get_json()["booking"]
        resp = self.client.post("/api/bookings/%s/pay" % booking["id"], json=CARD)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])


if __name__ == "__main__":
    unittest.main()
