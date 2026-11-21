"""Tests for vehicle classes + new pricing (decided 2026-11-16; tax
and gratuity removed by owner orders 2026-11-17).

Settled rules under test:
- TWO classes only: sedan (Business Class) $9/mile, SUV (Business
  SUV) $10/mile. NO booking fee. Driver: FLAT slab pay by distance
  (owner decision 2026-11-20) + toll, NOT per mile.
- NO tax, NO gratuity on any new booking. Toll passed to the driver.
  Total = fare + toll. Profit = total - driver earnings.
- Referral codes give 5% off a new customer's first one-way booking
  (owner decision 2026-11-18); driver pay unchanged. Hourly unchanged.
- The customer picks a class on the separate "Choose your experience"
  page before paying; dispatch is filtered by class; driver payloads
  never carry miles, fare, tax, total, gratuity, or fee keys.

Run:  python -m unittest discover -s tests -v
"""

import hashlib
import io
import os
import re
import sys
import tempfile
import unittest
from unittest import mock
from decimal import Decimal

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-class-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "class.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
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
    ("10.0", "sedan"): ("90.00", "0.00", "0.00", "90.00", "80.00", "10.00"),
    ("10.0", "suv"): ("100.00", "0.00", "0.00", "100.00", "90.00", "10.00"),
    ("18.0", "sedan"): ("162.00", "0.00", "0.00", "162.00", "95.00", "67.00"),
    ("18.0", "suv"): ("180.00", "0.00", "0.00", "180.00", "130.00", "50.00"),
    ("20.0", "sedan"): ("180.00", "0.00", "0.00", "180.00", "95.00", "85.00"),
    ("20.0", "suv"): ("200.00", "0.00", "0.00", "200.00", "130.00", "70.00"),
    ("35.0", "sedan"): ("315.00", "0.00", "0.00", "315.00", "140.00", "175.00"),
    ("35.0", "suv"): ("350.00", "0.00", "0.00", "350.00", "160.00", "190.00"),
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
                          D("130.00"), D("70.00")))
        sedan = compute_one_way(D("20.0"), vehicle_class="sedan")
        self.assertEqual((sedan["fare"], sedan["gratuity"], sedan["tax"], sedan["total"],
                          sedan["driver_earnings"], sedan["profit"]),
                         (D("180.00"), D("0.00"), D("0.00"), D("180.00"),
                          D("95.00"), D("85.00")))

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
        # Flat slab pay (owner decision 2026-11-20): 0-10 $80/$90,
        # 10-20 $95/$130, 20-30 $125/$160, 30-40 $140/$160.
        for miles, sedan_pay, suv_pay in (("10.0", "80.00", "90.00"),
                                          ("18.0", "95.00", "130.00"),
                                          ("20.0", "95.00", "130.00"),
                                          ("35.0", "140.00", "160.00")):
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

    def test_hourly_per_class_totals(self):
        # Blacklane-style hourly (owner decision 2026-11-20): the
        # customer picks a class; each class has its own hourly rate
        # (2-hour totals Business $218.32, SUV $269.46, First $343.31).
        r = compute_hourly(3, "sedan")
        self.assertEqual(r["total"], D("327.48"))
        self.assertEqual(r["driver_earnings"], D("180.00"))
        self.assertEqual(r["booking_fee"], D("0.00"))
        self.assertEqual(r["gratuity"], D("0.00"))
        self.assertEqual(r["tax"], D("0.00"))
        self.assertEqual(r["vehicle_class"], "sedan")
        self.assertEqual(compute_hourly(2, "suv")["total"], D("269.46"))
        self.assertEqual(compute_hourly(2, "first")["total"], D("343.31"))

    def test_class_totals_helper(self):
        totals = compute_class_totals(D("20.0"))
        self.assertEqual(totals, {"sedan": D("180.00"), "suv": D("200.00")})
        totals = compute_class_totals(D("18.0"), toll=D("10.00"))
        self.assertEqual(totals, {"sedan": D("172.00"), "suv": D("190.00")})

    def test_class_display_names(self):
        self.assertEqual(CLASS_LABELS, {"sedan": "Business Class",
                                        "suv": "Business SUV",
                                        "first": "First Class"})
        self.assertEqual(class_label("sedan"), "Business Class")
        self.assertEqual(class_label("suv"), "Business SUV")
        self.assertEqual(class_label("first"), "First Class")
        self.assertIsNone(class_label(None))


class TestModelClassMapping(unittest.TestCase):
    def test_all_133_models_mapped_to_exactly_one_class(self):
        mapping = car_models_module.VEHICLE_CLASS_BY_MODEL
        # The mapping covers every known model (132 + Model 3), even
        # though the dropdown hides Model 3 from most drivers
        # (owner decision 2026-11-19).
        self.assertEqual(set(mapping), set(car_models_module.ALLOWED_CAR_MODELS))
        self.assertEqual(len(mapping), 133)
        for model, cls in mapping.items():
            self.assertIn(cls, ("sedan", "suv"), model)

    def test_mapping_counts(self):
        values = list(car_models_module.VEHICLE_CLASS_BY_MODEL.values())
        # Owner decision 2026-11-21: only the 23 Uber Black SUV
        # models are SUVs; the other 62 SUV-body models are Business
        # Class ("sedan") and stay in the dropdown. 109 sedans of the
        # 132 Uber Black models + the Model 3 exception = 110.
        self.assertEqual(values.count("suv"), 23)
        self.assertEqual(values.count("sedan"), 110)

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
        # Owner decision 2026-11-21: Model X is Business Class now —
        # only the 23 Uber Black SUV models are SUVs. It stays
        # First-eligible by model (see test_first_class_models.py).
        self.assertEqual(car_models_module.class_for_model("Tesla Model X"), "sedan")

    def test_judgment_call_spot_checks(self):
        # Owner decision 2026-11-21: the SUV class is EXACTLY the 23
        # Uber Black SUV models; every other SUV-body model is
        # Business Class ("sedan") and stays in the dropdown.
        cases = {
            # Wagons / hatchback sedans -> sedan.
            "Audi A6 Avant": "sedan", "Audi RS 6": "sedan", "Audi A7": "sedan",
            "Porsche Panamera": "sedan", "Porsche Taycan": "sedan",
            # Coupe-roof SUVs -> sedan now.
            "BMW X6": "sedan", "Mercedes-Benz GLC Coupe": "sedan",
            "Mercedes-Benz GLE Coupe": "sedan", "Porsche Cayenne Coupe": "sedan",
            # Ambiguous names -> sedan now (MKT is one of the 23).
            "Audi e-tron": "sedan", "Jeep Wagoneer S": "sedan", "Lincoln MKT": "suv",
            # Compact crossovers -> sedan now.
            "Audi Q4 e-tron": "sedan", "BMW X3": "sedan", "Cadillac Optiq": "sedan",
            "Genesis GV60": "sedan", "Lincoln Corsair": "sedan",
            "Mercedes-Benz EQB": "sedan", "Volvo XC60": "sedan",
            # Big SUV bodies that are NOT Uber Black SUV -> sedan now.
            "Rolls-Royce Cullinan": "sedan", "Lamborghini Urus": "sedan",
            "Tesla Model X": "sedan", "Land Rover Range Rover": "sedan",
            # Plain sedans stay sedan; the 23 stay SUV.
            "Cadillac CT6": "sedan", "Lincoln Continental": "sedan",
            "Mercedes-Benz S-Class": "sedan", "Lucid Air": "sedan",
            "Cadillac Escalade": "suv", "Lincoln Navigator": "suv",
        }
        for model, expected in cases.items():
            self.assertEqual(car_models_module.class_for_model(model), expected, model)

    def test_unknown_model_returns_none(self):
        self.assertIsNone(car_models_module.class_for_model("Toyota Camry"))
        self.assertIsNone(car_models_module.class_for_model("Tesla Model Y"))
        self.assertIsNone(car_models_module.class_for_model(""))


# These tests pin the legacy $9/$10 totals as their fixtures (the
# class-switch and discount mechanics are engine-independent); the
# live engine is Blacklane by default since the owner flip
# (2026-11-20).
@mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"})
class ClassApiCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
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
        self.assertNotIn("class_totals", got)
        self.assertNotIn("total", got)

    def test_hourly_booking_carries_class_and_no_class_totals(self):
        # Blacklane-style hourly (owner decision 2026-11-20): the
        # customer picks a class on the form; the booking carries it
        # and is priced per class (2h Business $218.32). One-way
        # class totals are a one-way concept only.
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Hourly", "phone": "+15550009992",
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": "2030-06-04", "time": "14:00",
            "ride_type": "hourly", "hours": 2, "vehicle_class": "sedan"})
        booking = resp.get_json()["booking"]
        self.assertEqual(booking["vehicle_class"], "sedan")
        self.assertEqual(booking["vehicle_class_label"], "Business Class")
        self.assertTrue(approx(booking["total"], "218.32"), booking)
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
        self.assertTrue(approx(detail["driver_earnings"], "130.00"), detail)
        self.assertTrue(approx(detail["profit"], "50.00"), detail)
        # Switch back: sedan totals return exactly.
        resp = self.switch_class(booking["id"], "sedan")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(approx(resp.get_json()["booking"]["total"], "162.00"))
        detail = self.owner_detail(booking["id"])
        self.assertTrue(approx(detail["tax"], "0.00"), detail)
        self.assertTrue(approx(detail["profit"], "67.00"), detail)

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
        # Hourly bookings CAN switch class before payment now
        # (Blacklane-style hourly, owner decision 2026-11-20): the
        # class is picked on the form and may be changed on the
        # options page while still awaiting payment.
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Hourly", "phone": "+15550009993",
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": "2030-06-04", "time": "14:00",
            "ride_type": "hourly", "hours": 2, "vehicle_class": "sedan"})
        hourly_id = resp.get_json()["booking"]["id"]
        resp = self.switch_class(hourly_id, "suv")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        switched = resp.get_json()["booking"]
        self.assertEqual(switched["vehicle_class"], "suv")
        self.assertEqual(switched["vehicle_class_label"], "Business SUV")
        self.assertTrue(approx(switched["total"], "269.46"), switched)

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

    def test_existing_driver_reclasses_when_mapping_changes(self):
        # Owner decision 2026-11-21: a BMW X5 is Business Class now.
        # A driver registered before the change has "suv" stored for
        # it; the stored value must not keep him an SUV — the class
        # is derived from the car model on read.
        driver, token = self.register_driver("BMW X5")
        self.assertEqual(driver["vehicle_class"], "sedan")
        with app_module.app.app_context():
            row = app_module.Driver.query.filter_by(phone=driver["phone"]).first()
            row.vehicle_class = "suv"  # as stored before the change
            app_module.db.session.commit()
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": token}).get_json()["driver"]
        self.assertEqual(me["vehicle_class"], "sedan")
        self.assertEqual(me["vehicle_class_label"], "Business Class")
        # And he no longer gets SUV offers, only Business Class ones.
        booking = self.book()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        offers = self.client.get("/api/drivers/me/offers",
                                 headers={"X-Driver-Token": token}).get_json()
        self.assertEqual([o["booking_id"] for o in offers], [booking["id"]])

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
        self.assertNotIn("earnings", sedan_offers[0])
        self.assertNotIn("toll", sedan_offers[0])
        self.assertNotIn("earnings", suv_offers[0])
        self.assertNotIn("toll", suv_offers[0])

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

    def test_hourly_dispatch_is_filtered_by_class(self):
        # Blacklane-style hourly (owner decision 2026-11-20): an
        # hourly booking reaches only drivers whose car class matches
        # the class the customer picked — like one-way rides.
        _, sedan_token = self.register_driver("Mercedes-Benz E-Class")
        _, suv_token = self.register_driver("Cadillac Escalade")
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Hourly Sedan", "phone": "+15550009994",
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": "2030-06-04", "time": "14:00",
            "ride_type": "hourly", "hours": 2, "vehicle_class": "sedan"})
        sedan_hourly_id = resp.get_json()["booking"]["id"]
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Hourly SUV", "phone": "+15550009995",
            "email": "hourly@test.com", "pickup": "Central Park, New York",
            "date": "2030-06-04", "time": "16:00",
            "ride_type": "hourly", "hours": 2, "vehicle_class": "suv"})
        suv_hourly_id = resp.get_json()["booking"]["id"]
        self.assertEqual(self.pay(sedan_hourly_id).status_code, 200)
        self.assertEqual(self.pay(suv_hourly_id).status_code, 200)
        sedan_offers = self.client.get("/api/drivers/me/offers",
                                       headers={"X-Driver-Token": sedan_token}).get_json()
        self.assertEqual([o["booking_id"] for o in sedan_offers], [sedan_hourly_id])
        self.assertEqual(sedan_offers[0]["vehicle_class"], "sedan")
        suv_offers = self.client.get("/api/drivers/me/offers",
                                     headers={"X-Driver-Token": suv_token}).get_json()
        self.assertEqual([o["booking_id"] for o in suv_offers], [suv_hourly_id])
        self.assertEqual(suv_offers[0]["vehicle_class"], "suv")
        # A sedan driver cannot accept the SUV hourly job.
        resp = self.client.post(f"/api/drivers/me/offers/{suv_hourly_id}/accept",
                                headers={"X-Driver-Token": sedan_token})
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
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
        self.assertNotIn("earnings", trip)
        self.assertNotIn("toll", trip)
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
        self.assertNotIn("total_earnings", earn)
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
                (b1["id"], "162.00", "0.00", "0.00", "162.00", "95.00", "67.00"),
                (b2["id"], "180.00", "0.00", "0.00", "180.00", "130.00", "50.00")):
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
        self.assertTrue(approx(summary["driver_owed"], "225.00"), summary)
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
        self.assertTrue(approx(row["driver_earnings"], "148.50"), row)
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

    def test_class_step_shows_included_and_breakdown(self):
        # Blacklane-style options page (owner decision 2026-11-20):
        # what's included under every class, and the selected
        # class's fare breakdown (base fare + fees + tax). No
        # per-mile rates, no driver pay, no miles anywhere in it.
        with open(os.path.join(REPO_DIR, "static", "index.html"),
                  encoding="utf-8") as fh:
            index = fh.read()
        with open(os.path.join(REPO_DIR, "static", "js", "customer.js"),
                  encoding="utf-8") as fh:
            customer_js = fh.read()
        for text in ("Price breakdown", 'id="class-breakdown"',
                     "car-business.jpg", "car-suv.jpg", "car-first.jpg",
                     "class-option-car"):
            self.assertIn(text, index, "options page must show %r" % text)
        for text in ("classBreakdowns", "class-breakdown", "Base fare",
                     "Airport access fee", "NY State congestion surcharge",
                     "MTA congestion surcharge", "Sales tax",
                     "Black car fee", "Referral discount"):
            self.assertIn(text, customer_js,
                          "customer.js must paint %r" % text)
        # The breakdown painter must never touch driver pay or profit.
        self.assertNotIn("driver_earnings", customer_js)
        self.assertNotIn("profit", customer_js)

    def test_no_rates_or_breakdown_words_in_customer_driver_files(self):
        # Customer rates and breakdown words must appear nowhere
        # customer- or driver-facing.
        banned_everywhere = [r"\$9", r"\$10", r"\$11", r"\$12", r"\$20", r"\$90", r"\$50",
                             "booking fee", "gratuity", "dispatch"]
        # Driver pay ($4/$6 per mile) is banned everywhere too:
        # owner decision 2026-11-20 removed the displayed driver
        # per-mile rates from the driver page (they were stated
        # there before, owner decision 2026-11-18); new prices
        # will be added later. Backend pricing logic is untouched.
        banned_everywhere += [r"\$7", r"\$4", "per mile"]
        files = ["static/index.html", "static/driver.html",
                 "static/css/customer.css", "static/css/driver.css",
                 "static/js/customer.js", "static/js/driver.js"]
        for rel in files:
            with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
                text = fh.read()
            for pat in banned_everywhere:
                self.assertIsNone(re.search(pat, text), f"{rel}: banned {pat!r}")


    def test_class_car_photos_show_noel_chauffer_plates(self):
        # Owner order 2026-11-21: the number plates visible on the
        # three class-card photos must read "Noel Chauffer" (branded
        # show plate), not the stock photos' real numbers
        # ("S-Class" show plate, German "M AG 350", Finnish
        # "BM-762"). The plate shape stays; only the text changed.
        # The files must differ from the original Wikimedia
        # downloads, each plate region must still carry visible
        # markings (the branded text — not blanked or blurred out),
        # and no blue EU-strip pixel may remain in a plate area.
        try:
            from PIL import Image, ImageStat
        except ImportError:
            self.skipTest("Pillow not installed")
        original_sha256 = {
            "car-business.jpg":
                "813567c000ca11146d2e232c114f5147f72993740f59c8a307d8f8641d4862ba",
            "car-suv.jpg":
                "478074f3d2dabad00b9d0e68605b6e40c847bc3df9a0f38d8cd9690994899c0a",
            "car-first.jpg":
                "1601c67dc357a7408494b966c8adbcd2754fffcbf803283b93975607094db17f",
        }
        # Bounding boxes of the (tilted) plate polygons.
        plate_boxes = {
            "car-business.jpg": (64, 176, 142, 202),
            "car-suv.jpg": (324, 400, 452, 440),
            "car-first.jpg": (76, 292, 224, 336),
        }
        for name, original_hash in original_sha256.items():
            path = os.path.join(REPO_DIR, "static", "img", name)
            with open(path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            self.assertNotEqual(
                digest, original_hash,
                "%s must differ from the original stock photo" % name)
            img = Image.open(path).convert("RGB")
            box = plate_boxes[name]
            plate = img.crop(box).convert("L")
            stddev = ImageStat.Stat(plate).stddev[0]
            self.assertGreater(
                stddev, 20,
                "%s plate region must carry visible text, not a blank" % name)
            blue_left = 0
            for y in range(box[1], box[3]):
                for x in range(box[0], box[2]):
                    r, g, b = img.getpixel((x, y))
                    if b > 100 and b - r > 50 and b - g > 30:
                        blue_left += 1
            self.assertEqual(
                blue_left, 0,
                "%s plate area must not keep any EU-strip blue" % name)


if __name__ == "__main__":
    unittest.main()
