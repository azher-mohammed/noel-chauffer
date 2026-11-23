"""Tests for the class-page Continue change (owner order, voice call
2026-11-22 ~18:50 EST, from his phone screenshot of the class page).

- KEEP: Your name, Phone number, Email fields.
- REMOVE everything below the Email field: the "Sign in to continue"
  line, the "Signed in as ..." line, the "Use a different email" link.
- REMOVE the sticky bottom bar with the "Select Business Class" /
  "Select Business SUV" buttons — no select buttons down there.
- ADD one "Continue" button directly below the Email field. Tapping
  a class card still selects that class (Business pre-selected);
  Continue signs in AND proceeds to payment with the selected class.
- ALSO FIX (standing form-fix order): stack Phone and Email
  FULL-WIDTH on narrow screens so a long email never truncates.
- KEEP: the "Please note" bullets, the class cards + price breakdown,
  and the "← Back to booking form" link.
- The sign-in session logic itself is unchanged — only the display
  lines are gone. The hourly class step keeps its own Select button
  (it has no details fields, so Continue-under-email does not apply).

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as f:
        return f.read()


def _class_step(html, step_id, back_id):
    """The one-way class step only (not the hourly step, not the
    history screen, which keeps its own "Signed in as" line). The
    slice runs through the Back button at the end of the step."""
    start = html.index('id="%s"' % step_id)
    back = html.index('id="%s"' % back_id, start)
    end = html.index('</button>', back) + len('</button>')
    return html[start:end]


class ClassContinueButtonTest(unittest.TestCase):
    """Website + customer app class page: Continue, no Select bar."""

    def setUp(self):
        self.html = _read("static/index.html")
        self.app_html = _read("static/customer-app.html")
        self.js = _read("static/js/customer.js")
        self.app_js = _read("static/js/customer-app.js")
        self.css = _read("static/css/customer.css")
        self.app_css = _read("static/css/customer-app.css")
        self.step = _class_step(self.html, "class-step", "class-back")
        self.app_step = _class_step(self.app_html, "ca-class-step",
                                    "ca-class-back")

    def test_signin_lines_gone_from_class_step(self):
        for step in (self.step, self.app_step):
            self.assertNotIn("Sign in to continue", step)
            self.assertNotIn("Signed in as", step)
            self.assertNotIn("Use a different email", step)
            self.assertNotIn("signedin-note", step)
            self.assertNotIn("signedin-email", step)
            self.assertNotIn("signout", step)

    def test_no_select_sticky_bar_on_class_step(self):
        for step in (self.step, self.app_step):
            self.assertNotIn("Select Business Class", step)
            self.assertNotIn("Select Business SUV", step)
            self.assertNotIn("Select First Class", step)
            self.assertNotIn("class-sticky-total", step)
            self.assertNotIn("class-actions", step)
        # The hourly step keeps its own Select button (no details
        # fields there, so there is no Continue-under-email).
        self.assertIn('id="hourly-class-continue"', self.html)
        self.assertIn('id="ca-hourly-class-continue"', self.app_html)

    def test_continue_button_below_email(self):
        # Website: email field, then the Continue button, still
        # inside the Your-details block, before the Back link.
        self.assertLess(self.step.index('id="class-email"'),
                        self.step.index('id="class-signin-continue"'))
        self.assertIn('id="class-signin-continue">Continue<',
                      self.step)
        self.assertLess(self.step.index('id="class-signin-continue"'),
                        self.step.index('id="class-back"'))
        # Customer app: same, with the app's ids.
        self.assertLess(self.app_step.index('id="ca-class-email"'),
                        self.app_step.index('id="ca-signin-continue"'))
        self.assertIn('id="ca-signin-continue">Continue<',
                      self.app_step)
        # The Continue button is the prominent primary button, not a
        # ghost button.
        self.assertIn('class="btn-primary" id="class-signin-continue"',
                      self.step)
        self.assertIn('class="btn-primary btn-gold" id="ca-signin-continue"',
                      self.app_step)

    def test_contact_fields_kept(self):
        for step, pfx in ((self.step, ""), (self.app_step, "ca-")):
            self.assertIn('id="%sclass-name"' % pfx, step)
            self.assertIn('id="%sclass-phone"' % pfx, step)
            self.assertIn('id="%sclass-email"' % pfx, step)
            self.assertIn("Your name", step)
            self.assertIn("Phone number", step)
            self.assertIn("Email", step)

    def test_kept_sections(self):
        for step in (self.step, self.app_step):
            # Please note bullets above the details.
            self.assertIn("Please note", step)
            self.assertIn("final fare may change", step)
            # Class cards + price breakdown.
            self.assertIn("class-option-sedan", step)
            self.assertIn("class-option-suv", step)
            self.assertIn("class-option-first", step)
            self.assertIn("Price breakdown", step)
            # Back link stays.
            self.assertIn("Back to booking form", step)

    def test_continue_signs_in_then_proceeds(self):
        # The single Continue handler posts the sign-in, then saves
        # the contact and proceeds to payment with the selected class.
        for js, ident in ((self.js, "class-signin-continue"),
                          (self.app_js, "ca-signin-continue")):
            handler = js[js.index('$("%s").addEventListener' % ident):]
            self.assertIn("/api/customers/signin", handler)
            self.assertIn("saveContact", handler)
            self.assertIn("proceedWith", handler)
            self.assertIn("/vehicle-class", handler,
                          "class change still follows the selected card")
            # No two-step gate: Continue never stops to ask for a
            # separate sign-in first.
            self.assertNotIn("Please sign in first", js)
        # Server-side gating is untouched: /contact and /pay still
        # require the session (covered by test_customer_signin.py).
        self.assertIn("state.customerSignedIn", self.js)
        self.assertIn("state.customerSignedIn", self.app_js)

    def test_phone_email_stack_full_width_on_narrow(self):
        # Website: at phone widths the class-step field row is one
        # column, so phone and email sit one under the other.
        m = re.search(r"@media \(max-width: 560px\) \{\s*"
                      r"#class-step \.field-row \{ "
                      r"grid-template-columns: 1fr; \}",
                      self.css)
        self.assertIsNotNone(m, "website narrow stacking rule")
        self.assertIn("#class-step .field-row .field { min-width: 0; }",
                      self.css)
        m = re.search(r"@media \(max-width: 560px\) \{\s*"
                      r"#ca-class-step \.field-row \{ "
                      r"grid-template-columns: 1fr; \}",
                      self.app_css)
        self.assertIsNotNone(m, "app narrow stacking rule")
        self.assertIn("#ca-class-step .field-row .field { min-width: 0; }",
                      self.app_css)
        # The wide layout is unchanged: two columns side by side.
        self.assertIn(".field-row { display: grid; "
                      "grid-template-columns: 1fr 1fr; gap: 12px; }",
                      self.css)


if __name__ == "__main__":
    unittest.main()
