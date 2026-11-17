"""Pricing for Noel Chauffer — pure functions, Decimal, ROUND_HALF_UP.

Rates are settled by the owner. Do not change them here.

ONE-WAY (decided 2026-11-16; SUPERSEDES the old $20 booking fee +
$7/mile formula entirely): TWO vehicle classes, each with its own
per-mile rate and driver rate. NO booking fee.
- Business Class (sedan): customer $11/mile, driver $4/mile.
- Business SUV (SUV): customer $12/mile, driver $7/mile.
- fare = miles x class rate.
- gratuity = 10% of the fare (before toll and before tax), charged to
  the customer, goes to the OWNER's profit (never the driver).
- NYC TAX = 8.875% of the fare, added to the CUSTOMER total, for BOTH
  classes. Verified: NYC311/TLC confirm 8.875% on car-service /
  limousine / black-car passenger fares, and Blacklane's own quote
  applied exactly 8.875% to the base fare. Tax is pass-through: it is
  NOT driver pay and NOT owner profit. Tolls are NOT taxed.
- customer total = fare + gratuity + tax + toll.
- driver earnings = miles x driver rate + toll.
- owner profit = total - driver earnings - tax.
- Referral codes are accepted but give a $0 discount for now: the old
  benefit (waiving the $20 booking fee) no longer applies since there
  is no fee. A new referral benefit is TBD pending the owner's
  decision — do not invent one.
- HOURLY: total = $90/hour; driver = $50/hour. No fee, no gratuity,
  no tax. Whether hourly rides get tax is TBD pending the owner's
  decision; do not add tax to hourly.
- WAITING: 60 free minutes at airport pickups, else 15; then $1/minute.
  No gratuity on waiting. Waiting money goes to owner profit.
- CANCELLATION: free (full refund) if cancelled MORE than 1 hour before
  the pickup datetime (America/New_York); 1 hour or less keeps the full
  price.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

CENT = Decimal("0.01")
TENTH = Decimal("0.1")

# One-way rates, per vehicle class. Internal keys stay "sedan"/"suv";
# customer-facing display names are in CLASS_LABELS.
SEDAN_RATE = Decimal("11")
SUV_RATE = Decimal("12")
DRIVER_SEDAN = Decimal("4")
DRIVER_SUV = Decimal("7")
CLASS_RATES = {"sedan": SEDAN_RATE, "suv": SUV_RATE}
CLASS_DRIVER_RATES = {"sedan": DRIVER_SEDAN, "suv": DRIVER_SUV}
CLASS_LABELS = {"sedan": "Business Class", "suv": "Business SUV"}
TAX_RATE = Decimal("0.08875")
BOOKING_FEE = Decimal("0")
GRATUITY_RATE = Decimal("0.10")
# Referral discount is $0 for now — TBD pending the owner's decision.
REFERRAL_DISCOUNT = Decimal("0")
HOURLY_CUSTOMER = Decimal("90")
HOURLY_DRIVER = Decimal("50")
WAITING_RATE_PER_MIN = Decimal("1")

AIRPORT_KEYWORDS = ("airport", "jfk", "lga", "ewr", "laguardia", "newark", "liberty")


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
    referral is accepted but gives a $0 discount for now (TBD).
    """
    miles = miles_1dp(miles)
    toll = money(toll)
    vehicle_class = vehicle_class or "sedan"
    if vehicle_class not in CLASS_RATES:
        raise ValueError("vehicle_class must be 'sedan' or 'suv'")
    fare = money(CLASS_RATES[vehicle_class] * miles)
    gratuity = money(fare * GRATUITY_RATE)
    tax = money(fare * TAX_RATE)
    total = money(fare + gratuity + tax + toll)
    if referral:
        total = money(total - REFERRAL_DISCOUNT)
    driver_earnings = money(CLASS_DRIVER_RATES[vehicle_class] * miles + toll)
    profit = money(total - driver_earnings - tax)
    return {
        "miles": miles,
        "fare": fare,
        "gratuity": gratuity,
        "tax": tax,
        "booking_fee": BOOKING_FEE,
        "toll": toll,
        "total": total,
        "driver_earnings": driver_earnings,
        "profit": profit,
        "vehicle_class": vehicle_class,
    }


def compute_class_totals(miles, toll=Decimal("0")) -> dict:
    """Single total per vehicle class, for the options page."""
    return {
        "sedan": compute_one_way(miles, toll=toll, vehicle_class="sedan")["total"],
        "suv": compute_one_way(miles, toll=toll, vehicle_class="suv")["total"],
    }


def compute_extra_distance(extra_miles, vehicle_class="sedan") -> dict:
    """Pricing for extra miles driven beyond the booked route.

    One-way rides only: the driver enters the extra miles at
    completion. Uses the SAME formula as the booked fare — added fare
    = extra miles x class rate, gratuity 10% of the added fare, NYC
    tax 8.875% of the added fare; toll unchanged. Driver addition =
    extra miles x driver rate. All values Decimal.
    """
    miles = miles_1dp(extra_miles)
    if miles < 0:
        raise ValueError("extra miles cannot be negative")
    vehicle_class = vehicle_class or "sedan"
    if vehicle_class not in CLASS_RATES:
        raise ValueError("vehicle_class must be 'sedan' or 'suv'")
    fare = money(CLASS_RATES[vehicle_class] * miles)
    gratuity = money(fare * GRATUITY_RATE)
    tax = money(fare * TAX_RATE)
    total = money(fare + gratuity + tax)
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
    """Waiting charge: $1/min beyond the free allowance. No gratuity."""
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
