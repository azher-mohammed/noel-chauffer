/* Noel Chauffer — airport detection for the flight-number step.
   Pure functions, no DOM: unit-tested with node (see tests/test_flights.py).
   Primary signal: the chosen place suggestion's airport flag (aeroway /
   aerodrome from Nominatim). Fallback: the address text — airport and
   terminal words, or a major US airport code. The fallback is deliberately
   generous: the flight step is skippable and never blocks a booking.
   Codes that are also ordinary words (SAN, OAK, SEA, LAS) are excluded
   so street addresses are not mistaken for airports. */
(function (root) {
  "use strict";

  /* Major US airport codes, fallback detection only. Never used for
     terminal data — terminals always come from live map data. */
  var AIRPORT_CODES = [
    "ATL", "LAX", "ORD", "DFW", "DEN", "JFK", "SFO", "MCO",
    "MIA", "EWR", "CLT", "PHX", "IAH", "BOS", "MSP", "DTW", "PHL", "LGA",
    "BWI", "SLC", "DCA", "IAD", "TPA", "BNA", "AUS", "MDW", "DAL",
    "HOU", "STL", "RDU", "PDX", "MCI", "SMF", "SJC", "FLL", "MSY",
    "CLE", "PIT", "CMH", "IND", "BDL", "PVD", "JAX", "SAT", "ABQ", "HNL"
  ];

  function isAirportSuggestion(place) {
    return !!(place && place.airport === true);
  }

  function isAirportText(text) {
    if (!text) return false;
    var upper = String(text).toUpperCase();
    if (/\bAIRPORT\b/.test(upper) || /\bTERMINAL\b/.test(upper)) return true;
    for (var i = 0; i < AIRPORT_CODES.length; i++) {
      if (new RegExp("\\b" + AIRPORT_CODES[i] + "\\b").test(upper)) return true;
    }
    return false;
  }

  function isAirportSide(place, text) {
    return isAirportSuggestion(place) || isAirportText(text);
  }

  function airportSides(pickupPlace, dropoffPlace, pickupText, dropoffText) {
    var pickup = isAirportSide(pickupPlace, pickupText);
    var dropoff = isAirportSide(dropoffPlace, dropoffText);
    return { pickup: pickup, dropoff: dropoff, any: pickup || dropoff };
  }

  root.NoelFlight = {
    isAirportSuggestion: isAirportSuggestion,
    isAirportText: isAirportText,
    airportSides: airportSides
  };
})(typeof window !== "undefined" ? window : globalThis);
