"""Tests for Blacklane-style hourly ("By the hour") bookings.

Owner decision 2026-11-20 ("same same Blacklane jaisa"): hourly rides
work like Blacklane's — per-class rates from the live Blacklane quote
2026-11-20 (Hilton Times Square, Sat 21 Nov 2026 12:00, 2 hours):
2-hour totals Business $218.32, SUV $269.46, First $343.31; driver
Business $60/hr, SUV $70/hr, First $90/hr. Minimum 2 hours, maximum
24. 25 miles of travel included per hour. Free cancellation up to 24
hours before pickup (vs 1 hour for one-way).

Run:  python -m unittest discover -s tests -p "test_hourly_blacklane.py"
"""

import io
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-hourly-blacklane-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "hourly-blacklane-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: hourly rides price by the hour, not by distance.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
from pricing import compute_hourly  # noqa: E402

CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Hourly Blacklane Customer"}


def approx(a, b):
    return a is not None and abs(float(a) - float(b)) < 0.005


def _ny_from_now(hours):
    """(date, time) strings hours from now, in America/New_York."""
    try:
        from zoneinfo import ZoneInfo
        soon = datetime.now(ZoneInfo("America/New_York")) + timedelta(hours=hours)
    except Exception:
        soon = datetime.now(timezone.utc) + timedelta(hours=hours)
    return soon.strftime("%Y-%m-%d"), soon.strftime("%H:%M")


class HourlyBlacklaneCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, car_model="Mercedes-Benz E-Class"):
        self._driver_seq += 1
        phone = f"+1555002{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Hourly Driver {self._driver_seq}", "phone": phone,
            "email": f"hb{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
            "plate": f"H{self._driver_seq:05d}",
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
        needs a verified sign-in with the booking's email. Signs in
        once per email per test — the session persists for later
        bookings and payments in the same test."""
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin/request",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            row = (app_module.OutboxMessage.query
                   .filter_by(recipient=email, channel="email")
                   .order_by(app_module.OutboxMessage.id.desc()).first())
        self.assertIsNotNone(row, "no sign-in email was queued")
        match = re.search(r"(\d{6})", row.body or "")
        self.assertIsNotNone(match, "no 6-digit code in the email")
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": email, "code": match.group(1)})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def book_hourly(self, hours=2, vehicle_class="sedan", date="2030-06-04", time="14:00"):
        self._phone_seq += 1
        self._last_phone = f"+1555003{self._phone_seq:04d}"
        payload = {
            "customer_name": "Hourly Blacklane Customer",
            "phone": self._last_phone,
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": date, "time": time,
            "ride_type": "hourly", "hours": hours,
        }
        if vehicle_class is not None:
            payload["vehicle_class"] = vehicle_class
        resp = self.client.post("/api/bookings", json=payload)
        if resp.status_code == 201:
            self.signin(payload["email"], payload["phone"])
        return resp

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)

    def owner_detail(self, booking_id):
        return self.client.get(f"/api/owner/bookings/{booking_id}").get_json()

    def offers(self, token):
        return self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token}).get_json()

    # -- per-class totals --------------------------------------------------
    def test_2_hour_totals_per_class(self):
        # 2-hour totals are Blacklane's live quote, to the cent.
        for vehicle_class, total in (("sedan", "218.32"),
                                     ("suv", "269.46"),
                                     ("first", "343.31")):
            resp = self.book_hourly(hours=2, vehicle_class=vehicle_class)
            self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
            booking = resp.get_json()["booking"]
            self.assertTrue(approx(booking["total"], total), booking)
            self.assertEqual(booking["vehicle_class"], vehicle_class)

    def test_3_hour_totals_per_class(self):
        for vehicle_class, total in (("sedan", "327.48"),
                                     ("suv", "404.19"),
                                     ("first", "514.97")):
            resp = self.book_hourly(hours=3, vehicle_class=vehicle_class)
            self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
            booking = resp.get_json()["booking"]
            self.assertTrue(approx(booking["total"], total), booking)

    def test_miles_included_per_hour(self):
        # Owner correction 2026-11-20: miles only — 25 miles included
        # per booked hour (2h = 50 miles, 3h = 75 miles).
        self.assertEqual(compute_hourly(2, "sedan")["miles_included"], 50)
        self.assertEqual(compute_hourly(3, "first")["miles_included"], 75)
        self.assertNotIn("km_included", compute_hourly(2, "sedan"))

    def test_driver_pay_per_class(self):
        # Driver: Business $60/hr, SUV $70/hr, First $90/hr.
        self.owner_login()
        resp = self.book_hourly(hours=2, vehicle_class="sedan")
        sedan_id = resp.get_json()["booking"]["id"]
        self.assertTrue(approx(self.owner_detail(sedan_id)["driver_earnings"], "120.00"))
        resp = self.book_hourly(hours=3, vehicle_class="suv")
        suv_id = resp.get_json()["booking"]["id"]
        self.assertTrue(approx(self.owner_detail(suv_id)["driver_earnings"], "210.00"))
        resp = self.book_hourly(hours=2, vehicle_class="first")
        first_id = resp.get_json()["booking"]["id"]
        self.assertTrue(approx(self.owner_detail(first_id)["driver_earnings"], "180.00"))

    # -- hours validation ---------------------------------------------------
    def test_hours_below_minimum_rejected(self):
        for bad_hours in (1, 0, -1):
            resp = self.book_hourly(hours=bad_hours)
            self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            self.assertEqual(app_module.Booking.query.count(), 0)

    def test_hours_above_maximum_rejected(self):
        resp = self.book_hourly(hours=25)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            self.assertEqual(app_module.Booking.query.count(), 0)

    def test_hours_at_the_edges_accepted(self):
        for ok_hours in (2, 24):
            resp = self.book_hourly(hours=ok_hours)
            self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])

    def test_missing_hours_rejected(self):
        self._phone_seq += 1
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Hourly", "phone": f"+1555003{self._phone_seq:04d}",
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": "2030-06-04", "time": "14:00",
            "ride_type": "hourly", "vehicle_class": "sedan"})
        self.assertEqual(resp.status_code, 400)

    # -- class required ------------------------------------------------------
    def test_class_required(self):
        resp = self.book_hourly(vehicle_class=None)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            self.assertEqual(app_module.Booking.query.count(), 0)

    def test_unknown_class_rejected(self):
        resp = self.book_hourly(vehicle_class="luxury")
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])

    # -- class switch before payment ----------------------------------------
    def test_hourly_class_switch_reprices_before_payment(self):
        resp = self.book_hourly(hours=2, vehicle_class="sedan")
        booking_id = resp.get_json()["booking"]["id"]
        resp = self.client.post(f"/api/bookings/{booking_id}/vehicle-class",
                                json={"vehicle_class": "first"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        switched = resp.get_json()["booking"]
        self.assertEqual(switched["vehicle_class"], "first")
        self.assertEqual(switched["vehicle_class_label"], "First Class")
        self.assertTrue(approx(switched["total"], "343.31"), switched)

    def test_hourly_class_switch_rejected_after_payment(self):
        resp = self.book_hourly(hours=2, vehicle_class="sedan")
        booking_id = resp.get_json()["booking"]["id"]
        self.assertEqual(self.pay(booking_id).status_code, 200)
        resp = self.client.post(f"/api/bookings/{booking_id}/vehicle-class",
                                json={"vehicle_class": "suv"})
        self.assertEqual(resp.status_code, 409)

    # -- class-filtered dispatch ---------------------------------------------
    def test_sedan_and_suv_hourly_dispatch_split(self):
        _, sedan_token = self.register_driver("Mercedes-Benz E-Class")
        _, suv_token = self.register_driver("Cadillac Escalade")
        sedan_id = self.book_hourly(hours=2, vehicle_class="sedan",
                                    time="14:00").get_json()["booking"]["id"]
        suv_id = self.book_hourly(hours=2, vehicle_class="suv",
                                  time="17:00").get_json()["booking"]["id"]
        self.assertEqual(self.pay(sedan_id).status_code, 200)
        self.assertEqual(self.pay(suv_id).status_code, 200)
        self.assertEqual([o["booking_id"] for o in self.offers(sedan_token)], [sedan_id])
        self.assertEqual([o["booking_id"] for o in self.offers(suv_token)], [suv_id])

    def test_first_class_hourly_reaches_only_first_class_drivers(self):
        _, first_token = self.register_driver("Mercedes-Benz S-Class")
        _, sedan_token = self.register_driver("Mercedes-Benz E-Class")
        _, suv_token = self.register_driver("Cadillac Escalade")
        booking_id = self.book_hourly(hours=2, vehicle_class="first").get_json()["booking"]["id"]
        self.assertEqual(self.pay(booking_id).status_code, 200)
        self.assertEqual([o["booking_id"] for o in self.offers(first_token)], [booking_id])
        self.assertEqual(self.offers(sedan_token), [])
        self.assertEqual(self.offers(suv_token), [])
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": sedan_token})
        self.assertEqual(resp.status_code, 409)

    # -- 24-hour free-cancel window -------------------------------------------
    def _paid_hourly_near(self, hours_from_now):
        date, time = _ny_from_now(hours_from_now)
        resp = self.book_hourly(hours=2, vehicle_class="sedan", date=date, time=time)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking = resp.get_json()["booking"]
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        return booking

    def test_hourly_free_cancel_up_to_24_hours_before(self):
        booking = self._paid_hourly_near(25)
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": self._last_phone})
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.get_json()["refund"], True)
        self.assertIs(resp.get_json()["charge_kept"], False)

    def test_hourly_cancel_inside_24_hours_keeps_full_price(self):
        booking = self._paid_hourly_near(23)
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": self._last_phone})
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.get_json()["refund"], False)
        self.assertIs(resp.get_json()["charge_kept"], True)

    def test_one_way_cancel_at_23_hours_still_refunds(self):
        # The 1-hour window is unchanged for one-way rides.
        date, time = _ny_from_now(23)
        self._phone_seq += 1
        phone = f"+1555003{self._phone_seq:04d}"
        resp = self.client.post("/api/bookings", json={
            "customer_name": "One Way", "phone": phone,
            "email": "oneway@test.com", "pickup": "JFK Airport",
            "dropoff": "Times Square, New York",
            "date": date, "time": time, "ride_type": "one_way"})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking = resp.get_json()["booking"]
        # Compulsory sign-in (owner 2026-11-22): payment needs a
        # verified sign-in with the booking's email.
        self.signin("oneway@test.com", phone)
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": phone})
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.get_json()["refund"], True)
        self.assertIs(resp.get_json()["charge_kept"], False)


REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class HourlyClassStepCase(unittest.TestCase):
    """Hourly class/rates show ONLY after View options (owner decision
    2026-11-21), on the website and the customer app. The class step
    is a separate step, mirroring the one-way options page; the first
    screen keeps only Pickup, Date, Time, Hours (+ hint) and contact.
    Rates, miles math, the 2-hour minimum and all totals are unchanged
    (covered by the API tests above)."""

    def test_website_hourly_class_step_after_view_options(self):
        index = _read("static/index.html")
        js = _read("static/js/customer.js")
        # The step exists, hidden until View options.
        self.assertIn('class="class-section hidden" id="hourly-class-step"', index)
        # The class cards, per-class totals and miles note live in the
        # step — not in the booking form.
        form = index.split('id="hourly-class-step"')[0].split('<form id="booking-form"')[1]
        step = index.split('id="hourly-class-step"')[1].split("</section>")[0]
        for gone in ("hr-class-sedan", "hr-class-suv", "hr-class-first",
                     "hr-total-sedan", "hr-total-suv", "hr-total-first",
                     "hr-miles-note"):
            self.assertNotIn(gone, form,
                             "hourly class/rates must not sit on the first screen: %s" % gone)
        for present in ("hr-class-sedan", "hr-class-suv", "hr-class-first",
                        "hr-total-sedan", "hr-total-suv", "hr-total-first",
                        "hr-miles-note", "hourly-class-continue",
                        "hourly-class-back", "hourly-class-trip-summary"):
            self.assertIn(present, step, "hourly class step must show %r" % present)
        # Hours field + min/max hint stay on the first screen.
        self.assertIn('id="bk-hours"', form)
        self.assertIn("Minimum 2 hours, maximum 24", form)
        # JS: View options opens the step; the class is attached there
        # (once), never on the form submit; the tab never shows the
        # class block directly.
        self.assertIn("showHourlyClassStep(payload)", js)
        self.assertIn('show($("hourly-class-step"))', js)
        self.assertIn('hide($("hourly-class-step"))', js)
        self.assertEqual(js.count("payload.vehicle_class = state.hourlyClass"), 1,
                         "the class must be attached only from the class step")
        self.assertNotIn('show($("field-hourly-class"))', js)
        self.assertIn('hourly-class-continue', js)
        self.assertIn('hourly-class-back', js)

    def test_app_hourly_class_step_after_view_options(self):
        html = _read("static/customer-app.html")
        js = _read("static/js/customer-app.js")
        self.assertIn('class="hidden" id="ca-hourly-class-step"', html)
        form = html.split('id="ca-hourly-class-step"')[0].split('<form id="ca-booking-form"')[1]
        step = html.split('id="ca-hourly-class-step"')[1].split('id="ca-class-step"')[0]
        for gone in ("ca-hr-class-sedan", "ca-hr-class-suv", "ca-hr-class-first",
                     "ca-hr-total-sedan", "ca-hr-total-suv", "ca-hr-total-first",
                     "ca-hr-miles-note"):
            self.assertNotIn(gone, form,
                             "hourly class/rates must not sit on the app first screen: %s" % gone)
        for present in ("ca-hr-class-sedan", "ca-hr-class-suv", "ca-hr-class-first",
                        "ca-hr-total-sedan", "ca-hr-total-suv", "ca-hr-total-first",
                        "ca-hr-miles-note", "ca-hourly-class-continue",
                        "ca-hourly-class-back", "ca-hourly-class-trip-summary"):
            self.assertIn(present, step, "app hourly class step must show %r" % present)
        self.assertIn('id="ca-hours"', form)
        self.assertIn("Minimum 2 hours, maximum 24", form)
        self.assertIn("showHourlyClassStep(payload)", js)
        self.assertIn('show($("ca-hourly-class-step"))', js)
        self.assertIn('hide($("ca-hourly-class-step"))', js)
        self.assertEqual(js.count("payload.vehicle_class = state.hourlyClass"), 1,
                         "the class must be attached only from the class step")
        self.assertNotIn('show($("ca-field-hourly-class"))', js)
        self.assertIn('ca-hourly-class-continue', js)
        self.assertIn('ca-hourly-class-back', js)


class ClassCapacitySymbolsCase(unittest.TestCase):
    """Class-card capacity is SVG symbols + numbers only (owner decision
    2026-11-21, spotted on his phone): person icon + number, dot, bag
    icon + number. No visible words like "3 passengers · 2 bags" anywhere
    on the website or the customer app — one-way options or hourly step.
    The aria-labels keep the words for screen readers only."""

    def _check_capacity_symbols(self, html, where):
        self.assertNotIn("passengers · ", html,
                         "%s must show no visible capacity words" % where)
        parts = html.split('class="class-option-capacity"')
        self.assertEqual(len(parts) - 1, 6,
                         "%s must have six capacity lines (3 one-way + 3 hourly)" % where)
        for part in parts[1:]:
            body = part.split("</span></span>", 1)[0]
            self.assertEqual(body.count('class="cap-icon"'), 2,
                             "%s: every capacity line needs person + bag icons" % where)
            visible = re.sub(r"<[^>]+>", "", body.split(">", 1)[1])
            self.assertNotIn("passengers", visible,
                             "%s: no visible capacity words" % where)
            self.assertNotIn("bags", visible,
                             "%s: no visible capacity words" % where)
        for label, count in (("3 passengers, 2 bags", 4), ("5 passengers, 5 bags", 2)):
            self.assertEqual(html.count('aria-label="%s"' % label), count,
                             "%s: aria-labels stay for screen readers: %s" % (where, label))

    def test_website_capacity_is_symbols_not_words(self):
        self._check_capacity_symbols(_read("static/index.html"), "website")

    def test_app_capacity_is_symbols_not_words(self):
        self._check_capacity_symbols(_read("static/customer-app.html"), "customer app")


if __name__ == "__main__":
    unittest.main()
