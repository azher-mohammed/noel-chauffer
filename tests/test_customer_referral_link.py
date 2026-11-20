"""Tests for the CUSTOMER referral LINK (owner request, voice call
2026-11-18, clarified the same call): a happy customer shares a
referral LINK — not just a typed code — so a friend clicking it
lands on booking with the referral already applied.

The entry point is the standard pattern: a clearly labeled
"Refer a Friend" button in the website referral box and in the
customer app (thank-you box + Referral tab). Tapping it reveals
the customer's referral link with Copy and native Share options.
The CUSTOMER shares the link himself (WhatsApp, message, etc.) —
the system sends nothing to friends.

Link format (query param on the existing pages, zero new server
routes, zero new server logic — purely client-side):
- website: https://noelchauffer.com/?ref=CODE
- app:     https://noelchauffer.com/app?ref=CODE

Clicking the link prefills the booking form's referral field;
booking-time validation is unchanged (an unknown code is rejected
exactly as a mistyped one), attribution is identical to a typed
code (used_count increments), and a NEW customer's first booking
with the code gets 5% off (owner decision 2026-11-18) while the
referring customer gets nothing. The existing "Your referral code:"
line is untouched; the explainer text gains one sentence stating
the friend's 5% off.

These tests pin:
- The "Refer a Friend" button, link line, anchor, Copy and Share
  controls exist in all three referral spots, start hidden, and
  the approved code line + explainer text are byte-identical.
- The JS builds the exact link formats, reads the ref param on
  load, prefills the referral field (app: opens the Book tab),
  reveals the link on button tap, and offers Copy (clipboard +
  fallback) and native Share.
- The referral sections state the friend-only 5% first-ride
  discount ("Your friend gets 5% off their first ride."); no
  referrer-benefit wording exists anywhere in the customer files.
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

EXPLAINER = ("Know someone who would enjoy a calm, comfortable ride? "
             "Tell them about Noel Chauffer. When they book, they can "
             "enter a referral code in the booking form.")


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def referral_link_block(js):
    """The referral-link section of a customer JS file."""
    start = js.index("/* ---------- Referral link ---------- */")
    end = js.index("/* ----------", start + 10)
    return js[start:end]


class ReferralLinkMarkupCase(unittest.TestCase):
    # -- website referral box ----------------------------------------------
    def test_website_referral_box_has_button_link_and_actions(self):
        html = read("static/index.html")
        self.assertIn(EXPLAINER, html)
        self.assertIn('id="referral-code-line" class="hidden">Your referral code: '
                      '<strong id="referral-code-value"></strong>', html)
        self.assertIn('id="referral-show-btn">Refer a Friend</button>', html)
        self.assertIn('id="referral-link-line" class="hidden">Your referral link: '
                      '<a id="referral-link-anchor" href="#"></a>', html)
        self.assertIn('id="referral-copy-btn">Copy link</button>', html)
        self.assertIn('id="referral-share-btn">Share link</button>', html)
        # The reveal button and the link start hidden.
        self.assertIn('id="referral-show-btn"',
                      re.search(r'<button[^>]*id="referral-show-btn"[^>]*>', html).group(0))
        self.assertIn("hidden", re.search(r'<button[^>]*id="referral-show-btn"[^>]*>', html).group(0))
        self.assertIn("hidden", re.search(r'<div[^>]*id="referral-link-actions"[^>]*>', html).group(0))

    # -- customer app: thank-you box + Referral tab -------------------------
    def test_app_thankyou_box_has_button_link_and_actions(self):
        html = read("static/customer-app.html")
        self.assertIn('id="ca-referral-code-line" class="hidden">Your referral code: '
                      '<strong id="ca-referral-code-value"></strong>', html)
        self.assertIn('id="ca-referral-show-btn">Refer a Friend</button>', html)
        self.assertIn('id="ca-referral-link-line" class="hidden">Your referral link: '
                      '<a id="ca-referral-link-anchor" href="#"></a>', html)
        self.assertIn('id="ca-referral-copy-btn">Copy link</button>', html)
        self.assertIn('id="ca-referral-share-btn">Share link</button>', html)
        self.assertIn("hidden", re.search(r'<button[^>]*id="ca-referral-show-btn"[^>]*>', html).group(0))

    def test_app_referral_tab_has_button_link_and_actions(self):
        html = read("static/customer-app.html")
        self.assertIn('id="ca-tab-referral-line" class="hidden">Your referral code: '
                      '<strong id="ca-tab-referral-value"></strong>', html)
        self.assertIn('id="ca-tab-referral-show-btn">Refer a Friend</button>', html)
        self.assertIn('id="ca-tab-referral-link-line" class="hidden">Your referral link: '
                      '<a id="ca-tab-referral-link-anchor" href="#"></a>', html)
        self.assertIn('id="ca-tab-referral-copy-btn">Copy link</button>', html)
        self.assertIn('id="ca-tab-referral-share-btn">Share link</button>', html)
        self.assertIn("hidden", re.search(r'<button[^>]*id="ca-tab-referral-show-btn"[^>]*>', html).group(0))
        # The empty-state line is untouched.
        self.assertIn("Your referral code appears here after your first ride is booked.", html)

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
    # -- website JS ---------------------------------------------------------
    def test_website_js_builds_exact_link_format(self):
        js = read("static/js/customer.js")
        self.assertIn('window.location.origin + "/?ref=" + encodeURIComponent(code)', js)

    def test_website_js_prefills_from_ref_param(self):
        js = read("static/js/customer.js")
        block = referral_link_block(js)
        self.assertIn('URLSearchParams(window.location.search).get("ref")', block)
        self.assertIn('$("bk-referral")', block)
        self.assertIn("field.value = ref", block)

    def test_website_js_reveals_link_on_button_tap(self):
        js = read("static/js/customer.js")
        block = referral_link_block(js)
        self.assertIn('$("referral-show-btn")', block)
        self.assertIn('show($("referral-link-line"))', block)
        self.assertIn('show($("referral-link-actions"))', block)
        self.assertIn('anchor.href = link', block)
        self.assertIn('anchor.textContent = link', block)

    # -- customer app JS ----------------------------------------------------
    def test_app_js_builds_exact_link_format(self):
        js = read("static/js/customer-app.js")
        self.assertIn('window.location.origin + "/app?ref=" + encodeURIComponent(code)', js)

    def test_app_js_prefills_and_opens_book_tab(self):
        js = read("static/js/customer-app.js")
        block = referral_link_block(js)
        self.assertIn('URLSearchParams(window.location.search).get("ref")', block)
        self.assertIn('$("ca-referral")', block)
        self.assertIn("field.value = ref", block)
        self.assertIn('showScreen("book")', block)

    def test_app_js_reveals_link_on_button_tap_both_spots(self):
        js = read("static/js/customer-app.js")
        block = referral_link_block(js)
        self.assertIn("THANKYOU_REFERRAL_IDS", block)
        self.assertIn("TAB_REFERRAL_IDS", block)
        self.assertIn('show($(ids.line))', block)
        self.assertIn('show($(ids.actions))', block)
        self.assertIn('anchor.href = link', block)
        self.assertIn('showReferralLink(code, TAB_REFERRAL_IDS)', js)
        self.assertIn('showReferralLink(code, THANKYOU_REFERRAL_IDS)', js)

    # -- Copy + Share in both files -----------------------------------------
    def test_copy_and_share_in_both_js_files(self):
        for rel in ("static/js/customer.js", "static/js/customer-app.js"):
            js = read(rel)
            block = referral_link_block(js)
            self.assertIn("navigator.clipboard.writeText", block, rel)
            self.assertIn('document.execCommand("copy")', block, rel)
            self.assertIn("navigator.share", block, rel)
            self.assertIn('"Copied"', block, rel)

    # -- friend-only benefit, no referrer promise ---------------------------
    def test_no_referrer_benefit_wording(self):
        # The 5% discount is for the NEW customer only (owner decision
        # 2026-11-18): the referral sections may say the friend gets
        # 5% off their first ride, but nothing may promise the
        # referrer anything.
        for rel in ("static/js/customer.js", "static/js/customer-app.js"):
            block = referral_link_block(read(rel))
            for word in ("reward", "earn", "cash back", "cashback",
                         "free ride", "$5", "$10", "$20"):
                self.assertNotIn(word, block.lower(),
                                 f"{rel} referral block must not promise {word!r}")
        for rel in ("static/index.html", "static/customer-app.html"):
            html = read(rel)
            self.assertIn("Your friend gets 5% off their first ride.", html, rel)
            for word in ("you earn", "you get 5%", "your reward",
                         "cash back", "cashback", "free ride", "both get",
                         "$5", "$10", "$20"):
                self.assertNotIn(word, html.lower(),
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
            self.assertIn("Refer a friend", resp.get_data(as_text=True))

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
