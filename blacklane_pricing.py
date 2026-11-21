"""Blacklane-style base-fare pricing engine for Noel Chauffer.

Source of truth: the Blacklane price-check workbook
``~/workspace/goals/noel-chauffer-luxury-chauffeur-website/files/blacklane-price-check-48-routes/blacklane-price-check-48-routes.xlsx``
(sheet "Quotes", 158 routes, all quoted Fri 20 Nov 2026 12:00 PM, 1
passenger, nothing booked). The 100-ride mile ladder (rows 62-161,
Times Square out to 1-100 road miles) gives the base fare per class
at each distance; the fee recipe comes from the "Business fee
breakdown" column of the same sheet.

FEE RULES (fitted from the sheet; the model reproduces all 158
Business totals exactly, and the SUV/First-Class base fares inverted
from the sheet match the ladder file's own bases to within $0.01):
- black car fee = 2.5% of the base fare, iff the PICKUP is in NY State.
- sales tax follows the PICKUP state (owner decision 2026-11-20,
  voice call — "Sales tax doosre state ke hisaab se lagana"):
  NY pickups keep the sheet rule — the PICKUP county rate
  (New York City (the five boroughs) 8.875%, Nassau County 8.625%,
  Suffolk County 8.75%) and only when the dropoff is also in NY
  State (a NY pickup to another state is still $0.00 tax, exactly
  as the sheet quotes it — the 158-route sheet reproduction and
  the 100-rung ladder are unchanged by this); a pickup in any
  other state uses that state's BASE sales-tax rate (Tax
  Foundation, "2026 Sales Tax Rates, Midyear Update", as of
  1 July 2026 — see STATE_SALES_TAX_RATES below), regardless of
  the dropoff state. The five states with no statewide sales tax
  (Alaska, Delaware, Montana, New Hampshire, Oregon) get $0.00.
  A NY pickup in any other county falls back to the NYC rate and
  is flagged ``tax_rate_estimated`` — the sheet has no row for
  those counties.
- NY State congestion $2.75 iff (pickup or dropoff is in Manhattan)
  AND pickup and dropoff are both in NY State. This is New York
  State law (NYC311: the surcharge applies only to trips that
  both begin and end in NY State and touch Manhattan south of
  96th Street) — it cannot arise anywhere else.
- MTA congestion $0.75 iff (pickup or dropoff is in Manhattan) OR
  (one endpoint is in NJ-Hudson — Hoboken / Weehawken / Jersey City /
  Newark / EWR — and the other is in the NYC five boroughs).
- Congestion surcharges stay NY-only (owner decision 2026-11-20,
  "wo tum dekh lena"): New York City is the ONLY US city with
  congestion pricing for for-hire vehicles (MTA Congestion Relief
  Zone, in effect 5 January 2025; FHV riders pay the $0.75
  per-trip surcharge, black cars included). The only other US
  congestion fee found is Chicago's downtown fee — but it applies
  to Transportation Network Providers (Uber/Lyft) ONLY and
  explicitly EXCLUDES taxis and liveries, so it does not apply
  to Noel Chauffer black-car rides and is not modelled here.
- airport access $3.50 iff pickup or dropoff is a NY-metro airport
  (JFK, LaGuardia, Newark/EWR).
- total = base + airport + congestion + MTA + tax + black car fee.
- Non-NY airports (LAX, MIA, SFO, ATL, DFW, SEA, ...) carry a
  "Meet & Greet" fee instead ($4.28-$20.33, airport-specific) in the
  sheet; this NY-metro engine does NOT model Meet & Greet — a route
  touching a non-NY airport is flagged ``meet_and_greet_unknown`` and
  its total excludes that fee.
- minimum-fare floor: the base fare never drops below the rung-1
  base — Business $112.97, Business SUV $175.37, First Class $187.93
  (rungs 1-3 all price at the Business floor, total $129.32).

CUSTOMER TOTAL vs MAP TOLL: Blacklane's own quote has no separate
route-toll line — its total is base + the fees above. So the
Blacklane-style customer total here is base + fees ONLY; the map toll
(the E-ZPass crossings from tolls.py, kept on the booking as before)
is NOT added to what the customer pays. The driver still gets the
map toll in his pay (driver earnings = flat slab + map toll), so
in Blacklane mode the map toll comes out of Noel's profit. If the
owner wants the toll added on top of the Blacklane total instead,
that is a one-line change in ``compute_blacklane_one_way``.

DRIVER PAY — FLAT SLAB (owner decision 2026-11-20 ~06:25 EST,
"Slap wala"): the driver gets pricing.driver_slab_pay(miles,
class) + map toll — NOT per mile. The old per-mile rates (sedan
$4/mi, SUV $6/mi, First Class $9/mi) are gone from this engine.
CUSTOMER FLAT (owner decision 2026-11-20 ~06:38 EST): at miles
<= 10, Business Class is a flat $100 and Business SUV a flat
$130, charged exactly; First Class keeps the engine total.
The engine computes the First Class customer fare AND driver pay. First Class
is OPEN since owner decision 2026-11-20 ~03:00 EST ("wahi daal dena
na same" — same models as Blacklane), expanded 2026-11-21 by owner
order to twelve models: Blacklane's four plus Bentley Bentayga /
Flying Spur / Mulsanne, Mercedes-Benz Maybach S-Class, Rolls-Royce
Cullinan / Ghost / Phantom and Lamborghini Urus (see
car_models.FIRST_CLASS_MODELS; app.py: driver_matches_booking_class).
It exists only in Blacklane
mode — the legacy engine has no First Class rate, so selection
refuses "first" while NOEL_PRICING is legacy.

GATING: this engine changes NO live price by itself. The app uses it
only when ``NOEL_PRICING=blacklane`` (see pricing.pricing_mode);
the default is the legacy $9/$10 formula. The preview endpoint
``GET /api/fare-preview`` returns both totals for comparison.

DISTANCE-ONLY MODEL, READ THIS: the ladder prices by road miles from
Times Square. Real Blacklane base fares vary by ROUTE at the same
distance (airport routes cost more per mile, some suburban routes
less), so the interpolated base can sit ~$10-17 off a real route's
quoted base — e.g. JFK -> Times Square interpolates to ~$167.79
against the quoted $175.91, and Valley Stream -> JFK to ~$149.90
against the quoted $134.47. The ladder rungs themselves reproduce
exactly; any other route is an estimate. The fee rules, applied to
a route's own quoted base, reproduce that route's total exactly.

SUB-CENT LADDER BASES (owner hard rule 2026-11-20 ~02:32 EST:
"dono mein ek rupay ka fark nahi aana" — zero difference to the
cent between Blacklane's total and Noel's, on all 100 ladder rungs
x 3 classes): the ladder points below carry base fares to four
decimals, recovered from the sheet totals. Blacklane's own totals
were built from fractional bases, while the sheet prints each base
rounded to cents — on three rungs (64 Business, 80 Business, 90
SUV) the rounded base pushes the recomputed total a cent over the
sheet total. The recovered bases reproduce every one of the 300
sheet rung totals exactly (see tests/test_blacklane_pricing.py::
LadderExactCase, which pins all 100 rungs x 3 classes against the
sheet). The displayed base is still rounded to cents; only the
fee computation uses the precise value.
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

from pricing import REFERRAL_DISCOUNT_RATE, driver_slab_pay, money

CENT = Decimal("0.01")

# ---------------------------------------------------------------- classes --

# Internal keys stay "sedan"/"suv" (as in pricing.py); "first" is the
# NEW third class. NOTE: do NOT add "first" to pricing.CLASS_LABELS /
# pricing.CLASS_RATES — tests pin those to the two legacy classes and
# the legacy engine has no First Class at all.
BLACKLANE_CLASSES = ("sedan", "suv", "first")
BLACKLANE_CLASS_LABELS = {
    "sedan": "Business Class",
    "suv": "Business SUV",
    "first": "First Class",
}
# Driver pay is NOT per mile here any more: the owner's FLAT slab
# system (pricing.driver_slab_pay) applies in Blacklane mode too —
# owner decision 2026-11-20 ~06:25 EST, voice call ("Slap wala").
# The old per-mile rates (sedan $4/mi, SUV $6/mi, First $9/mi)
# are gone from this engine; the slab table lives in pricing.py.
# Customer FLAT total for short rides (owner decision 2026-11-20
# ~06:38 EST, voice call): 1-10 miles, Business Class $100,
# Business SUV $130 — the customer is charged exactly that, no
# Blacklane base/fees on top. First Class is NOT flat: it keeps
# the Blacklane engine total ("rehne do jaisa hai waisa").
# The flat applies at miles <= 10 (a 0.5-mile ride is in the band).
CUSTOMER_FLAT_1_TO_10 = {
    "sedan": Decimal("100"),
    "suv": Decimal("130"),
}


def blacklane_class_label(vehicle_class):
    """Customer-facing display name for a Blacklane class key."""
    return BLACKLANE_CLASS_LABELS.get(vehicle_class)


# -------------------------------------------------------------------- fees --

AIRPORT_ACCESS_FEE = Decimal("3.50")
NY_CONGESTION_FEE = Decimal("2.75")
MTA_CONGESTION_FEE = Decimal("0.75")
BLACK_CAR_FEE_RATE = Decimal("0.025")
NYC_TAX_RATE = Decimal("0.08875")
NASSAU_TAX_RATE = Decimal("0.08625")
SUFFOLK_TAX_RATE = Decimal("0.0875")

# Endpoint classification keywords. These are the text fallback used
# when the geocoder gave no state/county for an endpoint; geocoder
# data (state/county/city) always wins over the keywords. The
# state-suffix override (NON_NY_MARKERS) is checked FIRST so
# "Ridgewood NJ" never matches the Queens "Ridgewood" keyword.
_MANHATTAN_KEYWORDS = (
    "times square", "manhattan", "empire state", "madison square",
    "gracie mansion", "mount sinai", "city college", "rockefeller",
    "metropolitan museum",
)
_NY_KEYWORDS = _MANHATTAN_KEYWORDS + (
    "brooklyn", "queens", "bronx", "staten island", "long island",
    "astoria", "flushing", "jackson heights", "rego park", "unisphere",
    "long island city", "jamaica", "forest hills", "kew gardens",
    "elmhurst", "woodside", "sunnyside", "corona", "bayside",
    "douglaston", "fresh meadows", "whitestone", "college point",
    "maspeth", "middle village", "ridgewood", "glendale", "ozone park",
    "richmond hill", "howard beach", "rockaway", "hollis",
    "queens village", "st. albans", "springfield gardens", "rosedale",
    "laurelton", "cambria heights", "bellerose", "floral park",
    "glen oaks", "new hyde park", "great neck", "port washington",
    "manhasset", "roslyn", "albertson", "williston park",
    "east williston", "park slope", "williamsburg", "greenpoint",
    "bushwick", "bedford-stuyvesant", "crown heights", "flatbush",
    "bay ridge", "bensonhurst", "sheepshead bay", "coney island",
    "brighton beach", "sunset park", "dyker heights", "borough park",
    "canarsie", "east new york", "brownsville", "citi field",
    "riverdale", "van cortlandt",
    "valley stream", "hempstead", "garden city", "nassau", "syosset",
    "huntington", "northport", "brentwood", "east islip", "ronkonkoma",
    "sayville", "patchogue", "coram", "miller place", "sound beach",
    "rocky point", "shirley", "mastic", "moriches", "wading river",
    "calverton", "mineola", "hicksville", "westbury", "carle place",
    "uniondale", "freeport", "baldwin", "oceanside",
    "rockville centre", "lynbrook", "east rockaway", "malverne",
    "franklin square", "garden city park", "levittown", "wantagh",
    "seaford", "massapequa", "farmingdale", "plainview",
    "old bethpage", "bethpage", "jericho", "woodbury", "oyster bay",
    "glen cove", "locust valley", "bayville", "muttontown",
    "east meadow", "bellmore", "merrick", "roosevelt", "island park",
    "long beach", "atlantic beach", "lido beach", "point lookout",
    "east atlantic beach",
    "east hampton", "southampton", "montauk", "suffolk", "quogue",
    "sag harbor", "riverhead", "hampton bays", "westhampton",
    "eastport", "manorville", "center moriches", "east moriches",
    "east quogue", "bridgehampton", "water mill", "sagaponack",
    "wainscott", "amagansett", "shelter island", "greenport",
    "southold", "mattituck", "cutchogue", "peconic", "jamesport",
    "laurel", "aquerbogue", "east marion", "orient",
    "fishers island",
    "yonkers", "mount vernon", "pelham", "irvington", "mamaroneck",
    "white plains", "tarrytown", "pocantico", "chappaqua", "cortlandt",
    "katonah", "peekskill", "verplanck", "lincolndale", "garrison",
    "lewisboro", "brewster", "hopewell", "beacon", "plattekill",
    "gardiner", "new paltz", "dover plains", "salt point", "rosendale",
    "hyde park", "kingston", "stone ridge",
    "jfk", "la guardia", "laguardia",
)
_NASSAU_KEYWORDS = (
    "valley stream", "hempstead", "garden city", "nassau", "syosset",
    "huntington", "northport", "brentwood", "east islip", "ronkonkoma",
    "sayville", "patchogue", "coram", "miller place", "sound beach",
    "rocky point", "shirley", "mastic", "moriches", "wading river",
    "calverton", "mineola", "hicksville", "westbury", "carle place",
    "uniondale", "freeport", "baldwin", "oceanside",
    "rockville centre", "lynbrook", "east rockaway", "malverne",
    "franklin square", "garden city park", "new hyde park",
    "great neck", "port washington", "manhasset", "roslyn",
    "albertson", "williston park", "east williston", "levittown",
    "wantagh", "seaford", "massapequa", "farmingdale", "plainview",
    "old bethpage", "bethpage", "jericho", "woodbury", "oyster bay",
    "glen cove", "locust valley", "bayville", "muttontown",
    "east meadow", "bellmore", "merrick", "roosevelt", "island park",
    "long beach", "atlantic beach", "lido beach", "point lookout",
    "east atlantic beach",
)
_SUFFOLK_KEYWORDS = (
    "east hampton", "southampton", "montauk", "suffolk", "quogue",
    "sag harbor", "riverhead", "hampton bays", "westhampton",
    "eastport", "manorville", "center moriches", "east moriches",
    "east quogue", "bridgehampton", "water mill", "sagaponack",
    "wainscott", "amagansett", "shelter island", "greenport",
    "southold", "mattituck", "cutchogue", "peconic", "jamesport",
    "laurel", "aquerbogue", "east marion", "orient", "fishers island",
)
# Explicit non-NY markers — checked BEFORE any NY keyword, so a
# New Jersey / Connecticut / Pennsylvania place that shares a name
# with a NY neighbourhood (Ridgewood NJ vs Ridgewood Queens) is
# never misclassified as NY.
_NON_NY_MARKERS = (
    "new jersey", "connecticut", "pennsylvania", "massachusetts",
    " NJ", " CT", " PA", " MA", ", nj", ", ct", ", pa", ", ma",
    "(nj)", "(ct)", "philadelphia", "stamford", "greenwich", "newark",
    "hoboken", "weehawken", "jersey city", "ridgewood nj", "clifton",
    "montclair", "paramus", "livingston", "linden", "chatham",
    "mahwah", "cos cob", "perth amboy", "keyport", "glenbrook",
    "westport", "freehold", "kearny", "south orange", "new milford",
    "hamden", "meriden", "clinton", "sharon",
)
_NJ_HUDSON_KEYWORDS = ("hoboken", "weehawken", "jersey city", "newark", "ewr")
_NYC5_KEYWORDS = (
    "manhattan", "brooklyn", "queens", "bronx", "staten island",
    "times square", "astoria", "flushing", "williamsburg",
    "long island city", "jamaica", "rego park", "jackson heights",
    "citi field", "riverdale", "van cortlandt", "jfk", "la guardia",
    "laguardia",
)
_AIRPORT_KEYWORDS = ("jfk", "la guardia", "laguardia", "newark", "ewr")
_NYC_COUNTY_RATES = {
    "new york county": ("NYC", NYC_TAX_RATE),
    "kings county": ("NYC", NYC_TAX_RATE),
    "queens county": ("NYC", NYC_TAX_RATE),
    "bronx county": ("NYC", NYC_TAX_RATE),
    "richmond county": ("NYC", NYC_TAX_RATE),
    "nassau county": ("Nassau", NASSAU_TAX_RATE),
    "suffolk county": ("Suffolk", SUFFOLK_TAX_RATE),
}
_NJ_HUDSON_CITIES = {"hoboken", "weehawken", "jersey city", "newark"}

# Base STATEWIDE sales-tax rates (owner decision 2026-11-20, voice
# call — "Sales tax doosre state ke hisaab se lagana"): a pickup in
# any state other than NY is taxed at that state's base rate.
# Source: Tax Foundation, "2026 Sales Tax Rates, Midyear Update",
# state-rate column as of 1 July 2026
# (taxfoundation.org/data/all/state/2026-sales-tax-rates-midyear/).
# The column already includes the mandatory statewide local add-ons
# for California (1.25%), Utah (1.25%) and Virginia (1%). NY is NOT
# in this table — NY pickups use the county rates above. The five
# states with no statewide sales tax sit here at 0.00 (Alaska
# localities may add their own local tax, averaging 1.82% — not
# modelled). District of Columbia is 6.00%.
# Exact decimals (the Foundation prints them rounded): NJ 6.625%,
# MN 6.875%, MO 4.225%, NM 4.875%.
STATE_SALES_TAX_RATES = {
    "AL": Decimal("0.04"), "AK": Decimal("0.00"),
    "AZ": Decimal("0.056"), "AR": Decimal("0.065"),
    "CA": Decimal("0.0725"), "CO": Decimal("0.029"),
    "CT": Decimal("0.0635"), "DE": Decimal("0.00"),
    "DC": Decimal("0.06"), "FL": Decimal("0.06"),
    "GA": Decimal("0.04"), "HI": Decimal("0.04"),
    "ID": Decimal("0.06"), "IL": Decimal("0.0625"),
    "IN": Decimal("0.07"), "IA": Decimal("0.06"),
    "KS": Decimal("0.065"), "KY": Decimal("0.06"),
    "LA": Decimal("0.05"), "ME": Decimal("0.055"),
    "MD": Decimal("0.06"), "MA": Decimal("0.0625"),
    "MI": Decimal("0.06"), "MN": Decimal("0.06875"),
    "MS": Decimal("0.07"), "MO": Decimal("0.04225"),
    "MT": Decimal("0.00"), "NE": Decimal("0.055"),
    "NV": Decimal("0.0685"), "NH": Decimal("0.00"),
    "NJ": Decimal("0.06625"), "NM": Decimal("0.04875"),
    "NC": Decimal("0.0475"), "ND": Decimal("0.05"),
    "OH": Decimal("0.0575"), "OK": Decimal("0.045"),
    "OR": Decimal("0.00"), "PA": Decimal("0.06"),
    "RI": Decimal("0.07"), "SC": Decimal("0.06"),
    "SD": Decimal("0.042"), "TN": Decimal("0.07"),
    "TX": Decimal("0.0625"), "UT": Decimal("0.061"),
    "VT": Decimal("0.06"), "VA": Decimal("0.053"),
    "WA": Decimal("0.065"), "WV": Decimal("0.06"),
    "WI": Decimal("0.05"), "WY": Decimal("0.04"),
}

# US state full name / abbreviation (lowercase) -> 2-letter code.
# Built from STATE_SALES_TAX_RATES plus NY (county rates, not the
# state table). Geocoder values arrive as full names ("New Jersey")
# or codes ("NJ", "US-NJ"); typed text arrives as ", NJ" suffixes
# or full names ("Newark, NJ", "Stamford, Connecticut").
_STATE_NAME_TO_CODE = {
    "alabama": "AL", "al": "AL",
    "alaska": "AK", "ak": "AK",
    "arizona": "AZ", "az": "AZ",
    "arkansas": "AR", "ar": "AR",
    "california": "CA", "ca": "CA",
    "colorado": "CO", "co": "CO",
    "connecticut": "CT", "ct": "CT",
    "delaware": "DE", "de": "DE",
    "district of columbia": "DC", "dc": "DC",
    "florida": "FL", "fl": "FL",
    "georgia": "GA", "ga": "GA",
    "hawaii": "HI", "hi": "HI",
    "idaho": "ID", "id": "ID",
    "illinois": "IL", "il": "IL",
    "indiana": "IN", "in": "IN",
    "iowa": "IA", "ia": "IA",
    "kansas": "KS", "ks": "KS",
    "kentucky": "KY", "ky": "KY",
    "louisiana": "LA", "la": "LA",
    "maine": "ME", "me": "ME",
    "maryland": "MD", "md": "MD",
    "massachusetts": "MA", "ma": "MA",
    "michigan": "MI", "mi": "MI",
    "minnesota": "MN", "mn": "MN",
    "mississippi": "MS", "ms": "MS",
    "missouri": "MO", "mo": "MO",
    "montana": "MT", "mt": "MT",
    "nebraska": "NE", "ne": "NE",
    "nevada": "NV", "nv": "NV",
    "new hampshire": "NH", "nh": "NH",
    "new jersey": "NJ", "nj": "NJ",
    "new mexico": "NM", "nm": "NM",
    "new york": "NY", "ny": "NY",
    "north carolina": "NC", "nc": "NC",
    "north dakota": "ND", "nd": "ND",
    "ohio": "OH", "oh": "OH",
    "oklahoma": "OK", "ok": "OK",
    "oregon": "OR", "or": "OR",
    "pennsylvania": "PA", "pa": "PA",
    "rhode island": "RI", "ri": "RI",
    "south carolina": "SC", "sc": "SC",
    "south dakota": "SD", "sd": "SD",
    "tennessee": "TN", "tn": "TN",
    "texas": "TX", "tx": "TX",
    "utah": "UT", "ut": "UT",
    "vermont": "VT", "vt": "VT",
    "virginia": "VA", "va": "VA",
    "washington": "WA", "wa": "WA",
    "west virginia": "WV", "wv": "WV",
    "wisconsin": "WI", "wi": "WI",
    "wyoming": "WY", "wy": "WY",
}


# ------------------------------------------------------------------- ladder --
# Base fare per class at each ladder distance (road miles from Times
# Square), from /tmp/ladder_quotes_fixed.json — the 100-ride mile
# ladder quoted 2026-11-20 via Blacklane's public quote API (same
# endpoint the website uses). Points are sorted by miles; to rebuild
# this table, re-run the ladder quote and invert each rung's total
# with the fee rules above (base = (total - fixed fees) /
# (1 + tax rate + 0.025)). The Business floor ($112.97) is the rung-1
# base; SUV ($175.37) and First Class ($187.93) floors are their
# rung-1 bases.
LADDER = {
    "sedan": [
        (1.08, Decimal("112.97")),
        (2.05, Decimal("112.97")),
        (2.87, Decimal("112.97")),
        (4.1, Decimal("116.52")),
        (4.93, Decimal("114.57")),
        (5.97, Decimal("125.88")),
        (6.77, Decimal("127.86")),
        (7.96, Decimal("139.14")),
        (8.9, Decimal("131.93")),
        (10.2, Decimal("138.21")),
        (11.0, Decimal("141.10")),
        (11.97, Decimal("145.02")),
        (12.95, Decimal("147.96")),
        (14.05, Decimal("151.81")),
        (14.93, Decimal("162.07")),
        (15.75, Decimal("166.42")),
        (16.87, Decimal("163.3195")),
        (18.0, Decimal("168.22")),
        (19.22, Decimal("168.2784")),
        (20.01, Decimal("174.75")),
        (20.94, Decimal("175.73")),
        (21.74, Decimal("180.62")),
        (23.21, Decimal("185.77")),
        (23.98, Decimal("186.17")),
        (24.97, Decimal("197.63")),
        (25.94, Decimal("194.04")),
        (27.06, Decimal("195.12")),
        (28.02, Decimal("198.39")),
        (29.06, Decimal("202.13")),
        (30.13, Decimal("207.21")),
        (30.99, Decimal("211.67")),
        (32.05, Decimal("217.94")),
        (33.03, Decimal("220.13")),
        (34.19, Decimal("223.0024")),
        (34.74, Decimal("229.93")),
        (35.73, Decimal("229.26")),
        (37.36, Decimal("239.23")),
        (38.08, Decimal("242.54")),
        (39.03, Decimal("240.54")),
        (39.83, Decimal("250.70")),
        (41.05, Decimal("255.99")),
        (41.94, Decimal("251.73")),
        (42.9, Decimal("266.09")),
        (44.05, Decimal("258.52")),
        (44.98, Decimal("262.55")),
        (45.95, Decimal("267.61")),
        (46.95, Decimal("282.58")),
        (48.28, Decimal("277.98")),
        (48.84, Decimal("275.63")),
        (50.02, Decimal("286.34")),
        (50.99, Decimal("281.16")),
        (51.87, Decimal("286.29")),
        (52.79, Decimal("293.05")),
        (53.97, Decimal("294.62")),
        (55.09, Decimal("300.63")),
        (56.0, Decimal("308.94")),
        (56.82, Decimal("302.29")),
        (57.94, Decimal("324.34")),
        (58.8, Decimal("308.85")),
        (59.83, Decimal("326.94")),
        (60.92, Decimal("329.43")),
        (62.59, Decimal("334.08")),
        (63.0, Decimal("323.70")),
        (64.02, Decimal("328.1975")),
        (64.71, Decimal("331.62")),
        (65.91, Decimal("333.20")),
        (66.99, Decimal("335.68")),
        (67.97, Decimal("345.01")),
        (68.78, Decimal("326.02")),
        (69.83, Decimal("354.45")),
        (71.13, Decimal("348.96")),
        (71.95, Decimal("348.32")),
        (73.07, Decimal("357.56")),
        (74.1, Decimal("357.5812")),
        (75.08, Decimal("357.74")),
        (75.64, Decimal("362.42")),
        (76.97, Decimal("365.56")),
        (78.21, Decimal("368.45")),
        (78.75, Decimal("374.99")),
        (79.8, Decimal("373.3975")),
        (80.68, Decimal("377.63")),
        (81.82, Decimal("378.52")),
        (83.11, Decimal("379.95")),
        (84.05, Decimal("386.85")),
        (85.11, Decimal("385.36")),
        (86.12, Decimal("388.82")),
        (87.15, Decimal("393.72")),
        (88.03, Decimal("401.78")),
        (89.29, Decimal("398.04")),
        (89.84, Decimal("398.88")),
        (90.98, Decimal("405.33")),
        (91.83, Decimal("409.62")),
        (92.86, Decimal("409.66")),
        (94.22, Decimal("435.38")),
        (95.17, Decimal("414.16")),
        (96.25, Decimal("418.84")),
        (96.28, Decimal("419.31")),
        (97.78, Decimal("421.78")),
        (99.04, Decimal("431.17")),
        (100.24, Decimal("433.06")),
    ],
    "suv": [
        (1.08, Decimal("175.37")),
        (2.05, Decimal("178.07")),
        (2.87, Decimal("183.87")),
        (4.1, Decimal("189.78")),
        (4.93, Decimal("187.18")),
        (5.97, Decimal("202.27")),
        (6.77, Decimal("204.8982")),
        (7.96, Decimal("219.95")),
        (8.9, Decimal("210.33")),
        (10.2, Decimal("218.70")),
        (11.0, Decimal("222.57")),
        (11.97, Decimal("227.79")),
        (12.95, Decimal("231.71")),
        (14.05, Decimal("236.84")),
        (14.93, Decimal("250.52")),
        (15.75, Decimal("256.32")),
        (16.87, Decimal("252.19")),
        (18.0, Decimal("258.72")),
        (19.22, Decimal("258.81")),
        (20.01, Decimal("267.43")),
        (20.94, Decimal("268.74")),
        (21.74, Decimal("275.26")),
        (23.21, Decimal("282.13")),
        (23.98, Decimal("282.67")),
        (24.97, Decimal("297.94")),
        (25.94, Decimal("293.15")),
        (27.06, Decimal("294.5883")),
        (28.02, Decimal("298.95")),
        (29.06, Decimal("303.9394")),
        (30.13, Decimal("310.72")),
        (30.99, Decimal("316.66")),
        (32.05, Decimal("325.03")),
        (33.03, Decimal("327.94")),
        (34.19, Decimal("331.78")),
        (34.74, Decimal("341.01")),
        (35.73, Decimal("340.12")),
        (37.36, Decimal("353.41")),
        (38.08, Decimal("357.84")),
        (39.03, Decimal("355.17")),
        (39.83, Decimal("368.71")),
        (41.05, Decimal("375.77")),
        (41.94, Decimal("370.0798")),
        (42.9, Decimal("389.2422")),
        (44.05, Decimal("379.14")),
        (44.98, Decimal("384.5110")),
        (45.95, Decimal("391.2713")),
        (46.95, Decimal("411.22")),
        (48.28, Decimal("405.10")),
        (48.84, Decimal("401.96")),
        (50.02, Decimal("416.24")),
        (50.99, Decimal("409.33")),
        (51.87, Decimal("416.1720")),
        (52.79, Decimal("425.19")),
        (53.97, Decimal("427.28")),
        (55.09, Decimal("435.30")),
        (56.0, Decimal("446.3706")),
        (56.82, Decimal("437.52")),
        (57.94, Decimal("466.46")),
        (58.8, Decimal("446.2493")),
        (59.83, Decimal("469.22")),
        (60.92, Decimal("471.86")),
        (62.59, Decimal("476.78")),
        (63.0, Decimal("465.78")),
        (64.02, Decimal("470.56")),
        (64.71, Decimal("474.18")),
        (65.91, Decimal("475.85")),
        (66.99, Decimal("478.47")),
        (67.97, Decimal("488.36")),
        (68.78, Decimal("468.25")),
        (69.83, Decimal("498.36")),
        (71.13, Decimal("492.54")),
        (71.95, Decimal("491.87")),
        (73.07, Decimal("501.64")),
        (74.1, Decimal("501.67")),
        (75.08, Decimal("501.84")),
        (75.64, Decimal("506.79")),
        (76.97, Decimal("510.11")),
        (78.21, Decimal("513.18")),
        (78.75, Decimal("520.11")),
        (79.8, Decimal("518.43")),
        (80.68, Decimal("522.91")),
        (81.82, Decimal("523.85")),
        (83.11, Decimal("525.36")),
        (84.05, Decimal("532.67")),
        (85.11, Decimal("531.09")),
        (86.12, Decimal("534.75")),
        (87.15, Decimal("539.94")),
        (88.03, Decimal("548.48")),
        (89.29, Decimal("544.51")),
        (89.84, Decimal("545.3975")),
        (90.98, Decimal("552.23")),
        (91.83, Decimal("556.74")),
        (92.86, Decimal("556.78")),
        (94.22, Decimal("582.50")),
        (95.17, Decimal("561.28")),
        (96.25, Decimal("565.96")),
        (96.28, Decimal("566.43")),
        (97.78, Decimal("568.90")),
        (99.04, Decimal("578.29")),
        (100.24, Decimal("580.18")),
    ],
    "first": [
        (1.08, Decimal("187.93")),
        (2.05, Decimal("190.35")),
        (2.87, Decimal("197.94")),
        (4.1, Decimal("205.69")),
        (4.93, Decimal("202.29")),
        (5.97, Decimal("222.06")),
        (6.77, Decimal("225.51")),
        (7.96, Decimal("245.22")),
        (8.9, Decimal("232.6224")),
        (10.2, Decimal("243.59")),
        (11.0, Decimal("248.65")),
        (11.97, Decimal("255.50")),
        (12.95, Decimal("260.63")),
        (14.05, Decimal("267.37")),
        (14.93, Decimal("285.29")),
        (15.75, Decimal("292.89")),
        (16.87, Decimal("287.47")),
        (18.0, Decimal("296.03")),
        (19.22, Decimal("296.15")),
        (20.01, Decimal("307.45")),
        (20.94, Decimal("309.16")),
        (21.74, Decimal("317.71")),
        (23.21, Decimal("326.6996")),
        (23.98, Decimal("327.41")),
        (24.97, Decimal("347.42")),
        (25.94, Decimal("341.15")),
        (27.06, Decimal("343.0386")),
        (28.02, Decimal("348.75")),
        (29.06, Decimal("355.29")),
        (30.13, Decimal("364.18")),
        (30.99, Decimal("371.96")),
        (32.05, Decimal("382.93")),
        (33.03, Decimal("386.74")),
        (34.19, Decimal("391.76")),
        (34.74, Decimal("403.86")),
        (35.73, Decimal("402.70")),
        (37.36, Decimal("420.12")),
        (38.08, Decimal("425.91")),
        (39.03, Decimal("422.42")),
        (39.83, Decimal("440.16")),
        (41.05, Decimal("449.42")),
        (41.94, Decimal("441.96")),
        (42.9, Decimal("467.06")),
        (44.05, Decimal("453.83")),
        (44.98, Decimal("460.87")),
        (45.95, Decimal("469.72")),
        (46.95, Decimal("495.87")),
        (48.28, Decimal("487.84")),
        (48.84, Decimal("483.73")),
        (50.02, Decimal("502.45")),
        (50.99, Decimal("493.39")),
        (51.87, Decimal("502.36")),
        (52.79, Decimal("514.18")),
        (53.97, Decimal("516.91")),
        (55.09, Decimal("527.43")),
        (56.0, Decimal("541.93")),
        (56.82, Decimal("530.33")),
        (57.94, Decimal("567.91")),
        (58.8, Decimal("541.78")),
        (59.83, Decimal("570.97")),
        (60.92, Decimal("573.90")),
        (62.59, Decimal("579.37")),
        (63.0, Decimal("567.15")),
        (64.02, Decimal("572.46")),
        (64.71, Decimal("576.48")),
        (65.91, Decimal("578.34")),
        (66.99, Decimal("581.25")),
        (67.97, Decimal("592.23")),
        (68.78, Decimal("569.89")),
        (69.83, Decimal("603.34")),
        (71.13, Decimal("596.88")),
        (71.95, Decimal("596.13")),
        (73.07, Decimal("606.99")),
        (74.1, Decimal("607.02")),
        (75.08, Decimal("607.21")),
        (75.64, Decimal("612.71")),
        (76.97, Decimal("616.40")),
        (78.21, Decimal("619.81")),
        (78.75, Decimal("627.50")),
        (79.8, Decimal("625.64")),
        (80.68, Decimal("630.62")),
        (81.82, Decimal("631.66")),
        (83.11, Decimal("633.34")),
        (84.05, Decimal("641.46")),
        (85.11, Decimal("639.71")),
        (86.12, Decimal("643.7698")),
        (87.15, Decimal("649.54")),
        (88.03, Decimal("659.03")),
        (89.29, Decimal("654.62")),
        (89.84, Decimal("655.61")),
        (90.98, Decimal("663.20")),
        (91.83, Decimal("668.13")),
        (92.86, Decimal("668.17")),
        (94.22, Decimal("693.89")),
        (95.17, Decimal("672.67")),
        (96.25, Decimal("677.35")),
        (96.28, Decimal("677.82")),
        (97.78, Decimal("680.29")),
        (99.04, Decimal("689.68")),
        (100.24, Decimal("691.57")),
    ],
}



def base_fare(vehicle_class, miles):
    """Base fare for a class at a road distance, by linear interpolation.

    Returns the precise interpolated Decimal — NOT rounded to cents.
    The ladder points carry sub-cent values (recovered from the
    sheet totals so the engine reproduces them to the cent — see the
    module docstring), and the fee rules are applied to the precise
    base; callers round for display and for the total. Between
    ladder points: straight-line interpolation. Below the first
    point the base is clamped at the class floor (the rung-1 base).
    Above the last point (100.24 mi) the base extends with the
    slope of the last segment. The ladder itself is not perfectly
    monotonic — Blacklane prices by route, so a few neighbouring
    rungs dip by a few dollars (e.g. the Weehawken NJ rung prices
    above the Mount Sinai rung at a similar distance); interpolation
    keeps those dips rather than smoothing them away.
    """
    if vehicle_class not in LADDER:
        raise ValueError("vehicle_class must be 'sedan', 'suv' or 'first'")
    points = LADDER[vehicle_class]
    try:
        miles_f = float(miles)
    except (TypeError, ValueError):
        raise ValueError("miles must be a number")
    if miles_f <= points[0][0]:
        return points[0][1]
    if miles_f >= points[-1][0]:
        (m1, b1), (m2, b2) = points[-2], points[-1]
        slope = (b2 - b1) / Decimal(str(m2 - m1))
        return b2 + slope * Decimal(str(miles_f - m2))
    for (m1, b1), (m2, b2) in zip(points, points[1:]):
        if m1 <= miles_f <= m2:
            if m2 == m1:
                return b1
            frac = Decimal(str((miles_f - m1) / (m2 - m1)))
            return b1 + (b2 - b1) * frac
    return points[-1][1]  # pragma: no cover - unreachable


def _norm_state(state):
    """Geocoder state value -> 2-letter US state code (or None).

    Accepts full names ("New Jersey"), codes ("NJ") and ISO-style
    codes ("US-NJ"). Anything that is not a US state (or DC) comes
    back as the raw lowercased text, or None when empty.
    """
    text = (state or "").strip().lower()
    if not text:
        return None
    if text.startswith("us-"):
        text = text[3:]
    return _STATE_NAME_TO_CODE.get(text, text or None)


def _state_from_text(lowered):
    """State code from a typed address string (no geocoder details).

    Used only when the geocoder gave no state: a ", XX" suffix or a
    trailing " XX" code, or a full state name in the text. Full names
    are matched longest-first with word boundaries, so "West
    Virginia" wins over "Virginia" and "Arkansas" never matches
    "Kansas". District of Columbia is checked before Washington
    state, so "Washington, DC" is DC, not WA. Returns a 2-letter
    code or None.
    """
    if not lowered:
        return None
    if ("district of columbia" in lowered
            or re.search(r",\s*dc\b", lowered)
            or lowered.rstrip().endswith(" dc")):
        return "DC"
    for name in sorted(
            (n for n in _STATE_NAME_TO_CODE if len(n) > 2),
            key=len, reverse=True):
        if re.search(r"\b" + re.escape(name) + r"\b", lowered):
            return _STATE_NAME_TO_CODE[name]
    m = re.search(r",\s*([a-z]{2})\b", lowered)
    if m and m.group(1) in _STATE_NAME_TO_CODE:
        return _STATE_NAME_TO_CODE[m.group(1)]
    m = re.search(r"\b([a-z]{2})\s*$", lowered)
    if m and m.group(1) in _STATE_NAME_TO_CODE:
        return _STATE_NAME_TO_CODE[m.group(1)]
    return None


def classify_endpoint(text, details=None):
    """Classify one trip endpoint for the fee rules.

    ``text`` is the address as typed/picked; ``details`` is the
    geocoder address dict for it (geo.geocode_address — county/state/
    city when Nominatim supplied them) or None. Geocoder data wins
    over the text keywords; with no geocoder data the text fallback
    applies (state-suffix override first, then the keyword lists).

    Returns a dict: in_ny, is_manhattan, is_airport, is_nj_hudson,
    is_nyc5, state (2-letter code or None), tax_county
    ("NYC"/"Nassau"/"Suffolk"/None), tax_rate (NY county rate for NY
    pickups, the pickup state's base sales-tax rate for any other
    US state — $0.00 in the five no-tax states — or None when the
    state is unknown),
    tax_rate_estimated (True when a NY pickup county outside the
    sheet's three fell back to the NYC rate), meet_and_greet_unknown
    (True when the endpoint looks like a non-NY-metro airport, whose
    Meet & Greet fee this engine does not model).
    """
    lowered = (text or "").lower()
    details = details or {}
    # Geocoder state wins; the text fallback only fills in when the
    # geocoder gave no state at all.
    state_from_details = _norm_state(details.get("state"))
    state = state_from_details or _state_from_text(lowered)
    county = (details.get("county") or "").strip().lower()
    city = (details.get("city") or details.get("town")
            or details.get("village") or "").strip().lower()

    if state == "NY":
        in_ny = True
    elif state is not None:
        in_ny = False
    elif any(k in lowered for k in _NON_NY_MARKERS):
        in_ny = False
    else:
        in_ny = any(k in lowered for k in _NY_KEYWORDS)

    is_manhattan = county == "new york county" or any(
        k in lowered for k in _MANHATTAN_KEYWORDS)
    is_airport = any(k in lowered for k in _AIRPORT_KEYWORDS)
    is_nj_hudson = city in _NJ_HUDSON_CITIES or any(
        k in lowered for k in _NJ_HUDSON_KEYWORDS)
    is_nyc5 = county in (
        "new york county", "kings county", "queens county",
        "bronx county", "richmond county",
    ) or any(k in lowered for k in _NYC5_KEYWORDS)

    tax_county = None
    tax_rate = None
    tax_rate_estimated = False
    if county in _NYC_COUNTY_RATES:
        tax_county, tax_rate = _NYC_COUNTY_RATES[county]
    elif in_ny and state_from_details == "NY":
        # The geocoder said NY but the county is one the sheet has
        # no row for — fall back to the NYC rate and say so, rather
        # than guessing a county rate. (Only when the state came
        # from the geocoder: a text-only "Valley Stream, NY" still
        # falls through to the keyword county check below.)
        tax_county, tax_rate = "NYC", NYC_TAX_RATE
        tax_rate_estimated = True
    elif in_ny:
        if any(k in lowered for k in _NASSAU_KEYWORDS):
            tax_county, tax_rate = "Nassau", NASSAU_TAX_RATE
        elif any(k in lowered for k in _SUFFOLK_KEYWORDS):
            tax_county, tax_rate = "Suffolk", SUFFOLK_TAX_RATE
        else:
            tax_county, tax_rate = "NYC", NYC_TAX_RATE
    elif state in STATE_SALES_TAX_RATES:
        # Owner decision 2026-11-20 ("Sales tax doosre state ke
        # hisaab se lagana"): a pickup outside NY is taxed at that
        # state's base sales-tax rate — $0.00 in the five no-tax
        # states (AK, DE, MT, NH, OR). No county/local add-ons.
        tax_rate = STATE_SALES_TAX_RATES[state]

    meet_unknown = (("airport" in lowered) and not is_airport
                    and not in_ny)
    return {
        "in_ny": in_ny,
        "is_manhattan": is_manhattan,
        "is_airport": is_airport,
        "is_nj_hudson": is_nj_hudson,
        "is_nyc5": is_nyc5,
        "state": state,
        "tax_county": tax_county,
        "tax_rate": tax_rate,
        "tax_rate_estimated": tax_rate_estimated,
        "meet_and_greet_unknown": meet_unknown,
    }


def blacklane_fees(pickup, dropoff, base):
    """Fee breakdown for a base fare, from two classified endpoints.

    ``pickup``/``dropoff`` are classify_endpoint() dicts. ``base``
    arrives at FULL precision (ladder points carry sub-cent values
    recovered from the sheet totals — see the module docstring): the
    sales tax and black car fee are computed from the precise base
    and each rounded to cents, exactly as the sheet's totals were
    built. Do NOT round the base first — on the rungs whose true
    base sits a fraction of a cent below its rounded display value,
    rounding first pushes the total a cent over the sheet total.
    Returns Decimals: airport_access, ny_congestion, mta_congestion,
    sales_tax, black_car_fee, plus meet_and_greet (always $0.00 —
    non-NY-airport Meet & Greet is not modelled; see the module
    docstring) and the summed fees_total.
    """
    airport = (AIRPORT_ACCESS_FEE
               if (pickup["is_airport"] or dropoff["is_airport"])
               else Decimal("0.00"))
    congestion = (NY_CONGESTION_FEE
                  if (pickup["is_manhattan"] or dropoff["is_manhattan"])
                  and pickup["in_ny"] and dropoff["in_ny"]
                  else Decimal("0.00"))
    mta = (MTA_CONGESTION_FEE
           if (pickup["is_manhattan"] or dropoff["is_manhattan"])
           or ((pickup["is_nj_hudson"] and dropoff["is_nyc5"])
               or (dropoff["is_nj_hudson"] and pickup["is_nyc5"]))
           else Decimal("0.00"))
    # Sales tax follows the PICKUP state (owner decision 2026-11-20,
    # "Sales tax doosre state ke hisaab se lagana"): a NY pickup is
    # taxed at its county rate only when the dropoff is also in NY
    # (the sheet rule — a NY pickup to another state stays $0.00,
    # so the 158-route sheet reproduction and the 100-rung ladder
    # are unchanged); a pickup in any other state is taxed at that
    # state's base rate regardless of the dropoff. tax_rate is None
    # only when the pickup state is unknown.
    tax = (money(base * pickup["tax_rate"])
           if pickup["tax_rate"] is not None
           and (not pickup["in_ny"] or dropoff["in_ny"])
           else Decimal("0.00"))
    black_car = (money(base * BLACK_CAR_FEE_RATE)
                 if pickup["in_ny"] else Decimal("0.00"))
    fees_total = money(airport + congestion + mta + tax + black_car)
    return {
        "airport_access": airport,
        "ny_congestion": congestion,
        "mta_congestion": mta,
        "sales_tax": tax,
        "black_car_fee": black_car,
        "meet_and_greet": Decimal("0.00"),
        "fees_total": fees_total,
    }


def compute_blacklane_one_way(miles, vehicle_class, pickup_text,
                              dropoff_text, pickup_details=None,
                              dropoff_details=None, toll=Decimal("0"),
                              referral=False):
    """Blacklane-style fare breakdown for a one-way ride. All values Decimal.

    vehicle_class: "sedan" (Business Class), "suv" (Business SUV) or
    "first" (First Class). toll is the MAP toll for the route (kept
    for driver pay — see the module docstring: it is NOT added to
    the customer total). referral: a NEW customer's first booking
    with a valid referral code gets 5% off the total, driver pay
    unchanged (same rule as the legacy engine).

    Driver pay is the owner's FLAT slab (pricing.driver_slab_pay)
    + map toll for every class — NOT per mile (owner decision
    2026-11-20 ~06:25 EST). Customer total: the Blacklane
    base + fees, EXCEPT at miles <= 10 where Business Class is a
    flat $100 and Business SUV a flat $130 (owner decision
    2026-11-20 ~06:38 EST); First Class keeps the engine total.
    """
    if vehicle_class not in BLACKLANE_CLASSES:
        raise ValueError("vehicle_class must be 'sedan', 'suv' or 'first'")
    miles_dec = Decimal(str(miles))
    toll = money(toll)
    base = base_fare(vehicle_class, miles_dec)
    pickup = classify_endpoint(pickup_text, pickup_details)
    dropoff = classify_endpoint(dropoff_text, dropoff_details)
    fees = blacklane_fees(pickup, dropoff, base)
    flat_total = CUSTOMER_FLAT_1_TO_10.get(vehicle_class)
    if flat_total is not None and miles_dec <= Decimal("10"):
        # Short ride: the customer is charged exactly the flat
        # $100/$130 — no Blacklane base/fees on top of it.
        base = flat_total
        fees = {k: Decimal("0.00") for k in fees}
    total = money(base + fees["fees_total"])
    referral_discount = Decimal("0.00")
    if referral:
        referral_discount = money(total * REFERRAL_DISCOUNT_RATE)
        total = money(total - referral_discount)
    driver_earnings = money(driver_slab_pay(miles_dec, vehicle_class) + toll)
    profit = money(total - driver_earnings)
    return {
        "miles": miles_dec,
        "fare": money(base),
        "base": money(base),
        "fees": fees,
        "gratuity": Decimal("0.00"),
        "tax": fees["sales_tax"],
        "booking_fee": Decimal("0.00"),
        "toll": toll,
        "total": total,
        "referral_discount": referral_discount,
        "driver_earnings": driver_earnings,
        "profit": profit,
        "vehicle_class": vehicle_class,
        "vehicle_class_label": BLACKLANE_CLASS_LABELS[vehicle_class],
        "first_class_driver_pay_tbd": False,
        "tax_rate_estimated": pickup["tax_rate_estimated"],
        "meet_and_greet_unknown": (pickup["meet_and_greet_unknown"]
                                   or dropoff["meet_and_greet_unknown"]),
    }


def blacklane_class_totals(miles, pickup_text, dropoff_text,
                           pickup_details=None, dropoff_details=None,
                           toll=Decimal("0"), referral=False):
    """Customer total per class (sedan/suv/first) for the options page."""
    return {
        cls: compute_blacklane_one_way(
            miles, cls, pickup_text, dropoff_text,
            pickup_details=pickup_details, dropoff_details=dropoff_details,
            toll=toll, referral=referral)["total"]
        for cls in BLACKLANE_CLASSES
    }
