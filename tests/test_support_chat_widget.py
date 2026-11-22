"""Tests for the pre-booking 'Chat with us' widget fix (owner
requirement 2026-11-18: the widget must be available ALWAYS — no
booking, no trip, no driver registration — so a customer can ask
BEFORE booking).

ROOT CAUSE FIXED HERE: static/index.html had DUPLICATE element IDs —
the ride-chat panel ('Chat with your chauffeur') and the floating
support widget panel both used id='chat-panel', id='chat-messages'
and id='chat-input'. document.getElementById returns the FIRST
match (the ride-chat elements), so the widget code showed, hid,
wrote into and focused the WRONG elements and the floating panel
never opened: tapping 'Chat with us' looked dead. The widget now
uses unique support-chat-* IDs; the ride chat keeps its IDs and its
accept-gating untouched. The two chats are separate and must stay
separate — do not merge them.

ESCALATION WIRING (agreed 2026-11-15: scripted answers first, Azher
alerted on big/difficult issues): the widget's scripted answers
already promised owner escalation + 'team replies within 24 hours',
but the widget sent NOTHING to the server. Typed messages are now
stored via POST /api/support-messages (no login/booking required,
fail-soft) and listed in the owner dashboard under the owner PIN.

Scripted answers only — NO LLM/AI backend exists here or is wanted;
the answer facts are pinned verbatim below.

Run:  python -m unittest discover -s tests -v
"""

import io
import os
import re
import sys
import tempfile
import unittest
from collections import Counter

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-supportchat-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "supportchat-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo (same as the other API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
import translation as translation_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Support Chat Customer"}


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def widget_block(customer_js):
    marker = "Chat widget (scripted answers only)"
    start = customer_js.index(marker)
    return customer_js[start:]


class SupportChatWidgetCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    # -- helpers (same shapes as test_free_features) ---------------------
    def register_driver(self, car_model="Cadillac CT6"):
        self._driver_seq += 1
        phone = f"+1555007{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Support Driver {self._driver_seq}", "phone": phone,
            "email": f"sd{self._driver_seq}@test.com",
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
            "customer_name": "Support Chat Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "support@test.com",
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

    def pay(self, booking_id):
        return self.client.post(f"/api/bookings/{booking_id}/pay", json=dict(CARD))

    def accept(self, booking_id, token):
        return self.client.post(f"/api/drivers/me/offers/{booking_id}/accept",
                                json={}, headers={"X-Driver-Token": token})

    def owner_login(self):
        resp = self.client.post("/api/owner/login", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)

    # -- (a) no duplicate IDs ----------------------------------------------
    def test_no_duplicate_ids_in_customer_pages(self):
        for rel in ("static/index.html", "static/driver.html", "static/owner.html"):
            html = read(rel)
            ids = re.findall(r'id="([^"]+)"', html)
            dupes = [i for i, c in Counter(ids).items() if c > 1]
            self.assertEqual(dupes, [], f"duplicate id(s) in {rel}: {dupes}")

    # -- (b) widget opens with no booking: unique IDs resolve to it --------
    def test_widget_has_unique_ids_and_ride_chat_keeps_its_ids(self):
        html = read("static/index.html")
        # The floating widget panel: class chat-panel (fixed bottom-right
        # styling) with its OWN id, plus its own messages/chips/form/input.
        self.assertIn('id="support-chat-panel"', html)
        self.assertIn('id="support-chat-messages"', html)
        self.assertIn('id="support-chat-chips"', html)
        self.assertIn('id="support-chat-form"', html)
        self.assertIn('id="support-chat-input"', html)
        self.assertIn('id="chat-fab"', html)
        self.assertIn('id="chat-close"', html)
        # "Open chat" lives in the Contacts section, which moved to its
        # own page in the 2026-11-21 homepage split.
        self.assertIn('id="open-chat-btn"', read("static/contacts.html"))
        # The ride chat keeps the original IDs (exactly one of each —
        # the no-duplicate test above proves the count).
        self.assertIn('<div id="chat-panel" class="hidden">', html)
        self.assertIn("Chat with your chauffeur", html)
        self.assertIn('id="chat-send"', html)
        # The widget panel is the element carrying the dialog role.
        self.assertIn('id="support-chat-panel" role="dialog"', html)

    def test_widget_js_targets_widget_elements_not_ride_chat(self):
        block = widget_block(read("static/js/customer.js"))
        # Every element lookup in the widget block resolves to a
        # support-chat-* element — never to the ride chat's IDs.
        self.assertIn('$("support-chat-panel")', block)
        self.assertIn('$("support-chat-messages")', block)
        self.assertIn('$("support-chat-input")', block)
        self.assertIn('$("support-chat-form")', block)
        self.assertIn('"#support-chat-chips button"', block)
        for bare in ('$("chat-panel")', '$("chat-messages")',
                     '$("chat-input")', '$("chat-form")', '"#chat-chips'):
            self.assertNotIn(bare, block,
                             f"widget block must not look up ride-chat {bare}")
        # FAB toggles the widget panel, close + Contacts buttons wire up.
        self.assertIn('$("chat-fab").addEventListener("click"', block)
        self.assertIn('$("chat-close").addEventListener("click"', block)
        self.assertIn('$("open-chat-btn").addEventListener("click", openChat)', block)

    def test_widget_needs_no_booking_state(self):
        # The widget block never consults booking state: no bookingId,
        # no status gate, no phone check — it opens on a fresh page.
        block = widget_block(read("static/js/customer.js"))
        for gated in ("bookingId", "bookingPhone", "CHAT_OPEN_STATUSES",
                      "chatOpenFor", "loadChatIfOpen"):
            self.assertNotIn(gated, block,
                             f"widget must not depend on {gated}")
        # The FAB is plain markup on the page, outside any gated panel.
        self.assertIn("Chat with us", read("static/index.html"))

    def test_widget_styling_is_class_based(self):
        # The widget keeps its fixed bottom-right look from classes
        # alone; no #support-chat-* ID rules are needed, and the
        # #chat-panel rules style only the ride panel now.
        css = read("static/css/customer.css")
        self.assertIn(".chat-panel {", css)
        self.assertIn("position: fixed; right: 20px; bottom: 76px;", css)
        self.assertIn(".chat-fab {", css)
        self.assertNotIn("#support-chat-panel", css)

    def test_widget_scripted_answers_unchanged(self):
        js = read("static/js/customer.js")
        # Every answer's facts pinned verbatim — the fix must not
        # rewrite what the widget says.
        for snippet in (
            "Cancellation is free if you cancel more than 1 hour before pickup",
            "Waiting is free for 60 minutes at airports and 15 minutes at other pickups",
            "Bookings are open",
            "you will see the total for each class before you pay",
            "Unclaimed items go to the police station after one week",
            "I will escalate this to the owner, who will look into it personally",
            "you will see their name, phone number, car, colour and plate number",
            "Business Class, Business SUV and First Class — recent high-end cars",
            "book a second one-way ride",
            "Choose the “By the hour” tab in the booking form",
            "open their referral link",
            "The team replies within 24 hours",
        ):
            self.assertIn(snippet, js)

    # -- (c) ride chat still gated + translation unchanged ------------------
    def test_ride_chat_still_gated_on_accept(self):
        booking = self.book()
        # No driver has accepted: trip chat stays closed (409).
        resp = self.client.post(f"/api/bookings/{booking['id']}/messages",
                                json={"phone": booking["phone"], "text": "hello"})
        self.assertEqual(resp.status_code, 409)
        resp = self.client.get(f"/api/bookings/{booking['id']}/messages",
                               query_string={"phone": booking["phone"]})
        self.assertEqual(resp.status_code, 409)
        # After pay + accept, the same chat opens.
        _, token = self.register_driver()
        self.assertEqual(self.pay(booking["id"]).status_code, 200)
        self.assertEqual(self.accept(booking["id"], token).status_code, 200)
        resp = self.client.post(f"/api/bookings/{booking['id']}/messages",
                                json={"phone": booking["phone"], "text": "hello"})
        self.assertEqual(resp.status_code, 201)

    def test_translation_wiring_unchanged(self):
        self.assertEqual(
            set(translation_module.CHAT_LANGUAGES),
            {"en", "ur-Latn", "es", "fr", "ar", "hi", "bn", "pt"})
        customer_js = read("static/js/customer.js")
        self.assertIn("ride-chat-language", customer_js)
        self.assertIn("/chat-language", customer_js)
        self.assertIn("ur-Latn", customer_js)

    # -- (d) support endpoint + owner list + fail-soft ----------------------
    def test_support_endpoint_stores_and_flags(self):
        resp = self.client.post("/api/support-messages",
                                json={"text": "How do I book a ride?"})
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()["message"]
        self.assertEqual(body["text"], "How do I book a ride?")
        self.assertFalse(body["flagged"])
        self.assertIn("created_at", body)

        resp = self.client.post("/api/support-messages",
                                json={"text": "I have a problem with my driver"})
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.get_json()["message"]["flagged"])

        resp = self.client.post("/api/support-messages",
                                json={"text": "I left my bag in the car"})
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.get_json()["message"]["flagged"])

    def test_support_endpoint_validates_text(self):
        for payload, why in (( {"text": ""}, "empty"),
                             ( {"text": "   "}, "blank"),
                             ( {"text": "x" * 501}, "too long"),
                             ( {"text": 123}, "non-string"),
                             ( {}, "missing")):
            resp = self.client.post("/api/support-messages", json=payload)
            self.assertEqual(resp.status_code, 400, why)
        # No login and no booking required: the plain client above
        # (never logged in) stored messages in the previous test.
        resp = self.client.post("/api/support-messages",
                                json={"text": "  padded question?  "})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["message"]["text"], "padded question?")

    def test_owner_support_list_requires_auth_and_is_newest_first(self):
        self.client.post("/api/support-messages", json={"text": "first question"})
        self.client.post("/api/support-messages",
                         json={"text": "second, a complaint about a ride"})
        # Logged out: denied.
        resp = self.client.get("/api/owner/support-messages")
        self.assertEqual(resp.status_code, 401)
        # Logged in: newest first, flagged marked.
        self.owner_login()
        resp = self.client.get("/api/owner/support-messages")
        self.assertEqual(resp.status_code, 200)
        messages = resp.get_json()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["text"], "second, a complaint about a ride")
        self.assertTrue(messages[0]["flagged"])
        self.assertEqual(messages[1]["text"], "first question")
        self.assertFalse(messages[1]["flagged"])

    def test_widget_reports_typed_messages_fail_soft(self):
        block = widget_block(read("static/js/customer.js"))
        # Typed text is reported via a fire-and-forget POST whose
        # failure is swallowed; the scripted answer path never waits
        # on it (handleQuestion answers via setTimeout regardless).
        self.assertIn('fetch("/api/support-messages"', block)
        self.assertIn(".catch(function ()", block)
        self.assertIn("setTimeout(function () { addMsg(\"bot\", answer(q)); }", block)
        # Only the typed-text submit reports; chip taps just answer.
        submit = block[block.index("support-chat-form"):]
        self.assertIn("reportToOwner(q)", submit)
        chips = block[block.index("support-chat-chips"):]
        self.assertNotIn("reportToOwner", chips)

    def test_owner_dashboard_shows_support_feed(self):
        owner_html = read("static/owner.html")
        self.assertIn("Support messages", owner_html)
        self.assertIn('id="support-feed"', owner_html)
        owner_js = read("static/js/owner.js")
        self.assertIn("loadSupportMessages", owner_js)
        self.assertIn('fetch("/api/owner/support-messages"', owner_js)
        self.assertIn("Needs attention", owner_js)
        self.assertIn('esc(m.text', owner_js)

    def test_clear_rides_keeps_support_messages(self):
        self.client.post("/api/support-messages", json={"text": "kept question"})
        self.owner_login()
        resp = self.client.post("/api/owner/clear-rides", json={"pin": "9999"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get("/api/owner/support-messages")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([m["text"] for m in resp.get_json()], ["kept question"])


if __name__ == "__main__":
    unittest.main()
