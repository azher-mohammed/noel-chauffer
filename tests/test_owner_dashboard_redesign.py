"""Tests for the owner dashboard redesign (owner decision 2026-11-23,
voice call): "jo owner ka dashboard hai ye bahut ajeeb bana hua hai...
The best way banao tum apne khud se" — plus the hard requirement
minutes later: "mere ko poora scroll karna padta hai har cheez.
scroll thodi karunga main."

The old dashboard was ONE long scrolling page (Summary, Bookings,
Payouts, Alerts, Outbox, Support, Drivers, Referrals, Flags, Expiry —
all stacked). The redesign is TABBED: Dashboard / Rides / Drivers /
Money / More, one screen per tab. The Dashboard tab is a compact
one-screen overview (money cards, latest rides, needs-attention
counts, latest alerts); everything else lives behind its tab.
Bookings page at 10 rows instead of 50; driver documents collapse
behind one line per driver.

NOTHING is removed and no logic changes: every feature, endpoint,
PIN behaviour and id from the old dashboard still exists — the tests
below pin the full inventory. Pure presentation/UX redesign.

Run:  python -m unittest discover -s tests -v
"""


import os
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-owner-redesign-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "owner-redesign-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


class OwnerRedesignCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()

    # -- the page still serves, PIN gate still first ----------------------
    def test_owner_page_serves_with_pin_gate(self):
        resp = self.client.get("/owner")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('id="pin-gate"', html)
        self.assertIn('id="dashboard"', html)
        self.assertIn('id="pin-form"', html)
        self.assertIn('id="pin-input"', html)

    def test_owner_api_still_requires_login(self):
        resp = self.client.get("/api/owner/summary")
        self.assertNotEqual(resp.status_code, 200)

    # -- tabs exist, one panel per section ----------------------------------
    def test_five_tabs_present(self):
        html = read("static/owner.html")
        for tab in ("dashboard", "rides", "drivers", "money", "more"):
            self.assertIn('data-tab="%s"' % tab, html)
            self.assertIn('id="tab-%s"' % tab, html)
        self.assertIn("Dashboard", html)
        self.assertIn("Rides", html)
        self.assertIn("Drivers", html)
        self.assertIn("Money", html)
        self.assertIn("More", html)
        js = read("static/js/owner.js")
        self.assertIn("showTab", js)
        self.assertIn("tab-btn", js)
        self.assertIn("tab-", js)

    # -- every old feature still has its home ------------------------------
    def test_all_sections_still_present(self):
        html = read("static/owner.html")
        for section in ("Today at a glance", "Bookings", "Driver payouts",
                        "Driver referrals", "Alerts", "Messages outbox",
                        "Support messages", "Documents expiring soon",
                        "Flagged documents", "Test only"):
            self.assertIn(section, html)
        for el in ("sum-gross", "sum-profit", "sum-owed", "sum-rides",
                   "sum-gross-hint", "sum-rides-hint",
                   "bookings-search", "bookings-body", "bookings-empty",
                   "bookings-pager", "bookings-prev", "bookings-next",
                   "bookings-page-info", "booking-detail",
                   "payouts-body", "payouts-empty",
                   "alerts-feed", "outbox-feed", "support-feed",
                   "drivers-list", "referrals-feed", "flags-feed",
                   "expiry-feed", "viewer-backdrop", "viewer-close",
                   "viewer-title", "viewer-body",
                   "pin-confirm-modal", "pin-confirm-title",
                   "pin-confirm-text", "pin-confirm-form",
                   "pin-confirm-input", "pin-confirm-error",
                   "pin-confirm-cancel", "pin-confirm-submit",
                   "today-list", "attention-list", "dash-alerts"):
            self.assertIn('id="%s"' % el, html, "missing id: %s" % el)

    def test_search_placeholder_still_names_every_field(self):
        html = read("static/owner.html")
        for field in ("customer", "phone", "pickup", "drop-off",
                      "driver", "booking #", "date", "status"):
            self.assertIn(field, html)

    def test_outbox_still_shows_sent_queued(self):
        html = read("static/owner.html")
        self.assertIn("Sent once delivered", html)
        js = read("static/js/owner.js")
        self.assertIn('"Sent"', js)
        self.assertIn('"Queued"', js)

    # -- danger buttons: still PIN-guarded, still after the dashboard ------
    def test_danger_buttons_still_present_and_guarded(self):
        html = read("static/owner.html")
        gate = html.index('id="pin-gate"')
        dash = html.index('id="dashboard"')
        rides = html.index('id="clear-rides-btn"')
        drivers = html.index('id="clear-drivers-btn"')
        self.assertIn("Clear all rides", html)
        self.assertIn("Remove all drivers", html)
        self.assertGreater(dash, gate)
        self.assertGreater(rides, dash)
        self.assertGreater(drivers, rides)
        js = read("static/js/owner.js")
        self.assertIn("/api/owner/clear-rides", js)
        self.assertIn("/api/owner/clear-drivers", js)
        self.assertIn("pin-confirm-modal", js)
        self.assertIn("pin-confirm-input", js)
        self.assertIn("pin: pin", js)

    # -- every owner endpoint still wired in the JS ---------------------------
    def test_all_owner_endpoints_still_wired(self):
        js = read("static/js/owner.js")
        for endpoint in ("/api/owner/summary", "/api/owner/login",
                         "/api/owner/logout", "/api/owner/bookings",
                         "/api/owner/payouts", "/api/owner/payouts/mark-paid",
                         "/api/owner/alerts", "/api/owner/outbox",
                         "/api/owner/support-messages",
                         "/api/owner/driver-referrals",
                         "/api/owner/document-flags",
                         "/api/owner/expiring-documents",
                         "/api/owner/run-pickup-reminders",
                         "/api/owner/run-expiry-alerts",
                         "/api/owner/drivers", "/api/owner/documents/"):
            self.assertIn(endpoint, js, "endpoint missing: %s" % endpoint)
        self.assertIn("loadDriverReferrals();", js)
        self.assertIn("No driver referrals yet.", js)
        self.assertIn("No rides match that search.", js)
        self.assertIn("flight_number", js)
        self.assertIn("airline_name", js)

    # -- compact pages: 10 rides per page, not 50 ----------------------------
    def test_bookings_page_is_compact(self):
        js = read("static/js/owner.js")
        self.assertIn("BOOKINGS_PER_PAGE = 10", js)
        self.assertNotIn("BOOKINGS_PER_PAGE = 50", js)
        self.assertIn("per_page=", js)
        self.assertIn('"&q="', js)
        self.assertIn("setTimeout", js)
        self.assertIn("300", js)

    # -- overview helpers exist ----------------------------------------------
    def test_dashboard_overview_helpers(self):
        js = read("static/js/owner.js")
        self.assertIn("renderTodayList", js)
        self.assertIn("renderAttention", js)
        self.assertIn("renderDashAlerts", js)
        self.assertIn("Needs attention", read("static/owner.html"))

    # -- driver documents collapse behind one line ----------------------------
    def test_driver_documents_collapse(self):
        js = read("static/js/owner.js")
        self.assertIn("driver-docs", js)
        self.assertIn("Documents (", js)
        self.assertIn(" of ", js)
        self.assertIn(" complete)", js)
        css = read("static/css/owner.css")
        self.assertIn(".driver-docs", css)

    # -- detail panel can be closed -------------------------------------------
    def test_booking_detail_has_close(self):
        js = read("static/js/owner.js")
        self.assertIn("detail-close", js)

    # -- style rules: blue buttons, gold only on "Chauffeur", no green --------
    def test_owner_style_rules(self):
        css = read("static/css/owner.css").lower()
        self.assertIn("#5b9bd5", css)
        self.assertIn("#4a8ac2", css)
        self.assertIn("#d4af37", css)
        self.assertNotIn("#c9a227", css)
        self.assertNotIn("#1e7a4c", css)
        self.assertNotIn("#25d366", css)
        self.assertNotIn("linear-gradient", css)
        html = read("static/owner.html")
        self.assertIn("Noel <span>Chauffer</span>", html)


if __name__ == "__main__":
    unittest.main()
