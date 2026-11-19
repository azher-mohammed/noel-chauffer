"""Tests for vehicle classes + new pricing (decided 2026-11-16; tax
and gratuity removed by owner orders 2026-11-17).

Settled rules under test:
- TWO classes only: sedan (Business Class) $9/mile, SUV (Business
  SUV) $10/mile. NO booking fee. Driver: sedan $4/mile, SUV $7/mile.
- NO tax, NO gratuity on any new booking. Toll passed to the driver.
  Total = fare + toll. Profit = total - driver earnings.
- Referral codes give 5% off a new customer's first one-way booking
  (owner decision 2026-11-18); driver pay unchanged. Hourly unchanged.
- The customer picks a class on the separate "Choose your experience"
  page before paying; dispatch is filtered by class; driver payloads
  never carry miles, fare, tax, total, gratuity, or fee keys.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import re
import sys
import tempfile
import unittest
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-class-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "class.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "class-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the
# other API test modules): sedan total $162.00, SUV total $180.00.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
import car_models as car_models_module  # noqa: E402
from pricing import (  # noqa: E402
    BOOKING_FEE,
    CLASS_LABELS,
    class_label,
    compute_class_totals,
    compute_hourly,
    compute_one_way,
    money,
)

D = Decimal
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Class Customer"}

# (miles, class) -> (fare, gratuity, tax, total, driver, profit).
# Gratuity and tax are $0.00 on every new booking (removed 2026-11-17);
# the keys stay so stored records and the owner API keep their shape.
EXPECTED = {
    ("10.0", "sedan"): ("90.00", "0.00", "0.00", "90.00", "40.00", "50.00"),
    ("10.0", "suv"): ("100.00", "0.00", "0.00", "100.00", "70.00", "30.00"),
    ("18.0", "sedan"): ("162.00", "0.00", "0.00", "162.00", "72.00", "90.00"),
    ("18.0", "suv"): ("180.00", "0.00", "0.00", "180.00", "126.00", "54.00"),
    ("20.0", "sedan"): ("180.00", "0.00", "0.00", "180.00", "80.00", "100.00"),
    ("20.0", "suv"): ("200.00", "0.00", "0.00", "200.00", "140.00", "60.00"),
    ("35.0", "sedan"): ("315.00", "0.00", "0.00", "315.00", "140.00", "175.00"),
    ("35.0", "suv"): ("350.00", "0.00", "0.00", "350.00", "245.00", "105.00"),
}


def approx(a, b):
    return a is not None and abs(float(a) - float(b)) < 0.005


class TestClassPricingPure(unittest.TestCase):
    def test_expected_totals_at_10_18_20_35_miles_both_classes(self):
        for (miles, cls), (fare, grat, tax, total, driver, profit) in EXPECTED.items():
            r = compute_one_way(D(miles), vehicle_class=cls)
            self.assertEqual(r["fare"], D(fare), (miles, cls))
            self.assertEqual(r["gratuity"], D(grat), (miles, cls))
            self.assertEqual(r["tax"], D(tax), (miles, cls))
            self.assertEqual(r["total"], D(total), (miles, cls))
            self.assertEqual(r["driver_earnings"], D(driver), (miles, cls))
            self.assertEqual(r["profit"], D(profit), (miles, cls))
            self.assertEqual(r["vehicle_class"], cls)

    def test_owner_verified_20_mile_examples(self):
        # The exact figures for the 20-mile examples (tax and gratuity
        # removed 2026-11-17: total = fare, profit = total - driver).
        suv = compute_one_way(D("20.0"), vehicle_class="suv")
        self.assertEqual((suv["fare"], suv["gratuity"], suv["tax"], suv["total"],
                          suv["driver_earnings"], suv["profit"]),
                         (D("200.00"), D("0.00"), D("0.00"), D("200.00"),
                          D("140.00"), D("60.00")))
        sedan = compute_one_way(D("20.0"), vehicle_class="sedan")
        self.assertEqual((sedan["fare"], sedan["gratuity"], sedan["tax"], sedan["total"],
                          sedan["driver_earnings"], sedan["profit"]),
                         (D("180.00"), D("0.00"), D("0.00"), D("180.00"),
                          D("80.00"), D("100.00")))

    def test_zero_booking_fee(self):
        self.assertEqual(BOOKING_FEE, D("0"))
        for cls in ("sedan", "suv"):
            self.assertEqual(compute_one_way(D("18.0"), vehicle_class=cls)["booking_fee"], D("0"))

    def test_no_tax_no_gratuity_on_any_new_booking(self):
        # Owner orders 2026-11-17: tax and gratuity are gone from
        # every new booking, both classes, any distance, with or
        # without a toll. Total = fare + toll.
        for miles in ("1.0", "7.3", "10.0", "18.0", "20.0", "35.0", "61.5"):
            for cls in ("sedan", "suv"):
                for toll in ("0.00", "7.46", "18.50"):
                    r = compute_one_way(D(miles), toll=D(toll), vehicle_class=cls)
                    self.assertEqual(r["tax"], D("0.00"), (miles, cls, toll))
                    self.assertEqual(r["gratuity"], D("0.00"), (miles, cls, toll))
                    self.assertEqual(r["total"], r["fare"] + D(toll), (miles, cls, toll))

    def test_toll_passes_through_to_driver(self):
        for cls in ("sedan", "suv"):
            base = compute_one_way(D("18.0"), vehicle_class=cls)
            tolled = compute_one_way(D("18.0"), toll=D("18.50"), vehicle_class=cls)
            self.assertEqual(tolled["tax"], base["tax"], cls)
            self.assertEqual(tolled["fare"], base["fare"], cls)
            self.assertEqual(tolled["total"], base["total"] + D("18.50"), cls)
            self.assertEqual(tolled["driver_earnings"],
                             base["driver_earnings"] + D("18.50"), cls)

    def test_driver_pay_per_class(self):
        for miles, sedan_pay, suv_pay in (("10.0", "40.00", "70.00"),
                                          ("18.0", "72.00", "126.00"),
                                          ("20.0", "80.00", "140.00"),
                                          ("35.0", "140.00", "245.00")):
            self.assertEqual(compute_one_way(D(miles), vehicle_class="sedan")["driver_earnings"],
                             D(sedan_pay))
            self.assertEqual(compute_one_way(D(miles), vehicle_class="suv")["driver_earnings"],
                             D(suv_pay))

    def test_profit_identity(self):
        for miles in ("10.0", "18.0", "20.0", "35.0"):
            for cls in ("sedan", "suv"):
                r = compute_one_way(D(miles), toll=D("5.00"), vehicle_class=cls)
                self.assertEqual(r["profit"], r["total"] - r["driver_earnings"] - r["tax"])
                # Profit = fare - driver pay before toll (toll cancels
                # out; tax and gratuity are $0.00 on new bookings).
                self.assertEqual(r["profit"],
                                 r["fare"]
                                 - (r["driver_earnings"] - r["toll"]))

    def test_referral_code_is_five_percent_off(self):
        # 5% off the total for a first booking with a valid code
        # (owner decision 2026-11-18); driver pay unchanged.
        for cls in ("sedan", "suv"):
            plain = compute_one_way(D("18.0"), vehicle_class=cls)
            referred = compute_one_way(D("18.0"), vehicle_class=cls, referral=True)
            self.assertEqual(referred["total"],
                             plain["total"] - referred["referral_discount"], cls)
            self.assertEqual(referred["driver_earnings"],
                             plain["driver_earnings"], cls)
            self.assertEqual(referred["profit"],
                             plain["profit"] - referred["referral_discount"], cls)
        self.assertEqual(
            compute_one_way(D("18.0"), vehicle_class="sedan", referral=True)["total"],
            D("153.90"))
        self.assertEqual(
            compute_one_way(D("18.0"), vehicle_class="suv", referral=True)["total"],
            D("171.00"))

    def test_hourly_unchanged(self):
        r = compute_hourly(3)
        self.assertEqual(r["total"], D("270.00"))
        self.assertEqual(r["driver_earnings"], D("150.00"))
        self.assertEqual(r["booking_fee"], D("0.00"))
        self.assertEqual(r["gratuity"], D("0.00"))
        self.assertEqual(r["tax"], D("0.00"))
        self.assertIsNone(r["vehicle_class"])

    def test_class_totals_helper(self):
        totals = compute_class_totals(D("20.0"))
        self.assertEqual(totals, {"sedan": D("180.00"), "suv": D("200.00")})
        totals = compute_class_totals(D("18.0"), toll=D("10.00"))
        self.assertEqual(totals, {"sedan": D("172.00"), "suv": D("190.00")})

    def test_class_display_names(self):
        self.assertEqual(CLASS_LABELS, {"sedan": "Business Class", "suv": "Business SUV"})
        self.assertEqual(class_label("sedan"), "Business Class")
        self.assertEqual(class_label("suv"), "Business SUV")
        self.assertIsNone(class_label(None))


class TestModelClassMapping(unittest.TestCase):
    def test_all_133_models_mapped_to_exactly_one_class(self):
        mapping = car_models_module.VEHICLE_CLASS_BY_MODEL
        self.assertEqual(set(mapping), set(car_models_module.allowed_models()))
        self.assertEqual(len(mapping), 133)
        for model, cls in mapping.items():
            self.assertIn(cls, ("sedan", "suv"), model)

    def test_mapping_counts(self):
        values = list(car_models_module.VEHICLE_CLASS_BY_MODEL.values())
        self.assertEqual(values.count("suv"), 85)
        self.assertEqual(values.count("sedan"), 48)

    def test_all_23_black_suv_models_are_suvs(self):
        black_suv = [
            "Cadillac Escalade", "Cadillac Escalade ESV", "Cadillac Escalade IQ",
            "Chevrolet Suburban", "Chevrolet Tahoe",
            "Ford Expedition", "Ford Expedition MAX", "Ford Expedition MAX XLT",
            "GMC Yukon", "GMC Yukon Denali", "GMC Yukon XL", "GMC Yukon XL Denali",
            "Infiniti QX80",
            "Jeep Grand Wagoneer", "Jeep Grand Wagoneer L",
            "Jeep Wagoneer", "Jeep Wagoneer L",
            "Lincoln MKT", "Lincoln Navigator", "Lincoln Navigator L",
            "Mercedes-Benz GL-Class", "Mercedes-Benz GLS SUV", "Rivian R1S",
        ]
        self.assertEqual(len(black_suv), 23)
        for model in black_suv:
            self.assertEqual(car_models_module.class_for_model(model), "suv", model)

    def test_tesla_mapping(self):
        # Model 3 is the temporary owner-trial exception: a sedan.
        self.assertEqual(car_models_module.class_for_model("Tesla Model 3"), "sedan")
        self.assertEqual(car_models_module.class_for_model("Tesla Model S"), "sedan")
        self.assertEqual(car_models_module.class_for_model("Tesla Model X"), "suv")

    def test_judgment_call_spot_checks(self):
        cases = {
            # Wagons / hatchback sedans -> sedan.
            "Audi A6 Avant": "sedan", "Audi RS 6": "sedan", "Audi A7": "sedan",
            "Porsche Panamera": "sedan", "Porsche Taycan": "sedan",
            # Coupe-roof SUVs -> SUV.
            "BMW X6": "suv", "Mercedes-Benz GLC Coupe": "suv",
            "Mercedes-Benz GLE Coupe": "suv", "Porsche Cayenne Coupe": "suv",
            # Ambiguous names.
            "Audi e-tron": "suv", "Jeep Wagoneer S": "suv", "Lincoln MKT": "suv",
            # Compact crossovers -> SUV.
            "Audi Q4 e-tron": "suv", "BMW X3": "suv", "Cadillac Optiq": "suv",
            "Genesis GV60": "suv", "Lincoln Corsair": "suv",
            "Mercedes-Benz EQB": "suv", "Volvo XC60": "suv",
            # Plain sedans and SUVs.
            "Cadillac CT6": "sedan", "Lincoln Continental": "sedan",
            "Mercedes-Benz S-Class": "sedan", "Lucid Air": "sedan",
            "Cadillac Escalade": "suv", "Lincoln Navigator": "suv",
            "Rolls-Royce Cullinan": "suv", "Lamborghini Urus": "suv",
        }
        for model, expected in cases.items():
            self.assertEqual(car_models_module.class_for_model(model), expected, model)

    def test_unknown_model_returns_none(self):
        self.assertIsNone(car_models_module.class_for_model("Toyota Camry"))
        self.assertIsNone(car_models_module.class_for_model("Tesla Model Y"))
        self.assertIsNone(car_models_module.class_for_model(""))


class ClassApiCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, car_model):
        self._driver_seq += 1
        phone = f"+1555003{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Class Driver {self._driver_seq}", "phone": phone,
            "email": f"cd{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
            "plate": f"C{self._driver_seq:05d}",
            "state": "New York", "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "profile_photo": (io.BytesIO(photo_factory.VALID_PROFILE_PHOTO), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(b"fake png"), "license.png"),
            "doc_tlc_license": (io.BytesIO(b"fake png"), "tlc.png"),
            "doc_fh1": (io.BytesIO(b"fake png"), "fh1.png"),
            "doc_registration": (io.BytesIO(b"fake png"), "reg.png"),
            "doc_inspection": (io.BytesIO(b"fake png"), "insp.png"),
            "doc_vehicle_permit": (io.BytesIO(b"fake png"), "permit.png"),
        }, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        body = resp.get_json()
        self.client.post("/api/drivers/me/availability", json={"available": True},
                         headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Class Customer",
            "phone": f"+1555004{self._phone_seq:04d}",
            "email": "class@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)

    def owner_detail(self, booking_id):
        return self.client.get(f"/api/owner/bookings/{booking_id}").get_json()

    def switch_class(self, booking_id, vehicle_class):
        return self.client.post(f"/api/bookings/{booking_id}/vehicle-class",
                                json={"vehicle_class": vehicle_class})

    def complete_ride(self, booking_id, token):
        self.assertEqual(self.pay(booking_id).status_code, 200)
        resp = self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        for event in ("en_route", "arrived", "start", "complete"):
            resp = self.client.post(f"/api/drivers/me/trip/{booking_id}/event",
                                    json={"event": event},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")

    # -- options page: create + class selection ---------------------------
    def test_create_defaults_to_sedan_with_both_class_totals(self):
        booking = self.book()
        self.assertEqual(booking["status"], "awaiting_payment")
        self.assertEqual(booking["vehicle_class"], "sedan")
        self.assertEqual(booking["vehicle_class_label"], "Business Class")
        self.assertTrue(approx(booking["total"], "162.00"), booking)
        self.assertTrue(approx(booking["class_totals"]["sedan"], "162.00"), booking)
        self.assertTrue(approx(booking["class_totals"]["suv"], "180.00"), booking)
        got = self.client.get(f"/api/bookings/{booking['id']}").get_json()["booking"]
        self.assertEqual(got["vehicle_class"], "sedan")
        self.assertEqual(got["vehicle_class_label"], "Business Class")
        self.assertTrue(approx(got["class_totals"]["suv"], "180.00"), got)

    def test_hourly_booking_has_no_class_or_totals(self):
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Hourly", "phone": "+15550009992",
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": "2030-06-04", "time": "14:00",
            "ride_type": "hourly", "hours": 2})
        booking = resp.get_json()["booking"]
        self.assertIsNone(booking["vehicle_class"])
        self.assertIsNone(booking["vehicle_class_label"])
        self.assertNotIn("class_totals", booking)

    def test_class_switch_recomputes_totals_and_owner_breakdown(self):
        booking = self.book()
        resp = self.switch_class(booking["id"], "suv")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        switched = resp.get_json()["booking"]
        self.assertEqual(switched["vehicle_class"], "suv")
        self.assertEqual(switched["vehicle_class_label"], "Business SUV")
        self.assertTrue(approx(switched["total"], "180.00"), switched)
        self.owner_login()
        detail = self.owner_detail(booking["id"])
        self.assertEqual(detail["vehicle_class"], "suv")
        self.assertEqual(detail["vehicle_class_label"], "Business SUV")
        self.assertTrue(approx(detail["fare"], "180.00"), detail)
        self.assertTrue(approx(detail["gratuity"], "0.00"), detail)
        self.assertTrue(approx(detail["tax"], "0.00"), detail)
        self.assertTrue(approx(detail["driver_earnings"], "126.00"), detail)
        self.assertTrue(approx(detail["profit"], "54.00"), detail)
        # Switch back: sedan totals return exactly.
        resp = self.switch_class(booking["id"], "sedan")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(approx(resp.get_json()["booking"]["total"], "162.00"))
        detail = self.owner_detail(booking["id"])
        self.assertTrue(approx(detail["tax"], "0.00"), detail)
        self.assertTrue(approx(detail["profit"], "90.00"), detail)

    def test_class_switch_rejected_after_payment(self):
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.switch_class(booking["id"], "suv")
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])

    def test_class_switch_validation(self):
        booking = self.book()
        resp = self.switch_class(booking["id"], "luxury")
        self.assertEqual(resp.status_code, 400)
        resp = self.switch_class(booking["id"], None)
        self.assertEqual(resp.status_code, 400)
        resp = self.switch_class(999999, "suv")
        self.assertEqual(resp.status_code, 404)
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Hourly", "phone": "+15550009993",
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": "2030-06-04", "time": "14:00",
            "ride_type": "hourly", "hours": 2})
        hourly_id = resp.get_json()["booking"]["id"]
        resp = self.switch_class(hourly_id, "suv")
        self.assertEqual(resp.status_code, 409)

    # -- driver class derivation ------------------------------------------
    def test_driver_class_derived_on_registration(self):
        sedan_driver, sedan_token = self.register_driver("Cadillac CT6")
        self.assertEqual(sedan_driver["vehicle_class"], "sedan")
        self.assertEqual(sedan_driver["vehicle_class_label"], "Business Class")
        suv_driver, _ = self.register_driver("Cadillac Escalade")
        self.assertEqual(suv_driver["vehicle_class"], "suv")
        self.assertEqual(suv_driver["vehicle_class_label"], "Business SUV")
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": sedan_token}).get_json()["driver"]
        self.assertEqual(me["vehicle_class"], "sedan")
        self.assertEqual(me["vehicle_class_label"], "Business Class")
        self.owner_login()
        rows = self.client.get("/api/owner/drivers").get_json()
        by_phone = {r["phone"]: r for r in rows}
        self.assertEqual(by_phone[sedan_driver["phone"]]["vehicle_class_label"], "Business Class")
        self.assertEqual(by_phone[suv_driver["phone"]]["vehicle_class_label"], "Business SUV")

    # -- dispatch filtering -------------------------------------------------
    def test_dispatch_filtering_both_ways(self):
        _, sedan_token = self.register_driver("Cadillac CT6")
        _, suv_token = self.register_driver("Cadillac Escalade")
        sedan_booking = self.book()
        self.assertEqual(self.pay(sedan_booking["id"]).status_code, 200)
        suv_booking = self.book()
        self.assertEqual(self.switch_class(suv_booking["id"], "suv").status_code, 200)
        self.assertEqual(self.pay(suv_booking["id"]).status_code, 200)
        sedan_offers = self.client.get("/api/drivers/me/offers",
                                       headers={"X-Driver-Token": sedan_token}).get_json()
        suv_offers = self.client.get("/api/drivers/me/offers",
                                     headers={"X-Driver-Token": suv_token}).get_json()
        self.assertEqual([o["booking_id"] for o in sedan_offers], [sedan_booking["id"]])
        self.assertEqual([o["booking_id"] for o in suv_offers], [suv_booking["id"]])
        self.assertEqual(sedan_offers[0]["vehicle_class_label"], "Business Class")
        self.assertEqual(suv_offers[0]["vehicle_class_label"], "Business SUV")
        self.assertTrue(approx(sedan_offers[0]["earnings"], "72.00"))
        self.assertTrue(approx(suv_offers[0]["earnings"], "126.00"))

    def test_accept_enforces_class_match(self):
        _, sedan_token = self.register_driver("Cadillac CT6")
        _, suv_token = self.register_driver("Cadillac Escalade")
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                                headers={"X-Driver-Token": suv_token})
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                                headers={"X-Driver-Token": sedan_token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_hourly_reaches_drivers_of_both_classes(self):
        _, sedan_token = self.register_driver("Cadillac CT6")
        _, suv_token = self.register_driver("Cadillac Escalade")
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Hourly", "phone": "+15550009994",
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": "2030-06-04", "time": "14:00",
            "ride_type": "hourly", "hours": 2})
        hourly_id = resp.get_json()["booking"]["id"]
        self.assertEqual(self.pay(hourly_id).status_code, 200)
        for token in (sedan_token, suv_token):
            offers = self.client.get("/api/drivers/me/offers",
                                     headers={"X-Driver-Token": token}).get_json()
            self.assertEqual([o["booking_id"] for o in offers], [hourly_id])
            self.assertIsNone(offers[0]["vehicle_class"])

    # -- driver privacy ------------------------------------------------------
    def test_driver_payload_privacy_sweep(self):
        _, sedan_token = self.register_driver("Cadillac CT6")
        _, suv_token = self.register_driver("Cadillac Escalade")
        booking = self.book()
        self.switch_class(booking["id"], "suv")
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": suv_token}).get_json()
        self.assertEqual(len(offers), 1)
        self.assertFalse(FORBIDDEN_KEYS & set(offers[0]), str(offers[0]))
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                                headers={"X-Driver-Token": suv_token})
        trip = resp.get_json()["booking"]
        self.assertFalse(FORBIDDEN_KEYS & set(trip), str(trip))
        self.assertIn("earnings", trip)
        active = self.client.get("/api/drivers/me/active-trip",
                                 headers={"X-Driver-Token": suv_token}).get_json()["booking"]
        self.assertFalse(FORBIDDEN_KEYS & set(active), str(active))
        for event in ("en_route", "arrived", "start", "complete"):
            self.client.post(f"/api/drivers/me/trip/{booking['id']}/event",
                             json={"event": event}, headers={"X-Driver-Token": suv_token})
        earn = self.client.get("/api/drivers/me/earnings",
                               headers={"X-Driver-Token": suv_token}).get_json()
        for week in earn["weeks"]:
            self.assertFalse(FORBIDDEN_KEYS & set(week), str(week))
        for ride in earn["rides"]:
            self.assertFalse(FORBIDDEN_KEYS & set(ride), str(ride))
        self.assertTrue(approx(earn["total_earnings"], "126.00"))
        # The sedan driver never saw the SUV booking at all.
        self.assertEqual(self.client.get("/api/drivers/me/offers",
                                         headers={"X-Driver-Token": sedan_token}).get_json(), [])

    # -- owner reconciliation (no tax, no gratuity on new rides) -----------
    def test_owner_summary_reconciliation(self):
        _, sedan_token = self.register_driver("Cadillac CT6")
        _, suv_token = self.register_driver("Cadillac Escalade")
        b1 = self.book()
        self.complete_ride(b1["id"], sedan_token)
        b2 = self.book()
        self.switch_class(b2["id"], "suv")
        self.complete_ride(b2["id"], suv_token)
        self.owner_login()
        rows = {r["id"]: r for r in self.client.get("/api/owner/bookings").get_json()}
        for booking_id, fare, grat, tax, total, driver, profit in (
                (b1["id"], "162.00", "0.00", "0.00", "162.00", "72.00", "90.00"),
                (b2["id"], "180.00", "0.00", "0.00", "180.00", "126.00", "54.00")):
            row = rows[booking_id]
            self.assertTrue(approx(row["fare"], fare), row)
            self.assertTrue(approx(row["gratuity"], grat), row)
            self.assertTrue(approx(row["tax"], tax), row)
            self.assertTrue(approx(row["customer_total"], total), row)
            self.assertTrue(approx(row["driver_earnings"], driver), row)
            self.assertTrue(approx(row["profit"], profit), row)
            self.assertTrue(approx(D(str(row["customer_total"])) + D(str(row["waiting_charge"]))
                            - D(str(row["driver_earnings"])) - D(str(row["tax"])),
                            row["profit"]), row)
        summary = self.client.get("/api/owner/summary").get_json()
        self.assertTrue(approx(summary["gross"], "342.00"), summary)
        self.assertTrue(approx(summary["driver_owed"], "198.00"), summary)
        self.assertTrue(approx(summary["tax_collected"], "0.00"), summary)
        self.assertTrue(approx(summary["profit"],
                               D(str(summary["gross"])) - D(str(summary["driver_owed"]))), summary)

    def test_refunded_ride_excluded_from_gross_and_tax_collected(self):
        _, token = self.register_driver("Cadillac CT6")
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        with app_module.app.app_context():
            phone = app_module.db.session.get(app_module.Booking, booking["id"]).phone
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": phone})
        self.assertTrue(resp.get_json()["refund"])
        self.owner_login()
        summary = self.client.get("/api/owner/summary").get_json()
        self.assertTrue(approx(summary["tax_collected"], "0.00"), summary)
        self.assertTrue(approx(summary["gross"], "0.00"), summary)

    def test_toll_recompute_keeps_class_and_zero_tax(self):
        booking = self.book()
        self.switch_class(booking["id"], "suv")
        self.owner_login()
        resp = self.client.post(f"/api/owner/bookings/{booking['id']}/toll",
                                json={"toll": 18.50})
        self.assertEqual(resp.status_code, 200)
        row = resp.get_json()["booking"]
        self.assertEqual(row["vehicle_class"], "suv")
        self.assertTrue(approx(row["customer_total"], "198.50"), row)
        self.assertTrue(approx(row["driver_earnings"], "144.50"), row)
        self.assertTrue(approx(row["tax"], "0.00"), row)
        self.assertTrue(approx(row["fare"], "180.00"), row)

    def test_referral_code_gives_five_percent_off_via_api(self):
        first = self.book()
        code = first["referral_code"]
        self.assertTrue(code)
        referred = self.book(referral_code=code)
        self.assertTrue(approx(referred["total"], "153.90"), referred)
        resp = self.pay(referred["id"])
        self.assertTrue(approx(resp.get_json()["payment"]["amount"], "153.90"))

    # -- static copy: options page + no rates anywhere customer-facing -------
    def test_static_options_page_copy(self):
        with open(os.path.join(REPO_DIR, "static", "index.html"),
                  encoding="utf-8") as fh:
            index = fh.read()
        with open(os.path.join(REPO_DIR, "static", "js", "customer.js"),
                  encoding="utf-8") as fh:
            customer_js = fh.read()
        self.assertIn('id="book-submit">View options<', index)
        self.assertIn("Choose your experience", index)
        self.assertIn("Business Class", index)
        self.assertIn("Business SUV", index)
        self.assertIn('id="class-step"', index)
        self.assertIn('id="class-back"', index)
        self.assertIn("View options", customer_js)
        self.assertIn("/vehicle-class", customer_js)
        self.assertNotIn("Book a ride", index)
        self.assertNotIn("Book a ride", customer_js)

    def test_no_rates_or_breakdown_words_in_customer_driver_files(self):
        banned = [r"\$9", r"\$10", r"\$11", r"\$12", r"\$7", r"\$20", r"\$4", r"\$90", r"\$50",
                  "per mile", "booking fee", "gratuity", "dispatch"]
        files = ["static/index.html", "static/driver.html",
                 "static/css/customer.css", "static/css/driver.css",
                 "static/js/customer.js", "static/js/driver.js"]
        for rel in files:
            with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
                text = fh.read()
            for pat in banned:
                self.assertIsNone(re.search(pat, text), f"{rel}: banned {pat!r}")


if __name__ == "__main__":
    unittest.main()
