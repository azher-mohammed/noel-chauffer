"""Tests for First Class car models and dispatch.

Owner decision 2026-11-20 ~03:00 EST (voice call): First Class uses
the SAME cars as Blacklane — Mercedes-Benz S-Class, BMW 7 Series,
Audi A8, Tesla Model X ("or similar": the customer picks a CLASS,
the exact model is never guaranteed). Owner decision 2026-11-21
~01:44-01:48 EST (voice call): ADD eight flagships — Bentley
Bentayga, Flying Spur, Mulsanne; Mercedes-Benz Maybach S-Class;
Rolls-Royce Cullinan, Ghost, Phantom; Lamborghini Urus — so First
Class is TWELVE models. All twelve stay in Business Class too
("dono mein bhi rakhen"): a First Class booking reaches ONLY
drivers whose registered car is one of the twelve; every other
driver never sees it and cannot accept it even by direct API call.
The Model X is an SUV by body but classed Business Class since the
2026-11-21 Professional SUV change (only the 23 Uber Black SUV
models are SUVs), and so are the SUV-body Bentayga, Urus and
Cullinan, so their drivers keep their Business Class dispatch just
like an S-Class driver — First Class is an extra qualification
by model, not a replacement class.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-firstclass-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "firstclass-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
from car_models import (  # noqa: E402
    ALLOWED_CAR_MODELS,
    FIRST_CLASS_MODELS,
    allowed_models,
    class_for_model,
    is_first_class_model,
)

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "First Class Customer"}


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class FirstClassModelsCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, car_model="Mercedes-Benz S-Class"):
        self._driver_seq += 1
        phone = f"+1555011{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"FirstClass Driver {self._driver_seq}", "phone": phone,
            "email": f"fc{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
            "plate": f"F{self._driver_seq:05d}",
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
            "customer_name": "First Class Customer",
            "phone": f"+1555012{self._phone_seq:04d}",
            "email": "firstclass@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        if "@" in (payload.get("email") or "") and payload.get("phone"):
            self.signin(payload["email"], payload["phone"])
        return resp.get_json()["booking"]

    def book_first_class(self):
        """A paid First Class booking (Blacklane mode): create, pick
        First Class on the options page, pay. Returns the booking."""
        with mock.patch.dict(os.environ, {"NOEL_PRICING": "blacklane"}):
            booking = self.book()
            self.assertTrue(booking["first_class_bookable"])
            resp = self.client.post(
                f"/api/bookings/{booking['id']}/vehicle-class",
                json={"vehicle_class": "first"})
            self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
            resp = self.client.post(f"/api/bookings/{booking['id']}/pay", json=dict(CARD))
            self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return booking

    def offers(self, token):
        return self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token}).get_json()

    def offer_ids(self, token):
        return [o["booking_id"] for o in self.offers(token)]

    def accept(self, token, booking_id):
        return self.client.post(
            f"/api/drivers/me/offers/{booking_id}/accept",
            headers={"X-Driver-Token": token})

    def trip_event(self, token, booking_id, event, **extra):
        payload = {"event": event}
        payload.update(extra)
        return self.client.post(
            f"/api/drivers/me/trip/{booking_id}/event", json=payload,
            headers={"X-Driver-Token": token})

    # -- the model list --------------------------------------------------
    def test_first_class_models_are_exactly_the_twelve(self):
        # Blacklane's four (owner decision 2026-11-20) plus the eight
        # owner-added flagships (owner decision 2026-11-21).
        self.assertEqual(FIRST_CLASS_MODELS, {
            "Mercedes-Benz S-Class", "BMW 7 Series", "Audi A8",
            "Tesla Model X",
            "Bentley Bentayga", "Bentley Flying Spur",
            "Bentley Mulsanne", "Mercedes-Benz Maybach S-Class",
            "Rolls-Royce Cullinan", "Rolls-Royce Ghost",
            "Rolls-Royce Phantom", "Lamborghini Urus",
        })
        self.assertEqual(len(FIRST_CLASS_MODELS), 12)

    def test_new_first_class_models_stay_business_class(self):
        # DUAL eligibility ("dono mein bhi rakhen", owner decision
        # 2026-11-21): the eight new models keep their Business
        # Class ("sedan") mapping — including the SUV-body Bentayga,
        # Urus and Cullinan, since only the 23 Uber Black SUV models
        # are SUVs. Nothing was removed from Business.
        for model in ("Bentley Bentayga", "Bentley Flying Spur",
                      "Bentley Mulsanne", "Mercedes-Benz Maybach S-Class",
                      "Rolls-Royce Cullinan", "Rolls-Royce Ghost",
                      "Rolls-Royce Phantom", "Lamborghini Urus"):
            self.assertEqual(class_for_model(model), "sedan", model)

    def test_first_class_models_are_all_in_the_dropdown(self):
        # No dropdown addition was needed: all twelve are already on
        # the Uber Black list the dropdown serves.
        for model in FIRST_CLASS_MODELS:
            self.assertIn(model, ALLOWED_CAR_MODELS)
            self.assertIn(model, allowed_models())

    def test_is_first_class_model(self):
        for model in ("Mercedes-Benz S-Class", "BMW 7 Series",
                      "Audi A8", "Tesla Model X",
                      "Bentley Bentayga", "Bentley Flying Spur",
                      "Bentley Mulsanne", "Mercedes-Benz Maybach S-Class",
                      "Rolls-Royce Cullinan", "Rolls-Royce Ghost",
                      "Rolls-Royce Phantom", "Lamborghini Urus"):
            self.assertTrue(is_first_class_model(model), model)
        for model in ("Mercedes-Benz E-Class", "BMW 5 Series",
                      "Tesla Model S", "Tesla Model 3",
                      "Chevrolet Suburban", "Cadillac Escalade",
                      "bentley bentayga",
                      "", None):
            self.assertFalse(is_first_class_model(model), model)

    def test_class_label_for_first(self):
        from pricing import class_label
        self.assertEqual(class_label("first"), "First Class")

    # -- dispatch: offers --------------------------------------------------
    def test_first_class_offer_reaches_only_qualifying_drivers(self):
        _, s_token = self.register_driver("Mercedes-Benz S-Class")
        _, e_token = self.register_driver("Mercedes-Benz E-Class")
        _, x_token = self.register_driver("Tesla Model X")
        _, sub_token = self.register_driver("Chevrolet Suburban")
        booking = self.book_first_class()
        self.assertIn(booking["id"], self.offer_ids(s_token))
        self.assertIn(booking["id"], self.offer_ids(x_token))
        self.assertNotIn(booking["id"], self.offer_ids(e_token))
        self.assertNotIn(booking["id"], self.offer_ids(sub_token))
        # The offer card names the class it is.
        offer = [o for o in self.offers(s_token)
                 if o["booking_id"] == booking["id"]][0]
        self.assertEqual(offer["vehicle_class"], "first")
        self.assertEqual(offer["vehicle_class_label"], "First Class")

    def test_first_class_drivers_keep_their_business_dispatch(self):
        # S-Class (a sedan) still gets Business Class jobs; Model X
        # (Business Class since the 2026-11-21 Professional SUV
        # change — only the 23 Uber Black SUV models are SUVs) now
        # gets Business Class jobs too and no longer gets Business
        # SUV jobs — First Class is an extra qualification, not a
        # replacement class.
        _, s_token = self.register_driver("Mercedes-Benz S-Class")
        _, x_token = self.register_driver("Tesla Model X")
        _, sub_token = self.register_driver("Chevrolet Suburban")
        sedan = self.book()
        self.pay(sedan["id"])
        self.assertIn(sedan["id"], self.offer_ids(s_token))
        self.assertIn(sedan["id"], self.offer_ids(x_token))
        self.assertNotIn(sedan["id"], self.offer_ids(sub_token))
        suv = self.book()
        resp = self.client.post(
            f"/api/bookings/{suv['id']}/vehicle-class",
            json={"vehicle_class": "suv"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.pay(suv["id"])
        self.assertNotIn(suv["id"], self.offer_ids(s_token))
        self.assertNotIn(suv["id"], self.offer_ids(x_token))
        self.assertIn(suv["id"], self.offer_ids(sub_token))

    def test_new_first_class_models_get_first_and_business_offers(self):
        # DUAL dispatch (owner decision 2026-11-21): a Bentayga or
        # Ghost driver sees First Class jobs AND Business Class
        # (sedan) jobs — but no Business SUV jobs, since both are
        # "sedan" class. An E-Class driver sees the Business job
        # only, never the First Class one.
        _, b_token = self.register_driver("Bentley Bentayga")
        _, g_token = self.register_driver("Rolls-Royce Ghost")
        _, e_token = self.register_driver("Mercedes-Benz E-Class")
        first = self.book_first_class()
        self.assertIn(first["id"], self.offer_ids(b_token))
        self.assertIn(first["id"], self.offer_ids(g_token))
        self.assertNotIn(first["id"], self.offer_ids(e_token))
        sedan = self.book()
        self.pay(sedan["id"])
        self.assertIn(sedan["id"], self.offer_ids(b_token))
        self.assertIn(sedan["id"], self.offer_ids(g_token))
        self.assertIn(sedan["id"], self.offer_ids(e_token))
        suv = self.book()
        resp = self.client.post(
            f"/api/bookings/{suv['id']}/vehicle-class",
            json={"vehicle_class": "suv"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.pay(suv["id"])
        self.assertNotIn(suv["id"], self.offer_ids(b_token))
        self.assertNotIn(suv["id"], self.offer_ids(g_token))
        self.assertNotIn(suv["id"], self.offer_ids(e_token))

    def test_new_first_class_driver_can_accept(self):
        # A new-model driver can accept a First Class job by direct
        # API call; a non-qualifying driver still gets the 409.
        _, u_token = self.register_driver("Lamborghini Urus")
        _, e_token = self.register_driver("Mercedes-Benz E-Class")
        booking = self.book_first_class()
        resp = self.accept(e_token, booking["id"])
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn("First Class car", resp.get_json()["error"])
        resp = self.accept(u_token, booking["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def pay(self, booking_id):
        resp = self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return resp

    # -- dispatch: accept --------------------------------------------------
    def test_first_class_accept_refused_for_non_qualifying_driver(self):
        _, e_token = self.register_driver("Mercedes-Benz E-Class")
        _, s_token = self.register_driver("Mercedes-Benz S-Class")
        booking = self.book_first_class()
        resp = self.accept(e_token, booking["id"])
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        self.assertIn("First Class car", resp.get_json()["error"])
        # The qualifying driver takes it.
        resp = self.accept(s_token, booking["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def test_owner_assign_first_class_to_non_qualifying_driver_refused(self):
        e_driver, _ = self.register_driver("Mercedes-Benz E-Class")
        s_driver, _ = self.register_driver("Mercedes-Benz S-Class")
        booking = self.book_first_class()
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(
            f"/api/owner/bookings/{booking['id']}/assign",
            json={"driver_id": e_driver["id"]})
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])
        resp = self.client.post(
            f"/api/owner/bookings/{booking['id']}/assign",
            json={"driver_id": s_driver["id"]})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    # -- completion edge case ---------------------------------------------
    def test_extra_miles_refused_on_first_class_completion(self):
        _, s_token = self.register_driver("Mercedes-Benz S-Class")
        booking = self.book_first_class()
        resp = self.accept(s_token, booking["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        for event in ("en_route", "arrived", "start"):
            resp = self.trip_event(s_token, booking["id"], event)
            self.assertEqual(resp.status_code, 200,
                             f"{event}: {resp.get_data(as_text=True)[:200]}")
        # Extra miles have no First Class rate: refused cleanly, the
        # ride itself is unaffected.
        resp = self.trip_event(s_token, booking["id"], "complete",
                               extra_miles=2)
        self.assertEqual(resp.status_code, 400, resp.get_data(as_text=True)[:200])
        self.assertIn("Extra miles", resp.get_json()["error"])
        resp = self.trip_event(s_token, booking["id"], "complete")
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    # -- customer options page --------------------------------------------
    def test_class_choice_page_offers_first_class(self):
        website = read("static/index.html")
        self.assertIn('id="class-option-first"', website)
        self.assertIn("First Class", website)
        app_html = read("static/customer-app.html")
        self.assertIn('id="ca-class-option-first"', app_html)
        customer_js = read("static/js/customer.js")
        self.assertIn('first: "First Class"', customer_js)
        self.assertIn('["sedan", "suv", "first"]', customer_js)
        app_js = read("static/js/customer-app.js")
        self.assertIn('first: "First Class"', app_js)
        self.assertIn('["sedan", "suv", "first"]', app_js)


if __name__ == "__main__":
    unittest.main()
