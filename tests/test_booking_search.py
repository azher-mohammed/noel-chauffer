"""Tests for server-side booking search + pagination on the owner
dashboard (owner decision 2026-11-19, voice call): finding ONE trip
among 10,000 must be instant, without scrolling through rides.

GET /api/owner/bookings?q=...&page=...&per_page=... searches the
DATABASE (customer name, customer phone, pickup, drop-off, driver
name, booking number/ID, date, status) and returns only matching
rides, 50 per page, newest first. The dashboard and the owner app
load one page at a time and search on the server as he types
(300 ms debounce) — they never load all bookings at once.

A bare call (no ?q= and no ?page=) keeps returning the plain list,
so older callers keep working unchanged.

Run:  python -m unittest discover -s tests -v
"""


import io
import os
import re
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-search-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "search.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "search-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Search Customer"}
PHOTO_BYTES = photo_factory.VALID_PROFILE_PHOTO


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def read_app(rel):
    """Read a file from the owner app repo (separate checkout)."""
    with open(os.path.join(os.path.expanduser(
            "~/workspace/noel-chauffer-owner-app"), rel),
            encoding="utf-8") as fh:
        return fh.read()


class BookingSearchCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, name=None):
        self._driver_seq += 1
        phone = f"+1555007{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": name or f"Search Driver {self._driver_seq}", "phone": phone,
            "email": f"sd{self._driver_seq}@test.com",
            "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
            "plate": f"S{self._driver_seq:05d}",
            "state": "New York", "bank_account_number": "123456789", "bank_routing_number": "021000021",
            "expiry_dmv_license": "2030-01-01",
            "expiry_tlc_license": "2030-01-01",
            "expiry_fh1_insurance": "2030-01-01",
            "expiry_registration": "2030-01-01",
            "expiry_inspection": "2030-01-01",
            "expiry_vehicle_permit": "2030-01-01",
            "expiry_vehicle_registration": "2030-01-01",
            "expiry_insurance_card": "2030-01-01",
            "profile_photo": (io.BytesIO(PHOTO_BYTES), "photo.jpg"),
            "doc_dmv_license": (io.BytesIO(photo_factory.doc_photo()), "dmv.jpg"),
            "doc_tlc_license": (io.BytesIO(photo_factory.doc_photo()), "tlc.jpg"),
            "doc_fh1": (io.BytesIO(photo_factory.doc_photo()), "fh1.jpg"),
            "doc_registration": (io.BytesIO(photo_factory.doc_photo()), "reg.jpg"),
            "doc_inspection": (io.BytesIO(photo_factory.doc_photo()), "insp.jpg"),
            "doc_vehicle_permit": (io.BytesIO(photo_factory.doc_photo()), "permit.jpg"),
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
            "customer_name": "Search Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "search@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking = resp.get_json()["booking"]
        booking["phone"] = payload["phone"]
        self.signin(payload["email"], payload["phone"])
        return booking

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def owner_login(self, client=None):
        resp = (client or self.client).post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])

    def search(self, **params):
        self.owner_login()
        resp = self.client.get("/api/owner/bookings", query_string=params)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return resp.get_json()

    def set_status(self, booking_id, status):
        with app_module.app.app_context():
            booking = app_module.db.session.get(app_module.Booking, booking_id)
            booking.status = status
            app_module.db.session.commit()

    def seed_searchable_rides(self):
        """Five rides with distinct values in every searchable field,
        plus one accepted by driver one and one assigned to driver two.
        Returns (driver1, driver2, rides)."""
        driver1, token1 = self.register_driver("Aarav Sharma")
        driver2, _token2 = self.register_driver("Bilal Qureshi")
        rides = [
            self.book(customer_name="Priya Nair", phone="+15550081111",
                      pickup="JFK Airport Terminal 4", dropoff="Times Square, New York",
                      date="2030-06-01", time="09:00"),
            self.book(customer_name="Omar Farouk", phone="+15550082222",
                      pickup="LaGuardia Airport", dropoff="Brooklyn Bridge Park",
                      date="2030-06-02", time="10:00"),
            self.book(customer_name="Lena Fischer", phone="+15550083333",
                      pickup="Newark Airport", dropoff="Central Park South",
                      date="2030-06-03", time="11:00"),
            self.book(customer_name="Raj Patel", phone="+15550084444",
                      pickup="Valley Stream", dropoff="Stamford Station",
                      date="2030-06-04", time="12:00"),
            self.book(customer_name="Maya Chen", phone="+15550085555",
                      pickup="JFK Airport Terminal 1", dropoff="Wall Street",
                      date="2030-06-05", time="13:00"),
        ]
        # Ride 0: accepted by Aarav Sharma. Ride 1: assigned to Bilal Qureshi.
        self.assertEqual(self.pay(rides[0]["id"]).status_code, 200)
        resp = self.client.post(
            f"/api/drivers/me/offers/{rides[0]['id']}/accept", json={},
            headers={"X-Driver-Token": token1})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(self.pay(rides[1]["id"]).status_code, 200)
        self.owner_login()
        resp = self.client.post(
            f"/api/owner/bookings/{rides[1]['id']}/assign",
            json={"driver_id": driver2["id"]})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        # Distinct statuses for the status search.
        self.set_status(rides[2]["id"], "completed")
        self.set_status(rides[3]["id"], "cancelled")
        return driver1, driver2, rides

    # -- auth ---------------------------------------------------------------
    def test_search_requires_owner_login(self):
        resp = self.client.get("/api/owner/bookings", query_string={"q": "JFK"})
        self.assertEqual(resp.status_code, 401)

    # -- backward compatibility --------------------------------------------
    def test_no_params_returns_plain_list(self):
        self.book()
        self.book()
        self.owner_login()
        resp = self.client.get("/api/owner/bookings")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 2)

    # -- one field at a time -------------------------------------------------
    def test_search_by_customer_name(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="Priya")
        self.assertEqual([b["id"] for b in found["bookings"]], [rides[0]["id"]])

    def test_search_by_phone(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="+15550083333")
        self.assertEqual([b["id"] for b in found["bookings"]], [rides[2]["id"]])

    def test_search_by_pickup(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="LaGuardia")
        self.assertEqual([b["id"] for b in found["bookings"]], [rides[1]["id"]])

    def test_search_by_dropoff(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="Stamford")
        self.assertEqual([b["id"] for b in found["bookings"]], [rides[3]["id"]])

    def test_search_by_driver_name_accepted(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="Aarav")
        self.assertEqual([b["id"] for b in found["bookings"]], [rides[0]["id"]])

    def test_search_by_driver_name_assigned(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="Bilal")
        self.assertEqual([b["id"] for b in found["bookings"]], [rides[1]["id"]])

    def test_search_by_booking_id(self):
        # A single ride whose other fields contain no "1", so only
        # the booking-number match can hit it.
        ride = self.book(customer_name="Test User", phone="+15550082222",
                         pickup="JFK Airport", dropoff="Times Square",
                         date="2030-06-02", time="09:00")
        target = ride["id"]
        self.assertEqual(target, 1)
        found = self.search(q=str(target))
        self.assertEqual([b["id"] for b in found["bookings"]], [target])
        # "#123" form, as shown on the dashboard.
        found = self.search(q="#" + str(target))
        self.assertEqual([b["id"] for b in found["bookings"]], [target])

    def test_search_by_date(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="2030-06-04")
        self.assertEqual([b["id"] for b in found["bookings"]], [rides[3]["id"]])

    def test_search_by_status(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="completed")
        self.assertEqual([b["id"] for b in found["bookings"]], [rides[2]["id"]])
        found = self.search(q="cancelled")
        self.assertEqual([b["id"] for b in found["bookings"]], [rides[3]["id"]])

    def test_search_is_case_insensitive(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="jfk airport")
        self.assertEqual(
            sorted(b["id"] for b in found["bookings"]),
            sorted([rides[0]["id"], rides[4]["id"]]))

    def test_search_no_match_returns_empty_page(self):
        self.seed_searchable_rides()
        found = self.search(q="zzz-no-such-place")
        self.assertEqual(found["bookings"], [])
        self.assertEqual(found["total"], 0)
        self.assertEqual(found["pages"], 0)

    # -- pagination -----------------------------------------------------------
    def test_pagination_pages_and_newest_first(self):
        for _ in range(7):
            self.book()
        page1 = self.search(page=1, per_page=3)
        self.assertEqual(page1["total"], 7)
        self.assertEqual(page1["pages"], 3)
        self.assertEqual(page1["per_page"], 3)
        self.assertEqual(len(page1["bookings"]), 3)
        page2 = self.search(page=2, per_page=3)
        self.assertEqual(len(page2["bookings"]), 3)
        page3 = self.search(page=3, per_page=3)
        self.assertEqual(len(page3["bookings"]), 1)
        # Newest first: ids strictly descending across the pages.
        ids = ([b["id"] for b in page1["bookings"]]
               + [b["id"] for b in page2["bookings"]]
               + [b["id"] for b in page3["bookings"]])
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_pagination_defaults_50_per_page(self):
        for _ in range(3):
            self.book()
        found = self.search(page=1)
        self.assertEqual(found["per_page"], 50)
        self.assertEqual(found["total"], 3)
        self.assertEqual(len(found["bookings"]), 3)

    def test_pagination_clamps(self):
        for _ in range(3):
            self.book()
        # per_page above the cap is clamped to 100.
        found = self.search(page=1, per_page=500)
        self.assertEqual(found["per_page"], 100)
        # A page past the end is clamped to the last page with rows.
        found = self.search(page=99, per_page=2)
        self.assertEqual(found["page"], 2)
        self.assertEqual(len(found["bookings"]), 1)
        # Junk values fall back to the defaults, never 500.
        found = self.search(page="abc", per_page="xyz")
        self.assertEqual(found["page"], 1)
        self.assertEqual(found["per_page"], 50)

    def test_search_combined_with_pagination(self):
        _d1, _d2, rides = self.seed_searchable_rides()
        found = self.search(q="JFK", page=1, per_page=1)
        self.assertEqual(found["total"], 2)
        self.assertEqual(found["pages"], 2)
        self.assertEqual(len(found["bookings"]), 1)
        found2 = self.search(q="JFK", page=2, per_page=1)
        self.assertEqual(len(found2["bookings"]), 1)
        self.assertNotEqual(
            found["bookings"][0]["id"], found2["bookings"][0]["id"])

    # -- dashboard + owner app wiring ----------------------------------------
    def test_dashboard_search_box_and_pager_present(self):
        html = read("static/owner.html")
        self.assertIn('id="bookings-search"', html)
        # The placeholder names every searchable field.
        for field in ("customer", "phone", "pickup", "drop-off",
                      "driver", "booking #", "date", "status"):
            self.assertIn(field, html)
        self.assertIn('id="bookings-pager"', html)
        self.assertIn('id="bookings-prev"', html)
        self.assertIn('id="bookings-next"', html)
        self.assertIn('id="bookings-page-info"', html)
        js = read("static/js/owner.js")
        # Server-side search: the dashboard asks for a page with ?q=
        # (debounced 300 ms as he types) instead of loading all rows.
        self.assertIn("per_page=", js)
        self.assertIn('"&q="', js)
        self.assertIn("setTimeout", js)
        self.assertIn("300", js)
        self.assertIn("bookings-prev", js)
        self.assertIn("bookings-next", js)
        self.assertIn("No rides match that search.", js)
        # The owner app searches on the server too.
        app_js = read_app("src/api/client.ts")
        self.assertIn("getOwnerBookings", app_js)
        self.assertIn("params.set('q'", app_js)
        self.assertIn("params.set('page'", app_js)
        rides_tsx = read_app("src/app/(tabs)/rides.tsx")
        self.assertIn("debouncedQuery", rides_tsx)
        self.assertIn("getOwnerBookings({ q: debouncedQuery, page })", rides_tsx)
        self.assertIn("Page {effectivePage} of", rides_tsx)
        # No client-side filtering over a full list in the app anymore.
        self.assertNotIn("hay.includes", rides_tsx)


if __name__ == "__main__":
    unittest.main()
