"""Tests for the Azure Translator chat translation (owner decision
2026-11-18: each side reads replies in their own language; driver
writing Roman Urdu gets replies IN Roman Urdu; other languages too).

TEXT only — no speech/voice work exists here or anywhere in the chat.
Design under test:
* Azure Translator F0, key/region/endpoint from env vars only.
* Roman Urdu via the two-hop (transliterate + translate), both ways.
* Translate ONCE at send time and store; reads never translate.
* DECLARED language preference (picker), never auto-detection.
* Fail-soft: no key / HTTP error / timeout / bad response -> the
  original text is stored and shown, chat never breaks, no error.
* No key configured -> behaviour identical to before translation.

All Azure HTTP is mocked (no real network, no real key). The mocked
responses use the shapes from the official Translator REST API v3.0
docs: translate -> [{"translations": [{"text": ...}]}],
transliterate -> [{"text": ..., "script": ...}].

Run:  python -m unittest discover -s tests -v
"""

import io
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-chatxl-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "chatxl.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "chatxl-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo: every one-way ride is 18.0 miles (same as the other
# API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402
import photo_factory  # noqa: E402
import translation as translation_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = {"card_number": "4242424242424242", "card_exp": "12/30",
        "card_cvc": "123", "card_name": "Chat Translation Customer"}
FORBIDDEN_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                  "fare_total", "customer_total", "subtotal", "profit", "tax"}
ALL_LANGUAGES = ["en", "ur-Latn", "es", "fr", "ar", "hi", "bn", "pt"]


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class FakeResponse:
    """Minimal urlopen response: context manager + read()."""

    def __init__(self, raw):
        self._raw = raw if isinstance(raw, bytes) else json.dumps(raw).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def request_headers(request):
    return {k.lower(): v for k, v in request.header_items()}


def request_query(request):
    return {k: v[0] for k, v in parse_qs(urlparse(request.full_url).query).items()}


def request_text(request):
    return json.loads(request.data.decode("utf-8"))[0]["Text"]


def scripted_urlopen(calls, script):
    """urlopen fake: pops one scripted payload/exception per call.

    Script items are response payloads (returned as JSON) or
    exceptions (raised). Every request is appended to `calls`.
    """

    def _fake(request, timeout=None):
        calls.append(request)
        item = script.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item)

    return _fake


def smart_urlopen(calls):
    """urlopen fake that answers like Azure, deterministically.

    Transliterate answers "SCRIPT:<input>"; translate answers
    "TEXT:<to>:<input>". The composed strings prove hop order: a
    Roman-Urdu-in message reaches the customer as
    "TEXT:en:SCRIPT:<original>".
    """

    def _fake(request, timeout=None):
        calls.append(request)
        query = request_query(request)
        text = request_text(request)
        if "/transliterate" in request.full_url:
            return FakeResponse([{"text": "SCRIPT:" + text, "script": query["toScript"]}])
        return FakeResponse([{"translations": [{"text": "TEXT:" + query["to"] + ":" + text,
                                                "to": query["to"]}]}])

    return _fake


def azure_env():
    return {"AZURE_TRANSLATOR_KEY": "test-key-123",
            "AZURE_TRANSLATOR_REGION": "eastus"}


class TranslationUnitCase(unittest.TestCase):
    """Pure translation-module tests: mocked HTTP, no Flask involved."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        for key in ("AZURE_TRANSLATOR_KEY", "AZURE_TRANSLATOR_REGION",
                    "AZURE_TRANSLATOR_ENDPOINT"):
            os.environ.pop(key, None)

    def tearDown(self):
        self.setUp()

    def test_same_language_makes_no_api_call(self):
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen") as fake:
                self.assertIsNone(translation_module.translate_chat_text(
                    "hello", "en", "en"))
                self.assertIsNone(translation_module.translate_chat_text(
                    "salam", "ur-Latn", "ur-Latn"))
                fake.assert_not_called()

    def test_missing_key_makes_no_api_call(self):
        with mock.patch.object(translation_module, "urlopen") as fake:
            self.assertIsNone(translation_module.translate_chat_text(
                "hello", "en", "es"))
            fake.assert_not_called()

    def test_empty_text_makes_no_api_call(self):
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen") as fake:
                self.assertIsNone(translation_module.translate_chat_text(
                    "   ", "en", "es"))
                fake.assert_not_called()

    def test_direct_translate_request_shape(self):
        calls = []
        script = [[{"translations": [{"text": "Hola", "to": "es"}]}]]
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=scripted_urlopen(calls, script)):
                result = translation_module.translate_chat_text("Hello", "en", "es")
        self.assertEqual(result, "Hola")
        self.assertEqual(len(calls), 1)
        req = calls[0]
        self.assertTrue(req.full_url.startswith(
            "https://api.cognitive.microsofttranslator.com/translate?"))
        query = request_query(req)
        self.assertEqual(query["api-version"], "3.0")
        self.assertEqual(query["from"], "en")  # declared source, never auto-detect
        self.assertEqual(query["to"], "es")
        headers = request_headers(req)
        self.assertEqual(headers["ocp-apim-subscription-key"], "test-key-123")
        self.assertEqual(headers["ocp-apim-subscription-region"], "eastus")
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(request_text(req), "Hello")
        self.assertEqual(req.get_method(), "POST")

    def test_region_header_omitted_when_unset(self):
        calls = []
        script = [[{"translations": [{"text": "Bonjour", "to": "fr"}]}]]
        with mock.patch.dict(os.environ, {"AZURE_TRANSLATOR_KEY": "k1"}):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=scripted_urlopen(calls, script)):
                self.assertEqual(
                    translation_module.translate_chat_text("Hello", "en", "fr"),
                    "Bonjour")
        self.assertNotIn("ocp-apim-subscription-region", request_headers(calls[0]))

    def test_endpoint_override_used(self):
        calls = []
        script = [[{"translations": [{"text": "Hola", "to": "es"}]}]]
        env = dict(azure_env(), AZURE_TRANSLATOR_ENDPOINT="https://example.invalid/translator/")
        with mock.patch.dict(os.environ, env):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=scripted_urlopen(calls, script)):
                translation_module.translate_chat_text("Hello", "en", "es")
        self.assertTrue(calls[0].full_url.startswith(
            "https://example.invalid/translator/translate?"))

    def test_roman_urdu_in_two_hops(self):
        calls = []
        script = [
            [{"text": "SCRIPT-URDU", "script": "Arab"}],
            [{"translations": [{"text": "I am coming", "to": "en"}]}],
        ]
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=scripted_urlopen(calls, script)):
                result = translation_module.translate_chat_text(
                    "main aa raha hoon", "ur-Latn", "en")
        self.assertEqual(result, "I am coming")
        self.assertEqual(len(calls), 2)
        # Hop 1: transliterate Roman Urdu -> Urdu script.
        self.assertIn("/transliterate", calls[0].full_url)
        q1 = request_query(calls[0])
        self.assertEqual(q1["language"], "ur")
        self.assertEqual(q1["fromScript"], "Latn")
        self.assertEqual(q1["toScript"], "Arab")
        self.assertEqual(request_text(calls[0]), "main aa raha hoon")
        # Hop 2: translate Urdu script -> English.
        self.assertIn("/translate", calls[1].full_url)
        q2 = request_query(calls[1])
        self.assertEqual(q2["from"], "ur")
        self.assertEqual(q2["to"], "en")
        self.assertEqual(request_text(calls[1]), "SCRIPT-URDU")

    def test_roman_urdu_out_two_hops(self):
        calls = []
        script = [
            [{"translations": [{"text": "SCRIPT-URDU", "to": "ur"}]}],
            [{"text": "main aa raha hoon", "script": "Latn"}],
        ]
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=scripted_urlopen(calls, script)):
                result = translation_module.translate_chat_text(
                    "I am coming", "en", "ur-Latn")
        self.assertEqual(result, "main aa raha hoon")
        self.assertEqual(len(calls), 2)
        # Hop 1: translate English -> Urdu script.
        self.assertIn("/translate", calls[0].full_url)
        q1 = request_query(calls[0])
        self.assertEqual(q1["from"], "en")
        self.assertEqual(q1["to"], "ur")
        # Hop 2: transliterate Urdu script -> Roman Urdu.
        self.assertIn("/transliterate", calls[1].full_url)
        q2 = request_query(calls[1])
        self.assertEqual(q2["language"], "ur")
        self.assertEqual(q2["fromScript"], "Arab")
        self.assertEqual(q2["toScript"], "Latn")
        self.assertEqual(request_text(calls[1]), "SCRIPT-URDU")

    def test_first_hop_failure_skips_second_hop(self):
        calls = []
        script = [HTTPError("https://x.invalid/", 400, "Bad Request", {}, None)]
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=scripted_urlopen(calls, script)):
                self.assertIsNone(translation_module.translate_chat_text(
                    "main aa raha hoon", "ur-Latn", "en"))
        self.assertEqual(len(calls), 1)  # transliterate failed; no translate call

    def test_http_error_fails_soft(self):
        calls = []
        script = [HTTPError("https://x.invalid/", 403, "Quota exceeded", {}, None)]
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=scripted_urlopen(calls, script)):
                self.assertIsNone(translation_module.translate_chat_text(
                    "Hello", "en", "es"))

    def test_timeout_and_network_error_fail_soft(self):
        for error in (TimeoutError("timed out"),
                      URLError("connection reset")):
            calls = []
            script = [error]
            with mock.patch.dict(os.environ, azure_env()):
                with mock.patch.object(translation_module, "urlopen",
                                        side_effect=scripted_urlopen(calls, script)):
                    self.assertIsNone(translation_module.translate_chat_text(
                        "Hello", "en", "es"))

    def test_malformed_response_fails_soft(self):
        bad = [
            FakeResponse(b"this is not json"),
            FakeResponse([{"no_translations": True}]),
            FakeResponse([{"translations": []}]),
            FakeResponse([{"translations": [{"text": "   "}]}]),
            FakeResponse([]),
        ]
        for response in bad:
            with mock.patch.dict(os.environ, azure_env()):
                with mock.patch.object(translation_module, "urlopen",
                                        return_value=response):
                    self.assertIsNone(translation_module.translate_chat_text(
                        "Hello", "en", "es"))

    def test_normalize_chat_language(self):
        for code in ALL_LANGUAGES:
            self.assertEqual(translation_module.normalize_chat_language(code), code)
        self.assertEqual(translation_module.normalize_chat_language("xx"), "en")
        self.assertEqual(translation_module.normalize_chat_language(""), "en")
        self.assertEqual(translation_module.normalize_chat_language(None), "en")
        self.assertEqual(translation_module.normalize_chat_language(42), "en")


class ChatTranslationApiCase(unittest.TestCase):
    """End-to-end chat tests over the Flask test client."""

    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        for key in ("AZURE_TRANSLATOR_KEY", "AZURE_TRANSLATOR_REGION",
                    "AZURE_TRANSLATOR_ENDPOINT"):
            os.environ.pop(key, None)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._driver_seq = 0
        self._phone_seq = 0

    def tearDown(self):
        for key in ("AZURE_TRANSLATOR_KEY", "AZURE_TRANSLATOR_REGION",
                    "AZURE_TRANSLATOR_ENDPOINT"):
            os.environ.pop(key, None)

    # -- helpers ---------------------------------------------------------
    def register_driver(self, car_model="Cadillac CT6"):
        self._driver_seq += 1
        phone = f"+1555007{self._driver_seq:04d}"
        resp = self.client.post("/api/drivers/register", data={
            "name": f"Chat Driver {self._driver_seq}", "phone": phone,
            "email": f"cd{self._driver_seq}@test.com",
            "car_model": car_model, "car_year": "2023", "car_colour": "Black",
            "plate": f"C{self._driver_seq:05d}",
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
        needs a verified sign-in with the booking's email. Signs in
        once per email per test — the session persists for later
        bookings and payments in the same test."""
        if getattr(self, "_signed_in_email", None) == email:
            return
        resp = self.client.post("/api/customers/signin/request",
                                json={"email": email, "phone": phone})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        with app_module.app.app_context():
            row = (app_module.OutboxMessage.query
                   .filter_by(recipient=email, channel="email")
                   .order_by(app_module.OutboxMessage.id.desc()).first())
        self.assertIsNotNone(row, "no sign-in email was queued")
        match = re.search(r"(\d{6})", row.body or "")
        self.assertIsNotNone(match, "no 6-digit code in the email")
        resp = self.client.post("/api/customers/signin/verify",
                                json={"email": email, "code": match.group(1)})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        self._signed_in_email = email

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Chat Translation Customer",
            "phone": f"+1555008{self._phone_seq:04d}",
            "email": "chatxl@test.com",
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

    def accepted_booking(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.client.post(
            f"/api/bookings/{booking['id']}/pay", json=dict(CARD)).status_code, 200)
        resp = self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                                json={}, headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return booking, token

    def driver_messages(self, bid, token, **qs):
        return self.client.get(f"/api/drivers/me/trip/{bid}/messages",
                               query_string=qs,
                               headers={"X-Driver-Token": token})

    def customer_messages(self, bid, phone, **qs):
        params = {"phone": phone}
        params.update(qs)
        return self.client.get(f"/api/bookings/{bid}/messages", query_string=params)

    # -- no key: identical to today ---------------------------------------
    def test_no_key_chat_unchanged(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        with mock.patch.object(translation_module, "urlopen") as fake:
            resp = self.client.post(f"/api/drivers/me/trip/{bid}/messages",
                                    json={"text": "I am on my way."},
                                    headers={"X-Driver-Token": token})
            self.assertEqual(resp.status_code, 201)
            resp = self.client.post(f"/api/bookings/{bid}/messages",
                                    json={"phone": booking["phone"],
                                          "text": "I am at arrivals."})
            self.assertEqual(resp.status_code, 201)
            fake.assert_not_called()
        messages = self.customer_messages(bid, booking["phone"]).get_json()["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["text"], "I am on my way.")
        self.assertEqual(messages[1]["text"], "I am at arrivals.")
        for message in messages:
            self.assertFalse(message["translated"])
            self.assertEqual(message["original_text"], message["text"])
            for key in ("id", "sender", "text", "created_at"):
                self.assertIn(key, message)
            self.assertFalse(FORBIDDEN_KEYS & set(message.keys()))

    def test_legacy_message_without_translation_fields(self):
        booking, token = self.accepted_booking()
        with app_module.app.app_context():
            # A message stored before translation existed: only the
            # original columns are set; the new ones stay NULL.
            app_module.db.session.add(app_module.ChatMessage(
                booking_id=booking["id"], sender="driver", text="Old message."))
            app_module.db.session.commit()
        messages = self.driver_messages(booking["id"], token).get_json()["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["text"], "Old message.")
        self.assertFalse(messages[0]["translated"])

    def test_translation_columns_exist(self):
        from sqlalchemy import inspect as sa_inspect
        with app_module.app.app_context():
            drivers = [c["name"] for c in sa_inspect(app_module.db.engine).get_columns("drivers")]
            bookings = [c["name"] for c in sa_inspect(app_module.db.engine).get_columns("bookings")]
            messages = [c["name"] for c in sa_inspect(app_module.db.engine).get_columns("chat_messages")]
        self.assertIn("chat_language", drivers)
        self.assertIn("customer_chat_language", bookings)
        for col in ("sender_language", "translated_text", "translated_language"):
            self.assertIn(col, messages)

    # -- mocked Azure: both directions ------------------------------------
    def test_driver_roman_urdu_to_customer_english(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        resp = self.client.post("/api/drivers/me/chat-language",
                                json={"language": "ur-Latn"},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        calls = []
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=smart_urlopen(calls)):
                resp = self.client.post(f"/api/drivers/me/trip/{bid}/messages",
                                        json={"text": "main 5 minute mein aa raha hoon"},
                                        headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        # The driver sees his own message exactly as typed.
        self.assertEqual(resp.get_json()["message"]["text"],
                         "main 5 minute mein aa raha hoon")
        self.assertFalse(resp.get_json()["message"]["translated"])
        # Two hops, in order: transliterate, then translate.
        self.assertEqual(len(calls), 2)
        self.assertIn("/transliterate", calls[0].full_url)
        self.assertEqual(request_query(calls[0])["fromScript"], "Latn")
        self.assertIn("/translate", calls[1].full_url)
        self.assertEqual(request_query(calls[1])["from"], "ur")
        self.assertEqual(request_query(calls[1])["to"], "en")
        # The customer (English) reads the stored translation.
        messages = self.customer_messages(bid, booking["phone"]).get_json()["messages"]
        self.assertEqual(messages[0]["text"],
                         "TEXT:en:SCRIPT:main 5 minute mein aa raha hoon")
        self.assertTrue(messages[0]["translated"])
        self.assertEqual(messages[0]["original_text"], "main 5 minute mein aa raha hoon")

    def test_customer_english_to_driver_roman_urdu(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        self.client.post("/api/drivers/me/chat-language",
                         json={"language": "ur-Latn"},
                         headers={"X-Driver-Token": token})
        calls = []
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=smart_urlopen(calls)):
                resp = self.client.post(
                    f"/api/bookings/{bid}/messages",
                    json={"phone": booking["phone"], "text": "I am at Terminal 4."})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(calls), 2)
        self.assertIn("/translate", calls[0].full_url)
        self.assertEqual(request_query(calls[0])["to"], "ur")
        self.assertIn("/transliterate", calls[1].full_url)
        self.assertEqual(request_query(calls[1])["fromScript"], "Arab")
        self.assertEqual(request_query(calls[1])["toScript"], "Latn")
        # The driver (Roman Urdu) reads the stored translation.
        messages = self.driver_messages(bid, token).get_json()["messages"]
        self.assertEqual(messages[0]["text"], "SCRIPT:TEXT:ur:I am at Terminal 4.")
        self.assertTrue(messages[0]["translated"])
        # The customer sees her own message exactly as typed.
        messages = self.customer_messages(bid, booking["phone"]).get_json()["messages"]
        self.assertEqual(messages[0]["text"], "I am at Terminal 4.")
        self.assertFalse(messages[0]["translated"])

    def test_direct_translate_other_languages(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        self.client.post("/api/drivers/me/chat-language",
                         json={"language": "es"},
                         headers={"X-Driver-Token": token})
        calls = []
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=smart_urlopen(calls)):
                resp = self.client.post(
                    f"/api/bookings/{bid}/messages",
                    json={"phone": booking["phone"], "text": "Hello"})
        self.assertEqual(resp.status_code, 201)
        # Direct pair: exactly one translate call, no transliteration.
        self.assertEqual(len(calls), 1)
        self.assertIn("/translate", calls[0].full_url)
        self.assertEqual(request_query(calls[0])["from"], "en")
        self.assertEqual(request_query(calls[0])["to"], "es")
        messages = self.driver_messages(bid, token).get_json()["messages"]
        self.assertEqual(messages[0]["text"], "TEXT:es:Hello")

    def test_same_language_no_api_call_with_key(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen") as fake:
                self.assertEqual(self.client.post(
                    f"/api/drivers/me/trip/{bid}/messages",
                    json={"text": "On my way."},
                    headers={"X-Driver-Token": token}).status_code, 201)
                self.assertEqual(self.client.post(
                    f"/api/bookings/{bid}/messages",
                    json={"phone": booking["phone"], "text": "Thanks."}).status_code, 201)
                fake.assert_not_called()

    def test_azure_failure_message_still_saved_original(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        self.client.post("/api/drivers/me/chat-language",
                         json={"language": "ur-Latn"},
                         headers={"X-Driver-Token": token})
        calls = []
        script = [HTTPError("https://x.invalid/", 403, "Quota exceeded", {}, None)]
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=scripted_urlopen(calls, script)):
                resp = self.client.post(
                    f"/api/bookings/{bid}/messages",
                    json={"phone": booking["phone"], "text": "Where are you?"})
        # No error shown: the message is stored and both sides read it.
        self.assertEqual(resp.status_code, 201)
        for messages in (self.driver_messages(bid, token).get_json()["messages"],
                         self.customer_messages(bid, booking["phone"]).get_json()["messages"]):
            self.assertEqual(messages[0]["text"], "Where are you?")
            self.assertFalse(messages[0]["translated"])

    def test_reads_never_translate(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        self.client.post("/api/drivers/me/chat-language",
                         json={"language": "ur-Latn"},
                         headers={"X-Driver-Token": token})
        calls = []
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=smart_urlopen(calls)):
                self.assertEqual(self.client.post(
                    f"/api/bookings/{bid}/messages",
                    json={"phone": booking["phone"], "text": "Hello"}).status_code, 201)
        send_calls = len(calls)
        self.assertEqual(send_calls, 2)
        # Polling (the 3-4s loop) must never call Azure again.
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen") as fake:
                for _ in range(3):
                    self.assertEqual(self.driver_messages(bid, token).status_code, 200)
                    self.assertEqual(
                        self.customer_messages(bid, booking["phone"]).status_code, 200)
                fake.assert_not_called()

    def test_language_change_after_send_shows_original(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        self.client.post("/api/drivers/me/chat-language",
                         json={"language": "ur-Latn"},
                         headers={"X-Driver-Token": token})
        calls = []
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=smart_urlopen(calls)):
                self.client.post(f"/api/drivers/me/trip/{bid}/messages",
                                 json={"text": "main aa raha hoon"},
                                 headers={"X-Driver-Token": token})
        # Stored translation is English. Customer switches to Spanish:
        # the old message falls back to the original (no re-translation
        # on read); a NEW message is translated into Spanish.
        self.client.post(f"/api/bookings/{bid}/chat-language",
                         json={"phone": booking["phone"], "language": "es"})
        messages = self.customer_messages(bid, booking["phone"]).get_json()["messages"]
        self.assertEqual(messages[0]["text"], "main aa raha hoon")
        self.assertFalse(messages[0]["translated"])
        with mock.patch.dict(os.environ, azure_env()):
            with mock.patch.object(translation_module, "urlopen",
                                    side_effect=smart_urlopen(calls)):
                self.client.post(f"/api/drivers/me/trip/{bid}/messages",
                                 json={"text": "main pahunch gaya"},
                                 headers={"X-Driver-Token": token})
        messages = self.customer_messages(bid, booking["phone"]).get_json()["messages"]
        self.assertEqual(messages[1]["text"], "TEXT:es:SCRIPT:main pahunch gaya")
        self.assertTrue(messages[1]["translated"])

    # -- preference endpoints ---------------------------------------------
    def test_language_preference_endpoints(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        # Driver: default English, then saved + reflected in /me.
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": token}).get_json()["driver"]
        self.assertEqual(me["chat_language"], "en")
        resp = self.client.post("/api/drivers/me/chat-language",
                                json={"language": "ur-Latn"},
                                headers={"X-Driver-Token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["chat_language"], "ur-Latn")
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": token}).get_json()["driver"]
        self.assertEqual(me["chat_language"], "ur-Latn")
        # Customer: default English, then saved + reflected in booking.
        view = self.client.get(f"/api/bookings/{bid}").get_json()["booking"]
        self.assertEqual(view["chat_language"], "en")
        resp = self.client.post(f"/api/bookings/{bid}/chat-language",
                                json={"phone": booking["phone"], "language": "fr"})
        self.assertEqual(resp.status_code, 200)
        view = self.client.get(f"/api/bookings/{bid}").get_json()["booking"]
        self.assertEqual(view["chat_language"], "fr")
        # Invalid language, wrong phone, missing auth.
        self.assertEqual(self.client.post(
            "/api/drivers/me/chat-language", json={"language": "xx"},
            headers={"X-Driver-Token": token}).status_code, 400)
        self.assertEqual(self.client.post(
            f"/api/bookings/{bid}/chat-language",
            json={"phone": booking["phone"], "language": "xx"}).status_code, 400)
        self.assertEqual(self.client.post(
            f"/api/bookings/{bid}/chat-language",
            json={"phone": "+19999999999", "language": "fr"}).status_code, 403)
        self.assertEqual(self.client.post(
            "/api/drivers/me/chat-language",
            json={"language": "fr"}).status_code, 401)

    def test_language_sent_with_message_is_saved(self):
        booking, token = self.accepted_booking()
        bid = booking["id"]
        self.assertEqual(self.client.post(
            f"/api/drivers/me/trip/{bid}/messages",
            json={"text": "Hola", "language": "es"},
            headers={"X-Driver-Token": token}).status_code, 201)
        me = self.client.get("/api/drivers/me",
                             headers={"X-Driver-Token": token}).get_json()["driver"]
        self.assertEqual(me["chat_language"], "es")
        self.assertEqual(self.client.post(
            f"/api/bookings/{bid}/messages",
            json={"phone": booking["phone"], "text": "Bonjour",
                  "language": "fr"}).status_code, 201)
        view = self.client.get(f"/api/bookings/{bid}").get_json()["booking"]
        self.assertEqual(view["chat_language"], "fr")
        # An unknown language on send is rejected and nothing is stored.
        self.assertEqual(self.client.post(
            f"/api/drivers/me/trip/{bid}/messages",
            json={"text": "Nope", "language": "xx"},
            headers={"X-Driver-Token": token}).status_code, 400)
        self.assertEqual(len(
            self.driver_messages(bid, token).get_json()["messages"]), 2)

    def test_chat_gating_unchanged(self):
        _, token = self.register_driver()
        booking = self.book()
        self.assertEqual(self.client.post(
            f"/api/bookings/{booking['id']}/pay", json=dict(CARD)).status_code, 200)
        # Not yet accepted: customer gets 409 (chat not open), driver
        # gets 403 (booking not assigned to him) — same as before.
        self.assertEqual(self.client.post(
            f"/api/drivers/me/trip/{booking['id']}/messages",
            json={"text": "Too early"},
            headers={"X-Driver-Token": token}).status_code, 403)
        self.assertEqual(self.client.post(
            f"/api/bookings/{booking['id']}/messages",
            json={"phone": booking["phone"], "text": "Too early"}).status_code, 409)
        # Wrong phone still 403.
        self.assertEqual(self.client.get(
            f"/api/bookings/{booking['id']}/messages",
            query_string={"phone": "+19999999999"}).status_code, 403)
        # Text validation unchanged: empty and >500 chars rejected.
        self.client.post(f"/api/drivers/me/offers/{booking['id']}/accept",
                         json={}, headers={"X-Driver-Token": token})
        self.assertEqual(self.client.post(
            f"/api/drivers/me/trip/{booking['id']}/messages",
            json={"text": "   "},
            headers={"X-Driver-Token": token}).status_code, 400)
        self.assertEqual(self.client.post(
            f"/api/drivers/me/trip/{booking['id']}/messages",
            json={"text": "x" * 501},
            headers={"X-Driver-Token": token}).status_code, 400)

    # -- frontend ----------------------------------------------------------
    def test_frontend_picker_present(self):
        customer_html = read("static/index.html")
        driver_html = read("static/driver.html")
        customer_js = read("static/js/customer.js")
        driver_js = read("static/js/driver.js")
        # One picker per side, unique IDs, all 8 languages, plain labels.
        self.assertIn('id="ride-chat-language"', customer_html)
        self.assertIn('id="trip-chat-language"', driver_html)
        for code, label in [("en", "English"), ("ur-Latn", "Roman Urdu"),
                            ("es", "Spanish"), ("fr", "French"),
                            ("ar", "Arabic"), ("hi", "Hindi"),
                            ("bn", "Bengali"), ("pt", "Portuguese")]:
            option = f'value="{code}">{label}</option>'
            self.assertIn(option, customer_html)
            self.assertIn(option, driver_html)
        # The picker value travels with sends + polls and persists.
        self.assertIn("ride-chat-language", customer_js)
        self.assertIn("chat-language", customer_js)
        self.assertIn("language: state.chatLanguage", customer_js)
        self.assertIn("trip-chat-language", driver_js)
        self.assertIn("/api/drivers/me/chat-language", driver_js)
        self.assertIn("language: state.chatLanguage", driver_js)
        self.assertIn("?language=", driver_js)
        self.assertIn("&language=", customer_js)
        # Picker styling exists on both sides.
        self.assertIn(".chat-lang", read("static/css/customer.css"))
        self.assertIn(".chat-lang", read("static/css/driver.css"))


if __name__ == "__main__":
    unittest.main()
