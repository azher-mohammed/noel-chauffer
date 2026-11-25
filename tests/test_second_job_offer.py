"""Tests for the second-job card on the driver trip screen.

Owner order 2026-11-25 (voice call, "Tum hi bool larlo" / "kaisa
adjust karte karo"): while a driver is on a job, a new job arrived
but ONLY the chime played — no card showed, and the driver could
not see or accept the second job. Root cause: offers were only
polled on the home screen, and not at all during a trip.

NOW:
- Offers are polled on the trip screen too, at every stage, and
  the card shows under the current trip (pickup, drop-off, time,
  class, Accept / Decline) without disturbing the current trip.
- Accepting a second job mid-trip queues it as the next job: the
  current trip keeps running untouched, and when it ends the queued
  job becomes the active trip.
- The no-double-booking rule (owner decision 2026-11-16) is
  unchanged: an overlapping second job stays hidden from offers and
  its accept is still rejected with 409 — on the home screen and
  mid-trip alike.
- After a reload mid-trip, the started trip (not the queued job) is
  restored as the current trip.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-secondjob-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "secondjob-secret-key"
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
        "card_cvc": "123", "card_name": "Second Job Customer"}


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def extract_function(source, signature):
    """Extract a `function NAME(...) {...}` body from JS source by
    balanced-brace scanning. The extracted functions contain no braces
    inside strings, so a plain counter is exact."""
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unbalanced braces in " + signature)


class SecondJobOfferCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers ---------------------------------------------------------
    def register_driver(self, available=False, car_model="Cadillac CT6"):
        self._driver_seq += 1
        phone = f"+1555007{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"SecondJob Driver {self._driver_seq}", "phone": phone,
            "email": f"sj{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
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
        if available:
            self.client.post("/api/drivers/me/availability", json={"available": True},
                             headers={"X-Driver-Token": body["token"]})
        return body["driver"], body["token"]

    def signin(self, email, phone):
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Second Job Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "secondjob@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        if "@" in (payload.get("email") or "") and payload.get("phone"):
            self.signin(payload["email"], payload["phone"])
        return resp.get_json()["booking"]

    def pay(self, booking_id):
        resp = self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return resp

    def offers(self, token):
        return self.client.get("/api/drivers/me/offers",
                               headers={"X-Driver-Token": token}).get_json()

    def offer_ids(self, token):
        return [o["booking_id"] for o in self.offers(token)]

    def accept(self, token, booking_id):
        return self.client.post(
            f"/api/drivers/me/offers/{booking_id}/accept",
            headers={"X-Driver-Token": token})

    def next_jobs(self, token):
        return self.client.get("/api/drivers/me/next-jobs",
                               headers={"X-Driver-Token": token}).get_json()

    def next_job_ids(self, token):
        return [o["booking_id"] for o in self.next_jobs(token)]

    def active_trip(self, token):
        body = self.client.get("/api/drivers/me/active-trip",
                               headers={"X-Driver-Token": token}).get_json()
        return (body or {}).get("booking")

    def set_status(self, booking_id, status):
        with app_module.app.app_context():
            row = app_module.db.session.get(app_module.Booking, booking_id)
            row.status = status
            app_module.db.session.commit()

    def booking_status(self, booking_id):
        with app_module.app.app_context():
            return app_module.db.session.get(app_module.Booking, booking_id).status

    # -- the fix: offers keep arriving during a trip ----------------------
    def test_non_overlapping_offer_still_arrives_after_accept(self):
        # 18 miles -> busy 12:00 + 66 min = until 13:06. The 14:00 job
        # does not overlap, so it must still be offered after the
        # driver accepts the 12:00 job — this is the offer the trip
        # screen now polls for.
        _, token = self.register_driver()
        first = self.book(time="12:00")
        later = self.book(time="14:00")
        self.pay(first["id"])
        self.pay(later["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        self.assertIn(later["id"], self.offer_ids(token))

    def test_overlapping_offer_stays_hidden_during_trip(self):
        # The overlap rule is unchanged: an overlapping second job is
        # hidden from offers (it must never be acceptable), on the
        # home screen and mid-trip alike.
        _, token = self.register_driver()
        first = self.book(time="12:00")
        overlap = self.book(time="12:30")
        self.pay(first["id"])
        self.pay(overlap["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        self.assertNotIn(overlap["id"], self.offer_ids(token))

    def test_overlapping_accept_rejected_mid_trip(self):
        _, token = self.register_driver()
        first = self.book(time="12:00")
        overlap = self.book(time="12:30")
        self.pay(first["id"])
        self.pay(overlap["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        resp = self.accept(token, overlap["id"])
        self.assertEqual(resp.status_code, 409, resp.get_data(as_text=True)[:200])

    def test_second_job_accept_queues_and_first_trip_unchanged(self):
        _, token = self.register_driver()
        first = self.book(time="12:00")
        later = self.book(time="14:00")
        self.pay(first["id"])
        self.pay(later["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        resp = self.accept(token, later["id"])
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        # The first trip is untouched by accepting the second job.
        self.assertEqual(self.booking_status(first["id"]), "accepted")
        self.assertEqual(self.booking_status(later["id"]), "accepted")
        # The queued job is listed as a next job; the current trip
        # (still merely accepted here) is the active trip.
        self.assertIn(later["id"], self.next_job_ids(token))
        active = self.active_trip(token)
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], first["id"])

    # -- active-trip restore: started trip wins over a queued job --------
    def test_active_trip_prefers_started_trip_over_queued_job(self):
        _, token = self.register_driver()
        first = self.book(time="12:00")
        later = self.book(time="14:00")
        self.pay(first["id"])
        self.pay(later["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        self.assertEqual(self.accept(token, later["id"]).status_code, 200)
        self.set_status(first["id"], "in_progress")
        active = self.active_trip(token)
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], first["id"])
        # The queued job is a next job, not the current trip.
        self.assertEqual(self.next_job_ids(token), [later["id"]])

    def test_active_trip_started_wins_even_with_later_pickup(self):
        # Artificial state to pin the ordering rule: the started trip
        # wins even when its pickup is LATER than a merely accepted
        # job's — otherwise a reload mid-trip could swap the current
        # trip for the queued job.
        _, token = self.register_driver()
        early = self.book(time="12:00")
        late = self.book(time="14:00")
        self.pay(early["id"])
        self.pay(late["id"])
        self.assertEqual(self.accept(token, early["id"]).status_code, 200)
        self.assertEqual(self.accept(token, late["id"]).status_code, 200)
        self.set_status(late["id"], "in_progress")
        active = self.active_trip(token)
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], late["id"])

    def test_active_trip_returns_earliest_pickup_when_nothing_started(self):
        _, token = self.register_driver()
        early = self.book(time="12:00")
        late = self.book(time="14:00")
        self.pay(early["id"])
        self.pay(late["id"])
        self.assertEqual(self.accept(token, early["id"]).status_code, 200)
        self.assertEqual(self.accept(token, late["id"]).status_code, 200)
        active = self.active_trip(token)
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], early["id"])

    def test_completed_first_trip_hands_over_to_next_job(self):
        # The server side of the end-of-trip advance: once the first
        # trip is completed, the queued job is the active trip.
        _, token = self.register_driver()
        first = self.book(time="12:00")
        later = self.book(time="14:00")
        self.pay(first["id"])
        self.pay(later["id"])
        self.assertEqual(self.accept(token, first["id"]).status_code, 200)
        self.assertEqual(self.accept(token, later["id"]).status_code, 200)
        self.set_status(first["id"], "completed")
        active = self.active_trip(token)
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], later["id"])
        self.assertEqual(self.next_job_ids(token), [later["id"]])

    # -- frontend: polling on the trip screen, card under the trip -------
    def test_polling_runs_on_trip_screen_too(self):
        driver_js = read("static/js/driver.js")
        # The pinned home-screen gate is untouched (see
        # test_no_double_booking.py).
        self.assertIn('if (!$("screen-home").classList.contains("hidden") && !state.trip)',
                      driver_js)
        # ... and the trip screen polls the same way, at every stage.
        self.assertIn('} else if (!$("screen-trip").classList.contains("hidden") && state.trip) {',
                      driver_js)
        self.assertIn("renderTripOffers(list);", driver_js)
        self.assertIn("refreshNextJobs();", driver_js)

    def test_trip_screen_has_second_job_section_before_chat(self):
        html = read("static/driver.html")
        trip_start = html.index('id="screen-trip"')
        trip_end = html.index('id="screen-earnings"')
        trip = html[trip_start:trip_end]
        self.assertIn('id="trip-offers-section"', trip)
        self.assertIn('id="trip-offers-list"', trip)
        self.assertIn('id="trip-next-jobs"', trip)
        # The section sits under the current trip and above the chat:
        # the chat box stays at the bottom of the trip screen.
        self.assertLess(trip.index('id="trip-offers-section"'),
                        trip.index('id="trip-chat"'))
        self.assertGreater(trip.index('id="trip-offers-section"'),
                           trip.index('id="trip-next-btn"'))

    def test_mid_trip_accept_queues_without_replacing_trip(self):
        driver_js = read("static/js/driver.js")
        handler = extract_function(driver_js, "function respondToOffer(id, action)")
        # The mid-trip branch queues the job and returns before the
        # normal path that replaces state.trip and opens the chat.
        self.assertIn("if (state.trip) {", handler)
        self.assertIn("state.nextJobs =", handler)
        self.assertIn("renderTripNextJobs();", handler)
        branch_at = handler.index("if (state.trip) {")
        replace_at = handler.index("state.trip = tripFromBooking(b, id);")
        self.assertLess(branch_at, replace_at)
        # The chat still opens exactly once, on the normal (no
        # current trip) accept path — not on a mid-trip accept.
        self.assertEqual(driver_js.count("openTripChatOnAccept"), 2)

    def test_end_trip_advances_to_queued_job(self):
        driver_js = read("static/js/driver.js")
        end = extract_function(driver_js, "function endTrip()")
        self.assertIn("restoreActiveTrip();", end)

    def test_trip_offer_cards_show_no_amounts(self):
        # Offers show pickup, drop-off and time only (owner decision
        # 2026-11-20): the new trip-screen cards and the queued-job
        # card carry no money figure.
        driver_js = read("static/js/driver.js")
        self.assertNotIn("Your earnings", driver_js)
        self.assertNotIn("$5", driver_js)
        html = read("static/driver.html")
        self.assertNotIn("$5", html)


if __name__ == "__main__":
    unittest.main()
