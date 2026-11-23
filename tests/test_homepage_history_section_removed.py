"""Homepage "Your ride history" section removed (owner order, voice call
2026-11-22 ~19:32 EST): "homepage se nikal do, your ride history menu
mein rehne do."

- The section (heading, intro, phone lookup form, results) must NOT
  show on the homepage at all, and the homepage must not load
  ride-history.js any more.
- The top-nav "Ride history" link STAYS, pointing at the separate
  page /your-ride-history, which keeps its full content and still
  returns 200 with the lookup form.
- Same pattern as the earlier FAQ / Cancellation & waiting / Contacts
  removals (tests/test_homepage_sections_removed.py).

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="noel-history-section-removed-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "history-section-removed-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
INDEX = (REPO_DIR / "static" / "index.html").read_text()


class TestHomepageHistorySectionRemoved(unittest.TestCase):
    def test_section_absent_from_homepage(self):
        self.assertNotIn('id="history"', INDEX)
        self.assertNotIn('id="history-form"', INDEX)
        self.assertNotIn('id="history-phone"', INDEX)
        self.assertNotIn('id="history-results"', INDEX)
        self.assertNotIn('id="history-signedin"', INDEX)
        self.assertNotIn('id="history-error"', INDEX)
        self.assertNotIn("Your ride history", INDEX)
        self.assertNotIn("Enter the phone number you booked with to see your past rides.", INDEX)
        self.assertNotIn("history-box", INDEX)
        self.assertNotIn("/static/js/ride-history.js", INDEX)

    def test_nav_link_to_separate_page_stays(self):
        nav = INDEX.split("</nav>")[0]
        self.assertIn('href="/your-ride-history"', nav)
        self.assertIn('>Ride history</a>', nav)  # link carries data-i18n="menu.ride_history" now

    def test_separate_page_still_returns_200_with_lookup(self):
        client = app_module.app.test_client()
        res = client.get("/your-ride-history")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn(">Your ride history</h2>", html)  # h2 carries data-i18n now
        self.assertIn('id="history-form"', html)
        self.assertIn('id="history-phone"', html)
        self.assertIn('id="history-results"', html)
        self.assertIn("/static/js/ride-history.js", html)
        self.assertEqual(
            html,
            (REPO_DIR / "static" / "your-ride-history.html").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
