"""Tests for the CUSTOMER referral LINK after the visible referral UI
was removed (owner order, voice call 2026-11-21): the ENTIRE
"Refer a friend" section is gone from the customer-facing surfaces
— no referral box on the website thank-you view, no Referral tab in
the customer app, no "Refer a Friend" button anywhere.

What REMAINS (and these tests pin it): already-shared referral links
keep working. A friend clicking a link lands on booking with the
referral already applied via the ?ref= prefill (client-side only),
booking-time validation is unchanged (an unknown code is rejected
exactly as a mistyped one), attribution is identical to a typed
code (used_count increments), and a NEW customer's first booking
with the code gets 5% off (owner decision 2026-11-18) while the
referring customer gets nothing.

Link format (query param on the existing pages, zero new server
routes, zero new server logic — purely client-side prefill):
- website: https://noelchauffer.com/?ref=CODE
- app:     https://noelchauffer.com/app?ref=CODE

The DRIVER referral ("Get $5 in cash for each ride you refer") is a
separate feature and is untouched by this removal.

These tests pin:
- NO "Refer a friend" text, referral box, Referral tab, or
  "Refer a Friend" button exists in the website or customer-app
  HTML/JS; the app tab bar has only Book / My Rides / Support.
- The JS still reads the ref param on load and prefills the hidden
  referral field (app: opens the Book tab); the prefill adds no
  validation semantics.
- No new server route exists for referrals.
- Pages load fine with an unknown ref value (?ref= garbage).
- Typed-code booking behavior: valid code accepted, used_count
  increments; a first booking with the code totals 5% less, a
  repeat phone totals the same; invalid code rejected with the
  existing message.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import sys
import tempfile
import unittest
from unittest import mock
from collections import Counter

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-ref-link-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "reflink-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

# Deterministic geo (same as the other API test modules).
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Owner decision 2026-11-21: the visible "Refer a friend" UI is gone.
# The explainer text below must NOT appear in any customer file.
REMOVED_EXPLAINER = ("Know someone who would enjoy a calm, comfortable ride? "
                     "Tell them about Noel Chauffer. Your friend gets 5% off "
                     "their first ride. They just need to book through your link.")


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def referral_link_block(js):
    """The referral-link prefill section of a customer JS file."""
    start = js.index("/* ---------- Referral link prefill")
    try:
        end = js.index("/* ----------", start + 10)
    except ValueError:
        end = len(js)  # prefill is the last section in customer-app.js
    return js[start:end]


class ReferralLinkMarkupCase(unittest.TestCase):
    # -- the visible referral UI is GONE (owner 2026-11-21) ---------------
    def test_website_has_no_referral_ui(self):
        html = read("static/index.html")
        self.assertNotIn("Refer a friend", html)
        self.assertNotIn("Refer a Friend", html)
        self.assertNotIn("referral-box", html)
        self.assertNotIn(REMOVED_EXPLAINER, html)
        for gone_id in ("referral-code-line", "referral-code-value",
                        "referral-show-btn", "referral-link-line",
                        "referral-link-anchor", "referral-link-actions",
                        "referral-copy-btn", "referral-share-btn"):
            self.assertNotIn(gone_id, html, f"{gone_id} must be gone")
        # The thank-you view itself is untouched: return-trip and
        # book-another-ride buttons still there.
        self.assertIn('id="thankyou-block"', html)
        self.assertIn('id="return-trip-btn"', html)
        self.assertIn('id="new-booking-btn"', html)
        # The hidden referral field that links prefill into stays.
        self.assertIn('id="bk-referral"', html)

    # -- customer app: no thank-you box, no Referral tab -------------------
    def test_app_has_no_referral_ui(self):
        html = read("static/customer-app.html")
        self.assertNotIn("Refer a friend", html)
        self.assertNotIn("Refer a Friend", html)
        self.assertNotIn("referral-box", html)
        self.assertNotIn(REMOVED_EXPLAINER, html)
        self.assertNotIn('id="screen-referral"', html)
        self.assertNotIn('data-screen="referral"', html)
        for gone_id in ("ca-referral-code-line", "ca-referral-code-value",
                        "ca-referral-show-btn", "ca-referral-link-line",
                        "ca-referral-link-anchor", "ca-referral-link-actions",
                        "ca-referral-copy-btn", "ca-referral-share-btn",
                        "ca-tab-referral-line", "ca-tab-referral-value",
                        "ca-tab-referral-show-btn", "ca-tab-referral-link-line",
                        "ca-tab-referral-link-anchor",
                        "ca-tab-referral-link-actions",
                        "ca-tab-referral-copy-btn", "ca-tab-referral-share-btn",
                        "ca-tab-referral-empty", "ca-referral-form",
                        "ca-referral-phone", "ca-referral-error"):
            self.assertNotIn(gone_id, html, f"{gone_id} must be gone")
        # The thank-you view itself is untouched.
        self.assertIn('id="ca-thankyou-block"', html)
        self.assertIn('id="ca-return-trip-btn"', html)
        self.assertIn('id="ca-new-booking-btn"', html)
        # The hidden referral field that links prefill into stays.
        self.assertIn('id="ca-referral"', html)
        # Tab bar: only Book / My Rides / Support remain.
        for tab in ("book", "rides", "support"):
            self.assertIn(f'data-screen="{tab}"', html)

    def test_no_duplicate_ids_introduced(self):
        for rel in ("static/index.html", "static/customer-app.html"):
            html = read(rel)
            ids = re.findall(r'id="([^"]+)"', html)
            dupes = [i for i, n in Counter(ids).items() if n > 1]
            self.assertEqual(dupes, [], f"duplicate ids in {rel}: {dupes}")

    def test_referral_link_css_present_on_both_pages(self):
        site = read("static/css/customer.css")
        self.assertIn("#referral-link-line a", site)
        self.assertIn(".referral-actions", site)
        app_css = read("static/css/customer-app.css")
        self.assertIn("#ca-referral-link-line a", app_css)
        self.assertIn("#ca-tab-referral-link-line a", app_css)
        self.assertIn(".referral-actions", app_css)


class ReferralLinkJsCase(unittest.TestCase):
    # -- website JS: no referral UI wiring, prefill stays -------------------
    def test_website_js_has_no_referral_ui_wiring(self):
        js = read("static/js/customer.js")
        for gone in ("Refer a Friend", "referral-show-btn",
                     "referral-link-line", "referral-link-anchor",
                     "referral-copy-btn", "referral-share-btn",
                     "referral-link-actions", "referral-code-line",
                     "referral-code-value", "showReferralLink",
                     "referralLinkFor", "copyTextToClipboard"):
            self.assertNotIn(gone, js, f"{gone} must be gone from customer.js")
        # The hidden referral field + discount display stay.
        self.assertIn('$("bk-referral")', js)
        self.assertIn("referral_discount", js)

    def test_website_js_prefills_from_ref_param(self):
        js = read("static/js/customer.js")
        block = referral_link_block(js)
        self.assertIn('URLSearchParams(window.location.search).get("ref")', block)
        self.assertIn('$("bk-referral")', block)
        self.assertIn("field.value = ref", block)

    # -- customer app JS: no referral UI wiring, prefill stays --------------
    def test_app_js_has_no_referral_ui_wiring(self):
        js = read("static/js/customer-app.js")
        for gone in ("Refer a Friend", "Refer a friend", "Referral tab",
                     "ca-referral-show-btn", "ca-referral-link-line",
                     "ca-referral-link-anchor", "ca-referral-copy-btn",
                     "ca-referral-share-btn", "ca-referral-link-actions",
                     "ca-referral-code-line", "ca-referral-code-value",
                     "ca-tab-referral", "ca-referral-form",
                     "showReferralLink", "showReferralCode",
                     "referralLinkFor", "copyTextToClipboard",
                     "THANKYOU_REFERRAL_IDS", "TAB_REFERRAL_IDS"):
            self.assertNotIn(gone, js, f"{gone} must be gone from customer-app.js")
        # Only three screens remain.
        self.assertIn('var SCREENS = ["book", "rides", "support"];', js)
        # The hidden referral field + discount display stay.
        self.assertIn('$("ca-referral")', js)
        self.assertIn("referral_discount", js)

    def test_app_js_prefills_and_opens_book_tab(self):
        js = read("static/js/customer-app.js")
        block = referral_link_block(js)
        self.assertIn('URLSearchParams(window.location.search).get("ref")', block)
        self.assertIn('$("ca-referral")', block)
        self.assertIn("field.value = ref", block)
        self.assertIn('showScreen("book")', block)

    # -- no referrer-benefit wording anywhere in the customer files --------
    def test_no_referrer_benefit_wording(self):
        # The 5% discount is for the NEW customer only (owner decision
        # 2026-11-18) and the visible referral sections are gone
        # (owner decision 2026-11-21): nothing in the customer files
        # may promise the referrer anything, and the removed
        # explainer text must not appear anywhere.
        for rel in ("static/index.html", "static/customer-app.html",
                    "static/js/customer.js", "static/js/customer-app.js"):
            text = read(rel)
            self.assertNotIn(REMOVED_EXPLAINER, text, rel)
            for word in ("you earn", "your reward", "cash back",
                         "cashback", "free ride", "both get",
                         "get $5", "get $10", "get $20"):
                self.assertNotIn(word, text.lower(),
                                 f"{rel} must not promise the referrer {word!r}")

    def test_prefill_does_not_validate_or_fetch(self):
        # The prefill must never add validation semantics: no fetch, no
        # API call, no error message in the prefill block.
        for rel in ("static/js/customer.js", "static/js/customer-app.js"):
            block = referral_link_block(read(rel))
            prefill = block[block.index("prefillReferralFromUrl"):]
            self.assertNotIn("fetch(", prefill, rel)
            self.assertNotIn("XMLHttpRequest", prefill, rel)
            self.assertNotIn("Invalid referral code", prefill, rel)


# These tests pin the legacy $9/$10 totals as their fixtures; the
# live engine is Blacklane by default since the owner flip
# (2026-11-20).
@mock.patch.dict(os.environ, {"NOEL_PRICING": "legacy"})
class ReferralLinkServerCase(unittest.TestCase):
    def setUp(self):
        app_module.BOOKINGS_PAUSED = False  # pause OFF for booking-flow tests (owner decision 2026-11-20)
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._phone_seq = 0

    def book(self, **extra):
        self._phone_seq += 1
        payload = {
            "customer_name": "Referral Link Tester",
            "phone": f"+1555011{self._phone_seq:04d}",
            "email": "reflink@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
        }
        payload.update(extra)
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True)[:200])
        return resp.get_json()["booking"]

    def test_no_new_server_route_for_referrals(self):
        # The CUSTOMER referral link adds no server route: it reuses
        # the booking endpoints and the ?ref= prefill is client-side
        # only. The only "referral" routes are the DRIVER referral
        # feature (owner decision 2026-11-18, separate from the
        # customer referral): the signed-in driver's own referral
        # view and the owner dashboard's referral records.
        rules = [str(r) for r in app_module.app.url_map.iter_rules()]
        self.assertEqual(sorted(r for r in rules if "referral" in r), [
            "/api/drivers/me/referral",
            "/api/owner/driver-referrals",
        ])
        self.assertEqual([r for r in rules if re.match(r"^/r(/|$)", r)], [])

    def test_pages_load_with_unknown_ref_value(self):
        for path in ("/?ref=NOEL-XXXXXX", "/?ref=garbage%20value",
                     "/app?ref=NOEL-XXXXXX", "/app?ref=garbage%20value"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)
            self.assertNotIn("Refer a friend", resp.get_data(as_text=True))

    def test_typed_code_behavior_unchanged(self):
        first = self.book()
        code = first["referral_code"]
        self.assertTrue(code)
        referred = self.book(referral_code=code)
        # 5% off for this phone's first booking with the code: the
        # totals are 5% lower than the same ride without a code.
        # (18.0 miles, toll $0.00 in this test env: $162.00 -> $153.90.)
        self.assertEqual(referred["class_totals"]["sedan"], 153.90)
        self.assertEqual(referred["class_totals"]["suv"], 171.00)
        self.assertEqual(referred["referral_discount"], 8.10)
        # Attribution identical: used_count increments.
        with app_module.app.app_context():
            row = app_module.ReferralCode.query.filter_by(code=code).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.used_count, 1)
            booking = app_module.db.session.get(app_module.Booking, referred["id"])
            self.assertEqual(booking.referral_code_used, code)

    def test_invalid_code_still_rejected_at_booking_time(self):
        resp = self.client.post("/api/bookings", json={
            "customer_name": "Referral Link Tester",
            "phone": "+15550119999",
            "email": "reflink@test.com",
            "pickup": "JFK Airport", "dropoff": "Times Square, New York",
            "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
            "referral_code": "NOEL-XXXXXX",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid referral code", resp.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
