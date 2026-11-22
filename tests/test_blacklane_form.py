"""Tests for the Blacklane-style booking form + class page (owner
decision, voice call 2026-11-22): the homepage booking form and the
"Choose your experience" page follow the verified Blacklane
walk-through (pickup 180 Green Acres Rd -> JFK, Tue Nov 24, 07:00 AM).

Rules pinned here (website + customer app, unless noted):
1. Hamburger menu: circular button with THREE lines (not dots) at
   narrow width; full-screen dark overlay; Our services / For
   business accordions (one open at a time); every item links to the
   closest EXISTING Noel page — no new pages. "Sign in" and the
   language are plain items: Noel has no customer accounts and the
   site is English-only.
2. No "Book" wording on the homepage; the booking button stays
   "View options".
3. Address suggestions, Blacklane look: dark dropdown, full address
   as the bold main line + the same text smaller/grey beneath, type
   icons (plane / hotel / pin), same font sizes as Blacklane's list.
   Suggestions still come from Photon/Nominatim — the owner DROPPED
   Google Places 2026-11-22 ("phir bhi hai to chhodo bhai"), so there
   is no Google integration, no API-key plumbing and NO Google
   attribution line anywhere. A suggestion must be picked, not just
   typed: View options with an unselected/empty pickup or drop-off
   stops with a red "This field is required" + red underline.
4. Date picker: dark November-calendar popup, weekday header
   "Su Mo Tu We Th Fr Sa", past dates dimmed, struck through and
   unselectable, today first enabled, picking a date sets
   "Tue, Nov 24" (no year). Server-side past blocking unchanged.
5. Time picker: dropdown list, every 10 minutes, 12:00 AM-11:50 PM
   (144 options), 12-hour format, zero-padded hours, current value
   highlighted and auto-scrolled. The Time field is full width like
   the Date field.
6. Flight number field: appears between Date and Pickup time when
   ANY airport (or terminal) is picked, pickup or drop-off;
   placeholder "e.g. LH202, BA2490"; no terminal field.
7. "Choose your experience": side-by-side class cards (swipeable on
   narrow widths), Business pre-selected; Explore details line;
   5-slide highlights carousel (first slide: class photo +
   "Clean, quiet, and executive-level comfort."); "What's included"
   with the 5 items ONLY — NO complimentary water (owner decided);
   Capacity Luggage / Seating tabs ("2 x Carry-on"); price-breakdown
   card with dotted leader lines (existing values, no pricing
   change); "Please note" items; sticky bottom bar with the total +
   blue "Select <Class>"; NO footer on the booking page. After class
   selection the flow continues into Noel's EXISTING contact +
   card-payment steps — no sign-in gate, no new account step.
8. "View options" button: served CSS says light blue #5b9bd5 — no
   black rule for it exists (the black seen in the cloud browser was
   not in the served CSS).

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-blacklane-form-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "blacklane-form-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402
import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JFK_AIRPORT = [{
    "place_id": 1,
    "display_name": "John F. Kennedy International Airport, Queens, New York, 11430, United States",
    "lat": "40.6413111", "lon": "-73.7803273",
    "class": "aeroway", "type": "aerodrome",
    "address": {"county": "Queens", "state": "New York", "postcode": "11430",
                "country": "United States", "country_code": "us"},
}]
TERMINAL_4 = [{
    "place_id": 10,
    "display_name": "Terminal 4, John F. Kennedy International Airport, Queens, New York, 11430, United States",
    "lat": "40.6415", "lon": "-73.7780",
    "class": "aeroway", "type": "terminal",
    "address": {"county": "Queens", "state": "New York", "postcode": "11430",
                "country": "United States", "country_code": "us"},
}]
PLAZA_HOTEL = [{
    "place_id": 3,
    "display_name": "The Plaza Hotel, 768 5th Avenue, New York, NY 10019, United States",
    "lat": "40.7644", "lon": "-73.9747",
    "class": "tourism", "type": "hotel",
    "address": {"road": "5th Avenue", "city": "New York", "state": "New York",
                "postcode": "10019", "country": "United States", "country_code": "us"},
}]
STREET = [{
    "place_id": 2,
    "display_name": "180, Green Acres Road, East Valley Stream, Nassau County, New York, 11581, United States",
    "lat": "40.670123", "lon": "-73.708456",
    "class": "highway", "type": "residential",
    "address": {"house_number": "180", "road": "Green Acres Road",
                "village": "East Valley Stream", "county": "Nassau County",
                "state": "New York", "postcode": "11581",
                "country": "United States", "country_code": "us"},
}]


def read(path):
    with open(os.path.join(REPO_DIR, path), encoding="utf-8") as fh:
        return fh.read()


def block(text, start, length=1500):
    i = text.index(start)
    return text[i:i + length]


class BlacklaneFormCase(unittest.TestCase):
    def setUp(self):
        geo_module._search_cache.clear()
        geo_module._terminal_cache.clear()
        self.client = app_module.app.test_client()
        self.html = read("static/index.html")
        self.js = read("static/js/customer.js")
        self.css = read("static/css/customer.css")
        self.app_html = read("static/customer-app.html")
        self.app_js = read("static/js/customer-app.js")
        self.app_css = read("static/css/customer-app.css")

    # ---- 1. Hamburger menu (website) -----------------------------------
    def test_menu_button_is_circular_three_lines(self):
        m = re.search(r'<button[^>]*id="menu-btn"[^>]*>(.*?)</button>',
                      self.html, re.S)
        self.assertIsNotNone(m, "menu button must exist")
        self.assertEqual(m.group(1).count("<span"), 3,
                         "menu button must have exactly THREE line spans, not dots")
        self.assertIn('.menu-btn { display: none; }', self.css,
                      "menu button hidden on desktop (full nav shows)")
        self.assertIn("border-radius: 50%", self.css,
                      "menu button is circular")

    def test_menu_overlay_is_fullscreen_dark_with_wordmark_and_close(self):
        self.assertIn('id="mobile-menu"', self.html)
        self.assertIn('role="dialog"', self.html)
        self.assertIn('id="menu-close"', self.html)
        self.assertIn(".mobile-menu {", self.css)
        self.assertIn("position: fixed; inset: 0;", self.css)
        self.assertIn("background: rgba(11, 11, 12, 0.97);", self.css)

    def test_menu_items_in_blacklane_order(self):
        services = block(self.html, 'data-menu-sub="services"').split("</ul>")[0]
        found = re.findall(r'>([^<]+)</a>', services)
        self.assertEqual(found, ["City-to-City rides", "Chauffeur hailing",
                                 "Airport transfers", "Hourly hire",
                                 "Chauffeur service", "Limousine service"])
        business = block(self.html, 'data-menu-sub="business"').split("</ul>")[0]
        found = re.findall(r'>([^<]+)</a>', business)
        self.assertEqual(found, ["Overview", "Corporations",
                                 "Travel agencies", "Strategic partnerships"])
        menu = block(self.html, 'id="mobile-menu"', 4000)
        self.assertIn('href="/driver">For chauffeurs<', menu)
        self.assertIn('href="/frequently-asked-questions">Help<', menu)
        self.assertIn('class="menu-link menu-plain">English (US)<', menu)
        self.assertIn('class="menu-link menu-plain">Sign in<', menu)

    def test_menu_links_are_existing_pages(self):
        menu = block(self.html, 'id="mobile-menu"', 4000)
        hrefs = sorted(set(re.findall(r'href="([^"#]+)"', menu)))
        self.assertTrue(hrefs, "menu must link somewhere")
        for href in hrefs:
            resp = self.client.get(href)
            self.assertEqual(resp.status_code, 200,
                             "menu link %s must be an existing page" % href)

    def test_menu_only_one_accordion_open_at_a_time(self):
        body = block(self.js, "menu-group-btn", 1200)
        self.assertIn('querySelectorAll(".menu-sub")', body)
        self.assertIn('classList.add("hidden")', body,
                      "opening a section first closes all sections")

    def test_menu_served_on_homepage(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="menu-btn"', resp.data)
        self.assertIn(b'id="mobile-menu"', resp.data)

    # ---- 2. No "Book" wording on the homepage ---------------------------
    def test_homepage_has_no_book_wording_on_nav_or_buttons(self):
        self.assertNotIn('href="#book">Book<', self.html,
                         "nav must not say Book")
        self.assertNotIn('>Book your ride</h2>', self.html,
                         "sr-only heading must not say Book")
        self.assertNotIn('id="new-booking-btn">Book another ride<', self.html)
        self.assertNotIn('id="return-trip-btn">Book your return trip<', self.html)
        self.assertIn('id="new-booking-btn">Another ride<', self.html)
        self.assertIn('id="return-trip-btn">Your return trip<', self.html)
        self.assertIn('href="#book">Your ride<', self.html)

    def test_booking_button_stays_view_options(self):
        self.assertIn('id="book-submit">View options<', self.html)
        self.assertIn('id="ca-book-submit">View options<', self.app_html)

    # ---- 3. Suggestions: Blacklane look, Photon source, must-select -----
    def test_suggestion_box_is_dark_with_blacklane_font_sizes(self):
        for css in (self.css, self.app_css):
            self.assertIn(".places-list {", css)
        self.assertIn("background: #101c2e;", self.css,
                      "website suggestion box must be dark")
        self.assertIn(".places-main { display: block; font-weight: 600; font-size: 15px;",
                      self.css)
        self.assertIn(".places-detail { display: block; color: #9aa8bc; font-size: 13px;",
                      self.css)
        self.assertIn(".places-icon {", self.css)
        self.assertIn(".places-icon {", self.app_css)

    def test_suggestion_render_full_address_twice_with_icon(self):
        for js in (self.js, self.app_js):
            self.assertIn("mainEl.textContent = item.display_name;", js,
                          "bold main line must be the FULL address")
            self.assertIn("detEl.textContent = item.display_name;", js,
                          "smaller grey line repeats the SAME full address")
            self.assertIn("places-icon", js)
            self.assertIn("placeIcon(item)", js)

    def test_suggestion_icons_plane_hotel_pin(self):
        for js in (self.js, self.app_js):
            self.assertIn("M21 16v-2l-8-5", js, "plane icon for airports")
            self.assertIn("M7 13c1.66 0 3-1.34 3-3", js, "hotel icon for hotels")
            self.assertIn("M12 2C8.13 2 5 5.13 5 9", js, "pin icon for addresses")

    def test_no_google_anywhere(self):
        for path in ("static/js/customer.js", "static/js/customer-app.js",
                     "static/css/customer.css", "static/css/customer-app.css",
                     "static/index.html", "static/customer-app.html",
                     "geo.py", "app.py"):
            content = read(path)
            self.assertNotIn("powered by Google", content,
                             "%s must not carry Google attribution" % path)
            self.assertNotIn("GOOGLE_PLACES_API_KEY", content,
                             "%s must not have Google key plumbing" % path)
            self.assertNotIn("googleapis.com", content,
                             "%s must not call Google APIs" % path)

    def test_suggestion_must_be_selected(self):
        for js, prefix in ((self.js, "bk"), (self.app_js, "ca")):
            form_id = "booking-form" if prefix == "bk" else "ca-booking-form"
            submit = block(js, '$("%s").addEventListener("submit"' % form_id,
                           4000)
            self.assertIn("pickupPicked", submit,
                          "submit must require a picked pickup")
            self.assertIn('setFieldError("%s-pickup", "%s-pickup-error"' % (prefix, prefix),
                          submit)
            self.assertIn('setFieldError("%s-dropoff", "%s-dropoff-error"' % (prefix, prefix),
                          submit)
        for html, prefix in ((self.html, "bk"), (self.app_html, "ca")):
            self.assertIn('id="%s-pickup-error" role="alert">This field is required<' % prefix,
                          html)
            self.assertIn('id="%s-dropoff-error" role="alert">This field is required<' % prefix,
                          html)
        self.assertIn(".field-error { color: var(--bad);", self.css)
        self.assertIn(".field input.field-invalid { border-color: var(--bad); }",
                      self.css)

    def test_return_trip_keeps_swapped_picks(self):
        for js, btn in ((self.js, "return-trip-btn"),
                        (self.app_js, "ca-return-trip-btn")):
            body = block(js, '$("%s").addEventListener' % btn, 1600)
            self.assertIn("state.pickupPlace = prevDropoff;", body,
                          "return trip must keep the swapped pickup pick")
            self.assertIn("state.dropoffPlace = prevPickup;", body,
                          "return trip must keep the swapped drop-off pick")

    def test_suggestion_kind_airport_hotel_address(self):
        def fake_get(url):
            return JFK_AIRPORT
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=fake_get):
            results = geo_module.search_places("jfk-airport-kind")
        self.assertEqual(results[0]["kind"], "airport")
        self.assertIs(results[0]["airport"], True)
        geo_module._search_cache.clear()
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=lambda url: PLAZA_HOTEL):
            results = geo_module.search_places("plaza-hotel-kind")
        self.assertEqual(results[0]["kind"], "hotel")
        geo_module._search_cache.clear()
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=lambda url: STREET):
            results = geo_module.search_places("green-acres-kind")
        self.assertEqual(results[0]["kind"], "address")
        self.assertIs(results[0]["airport"], False)

    def test_terminal_results_are_kind_terminal(self):
        def fake_get(url):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if params.get("bounded") == ["1"]:
                return TERMINAL_4
            return JFK_AIRPORT
        with mock.patch.object(geo_module, "_http_get_json",
                               side_effect=fake_get):
            results = geo_module.search_places("jfk-terminal-kind")
        kinds = {r["display_name"].split(",")[0]: r["kind"] for r in results}
        self.assertEqual(kinds["John F. Kennedy International Airport"], "airport")
        self.assertEqual(kinds["Terminal 4"], "terminal")

    # ---- 4. Date picker --------------------------------------------------
    def test_date_input_is_text_with_calendar_popup(self):
        for html, prefix in ((self.html, "bk"), (self.app_html, "ca")):
            self.assertIn('id="%s-date" name="date" type="text" required readonly' % prefix,
                          html)
            self.assertIn('id="%s-date-picker"' % prefix, html)
            self.assertNotIn('type="date"', html,
                             "no native date input may survive")

    def test_calendar_structure_and_past_rules(self):
        for js in (self.js, self.app_js):
            self.assertIn('"Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"', js,
                          "weekday header must be Sunday-first")
            self.assertIn('"November"', js)
            self.assertIn('DAYS_SHORT[d.getDay()] + ", " + MONTHS_SHORT[d.getMonth()]',
                          js, "picked date must read like 'Tue, Nov 24'")
            self.assertIn('cls += " past"', js)
            self.assertIn('(iso < today ? " disabled" : "")', js,
                          "past dates must be unselectable")
            self.assertIn('cls += " today"', js,
                          "today must be marked as the first enabled date")
        self.assertIn(".dp-day.past { color: #5a6b82; text-decoration: line-through;",
                      self.css)

    def test_server_side_past_block_unchanged(self):
        self.assertIn("if (payload.date < today) {", self.js)
        self.assertIn("Past dates cannot be booked.", self.js)
        self.assertIn("if (payload.date < today) {", self.app_js)

    # ---- 5. Time picker --------------------------------------------------
    def test_time_list_has_144_ten_minute_options(self):
        for js in (self.js, self.app_js):
            self.assertIn("for (h = 0; h < 24; h++)", js)
            self.assertIn("for (m = 0; m < 60; m += 10)", js)
            self.assertIn('String(hh).padStart(2, "0")', js,
                          "hours must be zero-padded (07:10 AM)")
            self.assertIn('"AM"', js)
            self.assertIn('"PM"', js)
            self.assertIn("scrollIntoView", js,
                          "current value must be auto-scrolled to")

    def test_time_input_is_text_and_full_width(self):
        for html, prefix in ((self.html, "bk"), (self.app_html, "ca")):
            self.assertIn('id="%s-time" name="time" type="text" required readonly' % prefix,
                          html)
            self.assertIn('id="%s-time-list" role="listbox"' % prefix, html)
            self.assertNotIn('type="time"', html, "no native time input may survive")
        # Time field wrapper carries field-wide: full width like Date.
        self.assertIn('class="field field-wide field-time"', self.html)
        self.assertIn('class="field field-wide field-time"', self.app_html)

    # ---- 6. Flight number field ------------------------------------------
    def test_flight_field_between_date_and_time(self):
        for html, prefix in ((self.html, "bk"), (self.app_html, "ca")):
            flight_id = "field-flight" if prefix == "bk" else "ca-field-flight"
            date_pos = html.index('id="%s-date-picker"' % prefix)
            flight_pos = html.index('id="%s"' % flight_id)
            time_pos = html.index('id="%s-time-list"' % prefix)
            self.assertLess(date_pos, flight_pos,
                            "flight field must come after Date")
            self.assertLess(flight_pos, time_pos,
                            "flight field must come before Pickup time")
            self.assertIn('placeholder="e.g. LH202, BA2490"', html)
            self.assertNotIn('%s-terminal' % prefix, html,
                             "no terminal field may exist")

    def test_flight_field_shows_only_for_airport_picks(self):
        for js, flight_id in ((self.js, "field-flight"),
                              (self.app_js, "ca-field-flight")):
            fn = block(js, "function updateFlightField()", 600)
            self.assertIn("isAirportPlace(state.pickupPlace)", fn)
            self.assertIn("isAirportPlace(state.dropoffPlace)", fn)
            self.assertIn('show($("%s"))' % flight_id, fn)
            airport = block(js, "function isAirportPlace(p)", 200)
            self.assertIn('p.kind === "terminal"', airport,
                          "terminals count as airport picks too")

    def test_flight_number_sent_with_booking(self):
        for js, flight_id in ((self.js, "bk-flight"), (self.app_js, "ca-flight")):
            submit = block(js, "addEventListener(\"submit\"", 4500)
            self.assertIn('payload.flight_number = flightInput.value.trim()',
                          submit)
            self.assertIn('$("%s")' % flight_id, submit)

    # ---- 7. Choose your experience ---------------------------------------
    def test_class_cards_side_by_side_swipeable_on_narrow(self):
        self.assertIn(".class-options { flex-wrap: nowrap;", self.css)
        self.assertIn("flex: 1 1 0;", self.css)
        self.assertIn("flex-direction: column;", self.css)
        self.assertIn("scroll-snap-type: x mandatory;", self.css,
                      "narrow widths swipe card by card")
        self.assertIn("scroll-snap-type: x mandatory;", self.app_css)

    def test_explore_line_and_highlights_carousel(self):
        self.assertIn('id="class-explore">Explore Business Class details<', self.html)
        self.assertIn('id="class-highlights-track"', self.html)
        self.assertIn('id="class-hl-prev"', self.html)
        self.assertIn('id="class-hl-next"', self.html)
        self.assertIn('id="class-hl-dots"', self.html)
        self.assertIn('"Clean, quiet, and executive-level comfort."', self.js)
        self.assertIn("CLASS_PHOTOS[state.selectedClass]", self.js,
                      "first slide uses the selected class photo")
        self.assertIn('id="ca-class-explore">Explore Business Class details<',
                      self.app_html)
        self.assertIn('"Clean, quiet, and executive-level comfort."', self.app_js)

    def test_whats_included_five_items_no_water(self):
        for html in (self.html, self.app_html):
            self.assertNotIn("Complimentary water", html,
                             "owner decided NO complimentary water, never add it")
            included = block(html, "What's included", 600)
            for item in ("Personal meet &amp; greet",
                         "Includes up to 15 minutes of free wait time",
                         "Free to cancel up to 1 hour before pickup",
                         "iOS and Android chargers onboard",
                         "Assistance with luggage at pickup and drop-off"):
                self.assertIn(item, included)

    def test_capacity_tabs(self):
        for html in (self.html, self.app_html):
            self.assertIn('data-cap-tab="luggage"', html)
            self.assertIn('data-cap-tab="seating"', html)
            self.assertIn("2 x Carry-on", html)
        for js in (self.js, self.app_js):
            self.assertIn("sedan: { bags: 2, seats: 3 }", js)
            self.assertIn("suv: { bags: 5, seats: 5 }", js)
            self.assertIn("first: { bags: 2, seats: 3 }", js)

    def test_breakdown_dotted_leaders(self):
        for css in (self.css, self.app_css):
            self.assertIn(".class-breakdown .breakdown-row::after", css)
            self.assertIn("border-bottom: 1px dotted", css)

    def test_please_note_items(self):
        for html in (self.html, self.app_html):
            notes = block(html, "Please note", 900)
            self.assertIn("final fare may change", notes)
            self.assertIn("capacities must be respected", notes)
            self.assertIn("vehicle images above are examples", notes)

    def test_sticky_bar_and_no_footer_on_booking_page(self):
        self.assertIn('id="class-sticky-total"', self.html)
        self.assertIn("#class-step .class-actions {", self.css)
        self.assertIn("position: sticky; bottom: 0;", self.css)
        self.assertIn("body.class-step-open .site-footer { display: none; }",
                      self.css)
        show = block(self.js, "function showClassStep(booking, phone)", 2200)
        self.assertIn('document.body.classList.add("class-step-open")', show)
        back = block(self.js, '$("class-back").addEventListener', 500)
        self.assertIn('document.body.classList.remove("class-step-open")', back)
        self.assertIn('id="ca-class-sticky-total"', self.app_html)
        self.assertIn("#ca-class-step .class-actions {", self.app_css)
        self.assertIn("position: sticky; bottom: 0;", self.app_css)

    def test_business_preselected(self):
        self.assertIn('selectedClass: "sedan"', self.js)
        self.assertIn('state.selectedClass = booking.vehicle_class || "sedan"',
                      self.js)
        self.assertIn('selectedClass: "sedan"', self.app_js)

    def test_no_sign_in_gate_after_class_selection(self):
        for js in (self.js, self.app_js):
            self.assertNotIn("login.blacklane", js)
            self.assertNotIn("Auth0", js)
        cont = block(self.js, '$("class-continue").addEventListener', 1800)
        self.assertIn("saveContact", cont,
                      "class continue saves contact, then pays — no sign-in")
        self.assertIn("proceedWith", cont)

    # ---- 8. View options button colour check -----------------------------
    def test_view_options_button_is_light_blue_not_black(self):
        self.assertIn("--blue: #5b9bd5;", self.css)
        self.assertIn(".btn-primary {\n  width: 100%; background: var(--blue);",
                      self.css)
        self.assertIn(".booking-card .btn-primary { background: var(--blue);",
                      self.css)
        # No .btn-primary rule anywhere may set a black background.
        for m in re.finditer(r"\.btn-primary[^{]*\{[^}]*\}", self.css):
            self.assertNotIn("black", m.group(0).lower(),
                             "no black rule for .btn-primary: %s" % m.group(0))
        resp = self.client.get("/static/css/customer.css")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"--blue: #5b9bd5;", resp.data)

    # ---- Served pages -----------------------------------------------------
    def test_homepage_and_app_serve_the_new_form(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="bk-date-picker"', resp.data)
        self.assertIn(b'id="bk-time-list"', resp.data)
        self.assertIn(b'id="field-flight"', resp.data)
        self.assertIn(b'id="class-explore"', resp.data)
        resp = self.client.get("/app")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="ca-date-picker"', resp.data)
        self.assertIn(b'id="ca-time-list"', resp.data)
        self.assertIn(b'id="ca-field-flight"', resp.data)
        self.assertIn(b'id="ca-class-explore"', resp.data)


if __name__ == "__main__":
    unittest.main()
