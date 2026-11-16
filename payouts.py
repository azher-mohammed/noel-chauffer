"""Driver payout windows for Noel Chauffer — pure date math.

Settled by the owner (2026-11-16): drivers are paid every 14 days.
Trips are tallied in global 14-day windows anchored at 2026-11-16:

  window 0 = Nov 16-29, 2026
  window 1 = Nov 30-Dec 13, 2026
  window 2 = Dec 14-27, 2026
  ...

A completed, non-refunded trip belongs to the window containing its
completion date (the America/New_York calendar date on which the trip
was completed). The payout for a window is due on the window's last
day. The owner marks a window paid in the owner dashboard; that is
tracking only — no money moves in this app (test mode).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

ANCHOR = date(2026, 11, 16)
WINDOW_DAYS = 14


def _business_timezone():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("America/New_York")
        except Exception:
            pass
    return timezone.utc


def window_for(d: date) -> dict:
    """Return the payout window containing date `d`.

    Result: {"index": int, "start": date, "end": date, "due_date": date}
    where due_date == end (the window's last day). Dates before the
    anchor fall in negative-index windows on the same 14-day grid.
    """
    delta = (d - ANCHOR).days
    index = delta // WINDOW_DAYS
    start = ANCHOR + timedelta(days=WINDOW_DAYS * index)
    end = start + timedelta(days=WINDOW_DAYS - 1)
    return {"index": index, "start": start, "end": end, "due_date": end}


def window_bounds(index: int) -> dict:
    """Return the start/end/due dates for payout window `index`."""
    start = ANCHOR + timedelta(days=WINDOW_DAYS * index)
    end = start + timedelta(days=WINDOW_DAYS - 1)
    return {"index": index, "start": start, "end": end, "due_date": end}


def completion_date(completed_at, created_at=None) -> date:
    """Business date (America/New_York) on which a trip was completed.

    `completed_at` is the timestamp recorded when the driver completed
    the trip. `created_at` is the fallback for completed trips recorded
    before completion timestamps existed. Naive timestamps are read as
    UTC, matching how the app stores them.
    """
    dt = completed_at if completed_at is not None else created_at
    if dt is None:
        raise ValueError("no completion or creation timestamp to date the trip by")
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_business_timezone()).date()
    return dt  # already a date
