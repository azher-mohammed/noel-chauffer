"""Geocoding + routing + USA place search for Noel Chauffer.

Public no-key endpoints only: Nominatim for geocoding and address
suggestions, OSRM demo server for driving routes. When an address
cannot be resolved to coordinates, distance_miles returns miles=None
— the fare is NEVER computed from an invented distance (there is no
default-miles fallback: a booking with an unresolvable address is
rejected with a clear error instead of being priced on a guess).
Route fallback: haversine distance * 1.3, used only when the routing
service itself fails after coordinates are known. Suggestions return
an empty list on failure. Nothing here raises to the caller on geo
failure.
"""

from __future__ import annotations

import base64
import http.client
import json
import logging
import math
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError

log = logging.getLogger(__name__)

USER_AGENT = "NoelChauffer/1.0"
TIMEOUT = 10
METERS_PER_MILE = 1609.344

# Words stripped on the single retry when a geocode query returns no
# result: typed airport-terminal phrasing such as "JFK Terminal 1
# Arrivals" matches nothing in Nominatim, while "JFK Terminal 1"
# resolves to the terminal. Only whole-word matches are stripped, and
# only when the stripped query is still non-empty. The retry runs
# only on an empty result — never on a request error — and never
# replaces a result the original query already returned.
_RETRY_STRIP_WORDS = ("arrivals", "departures")

_geocode_cache: dict = {}
_geocode_address_cache: dict = {}
# Route cache: key -> (miles, geometry). Geometry is a list of
# (lat, lng) pairs from the same OSRM call, or None when the route
# came from the haversine fallback. Keeping both in one entry means
# clearing _route_cache clears geometry too (tests rely on this).
_route_cache: dict = {}
_search_cache: dict = {}
# Snapshot geocode index: snapshot query (lowercased) -> ((lat, lng),
# address details) from the first result of that query's snapshot
# entry. Built by load_places_snapshot() from the same committed
# Nominatim data that seeds the autocomplete cache, so the most-typed
# places resolve with NO network at all (see snapshot_coords).
_SNAPSHOT_GEOCODE: dict = {}
_CACHE_LIMIT = 500

# Address-detail keys passed through to autocomplete suggestions.
_ADDRESS_KEYS = (
    "house_number", "road", "neighbourhood", "suburb", "city", "town",
    "village", "county", "state", "postcode", "country", "country_code",
)


_tls = threading.local()


def _proxy_for(host: str):
    """Egress proxy for a host, or None when direct is right.

    Mirrors what urllib does with the environment: HTTPS_PROXY (or
    https_proxy) wins, no_proxy bypasses. The proxy URL may carry
    credentials, which are sent as a Proxy-Authorization header (the
    same thing urllib/curl do with these variables). Returns
    (proxy_host, proxy_port, auth_header_or_None). Production (Render)
    sets no proxy variables, so this is a no-op there.
    """
    proxies = urllib.request.getproxies()
    proxy_url = proxies.get("https")
    if not proxy_url:
        return None
    if urllib.request.proxy_bypass(host):
        return None
    parsed = urllib.parse.urlparse(proxy_url)
    if not parsed.hostname:
        return None
    auth = None
    if parsed.username:
        creds = urllib.parse.unquote(parsed.username)
        if parsed.password:
            creds += ":" + urllib.parse.unquote(parsed.password)
        auth = "Basic " + base64.b64encode(creds.encode("utf-8")).decode("ascii")
    return (parsed.hostname, parsed.port or 3128, auth)


def _connection_for(host: str):
    """One reused HTTPS connection per thread per host (keep-alive).

    Each thread keeps its own connections, so no lock is needed and the
    sync and threaded gunicorn workers are both safe. A connection is
    dropped (and recreated on the next call) when a request on it fails.
    When an egress proxy is configured (this dev VM), the connection
    goes through it with a CONNECT tunnel; direct otherwise.
    """
    conns = getattr(_tls, "connections", None)
    if conns is None:
        conns = _tls.connections = {}
    conn = conns.get(host)
    if conn is None:
        proxy = _proxy_for(host)
        if proxy is not None:
            proxy_host, proxy_port, auth = proxy
            # HTTPSConnection to the proxy: connect() opens the CONNECT
            # tunnel to the target host, then wraps the socket in TLS
            # (SNI = the tunnel host). A plain HTTPConnection here
            # would send the request unencrypted down the tunnel.
            conn = http.client.HTTPSConnection(
                proxy_host, proxy_port, timeout=TIMEOUT
            )
            headers = {"Proxy-Authorization": auth} if auth else None
            conn.set_tunnel(host, 443, headers=headers)
        else:
            conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
        conns[host] = conn
    return conn


def _drop_connection(host: str):
    conns = getattr(_tls, "connections", None)
    if conns:
        conns.pop(host, None)


def _http_get_json(url: str):
    """GET a URL and parse its JSON body, reusing a keep-alive connection.

    Same contract as the old urllib version: the custom User-Agent, the
    10s timeout, and raising on any failure (HTTP errors included) so
    callers keep their fail-soft behaviour. A stale server-closed
    connection raises a connection error, which is retried once on a
    fresh connection; a real HTTP error (e.g. Nominatim 403) is NOT
    retried. This removes one TLS handshake (~0.2–0.5s) from every
    Nominatim / OSRM / Photon call.
    """
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc
    path = parsed.path or "/"
    if parsed.params:  # urlparse splits ';' coords (OSRM routes) into params
        path += ";" + parsed.params
    if parsed.query:
        path += "?" + parsed.query
    for attempt in (0, 1):
        conn = _connection_for(host)
        try:
            # Origin-form path with an explicit Host header for the
            # TARGET host. (putrequest would otherwise take Host from
            # the proxy host on a tunneled connection — OSRM rejects
            # that with 400 — and an absolute-form target makes
            # Nominatim drop the connection.)
            conn.putrequest("GET", path, skip_host=True)
            conn.putheader("Host", host)
            conn.putheader("User-Agent", USER_AGENT)
            conn.endheaders()
            resp = conn.getresponse()
            body = resp.read()
        except (http.client.HTTPException, OSError) as exc:
            # Stale keep-alive connection the server already closed:
            # drop it and retry once on a fresh one.
            _drop_connection(host)
            if attempt == 0:
                continue
            raise
        if resp.status != 200:
            raise HTTPError(url, resp.status, resp.reason, resp.getheaders(), None)
        return json.loads(body.decode("utf-8"))
    raise RuntimeError("unreachable")  # pragma: no cover


# --------------------------------------------------------------------------
# Photon fallback (Komoot, free, no key): used ONLY when a Nominatim
# request itself fails (network error, 403/429 block). A Nominatim
# answer of "no match" (valid empty list) is genuine and never falls
# back. Photon results are normalized to Nominatim-shaped items and
# flow through the same parsing, so the public result shape is
# unchanged. Airports rank first and duplicate names collapse, so a
# "JFK" fallback still shows the airport before JFK Expressway.
# --------------------------------------------------------------------------

_PHOTON_URL = "https://photon.komoot.io/api/"


def _photon_items(query: str, limit: int = 5):
    """Photon search results as Nominatim-shaped items, or [].

    Raises on any request failure. Never invents data: only live
    Photon features, with the airport (aeroway/aerodrome) first.
    """
    url = (
        _PHOTON_URL + "?q=" + urllib.parse.quote(query)
        + "&limit=" + str(max(1, min(10, int(limit))))
    )
    data = _http_get_json(url)
    features = data.get("features") if isinstance(data, dict) else None
    if not features:
        return []
    items = []
    for feature in features:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if len(coords) != 2:
            continue
        name = props.get("name")
        if not name:
            continue
        address = {}
        if props.get("housenumber"):
            address["house_number"] = str(props["housenumber"])
        road = props.get("street")
        if road:
            if props.get("housenumber"):
                road = str(props["housenumber"]) + " " + road
            address["road"] = road
        if props.get("city"):
            address["city"] = props["city"]
        if props.get("state"):
            address["state"] = props["state"]
        if props.get("postcode"):
            address["postcode"] = str(props["postcode"])
        if props.get("country"):
            address["country"] = props["country"]
        if props.get("countrycode"):
            address["country_code"] = str(props["countrycode"]).lower()
        display_parts = [name]
        for key in ("road", "city", "state", "postcode", "country"):
            if address.get(key) and address[key] not in display_parts:
                display_parts.append(address[key])
        items.append({
            "display_name": ", ".join(display_parts),
            "lat": str(coords[1]),
            "lon": str(coords[0]),
            "class": props.get("osm_key"),
            "type": props.get("osm_value"),
            "address": address,
        })
    seen = set()
    deduped = []
    for item in items:
        first = item["display_name"].split(",")[0].strip().lower()
        if first in seen:
            continue
        seen.add(first)
        deduped.append(item)
    deduped.sort(key=lambda it: (
        0 if (it.get("class") == "aeroway" and it.get("type") == "aerodrome") else 1
    ))
    return deduped


def _geocode_query(address: str):
    """One USA-only Nominatim lookup.

    Returns (coords, address_details, errored): coords is a (lat, lng)
    tuple or None when the query matched nothing; errored is True only
    when the request itself failed. Never raises.
    """
    try:
        url = (
            "https://nominatim.openstreetmap.org/search?format=json&limit=1"
            "&addressdetails=1&countrycodes=us&q="
            + urllib.parse.quote(address)
        )
        data = _http_get_json(url)
        if data:
            coords = (float(data[0]["lat"]), float(data[0]["lon"]))
            raw_address = data[0].get("address")
            details = raw_address if isinstance(raw_address, dict) else None
            return coords, details, False
        return None, None, False
    except Exception as exc:  # Nominatim request failed: Photon fallback
        log.warning("geocode Nominatim failed for %r, trying Photon: %s",
                    address, exc)
        try:
            items = _photon_items(address, 1)
        except Exception as exc2:  # never raise: caller handles the miss
            log.warning("geocode Photon failed for %r: %s", address, exc2)
            return None, None, True
        if not items:
            return None, None, False
        item = items[0]
        try:
            coords = (float(item["lat"]), float(item["lon"]))
        except (KeyError, TypeError, ValueError):
            return None, None, True
        return coords, item.get("address"), False


def _strip_retry_words(address: str):
    """Query with standalone arrivals/departures words removed, or None.

    Returns None when nothing was stripped or nothing is left, so the
    caller only retries with a genuinely different, non-empty query.
    """
    words = re.split(r"\s+", (address or "").strip())
    kept = [w for w in words if w.strip(",.").lower() not in _RETRY_STRIP_WORDS]
    if len(kept) == len(words):
        return None
    stripped = " ".join(kept).strip(" ,")
    return stripped or None


def geocode(address: str):
    """Return (lat, lng) floats, or None when the address cannot be resolved.

    Cached on success only: failures and empty results are NEVER
    cached, so a transient outage cannot poison the process cache and
    keep mispricing or rejecting that address until a restart.

    The response's address details are cached alongside the
    coordinates (see geocode_state): the booking flow reads the US
    state from them without a second upstream request.
    """
    key = (address or "").strip().lower()
    if not key:
        return None
    if key in _geocode_cache:
        return _geocode_cache[key]
    result, address_details, errored = _geocode_query(address)
    if result is None and not errored:
        stripped = _strip_retry_words(address)
        if stripped is not None and stripped.strip().lower() != key:
            result, address_details, _errored = _geocode_query(stripped)
    if result is not None:
        if len(_geocode_cache) < _CACHE_LIMIT:
            _geocode_cache[key] = result
        if len(_geocode_address_cache) < _CACHE_LIMIT:
            _geocode_address_cache[key] = address_details
    return result


def geocode_state(address: str):
    """Return the US state string for an address, or None.

    Cache-only on purpose: it reads the address details stored by
    geocode() and NEVER makes an upstream request itself. The booking
    flow geocodes each address it has no coordinates for
    (distance_miles), so the cache is warm exactly when the state is
    needed for a geocoded address; when the customer picked a
    suggestion, its coordinates arrive with the booking, no geocode
    runs, and the cache stays cold — callers then fall back to
    matching the address display text. Returns None when the address
    was never geocoded or its lookup failed. Never raises.
    """
    key = (address or "").strip().lower()
    if not key:
        return None
    try:
        details = _geocode_address_cache.get(key)
    except Exception:
        return None
    if not isinstance(details, dict):
        return None
    state = details.get("state")
    if state:
        return str(state)
    iso = details.get("ISO3166-2-lvl4")
    if iso:
        return str(iso)
    return None


def geocode_address(address: str):
    """Return the cached geocoder address-details dict for an address, or None.

    Cache-only on purpose (same contract as geocode_state): it reads
    the address details stored by geocode() and NEVER makes an
    upstream request itself. The Blacklane pricing engine reads the
    state/county/city from it to apply the fee rules; when the cache
    is cold (picked-suggestion coordinates, or a failed lookup) the
    caller falls back to matching the address display text. Returns
    a copy so callers cannot mutate the cache. Never raises.
    """
    key = (address or "").strip().lower()
    if not key:
        return None
    try:
        details = _geocode_address_cache.get(key)
    except Exception:
        return None
    if not isinstance(details, dict):
        return None
    return dict(details)


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
        if not isinstance(data, list):
            data = []
    except Exception as exc:
        # Nominatim request failed (not "no match" — that is a valid
        # empty list above): fall back to Photon, same result shape.
        log.warning("place search Nominatim failed for %r, trying Photon: %s",
                    q, exc)
        try:
            data = _photon_items(q, limit)
        except Exception as exc2:
            # never raise: autocomplete degrades to plain text
            log.warning("place search Photon failed for %r: %s", q, exc2)
            return []
    for raw in data:
        parsed = _parse_place(raw)
        if not parsed:
            continue
        result, cls, typ = parsed
        results.append(result)
        if airport is None and cls == "aeroway" and typ == "aerodrome":
            airport = result
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


# --------------------------------------------------------------------------
# Popular-places warm cache.
#
# Why a committed snapshot: the live Render service's Nominatim calls
# currently return NOTHING (every /api/places/search returns an empty
# list — verified 2026-11-18; direct Nominatim calls from elsewhere
# work fine, so the shared Render egress IP is being throttled or
# blocked). A background thread that seeds from live Nominatim alone
# would therefore seed nothing. The snapshot is real Nominatim data —
# the exact search_places output for these queries, captured with
# scripts/generate_places_snapshot.py — frozen in
# geo_places_snapshot.json, so the most-typed queries answer instantly
# with zero upstream calls. Nothing here is invented: airports and
# landmarks do not move. Regenerate after any terminal changes with:
#   python scripts/generate_places_snapshot.py
# A background refresh (start_popular_places_refresh, production only)
# re-fetches the same queries from live data when the upstream answers
# and replaces an entry only when the live result is non-empty, so a
# failed refresh never clobbers the snapshot values.
# --------------------------------------------------------------------------

_POPULAR_SEARCH_QUERIES = (
    "JFK", "JFK Terminal 1", "JFK Terminal 4", "JFK Terminal 5",
    "JFK Terminal 8", "LaGuardia", "LGA", "LaGuardia Terminal B",
    "Newark Airport", "EWR", "Times Square", "Penn Station",
    "Grand Central", "Empire State Building", "Central Park",
    "Wall Street", "Brooklyn Bridge", "Grand Central Terminal",
    "Port Authority Bus Terminal",
)
_SNAPSHOT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "geo_places_snapshot.json"
)
_REFRESH_GAP_SECONDS = 1.1
_refresh_started = False
_SNAPSHOT_LOADED = False


def _seed_snapshot_geocode(query, results):
    """Seed _SNAPSHOT_GEOCODE for one query from its first result.

    The first result is the place itself for every seeded query
    (the airport for "jfk", Terminal 1 for "jfk terminal 1", Times
    Square for "times square"). No network, never raises.
    """
    qkey = (query or "").strip().lower()
    if not qkey or not isinstance(results, list) or not results:
        return
    first = results[0] if isinstance(results[0], dict) else None
    if first is None:
        return
    try:
        lat = float(first["lat"])
        lon = float(first["lon"])
    except (KeyError, TypeError, ValueError):
        return
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return
    _SNAPSHOT_GEOCODE[qkey] = ((lat, lon), dict(first.get("address") or {}))


def load_places_snapshot():
    """Load the committed popular-places snapshot into _search_cache.

    No network, never raises. Safe to call repeatedly (no-op after the
    first load). Entries use the same (query, limit=5) keys as a live
    search, so a seeded query is indistinguishable from a cached live
    one. Tests clear _search_cache in setUp, so they are unaffected.
    The same entries also seed _SNAPSHOT_GEOCODE (see
    snapshot_coords), which tests never clear.
    """
    global _SNAPSHOT_LOADED
    if _SNAPSHOT_LOADED:
        return
    _SNAPSHOT_LOADED = True
    try:
        with open(_SNAPSHOT_PATH, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        queries = payload.get("queries") or {}
        for query, entry in queries.items():
            results = (entry or {}).get("results") or []
            if not isinstance(results, list) or not results:
                continue
            _seed_snapshot_geocode(query, results)
            key = (str(query).strip().lower(), 5)
            if key in _search_cache or len(_search_cache) >= _CACHE_LIMIT:
                continue
            _search_cache[key] = [
                dict(item, address=dict(item.get("address") or {}))
                for item in results
                if isinstance(item, dict)
            ]
    except Exception as exc:  # missing/corrupt file: live search still works
        log.warning("places snapshot failed to load: %s", exc)


def snapshot_coords(address: str):
    """Coordinates + address details from the committed places snapshot.

    Returns ((lat, lng), details) or (None, None). No network, never
    raises. Matches a snapshot query exactly ("Times Square"), or
    when every word of a snapshot query appears in the typed address
    ("JFK Airport Terminal 1" matches the "jfk terminal 1" entry);
    the longest matching query wins, so "jfk terminal 1" beats "jfk".
    The details dict is a copy, so callers cannot mutate the index.
    This is the offline fallback for the fare preview when live
    geocoding answers nothing (see app.fare_preview); the booking
    flow does NOT use it — typed booking addresses still go through
    live geocoding, and unresolvable ones are rejected.
    """
    load_places_snapshot()  # no-op after the first load
    key = (address or "").strip().lower()
    if not key or not _SNAPSHOT_GEOCODE:
        return None, None
    entry = _SNAPSHOT_GEOCODE.get(key)
    if entry is not None:
        coords, details = entry
        return coords, dict(details)
    words = set(re.findall(r"[a-z0-9]+", key))
    best = None
    best_len = 0
    for query, value in _SNAPSHOT_GEOCODE.items():
        qwords = set(re.findall(r"[a-z0-9]+", query))
        if qwords and qwords <= words and len(qwords) > best_len:
            best, best_len = value, len(qwords)
    if best is None:
        return None, None
    coords, details = best
    return coords, dict(details)


def refresh_popular_places(search_fn=None, sleep_fn=None):
    """Re-fetch popular queries from live data, one shot, in order.

    An entry is replaced only when the live result is non-empty; on a
    failed or empty live result the previous (snapshot or live) value
    is restored, so a refresh can never leave a popular query empty.
    search_fn/sleep_fn are injectable for tests. Never raises.
    """
    search = search_fn or search_places
    sleep = sleep_fn or time.sleep
    for query in _POPULAR_SEARCH_QUERIES:
        key = (query.lower(), 5)
        previous = _search_cache.get(key)
        _search_cache.pop(key, None)
        try:
            fresh = search(query, 5)
        except Exception:
            fresh = []
        if fresh:
            # Cache explicitly: refresh must not depend on search_fn
            # caching (the real search_places does, a test double may
            # not). Storing copies keeps the cache immutable to callers.
            _search_cache[key] = [
                dict(item, address=dict(item.get("address") or {}))
                for item in fresh
                if isinstance(item, dict)
            ]
            # Keep the offline geocode index in step with the
            # refreshed search entry (same first result).
            _seed_snapshot_geocode(query, fresh)
        elif previous:
            _search_cache[key] = previous
        # Pace every iteration: Nominatim's usage policy asks for at
        # most 1 request/second, and a search can make several.
        sleep(_REFRESH_GAP_SECONDS)


def start_popular_places_refresh():
    """Start the one-shot background refresh thread (daemon, no-op twice).

    Called from app.py only when NOEL_SEARCH_WARMUP=1 (production).
    The thread sleeps briefly first so boot is never blocked.
    """
    global _refresh_started
    if _refresh_started:
        return
    _refresh_started = True

    def _run():
        time.sleep(5)
        refresh_popular_places()

    thread = threading.Thread(target=_run, name="places-refresh", daemon=True)
    thread.start()


# The snapshot loads at import so the very first request after a
# (free-tier) restart already has the popular queries warm.
load_places_snapshot()


def haversine_miles(lat1, lng1, lat2, lng2) -> float:
    r = 3958.8  # Earth radius in miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _route_key(lat1, lng1, lat2, lng2):
    return (round(lat1, 5), round(lng1, 5), round(lat2, 5), round(lng2, 5))


def _fetch_route(lat1, lng1, lat2, lng2):
    """One OSRM call returning (miles, geometry). Never raises.

    Geometry is a list of (lat, lng) pairs in travel order, or None
    when OSRM fails (the haversine fallback has no geometry).
    """
    key = _route_key(lat1, lng1, lat2, lng2)
    if key in _route_cache:
        return _route_cache[key]
    miles = None
    geometry = None
    try:
        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson"
        )
        data = _http_get_json(url)
        routes = data.get("routes") or []
        if routes:
            miles = routes[0]["distance"] / METERS_PER_MILE
            coords = (routes[0].get("geometry") or {}).get("coordinates") or []
            geometry = [(lat, lng) for lng, lat in coords]
            if len(geometry) < 2:
                geometry = None
    except Exception as exc:
        log.warning("OSRM route failed: %s", exc)
    if miles is None:
        miles = haversine_miles(lat1, lng1, lat2, lng2) * 1.3
        geometry = None
    miles = round(float(miles), 1)
    entry = (miles, geometry)
    if len(_route_cache) < _CACHE_LIMIT:
        _route_cache[key] = entry
    return entry


def route_miles(lat1, lng1, lat2, lng2) -> float:
    """Driving miles via OSRM; falls back to haversine * 1.3. Never raises."""
    miles, _geometry = _fetch_route(lat1, lng1, lat2, lng2)
    return miles


def route_geometry(lat1, lng1, lat2, lng2):
    """Route polyline for a previously fetched route, or None.

    Cache-only on purpose: this never fetches upstream itself (same
    contract as geocode_state). The booking flow always calls
    distance_miles/route_miles first, which warms the cache; callers
    must treat None as "no geometry" and apply the fallback toll rule.
    Returns a list of (lat, lng) pairs in travel order, or None.
    """
    entry = _route_cache.get(_route_key(lat1, lng1, lat2, lng2))
    if entry is None:
        return None
    return entry[1]


def _valid_coords(coords):
    """True for a (lat, lng) pair of finite numbers in range."""
    try:
        lat, lng = coords
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0


def distance_miles(pickup: str, dropoff: str, pickup_coords=None, dropoff_coords=None):
    """Return (miles, pickup_coords, dropoff_coords). Never raises.

    Coords are (lat, lng) tuples or None. Caller-supplied coordinates
    (from a picked autocomplete suggestion) are used as-is and never
    re-geocoded, so the priced route is exactly the place the customer
    picked; a side without coordinates is geocoded from its text. If
    either address cannot be resolved to coordinates, miles is None —
    the caller must reject the booking. There is deliberately NO
    default-miles fallback: a fare must never be computed from an
    invented distance.
    """
    try:
        if _valid_coords(pickup_coords):
            pickup_coords = (float(pickup_coords[0]), float(pickup_coords[1]))
        else:
            pickup_coords = geocode(pickup)
        if _valid_coords(dropoff_coords):
            dropoff_coords = (float(dropoff_coords[0]), float(dropoff_coords[1]))
        else:
            dropoff_coords = geocode(dropoff)
        if pickup_coords and dropoff_coords:
            miles = route_miles(
                pickup_coords[0], pickup_coords[1], dropoff_coords[0], dropoff_coords[1]
            )
            return miles, pickup_coords, dropoff_coords
        return None, pickup_coords, dropoff_coords
    except Exception as exc:  # absolute safety net
        log.warning("distance_miles failed: %s", exc)
        return None, None, None
