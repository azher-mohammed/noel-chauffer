"""Tests for the customer app (/app) Support screen ("Chat with us")
and My Rides screen matching the website's light look.

Owner orders, 2026-11-25:
- ~09:03 EST (with a screenshot of the Support screen): "Whit it
  in black" / "It should be in whote" — the Support screen goes
  white with dark text. Assistant bubbles were BLACK, the "Type
  your message..." input was BLACK.
- ~09:05 EST (My Rides screenshot): "It should be in light gray
  not in black" — the My Rides ride cards go LIGHT GREY with dark
  text, and the phone-number lookup input goes white.
- ~09:06 EST (same My Rides screen): Pickup and Drop-off must show
  on TWO DIFFERENT LINES in the ride cards, not run together with
  an arrow on one block — the same separation the driver app has
  for offer cards and the trip screen (owner order 2026-11-23).

What the website looks like (static/css/customer.css and
static/js/ride-history.js, verified 2026-11-25): the "Chat with
us" widget has a WHITE assistant (.msg.bot) bubble with a light
line border, and a white input with a #cfccc2 border. The website's
ride-history items are plain rows on white (no card background at
all), its status pill is light grey #f7f7f7 with a #cfcfcf border
and #4a4a4a text, and its history input has a #cfccc2 border. The
website does NOT split pickup/drop-off in history — it uses the
same one-line "pickup → dropoff" label — so the split is an /app
My Rides change only.

What the app does now: white assistant bubbles with dark text,
white support input with the same #cfccc2 border; My Rides cards
in light grey #f5f5f5 (the website has no grey history-card value,
so the standard light grey is used) with dark text, the website's
exact light pill, and a white phone input; each card shows Pickup
and Drop-off as separate labelled lines (hourly rides show the
pickup line only — they have no drop-off).

Kept unchanged by this change (pinned here): the green Send button
(#25D366 — the owner's WhatsApp-green exception), the quick-reply
chips, the Support heading/intro text, the black brand header, the
black bottom tab bar, the light-blue buttons (#5b9bd5 — "Show my
rides" and "View this ride"), the price breakdown, the trip chat
(chat with the chauffeur — .chat-msg.theirs stays dark), the
status view's one-line ride label, and the website itself (it loads
customer.css, not customer-app.css).

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


class WhiteSupportBubblesTest(unittest.TestCase):
    """The assistant's bubbles on the Support screen are white."""

    def test_assistant_bubble_is_white(self):
        css = _read("static/css/customer-app.css")
        bot = _rule(css, ".msg.bot")
        self.assertIn("background: var(--white);", bot)
        self.assertIn("border: 1px solid var(--line);", bot)
        self.assertIn("color: var(--ink);", bot)
        self.assertNotIn("#2a2a2c", bot)
        self.assertNotIn("#3a3a3e", bot)
        self.assertNotIn("var(--soft)", bot)

    def test_customer_bubble_stays_light_and_distinct(self):
        # The customer's own bubble stays light grey with a gold
        # border — still easy to tell apart from the white
        # assistant bubble, and still light (no black).
        css = _read("static/css/customer-app.css")
        user = _rule(css, ".msg.user")
        self.assertIn("background: #f2f2f2;", user)
        self.assertIn("color: var(--black);", user)
        self.assertNotIn("var(--black)", user.split("color:")[0])
        self.assertNotIn("#2a2a2c", user)

    def test_support_renders_msg_bubbles(self):
        # The Support tab builds its bubbles as .msg user / .msg bot
        # (supportAddMsg in customer-app.js) — the rules above are
        # the ones that actually paint them.
        js = _read("static/js/customer-app.js")
        self.assertIn('div.className = "msg " + who;', js)
        self.assertIn('supportAddMsg("bot",', js)
        html = _read("static/customer-app.html")
        self.assertIn('id="ca-support-messages"', html)


class WhiteSupportInputTest(unittest.TestCase):
    """The Support screen's message input is white."""

    def test_support_input_is_white(self):
        css = _read("static/css/customer-app.css")
        field = _rule(css, ".chat-form input")
        self.assertIn("background: #ffffff;", field)
        self.assertIn("color: var(--ink);", field)
        self.assertIn("border: 1px solid #cfccc2;", field)
        self.assertNotIn("#262628", field)
        self.assertNotIn("#3a3a3e", field)
        self.assertNotIn("var(--white)", field)

    def test_support_input_placeholder_is_readable_grey(self):
        css = _read("static/css/customer-app.css")
        ph = _rule(css, ".chat-form input::placeholder")
        self.assertIn("color: #8e8e93;", ph)

    def test_support_input_focus_is_light(self):
        # Near-black focus border + light ring, like the booking
        # fields — no gold border, no white glow.
        css = _read("static/css/customer-app.css")
        focus = _rule(css, ".chat-form input:focus")
        self.assertIn("border-color: #1a1a1a;", focus)
        self.assertIn("rgba(0, 0, 0, 0.25)", focus)
        self.assertNotIn("var(--gold)", focus)
        self.assertNotIn("rgba(255, 255, 255, 0.28)", focus)


class SupportUnchangedTest(unittest.TestCase):
    """What this change deliberately did not touch."""

    def test_send_button_stays_whatsapp_green(self):
        css = _read("static/css/customer-app.css")
        send = _rule(css, "#ca-chat-send,\n#ca-support-send")
        self.assertIn("background: #25D366;", send)
        self.assertIn("color: var(--white);", send)

    def test_trip_chat_stays_dark(self):
        # The chauffeur chat (post-booking) keeps its dark bubbles
        # and dark input — this change is Support-screen only.
        css = _read("static/css/customer-app.css")
        theirs = _rule(css, ".chat-msg.theirs")
        self.assertIn("background: #2a2a2c;", theirs)
        self.assertIn("color: var(--soft);", theirs)
        trip_input = _rule(css, ".chat-input-row input")
        self.assertIn("background: #262628;", trip_input)
        self.assertIn("color: var(--white);", trip_input)

    def test_header_and_buttons_unchanged(self):
        css = _read("static/css/customer-app.css")
        self.assertIn("--blue: #5b9bd5;", css)
        # The brand header stays black.
        header = _rule(css, ".app-head")
        self.assertIn("background: var(--black);", header)

    def test_website_chat_widget_untouched(self):
        # The website's own widget is already white — this change
        # aligned the app to it, and touched no website file.
        css = _read("static/css/customer.css")
        bot = _rule(css, ".msg.bot")
        self.assertIn("background: var(--white);", bot)
        self.assertIn("border: 1px solid var(--line);", bot)
        field = _rule(css, ".chat-form input")
        self.assertIn("border: 1px solid #cfccc2;", field)


class LightGreyMyRidesTest(unittest.TestCase):
    """The My Rides ride cards are light grey, not black."""

    def test_ride_cards_are_light_grey(self):
        css = _read("static/css/customer-app.css")
        card = _rule(css, ".history-item")
        self.assertIn("background: #f5f5f5;", card)
        self.assertIn("border: 1px solid var(--line);", card)
        self.assertNotIn("var(--card)", card)
        self.assertNotIn("#1d1d1f", card)
        self.assertIn("color: var(--ink);",
                      _rule(css, ".history-item .h-route"))
        self.assertIn("color: #6b6b6b;",
                      _rule(css, ".history-item .h-meta"))

    def test_status_pill_is_light_like_website(self):
        # The website's history pill: #f7f7f7 bg, #cfcfcf border,
        # #4a4a4a text. The app's pill is used only in history
        # items, so it takes the website's values directly.
        css = _read("static/css/customer-app.css")
        pill = _rule(css, ".pill")
        self.assertIn("background: #f7f7f7;", pill)
        self.assertIn("color: #4a4a4a;", pill)
        self.assertIn("border: 1px solid #cfcfcf;", pill)
        self.assertNotIn("rgba(255, 255, 255", pill)

    def test_history_phone_input_is_white(self):
        # Same white field as the booking page: white bg, dark
        # text, the website's #cfccc2 border, readable placeholder,
        # near-black focus.
        css = _read("static/css/customer-app.css")
        self.assertIn("#ca-history-form .field input",
                      _read("static/css/customer-app.css"))
        body = _rule(css, "#ca-history-form .field input")
        self.assertIn("background: #ffffff;", body)
        self.assertIn("color: var(--ink);", body)
        self.assertIn("border: 1px solid #cfccc2;", body)
        self.assertIn("color: #8e8e93;",
                      _rule(css, "#ca-history-form .field input::placeholder"))
        focus = _rule(css, "#ca-history-form .field input:focus")
        self.assertIn("border-color: #1a1a1a;", focus)
        self.assertNotIn("#1d1d1f", body)
        html = _read("static/customer-app.html")
        self.assertIn('id="ca-history-phone"', html)


class MyRidesTwoLineRouteTest(unittest.TestCase):
    """Pickup and Drop-off show on two separate lines per card."""

    def test_history_route_renders_two_labelled_lines(self):
        js = _read("static/js/customer-app.js")
        self.assertIn("function historyRouteHtml(b)", js)
        start = js.index("function historyRouteHtml(b)")
        fn = js[start:start + 1200]
        self.assertIn('class="route-leg"', fn)
        self.assertIn('class="route-label"', fn)
        self.assertIn('class="route-sep"', fn)
        self.assertIn('T("status.pickup_label", "Pickup")', fn)
        self.assertIn('T("status.dropoff_label", "Drop-off")', fn)
        self.assertIn("↓", fn)

    def test_hourly_rides_show_pickup_only(self):
        # Hourly rides have no drop-off: the helper returns after
        # the pickup leg, with no separator and no drop-off leg.
        js = _read("static/js/customer-app.js")
        start = js.index("function historyRouteHtml(b)")
        fn = js[start:start + 1200]
        self.assertIn('if (b.ride_type === "hourly" || !b.dropoff) return pickup;', fn)

    def test_history_list_uses_two_line_route(self):
        js = _read("static/js/customer-app.js")
        start = js.index("function renderHistoryList(")
        fn = js[start:start + 1500]
        self.assertIn("historyRouteHtml(b)", fn)
        self.assertNotIn("rideLabel(b)", fn)

    def test_status_view_ride_label_unchanged(self):
        # rideLabel() still builds the one-line "pickup → dropoff"
        # for the status view — only the history cards split it.
        js = _read("static/js/customer-app.js")
        start = js.index("function rideLabel(b)")
        fn = js[start:start + 600]
        self.assertIn('"  →  "', fn)

    def test_route_labels_have_translations(self):
        # Both T() keys the helper uses must exist in the i18n
        # dictionary with all 19 languages (test_language_switcher
        # fails the build otherwise — every T() key must exist).
        i18n = _read("static/js/i18n.js")
        for key in ('"status.pickup_label"', '"status.dropoff_label"'):
            self.assertIn("NOEL_I18N[%s]" % key, i18n, key)
        import json
        m = re.search(r'NOEL_I18N\["status\.dropoff_label"\] = (\{[^}]*\});',
                      i18n, re.S)
        self.assertIsNotNone(m, "status.dropoff_label entry missing")
        langs = json.loads(m.group(1))
        self.assertEqual(len(langs), 19)
        self.assertEqual(langs["en"], "Drop-off")

    def test_route_leg_styles_exist(self):
        css = _read("static/css/customer-app.css")
        self.assertIn("display: block;",
                      _rule(css, ".history-item .route-leg"))
        label = _rule(css, ".history-item .route-label")
        self.assertIn("color: #6b6b6b;", label)
        self.assertIn("font-weight: 600;", label)
        self.assertIn("display: block;",
                      _rule(css, ".history-item .route-sep"))


class MyRidesUnchangedTest(unittest.TestCase):
    """What the My Rides change deliberately did not touch."""

    def test_header_and_tab_bar_stay_black(self):
        css = _read("static/css/customer-app.css")
        self.assertIn("background: var(--black);",
                      _rule(css, ".app-head"))
        self.assertIn("background: var(--black);",
                      _rule(css, ".tabbar"))

    def test_ride_buttons_stay_light_blue(self):
        # "Show my rides" (.btn-primary) and "View this ride"
        # (.btn-ghost) are both the light-blue primary buttons.
        css = _read("static/css/customer-app.css")
        self.assertIn("background: var(--blue);",
                      _rule(css, ".btn-ghost"))
        self.assertIn("--blue: #5b9bd5;", css)


if __name__ == "__main__":
    unittest.main()
