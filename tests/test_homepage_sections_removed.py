"""Homepage sections removed: FAQ, Cancellation & waiting, Contacts
(owner orders, voice call 2026-11-22 ~06:52-06:54 EST).

- FAQ: "bas usko ek hi rakho frequently asked question" then
  corrected ("neeche dikhna nahi chahiye", "home page pe nahi
  dikhna chahiye") — the ENTIRE FAQ section is off the homepage.
- Cancellation & waiting: "cancellation and waiting ka bhi waise
  hi karo" — same: whole section off the homepage.
- Contacts: "contact nahi nikal do contact us" / "nikal hi de do"
  — whole Contacts section off the homepage.

For all three: the section (heading, intro, all content) must NOT
show on the homepage at all; the top-nav link to the separate page
STAYS and the separate page keeps its full content.

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="noel-sections-removed-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "sections-removed-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent
INDEX = (REPO_DIR / "static" / "index.html").read_text()

# route -> (separate page file, fragments that must live on that page)
REMOVED = {
    "/cancellation-and-waiting": (
        "cancellation-and-waiting.html",
        ["Cancellation &amp; waiting",
         "Free cancellation if you cancel more than 1 hour before pickup.",
         "60 minutes of waiting free"],
    ),
    "/frequently-asked-questions": (
        "frequently-asked-questions.html",
        ["Frequently asked questions",
         "How do I book a ride?",
         "Do you offer black car service in New York City?"],
    ),
    "/contacts": (
        "contacts.html",
        ["Contacts",
         "support@noelchauffer.com",
         "We reply within 24 hours."],
    ),
}


class TestHomepageSectionsRemoved(unittest.TestCase):
    def test_sections_absent_from_homepage(self):
        self.assertNotIn('id="policy"', INDEX)
        self.assertNotIn('id="faq"', INDEX)
        self.assertNotIn('id="contacts"', INDEX)
        self.assertNotIn("Frequently asked questions", INDEX)
        self.assertNotIn("Free cancellation if you cancel more than 1 hour before pickup.", INDEX)
        self.assertNotIn("<h3>How do I book a ride?</h3>", INDEX)
        self.assertNotIn("Do you offer black car service in New York City?", INDEX)
        self.assertNotIn("60 minutes of waiting free", INDEX)
        self.assertNotIn("contacts-box", INDEX)
        self.assertNotIn("open-chat-btn", INDEX)

    def test_nav_links_to_separate_pages_stay(self):
        nav = INDEX.split("</nav>")[0]
        self.assertIn('<a href="/cancellation-and-waiting">Cancellation &amp; waiting</a>', nav)
        self.assertIn('<a href="/frequently-asked-questions">FAQ</a>', nav)
        self.assertIn('<a href="/contacts">Contacts</a>', nav)

    def test_separate_pages_still_return_200_with_content(self):
        client = app_module.app.test_client()
        for route, (file, fragments) in REMOVED.items():
            with self.subTest(route=route):
                res = client.get(route)
                self.assertEqual(res.status_code, 200, route)
                html = res.get_data(as_text=True)
                for frag in fragments:
                    self.assertIn(frag, html, route)
                self.assertEqual(
                    html, (REPO_DIR / "static" / file).read_text(encoding="utf-8")
                )


if __name__ == "__main__":
    unittest.main()
