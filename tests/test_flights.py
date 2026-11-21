"""Tests for the flight-number flow (Blacklane-style).

- Flight number was REMOVED from the booking form and the separate
  step by owner order 2026-11-20 ("flight number nahi aana chahiye
  abhi"): no flight field on the first page, and the step never
  shows. The step panel and its wiring stay in place, parked, so the
  field can come back on his word; the server still accepts
  flight_number.
- Flight-number normalization + IATA airline names (flights.py).
- Terminal extraction from the chosen place suggestion text.
- Storage on the booking; a missing or invalid flight number never
  blocks the booking.
- Driver trip payloads show flight number + airline name + terminal,
  never miles, fare, or any other money figure.
- Owner ride details show the flight number.
- Airport detection for the prompt (node harness over
  static/js/flight.js).
- Static checks: no in-form flight field, the step is never
  triggered from submit, and no flight-tracking claims exist.

Run:  python -m unittest discover -s tests -v
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-flights-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "flights.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "flights-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as payouts tests).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
from flights import (  # noqa: E402
    AIRLINE_NAMES,
    airline_name_for,
    flight_info,
    normalize_flight_number,
    terminal_for_booking,
    terminal_from_address,
)

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}

TERMINAL_PICKUP = "Terminal 4 Arrivals, Jamaica, Queens, New York, 11430, United States"
HOTEL = "The Plaza Hotel, 5th Avenue, New York, NY 10019, United States"


class TestFlightNumberHelpers(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_flight_number("EK215"), "EK215")
        self.assertEqual(normalize_flight_number("ek 215"), "EK215")
        self.assertEqual(normalize_flight_number("B6 1234"), "B61234")
        self.assertEqual(normalize_flight_number("  AA123A "), "AA123A")
        self.assertIsNone(normalize_flight_number(""))
        self.assertIsNone(normalize_flight_number("   "))
        self.assertIsNone(normalize_flight_number(None))
        self.assertIsNone(normalize_flight_number("!!!"))
        self.assertIsNone(normalize_flight_number("EK"))  # no digits
        self.assertIsNone(normalize_flight_number("AA12345"))  # 5 digits
        self.assertIsNone(normalize_flight_number("EK215-EXTRA-LONG"))

    def test_airline_names_known_codes(self):
        self.assertEqual(airline_name_for("EK215"), "Emirates")
        self.assertEqual(airline_name_for("AA123"), "American Airlines")
        self.assertEqual(airline_name_for("DL456"), "Delta Air Lines")
        self.assertEqual(airline_name_for("UA789"), "United Airlines")
        self.assertEqual(airline_name_for("WN12"), "Southwest Airlines")
        self.assertEqual(airline_name_for("B61234"), "JetBlue")
        self.assertEqual(airline_name_for("F9111"), "Frontier Airlines")
        self.assertEqual(airline_name_for("G4222"), "Allegiant Air")
        self.assertEqual(airline_name_for("BA249"), "British Airways")
        self.assertEqual(airline_name_for("QR701"), "Qatar Airways")
        self.assertEqual(airline_name_for("AI111"), "Air India")

    def test_airline_names_unknown_code_never_guessed(self):
        self.assertIsNone(airline_name_for("XX123"))
        self.assertIsNone(airline_name_for("5J123"))
        self.assertIsNone(airline_name_for(None))
        self.assertIsNone(airline_name_for(""))

    def test_airline_table_sanity(self):
        # Every entry is a 2-character real IATA designator -> a name.
        self.assertGreater(len(AIRLINE_NAMES), 40)
        for code, name in AIRLINE_NAMES.items():
            self.assertEqual(len(code), 2, code)
            self.assertTrue(code.isalnum(), code)
            self.assertTrue(isinstance(name, str) and name.strip(), code)

    def test_terminal_from_address(self):
        self.assertEqual(terminal_from_address(TERMINAL_PICKUP),
                         "Terminal 4 Arrivals")
        self.assertEqual(terminal_from_address("Terminal B Departures, Queens, NY"),
                         "Terminal B Departures")
        self.assertIsNone(terminal_from_address(
            "John F. Kennedy International Airport, Queens, NY"))
        self.assertIsNone(terminal_from_address(HOTEL))
        self.assertIsNone(terminal_from_address(""))
        self.assertIsNone(terminal_from_address(None))

    def test_terminal_for_booking_prefers_pickup(self):
        self.assertEqual(
            terminal_for_booking(TERMINAL_PICKUP, "Terminal 1 Departures, LAX"),
            "Terminal 4 Arrivals")
        self.assertEqual(
            terminal_for_booking(HOTEL, "Terminal 1 Departures, LAX"),
            "Terminal 1 Departures")
        self.assertIsNone(terminal_for_booking(HOTEL, HOTEL))

    def test_flight_info_combines_fields(self):
        self.assertEqual(
            flight_info("EK215", TERMINAL_PICKUP, HOTEL),
            {"flight_number": "EK215", "airline_name": "Emirates",
             "terminal": "Terminal 4 Arrivals"})
        self.assertEqual(
            flight_info(None, HOTEL, HOTEL),
            {"flight_number": None, "airline_name": None, "terminal": None})


class FlightsApiTestCase(unittest.TestCase):
    _counter = 0

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        self.client = app_module.app.test_client()

    def _book(self, pickup, dropoff, **extra):
        FlightsApiTestCase._counter += 1
        payload = {
            "customer_name": "Flight Tester",
            "phone": "555-010-%04d" % FlightsApiTestCase._counter,
            "email": "flight@example.com",
            "pickup": pickup,
            "dropoff": dropoff,
            "date": "2030-06-01",
            "time": "10:00",
            "ride_type": "one_way",
        }
        payload.update(extra)
        return self.client.post("/api/bookings", json=payload)

    def _pay(self, booking_id):
        """Pay for a booking (payment comes before dispatch)."""
        resp = self.client.post("/api/bookings/%d/pay" % booking_id, json={
            "card_number": "4242424242424242", "card_exp": "12/30",
            "card_cvc": "123", "card_name": "Flight Tester"})
        self.assertEqual(resp.status_code, 200, resp.get_json())
        return resp

    def _make_driver(self):
        FlightsApiTestCase._counter += 1
        n = FlightsApiTestCase._counter
        with app_module.app.app_context():
            driver = app_module.Driver(
                name="Flight Driver", phone="555-020-%04d" % n,
                email="driver@example.com", car_model="Tesla Model 3",
                car_colour="Black", plate="T100", token="flight-token-%d" % n,
                available=True)
            app_module.db.session.add(driver)
            app_module.db.session.commit()
            return driver.token


class TestFlightStorage(FlightsApiTestCase):
    def test_create_with_flight_number_stores_and_returns_it(self):
        resp = self._book(TERMINAL_PICKUP, HOTEL, flight_number="ek 215")
        self.assertEqual(resp.status_code, 201, resp.get_json())
        booking = resp.get_json()["booking"]
        self.assertEqual(booking["flight_number"], "EK215")
        self.assertEqual(booking["airline_name"], "Emirates")
        self.assertEqual(booking["terminal"], "Terminal 4 Arrivals")
        detail = self.client.get("/api/bookings/%d" % booking["id"]).get_json()["booking"]
        self.assertEqual(detail["flight_number"], "EK215")
        self.assertEqual(detail["airline_name"], "Emirates")
        self.assertEqual(detail["terminal"], "Terminal 4 Arrivals")

    def test_create_without_flight_number(self):
        resp = self._book(TERMINAL_PICKUP, HOTEL)
        self.assertEqual(resp.status_code, 201)
        booking = resp.get_json()["booking"]
        self.assertIsNone(booking["flight_number"])
        self.assertIsNone(booking["airline_name"])
        # Terminal still derives from the chosen suggestion text.
        self.assertEqual(booking["terminal"], "Terminal 4 Arrivals")

    def test_invalid_flight_number_never_blocks_booking(self):
        resp = self._book(TERMINAL_PICKUP, HOTEL, flight_number="!!!")
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.get_json()["booking"]["flight_number"])

    def test_hourly_booking_with_flight_number(self):
        resp = self._book(TERMINAL_PICKUP, "", ride_type="hourly", hours=3,
                          flight_number="AA123", vehicle_class="sedan")
        self.assertEqual(resp.status_code, 201, resp.get_json())
        booking = resp.get_json()["booking"]
        self.assertEqual(booking["flight_number"], "AA123")
        self.assertEqual(booking["airline_name"], "American Airlines")

    def test_unknown_airline_code_shows_code_as_entered(self):
        resp = self._book(TERMINAL_PICKUP, HOTEL, flight_number="XX123")
        booking = resp.get_json()["booking"]
        self.assertEqual(booking["flight_number"], "XX123")
        self.assertIsNone(booking["airline_name"])


class TestDriverFlightPayloads(FlightsApiTestCase):
    def test_accept_and_active_trip_show_flight_no_fare(self):
        booking_id = self._book(TERMINAL_PICKUP, HOTEL,
                                flight_number="EK215").get_json()["booking"]["id"]
        self._pay(booking_id)
        token = self._make_driver()
        headers = {"X-Driver-Token": token}
        resp = self.client.post("/api/drivers/me/offers/%d/accept" % booking_id,
                                headers=headers)
        self.assertEqual(resp.status_code, 200, resp.get_json())
        trip = resp.get_json()["booking"]
        self.assertEqual(trip["flight_number"], "EK215")
        self.assertEqual(trip["airline_name"], "Emirates")
        self.assertEqual(trip["terminal"], "Terminal 4 Arrivals")
        self.assertNotIn("earnings", trip)
        self.assertNotIn("toll", trip)
        self.assertFalse(FORBIDDEN_KEYS & set(trip.keys()))

        resp = self.client.get("/api/drivers/me/active-trip", headers=headers)
        trip = resp.get_json()["booking"]
        self.assertEqual(trip["flight_number"], "EK215")
        self.assertEqual(trip["airline_name"], "Emirates")
        self.assertEqual(trip["terminal"], "Terminal 4 Arrivals")
        self.assertFalse(FORBIDDEN_KEYS & set(trip.keys()))

    def test_driver_trip_without_flight_has_nulls_no_fare(self):
        booking_id = self._book(HOTEL, HOTEL).get_json()["booking"]["id"]
        self._pay(booking_id)
        token = self._make_driver()
        headers = {"X-Driver-Token": token}
        resp = self.client.post("/api/drivers/me/offers/%d/accept" % booking_id,
                                headers=headers)
        trip = resp.get_json()["booking"]
        self.assertIsNone(trip["flight_number"])
        self.assertIsNone(trip["airline_name"])
        self.assertIsNone(trip["terminal"])
        self.assertFalse(FORBIDDEN_KEYS & set(trip.keys()))


class TestOwnerFlightFields(FlightsApiTestCase):
    def _owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200, resp.get_json())

    def test_owner_list_and_detail_show_flight(self):
        booking_id = self._book(TERMINAL_PICKUP, HOTEL,
                                flight_number="DL456").get_json()["booking"]["id"]
        self._owner_login()
        rows = self.client.get("/api/owner/bookings").get_json()
        row = [r for r in rows if r["id"] == booking_id][0]
        self.assertEqual(row["flight_number"], "DL456")
        self.assertEqual(row["airline_name"], "Delta Air Lines")
        self.assertEqual(row["terminal"], "Terminal 4 Arrivals")
        detail = self.client.get("/api/owner/bookings/%d" % booking_id).get_json()
        self.assertEqual(detail["flight_number"], "DL456")
        self.assertEqual(detail["airline_name"], "Delta Air Lines")
        self.assertEqual(detail["terminal"], "Terminal 4 Arrivals")


@unittest.skipUnless(shutil.which("node"), "node not available")
class TestFlightStepDetectionNode(unittest.TestCase):
    """Airport detection for the flight prompt, run against flight.js."""

    NODE_SCRIPT = """
const fs = require('fs');
const assert = require('assert');
const src = fs.readFileSync(%s, 'utf8');
eval(src);
const F = globalThis.NoelFlight;
assert(F, 'NoelFlight namespace missing');
// Suggestion flag (primary signal).
assert.deepStrictEqual(
  F.airportSides({airport: true}, null, 'JFK', ''),
  {pickup: true, dropoff: false, any: true});
assert.deepStrictEqual(
  F.airportSides(null, {airport: true}, 'Hotel', 'LAX'),
  {pickup: false, dropoff: true, any: true});
// Terminal suggestion text (flag false, terminal in the name).
assert.strictEqual(F.isAirportText('Terminal 4 Arrivals, Jamaica, Queens'), true);
assert.strictEqual(F.isAirportText('John F. Kennedy International Airport'), true);
assert.strictEqual(F.isAirportText('LaGuardia Airport'), true);
assert.strictEqual(F.isAirportText('EWR'), true);
assert.strictEqual(F.isAirportText('Pickup at JFK'), true);
// Plain addresses stay non-airport.
assert.strictEqual(F.isAirportText('180 Green Acres Road, Valley Stream'), false);
assert.strictEqual(F.isAirportText('123 Oak Street'), false);   // OAK excluded
assert.strictEqual(F.isAirportText('Las Vegas Blvd'), false);   // LAS excluded
assert.strictEqual(F.isAirportText('San Diego, CA'), false);    // SAN excluded
assert.strictEqual(F.isAirportText('Sea Cliff Avenue'), false); // SEA excluded
assert.strictEqual(F.isAirportText(''), false);
assert.strictEqual(F.isAirportText(null), false);
assert.deepStrictEqual(
  F.airportSides({airport: false}, {airport: false}, 'Hotel A', 'Hotel B'),
  {pickup: false, dropoff: false, any: false});
assert.deepStrictEqual(
  F.airportSides(null, null, null, null),
  {pickup: false, dropoff: false, any: false});
console.log('flight.js detection OK');
"""

    def test_detection_cases(self):
        path = os.path.join(REPO_DIR, "static", "js", "flight.js")
        script = self.NODE_SCRIPT % json.dumps(path)
        proc = subprocess.run(["node", "-e", script],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("flight.js detection OK", proc.stdout)


class TestFlightStepStatic(unittest.TestCase):
    def _read(self, rel):
        with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as handle:
            return handle.read()

    def test_flight_field_removed_from_form_step_panel_parked(self):
        html = self._read("static/index.html")
        # Owner order 2026-11-20: the flight number field is gone
        # from the booking form ("flight number nahi aana chahiye
        # abhi") and the separate step never shows for now. The
        # step panel stays in the DOM, hidden and unused, so the
        # field can come back on his word.
        self.assertIn('id="flight-step"', html)
        self.assertIn('id="flight-number"', html)
        self.assertIn("/static/js/flight.js", html)
        form_start = html.index('<form id="booking-form"')
        form_end = html.index("</form>", form_start)
        form_html = html[form_start:form_end]
        self.assertNotIn('id="bk-flight-number"', form_html)
        self.assertNotIn("Flight number (optional)", form_html)
        self.assertNotIn("flight-step", form_html)

    def test_app_form_has_no_flight_field(self):
        html = self._read("static/customer-app.html")
        form_start = html.index('<form id="ca-booking-form"')
        form_end = html.index("</form>", form_start)
        form_html = html[form_start:form_end]
        # Owner order 2026-11-20: no flight-number field in the
        # app booking form either.
        self.assertNotIn('id="ca-flight-number-form"', form_html)
        self.assertNotIn("Flight number (optional)", form_html)

    def test_js_no_longer_reads_in_form_flight_number(self):
        # Owner order 2026-11-20: the form fields are gone, so the
        # submit path must not read them.
        self.assertNotIn("bk-flight-number",
                         self._read("static/js/customer.js"))
        self.assertNotIn("ca-flight-number-form",
                         self._read("static/js/customer-app.js"))

    def test_skip_is_wired_and_prompt_is_gated(self):
        js = self._read("static/js/customer.js")
        # The step panel and its wiring stay in place, parked, so
        # the field can come back on the owner's word — but the
        # submit path never triggers it now.
        self.assertIn("flight-skip", js)
        self.assertIn("flight-continue", js)
        self.assertIn("showFlightStep", js)
        self.assertIn("flightResolved", js)
        self.assertNotIn("showFlightStep(sides, payload);", js)
        # The airport detection library itself stays (flight.js).
        self.assertIn("airportSides", self._read("static/js/flight.js"))

    def test_no_flight_tracking_claims_in_ui(self):
        for rel in ("static/index.html", "static/driver.html", "static/owner.html",
                    "static/js/customer.js", "static/js/driver.js",
                    "static/js/owner.js", "static/js/flight.js"):
            text = self._read(rel)
            self.assertNotRegex(text, re.compile(r"flight track", re.I), rel)
            self.assertNotRegex(text, re.compile(r"track (your|the) flight", re.I), rel)
            self.assertNotRegex(text, re.compile(r"live flight", re.I), rel)

    def test_driver_trip_screen_renders_flight_fields(self):
        js = self._read("static/js/driver.js")
        self.assertIn("trip-flight", js)
        self.assertIn("flight_number", js)
        self.assertIn("airline_name", js)
        self.assertIn("terminal", js)
        self.assertIn('id="trip-flight"', self._read("static/driver.html"))

    def test_owner_detail_renders_flight(self):
        self.assertIn("flight_number", self._read("static/js/owner.js"))
        self.assertIn("airline_name", self._read("static/js/owner.js"))


if __name__ == "__main__":
    unittest.main()
