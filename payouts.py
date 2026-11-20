"""Driver payout weeks for Noel Chauffer — pure date math.

Settled by the owner (2026-11-16, clarified the same day; due-date
rule CHANGED by the owner 2026-11-20, voice call): a week's earnings
are paid in the FOLLOWING week. Each week's accounting is separate,
and the money comes one week after the week starts.

Trips are tallied in 7-day weeks anchored at 2026-11-16, and each
week's payout comes due 7 days after that week starts:

  week 0 = Nov 16-22, 2026, due Nov 23, 2026
  week 1 = Nov 23-29, 2026, due Nov 30, 2026
  week 2 = Nov 30-Dec 6, 2026, due Dec 7, 2026
  ...

So the due date for a week is its start + 7 days: due dates fall
7 days apart (weekly), and every trip is paid 1-7 days after it
happens — the lag never grows.

A completed, non-refunded trip belongs to the week containing its
completion date (the America/New_York calendar date on which the trip
was completed). The owner marks a week paid in the owner dashboard;
that is tracking only — no money moves in this app (test mode).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

ANCHOR = date(2026, 11, 16)
WEEK_DAYS = 7
# Owner decision 2026-11-20 (CHANGED from 14): a week's payout is due
# 7 days after the week starts — paid in the following week.
PAYOUT_INTERVAL_DAYS = 7


def _business_timezone():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("America/New_York")
        except Exception:
            pass
    return timezone.utc


def week_for(d: date) -> dict:
    """Return the payout week containing date `d`.

    Result: {"index": int, "start": date, "end": date, "due_date": date}
    where the week runs 7 days from `start`, and `due_date` is the
    week start + 7 days, so due dates fall 7 days apart and every
    trip is paid 1-7 days after it happens. Dates before the anchor
    fall in negative-index weeks on the same 7-day grid.
    """
    delta = (d - ANCHOR).days
    index = delta // WEEK_DAYS
    start = ANCHOR + timedelta(days=WEEK_DAYS * index)
    end = start + timedelta(days=WEEK_DAYS - 1)
    due_date = start + timedelta(days=PAYOUT_INTERVAL_DAYS)
    return {"index": index, "start": start, "end": end, "due_date": due_date}


def week_bounds(index: int) -> dict:
    """Return the start/end/due dates for payout week `index`."""
    start = ANCHOR + timedelta(days=WEEK_DAYS * index)
    end = start + timedelta(days=WEEK_DAYS - 1)
    due_date = start + timedelta(days=PAYOUT_INTERVAL_DAYS)
    return {"index": index, "start": start, "end": end, "due_date": due_date}


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
