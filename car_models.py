"""Eligible car models for Noel Chauffer driver registration.

Single source of truth, read by the server (validation + the
``/api/car-models`` endpoint the driver app dropdown fetches) and by
the tests. Do NOT duplicate this list anywhere else.

Source: UBER_BLACK_LIST.md — Uber's Black eligible-vehicles list
(132 models, 23 makes), transcribed from Uber's eligible-vehicles
tool via RideWise, checked 18 Oct 2026. Model names below are the
full "Make Model" display names; the "(SUV)" markers in the source
file are eligibility notes, not part of any model name.

Owner decisions (voice call 2026-11-16):
- Year floor: 2022 or newer ("2022 se rakhna") — stricter than
  Uber's 2020+ rule.
- TEMPORARY exception: "Tesla Model 3" is included ONLY so the owner
  (Azhar Mohammed) can try the system with his own 2023 Model 3.
  Remove it when he says so. It is NOT on Uber's Black list.
  Owner decision 2026-11-19 (voice call): the exception is ONLY for
  the owner and Sana Baga — no other driver may use Model 3, and it
  must not even be VISIBLE to them in the dropdown. The endpoint
  serves it only when the email typed in the form belongs to one of
  the two (see MODEL_3_ALLOWED_EMAILS), and registration rejects it
  for anyone else even if posted directly.
- Tesla Model Y stays EXCLUDED. No other additions.
- Jeep Wagoneer S is included: the source marks it "SF Bay Area
  only", but keeping the full transcribed list intact is safer than
  silently dropping one model; the restriction is noted here and in
  UBER_BLACK_LIST.md.
- Vehicle class: every model maps to exactly one class — "sedan"
  (Business Class) or "suv" (Business SUV) — in
  VEHICLE_CLASS_BY_MAKE below. Owner decision 2026-11-21 (voice
  call, "Black SUV hi daalna" / "Black Cars hi daalna"): the SUV
  class is EXACTLY the 23 Uber Black SUV models (the "(SUV)"-marked
  models in UBER_BLACK_LIST.md) — "Professional SUV" in the owner's
  words. The other 62 SUV-body models from the source list are
  Business Class ("sedan") and STAY in the dropdown — body style no
  longer decides the class, and no model was removed from the list.
  So the list holds 109 sedans + 23 SUVs (132 models), plus the
  temporary Model 3 sedan exception (133 in the mapping). Judgment
  calls from before this change are documented in static/NOTES.md.
- First Class: exactly twelve models qualify — the four Blacklane
  First Class models (Mercedes-Benz S-Class, BMW 7 Series, Audi A8,
  Tesla Model X; owner decision 2026-11-20) plus eight owner-added
  flagships (Bentley Bentayga, Flying Spur, Mulsanne; Mercedes-Benz
  Maybach S-Class; Rolls-Royce Cullinan, Ghost, Phantom; Lamborghini
  Urus; owner decision 2026-11-21, "dono mein bhi rakhen") — see
  FIRST_CLASS_MODELS below. Qualification is by model, not by
  sedan/suv class: every First Class model KEEPS its Business Class
  dispatch, so First Class is an extra qualification, not a
  replacement class.
"""

from datetime import date

MIN_CAR_YEAR = 2022


def max_car_year():
    """Newest acceptable model year: current year + 1."""
    return date.today().year + 1


# Make -> model names, exactly as transcribed in UBER_BLACK_LIST.md.
CAR_MODELS_BY_MAKE = {
    "Audi": ["A6", "A6 Avant", "A7", "A8", "A8 L", "Q4 e-tron", "Q5",
             "Q7", "Q8", "Q8 e-tron", "RS 6", "RS 7", "S6", "S7", "S8",
             "SQ5", "SQ7", "SQ8", "e-tron"],
    "BMW": ["5 Series 530e", "5 Series", "7 Series 745e", "7 Series",
            "740i", "750", "Alpina B7", "X3", "X5", "X6", "X7", "i5",
            "i7", "iX"],
    "Bentley": ["Bentayga", "Flying Spur", "Mulsanne"],
    "Cadillac": ["CT6", "Escalade", "Escalade ESV", "Escalade IQ",
                 "LYRIQ", "Optiq", "VISTIQ", "XT5", "XT6", "XTS"],
    "Chevrolet": ["Suburban", "Tahoe"],
    "Ford": ["Expedition", "Expedition MAX", "Expedition MAX XLT"],
    "GMC": ["Yukon", "Yukon Denali", "Yukon XL", "Yukon XL Denali"],
    "Genesis": ["G90", "GV60", "GV70", "GV80"],
    "Infiniti": ["QX80"],
    "Jaguar": ["F-PACE", "XJ"],
    "Jeep": ["Grand Wagoneer", "Grand Wagoneer L", "Wagoneer",
             "Wagoneer L", "Wagoneer S"],
    "Lamborghini": ["Urus"],
    "Land Rover": ["Defender", "Range Rover", "Range Rover Sport",
                   "Range Rover Velar"],
    "Lexus": ["GS", "GS Hybrid", "GX", "LS", "LX", "TX", "TX 350",
              "TX 500h"],
    "Lincoln": ["Aviator", "Continental", "Corsair", "MKT", "Nautilus",
                "Navigator", "Navigator L"],
    "Lucid": ["Air", "Air Grand Touring", "Air Pure", "Air Touring",
              "Gravity"],
    "Maserati": ["Levante", "Quattroporte"],
    "Mercedes-Benz": ["E-Class", "E350e", "EQB", "EQE", "EQE SUV",
                      "EQS", "EQS SUV", "G-Class", "GL-Class", "GLC",
                      "GLC Coupe", "GLC-Class", "GLC-Class 350e", "GLE",
                      "GLE Coupe", "GLE-Class", "GLS", "GLS SUV",
                      "GLS-Class", "S-Class", "Maybach S-Class"],
    "Porsche": ["Cayenne", "Cayenne Coupe", "Panamera", "Taycan"],
    "Rivian": ["R1S"],
    "Rolls-Royce": ["Cullinan", "Ghost", "Phantom"],
    "Tesla": ["Model S", "Model X"],
    "Volvo": ["EX90", "S90", "S90 Hybrid", "XC60", "XC60 Hybrid",
              "XC90", "XC90 Hybrid"],
}

# Vehicle class per model: "sedan" (Business Class) or "suv"
# (Business SUV). Every model in CAR_MODELS_BY_MAKE appears here
# exactly once; the temporary Model 3 exception is added in
# vehicle_class_by_model() below. See the module docstring and
# static/NOTES.md for the classification rule and judgment calls.
VEHICLE_CLASS_BY_MAKE = {
    "Audi": {"A6": "sedan", "A6 Avant": "sedan", "A7": "sedan",
             "A8": "sedan", "A8 L": "sedan", "Q4 e-tron": "sedan",
             "Q5": "sedan", "Q7": "sedan", "Q8": "sedan", "Q8 e-tron": "sedan",
             "RS 6": "sedan", "RS 7": "sedan", "S6": "sedan",
             "S7": "sedan", "S8": "sedan", "SQ5": "sedan", "SQ7": "sedan",
             "SQ8": "sedan", "e-tron": "sedan"},
    "BMW": {"5 Series 530e": "sedan", "5 Series": "sedan",
            "7 Series 745e": "sedan", "7 Series": "sedan",
            "740i": "sedan", "750": "sedan", "Alpina B7": "sedan",
            "X3": "sedan", "X5": "sedan", "X6": "sedan", "X7": "sedan",
            "i5": "sedan", "i7": "sedan", "iX": "sedan"},
    "Bentley": {"Bentayga": "sedan", "Flying Spur": "sedan",
                "Mulsanne": "sedan"},
    "Cadillac": {"CT6": "sedan", "Escalade": "suv", "Escalade ESV": "suv",
                 "Escalade IQ": "suv", "LYRIQ": "sedan", "Optiq": "sedan",
                 "VISTIQ": "sedan", "XT5": "sedan", "XT6": "sedan",
                 "XTS": "sedan"},
    "Chevrolet": {"Suburban": "suv", "Tahoe": "suv"},
    "Ford": {"Expedition": "suv", "Expedition MAX": "suv",
             "Expedition MAX XLT": "suv"},
    "GMC": {"Yukon": "suv", "Yukon Denali": "suv", "Yukon XL": "suv",
            "Yukon XL Denali": "suv"},
    "Genesis": {"G90": "sedan", "GV60": "sedan", "GV70": "sedan",
                "GV80": "sedan"},
    "Infiniti": {"QX80": "suv"},
    "Jaguar": {"F-PACE": "sedan", "XJ": "sedan"},
    "Jeep": {"Grand Wagoneer": "suv", "Grand Wagoneer L": "suv",
             "Wagoneer": "suv", "Wagoneer L": "suv", "Wagoneer S": "sedan"},
    "Lamborghini": {"Urus": "sedan"},
    "Land Rover": {"Defender": "sedan", "Range Rover": "sedan",
                   "Range Rover Sport": "sedan", "Range Rover Velar": "sedan"},
    "Lexus": {"GS": "sedan", "GS Hybrid": "sedan", "GX": "sedan",
              "LS": "sedan", "LX": "sedan", "TX": "sedan", "TX 350": "sedan",
              "TX 500h": "sedan"},
    "Lincoln": {"Aviator": "sedan", "Continental": "sedan", "Corsair": "sedan",
                "MKT": "suv", "Nautilus": "sedan", "Navigator": "suv",
                "Navigator L": "suv"},
    "Lucid": {"Air": "sedan", "Air Grand Touring": "sedan",
              "Air Pure": "sedan", "Air Touring": "sedan",
              "Gravity": "sedan"},
    "Maserati": {"Levante": "sedan", "Quattroporte": "sedan"},
    "Mercedes-Benz": {"E-Class": "sedan", "E350e": "sedan", "EQB": "sedan",
                      "EQE": "sedan", "EQE SUV": "sedan", "EQS": "sedan",
                      "EQS SUV": "sedan", "G-Class": "sedan", "GL-Class": "suv",
                      "GLC": "sedan", "GLC Coupe": "sedan", "GLC-Class": "sedan",
                      "GLC-Class 350e": "sedan", "GLE": "sedan",
                      "GLE Coupe": "sedan", "GLE-Class": "sedan", "GLS": "sedan",
                      "GLS SUV": "suv", "GLS-Class": "sedan",
                      "S-Class": "sedan", "Maybach S-Class": "sedan"},
    "Porsche": {"Cayenne": "sedan", "Cayenne Coupe": "sedan",
                "Panamera": "sedan", "Taycan": "sedan"},
    "Rivian": {"R1S": "suv"},
    "Rolls-Royce": {"Cullinan": "sedan", "Ghost": "sedan", "Phantom": "sedan"},
    "Tesla": {"Model S": "sedan", "Model X": "sedan"},
    "Volvo": {"EX90": "sedan", "S90": "sedan", "S90 Hybrid": "sedan",
              "XC60": "sedan", "XC60 Hybrid": "sedan", "XC90": "sedan",
              "XC90 Hybrid": "sedan"},
}

# FIRST CLASS qualifying models — owner decisions 2026-11-20 ~03:00 EST
# (voice call): "wahi daal dena na same" — use the SAME cars as
# Blacklane First Class; and 2026-11-21 ~01:44-01:48 EST (voice call):
# add eight flagships, DUAL with Business Class ("dono mein bhi
# rakhen"). Blacklane First Class (blacklane.com, checked 2026-11-20):
# Mercedes-Benz S-Class, BMW 7 Series, Audi A8, and Tesla Model X in
# some cities — always "or similar": the customer picks a CLASS, the
# exact model is never guaranteed. Exactly these twelve qualify for
# Noel First Class dispatch. The other flagship equivalents stay in
# their Business Class / Business SUV classes (Alpina B7, i7, S8, LS,
# G90 and the rest) — the owner can add more later if he wants. All
# twelve are already on the Uber Black dropdown list, so nothing is
# added to CAR_MODELS_BY_MAKE for this. First Class qualification is
# by MODEL, not by sedan/suv class, and every one of the twelve keeps
# its Business Class dispatch (all twelve are "sedan" in
# VEHICLE_CLASS_BY_MAKE — including the SUV-body Bentayga, Urus and
# Cullinan, since only the 23 Uber Black SUV models are SUVs, owner
# decision 2026-11-21). So a Bentayga / Ghost / Urus driver gets
# Business Class jobs AND First Class jobs, exactly like an S-Class
# or Model X driver.
FIRST_CLASS_MODELS = frozenset({
    "Mercedes-Benz S-Class",
    "BMW 7 Series",
    "Audi A8",
    "Tesla Model X",
    "Bentley Bentayga",
    "Bentley Flying Spur",
    "Bentley Mulsanne",
    "Mercedes-Benz Maybach S-Class",
    "Rolls-Royce Cullinan",
    "Rolls-Royce Ghost",
    "Rolls-Royce Phantom",
    "Lamborghini Urus",
})


def is_first_class_model(value):
    """True when this car model qualifies for First Class dispatch."""
    return normalize_car_model(value) in FIRST_CLASS_MODELS


# TEMPORARY owner-trial exception (see module docstring). NOT on
# Uber's Black list. Remove when the owner says so.
TEMPORARY_MODEL_3 = "Tesla Model 3"

# Owner decision 2026-11-19 (voice call): the Model 3 exception is
# ONLY for the owner (Azher Mohammed) and Sana Baga. Both of the
# owner's own emails are listed because either could be the one on
# his driver record; Sana's is the address she re-registered with
# (sanabaga12@gmail.com, 2026-11-18).
MODEL_3_ALLOWED_EMAILS = frozenset({
    "m.azherahmed1@gmail.com",
    "ahmedazher476@gmail.com",
    "sanabaga12@gmail.com",
})


def model_3_allowed_for(email):
    """True only for the two drivers allowed the Model 3 exception."""
    return (email or "").strip().lower() in MODEL_3_ALLOWED_EMAILS


# Owner decision 2026-11-20 (voice call): the SAME two drivers — the
# owner (Azher Mohammed) and Sana Baga — are exempt from the
# arrival/completion location gate: "I have arrived" and "Complete
# trip" work for them without a location, and a far-away position
# never blocks them. Every other driver keeps the 100 m gate exactly
# as it is. This shares the Model 3 email set so the two
# special-cases stay consistent: both are owner + Sana only, and any
# change to who counts as one of the two must change both together.
LOCATION_EXEMPT_EMAILS = MODEL_3_ALLOWED_EMAILS


def location_exempt_for(email):
    """True only for the two drivers exempt from the location gate."""
    return (email or "").strip().lower() in LOCATION_EXEMPT_EMAILS


# Owner decision 2026-11-24 (voice call, "mere ko aur sana ko nahi
# karna pause"): the SAME two drivers — the owner (Azher Mohammed)
# and Sana Baga — are exempt from the 48-hour fault suspension
# after an emergency cancel: a fault cancel by either of them never
# blocks the driver app, and a suspension already on their record
# reads as lifted. Every other driver keeps the 48-hour block
# exactly as it is. This shares the Model 3 / location email set so
# the three special-cases stay consistent: all are owner + Sana
# only, and any change to who counts as one of the two must change
# all three together.
SUSPENSION_EXEMPT_EMAILS = MODEL_3_ALLOWED_EMAILS


def suspension_exempt_for(email):
    """True only for the two drivers exempt from the fault suspension."""
    return (email or "").strip().lower() in SUSPENSION_EXEMPT_EMAILS


def uber_black_models():
    """The 132 transcribed Uber Black models, as 'Make Model' names."""
    models = []
    for make in sorted(CAR_MODELS_BY_MAKE):
        for model in CAR_MODELS_BY_MAKE[make]:
            models.append("%s %s" % (make, model))
    return sorted(models)


def allowed_models(email=None):
    """Models the dropdown offers for this registrant.

    The 132 Uber Black models for everyone; the temporary Model 3
    only when `email` belongs to Azher Mohammed or Sana Baga. With
    no email (or any other email) the list is 132 and Model 3 never
    appears — other drivers must not even see it.
    """
    models = uber_black_models()
    if model_3_allowed_for(email):
        models = models + [TEMPORARY_MODEL_3]
    return sorted(models)


# Every model the server knows at all (132 + Model 3): the membership
# check in validate_car_model. Visibility is decided separately by
# allowed_models(email).
ALLOWED_CAR_MODELS = frozenset(uber_black_models() + [TEMPORARY_MODEL_3])


def vehicle_class_by_model():
    """Full "Make Model" name -> "sedan"/"suv", all 133 models."""
    mapping = {}
    for make, models in VEHICLE_CLASS_BY_MAKE.items():
        for model, cls in models.items():
            mapping["%s %s" % (make, model)] = cls
    # Temporary owner-trial exception: a sedan, like the other Teslas
    # that are cars rather than SUVs (Model S is a sedan; Model X is
    # classed sedan since the 2026-11-21 Professional SUV change,
    # though it stays First-eligible by model). Remove with
    # TEMPORARY_MODEL_3 when the owner says so.
    mapping[TEMPORARY_MODEL_3] = "sedan"
    return mapping


VEHICLE_CLASS_BY_MODEL = vehicle_class_by_model()


def class_for_model(value):
    """Return "sedan"/"suv" for an eligible model, else None."""
    return VEHICLE_CLASS_BY_MODEL.get(normalize_car_model(value))


def normalize_car_model(value):
    """Strip surrounding whitespace; matching is otherwise exact."""
    return (value or "").strip()


def validate_car_model(value, email=None):
    """Return (normalized_model, None) or (None, error_message).

    `email` is the registrant's email (already normalized). The
    temporary Model 3 is rejected for anyone but the two allowed
    drivers, even if it is posted directly instead of picked from
    the dropdown.
    """
    model = normalize_car_model(value)
    if not model:
        return None, "Please choose your car model from the list."
    if model not in ALLOWED_CAR_MODELS:
        return None, "That car model is not eligible. Please choose a model from the list."
    if model == TEMPORARY_MODEL_3 and not model_3_allowed_for(email):
        return None, ("Tesla Model 3 is only available for selected drivers. "
                      "Please choose another model from the list.")
    return model, None


def validate_car_year(value):
    """Return (year, None) or (None, error_message)."""
    if value is None or str(value).strip() == "":
        return None, "Please choose your car's model year."
    try:
        year = int(str(value).strip())
    except (TypeError, ValueError):
        return None, "Please choose a valid model year."
    if year < MIN_CAR_YEAR:
        return None, "Only cars from %d or newer can be registered." % MIN_CAR_YEAR
    if year > max_car_year():
        return None, "Please choose a valid model year."
    return year, None
