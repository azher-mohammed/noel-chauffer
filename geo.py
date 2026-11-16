"""Geocoding + routing for Noel Chauffer.

Public no-key endpoints only: Nominatim for geocoding, OSRM demo server for
driving routes. Fallback: haversine distance * 1.3. Never raises to the
caller on geo failure — always returns a miles value via fallback.
"""

from __future__ import annotations

import json
import logging
import math
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

USER_AGENT = "NoelChauffer/1.0"
TIMEOUT = 10
METERS_PER_MILE = 1609.344
FALLBACK_MILES = 10.0  # used only when geocoding fails outright (no coords)

_geocode_cache: dict = {}
_route_cache: dict = {}
_CACHE_LIMIT = 500


def _http_get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode(address: str):
    """Return (lat, lng) floats, or None on any failure. Cached."""
    key = (address or "").strip().lower()
    if not key:
        return None
    if key in _geocode_cache:
        return _geocode_cache[key]
    result = None
    try:
        url = (
            "https://nominatim.openstreetmap.org/search?format=json&limit=1&q="
            + urllib.parse.quote(address)
        )
        data = _http_get_json(url)
        if data:
            result = (float(data[0]["lat"]), float(data[0]["lon"]))
    except Exception as exc:  # never raise: caller falls back
        log.warning("geocode failed for %r: %s", address, exc)
    if len(_geocode_cache) < _CACHE_LIMIT:
        _geocode_cache[key] = result
    return result


def haversine_miles(lat1, lng1, lat2, lng2) -> float:
    r = 3958.8  # Earth radius in miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def route_miles(lat1, lng1, lat2, lng2) -> float:
    """Driving miles via OSRM; falls back to haversine * 1.3. Never raises."""
    key = (round(lat1, 5), round(lng1, 5), round(lat2, 5), round(lng2, 5))
    if key in _route_cache:
        return _route_cache[key]
    miles = None
    try:
        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{lng1},{lat1};{lng2},{lat2}?overview=false"
        )
        data = _http_get_json(url)
        routes = data.get("routes") or []
        if routes:
            miles = routes[0]["distance"] / METERS_PER_MILE
    except Exception as exc:
        log.warning("OSRM route failed: %s", exc)
    if miles is None:
        miles = haversine_miles(lat1, lng1, lat2, lng2) * 1.3
    miles = round(float(miles), 1)
    if len(_route_cache) < _CACHE_LIMIT:
        _route_cache[key] = miles
    return miles


def distance_miles(pickup: str, dropoff: str):
    """Return (miles, pickup_coords, dropoff_coords). Never raises.

    Coords are (lat, lng) tuples or None. If either address cannot be
    geocoded, miles falls back to FALLBACK_MILES.
    """
    try:
        pickup_coords = geocode(pickup)
        dropoff_coords = geocode(dropoff)
        if pickup_coords and dropoff_coords:
            miles = route_miles(
                pickup_coords[0], pickup_coords[1], dropoff_coords[0], dropoff_coords[1]
            )
            return miles, pickup_coords, dropoff_coords
        return FALLBACK_MILES, pickup_coords, dropoff_coords
    except Exception as exc:  # absolute safety net
        log.warning("distance_miles failed: %s", exc)
        return FALLBACK_MILES, None, None
