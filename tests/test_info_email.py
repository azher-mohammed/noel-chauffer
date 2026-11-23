"""Contact email swap — owner order, voice call 2026-11-23 ~16:28 EST
("Har jagah se support ke badla info").

- The customer-facing contact/sender email is info@noelchauffer.com
  EVERYWHERE: site footers, /contacts, /privacy, /terms, service and
  guide pages (visible text AND JSON-LD "email" fields), the customer
  app, the translated "Email us" strings, and the support auto-reply
  bank.
- The Resend sender (email_sender.DEFAULT_FROM) is
  "Noel Chauffer <info@noelchauffer.com>" — the noelchauffer.com
  domain is already verified in Resend, so any @noelchauffer.com
  sender works.
- support@noelchauffer.com appears NOWHERE in the repo any more.
  (The Namecheap forward for support@ is deliberately KEPT — old
  mail to support@ must keep arriving; this is a display/sender
  swap, not a deletion.)

Run:  python -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from pathlib import Path

REPO_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, str(REPO_DIR))

import email_sender  # noqa: E402

OLD = "support@noelchauffer.com"
NEW = "info@noelchauffer.com"

# Customer-facing pages that must carry the new contact email.
PAGES = [
    "static/index.html",
    "static/contacts.html",
    "static/privacy.html",
    "static/terms.html",
    "static/customer-app.html",
    "static/jfk-to-times-square.html",
    "static/manhattan-car-service.html",
    "static/brooklyn-car-service.html",
    "static/hourly-chauffeur-service.html",
]

# Repo file types scanned for any leftover old address.
SCAN_SUFFIXES = {".py", ".html", ".js", ".md", ".json"}
SCAN_SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}


class InfoEmailSwapCase(unittest.TestCase):
    def test_default_from_is_info(self):
        self.assertEqual(
            email_sender.DEFAULT_FROM,
            "Noel Chauffer <info@noelchauffer.com>",
        )

    def test_from_address_defaults_to_info(self):
        os.environ.pop("RESEND_FROM", None)
        self.assertEqual(
            email_sender._from_address(),
            "Noel Chauffer <info@noelchauffer.com>",
        )

    def test_from_address_override_still_wins(self):
        os.environ["RESEND_FROM"] = "Noel Chauffer <other@noelchauffer.com>"
        try:
            self.assertEqual(
                email_sender._from_address(),
                "Noel Chauffer <other@noelchauffer.com>",
            )
        finally:
            os.environ.pop("RESEND_FROM", None)

    def test_no_old_address_anywhere_in_repo(self):
        leftovers = []
        for path in sorted(REPO_DIR.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in SCAN_SUFFIXES:
                continue
            if any(part in SCAN_SKIP_DIRS for part in path.parts):
                continue
            # This test file itself names the old address (OLD constant)
            # so it can assert its absence everywhere else.
            if path.name == "test_info_email.py":
                continue
            if OLD in path.read_text(errors="ignore"):
                leftovers.append(str(path.relative_to(REPO_DIR)))
        self.assertEqual(leftovers, [])

    def test_customer_pages_show_info(self):
        for rel in PAGES:
            html = (REPO_DIR / rel).read_text()
            self.assertIn(NEW, html, rel)
            self.assertNotIn(OLD, html, rel)

    def test_translated_email_us_strings_show_info(self):
        i18n = (REPO_DIR / "static/js/i18n.js").read_text()
        self.assertIn(NEW, i18n)
        self.assertNotIn(OLD, i18n)

    def test_auto_reply_bank_uses_info(self):
        bank = (REPO_DIR / "support-auto-replies.md").read_text()
        self.assertIn(NEW, bank)
        self.assertNotIn(OLD, bank)


if __name__ == "__main__":
    unittest.main()
