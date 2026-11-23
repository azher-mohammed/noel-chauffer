"""Tests for the First Class customer-facing wording.

Owner decision 2026-11-23 ~16:38 EST (voice call): the long First Class
model list ("Mercedes-Benz S-Class, BMW 7 Series, Audi A8, Tesla Model X,
Bentley Bentayga, Bentley Flying Spur, Bentley Mulsanne, Mercedes-Benz
Maybach S-Class, Rolls-Royce Cullinan, Rolls-Royce Ghost, Rolls-Royce
Phantom or Lamborghini Urus, or similar") does NOT need to be written
("yeh likhne ki zarurat nahi hai"). It reads instead, in the owner's
exact words: "a luxury first class, for up to 3 passengers with luggage."

These tests pin:
- No served customer page contains the model-list strings (Bentley
  Bentayga, Rolls-Royce Cullinan, Lamborghini Urus, Maybach S-Class,
  Flying Spur, Mulsanne) — visible copy AND FAQ JSON-LD.
- The owner's wording is present on every changed page, and the
  Business Class / Business SUV lines are untouched.
- No dangling "or similar" is left referring to the removed list.
- The dispatch rule is UNCHANGED: the twelve First Class models still
  qualify for First Class dispatch (car_models.FIRST_CLASS_MODELS) —
  only the customer-facing WORDS changed.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-firstclass-text-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "firstclass-text-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
import car_models as car_models_module  # noqa: E402

NEW_WORDING = "a luxury first class, for up to 3 passengers with luggage"

# Every page that carried the long First Class model list.
CHANGED_PAGES = [
    "/manhattan-car-service",
    "/brooklyn-car-service",
    "/queens-car-service",
    "/long-island-car-service",
    "/westchester-car-service",
    "/new-jersey-car-service",
    "/connecticut-car-service",
    "/hamptons-car-service",
    "/jfk-to-times-square",
    "/jfk-to-manhattan",
    "/laguardia-to-manhattan",
    "/newark-to-manhattan",
    "/valley-stream-to-jfk",
    "/jfk-to-brooklyn",
    "/jfk-airport-transfers",
    "/laguardia-airport-transfers",
    "/newark-airport-transfers",
    "/teterboro-airport-transfers",
    "/hourly-chauffeur-service",
    "/corporate-car-service",
    "/wedding-car-service",
    "/point-to-point-car-service",
    "/guides/black-car-vs-uber-black",
    "/guides/how-much-is-a-black-car-in-nyc",
]

# Model-list strings that must not appear in customer-facing copy.
FORBIDDEN = [
    "Bentley Bentayga",
    "Bentley Flying Spur",
    "Bentley Mulsanne",
    "Maybach S-Class",
    "Rolls-Royce Cullinan",
    "Rolls-Royce Ghost",
    "Rolls-Royce Phantom",
    "Lamborghini Urus",
    "Bentley",
    "Cullinan",
    "Maybach",
    "Urus",
    "Flying Spur",
    "Mulsanne",
]


class FirstClassTextCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app_module.app.test_client()

    def test_changed_pages_serve_200(self):
        for path in CHANGED_PAGES:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)

    def test_no_model_list_on_changed_pages(self):
        for path in CHANGED_PAGES:
            body = self.client.get(path).data.decode("utf-8")
            for needle in FORBIDDEN:
                self.assertNotIn(needle, body, f"{needle!r} on {path}")

    def test_owner_wording_present_on_changed_pages(self):
        for path in CHANGED_PAGES:
            body = self.client.get(path).data.decode("utf-8")
            self.assertIn(NEW_WORDING, body, path)

    def test_no_dangling_or_similar(self):
        for path in CHANGED_PAGES:
            body = self.client.get(path).data.decode("utf-8")
            self.assertNotIn("or similar", body, path)

    def test_business_lines_untouched(self):
        body = self.client.get("/manhattan-car-service").data.decode("utf-8")
        self.assertIn("a luxury sedan, for up to 3 passengers with luggage", body)
        self.assertIn("a luxury SUV, for more space and luggage", body)
        body = self.client.get("/guides/black-car-vs-uber-black").data.decode("utf-8")
        self.assertIn("Business Class is a luxury sedan", body)
        self.assertIn("Business SUV is a luxury SUV", body)

    def test_no_model_list_on_home_terms_and_apps(self):
        for path in ("/", "/app", "/driver", "/privacy", "/terms", "/guides"):
            body = self.client.get(path).data.decode("utf-8")
            for needle in ("Bentley Bentayga", "Rolls-Royce Cullinan",
                           "Lamborghini Urus", "Maybach S-Class"):
                self.assertNotIn(needle, body, f"{needle!r} on {path}")

    def test_first_class_dispatch_models_unchanged(self):
        # Only the WORDS changed: all twelve models still qualify
        # for First Class dispatch.
        models = car_models_module.FIRST_CLASS_MODELS
        for model in (
            "Mercedes-Benz S-Class",
            "BMW 7 Series",
            "Audi A8",
            "Tesla Model X",
            "Bentley Bentayga",
            "Bentley Flying Spur",
            "Bentley Mulsanne",
            "Mercedes-Benz Maybach S-Class",
            "Rolls-Royce Cullinan",
            "Rolls-Royce Ghost",
            "Rolls-Royce Phantom",
            "Lamborghini Urus",
        ):
            self.assertIn(model, models, model)
        self.assertEqual(len(models), 12)


if __name__ == "__main__":
    unittest.main()
