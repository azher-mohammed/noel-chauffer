"""Tests for the CUSTOMER referral 5% discount (owner decision, voice
call 2026-11-18 ~19:19 EST): when a NEW customer books their FIRST
one-way ride with a valid referral code (from a customer's referral
link), they get 5% off the total (fare + toll). The referring
customer gets NOTHING — there is no referrer reward of any kind.

Rules pinned here:
- 5% off the total (fare + toll); driver pay UNCHANGED; the discount
  comes out of Noel's profit only.
- First booking only, identified by phone number (normalized, so
  "+1 929-..." and "929..." are the same phone). A phone with any
  prior booking gets no discount.
- Class totals on the options page show the DISCOUNTED totals.
- The discount is decided at booking creation and stored on the
  booking; switching class or changing the toll recomputes it at 5%
  of the new total — a booking without it never gains it.
- Hourly rides never get a referral discount.
- Chain: a referred friend who then refers someone else passes the
  same 5% first-ride discount on; referrers never earn at any step.
- Wording is friend-only: the referral sections say the friend gets
  5% off their first ride; nothing anywhere promises the referrer
  anything.

Concrete fare used throughout: JFK Airport -> Times Square, mocked
at 18.0 miles, toll $0.00. Sedan total $162.00, discounted $153.90
(discount $8.10); SUV total $180.00, discounted $171.00 (discount
$9.00); driver sedan $95.00, SUV $130.00 (slabs), unchanged.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-ref-discount-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "refdiscount-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo (same as the other API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
from pricing import compute_class_totals, compute_one_way, money  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = Decimal


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def approx(a, b):
    return a is not None and b is not None and abs(float(a) - float(b)) < 0.005


class ReferralDiscountPricingCase(unittest.TestCase):
    def test_five_percent_off_sedan_total(self):
        r = compute_one_way(D("18.0"), referral=True)
        self.assertEqual(r["referral_discount"], D("8.10"))
        self.assertEqual(r["total"], D("153.90"))
        # Driver pay unchanged; the discount comes out of profit only.
        self.assertEqual(r["driver_earnings"], D("95.00"))
        self.assertEqual(r["profit"], D("58.90"))

    def test_five_percent_off_suv_total(self):
        r = compute_one_way(D("18.0"), vehicle_class="suv", referral=True)
        self.assertEqual(r["referral_discount"], D("9.00"))
        self.assertEqual(r["total"], D("171.00"))
        self.assertEqual(r["driver_earnings"], D("130.00"))
        self.assertEqual(r["profit"], D("41.00"))

    def test_five_percent_off_total_including_toll(self):
        # JFK -> Times Square with the $7.46 toll: (162.00 + 7.46) * 5%.
        r = compute_one_way(D("18.0"), toll=D("7.46"), referral=True)
        self.assertEqual(r["referral_discount"], D("8.47"))
        self.assertEqual(r["total"], D("160.99"))
        self.assertEqual(r["driver_earnings"], D("102.46"))

    def test_no_referral_means_no_discount(self):
        r = compute_one_way(D("18.0"))
        self.assertEqual(r["referral_discount"], D("0.00"))
        self.assertEqual(r["total"], D("162.00"))

    def test_class_totals_carry_the_discount(self):
        totals = compute_class_totals(D("18.0"), referral=True)
        self.assertEqual(totals["sedan"], D("153.90"))
        self.assertEqual(totals["suv"], D("171.00"))
        plain = compute_class_totals(D("18.0"))
        self.assertEqual(plain["sedan"], D("162.00"))
        self.assertEqual(plain["suv"], D("180.00"))


class ReferralDiscountApiCase(unittest.TestCase):
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
            phone = f"+1555012{self._phone_seq:04d}"
        payload = {
            "customer_name": "Discount Tester",
            "phone": phone,
            "email": "discount@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json={
            "card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Discount Tester"})

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_first_booking_with_valid_code_gets_five_percent_off(self):
        first = self.book()
        code = first["referral_code"]
        self.assertTrue(code)
        referred = self.book(referral_code=code)
        self.assertTrue(approx(referred["total"], "153.90"), referred)
        self.assertTrue(approx(referred["referral_discount"], "8.10"), referred)
        self.assertEqual(referred["class_totals"]["sedan"], 153.90)
        self.assertEqual(referred["class_totals"]["suv"], 171.00)
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, referred["id"])
            self.assertEqual(row.referral_discount, D("8.10"))
            self.assertEqual(row.driver_earnings, D("95.00"))
            self.assertEqual(row.referral_code_used, code)
            used = app_module.ReferralCode.query.filter_by(code=code).first()
            self.assertEqual(used.used_count, 1)
        # Paying charges the discounted total.
        resp = self.pay(referred["id"])
        self.assertTrue(approx(resp.get_json()["payment"]["amount"], "153.90"))

    def test_second_booking_same_phone_gets_no_discount(self):
        first = self.book(phone="+15550129999")
        code = first["referral_code"]
        # Same phone again — even with a valid code.
        second = self.book(phone="+15550129999", referral_code=code)
        self.assertTrue(approx(second["total"], "162.00"), second)
        self.assertTrue(approx(second["referral_discount"], "0.00"), second)

    def test_same_phone_different_format_gets_no_discount(self):
        first = self.book(phone="+15550129998")
        code = first["referral_code"]
        # Same number without the +1 / punctuation.
        second = self.book(phone="5550129998", referral_code=code)
        self.assertTrue(approx(second["total"], "162.00"), second)
        self.assertTrue(approx(second["referral_discount"], "0.00"), second)

    def test_booking_without_code_is_unchanged(self):
        plain = self.book()
        self.assertTrue(approx(plain["total"], "162.00"), plain)
        self.assertTrue(approx(plain["referral_discount"], "0.00"), plain)

    def test_invalid_code_still_rejected(self):
        with app_module.app.app_context():
            before = app_module.Booking.query.count()
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Discount Tester", "phone": "+15550129997",
            "email": "discount@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
            "referral_code": "NOEL-XXXXXX",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid referral code", resp.get_data(as_text=True))
        with app_module.app.app_context():
            self.assertEqual(app_module.Booking.query.count(), before)

    def test_hourly_with_code_gets_no_discount(self):
        first = self.book()
        code = first["referral_code"]
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Discount Tester", "phone": "+15550129996",
            "email": "discount@test.com",
            "pickup": "Central Park, New York",
            "date": "2030-06-01", "time": "14:00", "ride_type": "hourly",
            "hours": 3, "referral_code": code,
        })
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking = resp.get_json()["booking"]
        self.assertTrue(approx(booking["total"], "270.00"), booking)
        self.assertIsNone(booking.get("referral_discount"))

    def test_class_switch_keeps_discount_at_new_class_rate(self):
        first = self.book()
        code = first["referral_code"]
        referred = self.book(referral_code=code)
        resp = self.client.post(
            f"/api/bookings/{referred['id']}/vehicle-class",
            json={"vehicle_class": "suv"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        updated = resp.get_json()["booking"]
        self.assertTrue(approx(updated["total"], "171.00"), updated)
        self.assertTrue(approx(updated["referral_discount"], "9.00"), updated)
        self.assertEqual(updated["class_totals"]["sedan"], 153.90)
        self.assertEqual(updated["class_totals"]["suv"], 171.00)

    def test_toll_change_recomputes_discount(self):
        first = self.book()
        code = first["referral_code"]
        referred = self.book(referral_code=code)
        self.owner_login()
        resp = self.client.post(
            f"/api/owner/bookings/{referred['id']}/toll", json={"toll": 18.50})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        row = resp.get_json()["booking"]
        # (162.00 + 18.50) = 180.50; 5% = 9.03; total 171.47.
        self.assertTrue(approx(row["customer_total"], "171.47"), row)
        self.assertTrue(approx(row["driver_earnings"], "113.50"), row)
        self.assertTrue(approx(row["referral_discount"], "9.03"), row)
        self.assertEqual(row["referral_code_used"], code)

    def test_owner_detail_shows_discounted_figures_and_code(self):
        first = self.book()
        code = first["referral_code"]
        referred = self.book(referral_code=code)
        self.owner_login()
        resp = self.client.get(f"/api/owner/bookings/{referred['id']}")
        self.assertEqual(resp.status_code, 200)
        detail = resp.get_json()
        self.assertTrue(approx(detail["customer_total"], "153.90"), detail)
        self.assertTrue(approx(detail["driver_earnings"], "95.00"), detail)
        self.assertTrue(approx(detail["profit"], "58.90"), detail)
        self.assertTrue(approx(detail["referral_discount"], "8.10"), detail)
        self.assertEqual(detail["referral_code_used"], code)

    def test_chain_friend_who_refers_passes_discount_on(self):
        # A books with a code and gets the discount; A receives their
        # own code; B books with A's code and gets the discount too.
        # A gets nothing for referring B.
        first = self.book()
        code = first["referral_code"]
        friend_a = self.book(referral_code=code)
        self.assertTrue(approx(friend_a["total"], "153.90"), friend_a)
        code_a = friend_a["referral_code"]
        self.assertTrue(code_a)
        self.assertNotEqual(code_a, code)
        friend_b = self.book(referral_code=code_a)
        self.assertTrue(approx(friend_b["total"], "153.90"), friend_b)
        self.assertTrue(approx(friend_b["referral_discount"], "8.10"), friend_b)
        with app_module.app.app_context():
            row_a = app_module.db.session.get(app_module.Booking, friend_a["id"])
            self.assertEqual(row_a.referral_discount, D("8.10"))
            # A earned nothing as a referrer: no referrer reward
            # exists anywhere on A's records.
            self.assertEqual(row_a.fare_total, D("153.90"))


class ReferralDiscountWordingCase(unittest.TestCase):
    FRIEND_ONLY = "Your friend gets 5% off their first ride."

    def test_referral_sections_state_friend_only_five_percent(self):
        for rel in ("static/index.html", "static/customer-app.html"):
            html = read(rel)
            self.assertIn(self.FRIEND_ONLY, html, rel)

    def test_no_referrer_benefit_promised_in_customer_files(self):
        banned = ("you earn", "you get 5%", "your reward", "cash back",
                  "cashback", "free ride", "both get", "referral earnings",
                  "you will earn", "you'll earn")
        for rel in ("static/index.html", "static/customer-app.html",
                    "static/js/customer.js", "static/js/customer-app.js"):
            text = read(rel).lower()
            for phrase in banned:
                self.assertNotIn(phrase, text,
                                 f"{rel} must not promise the referrer {phrase!r}")

    def test_options_note_and_form_hint_exist(self):
        self.assertIn('id="class-discount-note"',
                      read("static/index.html"))
        self.assertIn('id="ca-class-discount-note"',
                      read("static/customer-app.html"))
        self.assertIn("Referral discount applied — 5% off your first ride.",
                      read("static/index.html"))
        self.assertIn("Referral discount applied — 5% off your first ride.",
                      read("static/customer-app.html"))
        self.assertIn("First ride? Enter a friend's referral code for 5% off.",
                      read("static/index.html"))
        self.assertIn("First ride? Enter a friend's referral code for 5% off.",
                      read("static/customer-app.html"))

    def test_options_note_shown_only_when_discount_applies(self):
        for rel, note_id in (("static/js/customer.js", "class-discount-note"),
                             ("static/js/customer-app.js", "ca-class-discount-note")):
            js = read(rel)
            self.assertIn("referral_discount", js, rel)
            self.assertIn(note_id, js, rel)


if __name__ == "__main__":
    unittest.main()
