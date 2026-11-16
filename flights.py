"""Flight numbers for airport bookings: normalization, airline names,
and terminal extraction.

No live flight tracking: the airline name comes only from the flight
number's IATA airline code, looked up in a small curated table of real
public IATA codes for carriers serving US airports. Unknown codes are
shown exactly as entered — a name is never guessed. A missing or
unparseable flight number is never an error and never blocks a booking.
"""

from __future__ import annotations

import re

# Curated IATA airline designators (2 characters) -> airline name.
# Real public codes only, major carriers serving US airports.
AIRLINE_NAMES = {
    # United States
    "AA": "American Airlines",
    "AS": "Alaska Airlines",
    "B6": "JetBlue",
    "DL": "Delta Air Lines",
    "F9": "Frontier Airlines",
    "G4": "Allegiant Air",
    "HA": "Hawaiian Airlines",
    "MX": "Breeze Airways",
    "NK": "Spirit Airlines",
    "SY": "Sun Country Airlines",
    "UA": "United Airlines",
    "WN": "Southwest Airlines",
    "XP": "Avelo Airlines",
    # Canada, Mexico, Caribbean, Latin America
    "AC": "Air Canada",
    "AD": "Azul Brazilian Airlines",
    "AM": "Aeromexico",
    "AV": "Avianca",
    "CM": "Copa Airlines",
    "G3": "GOL Linhas Aereas",
    "LA": "LATAM Airlines",
    "PD": "Porter Airlines",
    "TS": "Air Transat",
    "VB": "Viva Aerobus",
    "WS": "WestJet",
    "Y4": "Volaris",
    # Europe
    "AF": "Air France",
    "AY": "Finnair",
    "AZ": "ITA Airways",
    "BA": "British Airways",
    "EI": "Aer Lingus",
    "FI": "Icelandair",
    "IB": "Iberia",
    "KL": "KLM Royal Dutch Airlines",
    "LH": "Lufthansa",
    "LO": "LOT Polish Airlines",
    "LX": "Swiss International Air Lines",
    "OS": "Austrian Airlines",
    "SK": "Scandinavian Airlines",
    "SN": "Brussels Airlines",
    "TP": "TAP Air Portugal",
    "TK": "Turkish Airlines",
    "VS": "Virgin Atlantic",
    # Middle East and Africa
    "AT": "Royal Air Maroc",
    "EK": "Emirates",
    "ET": "Ethiopian Airlines",
    "EY": "Etihad Airways",
    "GF": "Gulf Air",
    "LY": "El Al",
    "MS": "EgyptAir",
    "QR": "Qatar Airways",
    "RJ": "Royal Jordanian",
    "SV": "Saudia",
    "WY": "Oman Air",
    # Asia-Pacific
    "AI": "Air India",
    "BR": "EVA Air",
    "CA": "Air China",
    "CI": "China Airlines",
    "CX": "Cathay Pacific",
    "CZ": "China Southern Airlines",
    "FJ": "Fiji Airways",
    "JL": "Japan Airlines",
    "KE": "Korean Air",
    "MU": "China Eastern Airlines",
    "NH": "All Nippon Airways",
    "NZ": "Air New Zealand",
    "OZ": "Asiana Airlines",
    "PR": "Philippine Airlines",
    "QF": "Qantas",
    "SQ": "Singapore Airlines",
}

# IATA designator (2 letters/digits) + flight number (1-4 digits,
# optional single-letter suffix, e.g. EK215, B61234, AA123A).
_FLIGHT_RE = re.compile(r"^([A-Z0-9]{2})(\d{1,4}[A-Z]?)$")


def normalize_flight_number(raw):
    """Canonical flight-number form (e.g. 'EK215'), or None.

    Spaces are removed and letters uppercased, so 'ek 215' and 'EK215'
    store the same way. Anything that does not look like a flight
    number returns None — the booking still goes through.
    """
    if raw is None:
        return None
    cleaned = re.sub(r"\s+", "", str(raw)).upper()
    if not cleaned or len(cleaned) > 10:
        return None
    if not _FLIGHT_RE.match(cleaned):
        return None
    return cleaned


def airline_name_for(flight_number):
    """Airline name from the flight number's IATA code, or None.

    Unknown codes return None so the caller shows the code exactly as
    entered instead of guessing a name.
    """
    if not flight_number:
        return None
    return AIRLINE_NAMES.get(str(flight_number)[:2].upper())


def terminal_from_address(address_text):
    """First address component when it names a terminal, else None.

    The component comes from the place suggestion the customer chose
    (e.g. 'Terminal 4 Arrivals'); nothing is invented.
    """
    first = (address_text or "").split(",")[0].strip()
    return first if "terminal" in first.lower() else None


def terminal_for_booking(pickup, dropoff):
    """Terminal for a booking: the pickup side first, else drop-off."""
    return terminal_from_address(pickup) or terminal_from_address(dropoff)


def flight_info(flight_number, pickup, dropoff):
    """Flight display fields for a booking payload."""
    return {
        "flight_number": flight_number,
        "airline_name": airline_name_for(flight_number),
        "terminal": terminal_for_booking(pickup, dropoff),
    }
