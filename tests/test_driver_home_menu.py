"""Tests for the top-left "Home" button in the driver app.

Owner decision, voice call 2026-11-21 ~23:24 EST (final correction
after he first said bottom-right, then bottom-left): a "Home"
button at the TOP LEFT of the driver app screen, labelled "Home".
Tapping it shows: Profile, Documents, Earnings, Tax info (owner
order, voice call 2026-11-21 ~03:06 EST).

The app already has a bottom tab bar with those five tabs — the
top-left Home is in addition to it, not a replacement: the tab bar
and the home screen (availability card + job offers) stay exactly
as they are. The four menu items open the existing screens, so
their data loading (loadEarnings, loadTaxInfo, renderDocuments,
renderProfile) runs exactly as it does from the tab bar.

Static pins only (same pattern as the served-page tests in
tests/test_driver_entry_flow.py): the menu lives in shipped HTML,
CSS and JS, so these tests read the shipped files.

Run:  python -m unittest discover -s tests -v
"""

import os
import re
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(REPO_DIR, rel), encoding="utf-8") as fh:
        return fh.read()


def header_section(html):
    return html[html.index('<header class="app-head">'):
                html.index('</header>')]


def home_menu(html):
    section = header_section(html)
    return section[section.index('id="home-menu"'):]


class DriverHomeMenuCase(unittest.TestCase):
    # -- Home button: top-left of the header -------------------------
    def test_home_button_at_top_left_of_header(self):
        header = header_section(read("static/driver.html"))
        self.assertIn('id="home-menu-btn">Home</button>', header)
        # First element of the header row, before the brand: the
        # button sits at the top left, not at the bottom.
        self.assertLess(header.index('id="home-menu-btn"'),
                        header.index('class="brand"'))
        self.assertIn('class="app-head-row"', header)
        # Signed-out drivers never see it: it starts hidden and is
        # shown only on the signed-in screens (pinned in JS below).
        self.assertIn('class="home-menu-btn hidden"', header)
        self.assertNotIn('id="home-menu-btn"', read("static/driver.html")
                         .replace(header, "", 1))

    def test_home_menu_lists_four_sections_in_order(self):
        # Owner-ordered order (2026-11-21 ~03:06 EST): Profile
        # first, then Documents, then Earnings, then Tax info.
        menu = home_menu(read("static/driver.html"))
        items = re.findall(
            r'<button[^>]*data-screen="([^"]+)"[^>]*>([^<]+)</button>',
            menu)
        self.assertEqual(items, [
            ("profile", "Profile"),
            ("documents", "Documents"),
            ("earnings", "Earnings"),
            ("tax", "Tax info"),
        ])

    def test_home_menu_starts_hidden(self):
        header = header_section(read("static/driver.html"))
        self.assertIn('id="home-menu"', header)
        self.assertIn('class="home-menu hidden"', header)

    # -- tab bar and home screen: untouched ---------------------------
    def test_bottom_tab_bar_unchanged(self):
        html = read("static/driver.html")
        tabbar = html[html.index('id="tabbar"'):html.index('</nav>')]
        tabs = re.findall(
            r'data-screen="([^"]+)"[^>]*>(?:<span[^>]*>[^<]*</span>)?([^<]+)</button>',
            tabbar)
        self.assertEqual([t[0] for t in tabs],
                         ["home", "earnings", "tax", "documents", "profile"])
        self.assertEqual([t[1] for t in tabs],
                         ["Home", "Earnings", "Tax info", "Documents",
                          "Profile"])
        # Home is still the leftmost tab.
        self.assertLess(tabbar.index('data-screen="home"'),
                        tabbar.index('data-screen="earnings"'))

    def test_home_screen_unchanged(self):
        html = read("static/driver.html")
        home = html[html.index('id="screen-home"'):
                    html.index('id="screen-trip"')]
        # Owner-ordered label (2026-11-21): "Go online", not
        # "Go available"; the button sits at the bottom, below offers.
        self.assertIn('id="avail-toggle">Go online</button>', home)
        self.assertIn('id="offers-list"', home)
        self.assertIn('class="section-title">Job offers</div>', home)
        self.assertLess(home.index('id="offers-list"'),
                        home.index('id="avail-toggle"'))
        # Owner correction (2026-11-21 ~03:05 EST): no card, no
        # state line, no notes — ONLY the bare Go online button.
        self.assertNotIn('avail-card', home)
        self.assertNotIn('avail-state', home)
        self.assertNotIn('avail-note', home)

    # -- JS wiring -----------------------------------------------------
    def test_show_screen_toggles_home_button_with_tabbar(self):
        js = read("static/js/driver.js")
        show = js[js.index("function showScreen(name) {"):]
        show = show[:show.index("document.querySelectorAll(\"#tabbar button\")")]
        # The menu closes on every screen change.
        self.assertIn('hide($("home-menu"));', show)
        # Login / register / trip hide both the tab bar and the Home
        # button; every other screen shows both.
        self.assertIn('hide($("home-menu-btn"));', show)
        self.assertIn('show($("home-menu-btn"));', show)
        self.assertLess(show.index('hide($("tabbar"));'),
                        show.index('hide($("home-menu-btn"));'))
        self.assertLess(show.index('show($("tabbar"));'),
                        show.index('show($("home-menu-btn"));'))

    def test_home_button_toggles_menu(self):
        js = read("static/js/driver.js")
        handler = js[js.index('$("home-menu-btn").addEventListener'):]
        self.assertIn('$("home-menu").classList.toggle("hidden");',
                      handler[:200])

    def test_menu_items_open_their_existing_screens(self):
        js = read("static/js/driver.js")
        wiring = js[js.index('document.querySelectorAll("#home-menu button")'):]
        self.assertIn(
            'b.addEventListener("click", function () { '
            'showScreen(b.getAttribute("data-screen")); });',
            wiring[:300])

    # -- CSS: black and grey, top-left row -----------------------------
    def test_home_menu_styling_black_and_grey(self):
        css = read("static/css/driver.css")
        self.assertIn(".app-head-row { display: flex;", css)
        self.assertIn(".home-menu-btn {", css)
        self.assertIn("color: var(--gold);", css)
        self.assertIn(".home-menu {", css)
        self.assertIn("border: 1px solid var(--gold);", css)
        self.assertIn(".home-menu button {", css)


if __name__ == "__main__":
    unittest.main()
