"""Tests for the driver trip chat opening on accept.

Owner requirement 2026-11-18 (voice call): "Driver jaisa trip accept
karega, jab uske paas chat box khulna chahiye" — the moment the driver
accepts a trip, the chat box must OPEN for him.

BEFORE: accepting an offer ran renderTrip() + showScreen("trip"), and
showScreen lands at the TOP of the trip screen (window.scrollTo(0, 0)),
while the chat box sits at the BOTTOM of the trip screen — trip card,
stage list, buttons, cancel button, then the chat — well below the
fold on a phone. The box was always expanded (never collapsed or
hidden), but the driver had to scroll down himself to find it. Nothing
brought it into view.

NOW: the accept path scrolls the chat box into view at once, with no
extra tap or scroll from the driver, using the same scrollIntoView
pattern the customer side already uses. Only the accept path does this:
restoring an active trip on reload must not yank the driver to the
chat, and declining (or a failed accept) never opens it.

NOT a support widget: the owner CANCELLED the driver-side 'Chat with
us' widget in the same call ('nahi nahi driver ko nahi chahiye'). The
driver app must not gain one — these tests pin its absence. Trip-chat
gating and translation are untouched.

Run:  python -m unittest discover -s tests -v
"""

import os
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


class ChatOpensOnAcceptCase(unittest.TestCase):
    def test_accept_path_opens_chat_after_showing_trip_screen(self):
        driver_js = read("static/js/driver.js")
        handler = extract_function(driver_js, "function respondToOffer(id, action)")
        # The chat must open AFTER showScreen("trip"): showScreen
        # scrolls to the top, which would undo an earlier scroll.
        self.assertIn('showScreen("trip");', handler)
        self.assertIn("openTripChatOnAccept();", handler)
        self.assertLess(handler.index('showScreen("trip");'),
                        handler.index("openTripChatOnAccept();"))

    def test_helper_scrolls_chat_box_into_view(self):
        driver_js = read("static/js/driver.js")
        helper = extract_function(driver_js, "function openTripChatOnAccept()")
        self.assertIn('$("trip-chat")', helper)
        # Same scrollIntoView pattern the customer side uses.
        self.assertIn('scrollIntoView({ behavior: "smooth", block: "start" })',
                      helper)

    def test_chat_opens_only_on_accept(self):
        driver_js = read("static/js/driver.js")
        # Exactly two mentions: the definition and the single call
        # site in the accept path. No other caller (in particular
        # not restoreActiveTrip, which runs on every reload).
        self.assertEqual(driver_js.count("openTripChatOnAccept"), 2)
        restore = extract_function(driver_js, "function restoreActiveTrip()")
        self.assertNotIn("openTripChatOnAccept", restore)

    def test_decline_and_failed_accept_never_open_chat(self):
        driver_js = read("static/js/driver.js")
        handler = extract_function(driver_js, "function respondToOffer(id, action)")
        # Both early returns sit before the chat-open call, so a
        # decline or a failed accept never reaches it.
        self.assertLess(
            handler.index('if (action === "decline") { refreshOffers(); return; }'),
            handler.index("openTripChatOnAccept();"))
        self.assertLess(
            handler.index("if (!res.ok) { refreshOffers(); return; }"),
            handler.index("openTripChatOnAccept();"))

    def test_chat_box_is_expanded_on_the_trip_screen(self):
        html = read("static/driver.html")
        # Exactly one chat box, on the trip screen, always expanded:
        # no hidden class, no collapse toggle — visibility on accept
        # comes from scrolling it into view, not from un-hiding it.
        self.assertEqual(html.count('id="trip-chat"'), 1)
        self.assertIn('<div class="chat-box" id="trip-chat">', html)
        self.assertNotIn('class="chat-box hidden"', html)
        self.assertLess(html.index('id="screen-trip"'),
                        html.index('id="trip-chat"'))
        self.assertLess(html.index('id="trip-chat"'),
                        html.index('id="screen-earnings"'))

    def test_no_support_widget_on_driver_side(self):
        # Owner cancelled the driver-side 'Chat with us' widget
        # 2026-11-18: the driver does NOT need it. Guard against a
        # re-introduction from the cancelled parallel attempt.
        html = read("static/driver.html")
        driver_js = read("static/js/driver.js")
        for forbidden in ("support-chat", "chat-fab"):
            self.assertNotIn(forbidden, html)
            self.assertNotIn(forbidden, driver_js)

    def test_chat_polling_still_starts_when_trip_renders(self):
        driver_js = read("static/js/driver.js")
        render = extract_function(driver_js, "function renderTrip()")
        self.assertIn("startChatPolling();", render)


if __name__ == "__main__":
    unittest.main()
