"""Geocoding + routing + USA place search for Noel Chauffer.

Public no-key endpoints only: Nominatim for geocoding and address
suggestions, OSRM demo server for driving routes. Fallback: haversine
distance * 1.3. Never raises to the caller on geo failure — always
returns a miles value via fallback, or an empty suggestion list.
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
_search_cache: dict = {}
_CACHE_LIMIT = 500

# Address-detail keys passed through to autocomplete suggestions.
_ADDRESS_KEYS = (
    "house_number", "road", "neighbourhood", "suburb", "city", "town",
    "village", "county", "state", "postcode", "country", "country_code",
)


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


def _parse_place(item):
    """Normalize one Nominatim item to (result dict, class, type) or None.

    The result dict is the public shape: display_name, lat, lon,
    address. Class/type are internal only (airport/terminal detection)
    and are never included in API responses.
    """
    if not isinstance(item, dict):
        return None
    try:
        lat = float(item["lat"])
        lon = float(item["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    display_name = item.get("display_name")
    if not display_name:
        return None
    raw_address = item.get("address") or {}
    address = {}
    if isinstance(raw_address, dict):
        for k in _ADDRESS_KEYS:
            if raw_address.get(k):
                address[k] = raw_address[k]
    return (
        {
            "display_name": display_name,
            "lat": lat,
            "lon": lon,
            "address": address,
            # True only for the airport itself (aeroway/aerodrome), so
            # the booking form can tell an airport suggestion apart
            # from a terminal or street address.
            "airport": item.get("class") == "aeroway"
            and item.get("type") == "aerodrome",
        },
        item.get("class"),
        item.get("type"),
    )


# Terminal lookup: when a search result is an airport (aeroway/aerodrome),
# the airport's terminals are fetched with viewbox-bounded Nominatim
# searches around the airport and merged into the suggestions. Every
# terminal entry comes from live OpenStreetMap/Nominatim data — a terminal
# is never invented. The same mechanism runs for every US airport;
# airports whose terminals OSM does not map simply show fewer entries.
# The three queries are needed because Nominatim ranks generic terms by
# importance: a bare "Terminal" search alone misses arrivals/departures
# roads at some airports (e.g. LaGuardia) while the dedicated "Arrivals"
# and "Departures" searches find them. Results are cached per airport,
# so a first uncached airport query makes 4 upstream calls (base + 3)
# and repeat queries make none. Nominatim's usage policy asks for at
# most 1 request/second; the caches keep normal typing well under that.
_TERMINAL_QUERIES = ("Terminal", "Arrivals", "Departures")
_TERMINAL_VIEWBOX_DEG = 0.06
_TERMINAL_MAX_KM = 6.0
_TERMINAL_LIMIT = 25
_MERGED_CAP = 12
_TERMINAL_CLASSES = ("aeroway", "highway", "building")
_TERMINAL_DROP_TYPES = ("bus_stop", "taxi", "tower", "construction")
_terminal_cache: dict = {}


def _is_terminal_candidate(result, cls, typ, airport_lat, airport_lon):
    """True if a bounded-search hit is a real terminal feature.

    The first name component must mention "terminal" (so freight
    terminals and unrelated roads near an airport are kept only when
    they are actually named for a terminal), parking areas are
    excluded, and only terminal buildings plus the arrivals /
    departures roadways count. Distance is measured from the airport
    centre so a neighbouring airport's or freight terminal's features
    do not leak in.
    """
    name = (result["display_name"] or "").split(",")[0].strip().lower()
    if "terminal" not in name:
        return False
    if "parking" in name:
        return False
    if cls not in _TERMINAL_CLASSES:
        return False
    if typ in _TERMINAL_DROP_TYPES:
        return False
    distance_km = haversine_miles(
        airport_lat, airport_lon, result["lat"], result["lon"]
    ) * 1.609344
    return distance_km <= _TERMINAL_MAX_KM


def _airport_terminals(airport_lat, airport_lon):
    """Terminals around an airport, from live Nominatim data. Never raises.

    Returns result dicts sorted by terminal name, deduplicated by name
    (one entry per terminal road/building). Any upstream failure yields
    an empty list so the caller falls back to the base search results.
    """
    key = (round(airport_lat, 3), round(airport_lon, 3))
    if key in _terminal_cache:
        return [
            dict(item, address=dict(item["address"]))
            for item in _terminal_cache[key]
        ]
    found = {}
    try:
        left = airport_lon - _TERMINAL_VIEWBOX_DEG
        right = airport_lon + _TERMINAL_VIEWBOX_DEG
        bottom = airport_lat - _TERMINAL_VIEWBOX_DEG
        top = airport_lat + _TERMINAL_VIEWBOX_DEG
        box = "&viewbox=%f,%f,%f,%f&bounded=1" % (left, top, right, bottom)
        for term in _TERMINAL_QUERIES:
            url = (
                "https://nominatim.openstreetmap.org/search?format=json"
                "&addressdetails=1&countrycodes=us&limit=" + str(_TERMINAL_LIMIT)
                + "&q=" + urllib.parse.quote(term) + box
            )
            data = _http_get_json(url)
            if not isinstance(data, list):
                continue
            for raw in data:
                parsed = _parse_place(raw)
                if not parsed:
                    continue
                result, cls, typ = parsed
                if not _is_terminal_candidate(
                    result, cls, typ, airport_lat, airport_lon
                ):
                    continue
                name_key = result["display_name"].split(",")[0].strip().lower()
                if name_key not in found:
                    found[name_key] = result
    except Exception as exc:
        log.warning(
            "terminal lookup failed near %s,%s: %s", airport_lat, airport_lon, exc
        )
        return []
    terminals = sorted(
        found.values(),
        key=lambda item: item["display_name"].split(",")[0].strip().lower(),
    )
    if len(_terminal_cache) < _CACHE_LIMIT:
        _terminal_cache[key] = terminals
    return terminals


def search_places(query: str, limit: int = 5):
    """USA-only address suggestions for booking-form autocomplete.

    Returns a list of {display_name, lat, lon, address} dicts, or [] on
    any failure. Never raises. Uses Nominatim with countrycodes=us and
    addressdetails=1; no API key. Address text + coordinates only — no
    fare, miles, or pricing data of any kind.

    When a result is an airport, the airport's terminals — including
    arrivals and departures entries where OpenStreetMap maps them —
    are merged in directly below the airport, from live Nominatim data.
    """
    q = (query or "").strip()
    if not q:
        return []
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(10, limit))
    key = (q.lower(), limit)
    if key in _search_cache:
        return [dict(item, address=dict(item["address"])) for item in _search_cache[key]]
    results = []
    airport = None
    try:
        url = (
            "https://nominatim.openstreetmap.org/search?format=json"
            "&addressdetails=1&countrycodes=us&limit=" + str(limit)
            + "&q=" + urllib.parse.quote(q)
        )
        data = _http_get_json(url)
        if isinstance(data, list):
            for raw in data:
                parsed = _parse_place(raw)
                if not parsed:
                    continue
                result, cls, typ = parsed
                results.append(result)
                if airport is None and cls == "aeroway" and typ == "aerodrome":
                    airport = result
    except Exception as exc:  # never raise: autocomplete degrades to plain text
        log.warning("place search failed for %r: %s", q, exc)
        return []
    if airport is not None:
        terminals = _airport_terminals(airport["lat"], airport["lon"])
        if terminals:
            seen = {airport["display_name"]}
            merged = [airport]
            for terminal in terminals:
                if terminal["display_name"] not in seen:
                    seen.add(terminal["display_name"])
                    merged.append(terminal)
            for result in results:
                if result["display_name"] not in seen:
                    seen.add(result["display_name"])
                    merged.append(result)
            results = merged[:_MERGED_CAP]
    if len(_search_cache) < _CACHE_LIMIT:
        _search_cache[key] = results
    return results


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
