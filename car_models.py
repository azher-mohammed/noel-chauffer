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
- Tesla Model Y stays EXCLUDED. No other additions.
- Jeep Wagoneer S is included: the source marks it "SF Bay Area
  only", but keeping the full transcribed list intact is safer than
  silently dropping one model; the restriction is noted here and in
  UBER_BLACK_LIST.md.
- Vehicle class: every model maps to exactly one class — "sedan"
  (Business Class) or "suv" (Business SUV) — in
  VEHICLE_CLASS_BY_MAKE below. Rule: SUV/crossover body styles are
  SUVs; sedans, coupes, hatchbacks and wagons are sedans. The 23
  Black SUV models from UBER_BLACK_LIST.md are all SUVs. Judgment
  calls are documented in static/NOTES.md.
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
             "A8": "sedan", "A8 L": "sedan", "Q4 e-tron": "suv",
             "Q5": "suv", "Q7": "suv", "Q8": "suv", "Q8 e-tron": "suv",
             "RS 6": "sedan", "RS 7": "sedan", "S6": "sedan",
             "S7": "sedan", "S8": "sedan", "SQ5": "suv", "SQ7": "suv",
             "SQ8": "suv", "e-tron": "suv"},
    "BMW": {"5 Series 530e": "sedan", "5 Series": "sedan",
            "7 Series 745e": "sedan", "7 Series": "sedan",
            "740i": "sedan", "750": "sedan", "Alpina B7": "sedan",
            "X3": "suv", "X5": "suv", "X6": "suv", "X7": "suv",
            "i5": "sedan", "i7": "sedan", "iX": "suv"},
    "Bentley": {"Bentayga": "suv", "Flying Spur": "sedan",
                "Mulsanne": "sedan"},
    "Cadillac": {"CT6": "sedan", "Escalade": "suv", "Escalade ESV": "suv",
                 "Escalade IQ": "suv", "LYRIQ": "suv", "Optiq": "suv",
                 "VISTIQ": "suv", "XT5": "suv", "XT6": "suv",
                 "XTS": "sedan"},
    "Chevrolet": {"Suburban": "suv", "Tahoe": "suv"},
    "Ford": {"Expedition": "suv", "Expedition MAX": "suv",
             "Expedition MAX XLT": "suv"},
    "GMC": {"Yukon": "suv", "Yukon Denali": "suv", "Yukon XL": "suv",
            "Yukon XL Denali": "suv"},
    "Genesis": {"G90": "sedan", "GV60": "suv", "GV70": "suv",
                "GV80": "suv"},
    "Infiniti": {"QX80": "suv"},
    "Jaguar": {"F-PACE": "suv", "XJ": "sedan"},
    "Jeep": {"Grand Wagoneer": "suv", "Grand Wagoneer L": "suv",
             "Wagoneer": "suv", "Wagoneer L": "suv", "Wagoneer S": "suv"},
    "Lamborghini": {"Urus": "suv"},
    "Land Rover": {"Defender": "suv", "Range Rover": "suv",
                   "Range Rover Sport": "suv", "Range Rover Velar": "suv"},
    "Lexus": {"GS": "sedan", "GS Hybrid": "sedan", "GX": "suv",
              "LS": "sedan", "LX": "suv", "TX": "suv", "TX 350": "suv",
              "TX 500h": "suv"},
    "Lincoln": {"Aviator": "suv", "Continental": "sedan", "Corsair": "suv",
                "MKT": "suv", "Nautilus": "suv", "Navigator": "suv",
                "Navigator L": "suv"},
    "Lucid": {"Air": "sedan", "Air Grand Touring": "sedan",
              "Air Pure": "sedan", "Air Touring": "sedan",
              "Gravity": "suv"},
    "Maserati": {"Levante": "suv", "Quattroporte": "sedan"},
    "Mercedes-Benz": {"E-Class": "sedan", "E350e": "sedan", "EQB": "suv",
                      "EQE": "sedan", "EQE SUV": "suv", "EQS": "sedan",
                      "EQS SUV": "suv", "G-Class": "suv", "GL-Class": "suv",
                      "GLC": "suv", "GLC Coupe": "suv", "GLC-Class": "suv",
                      "GLC-Class 350e": "suv", "GLE": "suv",
                      "GLE Coupe": "suv", "GLE-Class": "suv", "GLS": "suv",
                      "GLS SUV": "suv", "GLS-Class": "suv",
                      "S-Class": "sedan", "Maybach S-Class": "sedan"},
    "Porsche": {"Cayenne": "suv", "Cayenne Coupe": "suv",
                "Panamera": "sedan", "Taycan": "sedan"},
    "Rivian": {"R1S": "suv"},
    "Rolls-Royce": {"Cullinan": "suv", "Ghost": "sedan", "Phantom": "sedan"},
    "Tesla": {"Model S": "sedan", "Model X": "suv"},
    "Volvo": {"EX90": "suv", "S90": "sedan", "S90 Hybrid": "sedan",
              "XC60": "suv", "XC60 Hybrid": "suv", "XC90": "suv",
              "XC90 Hybrid": "suv"},
}

# TEMPORARY owner-trial exception (see module docstring). NOT on
# Uber's Black list. Remove when the owner says so.
TEMPORARY_MODEL_3 = "Tesla Model 3"


def uber_black_models():
    """The 132 transcribed Uber Black models, as 'Make Model' names."""
    models = []
    for make in sorted(CAR_MODELS_BY_MAKE):
        for model in CAR_MODELS_BY_MAKE[make]:
            models.append("%s %s" % (make, model))
    return sorted(models)


def allowed_models():
    """Every model the dropdown offers: the 132 + temporary Model 3."""
    return sorted(uber_black_models() + [TEMPORARY_MODEL_3])


ALLOWED_CAR_MODELS = frozenset(allowed_models())


def vehicle_class_by_model():
    """Full "Make Model" name -> "sedan"/"suv", all 133 models."""
    mapping = {}
    for make, models in VEHICLE_CLASS_BY_MAKE.items():
        for model, cls in models.items():
            mapping["%s %s" % (make, model)] = cls
    # Temporary owner-trial exception: a sedan, like the other Teslas
    # that are cars rather than SUVs (Model S is a sedan; Model X is
    # the SUV). Remove with TEMPORARY_MODEL_3 when the owner says so.
    mapping[TEMPORARY_MODEL_3] = "sedan"
    return mapping


VEHICLE_CLASS_BY_MODEL = vehicle_class_by_model()


def class_for_model(value):
    """Return "sedan"/"suv" for an eligible model, else None."""
    return VEHICLE_CLASS_BY_MODEL.get(normalize_car_model(value))


def normalize_car_model(value):
    """Strip surrounding whitespace; matching is otherwise exact."""
    return (value or "").strip()


def validate_car_model(value):
    """Return (normalized_model, None) or (None, error_message)."""
    model = normalize_car_model(value)
    if not model:
        return None, "Please choose your car model from the list."
    if model not in ALLOWED_CAR_MODELS:
        return None, "That car model is not eligible. Please choose a model from the list."
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
