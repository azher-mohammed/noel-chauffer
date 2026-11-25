"""Tests for the customer app (/app) booking page matching the
website's booking flow look.

Owner decisions, 2026-11-25:
- ~06:19 EST ("White kar do"): the "Your details" fields and the
  Pay by card box go white.
- ~07:00 EST (latest word, supersedes the narrower scope): the
  WHOLE booking page matches the website — "why is the customer
  app booking page so black and why is it not like the website".
  Booking form card, class cards, highlights, fields, total box
  and pay area all go light like the website's booking flow.

What the website looks like (static/css/customer.css, verified
2026-11-25): white booking card with a black top accent; white
inputs with a #cfccc2 border and a near-black focus ring; white
class cards, selected card blue with white text; paper highlights;
#f7f7f7 total box with a near-black border; flat pay area (just
a divider line, no card). The website's dark surfaces — the
address-suggestions dropdown, date picker and time list (dark
navy #101c2e) — stay dark in the app too.

Kept unchanged by this change (pinned here): the black brand
header, the black tab bar, the light-blue buttons (#5b9bd5), the
price breakdown (including its dotted leaders), the dark
post-booking screens (driver card, chat, history, referral,
invoice), and the website itself (it loads customer.css, not
customer-app.css).

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as f:
        return f.read()


def _rule(css, selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css, re.S)
    assert m, "missing rule %s" % selector
    return m.group(1)


class WhiteBookingCardTest(unittest.TestCase):
    """The booking-form card is white like the website's."""

    def test_booking_card_is_white(self):
        css = _read("static/css/customer-app.css")
        card = _rule(css, "#ca-booking-card")
        self.assertIn("background: var(--white);", card)
        self.assertIn("border-top: 3px solid #1a1a1a;", card)
        self.assertIn("color-scheme: light;", card)
        self.assertNotIn("var(--black)", card)
        self.assertIn("color: var(--ink);",
                      _rule(css, "#ca-booking-card h2"))
        self.assertIn("background: #1a1a1a;",
                      _rule(css, "#ca-booking-card h2::after"))


class WhiteBookingFieldsTest(unittest.TestCase):
    """Every field on the booking page is white, like the website's."""

    WHITE_SCOPES = (
        "#ca-booking-card .field input, #ca-booking-card .field select,\n"
        "#ca-flight-step .field input, #ca-flight-step .field select,\n"
        ".class-contact .field input, .class-contact .field select,\n"
        ".pay-panel .field input, .pay-panel .field select",
    )

    def test_booking_fields_are_white(self):
        css = _read("static/css/customer-app.css")
        body = _rule(css, self.WHITE_SCOPES[0])
        self.assertIn("background: #ffffff;", body)
        self.assertIn("color: var(--ink);", body)
        self.assertIn("border: 1px solid #cfccc2;", body)
        # Focus matches the website: near-black border, dark ring.
        focus = _rule(
            css,
            "#ca-booking-card .field input:focus, #ca-booking-card .field select:focus,\n"
            "#ca-flight-step .field input:focus, #ca-flight-step .field select:focus,\n"
            ".class-contact .field input:focus, .class-contact .field select:focus,\n"
            ".pay-panel .field input:focus, .pay-panel .field select:focus")
        self.assertIn("border-color: #1a1a1a;", focus)
        self.assertIn("box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.25)", focus)
        # Autofill keeps the white fill with dark text.
        af = _rule(
            css,
            "#ca-booking-card .field input:-webkit-autofill, #ca-flight-step .field input:-webkit-autofill,\n"
            ".class-contact .field input:-webkit-autofill, .pay-panel .field input:-webkit-autofill")
        self.assertIn("-webkit-box-shadow: 0 0 0 60px #ffffff inset;", af)
        self.assertIn("-webkit-text-fill-color: var(--ink);", af)
        # Invalid fields still show the red border.
        inv = _rule(
            css,
            "#ca-booking-card .field input.field-invalid, #ca-flight-step .field input.field-invalid,\n"
            ".class-contact .field input.field-invalid, .pay-panel .field input.field-invalid")
        self.assertIn("border-color: #ff6b6b;", inv)
        # The required-field message is dark red on white.
        self.assertIn("color: var(--bad);", _rule(css, ".field-error"))

    def test_booking_fields_exist_in_markup(self):
        html = _read("static/customer-app.html")
        for ident in ("ca-pickup", "ca-dropoff", "ca-date", "ca-time",
                      "ca-flight-number", "ca-class-name",
                      "ca-class-phone", "ca-class-email",
                      "ca-pay-name", "ca-pay-number", "ca-pay-exp",
                      "ca-pay-cvc"):
            self.assertIn('id="%s"' % ident, html, ident)

    def test_history_lookup_keeps_dark_inputs(self):
        # Outside the booking flow: the My Rides phone lookup keeps
        # the dark base inputs.
        css = _read("static/css/customer-app.css")
        base = _rule(css, ".field input, .field select")
        self.assertIn("background: #1d1d1f;", base)
        self.assertIn("color: var(--white);", base)


class WhiteRideTabsTest(unittest.TestCase):
    """Ride-type tabs are light like the website's."""

    def test_ride_tabs_are_light(self):
        css = _read("static/css/customer-app.css")
        tab = _rule(css, ".ride-tab")
        self.assertIn("background: var(--paper);", tab)
        self.assertIn("color: var(--ink);", tab)
        self.assertIn("border: 1px solid var(--line);", tab)
        active = _rule(css, ".ride-tab.active")
        self.assertIn("background: var(--blue);", active)
        self.assertIn("box-shadow: inset 0 -3px 0 #1a1a1a;", active)


class WhiteClassCardsTest(unittest.TestCase):
    """Class cards are white like the website's; selected is blue."""

    def test_class_cards_are_white(self):
        css = _read("static/css/customer-app.css")
        card = _rule(css, ".class-option")
        self.assertIn("background: var(--white);", card)
        self.assertIn("border: 1px solid #cfccc2;", card)
        self.assertIn("color: var(--ink);", card)
        self.assertNotIn("var(--card)", card)
        # Name and total inherit the dark ink (white only when the
        # card itself is selected blue).
        self.assertNotIn("color: var(--white);",
                         _rule(css, ".class-option-name"))
        self.assertNotIn("color: var(--gold-soft);",
                         _rule(css, ".class-option-total"))
        selected = _rule(css, ".class-option.selected")
        self.assertIn("background: var(--blue);", selected)
        self.assertIn("color: var(--white);", selected)
        self.assertIn("color: var(--gold-soft);",
                      _rule(css, ".class-option.selected .class-option-total"))

    def test_highlights_are_light(self):
        css = _read("static/css/customer-app.css")
        # "Explore ..." line is dark ink, like the website's.
        self.assertIn("color: var(--ink);", _rule(css, ".class-explore"))
        self.assertIn("color: var(--ink);",
                      _rule(css, ".hl-slide figcaption"))
        text = _rule(css, ".hl-slide-text")
        self.assertIn("background: var(--paper);", text)
        self.assertIn("color: var(--ink);",
                      _rule(css, ".hl-slide-text h4"))
        self.assertIn("color: var(--grey);",
                      _rule(css, ".hl-slide-text p"))
        self.assertIn("background: #cfccc2;", _rule(css, ".hl-dot"))


class WhitePayAreaTest(unittest.TestCase):
    """The pay area is flat white like the website's (no card)."""

    def test_pay_panel_is_flat(self):
        css = _read("static/css/customer-app.css")
        body = _rule(css, ".pay-panel")
        self.assertIn("background: transparent;", body)
        self.assertIn("border-top: 1px solid var(--line);", body)
        self.assertIn("box-shadow: none;", body)
        self.assertNotIn("var(--card)", body)
        # Labels, errors and notes inside read dark on white.
        self.assertIn("color: #6b7280;", _rule(css, ".pay-panel .field label"))
        self.assertIn("color: var(--bad);", _rule(css, ".pay-panel .form-error"))
        self.assertIn("color: #6b7280;", _rule(css, ".pay-panel .form-note"))
        # Saved cards and the "save this card" row are dark on white.
        saved = _rule(css, ".saved-card-option")
        self.assertIn("background: #ffffff;", saved)
        self.assertIn("color: var(--ink);", saved)
        self.assertIn("color: var(--ink);", _rule(css, ".save-card"))
        self.assertIn("color: #6b7280;", _rule(css, ".field-label"))

    def test_stripe_card_element_is_white(self):
        css = _read("static/css/customer-app.css")
        body = _rule(css, ".stripe-card-element")
        self.assertIn("background: #ffffff;", body)
        self.assertIn("border: 1px solid #cfccc2;", body)
        # The text inside Stripe's iframe is dark, not white.
        js = _read("static/js/customer-app.js")
        m = re.search(r"elements\.create\(\"card\", \{\s*style: \{\s*base: \{([^}]*)\}",
                      js, re.S)
        self.assertIsNotNone(m, "stripe card element style")
        self.assertIn('color: "#161617"', m.group(1))
        self.assertIn('invalid: { color: "#a83232" }', js)

    def test_test_mode_banner_still_visible(self):
        css = _read("static/css/customer-app.css")
        body = _rule(css, ".test-banner")
        self.assertIn("background: #f2f2f2;", body)
        self.assertIn("color: #4a4a4a;", body)
        html = _read("static/customer-app.html")
        self.assertIn("TEST MODE", html)


class LightTotalBoxTest(unittest.TestCase):
    """The total box is light like the website's."""

    def test_total_box_is_light(self):
        css = _read("static/css/customer-app.css")
        body = _rule(css, ".total-box")
        self.assertIn("background: #f7f7f7;", body)
        self.assertIn("border: 1px solid #1a1a1a;", body)
        self.assertIn("color: var(--ink);", _rule(css, ".total-box .amount"))
        self.assertIn("color: var(--grey);", _rule(css, ".total-box .label"))
        self.assertIn("color: var(--grey);", _rule(css, ".total-box .note"))


class DarkPopupsStayDarkTest(unittest.TestCase):
    """The website's dark popups stay dark in the app too."""

    def test_suggestions_date_and_time_stay_dark(self):
        # The website's suggestions dropdown, date picker and time
        # list are dark navy (#101c2e) — the app's dark versions
        # match that intent and are untouched.
        css = _read("static/css/customer-app.css")
        self.assertIn("background: #262628;",
                      _rule(css, ".places-list"))
        self.assertIn("background: #262628;",
                      _rule(css, ".date-picker"))
        self.assertIn("background: #262628;",
                      _rule(css, ".time-list"))
        site = _read("static/css/customer.css")
        self.assertIn("background: #101c2e;", site)


class UntouchedSurfacesTest(unittest.TestCase):
    """What the owner did NOT ask to change stays exactly as it was."""

    def test_header_tabbar_and_blue_buttons_unchanged(self):
        css = _read("static/css/customer-app.css")
        self.assertIn("background: var(--black);", _rule(css, ".app-head"))
        self.assertIn("background: var(--black);", _rule(css, ".tabbar"))
        self.assertIn("background: var(--blue);",
                      _rule(css, ".btn-primary"))
        self.assertNotIn("#0b5fff", css)
        # The Pay button stays light blue.
        self.assertIn("background: var(--blue);",
                      _rule(css, "#ca-pay-submit"))

    def test_price_breakdown_unchanged(self):
        css = _read("static/css/customer-app.css")
        self.assertIn("breakdown-row", css)
        self.assertIn("breakdown-total", css)
        # The dotted leaders keep their colour.
        self.assertIn("border-bottom: 1px dotted #555558;",
                      _rule(css, ".class-breakdown .breakdown-row::after"))

    def test_post_booking_screens_stay_dark(self):
        css = _read("static/css/customer-app.css")
        self.assertIn("background: var(--card);",
                      _rule(css, ".driver-card"))
        self.assertIn("background: var(--card);",
                      _rule(css, ".chat-panel"))
        self.assertIn("background: var(--card);",
                      _rule(css, ".history-item"))
        self.assertIn("background: var(--card);",
                      _rule(css, ".invoice-panel"))

    def test_website_homepage_does_not_load_customer_app_css(self):
        html = _read("static/index.html")
        self.assertNotIn("customer-app.css", html)
        # The website checkout keeps its own sheet.
        self.assertIn("customer.css", html)


if __name__ == "__main__":
    unittest.main()
