"""Pricing for Noel Chauffer — pure functions, Decimal, ROUND_HALF_UP.

Rates are settled by the owner. Do not change them here.
- ONE-WAY: subtotal = $20 booking fee + $7/mile + toll; gratuity = 10% of
  subtotal; total = subtotal + gratuity. A valid referral code subtracts
  exactly $20 from the FINAL total (the fee is not zeroed before gratuity).
  Driver earnings = $4/mile + toll. Owner profit = total - driver earnings.
- HOURLY: total = $90/hour; driver = $50/hour. No booking fee, no gratuity.
- WAITING: 60 free minutes at airport pickups, else 15; then $1/minute.
  No gratuity on waiting. Waiting money goes to owner profit.
- CANCELLATION: free (full refund) if cancelled MORE than 1 hour before the
  pickup datetime (America/New_York); 1 hour or less keeps the full price.
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

BOOKING_FEE = Decimal("20")
PER_MILE_CUSTOMER = Decimal("7")
PER_MILE_DRIVER = Decimal("4")
GRATUITY_RATE = Decimal("0.10")
REFERRAL_DISCOUNT = Decimal("20")
HOURLY_CUSTOMER = Decimal("90")
HOURLY_DRIVER = Decimal("50")
WAITING_RATE_PER_MIN = Decimal("1")

AIRPORT_KEYWORDS = ("airport", "jfk", "lga", "ewr", "laguardia", "newark", "liberty")


def money(value) -> Decimal:
    """Quantize a value to cents, ROUND_HALF_UP."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def miles_1dp(value) -> Decimal:
    return Decimal(str(value)).quantize(TENTH, rounding=ROUND_HALF_UP)


def compute_one_way(miles, toll=Decimal("0"), referral: bool = False) -> dict:
    """Return fare breakdown for a one-way ride. All values Decimal."""
    miles = miles_1dp(miles)
    toll = money(toll)
    subtotal = money(BOOKING_FEE + PER_MILE_CUSTOMER * miles + toll)
    gratuity = money(subtotal * GRATUITY_RATE)
    total = money(subtotal + gratuity)
    if referral:
        total = money(total - REFERRAL_DISCOUNT)
    driver_earnings = money(PER_MILE_DRIVER * miles + toll)
    profit = money(total - driver_earnings)
    return {
        "miles": miles,
        "toll": toll,
        "booking_fee": BOOKING_FEE,
        "subtotal": subtotal,
        "gratuity": gratuity,
        "total": total,
        "driver_earnings": driver_earnings,
        "profit": profit,
    }


def compute_hourly(hours) -> dict:
    """Return fare breakdown for an hourly ride. No fee, no gratuity."""
    hours = Decimal(str(hours))
    total = money(HOURLY_CUSTOMER * hours)
    driver_earnings = money(HOURLY_DRIVER * hours)
    return {
        "hours": hours,
        "toll": Decimal("0.00"),
        "booking_fee": Decimal("0.00"),
        "subtotal": total,
        "gratuity": Decimal("0.00"),
        "total": total,
        "driver_earnings": driver_earnings,
        "profit": money(total - driver_earnings),
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
