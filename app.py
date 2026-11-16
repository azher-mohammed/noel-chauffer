"""Noel Chauffer — real booking system backend (Flask + SQLAlchemy).

TEST MODE ONLY for payments: no Stripe API call is ever made. Customer
messages are written to the owner-dashboard outbox only — this app never
sends SMS or email (no SMTP, no Twilio/SendGrid anywhere).

Run:  python app.py   (dev server on $PORT, default 5000)
Prod: gunicorn app:app

Env vars:
  DATABASE_URL    default sqlite:///noel.db in the project dir; postgres://
                  URLs are rewritten to postgresql:// for SQLAlchemy.
  ENCRYPTION_KEY  Fernet key for bank numbers; generated at startup (with a
                  loud warning) if unset — generated keys do not survive
                  restarts, so set this in production.
  OWNER_PIN       default "1234" (warning logged when the default is used).
  SECRET_KEY      Flask session key; generated at startup if unset.
  PORT            default 5000.
"""

from __future__ import annotations

import logging
import os
import secrets
import string
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote_plus

from cryptography.fernet import Fernet
from flask import Flask, Response, jsonify, request, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Numeric
from werkzeug.exceptions import HTTPException

import geo as geo_module
from car_models import (
    MIN_CAR_YEAR,
    allowed_models,
    class_for_model,
    max_car_year,
    validate_car_model,
    validate_car_year,
)
from flights import flight_info, normalize_flight_number
from payouts import completion_date, week_bounds, week_for
from pricing import (
    cancellation_refundable,
    class_label,
    compute_class_totals,
    compute_hourly,
    compute_one_way,
    free_waiting_minutes,
    is_airport_pickup,
    invoice_total,
    money,
    waiting_charge,
    waiting_time_elapsed,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("noel-chauffer")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- config ---

app = Flask(__name__, static_folder="static", static_url_path="/static")

database_url = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(BASE_DIR, "noel.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 5MB/file enforced per file below

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    log.warning("SECRET_KEY is not set; using a generated key (sessions will not survive restarts).")
app.config["SECRET_KEY"] = SECRET_KEY

OWNER_PIN = os.environ.get("OWNER_PIN", "1234")
if os.environ.get("OWNER_PIN") is None:
    log.warning("OWNER_PIN is not set; using default PIN 1234. Set OWNER_PIN in production.")

_encryption_key = os.environ.get("ENCRYPTION_KEY")
if _encryption_key:
    try:
        _fernet = Fernet(_encryption_key.encode())
    except Exception:
        log.warning("ENCRYPTION_KEY is invalid; generating an ephemeral key. Bank data will not survive restarts.")
        _fernet = Fernet(Fernet.generate_key())
else:
    log.warning(
        "!!! ENCRYPTION_KEY is not set — generated an ephemeral key. "
        "Stored bank numbers CANNOT be decrypted after a restart. "
        "Set ENCRYPTION_KEY to a persistent Fernet key in production. !!!"
    )
    _fernet = Fernet(Fernet.generate_key())

db = SQLAlchemy(app)

MAX_FILE_BYTES = 5 * 1024 * 1024
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "tlc_license",
    "fh1_insurance",
    "registration",
    "inspection",
    "vehicle_permit",
]
# multipart field name -> doc_type (profile_picture comes from profile_photo)
DOC_FIELD_MAP = {
    "doc_dmv_license": "dmv_license",
    "doc_tlc_license": "tlc_license",
    "doc_fh1": "fh1_insurance",
    "doc_registration": "registration",
    "doc_inspection": "inspection",
    "doc_vehicle_permit": "vehicle_permit",
}
# Booking lifecycle (payment BEFORE dispatch, decided 2026-11-16):
#   awaiting_payment -> offered -> accepted -> en_route -> arrived
#   -> in_progress -> completed | no_show | cancelled.
# The customer sees the single total from the moment the booking is
# created; driver details only once a driver has accepted. Unpaid
# bookings (awaiting_payment) never reach drivers.
DRIVER_VISIBLE_STATUSES = {"accepted", "en_route", "arrived", "in_progress", "completed"}
TRACKING_STATUSES = {"en_route", "arrived", "in_progress"}


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- models ---

class Driver(db.Model):
    __tablename__ = "drivers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(200), nullable=False, default="")
    car_model = db.Column(db.String(120), nullable=False)
    car_year = db.Column(db.Integer, nullable=True)  # nullable: drivers registered before the year field existed
    # Vehicle class derived from car_model at registration ("sedan" |
    # "suv", see car_models.class_for_model). Nullable: drivers
    # registered before the class system existed get it derived from
    # their car model on read (driver_vehicle_class below).
    vehicle_class = db.Column(db.String(10), nullable=True)
    car_colour = db.Column(db.String(60), nullable=False)
    plate = db.Column(db.String(40), nullable=False)
    profile_photo = db.Column(db.LargeBinary, nullable=True)
    profile_photo_mime = db.Column(db.String(60), nullable=True)
    available = db.Column(db.Boolean, nullable=False, default=False)
    bank_encrypted = db.Column(db.LargeBinary, nullable=True)
    bank_last4 = db.Column(db.String(4), nullable=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    documents = db.relationship("DriverDocument", backref="driver", cascade="all, delete-orphan")


class DriverDocument(db.Model):
    __tablename__ = "driver_documents"
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=False)
    doc_type = db.Column(db.String(40), nullable=False)
    file = db.Column(db.LargeBinary, nullable=False)
    mime = db.Column(db.String(60), nullable=False)
    original_name = db.Column(db.String(255), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (db.UniqueConstraint("driver_id", "doc_type"),)


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    pickup = db.Column(db.String(500), nullable=False)
    dropoff = db.Column(db.String(500), nullable=False, default="")
    pickup_lat = db.Column(db.Float, nullable=True)
    pickup_lng = db.Column(db.Float, nullable=True)
    dropoff_lat = db.Column(db.Float, nullable=True)
    dropoff_lng = db.Column(db.Float, nullable=True)
    miles = db.Column(Numeric(6, 1), nullable=True)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)   # HH:MM
    passengers = db.Column(db.Integer, nullable=False, default=1)
    ride_type = db.Column(db.String(20), nullable=False)  # one_way | hourly
    hours = db.Column(Numeric(5, 1), nullable=True)
    toll = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    referral_code_used = db.Column(db.String(40), nullable=True)
    # Optional flight number for airport rides, asked as a separate step
    # after the booking form; skippable, never blocks the booking. No
    # live flight tracking: the airline name is derived from the IATA
    # code in flights.py.
    flight_number = db.Column(db.String(20), nullable=True)
    # Vehicle class for one-way rides: "sedan" (Business Class, the
    # default the customer sees pre-selected) or "suv" (Business SUV).
    # Hourly rides have no class (None). Nullable: bookings created
    # before the class system existed read as "sedan" (see
    # booking_vehicle_class below).
    vehicle_class = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="offered")
    fare_total = db.Column(Numeric(10, 2), nullable=False)
    driver_earnings = db.Column(Numeric(10, 2), nullable=False)
    gratuity = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    booking_fee = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    # Fare (miles x class rate) and NYC sales tax (8.875% of the fare),
    # stored so the owner breakdown never has to recompute them.
    # Nullable: bookings created before the class/tax change read via
    # the recompute fallback in booking_fare/booking_tax below.
    fare = db.Column(Numeric(10, 2), nullable=True)
    tax = db.Column(Numeric(10, 2), nullable=True)
    waiting_minutes = db.Column(db.Integer, nullable=False, default=0)
    waiting_charge = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    accepted_driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=True)
    driver_lat = db.Column(db.Float, nullable=True)
    driver_lng = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    # Set when the driver completes the trip; the trip's payout week is
    # the 7-day week containing this timestamp's New York date.
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # True once the owner has marked this trip's payout week paid for its
    # driver. Per-booking (not per-week) so a trip completed late into
    # an already-paid week still shows as unpaid until marked again.
    payout_paid = db.Column(db.Boolean, nullable=False, default=False)

    accepted_driver = db.relationship("Driver", foreign_keys=[accepted_driver_id])
    payments = db.relationship("Payment", backref="booking", cascade="all, delete-orphan")
    events = db.relationship("BookingEvent", backref="booking", cascade="all, delete-orphan")


class BookingExclusion(db.Model):
    __tablename__ = "booking_exclusions"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=False)

    __table_args__ = (db.UniqueConstraint("booking_id", "driver_id"),)


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    amount = db.Column(Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # succeeded | refunded
    test = db.Column(db.Boolean, nullable=False, default=True)
    last4 = db.Column(db.String(4), nullable=True)
    stripe_test_id = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ReferralCode(db.Model):
    __tablename__ = "referral_codes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    issued_booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=True)
    used_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class OutboxMessage(db.Model):
    __tablename__ = "outbox_messages"
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(10), nullable=False)  # sms | email
    recipient = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class BookingEvent(db.Model):
    __tablename__ = "booking_events"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    type = db.Column(db.String(40), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


with app.app_context():
    db.create_all()
    # create_all() never alters an existing table, so add the
    # flight_number column to databases created before it existed
    # (e.g. the live database). Fresh databases already have it.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _cols = [c["name"] for c in _sa_inspect(db.engine).get_columns("bookings")]
        if "flight_number" not in _cols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE bookings ADD COLUMN flight_number VARCHAR(20)")
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("flight_number column check failed: %s", exc)
    # Same pattern for the driver car_year column (added with the
    # car-model dropdown, 2026-11-16). Nullable, so existing driver
    # rows keep working with no year on file.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _dcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("drivers")]
        if "car_year" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(_sa_text("ALTER TABLE drivers ADD COLUMN car_year INTEGER"))
    except Exception as exc:  # logged, never fatal at startup
        log.warning("car_year column check failed: %s", exc)
    # Same pattern for the vehicle-class / fare / tax columns (added
    # with the class + NYC-tax change, 2026-11-16). Nullable, so
    # existing rows keep working; the read helpers below derive the
    # values for rows that predate the columns.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _bcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("bookings")]
        _badds = {
            "vehicle_class": "ALTER TABLE bookings ADD COLUMN vehicle_class VARCHAR(10)",
            "fare": "ALTER TABLE bookings ADD COLUMN fare NUMERIC(10, 2)",
            "tax": "ALTER TABLE bookings ADD COLUMN tax NUMERIC(10, 2)",
        }
        for _name, _ddl in _badds.items():
            if _name not in _bcols:
                with db.engine.begin() as _conn:
                    _conn.execute(_sa_text(_ddl))
        _dcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("drivers")]
        if "vehicle_class" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE drivers ADD COLUMN vehicle_class VARCHAR(10)")
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("vehicle_class/fare/tax column check failed: %s", exc)

# --------------------------------------------------------------- helpers ---

def err(message, status=400):
    return jsonify({"error": message}), status


def num(value):
    """Decimal/float -> JSON number (float), preserving None."""
    if value is None:
        return None
    return float(value)


def iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def generate_referral_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "NOEL-" + "".join(secrets.choice(alphabet) for _ in range(6))
        if not ReferralCode.query.filter_by(code=code).first():
            return code


def add_event(booking_id, event_type, message):
    db.session.add(BookingEvent(booking_id=booking_id, type=event_type, message=message))


def add_outbox(channel, recipient, body, booking_id=None):
    db.session.add(OutboxMessage(channel=channel, recipient=recipient, body=body, booking_id=booking_id))


def outbox_to_customer(booking, sms_body, email_body=None):
    add_outbox("sms", booking.phone, sms_body, booking.id)
    add_outbox("email", booking.email, email_body or sms_body, booking.id)


def route_url_for(booking):
    if booking.dropoff:
        return (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={quote_plus(booking.pickup)}"
            f"&destination={quote_plus(booking.dropoff)}"
        )
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(booking.pickup)


def waze_url_for(booking):
    # Waze navigates to a single destination from the driver's current
    # location: the dropoff when there is one, else the pickup.
    dest = booking.dropoff or booking.pickup
    return "https://waze.com/ul?q=" + quote_plus(dest) + "&navigate=yes"


def driver_docs_status(driver):
    present = {d.doc_type for d in driver.documents}
    status = {}
    for doc_type in DOC_TYPES:
        if doc_type == "profile_picture":
            status[doc_type] = "completed" if driver.profile_photo else "missing"
        else:
            status[doc_type] = "completed" if doc_type in present else "missing"
    return status


def bank_masked(driver):
    if driver.bank_last4:
        return "••••" + driver.bank_last4
    return ""


def encrypt_bank(account_number, routing_number):
    payload = f"{account_number}|{routing_number}".encode()
    return _fernet.encrypt(payload)


def require_driver():
    token = request.headers.get("X-Driver-Token")
    if not token:
        return None, err("Missing X-Driver-Token header.", 401)
    driver = Driver.query.filter_by(token=token).first()
    if not driver:
        return None, err("Invalid driver token.", 401)
    return driver, None


def require_owner():
    if not session.get("owner"):
        return err("Owner login required.", 401)
    return None


def driver_vehicle_class(driver):
    """A driver's vehicle class: stored at registration, or derived
    from the car model for drivers registered before the class system
    existed. Always "sedan" or "suv" for a validated car model."""
    if driver.vehicle_class in ("sedan", "suv"):
        return driver.vehicle_class
    derived = class_for_model(driver.car_model)
    return derived or "sedan"


def booking_vehicle_class(booking):
    """A booking's vehicle class: None for hourly rides; "sedan" for
    one-way bookings created before the class system existed."""
    if booking.ride_type == "hourly":
        return None
    return booking.vehicle_class if booking.vehicle_class in ("sedan", "suv") else "sedan"


def _recomputed_breakdown(booking):
    """Pricing breakdown recomputed from miles/hours + toll + class.

    Read-only fallback for rows created before fare/tax were stored.
    """
    if booking.ride_type == "hourly":
        return compute_hourly(booking.hours or Decimal("0"))
    return compute_one_way(
        booking.miles or Decimal("0"),
        toll=booking.toll or Decimal("0"),
        vehicle_class=booking_vehicle_class(booking),
        referral=bool(booking.referral_code_used),
    )


def booking_fare(booking):
    if booking.fare is not None:
        return money(booking.fare)
    return _recomputed_breakdown(booking)["fare"]


def booking_tax(booking):
    if booking.tax is not None:
        return money(booking.tax)
    return _recomputed_breakdown(booking)["tax"]


def booking_profit(booking):
    # Owner profit per ride: total + waiting - driver pay - tax.
    # Tax is pass-through, so it never counts as profit.
    return (money(booking.fare_total) + money(booking.waiting_charge)
            - money(booking.driver_earnings) - booking_tax(booking))


# ---------------------------------------------------------- payout weeks ---

def _refunded_booking_ids():
    return {p.booking_id for p in Payment.query.filter_by(status="refunded").all()}


def _payout_eligible(bookings, refunded_ids=None):
    """Completed, non-refunded bookings: the only trips that count toward
    a payout week. A trip counts only once it is completed."""
    if refunded_ids is None:
        refunded_ids = _refunded_booking_ids()
    return [b for b in bookings if b.status == "completed" and b.id not in refunded_ids]


def _booking_week(booking):
    """The payout week dict for a booking, from its completion date."""
    return week_for(completion_date(booking.completed_at, booking.created_at))


def _week_summary(week, bookings):
    """JSON summary for one payout week. `bookings` are that week's
    eligible trips. A week is paid only when it has trips and every
    one of them has been marked paid."""
    total = sum((money(b.driver_earnings) for b in bookings), Decimal("0.00"))
    paid = bool(bookings) and all(b.payout_paid for b in bookings)
    return {
        "index": week["index"],
        "start": week["start"].isoformat(),
        "end": week["end"].isoformat(),
        "due_date": week["due_date"].isoformat(),
        "ride_count": len(bookings),
        "total_earnings": num(total),
        "paid": paid,
        "status": "paid" if paid else "unpaid",
    }


def _group_payout_weeks(bookings):
    """Group eligible bookings into payout weeks, newest week first.

    Returns a list of (week_summary, member_bookings) pairs.
    """
    groups = {}
    for b in bookings:
        w = _booking_week(b)
        groups.setdefault(w["index"], (w, []))[1].append(b)
    result = []
    for index in sorted(groups, reverse=True):
        w, members = groups[index]
        result.append((_week_summary(w, members), members))
    return result


def recompute_booking_fare(booking):
    """Recompute fare/driver/gratuity/tax/fee from miles/hours +
    current toll + vehicle class.

    Referral codes are accepted but give a $0 discount for now (the
    old $20-fee waiver no longer applies; a new benefit is TBD).
    """
    if booking.ride_type == "hourly":
        result = compute_hourly(booking.hours or Decimal("0"))
        booking.vehicle_class = None
    else:
        result = compute_one_way(
            booking.miles or Decimal("0"),
            toll=booking.toll or Decimal("0"),
            vehicle_class=booking_vehicle_class(booking),
            referral=bool(booking.referral_code_used),
        )
        booking.vehicle_class = result["vehicle_class"]
    booking.fare_total = result["total"]
    booking.driver_earnings = result["driver_earnings"]
    booking.gratuity = result["gratuity"]
    booking.booking_fee = result["booking_fee"]
    booking.fare = result["fare"]
    booking.tax = result["tax"]
    return result


@app.errorhandler(HTTPException)
def _http_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": e.description}), e.code
    return e


# ------------------------------------------------------------ page routes ---

def _serve_page(filename, label):
    path = os.path.join(app.static_folder, filename)
    if os.path.exists(path):
        return send_from_directory(app.static_folder, filename)
    return (
        f"<html><body><h1>Noel Chauffer</h1>"
        f"<p>The {label} page is not built yet. The backend API is running.</p>"
        f"</body></html>",
        200,
    )


@app.route("/")
def home():
    return _serve_page("index.html", "customer booking")


@app.route("/driver")
def driver_page():
    return _serve_page("driver.html", "driver app")


@app.route("/owner")
def owner_page():
    return _serve_page("owner.html", "owner dashboard")


# ------------------------------------------------------- place search ------

@app.route("/api/places/search", methods=["GET"])
def place_search():
    """USA-only address suggestions for the booking form (no API key).

    Always 200: an empty query, bad input, or an upstream failure all
    return an empty results list, so the form keeps working as plain
    text. Results carry address text + coordinates only: no fare,
    miles, or any pricing data.
    """
    try:
        q = (request.args.get("q") or "").strip()[:200]
        try:
            limit = int(request.args.get("limit", "5"))
        except (TypeError, ValueError):
            limit = 5
        results = geo_module.search_places(q, limit) if q else []
        return jsonify({"results": results})
    except Exception as exc:  # autocomplete must never break the page
        log.warning("place search endpoint failed: %s", exc)
        return jsonify({"results": []})


# ------------------------------------------------------- customer booking ---

def _booking_create_view(booking, referral_code=None):
    """The booking shape returned on create and on class selection:
    single total (+ both class totals for the options page on one-way
    rides), never a breakdown, never miles or rates."""
    view = {
        "id": booking.id,
        "status": booking.status,
        "total": num(booking.fare_total),
        "pickup": booking.pickup,
        "dropoff": booking.dropoff,
        "date": booking.date,
        "time": booking.time,
        "ride_type": booking.ride_type,
        "hours": num(booking.hours),
        "vehicle_class": booking_vehicle_class(booking),
        "vehicle_class_label": class_label(booking_vehicle_class(booking)),
        **flight_info(booking.flight_number, booking.pickup, booking.dropoff),
    }
    if booking.ride_type == "one_way":
        totals = compute_class_totals(
            booking.miles or Decimal("0"), toll=booking.toll or Decimal("0"))
        view["class_totals"] = {k: num(v) for k, v in totals.items()}
    if referral_code is not None:
        view["referral_code"] = referral_code
    return view


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    data = request.get_json(silent=True) or {}
    required = ["customer_name", "phone", "email", "pickup", "date", "time", "ride_type"]
    for field in required:
        if not data.get(field):
            return err(f"Missing required field: {field}.")
    ride_type = data["ride_type"]
    if ride_type not in ("one_way", "hourly"):
        return err("ride_type must be one_way or hourly.")
    try:
        datetime.strptime(data["date"], "%Y-%m-%d")
        datetime.strptime(data["time"], "%H:%M")
    except ValueError:
        return err("date must be YYYY-MM-DD and time must be HH:MM.")

    referral_code_used = (data.get("referral_code") or "").strip() or None
    referral_valid = False
    referral_row = None
    if referral_code_used:
        referral_row = ReferralCode.query.filter_by(code=referral_code_used).first()
        if not referral_row:
            return err("Invalid referral code.")
        referral_valid = True

    # Optional, skippable: an unparseable value stores as None and the
    # booking still goes through.
    flight_number = normalize_flight_number(data.get("flight_number"))

    booking = Booking(
        customer_name=data["customer_name"],
        phone=data["phone"],
        email=data["email"],
        pickup=data["pickup"],
        dropoff=data.get("dropoff") or "",
        date=data["date"],
        time=data["time"],
        passengers=int(data.get("passengers") or 1),
        ride_type=ride_type,
        toll=Decimal("0.00"),
        referral_code_used=referral_code_used,
        flight_number=flight_number,
        status="awaiting_payment",
    )

    if ride_type == "hourly":
        hours = data.get("hours")
        if hours is None:
            return err("hours is required for hourly rides.")
        try:
            hours_dec = Decimal(str(hours))
        except Exception:
            return err("hours must be a number.")
        if hours_dec <= 0:
            return err("hours must be greater than 0.")
        booking.hours = hours_dec
        booking.miles = None
        booking.vehicle_class = None
        result = compute_hourly(hours_dec)
    else:
        if not booking.dropoff:
            return err("dropoff is required for one-way rides.")
        miles, pickup_coords, dropoff_coords = geo_module.distance_miles(booking.pickup, booking.dropoff)
        booking.miles = Decimal(str(miles))
        if pickup_coords:
            booking.pickup_lat, booking.pickup_lng = pickup_coords
        if dropoff_coords:
            booking.dropoff_lat, booking.dropoff_lng = dropoff_coords
        # Default class is sedan (Business Class, pre-selected on the
        # options page); the customer may switch to SUV before paying.
        booking.vehicle_class = "sedan"
        result = compute_one_way(booking.miles, toll=Decimal("0.00"),
                                 vehicle_class="sedan", referral=referral_valid)

    booking.fare_total = result["total"]
    booking.driver_earnings = result["driver_earnings"]
    booking.gratuity = result["gratuity"]
    booking.booking_fee = result["booking_fee"]
    booking.fare = result["fare"]
    booking.tax = result["tax"]

    db.session.add(booking)
    db.session.flush()  # booking.id needed for the referral code + outbox

    if referral_row is not None:
        referral_row.used_count += 1

    new_code = generate_referral_code()
    db.session.add(ReferralCode(code=new_code, issued_booking_id=booking.id))

    route_text = f"{booking.pickup} to {booking.dropoff}" if booking.dropoff else booking.pickup
    outbox_to_customer(
        booking,
        f"Noel Chauffer: booking received for {booking.date} at {booking.time}, {route_text}. "
        f"Your total is ${booking.fare_total}. Complete your card payment to confirm "
        "your ride — your chauffeur will be assigned right after payment, and we "
        "will message you the chauffeur's details once a driver accepts.",
    )
    add_event(booking.id, "booking_received",
              f"New booking #{booking.id}: {route_text} on {booking.date} at {booking.time} "
              f"({booking.customer_name}, {booking.phone}).")
    db.session.commit()

    return jsonify({"booking": _booking_create_view(booking, referral_code=new_code)}), 201


@app.route("/api/bookings/<int:booking_id>/vehicle-class", methods=["POST"])
def select_vehicle_class(booking_id):
    """The customer picks a class on the options page ("Choose your
    experience") before paying. Only while the booking is still
    awaiting payment and only for one-way rides: after payment the
    booking is already with drivers and its class is fixed."""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.ride_type != "one_way":
        return err("Hourly rides have no vehicle class.", 409)
    if booking.status != "awaiting_payment":
        return err("The vehicle class can only be changed before payment.", 409)
    data = request.get_json(silent=True) or {}
    vehicle_class = data.get("vehicle_class")
    if vehicle_class not in ("sedan", "suv"):
        return err("vehicle_class must be sedan or suv.")
    booking.vehicle_class = vehicle_class
    recompute_booking_fare(booking)
    add_event(booking.id, "class_selected",
              f"Customer selected {class_label(vehicle_class)} for booking "
              f"#{booking.id} (total ${booking.fare_total}).")
    db.session.commit()
    return jsonify({"booking": _booking_create_view(booking)})


@app.route("/api/bookings/<int:booking_id>", methods=["GET"])
def get_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    driver = booking.accepted_driver if booking.status in DRIVER_VISIBLE_STATUSES else None
    referral = ReferralCode.query.filter_by(issued_booking_id=booking.id).first()
    tracking_visible = booking.status in TRACKING_STATUSES
    invoice = None
    if booking.status == "completed":
        invoice = {
            "total": num(invoice_total(booking.fare_total, booking.waiting_charge)),
            "waiting_charge": num(booking.waiting_charge),
        }
    view = {
        "id": booking.id,
        "status": booking.status,
        "pickup": booking.pickup,
        "dropoff": booking.dropoff,
        "date": booking.date,
        "time": booking.time,
        "ride_type": booking.ride_type,
        "hours": num(booking.hours),
        "vehicle_class": booking_vehicle_class(booking),
        "vehicle_class_label": class_label(booking_vehicle_class(booking)),
        **flight_info(booking.flight_number, booking.pickup, booking.dropoff),
        "driver": None if driver is None else {
            "name": driver.name,
            "phone": driver.phone,
            "car_model": driver.car_model,
            "car_year": driver.car_year,
            "car_colour": driver.car_colour,
            "plate": driver.plate,
            "photo_url": f"/api/bookings/{booking.id}/driver-photo",
        },
        "total": num(booking.fare_total),
        "tracking": {
            "visible": tracking_visible,
            "lat": booking.driver_lat if tracking_visible else None,
            "lng": booking.driver_lng if tracking_visible else None,
        },
        "invoice": invoice,
        "referral_code": referral.code if referral else None,
    }
    if booking.ride_type == "one_way":
        totals = compute_class_totals(
            booking.miles or Decimal("0"), toll=booking.toll or Decimal("0"))
        view["class_totals"] = {k: num(v) for k, v in totals.items()}
    return jsonify({"booking": view})


@app.route("/api/bookings/<int:booking_id>/pay", methods=["POST"])
def pay_booking(booking_id):
    """Card payment BEFORE dispatch: the customer picks a class on the
    options page, sees the single total for that class, and pays; only
    then is the booking sent to drivers (status awaiting_payment ->
    offered)."""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.status != "awaiting_payment":
        return err("Payment is taken before the booking is sent to drivers.", 409)
    data = request.get_json(silent=True) or {}
    for field in ("card_number", "card_exp", "card_cvc", "card_name"):
        if not data.get(field):
            return err(f"Missing required field: {field}.")
    digits = "".join(ch for ch in str(data["card_number"]) if ch.isdigit())
    if not (12 <= len(digits) <= 19):
        return err("Invalid card number.")
    # TEST MODE ONLY: no Stripe API call is ever made. Only the last 4
    # digits are stored; the card number itself is never persisted.
    payment = Payment(
        booking_id=booking.id,
        amount=booking.fare_total,
        status="succeeded",
        test=True,
        last4=digits[-4:],
        stripe_test_id="pi_test_" + secrets.token_hex(8),
    )
    db.session.add(payment)
    booking.status = "offered"
    add_event(booking.id, "payment_received",
              f"Test payment of ${booking.fare_total} received for booking #{booking.id} "
              f"(card ending {digits[-4:]}). Booking sent to drivers.")
    db.session.commit()
    return jsonify({"payment": {
        "id": payment.id,
        "amount": num(payment.amount),
        "status": payment.status,
        "test": True,
        "last4": payment.last4,
    }, "booking": {"status": booking.status}})


@app.route("/api/bookings/<int:booking_id>/cancel", methods=["POST"])
def cancel_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    data = request.get_json(silent=True) or {}
    if not data.get("phone") or str(data["phone"]) != str(booking.phone):
        return err("Phone number does not match this booking.", 403)
    if booking.status in ("cancelled", "completed", "no_show"):
        return err(f"Booking is already {booking.status}.", 409)
    refundable = cancellation_refundable(booking.date, booking.time)
    payment = Payment.query.filter_by(booking_id=booking.id, status="succeeded").order_by(Payment.id.desc()).first()
    refund = False
    charge_kept = False
    if payment is not None:
        if refundable:
            payment.status = "refunded"
            refund = True
        else:
            charge_kept = True
    booking.status = "cancelled"
    add_event(booking.id, "customer_cancelled",
              f"Booking #{booking.id} cancelled by customer. "
              f"{'Payment refunded (test mode).' if refund else 'Full price kept.' if charge_kept else 'No payment had been taken.'}")
    db.session.commit()
    return jsonify({"booking": {"status": "cancelled"}, "refund": refund, "charge_kept": charge_kept})


@app.route("/api/bookings", methods=["GET"])
def booking_history():
    phone = request.args.get("phone")
    if not phone:
        return err("phone query parameter is required.")
    bookings = (Booking.query.filter_by(phone=phone)
                .order_by(Booking.created_at.desc(), Booking.id.desc()).all())
    return jsonify([{
        "id": b.id,
        "pickup": b.pickup,
        "dropoff": b.dropoff,
        "date": b.date,
        "time": b.time,
        "status": b.status,
        "total": num(b.fare_total),
    } for b in bookings])


@app.route("/api/bookings/<int:booking_id>/driver-photo", methods=["GET"])
def booking_driver_photo(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking or not booking.accepted_driver_id:
        return err("No driver assigned to this booking.", 404)
    driver = booking.accepted_driver
    if not driver or not driver.profile_photo:
        return err("Driver photo not available.", 404)
    return Response(driver.profile_photo, mimetype=driver.profile_photo_mime or "image/jpeg")


# ---------------------------------------------------------------- drivers ---

def _validate_upload(storage, allowed_exts, field_name):
    """Return (bytes, mime, original_name) or an error response tuple."""
    data = storage.read()
    if len(data) > MAX_FILE_BYTES:
        return None, err(f"{field_name} exceeds the 5MB limit.")
    if len(data) == 0:
        return None, err(f"{field_name} is empty.")
    filename = storage.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_exts:
        return None, err(f"{field_name} must be one of: {', '.join(sorted(allowed_exts))}.")
    return (data, storage.mimetype or "application/octet-stream", filename), None


@app.route("/api/car-models", methods=["GET"])
def car_models():
    """Eligible car models for the driver registration dropdown.

    One list, served from car_models.py (the transcribed Uber Black
    list + the temporary Model 3 owner-trial exception). The driver
    app fetches this; the server validates against the same set.
    """
    return jsonify({
        "models": allowed_models(),
        "min_year": MIN_CAR_YEAR,
        "max_year": max_car_year(),
    })


@app.route("/api/drivers/register", methods=["POST"])
def register_driver():
    form = request.form
    for field in ("name", "phone", "car_model", "car_year", "car_colour", "plate",
                  "bank_account_number", "bank_routing_number"):
        if not (form.get(field) or "").strip():
            return err(f"Missing required field: {field}.")
    phone = form["phone"].strip()
    if Driver.query.filter_by(phone=phone).first():
        return err("A driver with this phone number is already registered.", 409)

    # Car model must come from the eligible list (dropdown), and the
    # model year must be 2022 or newer (owner decision 2026-11-16).
    car_model, model_error = validate_car_model(form.get("car_model"))
    if model_error:
        return err(model_error)
    car_year, year_error = validate_car_year(form.get("car_year"))
    if year_error:
        return err(year_error)

    # Validate all uploaded files before creating anything.
    profile_photo = None
    if "profile_photo" in request.files and request.files["profile_photo"].filename:
        profile_photo, error = _validate_upload(request.files["profile_photo"], IMAGE_EXTS, "profile_photo")
        if error:
            return error
    docs = {}
    for field_name, doc_type in DOC_FIELD_MAP.items():
        storage = request.files.get(field_name)
        if storage and storage.filename:
            allowed = IMAGE_EXTS | {".pdf"} if doc_type == "fh1_insurance" else IMAGE_EXTS
            parsed, error = _validate_upload(storage, allowed, field_name)
            if error:
                return error
            docs[doc_type] = parsed

    account = form["bank_account_number"].strip()
    routing = form["bank_routing_number"].strip()
    driver = Driver(
        name=form["name"].strip(),
        phone=phone,
        email=(form.get("email") or "").strip(),
        car_model=car_model,
        car_year=car_year,
        # Vehicle class is derived from the car model, never typed in.
        vehicle_class=class_for_model(car_model),
        car_colour=form["car_colour"].strip(),
        plate=form["plate"].strip(),
        profile_photo=profile_photo[0] if profile_photo else None,
        profile_photo_mime=profile_photo[1] if profile_photo else None,
        available=False,
        bank_encrypted=encrypt_bank(account, routing),
        bank_last4=account[-4:],
        token=uuid.uuid4().hex,
    )
    db.session.add(driver)
    db.session.flush()
    for doc_type, (data, mime, original_name) in docs.items():
        db.session.add(DriverDocument(
            driver_id=driver.id, doc_type=doc_type, file=data,
            mime=mime, original_name=original_name))
    db.session.commit()
    return jsonify({"driver": {
        "id": driver.id,
        "name": driver.name,
        "phone": driver.phone,
        "email": driver.email,
        "car_model": driver.car_model,
        "car_year": driver.car_year,
        "vehicle_class": driver_vehicle_class(driver),
        "vehicle_class_label": class_label(driver_vehicle_class(driver)),
        "car_colour": driver.car_colour,
        "plate": driver.plate,
        "docs": driver_docs_status(driver),
        "bank_masked": bank_masked(driver),
    }, "token": driver.token}), 201


@app.route("/api/drivers/me", methods=["GET"])
def driver_me():
    driver, error = require_driver()
    if error:
        return error
    return jsonify({"driver": {
        "id": driver.id,
        "name": driver.name,
        "phone": driver.phone,
        "email": driver.email,
        "car_model": driver.car_model,
        "car_year": driver.car_year,
        "vehicle_class": driver_vehicle_class(driver),
        "vehicle_class_label": class_label(driver_vehicle_class(driver)),
        "car_colour": driver.car_colour,
        "plate": driver.plate,
        "docs": driver_docs_status(driver),
        "bank_masked": bank_masked(driver),
        "available": driver.available,
    }})


@app.route("/api/drivers/me/lookup", methods=["POST"])
def driver_lookup():
    data = request.get_json(silent=True) or {}
    if not data.get("phone"):
        return err("phone is required.")
    driver = Driver.query.filter_by(phone=str(data["phone"])).first()
    if not driver:
        return err("No driver found with that phone number.", 404)
    driver.token = uuid.uuid4().hex  # re-issue token (trial only)
    db.session.commit()
    return jsonify({"driver": {"id": driver.id, "name": driver.name}, "token": driver.token})


@app.route("/api/drivers/me/active-trip", methods=["GET"])
def driver_active_trip():
    """The driver's currently assigned non-terminal booking, or null.

    Lets the driver app restore the trip screen after a reload. Same
    booking shape as the accept response, plus the booking status.
    Driver sees earnings only — never miles, fare, or total.
    """
    driver, error = require_driver()
    if error:
        return error
    booking = (Booking.query
               .filter(Booking.accepted_driver_id == driver.id,
                       Booking.status.in_(("accepted", "en_route", "arrived", "in_progress")))
               .order_by(Booking.created_at.desc(), Booking.id.desc())
               .first())
    if not booking:
        return jsonify({"booking": None})
    return jsonify({"booking": {
        "id": booking.id,
        "pickup": booking.pickup,
        "dropoff": booking.dropoff,
        "date": booking.date,
        "time": booking.time,
        "ride_type": booking.ride_type,
        "hours": num(booking.hours),
        "vehicle_class": booking_vehicle_class(booking),
        "vehicle_class_label": class_label(booking_vehicle_class(booking)),
        "customer_name": booking.customer_name,
        "customer_phone": booking.phone,
        "earnings": num(booking.driver_earnings),
        "route_url": route_url_for(booking),
        "route_waze_url": waze_url_for(booking),
        "free_waiting_minutes": free_waiting_minutes(booking.pickup),
        "airport_pickup": is_airport_pickup(booking.pickup),
        "status": booking.status,
        **flight_info(booking.flight_number, booking.pickup, booking.dropoff),
    }})


@app.route("/api/drivers/me/availability", methods=["POST"])
def driver_availability():
    driver, error = require_driver()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    if "available" not in data:
        return err("available is required.")
    driver.available = bool(data["available"])
    db.session.commit()
    return jsonify({"available": driver.available})


@app.route("/api/drivers/me/offers", methods=["GET"])
def driver_offers():
    driver, error = require_driver()
    if error:
        return error
    if not driver.available:
        return jsonify([])
    excluded_ids = [e.booking_id for e in BookingExclusion.query.filter_by(driver_id=driver.id).all()]
    # Only PAID bookings reach drivers: status "offered" means payment
    # succeeded. Unpaid bookings (awaiting_payment) never appear here.
    # Class filtering: one-way bookings reach only drivers whose car
    # class matches the booking's class; hourly rides (no class) reach
    # every available driver.
    driver_class = driver_vehicle_class(driver)
    query = Booking.query.filter_by(status="offered").order_by(Booking.created_at, Booking.id)
    if excluded_ids:
        query = query.filter(~Booking.id.in_(excluded_ids))
    offers = []
    for b in query.all():
        if b.ride_type == "one_way" and booking_vehicle_class(b) != driver_class:
            continue
        # Driver sees ONLY his own earnings — never miles, fare, total,
        # gratuity, tax, or the booking fee.
        offers.append({
            "booking_id": b.id,
            "pickup": b.pickup,
            "dropoff": b.dropoff,
            "date": b.date,
            "time": b.time,
            "ride_type": b.ride_type,
            "hours": num(b.hours),
            "vehicle_class": booking_vehicle_class(b),
            "vehicle_class_label": class_label(booking_vehicle_class(b)),
            "earnings": num(b.driver_earnings),
            "route_url": route_url_for(b),
            "route_waze_url": waze_url_for(b),
        })
    return jsonify(offers)


@app.route("/api/drivers/me/offers/<int:booking_id>/accept", methods=["POST"])
def driver_accept(booking_id):
    driver, error = require_driver()
    if error:
        return error
    if BookingExclusion.query.filter_by(booking_id=booking_id, driver_id=driver.id).first():
        return err("You have declined this booking.", 409)
    # Class match is enforced here too, so a driver can never accept a
    # booking of the other class even by calling this endpoint directly.
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if (booking.ride_type == "one_way"
            and booking_vehicle_class(booking) != driver_vehicle_class(driver)):
        return err("This ride is for a different vehicle class.", 409)
    # Atomic first-accept-wins: only one driver can flip offered -> accepted.
    rows = (db.session.query(Booking)
            .filter(Booking.id == booking_id, Booking.status == "offered")
            .update({"status": "accepted", "accepted_driver_id": driver.id},
                    synchronize_session=False))
    if rows == 0:
        db.session.rollback()
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return err("Booking not found.", 404)
        return err("This booking has already been taken.", 409)
    db.session.commit()
    booking = db.session.get(Booking, booking_id)
    outbox_to_customer(
        booking,
        f"Noel Chauffer: your chauffeur is {driver.name} ({driver.phone}), "
        f"{driver.car_model} ({driver.car_colour}), plate {driver.plate}. "
        f"Your ride total is ${booking.fare_total}. Pickup {booking.date} at {booking.time} from {booking.pickup}.",
    )
    add_event(booking.id, "driver_accepted",
              f"Driver {driver.name} accepted booking #{booking.id}.")
    db.session.commit()
    return jsonify({"booking": {
        "id": booking.id,
        "pickup": booking.pickup,
        "dropoff": booking.dropoff,
        "date": booking.date,
        "time": booking.time,
        "ride_type": booking.ride_type,
        "vehicle_class": booking_vehicle_class(booking),
        "vehicle_class_label": class_label(booking_vehicle_class(booking)),
        "customer_name": booking.customer_name,
        "customer_phone": booking.phone,
        "earnings": num(booking.driver_earnings),
        "route_url": route_url_for(booking),
        "route_waze_url": waze_url_for(booking),
        "free_waiting_minutes": free_waiting_minutes(booking.pickup),
        "airport_pickup": is_airport_pickup(booking.pickup),
        "status": booking.status,
        **flight_info(booking.flight_number, booking.pickup, booking.dropoff),
    }})


@app.route("/api/drivers/me/offers/<int:booking_id>/decline", methods=["POST"])
def driver_decline(booking_id):
    driver, error = require_driver()
    if error:
        return error
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if not BookingExclusion.query.filter_by(booking_id=booking_id, driver_id=driver.id).first():
        db.session.add(BookingExclusion(booking_id=booking_id, driver_id=driver.id))
        db.session.commit()
    return jsonify({"excluded": True, "booking_id": booking_id})


@app.route("/api/drivers/me/trip/<int:booking_id>/event", methods=["POST"])
def driver_trip_event(booking_id):
    driver, error = require_driver()
    if error:
        return error
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.accepted_driver_id != driver.id:
        return err("This booking is not assigned to you.", 403)
    data = request.get_json(silent=True) or {}
    event = data.get("event")
    if event not in ("en_route", "arrived", "start", "complete", "cancel", "no_show"):
        return err("Unknown event.")
    if data.get("lat") is not None and data.get("lng") is not None:
        booking.driver_lat = float(data["lat"])
        booking.driver_lng = float(data["lng"])

    response_extra = {}
    if event == "en_route":
        if booking.status != "accepted":
            return err("The driver heads to pickup only after accepting the booking.", 409)
        booking.status = "en_route"
        add_event(booking.id, "trip_en_route", f"Driver {driver.name} is on the way to pickup for booking #{booking.id}.")
    elif event == "arrived":
        if booking.status != "en_route":
            return err("Cannot mark arrived before heading to pickup.", 409)
        booking.status = "arrived"
        add_event(booking.id, "trip_arrived", f"Driver {driver.name} arrived at pickup for booking #{booking.id}.")
    elif event == "start":
        if booking.status != "arrived":
            return err("Cannot start the ride before arriving at pickup.", 409)
        booking.status = "in_progress"
        add_event(booking.id, "trip_started", f"Ride started for booking #{booking.id}.")
    elif event == "complete":
        if booking.status not in ("in_progress", "arrived"):
            return err("Cannot complete a ride that has not started.", 409)
        waiting_minutes = int(data.get("waiting_minutes") or 0)
        booking.waiting_minutes = max(0, waiting_minutes)
        booking.waiting_charge = waiting_charge(booking.pickup, booking.waiting_minutes)
        booking.status = "completed"
        booking.completed_at = utcnow()
        total = invoice_total(booking.fare_total, booking.waiting_charge)
        outbox_to_customer(
            booking,
            f"Noel Chauffer: thank you for riding with us. Your invoice total is ${total} "
            f"(including ${booking.waiting_charge} waiting charge).",
        )
        add_event(booking.id, "trip_completed",
                  f"Booking #{booking.id} completed. Invoice total ${total} "
                  f"(fare ${booking.fare_total} + waiting ${booking.waiting_charge}).")
        response_extra["invoice"] = {"total": num(total), "waiting_charge": num(booking.waiting_charge)}
    elif event == "cancel":
        if booking.status not in ("accepted", "en_route", "arrived"):
            return err("Cannot cancel a ride in this state.", 409)
        booking.status = "offered"
        booking.accepted_driver_id = None
        booking.driver_lat = None
        booking.driver_lng = None
        if not BookingExclusion.query.filter_by(booking_id=booking_id, driver_id=driver.id).first():
            db.session.add(BookingExclusion(booking_id=booking_id, driver_id=driver.id))
        # Payment was taken before dispatch, so it is kept; the booking
        # goes back to the other drivers automatically.
        add_event(booking.id, "driver_cancelled",
                  f"Driver {driver.name} cancelled booking #{booking.id}; sent back to other drivers. Payment kept.")
    elif event == "no_show":
        if booking.status not in ("en_route", "arrived"):
            return err("No-show can only be marked while heading to or at pickup.", 409)
        if not waiting_time_elapsed(booking.date, booking.time, booking.pickup):
            return err("The free waiting time has not finished yet. "
                       "The driver must wait the full waiting time before "
                       "marking a customer no-show.", 409)
        booking.status = "no_show"
        add_event(booking.id, "no_show",
                  f"Customer no-show for booking #{booking.id}. Full price kept.")
    db.session.commit()
    payload = {"booking": {"id": booking.id, "status": booking.status}}
    payload.update(response_extra)
    return jsonify(payload)


@app.route("/api/drivers/me/trip/<int:booking_id>/location", methods=["POST"])
def driver_location(booking_id):
    driver, error = require_driver()
    if error:
        return error
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.accepted_driver_id != driver.id:
        return err("This booking is not assigned to you.", 403)
    if booking.status not in TRACKING_STATUSES:
        return err("Location updates are only accepted while the trip is active.", 409)
    data = request.get_json(silent=True) or {}
    if data.get("lat") is None or data.get("lng") is None:
        return err("lat and lng are required.")
    booking.driver_lat = float(data["lat"])
    booking.driver_lng = float(data["lng"])
    db.session.commit()
    return jsonify({"lat": booking.driver_lat, "lng": booking.driver_lng})


@app.route("/api/drivers/me/earnings", methods=["GET"])
def driver_earnings():
    driver, error = require_driver()
    if error:
        return error
    rides = (Booking.query.filter_by(accepted_driver_id=driver.id, status="completed")
             .order_by(Booking.created_at.desc(), Booking.id.desc()).all())
    # Only completed, non-refunded trips count toward earnings and payout
    # weeks. Earnings amounts only — never miles, fares, or totals.
    eligible = _payout_eligible(rides)
    total = sum((money(b.driver_earnings) for b in eligible), Decimal("0.00"))
    weeks = [summary for summary, _ in _group_payout_weeks(eligible)]
    ride_rows = []
    for b in eligible:
        w = _booking_week(b)
        ride_rows.append({
            "id": b.id,
            "date": b.date,
            "route": f"{b.pickup} to {b.dropoff}" if b.dropoff else b.pickup,
            "vehicle_class": booking_vehicle_class(b),
            "vehicle_class_label": class_label(booking_vehicle_class(b)),
            "earnings": num(b.driver_earnings),
            "completed_date": completion_date(b.completed_at, b.created_at).isoformat(),
            "week_start": w["start"].isoformat(),
            "week_end": w["end"].isoformat(),
            "due_date": w["due_date"].isoformat(),
            "payout_paid": bool(b.payout_paid),
            "payout_status": "paid" if b.payout_paid else "unpaid",
        })
    return jsonify({
        "completed_rides": len(eligible),
        "total_earnings": num(total),
        "weeks": weeks,
        "rides": ride_rows,
    })


# ------------------------------------------------------------------ owner ---

@app.route("/api/owner/login", methods=["POST"])
def owner_login():
    data = request.get_json(silent=True) or {}
    if str(data.get("pin")) != OWNER_PIN:
        return err("Wrong PIN.", 401)
    session["owner"] = True
    return jsonify({"ok": True})


@app.route("/api/owner/logout", methods=["POST"])
def owner_logout():
    session.pop("owner", None)
    return jsonify({"ok": True})


@app.route("/api/owner/summary", methods=["GET"])
def owner_summary():
    error = require_owner()
    if error:
        return error
    # Gross counts rides whose test payment succeeded and was not
    # refunded (including no-shows and kept-price cancellations).
    # driver_owed counts only UNPAID completed trips: a trip is owed
    # once completed (and not refunded) until the owner marks its
    # payout week paid for that driver.
    paid_ids = [p.booking_id for p in Payment.query.filter_by(status="succeeded").all()]
    gross = Decimal("0.00")
    tax_collected = Decimal("0.00")
    if paid_ids:
        for b in Booking.query.filter(Booking.id.in_(paid_ids)).all():
            gross += money(b.fare_total) + money(b.waiting_charge)
            # Tax collected on paid, non-refunded rides only (refunded
            # payments have status "refunded", so they are not in
            # paid_ids). Tax is pass-through, never profit.
            tax_collected += booking_tax(b)
    refunded_ids = _refunded_booking_ids()
    driver_owed = Decimal("0.00")
    for b in Booking.query.filter_by(status="completed").all():
        if b.id in refunded_ids or b.payout_paid:
            continue
        driver_owed += money(b.driver_earnings)
    counts = {}
    for (status,) in db.session.query(Booking.status).all():
        counts[status] = counts.get(status, 0) + 1
    return jsonify({
        "gross": num(gross),
        "profit": num(gross - driver_owed),
        "driver_owed": num(driver_owed),
        "tax_collected": num(tax_collected),
        "counts": counts,
    })


def _owner_booking_row(b):
    row = {
        "id": b.id,
        "customer_name": b.customer_name,
        "phone": b.phone,
        "route": f"{b.pickup} to {b.dropoff}" if b.dropoff else b.pickup,
        "date": b.date,
        "time": b.time,
        "status": b.status,
        "ride_type": b.ride_type,
        "vehicle_class": booking_vehicle_class(b),
        "vehicle_class_label": class_label(booking_vehicle_class(b)),
        "customer_total": num(b.fare_total),
        "fare": num(booking_fare(b)),
        "tax": num(booking_tax(b)),
        "driver_earnings": num(b.driver_earnings),
        "toll": num(b.toll),
        "gratuity": num(b.gratuity),
        "booking_fee": num(b.booking_fee),
        "waiting_charge": num(b.waiting_charge),
        "profit": num(booking_profit(b)),
        "driver_name": b.accepted_driver.name if b.accepted_driver else None,
        "payout_paid": bool(b.payout_paid),
    }
    row.update(flight_info(b.flight_number, b.pickup, b.dropoff))
    return row


@app.route("/api/owner/bookings", methods=["GET"])
def owner_bookings():
    error = require_owner()
    if error:
        return error
    bookings = Booking.query.order_by(Booking.created_at.desc(), Booking.id.desc()).all()
    return jsonify([_owner_booking_row(b) for b in bookings])


@app.route("/api/owner/bookings/<int:booking_id>", methods=["GET"])
def owner_booking_detail(booking_id):
    error = require_owner()
    if error:
        return error
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    row = _owner_booking_row(booking)
    row.update({
        "pickup": booking.pickup,
        "dropoff": booking.dropoff,
        "email": booking.email,
        "passengers": booking.passengers,
        "ride_type": booking.ride_type,
        "hours": num(booking.hours),
        "miles": num(booking.miles),
        "referral_code_used": booking.referral_code_used,
        "waiting_minutes": booking.waiting_minutes,
        "completed_at": iso(booking.completed_at),
        "payout_paid": bool(booking.payout_paid),
        "invoice": {
            "fare_total": num(booking.fare_total),
            "waiting_charge": num(booking.waiting_charge),
            "total": num(invoice_total(booking.fare_total, booking.waiting_charge)),
        },
        "payments": [{
            "id": p.id, "amount": num(p.amount), "status": p.status,
            "test": p.test, "last4": p.last4, "stripe_test_id": p.stripe_test_id,
            "created_at": iso(p.created_at),
        } for p in booking.payments],
        "events": [{
            "id": e.id, "type": e.type, "message": e.message, "created_at": iso(e.created_at),
        } for e in sorted(booking.events, key=lambda e: e.id)],
    })
    return jsonify(row)


@app.route("/api/owner/bookings/<int:booking_id>/toll", methods=["POST"])
def owner_set_toll(booking_id):
    error = require_owner()
    if error:
        return error
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.status == "completed":
        return err("Cannot change the toll after a ride is completed.", 409)
    data = request.get_json(silent=True) or {}
    if data.get("toll") is None:
        return err("toll is required.")
    try:
        toll = money(data["toll"])
    except Exception:
        return err("toll must be a number.")
    if toll < 0:
        return err("toll cannot be negative.")
    booking.toll = toll
    recompute_booking_fare(booking)
    add_event(booking.id, "toll_updated",
              f"Toll set to ${toll} for booking #{booking.id}; totals recomputed "
              f"(customer ${booking.fare_total}, driver ${booking.driver_earnings}).")
    db.session.commit()
    payload = {"booking": _owner_booking_row(booking)}
    payment = Payment.query.filter_by(booking_id=booking.id, status="succeeded").order_by(Payment.id.desc()).first()
    if payment is not None:
        balance_due = invoice_total(booking.fare_total, booking.waiting_charge) - money(payment.amount)
        payload["balance_due"] = num(balance_due)
        payload["paid_amount"] = num(payment.amount)
    else:
        payload["balance_due"] = None
    return jsonify(payload)


@app.route("/api/owner/payouts", methods=["GET"])
def owner_payouts():
    """Per-driver, per-week payout totals. Owner PIN session required.

    Only completed, non-refunded trips appear. Each week's payout
    comes due 14 days after the week starts (week 0 due Nov 30,
    week 1 due Dec 7, week 2 due Dec 14, ...); a week is paid when
    every trip in it has been marked paid. Tracking only — no money
    moves here.
    """
    error = require_owner()
    if error:
        return error
    bookings = (Booking.query.filter_by(status="completed")
                .order_by(Booking.created_at, Booking.id).all())
    eligible = _payout_eligible(bookings)
    groups = {}
    for b in eligible:
        w = _booking_week(b)
        groups.setdefault((b.accepted_driver_id, w["index"]), (w, []))[1].append(b)
    drivers = {d.id: d for d in Driver.query.all()}
    result = []
    for (driver_id, _index), (w, members) in sorted(
            groups.items(), key=lambda kv: (-kv[0][1], kv[0][0] or 0)):
        driver = drivers.get(driver_id)
        summary = _week_summary(w, members)
        summary.update({
            "driver_id": driver_id,
            "driver_name": driver.name if driver else None,
            "driver_phone": driver.phone if driver else None,
            "rides": [{
                "id": b.id,
                "date": b.date,
                "completed_date": completion_date(b.completed_at, b.created_at).isoformat(),
                "route": f"{b.pickup} to {b.dropoff}" if b.dropoff else b.pickup,
                "earnings": num(b.driver_earnings),
                "payout_paid": bool(b.payout_paid),
            } for b in sorted(members, key=lambda b: b.id)],
        })
        result.append(summary)
    return jsonify(result)


@app.route("/api/owner/payouts/mark-paid", methods=["POST"])
def owner_mark_payout_paid():
    """Mark one driver's one payout week paid. Owner PIN session required.

    Body: {"driver_id": int, "week_index": int}. Sets the payout-paid
    flag on every completed, non-refunded trip of that driver in that
    week. Idempotent: marking an already-paid week again succeeds
    with marked=0. A trip completed later into the same week stays
    unpaid until marked again.
    """
    error = require_owner()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    if data.get("driver_id") is None or data.get("week_index") is None:
        return err("driver_id and week_index are required.")
    try:
        driver_id = int(data["driver_id"])
        week_index = int(data["week_index"])
    except (TypeError, ValueError):
        return err("driver_id and week_index must be integers.")
    driver = db.session.get(Driver, driver_id)
    if not driver:
        return err("Driver not found.", 404)
    bookings = (Booking.query.filter_by(status="completed", accepted_driver_id=driver_id).all())
    members = [b for b in _payout_eligible(bookings)
               if _booking_week(b)["index"] == week_index]
    if not members:
        return err("No completed trips in this week for this driver.", 404)
    marked = 0
    for b in members:
        if not b.payout_paid:
            b.payout_paid = True
            marked += 1
    db.session.commit()
    summary = _week_summary(week_bounds(week_index), members)
    summary.update({
        "driver_id": driver.id,
        "driver_name": driver.name,
        "marked": marked,
    })
    return jsonify({"payout": summary})


@app.route("/api/owner/alerts", methods=["GET"])
def owner_alerts():
    error = require_owner()
    if error:
        return error
    events = (BookingEvent.query.order_by(BookingEvent.id.desc()).limit(200).all())
    return jsonify([{
        "id": e.id, "type": e.type, "message": e.message,
        "booking_id": e.booking_id, "created_at": iso(e.created_at),
    } for e in events])


@app.route("/api/owner/outbox", methods=["GET"])
def owner_outbox():
    error = require_owner()
    if error:
        return error
    messages = (OutboxMessage.query.order_by(OutboxMessage.id.desc()).limit(200).all())
    return jsonify([{
        "id": m.id, "channel": m.channel, "recipient": m.recipient,
        "body": m.body, "booking_id": m.booking_id, "created_at": iso(m.created_at),
    } for m in messages])


@app.route("/api/owner/drivers", methods=["GET"])
def owner_drivers():
    error = require_owner()
    if error:
        return error
    drivers = Driver.query.order_by(Driver.created_at, Driver.id).all()
    return jsonify([{
        "id": d.id,
        "name": d.name,
        "phone": d.phone,
        "email": d.email,
        "car": f"{d.car_model} ({d.car_colour})",
        "car_model": d.car_model,
        "car_year": d.car_year,
        "vehicle_class": driver_vehicle_class(d),
        "vehicle_class_label": class_label(driver_vehicle_class(d)),
        "car_colour": d.car_colour,
        "plate": d.plate,
        "available": d.available,
        "docs": driver_docs_status(d),
        # Document row ids so the owner viewer can fetch each file via
        # GET /api/owner/documents/<id>. Profile picture has no document
        # row — it is served via GET /api/owner/drivers/<id>/photo.
        "doc_ids": {doc.doc_type: doc.id for doc in d.documents},
        "bank_masked": bank_masked(d),
    } for d in drivers])


@app.route("/api/owner/documents/<int:doc_id>", methods=["GET"])
def owner_document(doc_id):
    error = require_owner()
    if error:
        return error
    doc = db.session.get(DriverDocument, doc_id)
    if not doc:
        return err("Document not found.", 404)
    return Response(doc.file, mimetype=doc.mime)


@app.route("/api/owner/drivers/<int:driver_id>/photo", methods=["GET"])
def owner_driver_photo(driver_id):
    error = require_owner()
    if error:
        return error
    driver = db.session.get(Driver, driver_id)
    if not driver or not driver.profile_photo:
        return err("Photo not available.", 404)
    return Response(driver.profile_photo, mimetype=driver.profile_photo_mime or "image/jpeg")


# ------------------------------------------------------------------- main ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
