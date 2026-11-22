"""Tests for the price breakdown on EVERY ride.

Owner decision 2026-11-21 ~18:56 EST ("Bhai wo har ride pe breakdown
banana"): the price breakdown appears on EVERY ride — all classes,
all distances, one-way AND hourly. Breakdown lines, in order:
Base fare, Airport access fee (ONLY when the ride is to/from an
airport — never on non-airport rides), Black car fee, Sales tax,
Congestion (NY State + MTA), Toll (when it applies), Total. NO refund
line anywhere in the breakdown ("nahi nahi wo nahi chahiye"). Sales
tax is the pickup location's OWN tax. Flat short rides (1-10 miles):
$100 / $130 stays as the BASE FARE line only, with the fees on top
(total above $100 — approved 2026-11-21 ~18:48 EST).

Also pinned here: the homepage section headings are links to their
own pages but must look like the plain clean headings they were
before the split — NO underline (owner correction 2026-11-21 ~18:12
EST: "Achha text liyo").

Run:  python -m unittest discover -s tests -p "test_price_breakdown_every_ride.py"
"""

import os
import re
import sys
import tempfile
import unittest

# --- test env BEFORE importing the app -------------------------------------
_tmpdir = tempfile.mkdtemp(prefix="noel-breakdown-every-ride-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"  # bookings pause is OFF in tests (owner decision 2026-11-20)
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "breakdown-every-ride-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geo as geo_module  # noqa: E402

import app as app_module  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Owner's breakdown line order (2026-11-21 ~18:56 EST).
BREAKDOWN_ORDER = ["Base fare", "Airport access fee", "Black car fee",
                   "Sales tax", "NY State congestion surcharge",
                   "MTA congestion surcharge", "Toll",
                   "Referral discount"]


def _read(relpath):
    with open(os.path.join(REPO_DIR, relpath), encoding="utf-8") as fh:
        return fh.read()


def _painter_body(js, name):
    """The body of a JS function, up to the next top-level function."""
    start = js.index("function %s" % name)
    rest = js[start:]
    m = re.search(r"\n  function ", rest[10:])
    return rest[:m.start() + 10] if m else rest


class BreakdownUiCase(unittest.TestCase):
    # -- homepage headings: links, clean text, no underline -------------
    def test_homepage_headings_are_links_with_clean_text(self):
        html = _read("static/index.html")
        for slug, text in (
                ("why-ride-with-noel-chauffer", "Why ride with Noel Chauffer"),
                ("three-ways-to-ride", "Three ways to ride"),
                ("airport-pickups", "Airport pickups, without the rush."),
                ("experience", "Sit back and enjoy the ride."),
                ("cancellation-and-waiting", "Cancellation &amp; waiting"),
                ("frequently-asked-questions", "Frequently asked questions"),
                ("our-company", "Our company"),
                ("contacts", "Contacts"),
                ("your-rides-in-your-pocket", "Your rides, in your pocket."),
                ("your-ride-history", "Your ride history")):
            self.assertIn('<h2><a href="/%s">%s</a></h2>' % (slug, text),
                          html, slug)
        css = _read("static/css/customer.css")
        m = re.search(r"\.section h2 a, \.app-band h2 a\s*\{([^}]*)\}", css)
        self.assertIsNotNone(m, "missing heading-link rule")
        self.assertIn("text-decoration: none;", m.group(1))
        self.assertIn("color: inherit;", m.group(1))

    # -- breakdown row order, website + customer app --------------------
    def test_breakdown_row_order_website(self):
        js = _read("static/js/customer.js")
        body = _painter_body(js, "paintClassBreakdown")
        positions = [body.index('"%s"' % label) for label in BREAKDOWN_ORDER]
        self.assertEqual(positions, sorted(positions),
                         "breakdown rows out of the owner's order")

    def test_breakdown_row_order_app(self):
        js = _read("static/js/customer-app.js")
        body = _painter_body(js, "paintClassBreakdown")
        positions = [body.index('"%s"' % label) for label in BREAKDOWN_ORDER]
        self.assertEqual(positions, sorted(positions),
                         "breakdown rows out of the owner's order")

    def test_breakdown_has_toll_row_and_no_refund_row(self):
        # Toll is shown when the route has one; there is NO refund
        # line anywhere in the breakdown (owner 2026-11-21 ~18:56 EST).
        for rel in ("static/js/customer.js", "static/js/customer-app.js"):
            body = _painter_body(_read(rel), "paintClassBreakdown")
            self.assertIn('"Toll"', body, rel)
            self.assertNotIn("Refund", body, rel)
            self.assertNotIn("refund", body, rel)

    # -- hourly breakdown box -------------------------------------------
    def test_hourly_breakdown_box_exists_on_both_surfaces(self):
        self.assertIn('id="hourly-class-breakdown"',
                      _read("static/index.html"))
        self.assertIn('id="ca-hourly-class-breakdown"',
                      _read("static/customer-app.html"))
        for rel in ("static/js/customer.js", "static/js/customer-app.js"):
            js = _read(rel)
            self.assertIn("function paintHourlyBreakdown", js, rel)
            body = _painter_body(js, "paintHourlyBreakdown")
            self.assertIn(">Base fare<", body, rel)
            self.assertIn(">Total<", body, rel)


class BreakdownApiCase(unittest.TestCase):
    def setUp(self):
        with app_module.app.app_context():
            app_module.db.drop_all()
            app_module.db.create_all()
        self.client = app_module.app.test_client()
        self._phone_seq = 0
        self._saved_bookings_paused = getattr(
            app_module, "BOOKINGS_PAUSED", None)
        if self._saved_bookings_paused is not None:
            app_module.BOOKINGS_PAUSED = False
        self._saved_distance_miles = geo_module.distance_miles
        self._saved_pricing = os.environ.pop("NOEL_PRICING", None)

    def tearDown(self):
        geo_module.distance_miles = self._saved_distance_miles
        if self._saved_bookings_paused is not None:
            app_module.BOOKINGS_PAUSED = self._saved_bookings_paused
        if self._saved_pricing is None:
            os.environ.pop("NOEL_PRICING", None)
        else:
            os.environ["NOEL_PRICING"] = self._saved_pricing

    def _book(self, payload):
        self._phone_seq += 1
        payload.setdefault("customer_name", "Breakdown Customer")
        payload.setdefault("phone", f"+1555007{self._phone_seq:04d}")
        payload.setdefault("email", "breakdown@test.com")
        payload.setdefault("date", "2030-06-01")
        payload.setdefault("time", "12:00")
        resp = self.client.post("/api/bookings", json=payload)
        self.assertEqual(resp.status_code, 201,
                         resp.get_data(as_text=True)[:300])
        return resp.get_json()["booking"]

    def test_flat_short_ride_booking_breakdown(self):
        # 1.08 mi Manhattan ride: the $100 flat is the BASE FARE
        # only; the fees are on top — sedan $114.88, SUV $148.29.
        # The breakdown lines sum to the total.
        geo_module.distance_miles = lambda p, d: (  # noqa: E731
            1.08, (40.7580, -73.9855), (40.7587, -73.9787))
        booking = self._book({"pickup": "Times Square",
                              "dropoff": "Rockefeller Center",
                              "ride_type": "one_way"})
        breakdowns = booking.get("class_breakdowns")
        self.assertIsNotNone(breakdowns, "booking must carry class_breakdowns")
        self.assertEqual(set(breakdowns), {"sedan", "suv", "first"})
        sedan = breakdowns["sedan"]
        self.assertEqual(sedan["base"], 100.00)
        self.assertEqual(sedan["sales_tax"], 8.88)
        self.assertEqual(sedan["black_car_fee"], 2.50)
        self.assertEqual(sedan["ny_congestion"], 2.75)
        self.assertEqual(sedan["mta_congestion"], 0.75)
        self.assertEqual(sedan["airport_access"], 0.0)
        self.assertEqual(sedan["toll"], 0.0)
        self.assertEqual(sedan["total"], 114.88)
        self.assertEqual(breakdowns["suv"]["base"], 130.00)
        self.assertEqual(breakdowns["suv"]["total"], 148.29)
        for cls, b in breakdowns.items():
            parts = (b["base"] + b["airport_access"] + b["ny_congestion"]
                     + b["mta_congestion"] + b["sales_tax"]
                     + b["black_car_fee"] + b["toll"]
                     - b["referral_discount"])
            self.assertAlmostEqual(parts, b["total"], places=2,
                                   msg="%s breakdown must sum to its total" % cls)

    def test_hourly_booking_breakdown(self):
        # 2h hourly: the rate is all-in, so the breakdown is
        # Base fare + Total with every fee line $0.00.
        booking = self._book({"pickup": "Central Park, New York",
                              "ride_type": "hourly", "hours": 2,
                              "vehicle_class": "sedan"})
        breakdowns = booking.get("class_breakdowns")
        self.assertIsNotNone(breakdowns,
                             "hourly booking must carry class_breakdowns")
        self.assertEqual(set(breakdowns), {"sedan", "suv", "first"})
        for cls, total in (("sedan", 218.32), ("suv", 269.46),
                           ("first", 343.31)):
            b = breakdowns[cls]
            self.assertEqual(b["base"], total, cls)
            self.assertEqual(b["total"], total, cls)
            for key in ("airport_access", "ny_congestion", "mta_congestion",
                        "sales_tax", "black_car_fee", "toll",
                        "referral_discount"):
                self.assertEqual(b[key], 0.0, (cls, key))


if __name__ == "__main__":
    unittest.main()
