"""Tolled-crossing detection from route geometry.

A route polyline -- (latitude, longitude) pairs from the same OSRM call
that produces the trip miles -- is tested against short "gate" segments
placed over the water at each tolled crossing. A gate counts as crossed
when any consecutive pair of route points intersects the gate segment.
Gate-segment intersection (not a radius buffer) keeps nearby free roads
from producing false-positive tolls: every gate sits where the tolled
crossing is the only road.

Free crossings (Queensboro, Brooklyn, Manhattan and Williamsburg
Bridges) deliberately have NO gate: a route over one of them detects $0.

Rates are passenger-car E-ZPass rates, verified 2026-11-17 from the
official schedules:

* Port Authority of NY & NJ -- $16.79 peak / $14.79 off-peak, effective
  January 4, 2026, collected ONLY when entering New York. For the
  Hudson crossings, Goethals Bridge and Outerbridge Crossing that
  means eastbound; for the Bayonne Bridge it means westbound, because
  Staten Island lies WEST of Bayonne. This module charges the flat
  $16.79 peak figure for every tolled-direction detection, matching
  the agreed NJ return-toll figure; no peak / off-peak time-of-day
  logic is implemented (open question).
  Source: Port Authority toll schedule (panynj.gov), rates effective
  January 4, 2026.
* MTA Bridges & Tunnels (TBTA) -- $7.46 E-ZPass (NYCSC) for the major
  crossings, tolled in BOTH directions, effective January 4, 2026.
  Source: MTA "Triborough Bridge and Tunnel Authority Crossing
  Charges" (mta.info/document/180046).

Not gated (open questions): Henry Hudson Bridge, Cross Bay / Marine
Parkway Bridges, Gov. Mario M. Cuomo Bridge, and Manhattan
congestion-pricing zone charges.
"""

from collections import namedtuple
from decimal import Decimal

PA_EZPASS = Decimal("16.79")
MTA_EZPASS = Decimal("7.46")

# Direction rules: "eastbound" = tolled only when the route travels
# east (longitude increasing) across the gate; "westbound" = tolled
# only when the route travels west (longitude decreasing); "both" =
# tolled in either direction. Port Authority crossings are tolled
# only when entering New York; the Bayonne Bridge is the one case
# where entering New York means travelling west.
Gate = namedtuple("Gate", ["name", "a", "b", "direction", "rate"])

GATES = [
    # Port Authority Hudson crossings (tolled eastbound only).
    # Gate positions were placed on the actual road centerlines from
    # live OSRM route geometry + Nominatim (OSM) crossing locations,
    # and validated against real routes on 2026-11-17.
    Gate("Holland Tunnel", (40.7230, -74.0180), (40.7300, -74.0180),
         "eastbound", PA_EZPASS),
    Gate("Lincoln Tunnel", (40.7565, -74.0035), (40.7630, -74.0035),
         "eastbound", PA_EZPASS),
    Gate("George Washington Bridge", (40.8485, -73.9530), (40.8545, -73.9530),
         "eastbound", PA_EZPASS),
    # MTA crossings (tolled both directions).
    # Midtown gate sits in the western East River channel so a free
    # Queensboro Bridge trip that drives south on Roosevelt Island's
    # Main Street does not trip it.
    Gate("Queens-Midtown Tunnel", (40.7415, -73.9600), (40.7465, -73.9600),
         "both", MTA_EZPASS),
    Gate("Hugh L. Carey Tunnel", (40.69353, -74.01512), (40.69647, -74.00988),
         "both", MTA_EZPASS),
    # RFK Bridge: one toll covers all spans, so both legs share one
    # name and are counted at most once per trip. No gate on the
    # Manhattan (125th St) span: whether it is tolled standalone is
    # unverified.
    Gate("RFK Bridge", (40.7825, -73.9325), (40.7825, -73.9255),
         "both", MTA_EZPASS),
    Gate("RFK Bridge", (40.80106, -73.91522), (40.80554, -73.91298),
         "both", MTA_EZPASS),
    Gate("Whitestone Bridge", (40.80088, -73.83222), (40.80412, -73.82718),
         "both", MTA_EZPASS),
    Gate("Throgs Neck Bridge", (40.8080, -73.7975), (40.8080, -73.7905),
         "both", MTA_EZPASS),
    Gate("Verrazzano-Narrows Bridge", (40.60366, -74.04435), (40.60934, -74.04625),
         "both", MTA_EZPASS),
    # Port Authority Staten Island crossings (tolled entering NY only).
    # Bayonne is westbound-only: Staten Island lies west of Bayonne.
    Gate("Bayonne Bridge", (40.64348, -74.13836), (40.64592, -74.14384),
         "westbound", PA_EZPASS),
    Gate("Goethals Bridge", (40.62708, -74.18616), (40.63152, -74.18384),
         "eastbound", PA_EZPASS),
    Gate("Outerbridge Crossing", (40.5190, -74.233), (40.5280, -74.233),
         "eastbound", PA_EZPASS),
]

_EPS = 1e-9


def _cross(ax, ay, bx, by):
    return ax * by - ay * bx


def _on_segment(px, py, ax, ay, bx, by):
    """True when point P lies on segment AB (touching counts)."""
    if abs(_cross(px - ax, py - ay, bx - ax, by - ay)) > _EPS:
        return False
    return (min(ax, bx) - _EPS <= px <= max(ax, bx) + _EPS
            and min(ay, by) - _EPS <= py <= max(ay, by) + _EPS)


def _segments_intersect(p1, p2, p3, p4):
    """Orientation-based segment intersection; touching counts."""
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p1, p2, p3, p4
    d1 = _cross(x2 - x1, y2 - y1, x3 - x1, y3 - y1)
    d2 = _cross(x2 - x1, y2 - y1, x4 - x1, y4 - y1)
    d3 = _cross(x4 - x3, y4 - y3, x1 - x3, y1 - y3)
    d4 = _cross(x4 - x3, y4 - y3, x2 - x3, y2 - y3)
    if ((d1 > _EPS) != (d2 > _EPS) and (d3 > _EPS) != (d4 > _EPS)
            and abs(d1) > _EPS and abs(d2) > _EPS
            and abs(d3) > _EPS and abs(d4) > _EPS):
        return True
    # Collinear / touching cases.
    if abs(d1) <= _EPS and _on_segment(x3, y3, x1, y1, x2, y2):
        return True
    if abs(d2) <= _EPS and _on_segment(x4, y4, x1, y1, x2, y2):
        return True
    if abs(d3) <= _EPS and _on_segment(x1, y1, x3, y3, x4, y4):
        return True
    if abs(d4) <= _EPS and _on_segment(x2, y2, x3, y3, x4, y4):
        return True
    return False


def detect_crossing_tolls(geometry):
    """Detect tolled crossings on a route polyline.

    ``geometry`` is an iterable of (latitude, longitude) pairs in
    travel order. Returns ``(total, names)`` where ``total`` is the
    summed E-ZPass toll as a Decimal and ``names`` lists each crossed
    toll crossing once, in the order first crossed. Empty / missing
    geometry detects nothing (callers apply the fallback rule).
    """
    total = Decimal("0.00")
    names = []
    counted = set()
    points = [(lng, lat) for lat, lng in (geometry or [])]
    gates_xy = [((g.a[1], g.a[0]), (g.b[1], g.b[0]), g) for g in GATES]
    for p1, p2 in zip(points, points[1:]):
        dlng = p2[0] - p1[0]
        for ga, gb, gate in gates_xy:
            if gate.name in counted:
                continue
            if gate.direction == "eastbound" and dlng <= _EPS:
                # Westbound across a Port Authority gate: free.
                continue
            if gate.direction == "westbound" and dlng >= -_EPS:
                # Eastbound across the Bayonne Bridge gate: free
                # (toll is collected entering New York, i.e. westbound).
                continue
            if _segments_intersect(p1, p2, ga, gb):
                counted.add(gate.name)
                names.append(gate.name)
                total += gate.rate
    return total, names
