"""Pricing for Noel Chauffer — pure functions, Decimal, ROUND_HALF_UP.

Rates are settled by the owner. Do not change them here.

ONE-WAY (decided 2026-11-16; rates revised 2026-11-17; SUPERSEDES
the old $20 booking fee + $7/mile formula entirely): TWO vehicle
classes, each with its own per-mile rate and driver rate. NO booking fee.
- Business Class (sedan): customer $9/mile, driver FLAT by distance
  slab (see DRIVER_PAY_SLABS below — owner decision 2026-11-20).
- Business SUV (SUV): customer $10/mile, driver FLAT by distance slab.
- First Class: customer rate lives in the Blacklane engine only
  (gated, not flipped); driver FLAT by distance slab (First column).
- fare = miles x class rate.
- NO TAX, NO GRATUITY (owner orders 2026-11-17: "Tax nikal doh
  mere ismein se" and "10 percent gratuity bhi nikal doh mere").
  The 8.875% NYC sales tax and the 10% gratuity were REMOVED from
  all new bookings on 2026-11-17. The breakdown dicts still carry
  "tax" and "gratuity" keys at $0.00 so stored records and the
  owner API keep their shape; rides booked before the removal keep
  their stored tax/gratuity values (history is not rewritten).
- customer total = fare + toll.
- driver earnings = slab pay for the ride's miles + toll.
- owner profit = total - driver earnings.
- UP-FRONT TOLL (owner decision 2026-11-16, extended 2026-11-17):
  the toll estimate at booking creation comes from the MAP: every
  tolled crossing the route passes through is charged at the
  verified E-ZPass rate (see tolls.py), PLUS the $16.79 Port
  Authority return crossing (Holland Tunnel / Lincoln Tunnel /
  George Washington Bridge, E-ZPass peak rate, verified
  2026-11-16) on New York -> New Jersey trips. When no route
  geometry is available the Hudson toll is compulsory: ANY trip
  between New York and New Jersey in EITHER direction carries
  $16.79. The estimate is part of the single total the customer
  pays and the driver sees as a separate Toll line BEFORE
  accepting. The owner can still adjust the toll afterwards in
  the dashboard (not on completed rides).
- Referral discount (owner decision 2026-11-18, voice call): when a
  NEW customer books their FIRST ride with a valid referral code
  (from a customer's referral link), they get 5% off the total
  (fare + toll). The referring customer gets NOTHING — there is no
  referrer reward of any kind. The discount comes out of Noel's
  profit only: driver earnings are unchanged. First booking only,
  identified by phone number: a phone with any prior booking gets
  no discount. If the referred friend later refers someone else,
  that next new customer gets 5% off their first booking too
  (every booking issues its own referral code); referrers never
  earn at any step. One-way rides only; hourly rides never get a
  referral discount.
- HOURLY: total = $90/hour; driver = $50/hour. No fee, no gratuity,
  no tax. Unchanged by the tax/gratuity removal (hourly never had
  either).
- WAITING: 60 free minutes at airport pickups, else 15; then $1/minute.
  Waiting money goes to owner profit.
- CANCELLATION: free (full refund) if cancelled MORE than 1 hour before
  the pickup datetime (America/New_York); 1 hour or less keeps the full
  price.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from tolls import detect_crossing_tolls

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

CENT = Decimal("0.01")
TENTH = Decimal("0.1")

# One-way rates, per vehicle class. Internal keys stay "sedan"/"suv";
# customer-facing display names are in CLASS_LABELS.
SEDAN_RATE = Decimal("9")
SUV_RATE = Decimal("10")
# SUPERSEDED per-mile driver rates (owner decision 2026-11-20: flat
# slab pay replaced them for the base one-way fare — see
# DRIVER_PAY_SLABS below). Kept because compute_extra_distance still
# pays EXTRA miles at these rates, and the gated Blacklane engine
# (blacklane_pricing.py) still imports them. Do NOT delete.
DRIVER_SEDAN = Decimal("4")
DRIVER_SUV = Decimal("6")
CLASS_RATES = {"sedan": SEDAN_RATE, "suv": SUV_RATE}
CLASS_DRIVER_RATES = {"sedan": DRIVER_SEDAN, "suv": DRIVER_SUV}
CLASS_LABELS = {"sedan": "Business Class", "suv": "Business SUV",
                "first": "First Class"}
# No tax rate, no gratuity rate: both were removed by owner orders
# 2026-11-17. "tax"/"gratuity" breakdown keys stay at $0.00.
BOOKING_FEE = Decimal("0")

# Driver pay SLABS (owner decision 2026-11-20, voice call ~04:25 EST:
# "abhi ye kar do live"; FINAL RULE ~04:32 EST): FLAT per-ride
# driver pay by distance band, per class — NOT per mile. The 30-40
# slab is the BASE (Business $140, SUV $160, First $200); from there
# every next 10-mile slab is +$20 per class, up to 390-400
# ($860/$880/$920). Values verified against the draft sheet
# driver-pay-slabs-draft.xlsx. Each entry is (upper miles bound,
# {class: flat pay}); a ride belongs to the first slab whose bound
# its miles do not exceed (miles <= 10 -> 0-10, <= 20 -> 10-20, ...).
# Toll is NOT in the slab: the driver gets slab pay + the map toll.
# Hourly rides stay $50/hour (compute_hourly) — slabs are one-way
# distance rides only. NO slab exists above 400 miles: those rides
# are refused (driver_slab_pay raises) until the owner gives numbers.
# The first 5 slabs are the owner's dictated numbers (note: SUV is
# $160 at BOTH 20-30 and 30-40 — his own numbers, equal is fine, do
# NOT "fix" it). 1-5 miles: Business $80, SUV $80, First $100
# (owner decisions 2026-11-20 ~06:36-06:37 EST, voice call —
# Business $80, SUV $80, First Class $100; the SUV was briefly
# $100 at ~06:36 EST before he corrected it to $80).
# From 40-50 on, every slab is +$20 per class over
# the previous one.
_DRIVER_PAY_SLAB_ANCHORS = (
    (5, 80, 80, 100),
    (10, 80, 90, 110),
    (20, 95, 130, 150),
    (30, 125, 160, 190),
    (40, 140, 160, 200),
)


def _build_driver_pay_slabs():
    slabs = [
        (Decimal(str(upper)),
         {"sedan": Decimal(str(business)),
          "suv": Decimal(str(suv)),
          "first": Decimal(str(first))})
        for upper, business, suv, first in _DRIVER_PAY_SLAB_ANCHORS
    ]
    business, suv, first = 140, 160, 200  # 30-40 slab (the base)
    for upper in range(50, 401, 10):
        business, suv, first = business + 20, suv + 20, first + 20
        slabs.append((Decimal(str(upper)),
                      {"sedan": Decimal(str(business)),
                       "suv": Decimal(str(suv)),
                       "first": Decimal(str(first))}))
    return tuple(slabs)


DRIVER_PAY_SLABS = _build_driver_pay_slabs()
DRIVER_PAY_MAX_MILES = Decimal("400")
NO_DRIVER_SLAB_ABOVE_400 = ("No driver pay rate exists for rides over "
                            "400 miles yet.")


def driver_slab_pay(miles, vehicle_class="sedan") -> Decimal:
    """Flat driver pay for a one-way ride, by distance slab. Decimal.

    vehicle_class: "sedan" (Business Class), "suv" (Business SUV)
    or "first" (First Class). Toll is NOT included — the caller adds
    it on top, same as before. Raises ValueError for an unknown class
    and for rides over 400 miles (no slab exists there; the owner
    has not given numbers — do NOT invent a rate).
    """
    miles = miles_1dp(miles)
    vehicle_class = vehicle_class or "sedan"
    if vehicle_class not in ("sedan", "suv", "first"):
        raise ValueError("vehicle_class must be 'sedan', 'suv' or 'first'")
    if miles < 0:
        raise ValueError("miles cannot be negative")
    for upper, pay in DRIVER_PAY_SLABS:
        if miles <= upper:
            return money(pay[vehicle_class])
    raise ValueError(NO_DRIVER_SLAB_ABOVE_400)


def pricing_mode():
    """Which fare engine is live: "blacklane" (default) or "legacy".

    The Blacklane-style engine (blacklane_pricing.py) is LIVE since
    2026-11-20 (owner: "Live kar do", "Driver aur customer dono
    live kar do"). Set NOEL_PRICING=legacy in the Render environment
    to switch the customer fare computation back to the $9/$10
    formula. Anything else (including an empty value) means the
    Blacklane engine. Read from the environment on every call so
    tests can flip it in-process.
    """
    return ("legacy"
            if os.environ.get("NOEL_PRICING", "blacklane").strip().lower() == "legacy"
            else "blacklane")
# Referral discount (owner decision 2026-11-18, voice call): 5% off
# the total for a NEW customer's first one-way booking made with a
# valid referral code. The referrer gets nothing; the discount comes
# out of Noel's profit only (driver earnings are unchanged).
REFERRAL_DISCOUNT_RATE = Decimal("0.05")
HOURLY_CUSTOMER = Decimal("90")
HOURLY_DRIVER = Decimal("50")
WAITING_RATE_PER_MIN = Decimal("1")

# Up-front NJ return-toll estimate (owner decision 2026-11-16): the
# Port Authority E-ZPass peak rate for the return crossing into New
# York (Holland Tunnel / Lincoln Tunnel / George Washington Bridge),
# verified 2026-11-16. Applied at booking creation to New York ->
# New Jersey trips only; see estimate_return_toll.
NJ_RETURN_TOLL = Decimal("16.79")

AIRPORT_KEYWORDS = ("airport", "jfk", "lga", "ewr", "laguardia", "newark", "liberty")

_NY_STATE_NAMES = ("new york", "ny", "us-ny")
_NJ_STATE_NAMES = ("new jersey", "nj", "us-nj")


def _state_code(state):
    """Normalize a geocoder state value to "NY", "NJ", or None."""
    text = (state or "").strip().lower()
    if text in _NY_STATE_NAMES:
        return "NY"
    if text in _NJ_STATE_NAMES:
        return "NJ"
    return None


def _text_state(text):
    """Best-effort state from an address display string: "NY", "NJ", or None.

    Fallback only, used when the geocoder state is unavailable. Matches
    the full state name or a standalone state abbreviation. "Newark"
    matches neither, and a bare place name with no state yields None —
    the estimate must never be guessed from a city name alone.
    """
    lowered = (text or "").lower()
    if re.search(r"\bnew jersey\b", lowered) or re.search(r"\bnj\b", lowered):
        return "NJ"
    if re.search(r"\bnew york\b", lowered) or re.search(r"\bny\b", lowered):
        return "NY"
    return None


def estimate_return_toll(pickup_state, dropoff_state, pickup_text="", dropoff_text="") -> Decimal:
    """Up-front toll estimate for a one-way ride. Decimal.

    $16.79 when the trip goes from New York to New Jersey (the Port
    Authority return crossing); $0.00 for every other trip, including
    New Jersey -> New York and New Jersey -> New Jersey. Each side
    resolves from the geocoder state field first and falls back to the
    address display text when the state is unavailable, so a geocoding
    failure never blocks the estimate — it only falls back to what the
    customer typed or picked. This is the ONE helper for the estimate:
    booking creation stores its result on the booking, and the
    options-page quote reads the same stored toll, so quote and charge
    always agree exactly.
    """
    pickup_code = _state_code(pickup_state) or _text_state(pickup_text)
    dropoff_code = _state_code(dropoff_state) or _text_state(dropoff_text)
    if pickup_code == "NY" and dropoff_code == "NJ":
        return NJ_RETURN_TOLL
    return Decimal("0.00")


def estimate_upfront_toll(pickup_state, dropoff_state, pickup_text="",
                          dropoff_text="", geometry=None) -> Decimal:
    """Up-front toll estimate for a one-way ride, from the map. Decimal.

    With route geometry: the tolls for every tolled crossing the
    route polyline passes through (see tolls.py), PLUS the $16.79
    return toll when the trip goes New York -> New Jersey. The
    outbound Hudson crossing westbound is free, so geometry adds $0
    for it — the $16.79 is the return leg, with no double-counting.

    Without geometry (OSRM failure / no geometry): the compulsory
    fallback — $16.79 for ANY trip between New York and New Jersey
    in EITHER direction (the Hudson crossings' toll applies whether
    or not the map is connected, per the owner's rule); $0.00 for
    all other trips. State evidence resolves the same way as
    estimate_return_toll: geocoder state first, address text
    fallback.

    This is the ONE helper for the estimate: booking creation stores
    its result on the booking, and the options-page quote reads the
    same stored toll, so quote and charge always agree exactly.
    """
    pickup_code = _state_code(pickup_state) or _text_state(pickup_text)
    dropoff_code = _state_code(dropoff_state) or _text_state(dropoff_text)
    if not geometry:
        if {pickup_code, dropoff_code} == {"NY", "NJ"}:
            return NJ_RETURN_TOLL
        return Decimal("0.00")
    detected, _names = detect_crossing_tolls(geometry)
    total = detected
    if pickup_code == "NY" and dropoff_code == "NJ":
        total += NJ_RETURN_TOLL
    return money(total)


def money(value) -> Decimal:
    """Quantize a value to cents, ROUND_HALF_UP."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def miles_1dp(value) -> Decimal:
    return Decimal(str(value)).quantize(TENTH, rounding=ROUND_HALF_UP)


def class_label(vehicle_class):
    """Customer-facing display name for a class key, or None (hourly)."""
    if vehicle_class is None:
        return None
    return CLASS_LABELS.get(vehicle_class)


def compute_one_way(miles, toll=Decimal("0"), vehicle_class="sedan", referral: bool = False) -> dict:
    """Return fare breakdown for a one-way ride. All values Decimal.

    vehicle_class: "sedan" (Business Class) or "suv" (Business SUV).
    Driver pay is the FLAT slab amount for the ride's miles (see
    DRIVER_PAY_SLABS) + toll — NOT per mile (owner decision
    2026-11-20). Rides over 400 miles raise ValueError: no slab
    exists there yet.
    referral: a NEW customer's first booking with a valid referral
    code gets 5% off the total (fare + toll). Driver earnings are
    unchanged — the discount comes out of Noel's profit only.
    """
    miles = miles_1dp(miles)
    toll = money(toll)
    vehicle_class = vehicle_class or "sedan"
    if vehicle_class not in CLASS_RATES:
        raise ValueError("vehicle_class must be 'sedan' or 'suv'")
    fare = money(CLASS_RATES[vehicle_class] * miles)
    gratuity = Decimal("0.00")
    tax = Decimal("0.00")
    total = money(fare + toll)
    referral_discount = Decimal("0.00")
    if referral:
        referral_discount = money(total * REFERRAL_DISCOUNT_RATE)
        total = money(total - referral_discount)
    driver_earnings = money(driver_slab_pay(miles, vehicle_class) + toll)
    profit = money(total - driver_earnings)
    return {
        "miles": miles,
        "fare": fare,
        "gratuity": gratuity,
        "tax": tax,
        "booking_fee": BOOKING_FEE,
        "toll": toll,
        "total": total,
        "referral_discount": referral_discount,
        "driver_earnings": driver_earnings,
        "profit": profit,
        "vehicle_class": vehicle_class,
    }


def compute_class_totals(miles, toll=Decimal("0"), referral: bool = False) -> dict:
    """Single total per vehicle class, for the options page.

    referral: when True, each class total carries the 5% first-ride
    referral discount (owner decision 2026-11-18) — the totals the
    customer sees are the discounted totals.
    """
    return {
        "sedan": compute_one_way(miles, toll=toll, vehicle_class="sedan",
                                 referral=referral)["total"],
        "suv": compute_one_way(miles, toll=toll, vehicle_class="suv",
                               referral=referral)["total"],
    }


def compute_extra_distance(extra_miles, vehicle_class="sedan") -> dict:
    """Pricing for extra miles driven beyond the booked route.

    One-way rides only: the driver enters the extra miles at
    completion. Uses the SAME formula as the booked fare — added fare
    = extra miles x class rate, no gratuity, no tax; toll unchanged.
    Driver addition = extra miles x driver rate. All values Decimal.
    """
    miles = miles_1dp(extra_miles)
    if miles < 0:
        raise ValueError("extra miles cannot be negative")
    vehicle_class = vehicle_class or "sedan"
    if vehicle_class not in CLASS_RATES:
        raise ValueError("vehicle_class must be 'sedan' or 'suv'")
    fare = money(CLASS_RATES[vehicle_class] * miles)
    gratuity = Decimal("0.00")
    tax = Decimal("0.00")
    total = money(fare)
    driver_addition = money(CLASS_DRIVER_RATES[vehicle_class] * miles)
    return {
        "miles": miles,
        "fare": fare,
        "gratuity": gratuity,
        "tax": tax,
        "total": total,
        "driver_addition": driver_addition,
        "vehicle_class": vehicle_class,
    }


def compute_hourly(hours) -> dict:
    """Return fare breakdown for an hourly ride. No fee, no gratuity, no tax."""
    hours = Decimal(str(hours))
    total = money(HOURLY_CUSTOMER * hours)
    driver_earnings = money(HOURLY_DRIVER * hours)
    return {
        "hours": hours,
        "fare": total,
        "toll": Decimal("0.00"),
        "booking_fee": Decimal("0.00"),
        "subtotal": total,
        "gratuity": Decimal("0.00"),
        "tax": Decimal("0.00"),
        "total": total,
        "driver_earnings": driver_earnings,
        "profit": money(total - driver_earnings),
        "vehicle_class": None,
    }


def is_airport_pickup(pickup_text: str) -> bool:
    text = (pickup_text or "").lower()
    return any(word in text for word in AIRPORT_KEYWORDS)


def free_waiting_minutes(pickup_text: str) -> int:
    return 60 if is_airport_pickup(pickup_text) else 15


def waiting_charge(pickup_text: str, minutes: int) -> Decimal:
    """Waiting charge: $1/min beyond the free allowance."""
    minutes = max(0, int(minutes or 0))
    billable = max(0, minutes - free_waiting_minutes(pickup_text))
    return money(Decimal(billable) * WAITING_RATE_PER_MIN)


def invoice_total(fare_total, waiting: Decimal | int = Decimal("0")) -> Decimal:
    return money(Decimal(str(fare_total)) + Decimal(str(waiting)))


def _pickup_timezone():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("America/New_York")
        except Exception:
            pass
    return timezone.utc


def cancellation_refundable(date_str: str, time_str: str, now=None) -> bool:
    """True if cancelling now is free: more than 1 hour before pickup.

    Pickup datetime is interpreted in America/New_York. `now` may be given
    (aware datetime) for testing; otherwise the current UTC time is used.
    """
    pickup_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    pickup_dt = pickup_naive.replace(tzinfo=_pickup_timezone())
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (pickup_dt - now) > timedelta(hours=1)


def waiting_time_elapsed(date_str: str, time_str: str, pickup_text: str, now=None) -> bool:
    """True once the free waiting time has fully elapsed.

    The driver must wait the full allowance — 60 minutes at airport
    pickups, else 15 — from the pickup datetime (America/New_York)
    before a customer no-show may be marked. `now` may be given (aware
    datetime) for testing; otherwise the current UTC time is used.
    """
    pickup_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    pickup_dt = pickup_naive.replace(tzinfo=_pickup_timezone())
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now >= pickup_dt + timedelta(minutes=free_waiting_minutes(pickup_text))


# Driver cancel lock (owner decision 2026-11-17): once an accepted ride's
# pickup is within this many hours, the driver cannot cancel it normally.
# More than this before pickup, cancelling works as before and the job
# auto re-dispatches. Declining an offer before accepting is untouched,
# and so is the customer's 1-hour cancel/refund rule.
DRIVER_CANCEL_LOCK_HOURS = 2


def driver_cancel_locked(date_str: str, time_str: str, now=None) -> bool:
    """True when a driver may no longer cancel an accepted ride.

    Locked once the pickup datetime (America/New_York) is within
    DRIVER_CANCEL_LOCK_HOURS — including a pickup time already past.
    `now` may be given (aware datetime) for testing; otherwise the
    current UTC time is used.
    """
    pickup_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    pickup_dt = pickup_naive.replace(tzinfo=_pickup_timezone())
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (pickup_dt - now) <= timedelta(hours=DRIVER_CANCEL_LOCK_HOURS)
