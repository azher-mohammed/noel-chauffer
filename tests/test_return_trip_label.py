"""Tests for the return-trip label (owner decision, voice call
2026-11-20 ~21:54 EST): a booking made through "Book your return
trip" must display "Return trip", not "One way".

The bug: the return-trip button only swapped pickup/drop-off and
created a plain one-way booking — no return flag existed anywhere,
so every surface labelled it "One way". Worse, the history lookup
(GET /api/bookings?phone=) never returned a ride type at all, so
every history item rendered as "One way" regardless.

Rules pinned here:
- POST /api/bookings with is_return=true on a one-way ride stores
  the flag and returns it on create, on GET /api/bookings/<id>, on
  the history lookup, and on the owner row. A plain one-way (no
  flag) reads as False; an hourly ride can never carry the flag,
  even if is_return=true is sent with it.
- Customer site + app: the return-trip button marks the next
  booking as a return (payload is_return=true); "Book another ride",
  tab switches and the fresh-form reset clear the flag, so a fresh
  outward booking is never mislabelled. The confirmation/status
  summary and the history line show "Return trip" for returns and
  "One way" for true one-ways; hourly still shows "By the hour".
- Driver offers + trip screen show "Return trip" for return rides.
- Owner bookings list + detail show "Return trip" for returns.
- The existing test return booking (Times Square -> JFK, 21 Nov
  2026, made before the flag existed) is NOT relabelled from thin
  air: rows created before the flag read as outward one-ways.

Run:  python -m unittest discover -s tests -p "test_return_trip_label.py"
"""

import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-return-label-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "returnlabel-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo (same as the other API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Return Trip Tester"}


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def block(js, start, length=1500):
    i = js.index(start)
    return js[i:i + length]


class ReturnFlagApiCase(unittest.TestCase):
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
            phone = "+1555014%04d" % self._phone_seq
        payload = {
            "customer_name": "Return Trip Tester",
            "phone": phone,
            "email": "return@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def test_return_booking_stores_and_returns_flag(self):
        booking = self.book(is_return=True)
        self.assertTrue(booking["is_return"], "create must return is_return=true")
        resp = self.client.get(f"/api/bookings/{booking['id']}")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertTrue(resp.get_json()["booking"]["is_return"],
                        "GET booking must carry is_return=true")

    def test_outward_booking_defaults_to_not_return(self):
        booking = self.book()
        self.assertFalse(booking["is_return"], "a plain one-way must read as not a return")
        resp = self.client.get(f"/api/bookings/{booking['id']}")
        self.assertFalse(resp.get_json()["booking"]["is_return"])

    def test_hourly_cannot_be_a_return_trip(self):
        booking = self.book(ride_type="hourly", hours=2, is_return=True,
                            vehicle_class="sedan")
        self.assertFalse(booking["is_return"],
                         "an hourly ride must never carry the return flag")
        self.assertEqual(booking["ride_type"], "hourly")

    def test_history_returns_type_and_flag(self):
        phone = "+15550149999"
        outward = self.book(phone, pickup="Times Square, New York",
                            dropoff="JFK Airport")
        ret = self.book(phone, pickup="JFK Airport",
                        dropoff="Times Square, New York", is_return=True)
        resp = self.client.get("/api/bookings", query_string={"phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        rows = {row["id"]: row for row in resp.get_json()}
        self.assertEqual(rows[outward["id"]]["ride_type"], "one_way")
        self.assertFalse(rows[outward["id"]]["is_return"])
        self.assertEqual(rows[ret["id"]]["ride_type"], "one_way")
        self.assertTrue(rows[ret["id"]]["is_return"],
                        "history must carry the return flag so it can show 'Return trip'")

    def test_owner_row_carries_flag(self):
        booking = self.book(is_return=True)
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        resp = self.client.get("/api/owner/bookings",
                               query_string={"q": str(booking["id"])})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        rows = resp.get_json()["bookings"]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["is_return"], "owner row must carry is_return=true")


class ReturnLabelClientCase(unittest.TestCase):
    def setUp(self):
        self.web = read("static/js/customer.js")
        self.app_js = read("static/js/customer-app.js")

    def test_label_helper_distinguishes_return_from_one_way(self):
        for name, js in (("website", self.web), ("app", self.app_js)):
            body = block(js, "function rideTypeLabel", 400)
            self.assertIn('if (b.is_return) return T("status.return_trip_label", "Return trip");', body, name)
            self.assertIn('return T("status.one_way_label", "One way");', body, name)
            self.assertIn('return T("form.by_hour", "By the hour");', body, name)

    def test_return_button_marks_next_booking_as_return(self):
        for name, js, pickup in (("website", self.web, "bk-pickup"),
                                 ("app", self.app_js, "ca-pickup")):
            body = block(js, "return-trip-btn\").addEventListener", 1400)
            self.assertIn("state.isReturnTrip = true;", body, name)
            self.assertIn(f'$("{pickup}").value = b.dropoff', body, name)
            payload = block(js, 'if (state.rideType === "one_way") {', 400)
            self.assertIn("if (state.isReturnTrip) payload.is_return = true;",
                          payload, name)

    def test_fresh_form_clears_the_return_flag(self):
        for name, js in (("website", self.web), ("app", self.app_js)):
            body = block(js, "function clearBookingForm", 1200)
            self.assertIn("state.isReturnTrip = false;", body, name)
            tabs = block(js, 'state.rideType = tab.getAttribute("data-ride-type");', 120)
            self.assertIn("state.isReturnTrip = false;", tabs, name)

    def test_history_and_summary_show_return_trip(self):
        for name, js in (("website", self.web), ("app", self.app_js)):
            summary = block(js, "function summaryText", 400)
            self.assertIn('if (b.ride_type !== "hourly") text += " · " + rideTypeLabel(b);',
                          summary, name)
            self.assertNotIn('" · One way")', js,
                             "%s must not hard-code the One way label" % name)
        # The website history line moved out of customer.js into
        # ride-history.js with the homepage split (owner 2026-11-21):
        # it must use rideTypeLabel there, not hard-code "One way".
        history_js = read("static/js/ride-history.js")
        self.assertIn('" · " + rideTypeLabel(b)', history_js,
                      "history line must use rideTypeLabel")
        self.assertNotIn('" · One way")', history_js,
                         "history must not hard-code the One way label")

    def test_driver_offer_and_trip_show_return_trip(self):
        js = read("static/js/driver.js")
        self.assertIn('else if (o.is_return) when += (when ? " · " : "") + "Return trip";', js,
                      "driver offers must show Return trip")
        self.assertIn('else if (t.is_return) when += (when ? " · " : "") + "Return trip";', js,
                      "driver trip screen must show Return trip")

    def test_owner_list_and_detail_show_return_trip(self):
        js = read("static/js/owner.js")
        self.assertIn('(b.is_return ? "Return trip" : "One way")', js,
                      "owner detail Ride type must show Return trip")
        self.assertIn('classBit + (b.is_return ? " · Return trip" : "")', js,
                      "owner list row must show Return trip")


if __name__ == "__main__":
    unittest.main()
