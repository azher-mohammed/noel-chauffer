"""Tests for the browser-based customer app (owner decision 2026-11-18:
build the customer app the owner can open in his iPhone browser and
test right now, mirroring the driver web app pattern).

The app lives at /app (static/customer-app.html + static/js/customer-
app.js + static/css/customer-app.css) and is a shell over the SAME
/api/* contract the customer website uses — no parallel booking,
pricing, toll, dispatch, or payment logic. These tests pin:

- /app serves the real app page; /, /driver, /owner still serve
  their pages with their key markers intact.
- The app HTML has no duplicate IDs, no rates, no driver-owned
  wording, no app-download section, and English-only text.
- The app JS calls exactly the website's endpoints, reads totals
  from the API (never computes a fare), keeps the flight step wiring
  parked (owner order 2026-11-20: the step never shows for now), the
  class chooser breakdown-free, payment before dispatch, the trip chat
  gated on accept, the support chat scripted-only with owner
  reporting, and the referral display states the friend-only 5%
  first-ride discount (owner decision 2026-11-18, as on the website).
- The API contract the app relies on works end to end through the
  test client: create -> class totals -> class select -> pay ->
  offered; history lookup; support message storage + owner listing;
  referral code issued per booking.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from collections import Counter

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-customerapp-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "customerapp-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo (same as the other API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Customer App Tester"}


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class CustomerAppPageCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._phone_seq = 0

    # -- the route serves the real app page --------------------------------
    def test_app_route_serves_customer_app(self):
        resp = self.client.get("/app")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("<title>Noel Chauffer — Customer App</title>", html)
        self.assertIn('id="screen-book"', html)
        self.assertIn('id="screen-rides"', html)
        self.assertIn('id="screen-support"', html)
        # Referral tab removed (owner 2026-11-21): no referral screen
        # or "Refer a friend" text anywhere in the customer app.
        self.assertNotIn('id="screen-referral"', html)
        self.assertNotIn('data-screen="referral"', html)
        self.assertNotIn("Refer a friend", html)
        self.assertIn('id="ca-tabbar"', html)
        self.assertIn("Book your ride", html)
        self.assertIn("Choose your experience", html)
        self.assertIn("My rides", html)
        self.assertIn("Chat with us", html)
        self.assertNotIn("Refer a friend", html)
        self.assertIn("/static/js/customer-app.js", html)
        self.assertIn("/static/css/customer-app.css", html)
        self.assertIn("/static/js/flight.js", html)
        self.assertIn("leaflet", html)

    def test_existing_pages_unchanged(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        home = resp.get_data(as_text=True)
        self.assertNotIn("Luxury rides, chauffeur-driven.", home)  # headline removed by owner order 2026-11-20
        # "Book your ride" became "Your ride" (Blacklane batch, owner
        # order 2026-11-22: no 'Book' wording on the homepage).
        self.assertIn("Your ride", home)
        self.assertNotIn("Book your ride", home)
        self.assertIn("Travel on your own terms.", home)
        resp = self.client.get("/driver")
        self.assertEqual(resp.status_code, 200)
        driver = resp.get_data(as_text=True)
        self.assertIn("Driver app", driver)
        self.assertIn("New driver registration", driver)
        resp = self.client.get("/owner")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Noel Chauffer", resp.get_data(as_text=True))

    # -- HTML hygiene -------------------------------------------------------
    def test_no_duplicate_ids_in_app_page(self):
        html = read("static/customer-app.html")
        ids = re.findall(r'id="([^"]+)"', html)
        dupes = [i for i, c in Counter(ids).items() if c > 1]
        self.assertEqual(dupes, [], f"duplicate id(s) in customer-app.html: {dupes}")

    def test_app_page_shows_no_rates(self):
        html = read("static/customer-app.html")
        for banned in ("$9", "$10", "$90", "$50", "per mile", "/mile",
                       "per hour", "$1/min", "gratuity", "booking fee"):
            self.assertNotIn(banned, html, f"app page must not show {banned!r}")

    def test_app_page_has_no_driver_owned_wording_or_download_section(self):
        html = read("static/customer-app.html")
        lowered = html.lower()
        for banned in ("driver-owned", "drivers own", "belong to drivers",
                       "cars belong", "app store", "google play",
                       "download the app", "download our app", "get the app"):
            self.assertNotIn(banned, lowered, f"app page must not say {banned!r}")

    def test_app_page_text_is_english_only(self):
        html = read("static/customer-app.html")
        devanagari = [ch for ch in html if "\u0900" <= ch <= "\u097f"]
        self.assertEqual(devanagari, [], "app page must not contain Devanagari text")

    def test_app_form_mirrors_website_fields(self):
        html = read("static/customer-app.html")
        for field in ("ca-pickup", "ca-dropoff", "ca-date", "ca-time",
                      "ca-hours", "ca-name", "ca-phone",
                      "ca-email", "ca-referral", "ca-flight-number",
                      "ca-class-breakdown",
                      "ca-class-option-sedan", "ca-class-option-suv",
                      "ca-hourly-class-step", "ca-hourly-class-continue",
                      "ca-hourly-class-back",
                      "ca-pay-number", "ca-pay-exp", "ca-pay-cvc",
                      "ca-history-phone", "ca-support-input",
                      "ca-driver-photo",
                      "ca-chat-messages", "ca-map"):
            self.assertIn('id="%s"' % field, html)

    def test_app_class_step_shows_included_and_breakdown(self):
        # Blacklane-style options page (owner decision 2026-11-20),
        # same as the website: what's included + the selected
        # class's fare breakdown.
        html = read("static/customer-app.html")
        for text in ("Price breakdown", 'id="ca-class-breakdown"',
                     "car-business.jpg", "car-suv.jpg", "car-first.jpg",
                     "class-option-car"):
            self.assertIn(text, html, "app options page must show %r" % text)
        js = read("static/js/customer-app.js")
        for text in ("classBreakdowns", "ca-class-breakdown", "Base fare",
                     "Black car fee", "Referral discount"):
            self.assertIn(text, js, "app JS must paint %r" % text)

    # -- JS: same endpoints, no fare math -----------------------------------
    def test_app_js_calls_the_website_endpoints(self):
        js = read("static/js/customer-app.js")
        for endpoint in ('"/api/places/search?q="',
                         '"/api/bookings"',
                         '"/vehicle-class"',
                         '"/api/bookings/" + encodeURIComponent(booking.id)',
                         '"/pay"',
                         '"/cancel"',
                         '"/api/bookings?phone="',
                         '"/messages?phone="',
                         '"/messages"',
                         '"/chat-language"',
                         '"/api/support-messages"',
                         '"/driver-photo"'):
            self.assertIn(endpoint, js, f"app JS must call {endpoint}")
        # Owner order 2026-11-20: the flight step is parked, so the
        # app JS no longer calls the airport detection library; the
        # flight.js script tag stays loaded for a later re-enable.

    def test_app_js_never_computes_a_fare(self):
        js = read("static/js/customer-app.js")
        for banned in ("$9", "$10", "$90", "$50", "per mile", "miles *",
                       "* miles", "compute_", "fare_total", "fare =",
                       "gratuity", "booking_fee", "tax ="):
            self.assertNotIn(banned, js, f"app JS must not contain {banned!r}")
        # The options page renders each class total from the booking,
        # and the booking status shows the single total from the
        # booking (flip 2026-11-20; the JS only displays the server
        # total, it never computes a fare itself).
        self.assertIn("money(totals.sedan", js)
        self.assertIn("money(b.total)", js)
        self.assertIn("Bookings are open", js)

    def test_app_js_keeps_flight_step_skippable(self):
        js = read("static/js/customer-app.js")
        self.assertIn('state.flightResolved', js)
        self.assertIn('$("ca-flight-skip")', js)
        self.assertIn("proceedFromFlightStep", js)

    def test_app_js_gates_chat_on_accept_and_map_on_tracking(self):
        js = read("static/js/customer-app.js")
        self.assertIn('CHAT_OPEN_STATUSES = ["accepted", "en_route", "arrived", "in_progress"]', js)
        self.assertIn("tr.visible", js)
        self.assertIn("tracking", js)

    def test_app_js_support_is_scripted_with_owner_reporting(self):
        js = read("static/js/customer-app.js")
        self.assertIn("supportAnswer", js)
        self.assertIn("Cancellation is free if you cancel more than 1 hour before pickup", js)
        self.assertIn("Waiting is free for 60 minutes at airports", js)
        self.assertIn('"/api/support-messages"', js)
        for banned in ("fetch(\"https://", "openai", "gpt", "llm", "AI answer"):
            self.assertNotIn(banned, js)

    def test_app_js_referral_ui_removed(self):
        # Referral tab removed (owner 2026-11-21): no Referral tab
        # code, no referral UI wiring, only three screens.
        js = read("static/js/customer-app.js")
        self.assertNotIn("Referral tab", js)
        self.assertNotIn("showReferralCode", js)
        self.assertNotIn("showReferralLink", js)
        self.assertNotIn("ca-tab-referral", js)
        self.assertNotIn("ca-referral-form", js)
        self.assertIn('var SCREENS = ["book", "rides", "support"];', js)
        # The ?ref= prefill and the 5% first-ride discount stay.
        self.assertIn("prefillReferralFromUrl", js)
        self.assertIn("referral_code", js)

    def test_app_js_has_no_driver_owned_or_download_wording(self):
        js = read("static/js/customer-app.js")
        lowered = js.lower()
        for banned in ("driver-owned", "drivers own", "belong to drivers",
                       "app store", "google play", "download the app"):
            self.assertNotIn(banned, lowered)

    # -- the API contract the app relies on, end to end ----------------------
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
            "customer_name": "Customer App Tester",
            "phone": f"+1555009{self._phone_seq:04d}",
            "email": "apptest@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        booking = resp.get_json()["booking"]
        booking["phone"] = payload["phone"]
        if "@" in (payload.get("email") or "") and payload.get("phone"):
            self.signin(payload["email"], payload["phone"])
        return booking

    def test_create_class_pay_flow_as_the_app_drives_it(self):
        booking = self.book()
        self.assertEqual(booking["status"], "awaiting_payment")
        self.assertIn("class_totals", booking)
        self.assertIn("sedan", booking["class_totals"])
        self.assertIn("suv", booking["class_totals"])
        # The create view never leaks miles, rates, or a breakdown.
        for key in ("miles", "fare_total", "rate", "fare", "toll"):
            self.assertNotIn(key, booking)
        # Class selection (the app's "Choose your experience" screen).
        resp = self.client.post(f"/api/bookings/{booking['id']}/vehicle-class",
                                json={"vehicle_class": "suv"})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertEqual(resp.get_json()["booking"]["vehicle_class"], "suv")
        # Payment before dispatch.
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay", json=dict(CARD))
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self.assertTrue(resp.get_json()["payment"]["test"])
        self.assertEqual(resp.get_json()["booking"]["status"], "offered")
        # A second payment is rejected.
        resp = self.client.post(f"/api/bookings/{booking['id']}/pay", json=dict(CARD))
        self.assertEqual(resp.status_code, 409)

    def test_history_lookup_and_detail_carry_referral_code(self):
        booking = self.book()
        resp = self.client.get("/api/bookings", query_string={"phone": booking["phone"]})
        self.assertEqual(resp.status_code, 200)
        rows = resp.get_json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], booking["id"])
        resp = self.client.get(f"/api/bookings/{booking['id']}")
        self.assertEqual(resp.status_code, 200)
        detail = resp.get_json()["booking"]
        self.assertIsInstance(detail["referral_code"], str)
        self.assertTrue(detail["referral_code"])
        self.assertIsNone(detail["driver"])
        self.assertFalse(detail["tracking"]["visible"])

    def test_support_message_reaches_owner_list(self):
        resp = self.client.post("/api/support-messages",
                                json={"text": "App support test: where is my chauffeur?"})
        self.assertEqual(resp.status_code, 201)
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get("/api/owner/support-messages")
        self.assertEqual(resp.status_code, 200)
        texts = [m["text"] for m in resp.get_json()]
        self.assertIn("App support test: where is my chauffeur?", texts)

    def test_cancel_from_app_contract(self):
        booking = self.book()
        resp = self.client.post(f"/api/bookings/{booking['id']}/cancel",
                                json={"phone": booking["phone"]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["booking"]["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
