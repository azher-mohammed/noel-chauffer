"""Hamburger menu: "For chauffeurs" replaced by "Your rides" (owner order,
voice call 2026-11-22 ~21:14 EST, FINAL wording: "First offer hai nahi
bhai, your chauffeur ke first chauffeur ke badla your rides lagana hai").

- The mobile/hamburger menu on the website shows "Your rides" in the
  exact spot "For chauffeurs" used to sit (between "For business" and
  "Help"). Nothing else in the menu changes.
- "For chauffeurs" is gone from the menu. The /driver page itself stays
  live and working. The footer "Drive with us" link was REMOVED by a later
  owner order (voice call 2026-11-23 ~00:21 EST); the top-nav "Drive with
  us" link on the other pages stays.
- Clicking "Your rides" opens /your-ride-history, which shows the
  customer's FULL rides (phone lookup, plus auto-load for signed-in
  customers) with completed rides shown as completed
  ("Ride completed — thank you").

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="noel-menu-your-rides-")
os.environ["DATABASE_URL"] = "sqlite:///" + _tmpdir + "/test.db"
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "menu-your-rides-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
INDEX = (REPO_DIR / "static" / "index.html").read_text()
RIDE_HISTORY_JS = (REPO_DIR / "static" / "js" / "ride-history.js").read_text()


def _menu_block():
    start = INDEX.index('id="mobile-menu"')
    end = INDEX.index("</nav>", start)
    return INDEX[start:end]


class TestMenuYourRides(unittest.TestCase):
    def test_menu_has_your_rides_in_place_of_for_chauffeurs(self):
        menu = _menu_block()
        self.assertIn(
            '<a class="menu-link" href="/your-ride-history" data-i18n="menu.your_rides">Your rides</a>',
            menu,
        )
        self.assertNotIn("For chauffeurs", menu)
        self.assertNotIn('href="/driver"', menu)
        # Same position: after the "For business" group, before "Help".
        self.assertLess(menu.index("For business"), menu.index("Your rides"))
        self.assertLess(
            menu.index("Your rides"),
            menu.index('href="/frequently-asked-questions"'),  # Help link carries data-i18n now
        )

    def test_rest_of_menu_unchanged(self):
        menu = _menu_block()
        self.assertIn("Our services", menu)
        self.assertIn("City-to-City rides", menu)
        self.assertIn("Airport transfers", menu)
        self.assertIn("Hourly hire", menu)
        self.assertIn("For business", menu)
        self.assertIn("Help", menu)
        self.assertIn('id="menu-lang-slot"', menu,
                         "menu language item is now the working picker slot")
        self.assertIn("Sign in", menu)

    def test_driver_page_still_live_and_footer_drive_link_removed(self):
        client = app_module.app.test_client()
        res = client.get("/driver")
        self.assertEqual(res.status_code, 200)
        # Owner order 2026-11-23 ~00:21 EST: the footer "Drive with us"
        # link is gone. The homepage carried it ONLY in the footer, so
        # the phrase is gone from the homepage entirely; the /driver
        # page itself (and the top-nav link on the other pages) stays.
        self.assertNotIn("Drive with us", INDEX)
        # The top-nav "Ride history" link (kept by the earlier removal)
        # still points at the same separate page.
        self.assertIn('href="/your-ride-history"', INDEX)
        self.assertIn('>Ride history</a>', INDEX)  # link carries data-i18n="menu.ride_history" now

    def test_your_rides_page_returns_200_with_lookup(self):
        client = app_module.app.test_client()
        res = client.get("/your-ride-history")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('id="history-form"', html)
        self.assertIn('id="history-phone"', html)
        self.assertIn('id="history-results"', html)
        self.assertIn("/static/js/ride-history.js", html)

    def test_completed_rides_shown_as_completed(self):
        phone = "9295550142"
        with app_module.app.app_context():
            done = app_module.Booking(
                customer_name="Test Rider",
                phone=phone,
                email="rider@example.com",
                pickup="180 Green Acres Road, Valley Stream, NY",
                dropoff="Times Square, New York",
                date="2026-11-20",
                time="12:00",
                ride_type="one_way",
                status="completed",
                fare_total=201.82,
                driver_earnings=102.46,
            )
            open_ride = app_module.Booking(
                customer_name="Test Rider",
                phone=phone,
                email="rider@example.com",
                pickup="Times Square, New York",
                dropoff="JFK Airport, New York",
                date="2026-11-22",
                time="12:00",
                ride_type="one_way",
                status="offered",
                fare_total=201.82,
                driver_earnings=102.46,
            )
            app_module.db.session.add_all([done, open_ride])
            app_module.db.session.commit()
        client = app_module.app.test_client()
        res = client.get("/api/bookings?phone=" + phone)
        self.assertEqual(res.status_code, 200)
        rides = res.get_json()
        self.assertEqual(len(rides), 2)
        statuses = {r["status"] for r in rides}
        self.assertIn("completed", statuses)
        self.assertIn("offered", statuses)
        # The history view renders a completed ride as completed.
        self.assertIn('completed: T("status.completed", "Ride completed', RIDE_HISTORY_JS)


if __name__ == "__main__":
    unittest.main()
