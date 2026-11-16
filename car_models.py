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
