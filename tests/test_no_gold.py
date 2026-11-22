"""Tests for the gold removal + blue buttons + light-gold wordmark.

Owner decision, voice call 2026-11-21 ~08:45-08:47 EST ("sunehra
poora nikaal do"): ALL gold styling is gone from the website, the
customer app (/app) and the driver app (/driver). Non-button elements
are plain black / white / grey.

Standing colour rule, main chat 2026-11-21 ~09:55-09:57 EST ("I dont
like black" / "Blue kar do" / "Aab se best color use karo" / "Not black
buttons" / "Ek dum business wala button"): ALL buttons are BLUE
(#5b9bd5) with white normal text, full business look — no gradient,
no glow, normal weight. NEVER black buttons. This supersedes the
all-black buttons order of ~08:54 EST.

Wordmark exception (owner 2026-11-21 ~09:55-09:56 EST, "Only chauffeur
in Golden", refined ~10:02 EST, "Ek dum light golden kare toh"): in the
"Noel Chauffer" brand name, ONLY the word "Chauffeur" is golden, and
only in a VERY LIGHT gold (#e8cf8f — never the deep #d4af37) on dark
surfaces (website, customer app); on the WHITE driver app pages
(owner 2026-11-21 ~10:03 EST) the same word uses the deeper readable
gold #8a6d14, because the light gold does not read on white. The word
"Noel" stays white on dark backgrounds and black ink on the white
driver app. No layout or position changes.

Notes:
- The class name `.btn-gold` and the variable `var(--gold)` still
  exist by name; only their rendered values changed (the variable now
  resolves to a neutral grey/black, the class renders flat blue).
- The owner dashboard (/owner, owner.css) is NOT in scope and is not
  checked here.
- Page-background gradients (hero photo overlay, sky tints, dark
  canvas) are not buttons and are untouched.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS_FILES = ("static/css/customer.css",
             "static/css/customer-app.css",
             "static/css/driver.css")

# Gold colour values that must not render anywhere on the three surfaces.
# Includes the stragglers caught after the first live push: #e3c878 /
# #fdf3d7 (driver expiry banner), #8a6d1a (website ride-history total).
# The deep gold #d4af37 is banned too — the wordmark uses only the
# very light gold #e8cf8f on dark surfaces (website, customer app)
# and the deeper readable gold #8a6d14 on the white driver app
# (see test_gold_only_on_chauffeur_wordmark).
BANNED_VALUES = ("#c9a227", "#e8d9a0", "#a8861d", "#b08d1e", "#dcbd4d",
                 "#e6cb62", "#d4af2f", "#b8921f", "#fff4d6", "#fffdf4",
                 "#fdf6e3", "#ecd9a0", "#6b5510", "rgba(201, 162, 39",
                 "#d4af37", "#e3c878", "#fdf3d7", "#8a6d1a")

# The only allowed golds: the very light gold of the word "Chauffeur"
# on dark surfaces (website, customer app), and the deeper readable
# gold of the same word on the white driver app (owner 2026-11-21
# ~10:03 EST: driver app pages are white, so the light gold would
# not read there).
LIGHT_GOLD = "#e8cf8f"
DRIVER_GOLD = "#8a6d14"


def _read(relpath):
    with open(os.path.join(REPO_DIR, relpath), encoding="utf-8") as fh:
        return fh.read()


def _rule(css, selector):
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    if m is None:
        raise AssertionError("missing rule: %s" % selector)
    return m.group(1)


class NoGoldCase(unittest.TestCase):
    def test_no_gold_colour_values_anywhere(self):
        for rel in CSS_FILES:
            css = _read(rel)
            for token in BANNED_VALUES:
                self.assertNotIn(token, css, "%s: %s" % (rel, token))

    def test_gold_variables_resolve_to_neutrals(self):
        site = _read("static/css/customer.css")
        self.assertIn("--gold: #1a1a1a;", site)
        self.assertIn("--gold-soft: #d8d8d8;", site)
        for rel in ("static/css/customer-app.css",
                    "static/css/driver.css"):
            css = _read(rel)
            self.assertIn("--gold: #9a9a9a;", css, rel)
            self.assertIn("--gold-soft: #d8d8d8;", css, rel)

    def test_blue_is_defined_and_used(self):
        # Standing rule: buttons are blue (#5b9bd5), never black.
        for rel in CSS_FILES:
            css = _read(rel)
            self.assertIn("--blue: #5b9bd5;", css, rel)
            self.assertIn("var(--blue)", css, rel)

    def test_all_primary_buttons_flat_blue_white_text(self):
        for rel in CSS_FILES:
            css = _read(rel)
            for selector in (".btn-primary", ".btn-gold"):
                body = _rule(css, selector)
                self.assertIn("background: var(--blue);", body,
                              "%s %s" % (rel, selector))
                self.assertIn("color: var(--white);", body,
                              "%s %s" % (rel, selector))
                self.assertNotIn("linear-gradient", body,
                                 "%s %s" % (rel, selector))

    def test_driver_accept_and_toggle_blue(self):
        css = _read("static/css/driver.css")
        for selector in (".btn-accept", ".toggle-btn",
                         "#screen-home .toggle-btn"):
            body = _rule(css, selector)
            self.assertIn("background: var(--blue);", body, selector)
            self.assertIn("color: var(--white);", body, selector)
        for selector in (".toggle-btn.on",
                         "#screen-home .toggle-btn.on"):
            body = _rule(css, selector)
            self.assertIn("background: var(--blue);", body, selector)
            self.assertIn("color: var(--white);", body, selector)

    def test_chat_fab_green_and_pay_buttons_blue(self):
        # Chat with us is WhatsApp green #25D366 (owner 2026-11-22);
        # Pay buttons stay blue.
        site = _read("static/css/customer.css")
        body = _rule(site, ".chat-fab")
        self.assertIn("background: #25D366;", body, ".chat-fab")
        self.assertIn("color: var(--white);", body, ".chat-fab")
        for selector in ("#pay-open-btn",):
            body = _rule(site, selector)
            self.assertIn("background: var(--blue);", body, selector)
            self.assertIn("color: var(--white);", body, selector)
        body = _rule(site, ".pay-panel .btn-primary")
        self.assertIn("background: var(--blue);", body)
        self.assertIn("color: var(--white);", body)
        app = _read("static/css/customer-app.css")
        m = re.search(r"#ca-pay-submit\s*\{([^}]*)\}", app)
        self.assertIsNotNone(m, "missing #ca-pay-submit")
        self.assertIn("background: var(--blue);", m.group(1))
        self.assertIn("color: var(--white);", m.group(1))
        m = re.search(r"#ca-chat-send,\s*#ca-support-send\s*\{([^}]*)\}",
                      app)
        self.assertIsNotNone(m, "missing #ca-chat-send/#ca-support-send")
        self.assertIn("background: #25D366;", m.group(1))
        self.assertIn("color: var(--white);", m.group(1))

    def test_buttons_use_normal_weight(self):
        for rel in CSS_FILES:
            css = _read(rel)
            for selector in (".btn-gold",):
                body = _rule(css, selector)
                self.assertIn("font-weight: 400;", body,
                              "%s %s" % (rel, selector))

    def test_gold_only_on_chauffeur_wordmark(self):
        # ONLY the word "Chauffeur" is golden, in exactly one span rule
        # per stylesheet and nowhere else. "Noel" stays its normal
        # colour. The shade depends on the surface behind the wordmark:
        # very light gold #e8cf8f on dark (owner 2026-11-21 ~10:02 EST)
        # for the website and customer app, deeper readable gold #8a6d14
        # on the white driver app (owner 2026-11-21 ~10:03 EST).
        expected = {
            "static/css/customer.css": (".wordmark span", LIGHT_GOLD),
            "static/css/customer-app.css": (".app-head .brand span",
                                            LIGHT_GOLD),
            "static/css/driver.css": (".app-head .brand span", DRIVER_GOLD),
        }
        for rel, (selector, gold) in expected.items():
            css = _read(rel)
            self.assertEqual(css.count(gold), 1,
                             "%s: %s must appear exactly once" % (rel, gold))
            body = _rule(css, selector)
            self.assertIn("color: %s;" % gold, body, rel)
            # No deep gold anywhere, and no other surface's gold here.
            self.assertNotIn("#d4af37", css, rel)
            other = DRIVER_GOLD if gold == LIGHT_GOLD else LIGHT_GOLD
            self.assertNotIn(other, css, rel)
        # The wordmark base itself is white on dark backgrounds.
        site = _read("static/css/customer.css")
        self.assertIn(".home .wordmark { color: var(--white); }", site)
        # On the white driver app the wordmark base is black ink.
        driver = _read("static/css/driver.css")
        body = _rule(driver, ".app-head")
        self.assertIn("background: var(--white);", body)
        self.assertIn("color: var(--ink);", body)

    def test_former_gold_spots_are_neutral(self):
        # Spots the first sweep missed (caught 2026-11-21 after the
        # first live push): driver SEO headings, driver expiry banner
        # + expiry line, website referral link and ride-history total.
        driver = _read("static/css/driver.css")
        for selector in (".seo-drive h1", ".seo-drive h2",
                         ".seo-drive h3"):
            body = _rule(driver, selector)
            self.assertIn("color: #1a1a1a;", body, selector)
        body = _rule(driver, "#screen-home .expiry-banner")
        self.assertIn("border: 1px solid #c6c6c6;", body)
        self.assertIn("background: #e8e8e8;", body)
        body = _rule(driver, "#screen-documents .doc-expiry.soon")
        self.assertIn("color: #4a4a4a;", body)
        site = _read("static/css/customer.css")
        m = re.search(r"#referral-link-line a \{[^}]*color: #1a1a1a;",
                      site)
        self.assertIsNotNone(m, "referral link is not #1a1a1a")
        m = re.search(r"\.history-item \.h-total \{[^}]*color: #1a1a1a;",
                      site)
        self.assertIsNotNone(m, "history total is not #1a1a1a")


if __name__ == "__main__":
    unittest.main()
