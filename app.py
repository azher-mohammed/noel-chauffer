"""Noel Chauffer — real booking system backend (Flask + SQLAlchemy).

LIVE Stripe payments (owner decision 2026-11-20, voice call: "Uber
jaisa bana do"): cards are collected by Stripe.js in the browser and
authorized at booking (a hold for the estimated fare), then the final
fare is captured automatically when the ride ends. Saved cards live
with Stripe only. Keys come ONLY from the Render environment
(STRIPE_SECRET_KEY / STRIPE_PUBLISHABLE_KEY) — until the owner adds
them, payments refuse outright; there is no fake-success fallback.
See stripe_payments.py.

Customer messages are written to the owner-dashboard outbox only —
this app never sends SMS or email (no SMTP, no Twilio/SendGrid
anywhere).

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
  AZURE_TRANSLATOR_KEY      Azure Translator key for chat translation
                  (F0 free tier). Optional: without it the chat works
                  exactly as before, untranslated. Never commit a key.
  AZURE_TRANSLATOR_REGION   Azure region of the Translator resource
                  (e.g. eastus); sent as Ocp-Apim-Subscription-Region.
                  Optional for a single-service Translator resource.
  AZURE_TRANSLATOR_ENDPOINT Translator endpoint; defaults to
                  https://api.cognitive.microsofttranslator.com.
"""

from __future__ import annotations

import io
import hashlib
import hmac
import logging
import os
import secrets
import string
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from html import escape as html_escape
from urllib.parse import quote_plus

from cryptography.fernet import Fernet
from flask import Flask, Response, jsonify, request, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageOps
from sqlalchemy import Numeric, func, or_
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

import geo as geo_module
import stripe_payments
from car_models import (
    MIN_CAR_YEAR,
    allowed_models,
    class_for_model,
    is_first_class_model,
    location_exempt_for,
    max_car_year,
    suspension_exempt_for,
    validate_car_model,
    validate_car_year,
)
from email_sender import SENT as EMAIL_SENT, send_email
from flights import flight_info, normalize_flight_number
from payouts import completion_date, week_bounds, week_for
from translation import (
    CHAT_LANGUAGES,
    normalize_chat_language,
    translate_chat_text,
)
from pricing import (
    DRIVER_PAY_MAX_MILES,
    HOURLY_MAX_HOURS,
    HOURLY_MIN_HOURS,
    cancellation_refundable,
    class_label,
    compute_class_totals,
    compute_extra_distance,
    compute_hourly,
    compute_one_way,
    driver_cancel_locked,
    estimate_upfront_toll,
    free_waiting_minutes,
    is_airport_pickup,
    invoice_total,
    miles_1dp,
    money,
    pricing_mode,
    waiting_charge,
    waiting_time_elapsed,
)
from blacklane_pricing import (
    blacklane_class_label,
    compute_blacklane_one_way,
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

# Permanent customer login (owner decision 2026-11-23): once a
# customer signs in they stay signed in on that browser for ~365
# days, until they sign out. Only sessions explicitly marked
# permanent (customer sign-in below) get the long lifetime; the
# browser-session default still applies everywhere else.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365)

OWNER_PIN = os.environ.get("OWNER_PIN", "1234")
# Owner PIN session lifetime (owner decision 2026-11-23): the owner
# session used to live forever — session["owner"] = True with no
# timestamp and no expiry, so a browser that had logged in once
# stayed logged in and the dashboard opened without a PIN (found
# by a browser live-check 2026-11-23 ~03:33 EST). The session now
# expires OWNER_SESSION_MAX_AGE_SECONDS after login (default 8
# hours, absolute — no sliding refresh, so an open tab cannot stay
# live forever). After expiry the owner types the PIN again.
OWNER_SESSION_MAX_AGE_SECONDS = int(os.environ.get("OWNER_SESSION_MAX_AGE_SECONDS", "28800"))
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
    "doc_nj_qualification": "nj_qualification",
    "doc_nj_municipal_license": "nj_municipal_license",
    "doc_nj_limo_registration": "nj_limo_registration",
    "doc_nj_insurance": "nj_insurance",
    "doc_vehicle_registration": "vehicle_registration",
    "doc_insurance_card": "insurance_card",
    "doc_al_certificate": "al_certificate",
    "doc_al_form_e": "al_form_e",
    "doc_ca_tcp_permit": "ca_tcp_permit",
    "doc_ca_driver_statement": "ca_driver_statement",
    "doc_ca_commercial_registration": "ca_commercial_registration",
    "doc_ca_inspection_declaration": "ca_inspection_declaration",
    "doc_co_ll_permit": "co_ll_permit",
    "doc_co_inspection": "co_inspection",
    "doc_co_form_e": "co_form_e",
    "doc_ct_livery_permit": "ct_livery_permit",
    "doc_de_certificate": "de_certificate",
    "doc_de_limo_registration": "de_limo_registration",
    "doc_de_inspection": "de_inspection",
    "doc_dc_drivers_record": "dc_drivers_record",
    "doc_dc_ssc": "dc_ssc",
    "doc_dc_residency": "dc_residency",
    "doc_dc_medical_form": "dc_medical_form",
    "doc_dc_face_id": "dc_face_id",
    "doc_dc_public_vehicle_license": "dc_public_vehicle_license",
    "doc_dc_inspection": "dc_inspection",
    "doc_ga_carrier_certificate": "ga_carrier_certificate",
    "doc_ga_insurance_certificate": "ga_insurance_certificate",
    "doc_hi_carrier_certificate": "hi_carrier_certificate",
    "doc_hi_vehicle_inventory": "hi_vehicle_inventory",
    "doc_hi_tax_clearance": "hi_tax_clearance",
    "doc_ks_certificate": "ks_certificate",
    "doc_ky_limousine_certificate": "ky_limousine_certificate",
    "doc_ky_vehicle_license": "ky_vehicle_license",
    "doc_ky_inspection": "ky_inspection",
    "doc_me_registration": "me_registration",
    "doc_me_jb_filing": "me_jb_filing",
    "doc_md_for_hire_license": "md_for_hire_license",
    "doc_md_inspection_certificate": "md_inspection_certificate",
    "doc_mi_carrier_license": "mi_carrier_license",
    "doc_mn_permit": "mn_permit",
    "doc_mn_inspection": "mn_inspection",
    "doc_mn_form_e": "mn_form_e",
    "doc_mo_authority": "mo_authority",
    "doc_ne_medical_certificate": "ne_medical_certificate",
    "doc_ne_carrier_authority": "ne_carrier_authority",
    "doc_nv_drivers_permit": "nv_drivers_permit",
    "doc_nv_cpcn": "nv_cpcn",
    "doc_nm_inspection": "nm_inspection",
    "doc_oh_livery_registration": "oh_livery_registration",
    "doc_pa_driving_history": "pa_driving_history",
    "doc_pa_criminal_history": "pa_criminal_history",
    "doc_pa_certificate": "pa_certificate",
    "doc_pa_inspection": "pa_inspection",
    "doc_pa_form_e": "pa_form_e",
    "doc_ri_operator_license": "ri_operator_license",
    "doc_ri_driving_record": "ri_driving_record",
    "doc_ri_criminal_record": "ri_criminal_record",
    "doc_sc_driving_record": "sc_driving_record",
    "doc_sc_charter_certificate": "sc_charter_certificate",
    "doc_sc_ls_registration": "sc_ls_registration",
    "doc_sc_form_e": "sc_form_e",
    "doc_tn_citizenship_proof": "tn_citizenship_proof",
    "doc_tn_residency_proof": "tn_residency_proof",
    "doc_va_authority": "va_authority",
    "doc_va_title": "va_title",
    "doc_va_for_hire_registration": "va_for_hire_registration",
    "doc_va_authority_registration": "va_authority_registration",
    "doc_wa_medical_certificate": "wa_medical_certificate",
    "doc_wa_driving_record": "wa_driving_record",
    "doc_wa_carrier_license": "wa_carrier_license",
    "doc_wa_vehicle_certificate": "wa_vehicle_certificate",
    "doc_wa_chauffeur_addendum": "wa_chauffeur_addendum",
    "doc_wa_fh_registration": "wa_fh_registration",
    "doc_wa_inspection_report": "wa_inspection_report",
    "doc_wa_insurance_certificate": "wa_insurance_certificate",
    "doc_dallas_commercial_insurance": "dallas_commercial_insurance",
    "doc_dallas_driver_permit": "dallas_driver_permit",
    "doc_dallas_limo_permit": "dallas_limo_permit",
    "doc_buffalo_taxi_driver_license": "buffalo_taxi_driver_license",
    "doc_buffalo_insurance_certificate": "buffalo_insurance_certificate",
    "doc_buffalo_inspection_report": "buffalo_inspection_report",
    "doc_rochester_taxi_driver_license": "rochester_taxi_driver_license",
    "doc_rochester_hack_certificate": "rochester_hack_certificate",
    "doc_rochester_insurance": "rochester_insurance",
    "doc_syracuse_hack_license": "syracuse_hack_license",
    "doc_syracuse_ground_transportation": "syracuse_ground_transportation",
    "doc_syracuse_for_hire_insurance": "syracuse_for_hire_insurance",
    "doc_wctlc_driver_permit": "wctlc_driver_permit",
    "doc_wctlc_vehicle_permit": "wctlc_vehicle_permit",
    "doc_wctlc_insurance": "wctlc_insurance",
    "doc_wctlc_defensive_driving": "wctlc_defensive_driving",
    "doc_birmingham_operator_permit": "birmingham_operator_permit",
    "doc_huntsville_chauffeur_license": "huntsville_chauffeur_license",
    "doc_mobile_chauffeur_license": "mobile_chauffeur_license",
    "doc_montgomery_chauffeur_license": "montgomery_chauffeur_license",
    "doc_miami_chauffeur_registration": "miami_chauffeur_registration",
    "doc_orlando_driver_permit": "orlando_driver_permit",
    "doc_orlando_insurance": "orlando_insurance",
    "doc_tallahassee_driver_permit": "tallahassee_driver_permit",
    "doc_tampa_pvdl": "tampa_pvdl",
    "doc_tampa_transcript": "tampa_transcript",
    "doc_baton_rouge_chauffeur_license": "baton_rouge_chauffeur_license",
    "doc_baton_rouge_driving_record": "baton_rouge_driving_record",
    "doc_baton_rouge_clearance": "baton_rouge_clearance",
    "doc_new_orleans_driver_permit": "new_orleans_driver_permit",
    "doc_new_orleans_mvr": "new_orleans_mvr",
    "doc_mvfha_driver_permit": "mvfha_driver_permit",
    "doc_charlotte_pvh_permit": "charlotte_pvh_permit",
    "doc_charlotte_driving_record": "charlotte_driving_record",
    "doc_durham_pvfh_permit": "durham_pvfh_permit",
    "doc_charleston_chauffeur_license": "charleston_chauffeur_license",
    "doc_charleston_driving_record": "charleston_driving_record",
    "doc_nashville_opvh_permit": "nashville_opvh_permit",
    "doc_nashville_mvr": "nashville_mvr",
    "doc_chicago_chauffeur_license": "chicago_chauffeur_license",
    "doc_chicago_livery_vehicle_license": "chicago_livery_vehicle_license",
    "doc_chicago_insurance_certificate": "chicago_insurance_certificate",
    "doc_rockford_taxi_driver_license": "rockford_taxi_driver_license",
    "doc_springfield_il_taxi_driver_license": "springfield_il_taxi_driver_license",
    "doc_evansville_taxi_driver_license": "evansville_taxi_driver_license",
    "doc_indianapolis_operator_license": "indianapolis_operator_license",
    "doc_indianapolis_training_certificate": "indianapolis_training_certificate",
    "doc_indianapolis_bmv_record": "indianapolis_bmv_record",
    "doc_minneapolis_taxi_driver_license": "minneapolis_taxi_driver_license",
    "doc_minneapolis_training_certificate": "minneapolis_training_certificate",
    "doc_rochester_mn_taxi_driver_license": "rochester_mn_taxi_driver_license",
    "doc_saint_paul_taxi_driver_license": "saint_paul_taxi_driver_license",
    "doc_saint_paul_training_proof": "saint_paul_training_proof",
    "doc_columbia_chauffeur_license": "columbia_chauffeur_license",
    "doc_independence_vehicle_driver_permit": "independence_vehicle_driver_permit",
    "doc_jefferson_city_taxi_driver_permit": "jefferson_city_taxi_driver_permit",
    "doc_jefferson_city_driving_record": "jefferson_city_driving_record",
    "doc_kansas_city_driver_certificate": "kansas_city_driver_certificate",
    "doc_kansas_city_operating_record": "kansas_city_operating_record",
    "doc_saint_louis_mtc_license": "saint_louis_mtc_license",
    "doc_saint_louis_driver_history": "saint_louis_driver_history",
    "doc_lincoln_taxi_driver_license": "lincoln_taxi_driver_license",
    "doc_kenosha_taxi_driver_license": "kenosha_taxi_driver_license",
    "doc_madison_ppv_permit": "madison_ppv_permit",
    "doc_milwaukee_ppv_license": "milwaukee_ppv_license",
    "doc_columbus_vfh_license": "columbus_vfh_license",
    "doc_columbus_bmv_abstract": "columbus_bmv_abstract",
    "doc_portland_me_livery_license": "portland_me_livery_license",
    "doc_south_portland_taxi_driver_license": "south_portland_taxi_driver_license",
    "doc_lowell_hackney_license": "lowell_hackney_license",
    "doc_springfield_ma_chauffeur_license": "springfield_ma_chauffeur_license",
    "doc_worcester_taxi_livery_license": "worcester_taxi_livery_license",
    "doc_jersey_city_limo_driver_license": "jersey_city_limo_driver_license",
    "doc_philadelphia_limo_certificate": "philadelphia_limo_certificate",
    "doc_little_rock_gt_driver_permit": "little_rock_gt_driver_permit",
    "doc_springdale_taxi_driver_permit": "springdale_taxi_driver_permit",
    "doc_boise_cts_driver_license": "boise_cts_driver_license",
    "doc_idaho_falls_operator_license": "idaho_falls_operator_license",
    "doc_okc_vfh_driver_permit": "okc_vfh_driver_permit",
    "doc_tulsa_chauffeur_license": "tulsa_chauffeur_license",
    "doc_tulsa_mvr": "tulsa_mvr",
    "doc_austin_chauffeur_permit": "austin_chauffeur_permit",
    "doc_houston_vfh_driver_license": "houston_vfh_driver_license",
    "doc_san_antonio_driver_permit": "san_antonio_driver_permit",
    "doc_st_george_for_hire_permit": "st_george_for_hire_permit",
    "doc_cheyenne_pt_driver_permit": "cheyenne_pt_driver_permit",
    "doc_gillette_pt_driver_permit": "gillette_pt_driver_permit",
    "doc_clark_county_business_license": "clark_county_business_license",
    "doc_portland_or_certification": "portland_or_certification",
    "doc_portland_or_business_license": "portland_or_business_license",
}
# doc_type -> multipart field name (profile_picture comes from profile_photo)
FIELD_FOR_DOC_TYPE = {"profile_picture": "profile_photo"}
FIELD_FOR_DOC_TYPE.update({v: k for k, v in DOC_FIELD_MAP.items()})
# doc_type -> exact user-visible label, same wording as the driver app
# and owner dashboard. Used by the compulsory-documents gate so the
# rejection names each missing item in the owner's words.
DOC_LABELS = {
    "profile_picture": "Profile Picture",
    "dmv_license": "DMV driving license",
    "tlc_license": "TLC License",
    "fh1_insurance": "FH-1 Insurance Card",
    "registration": "Commercial Vehicle Registration",
    "inspection": "NYS DMV Inspection",
    "vehicle_permit": "TLC-for-hire Vehicle Permit",
}

# --- Driver document verification (owner decision 2026-11-19) -----------
# Approved by the owner in a voice call ("haan na", after asking how
# verification would work; the earlier "abhi nahi" deferral is lifted).
# Three server-side checks at registration, deterministic, no external
# API, no OCR, no background check, no new required document:
#   1. Duplicate detection: SHA-256 of the raw file bytes. The same
#      bytes on another driver, or in two slots of one registration,
#      are rejected. Existing drivers are never blocked retroactively.
#   2. Photo sanity for document IMAGES (not PDFs): must open as a
#      real image, both sides >= 200px, and not effectively blank.
#   3. Expiry (approved the same call, "expiry ka aap khud padhna
#      chahiye"): the driver types the expiry date printed on the
#      document; a past date is rejected. OCR was investigated and
#      NOT used: the Render service is a native Python Blueprint
#      (no Dockerfile, so no Tesseract binary can be added without
#      switching the deploy to Docker), and Azure AI Vision would
#      need a new Vision resource + key the owner must create — plus
#      OCR of dates off phone photos is unreliable. Typed dates are
#      deterministic and need no new key, cost or deploy change.
# EXPIRY_DOC_TYPES is the v1 set: the six New York items the owner
# named, plus the generic-list equivalents (vehicle_registration,
# insurance_card) used by every other state. Other state-specific
# permits/certificates are not expiry-checked in v1.
EXPIRY_DOC_TYPES = frozenset({
    "dmv_license", "tlc_license", "fh1_insurance", "registration",
    "inspection", "vehicle_permit", "vehicle_registration", "insurance_card",
})
DOC_PHOTO_MIN_SIDE = 200
# Blank-photo rule (conservative, so a normal document photo never
# trips it): downscaled to 64x64 grey, the image counts as blank only
# when it is nearly uniform (stddev < 3) AND nearly all white or all
# black. A solid-colour photo (e.g. a red test fixture) is uniform
# but mid-tone, so it passes; a photo of a blank white sheet fails.
BLANK_PHOTO_MAX_STDDEV = 3.0
BLANK_PHOTO_WHITE_MEAN = 240
BLANK_PHOTO_BLACK_MEAN = 15
# --- Per-state document requirements (owner decision 2026-11-17) ---------
# The 7 items above are New York City / New York only ("ye base sirf
# New York City ke vaaste hai"). A driver from another state cannot
# register against them — New Jersey has no TLC — so registration
# asks for the driver's state first (searchable dropdown, USA only)
# and the compulsory list follows the state. New York keeps EXACTLY
# the 7 items above, same labels, same order, same gate.
# New Jersey: items verified from official NJ sources only — the MVC
# "Letter of Qualification" (written chauffeur certification from the
# Chief Administrator under N.J.S.A. 48:16-22.3a), the municipal
# license to operate (N.J.S.A. 48:16-22; required by MVC for every
# limousine registration transaction), the MVC limousine (Code 14)
# vehicle registration, and the $1.5M liability insurance certificate
# (NJ MVC commercial-vehicle pages). Florida licensing is county-level
# (Miami-Dade and Broward each issue their own chauffeur's
# registration under different county codes), so no single statewide
# Florida list can be stated honestly: Florida uses the generic base
# list, as does every other state without a verified list. NEVER
# invent a state-specific permit or license name — an unverified
# state gets the generic list and the owner reviews the application.
# 2026-11-17 (owner order, "complete Uber driver ke document jaisa
# hi banana"): every state gets its OWN list from the official-source
# research report (51 jurisdictions). VERIFIED states (DC, Maine,
# Rhode Island, Washington, plus NY/NJ) carry their complete official
# list. PARTIAL states carry the generic base 4 plus ONLY the
# officially-named extra items, and keep the owner-review note. The
# 14 UNVERIFIED states and the county/city-level states (Florida,
# Illinois, Texas, Massachusetts) stay on the generic base list —
# nothing is invented, and no city list is ever applied statewide.
# Process-type requirements (background checks, drug tests, courses,
# exams) are never upload slots. No document count is ever shown
# (owner decision 2026-11-17, "Quantity nahi").
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
]
NJ_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "nj_qualification",
    "nj_municipal_license",
    "nj_limo_registration",
    "nj_insurance",
]
GENERIC_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "insurance_card",
]
# Per-state lists from the official-source research report
# (2026-11-17, 51 jurisdictions; see the report for the full
# table). VERIFIED lists are complete as named by the official
# source. PARTIAL lists are the generic base 4 plus ONLY the
# officially-named extra items; anything the report does not
# name for that state is NOT added, and the owner-review note
# stays on. States with no entry here — the 14 UNVERIFIED
# states and the county/city-level states (Florida, Illinois,
# Texas, Massachusetts) — fall back to GENERIC_DOC_TYPES.
# District of Columbia (VERIFIED, official sources):
#   https://dfhv.dc.gov/page/driver-licensing
#   https://dfhv.dc.gov/sites/default/files/dc/sites/dc%20taxi/page_content/attachments/Face%20ID%20APP%202024.pdf
# FBI background investigation + fingerprints and the Face ID exam left out: in-person processes. Livery tags left out: vehicle markings.
DC_DOC_TYPES = ["profile_picture", "dmv_license", "dc_drivers_record", "dc_ssc", "dc_residency", "dc_medical_form", "dc_face_id", "dc_public_vehicle_license", "vehicle_registration", "dc_inspection", "insurance_card"]
# Maine (VERIFIED, official sources):
#   https://www3.maine.gov/sos/taxi-limousine
# Town/city license left out: conditional ("if required locally"). USDOT number left out: conditional and a number, not a document. The JB filing IS the insurance evidence, so it replaces the generic insurance card; the HIRE-plates registration replaces the generic registration.
ME_DOC_TYPES = ["profile_picture", "dmv_license", "me_registration", "me_jb_filing"]
# Rhode Island (VERIFIED, official sources):
#   https://rules.sos.ri.gov/Regulations/part/815-50-10-3?reg_id=9376
#   https://rules.sos.ri.gov/Regulations/part/815-50-10-2?reg_id=9375
# English knowledge and age 21+ left out: not documents.
RI_DOC_TYPES = ["profile_picture", "dmv_license", "ri_operator_license", "ri_driving_record", "ri_criminal_record", "vehicle_registration", "insurance_card"]
# Washington (VERIFIED, official sources):
#   https://dor.wa.gov/manage-business/state-endorsements/limousine
#   https://dol.wa.gov/professional-licenses/limousines/licensing-requirements-wine-tour-transportation-providers
# Background-check results, NSC defensive-driving course, drug testing and the training course + written exam left out: check / course / test processes. The F/H registration certificate and the insurance certificate replace the generic slots.
WA_DOC_TYPES = ["profile_picture", "dmv_license", "wa_medical_certificate", "wa_driving_record", "wa_carrier_license", "wa_vehicle_certificate", "wa_chauffeur_addendum", "wa_fh_registration", "wa_inspection_report", "wa_insurance_certificate"]
# Alabama (PARTIAL, official sources):
#   http://apsc.alabama.gov/Transportation/intrastatereg.htm
# Tariff left out: conditional ("if granted") carrier filing.
AL_DOC_TYPES = ["profile_picture", "dmv_license", "al_certificate", "vehicle_registration", "al_form_e"]
# California (PARTIAL, official sources):
#   https://www.cpuc.ca.gov/regulatory-services/licensing/transportation-licensing-and-analysis-branch/charter-party-carriers/types-of-charter-party-carrier-authorities
#   https://www.cpuc.ca.gov/tcpforms/
# EPN enrollment and Form PL706-J drug-testing certification left out: program enrollment / drug-testing process, not uploadable documents.
# TCP slot relabelled 2026-11-18 per the owner Uber cross-check:
# Uber accepts a TCP Certificate Class A, B or P in the driver's
# own name or company name (A statewide, B 125 air miles from the
# home terminal, P vehicles seating 15 or fewer); driving under
# someone else's TCP does not qualify. No Subcarrier
# Acknowledgement slot (Uber's own form) and no Secretary of
# State slot (conditional on company-name TCPs; the owner-review
# note covers it).
CA_DOC_TYPES = ["profile_picture", "dmv_license", "ca_tcp_permit", "ca_driver_statement", "ca_commercial_registration", "ca_inspection_declaration", "insurance_card"]
# Colorado (PARTIAL, official sources):
#   https://puc.colorado.gov/passenger-carrier-frequently-asked-questions
#   https://puc.colorado.gov/limited-regulation-carriers-industry-info
# Vehicle stamp left out: a vehicle marking, not a document.
CO_DOC_TYPES = ["profile_picture", "dmv_license", "co_ll_permit", "vehicle_registration", "co_inspection", "co_form_e"]
# Connecticut (PARTIAL, official sources):
#   https://portal.CT.gov/dmv/licenses/licenses/endorsements-on-a-drivers-license
#   https://cga.ct.gov/2024/sup/chap_244b.htm
# "F" endorsement lives ON the license photo; no separate slot.
CT_DOC_TYPES = ["profile_picture", "dmv_license", "ct_livery_permit", "vehicle_registration", "insurance_card"]
# Delaware (PARTIAL, official sources):
#   https://delcode.delaware.gov/title21/c027/sc05/index.html
#   https://regulations.delaware.gov/api/AdminCode/title2/2287/9ef5fe4b-c667-44ab-8b54-c278fb577ad3
# Accident-prevention course evidence and criminal-history background check left out: course / check processes. Endorsement lives on the license photo.
DE_DOC_TYPES = ["profile_picture", "dmv_license", "de_certificate", "de_limo_registration", "de_inspection", "insurance_card"]
# Georgia (PARTIAL, official sources):
#   https://dds.georgia.gov/online-services-faqs
#   https://dps.georgia.gov/document/document/chapter-570-38-january-2020/download
# For-Hire endorsement lives on the license photo (the private background-check certification is an OR-alternative the gate cannot express); GAPS fingerprints are a process. "LM" plate detail was not independently verified, so the generic registration slot stays.
GA_DOC_TYPES = ["profile_picture", "dmv_license", "ga_carrier_certificate", "vehicle_registration", "ga_insurance_certificate"]
# Hawaii (PARTIAL, official sources):
#   https://puc.hawaii.gov/motor_carriers/
#   http://puc.hawaii.gov/wp-content/uploads/2013/06/MC-App-Passenger-92-001.fillable.pdf
HI_DOC_TYPES = ["profile_picture", "dmv_license", "hi_carrier_certificate", "hi_vehicle_inventory", "hi_tax_clearance", "vehicle_registration", "insurance_card"]
# Kansas (PARTIAL, official sources):
#   https://www.kcc.ks.gov/news-3-17-23
# Insurance filing and tariff/rates filing left out: carrier filings, not driver-held documents.
KS_DOC_TYPES = ["profile_picture", "dmv_license", "ks_certificate", "vehicle_registration", "insurance_card"]
# Kentucky (PARTIAL, official sources):
#   https://apps.legislature.ky.gov/recorddocuments/bill/25RS/hb493/orig_bill.pdf
#   https://apps.legislature.ky.gov/recorddocuments/bill/25RS/HB188/SCS1.pdf
# Indemnifying bond left out: OR-alternative to insurance (insurance card slot covers the insurance path). Background check left out: process. Confirm current KRS before launch (report used bill text).
KY_DOC_TYPES = ["profile_picture", "dmv_license", "ky_limousine_certificate", "ky_vehicle_license", "vehicle_registration", "ky_inspection", "insurance_card"]
# Maryland (PARTIAL, official sources):
#   https://psc.maryland.gov/regulated-utilities/transportation/
#   https://mva.maryland.gov/your-mva-guide/businesses/hire-vehicle-operators
# Human-trafficking training documentation, CJIS records check and driving-record check left out: training / check processes.
MD_DOC_TYPES = ["profile_picture", "dmv_license", "md_for_hire_license", "vehicle_registration", "md_inspection_certificate", "insurance_card"]
# Michigan (PARTIAL, official sources):
#   https://www.michigan.gov/sos/all-services/cdl-apply
#   https://www.michigan.gov/sos/faqs/license-and-id/enhanced-license-and-ids
# Chauffeur's license IS the license photo (a license type, not an extra document). CDL P endorsement and medical card left out: conditional (16+ passengers / 10,000+ lbs).
MI_DOC_TYPES = ["profile_picture", "dmv_license", "mi_carrier_license", "vehicle_registration", "insurance_card"]
# Minnesota (PARTIAL, official sources):
#   https://www.revisor.mn.gov/statutes/cite/221.84/version/2021-10-26%2010:04:20+00:00
#   https://www.revisor.mn.gov/rules/8880/full
# Criminal history check left out: process. Decal left out: vehicle marking. USDOT number left out: a number, not a document.
MN_DOC_TYPES = ["profile_picture", "dmv_license", "mn_permit", "vehicle_registration", "mn_inspection", "mn_form_e"]
# Missouri (PARTIAL, official sources):
#   https://data.mo.gov/api/file_data/p2O1Ykj892HuQeclCyWoUzmijiB--8QjGhm4Gcovwhs?filename=Application%2520for%2520Vehicle-for-Hire%2520Driver.pdf
# Kansas City / St. Louis items left out: local, not statewide. Class E endorsement lives on the license photo.
MO_DOC_TYPES = ["profile_picture", "dmv_license", "mo_authority", "vehicle_registration", "insurance_card"]
# Nebraska (PARTIAL, official sources):
#   https://psc.nebraska.gov/sites/default/files/doc/administration/Updated_RRs/2024_Updates/Chapter%203%20-%20Motor%20Transportation%20Rules%20and%20Regulations.pdf
# Rates filing and annual fees left out: carrier filing / payment, not documents.
NE_DOC_TYPES = ["profile_picture", "dmv_license", "ne_medical_certificate", "ne_carrier_authority", "vehicle_registration", "insurance_card"]
# Nevada (PARTIAL, official sources):
#   https://www.nta.nv.gov/consumers/illegal-passenger-transportation-in-nevada/
# Driver qualification file and vehicle maintenance files left out: files, not single documents. Drug testing left out: process. Decal left out: vehicle marking.
NV_DOC_TYPES = ["profile_picture", "dmv_license", "nv_drivers_permit", "nv_cpcn", "vehicle_registration", "insurance_card"]
# New Mexico (PARTIAL, official sources):
#   https://www.srca.nm.gov/parts/title18/18.003.0004.html
# Driver application, background check and driving-history review left out: application form / processes. CDL qualifications left out: conditional (CDL drivers only).
NM_DOC_TYPES = ["profile_picture", "dmv_license", "vehicle_registration", "nm_inspection", "insurance_card"]
# Ohio (PARTIAL, official sources):
#   https://codes.ohio.gov/ohio-revised-code/section-4503.24
#   https://dam.assets.ohio.gov/image/upload/publicsafety.ohio.gov/bmv4705.pdf
# ORC 4509.80 compliance left out: a requirement, not a document. The livery-plates registration replaces the generic registration.
OH_DOC_TYPES = ["profile_picture", "dmv_license", "oh_livery_registration", "insurance_card"]
# Pennsylvania (PARTIAL, official sources):
#   https://www.puc.pa.gov/pcdocs/1879004.pdf
# Age 21+ left out: not a document. Medical certification left out: not established as a statewide upload item. Docket-letter evidence: confirm current 52 Pa. Code before launch.
PA_DOC_TYPES = ["profile_picture", "dmv_license", "pa_driving_history", "pa_criminal_history", "pa_certificate", "vehicle_registration", "pa_inspection", "pa_form_e"]
# South Carolina (PARTIAL, official sources):
#   https://psc.sc.gov/sites/psc/files/Documents/Forms/transprtation/Class%20C%20Charter%20Application%20Amended%202026-10-26.pdf
#   http://ors.sc.gov/regulated-utilities/transportation/class-c/becoming-class-c-certificate-passenger-carrier
# ORS inspection left out: an inspection event, no named document. The LS-plates registration replaces the generic registration.
SC_DOC_TYPES = ["profile_picture", "dmv_license", "sc_driving_record", "sc_charter_certificate", "sc_ls_registration", "sc_form_e"]
# Tennessee (PARTIAL, official sources):
#   https://www.tn.gov/safety/driver-services/commercial-driver-license/classf.html
# Knowledge test and vision screening left out: processes. Endorsement lives on the license photo. Limousine scope by "main job" test: confirm with DOS before launch.
TN_DOC_TYPES = ["profile_picture", "dmv_license", "tn_citizenship_proof", "tn_residency_proof", "vehicle_registration", "insurance_card"]
# Virginia (PARTIAL, official sources):
#   https://www.dmv.virginia.gov/businesses/motor-carriers/intrastate/how-apply
# Surety bond / letter of credit left out: OR-alternative, conditional on certificate/license holders. For-hire plates left out: vehicle markings.
VA_DOC_TYPES = ["profile_picture", "dmv_license", "va_authority", "va_title", "va_for_hire_registration", "va_authority_registration", "insurance_card"]

# States with a state-specific list (verified or partial).
# Every other state uses GENERIC_DOC_TYPES via
# required_docs_for_state().
STATE_DOC_REQUIREMENTS = {
    "New York": DOC_TYPES,
    "New Jersey": NJ_DOC_TYPES,
    "District of Columbia": DC_DOC_TYPES,
    "Maine": ME_DOC_TYPES,
    "Rhode Island": RI_DOC_TYPES,
    "Washington": WA_DOC_TYPES,
    "Alabama": AL_DOC_TYPES,
    "California": CA_DOC_TYPES,
    "Colorado": CO_DOC_TYPES,
    "Connecticut": CT_DOC_TYPES,
    "Delaware": DE_DOC_TYPES,
    "Georgia": GA_DOC_TYPES,
    "Hawaii": HI_DOC_TYPES,
    "Kansas": KS_DOC_TYPES,
    "Kentucky": KY_DOC_TYPES,
    "Maryland": MD_DOC_TYPES,
    "Michigan": MI_DOC_TYPES,
    "Minnesota": MN_DOC_TYPES,
    "Missouri": MO_DOC_TYPES,
    "Nebraska": NE_DOC_TYPES,
    "Nevada": NV_DOC_TYPES,
    "New Mexico": NM_DOC_TYPES,
    "Ohio": OH_DOC_TYPES,
    "Pennsylvania": PA_DOC_TYPES,
    "South Carolina": SC_DOC_TYPES,
    "Tennessee": TN_DOC_TYPES,
    "Virginia": VA_DOC_TYPES,
}


# States whose list is fully verified from official sources.
# Only these hide the owner-review note; PARTIAL and generic
# states keep it.
VERIFIED_DOC_STATES = frozenset({
    "New York",
    "New Jersey",
    "District of Columbia",
    "Maine",
    "Rhode Island",
    "Washington",
})


def required_docs_for_state(state):
    """Ordered compulsory doc types for a state; the generic base list
    for any state without a state-specific list."""
    return STATE_DOC_REQUIREMENTS.get(state, GENERIC_DOC_TYPES)


# --- City picker (owner decision 2026-11-17, "City picker bana do,
# Uber jaisa") ------------------------------------------------------------
# Registration asks for the city the driver drives in, right after the
# state, in the same searchable-dropdown pattern (type a letter, see
# every matching city in that state, alphabetical). Uber asks for the
# city at signup and varies requirements by city; Noel keeps the state
# picker and adds the city picker after it.
#
# City NAMES only come from the Census Bureau's July 1, 2025 estimates
# as tabulated on Wikipedia ("List of largest cities of U.S. states
# and territories by population"): the five most populous incorporated
# places per state, plus the capital where it is not among the five.
# Names carry no requirements of their own. Every state's list ends
# with the "Other city" fallback, so a driver in an unlisted town is
# never blocked; "Other city" uses the state list.
#
# EFFECTIVE LIST RULE: a city with a verified city-specific list
# overrides its state list; every other city uses the state list
# unchanged (including the owner-review note where the state has it).
# Dallas, Texas is the FIRST city-specific list. Its items
# come from Uber's official pages only — the Uber Help livery article
# (valid state-issued DMV driving license, commercial insurance,
# vehicle registration, and the City of Dallas or Fort Worth limo
# permit) and the Uber Dallas vehicle-requirements page (Dallas
# Driver Permit required, commercial insurance):
#   https://help.uber.com/en-GB/driving-and-delivering/article/becoming-a-driver-livery?nodeId=d17a342c-ad81-403b-8a4a-14e9ef7300af
#   https://www.uber.com/us/en/drive/requirements/vehicle-requirements/?city=dallas
# Buffalo, New York is the SECOND (owner order 2026-11-17,
# "Buffalo ku tlc nahi chaiye" — TLC is New York City only, so
# Buffalo must not see TLC documents). Its items come from the
# City of Buffalo's official taxi/livery requirements (Office of
# Licenses): licensed as a City of Buffalo Taxi Driver, copy of
# NYS vehicle registration, certificate of automobile liability
# insurance, vehicle inspection report:
#   http://www.buffalony.gov/DocumentCenter/View/11873/taxi-livery-application-_-requirements
# Left out of the Buffalo gate: the worker's compensation /
# exemption certificate (an OR-alternative — Form CE-200 when
# exclusively owner-operated, a certificate otherwise — which
# the gate cannot express, same as other states' OR-alternatives),
# the MV 289 taxi-plate certification (a process: bring the
# registration card, obtain the form, get the plate from the
# DMV), and the license fees (not a document). Because the
# worker's compensation item is named by the city but not gated,
# the owner-review note STAYS ON for Buffalo (see
# CITY_LISTS_WITH_LOCAL_NOTE). Uber's Buffalo page names no TLC
# item either (DMV driving license, proof of residency,
# insurance, photo, background check); the background check is
# never built (owner declined it) and proof of residency is not
# a slot — the city source does not name it.
# Fort Worth was researched the same night (Uber Help + City of Fort
# Worth Ground Transportation Office, Chapter 34 Article VI): Fort
# Worth licenses the OPERATING business, not the individual driver —
# no Fort Worth driver permit document is named anywhere — so Fort
# Worth has NO city-specific list and falls back to the Texas state
# list. Never assume Fort Worth = Dallas. Process-type requirements
# (background checks, exams, courses) are never upload slots, and no
# document count is ever shown ("Quantity nahi").
# Rochester, Syracuse, and Yonkers, New York are the THIRD, FOURTH,
# and FIFTH city-specific lists (owner order 2026-11-17, "Haan bhai
# every city ka wahan ke rules" — every city gets its own local
# rules, verified from official sources only). Zero NYC TLC items
# on any of them: TLC is New York City only.
# Rochester (Municipal Code Chapter 108, Articles II-IV, plus the
# City Clerk permits page): no person shall drive a taxicab within
# the city without a current taxicab driver license issued by the
# City Clerk; a hack plate must be attached and its taxicab license
# certificate carried in the taxicab at all times; the hack-plate
# application requires proof of insurance. No form name (no FH-1,
# no ACORD) is named — none is imported. Inspections are evidenced
# by stickers, not a named report, so no inspection-report slot.
# Left out, with the owner-review note ON: the two-hour training
# session (a course; no certificate of completion is named), the
# DMV license abstract and employment-eligibility verification
# (application inputs; the eligibility proof is an OR-alternative),
# photographs and the police investigation (inputs/process), fees.
# Scope caveat, stated honestly: Rochester's regime is a TAXICAB
# regime under General Municipal Law §181; no separate pre-arranged
# limousine/livery driver license was found. Applying it to Noel
# follows the owner-approved Buffalo precedent; whether a
# pre-arranged-only luxury chauffeur service falls under it is a
# legal-scope question no official source found settles.
#   https://ecode360.com/8678898
#   https://ecode360.com/8678783
#   https://www.cityofrochester.gov/departments/city-clerk/permits-and-licenses
# Syracuse (City of Syracuse Business Licensing Guide 2025,
# Central Permit Office): a Taxi (Hack) License for any owner or
# operator of a taxicab or airbus, a Ground Transportation license
# for any taxicab or airbus operating within city limits, and proof
# of for-hire insurance (the guide's exact wording — NOT labelled
# FH-1; FH-1 appears only in a 2019 airport-authority form). Left
# out, with the owner-review note ON: the Medical Certification
# Form (a named form, but a filing consumed into the Hack License
# — held for an owner decision, same as the other medical items),
# the fingerprint receipt, title document, and photographs
# (application inputs), fees. No vehicle inspection document is
# named in the 2025 guide — none is invented. Syracuse Regional
# Airport Authority requirements are airport-only and are not
# imported. The same taxicab-regime scope caveat as Rochester
# applies (the 2014 bill that would have let Syracuse regulate
# limousines/livery was never enacted).
#   https://www.syr.gov/files/sharedassets/public/v/1/departments/permits/documents/business-license-applications/business-licensing-guide-2025.pdf
# Yonkers (Westchester County Taxi and Limousine Commission
# For-Hire Rules and Regulations v4.2, June 17, 2022): the WCTLC
# licenses for-hire drivers and vehicles county-wide, expressly
# including "livery", "car service", "black car", and "limousine".
# The list gates the WCTLC for-hire driver permit, the WCTLC
# for-hire vehicle permit, proof of adequate insurance (NOT
# labelled FH-1/ACORD — those appear only on an archived
# municipal-car form), and proof of completion of a NYS
# DMV-certified Defensive Driving Course (a named certificate, so
# slot-eligible). WCTLC is a DIFFERENT commission from NYC TLC —
# never label its items NYC TLC. Left out, with the owner-review
# note ON: the Social Security card OR SSA correspondence
# (OR-alternative + the same privacy flag as the other SSN items —
# owner decision required before any slot), fingerprinting,
# references, drug testing, fees, and the base-station affiliation
# (a structural gap: Noel is not stated to be a WCTLC base
# station). UNRESOLVED: the City of Yonkers ALSO has its own
# taxicab driver license and Class B regime (City Code Chapter
# 110); no official source states whether both are required
# together or one exempts the other. The city license is NOT
# gated silently — the owner decides stacking vs. WCTLC-only.
#   https://tlc.westchestercountyny.gov/images/archive/stories/pdfs/2022rulesregv4.2.pdf
# Albany, New York keeps the state-list fallback: the city
# REPEALED its taxicab licensing article in 2024 (Ordinance
# 2.21.24, adopted May 6, 2024) after having stopped issuing and
# requiring licenses toward the end of 2020 — an affirmative
# repeal, not an inconclusive finding. New York City itself keeps
# the 7-doc state list, re-verified item by item from official
# NYC TLC sources the same night. Long Island runs on the NY
# state TLC list by explicit owner decision ("Mein chah raha hoon
# Long Island poora TLC pe chale") — no county overrides, no code
# change; the "Other city" fallback already does exactly this.
OTHER_CITY = "Other city"

CITIES_BY_STATE = {
    "Alabama": ["Birmingham", "Huntsville", "Mobile", "Montgomery", "Tuscaloosa"],
    "Alaska": ["Anchorage", "Fairbanks", "Juneau", "Sitka", "Wasilla"],
    "Arizona": ["Chandler", "Gilbert", "Mesa", "Phoenix", "Tucson"],
    "Arkansas": ["Fayetteville", "Fort Smith", "Jonesboro", "Little Rock", "Springdale"],
    "California": ["Fresno", "Los Angeles", "Sacramento", "San Diego", "San Francisco", "San Jose"],
    "Colorado": ["Aurora", "Colorado Springs", "Denver", "Fort Collins", "Lakewood"],
    "Connecticut": ["Bridgeport", "Hartford", "New Haven", "Stamford", "Waterbury"],
    "Delaware": ["Dover", "Middletown", "Milford", "Newark", "Wilmington"],
    "District of Columbia": ["Washington, D.C."],
    "Florida": ["Jacksonville", "Miami", "Orlando", "Port St. Lucie", "Tallahassee", "Tampa"],
    "Georgia": ["Atlanta", "Augusta", "Columbus", "Macon", "Savannah"],
    "Hawaii": ["East Honolulu", "Hilo", "Honolulu", "Pearl City", "Waipahu"],
    "Idaho": ["Boise", "Caldwell", "Idaho Falls", "Meridian", "Nampa"],
    "Illinois": ["Aurora", "Chicago", "Joliet", "Naperville", "Rockford", "Springfield"],
    "Indiana": ["Carmel", "Evansville", "Fishers", "Fort Wayne", "Indianapolis"],
    "Iowa": ["Ankeny", "Cedar Rapids", "Davenport", "Des Moines", "Sioux City"],
    "Kansas": ["Kansas City", "Olathe", "Overland Park", "Topeka", "Wichita"],
    "Kentucky": ["Bowling Green", "Covington", "Frankfort", "Lexington", "Louisville", "Owensboro"],
    "Louisiana": ["Baton Rouge", "Lafayette", "Lake Charles", "New Orleans", "Shreveport"],
    "Maine": ["Auburn", "Augusta", "Bangor", "Lewiston", "Portland", "South Portland"],
    "Maryland": ["Annapolis", "Baltimore", "Bowie", "Frederick", "Gaithersburg", "Rockville"],
    "Massachusetts": ["Boston", "Cambridge", "Lowell", "Springfield", "Worcester"],
    "Michigan": ["Ann Arbor", "Detroit", "Grand Rapids", "Lansing", "Sterling Heights", "Warren"],
    "Minnesota": ["Bloomington", "Duluth", "Minneapolis", "Rochester", "Saint Paul"],
    "Mississippi": ["Biloxi", "Gulfport", "Hattiesburg", "Jackson", "Southaven"],
    "Missouri": ["Columbia", "Independence", "Jefferson City", "Kansas City", "Saint Louis", "Springfield"],
    "Montana": ["Billings", "Bozeman", "Butte", "Great Falls", "Helena", "Missoula"],
    "Nebraska": ["Bellevue", "Grand Island", "Kearney", "Lincoln", "Omaha"],
    "Nevada": ["Carson City", "Henderson", "Las Vegas", "North Las Vegas", "Reno", "Sparks"],
    "New Hampshire": ["Concord", "Derry", "Dover", "Manchester", "Nashua"],
    "New Jersey": ["Elizabeth", "Jersey City", "Lakewood", "Newark", "Paterson", "Trenton"],
    "New Mexico": ["Albuquerque", "Las Cruces", "Rio Rancho", "Roswell", "Santa Fe"],
    "New York": ["Albany", "Buffalo", "New York", "Rochester", "Syracuse", "Yonkers"],
    "North Carolina": ["Charlotte", "Durham", "Greensboro", "Raleigh", "Winston-Salem"],
    "North Dakota": ["Bismarck", "Fargo", "Grand Forks", "Minot", "West Fargo"],
    "Ohio": ["Akron", "Cincinnati", "Cleveland", "Columbus", "Toledo"],
    "Oklahoma": ["Broken Arrow", "Edmond", "Norman", "Oklahoma City", "Tulsa"],
    "Oregon": ["Eugene", "Gresham", "Hillsboro", "Portland", "Salem"],
    "Pennsylvania": ["Allentown", "Erie", "Harrisburg", "Philadelphia", "Pittsburgh", "Reading"],
    "Rhode Island": ["Cranston", "East Providence", "Pawtucket", "Providence", "Warwick"],
    "South Carolina": ["Charleston", "Columbia", "Mount Pleasant", "North Charleston", "Rock Hill"],
    "South Dakota": ["Aberdeen", "Brookings", "Pierre", "Rapid City", "Sioux Falls", "Watertown"],
    "Tennessee": ["Chattanooga", "Clarksville", "Knoxville", "Memphis", "Nashville"],
    "Texas": ["Austin", "Dallas", "Fort Worth", "Houston", "San Antonio"],
    "Utah": ["Provo", "Salt Lake City", "St. George", "West Jordan", "West Valley City"],
    "Vermont": ["Bennington", "Burlington", "Colchester", "Montpelier", "Rutland", "South Burlington"],
    "Virginia": ["Chesapeake", "Newport News", "Norfolk", "Richmond", "Virginia Beach"],
    "Washington": ["Bellevue", "Olympia", "Seattle", "Spokane", "Tacoma", "Vancouver"],
    "West Virginia": ["Charleston", "Huntington", "Morgantown", "Parkersburg", "Wheeling"],
    "Wisconsin": ["Green Bay", "Kenosha", "Madison", "Milwaukee", "Racine"],
    "Wyoming": ["Casper", "Cheyenne", "Gillette", "Laramie", "Rock Springs"],
}

# Dallas, Texas (VERIFIED from the Uber official pages above). The
# limo-permit slot accepts either city's permit, exactly as Uber
# words it ("City of Dallas or Fort Worth limo permit"). No
# background check, no age/experience gate: the owner declined the
# background check outright ("nahi background check nahi chahiye").
DALLAS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "dallas_commercial_insurance",
    "dallas_driver_permit",
    "dallas_limo_permit",
]

# Buffalo, New York (VERIFIED from the City of Buffalo official
# requirements above). Zero TLC items: TLC is New York City only.
# No background check, no age/experience gate: the owner declined
# the background check outright ("nahi background check nahi
# chahiye"). The inspection slot is the city's Vehicle Inspection
# Report, distinct from the New York "NYS DMV Inspection" slot.
BUFFALO_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "buffalo_taxi_driver_license",
    "vehicle_registration",
    "buffalo_insurance_certificate",
    "buffalo_inspection_report",
]

# Rochester, New York (VERIFIED from Rochester Municipal Code
# Chapter 108, Articles II-IV, and the City Clerk permits page
# above). Zero TLC items. No background check, no age/experience
# gate: the owner declined the background check outright ("nahi
# background check nahi chahiye").
ROCHESTER_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "rochester_taxi_driver_license",
    "rochester_hack_certificate",
    "rochester_insurance",
]

# Syracuse, New York (VERIFIED from the City of Syracuse Business
# Licensing Guide 2025, Central Permit Office, above). Zero TLC
# items. No background check, no age/experience gate.
SYRACUSE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "syracuse_hack_license",
    "syracuse_ground_transportation",
    "syracuse_for_hire_insurance",
]

# Yonkers, New York (VERIFIED from the Westchester County Taxi
# and Limousine Commission For-Hire Rules v4.2 above). Zero NYC
# TLC items: WCTLC is a different commission. No background
# check, no age/experience gate.
YONKERS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "wctlc_driver_permit",
    "wctlc_vehicle_permit",
    "wctlc_insurance",
    "wctlc_defensive_driving",
]

# Southeast batch (owner order 2026-11-17, "every city ka wahan ke
# rules"). Sixteen city-specific lists, each verified from official
# sources only; the five thin ones (Birmingham, Mobile, Montgomery,
# Tallahassee, Durham) were re-verified by the coordinator before
# build — see the ledger (CITY_RESEARCH.md). No background check
# anywhere; no age/experience gate; no document count.
# Birmingham, AL: Ordinance 14-5, Title 12 Ch. 16 (Taxis and
# Vehicles for Hire): an Operator's Permit is required to drive a
# vehicle for hire, and §12-16-51 requires the driver to carry a
# valid Alabama driver license, a current health and welfare
# certificate, and a current Operator's Permit. The health and
# welfare certificate is a PHYSICIAN'S certificate after a
# physical/mental exam — a medical item, HELD for an owner
# decision (same privacy handling as the other medical items), so
# the gate asks only for the Operator's Permit and the
# owner-review note stays ON. Currency caveat: the ordinance copy
# is hosted on the airport site; no repeal was found.
# Huntsville, AL: City Chauffeur License (Chief of Police), from
# the city ordinance. Supporting documents were not retrieved —
# nothing is invented, and the owner-review note stays ON.
# Mobile, AL: Chauffeur's license issued by the Police Department
# on ALL drivers (Certificate of Public Convenience and Necessity
# application packet, City Code Ch. 59, which covers taxicab,
# shuttle, limousine, carriage, and charter service). The packet's
# insurance and inspection-certificate filings belong to the
# company-level CPNC application, not to the driver — not slots.
# Montgomery, AL: Chauffeur's License Packet (Risk Management
# Department, Ordinance Ch. 6 Art. VIII — Vehicles for Hire). The
# packet contents were not retrieved — nothing is invented, and
# the owner-review note stays ON.
# Miami, FL: Miami-Dade Chauffeur Registration (county
# chauffeur application). Identity proof is an OR-alternative
# (SSN card OR passport OR birth certificate) — NO SSN slot, and
# the owner-review note stays ON.
# Orlando, FL: City of Orlando Driver Permit + Certificate of
# Insurance (commercial, City as additional insured), from the
# city's transportation-company page and Uber's official Orlando
# vehicle-requirements page.
# Tallahassee, FL: City of Tallahassee Driver Permit (Ordinance
# 15-O-10AA, 2015, Ch. 22 — Vehicles for Hire: "Driver means an
# individual permitted to drive a vehicle for hire"; "Limousine"
# is defined as a prearranged chauffeured luxury vehicle). Currency
# was not re-verified and no repeal was found, so the owner-review
# note stays ON.
# Tampa, FL: Hillsborough County Public Vehicle Driver License
# (PVDL) + Seven-Year Driver License Transcript (County Code
# Ch. 10 Art. XV).
# Baton Rouge, LA: Chauffeur License / Operator Permit + Official
# Driving Record + Clearance Certificate (city Chauffeurs page
# and Operators Permit and ID Badge Procedures).
# New Orleans, LA: Driver Permit for CPNC (covers Limousine) +
# Certified MVR (2-year, within 30 days), from the city's driver
# permit page. A defensive-driving certificate and proof of
# residency appear only in an older checklist — NOT included.
# Biloxi and Gulfport, MS: MVFHA Driver Permit, from the SAME
# Harrison County interlocal Authority (Mississippi Vehicle for
# Hire Authority) — one shared document type, not two cities
# copying each other.
# Charlotte, NC: PVH Driver Permit + Driving Record(s), from the
# city police PVH driver permit package. The SSN card named in
# the packet (bring the original, "DO NOT EMAIL") is HELD for an
# owner decision — NO SSN slot, owner-review note ON.
# Durham, NC: PVFH Driver Permit (City Code Ch. 50 Art. III; the
# program regulates taxicabs, limousines, limousine sedans,
# shuttles, and para-transits). The New Driver Permit Checklist
# was retrieved: the Physician's Statement (medical) and the
# Social Security Card are HELD for owner decisions, immigration
# information is an OR-alternative, and the Operator's Permission
# Form is an operator-affiliation gap — the owner-review note
# stays ON.
# Charleston, SC: Chauffeur License + Certified 10-Year Driving
# Record (Vehicle for Hire Ordinance). The Signed Medical
# Statement is a medical item, HELD for an owner decision. The
# ordinance offers an OR-alternative (city license OR licensee
# endorsement) — the owner-review note stays ON.
# Nashville, TN: MTLC OPVH Driver Permit + Motor Vehicle Record
# (within 30 days), from the OPVH Driver Permit Checklist (Oct
# 2022). Citizenship/ICE proof is an OR-alternative — the
# owner-review note stays ON. SSN, birth certificate, and
# training items appear only in a non-official draft — NOT
# included.
BIRMINGHAM_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "birmingham_operator_permit",
]

HUNTSVILLE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "huntsville_chauffeur_license",
]

MOBILE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "mobile_chauffeur_license",
]

MONTGOMERY_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "montgomery_chauffeur_license",
]

MIAMI_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "miami_chauffeur_registration",
]

ORLANDO_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "orlando_driver_permit",
    "orlando_insurance",
]

TALLAHASSEE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "tallahassee_driver_permit",
]

TAMPA_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "tampa_pvdl",
    "tampa_transcript",
]

BATON_ROUGE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "baton_rouge_chauffeur_license",
    "baton_rouge_driving_record",
    "baton_rouge_clearance",
]

NEW_ORLEANS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "new_orleans_driver_permit",
    "new_orleans_mvr",
]

BILOXI_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "mvfha_driver_permit",
]

GULFPORT_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "mvfha_driver_permit",
]

CHARLOTTE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "charlotte_pvh_permit",
    "charlotte_driving_record",
]

DURHAM_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "durham_pvfh_permit",
]

CHARLESTON_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "charleston_chauffeur_license",
    "charleston_driving_record",
]

NASHVILLE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "nashville_opvh_permit",
    "nashville_mvr",
]

# Midwest batch (owner order 2026-11-17, "every city ka wahan ke
# rules"). City-specific lists, each verified from official sources
# only — see the ledger (CITY_RESEARCH.md). No background check
# anywhere; no age/experience gate; no document count. Medical and
# Social Security items are HELD for owner decisions wherever a
# city names them (Kansas City, Saint Louis, Springfield IL,
# Indianapolis) — never gated silently, and the owner-review note
# stays ON for those cities. Fort Wayne, Sioux Falls, and Toledo
# were banked but DROPPED at build-time re-verification (Fort
# Wayne: taxi-only stale chapter, no issuance confirmed; Sioux
# Falls: no driver-license name, form, or limousine scope
# verified; Toledo: the cited section is the low-speed-vehicle
# chapter, and the real chapter's text could not be retrieved) —
# all three keep the state-list fallback; see the ledger.
# Chicago, IL: Restricted Livery Public Chauffeur License (BACP)
# + Livery Vehicle License + Commercial Insurance Certificate
# ($350k combined single limit, City as additional insured), from
# the city BACP livery page and Uber's official Chicago
# vehicle-requirements page. Training, exam, fingerprinting, drug
# test, and physical are process, not slots.
# Rockford, IL: Taxi Cab Driver License (city application); the
# vehicle license expressly applies to livery, so the scope is
# confirmed and the note stays off.
# Springfield, IL: Taxicab Driver License (City Clerk). The
# application asks for a Social Security card photocopy — NO slot
# without an owner decision — and the taxi-vs-limousine scope is
# unverified, so the owner-review note stays ON.
# Evansville, IN: City of Evansville Taxicab Driver License
# (Municipal Code §5.40.050).
# Indianapolis, IN: Operator License (public vehicle for hire) +
# Taxi Training Course Certificate + Certified BMV Driving Record
# (within 10 days), from the city requirements sheet and Municode
# Ch. 996. A Social Security / work-authorization card is flagged
# but NOT a slot; the Super Service certificate is NOT included
# (scope unverified); the owner-review note stays ON.
# Minneapolis, MN: Taxi Driver License + Taxi Driver Training
# Certificate (city business-licenses page). Conditional items
# (other-state reports, experience proof) and the company
# authorization are gaps the gate cannot express, and the scope
# is taxi-framed, so the owner-review note stays ON.
# Rochester, MN: Taxicab Driver License / Driver Permit ($110/yr,
# city applications page). The livery scope is flagged, so the
# owner-review note stays ON. (Rochester, NY keeps its own list.)
# Saint Paul, MN: Taxicab Driver License + Taxicab Driver
# Training Course completion proof (city business-licenses page).
# A DOT medical card appears only on a 2016 form and is omitted
# from the current page — NOT included.
# Columbia, MO: Chauffeur License (taxi/limousine expressly
# included, city business-licenses page). A letter-of-intent gap
# keeps the owner-review note ON.
# Independence, MO: Vehicle Driver Permit (Taxi Driver Permit,
# 2023 application packet). The packet is taxi/jitney/sightseeing
# framed with a meter requirement, so the scope flag keeps the
# owner-review note ON.
# Jefferson City, MO: Taxi Driver Permit + Certified Driving
# Record (MO DOR), from the current application form (rev.
# 7-31-2025). The drug/alcohol screening certificate and the
# fingerprint search are gaps, so the owner-review note stays ON.
# Kansas City, MO (Missouri side only — never copy Ch. 76 across
# the state line to Kansas City, KS): Vehicle-for-Hire Driver
# Certificate (Livery) + State Operating Record (KCMO Regulated
# Industries, Municode §§76-102/76-103). The physical-exam copy
# and the Social Security / work-authorization proof are HELD for
# owner decisions, so the owner-review note stays ON.
# Saint Louis, MO: MTC Driver License (limousine/premium sedan
# class) + Missouri Driver History Report (within 10 days), from
# the Metropolitan Taxicab Commission licensing page. The
# physical exam results and the Social Security / work-eligibility
# proof are HELD for owner decisions, so the owner-review note
# stays ON.
# Lincoln, NE: Taxicab Driver License (Code Ch. 5.50, city
# application). Employer-tied and livery-scope flags, and
# medical/exam gaps, keep the owner-review note ON.
# Kenosha, WI: Taxi Driver License (active issuance proven in
# 2025-2026 council minutes). No checklist was found and the
# livery scope is flagged, so the owner-review note stays ON.
# Madison, WI: Public Passenger Vehicle Driver Permit (Code
# Ch. 11, Chief of Police; Municode Ch. 11 + 2023 Dane County
# decision).
# Milwaukee, WI: Public Passenger Vehicle Driver License
# (limousine expressly included; TNC-only drivers exempt, city
# application ccl-DRN).
# Columbus, OH: Vehicle for Hire Driver License (Code Ch. 589,
# incl. livery) + Certified Ohio BMV Driver Abstract (within 30
# days, required for new or expired applicants), from the City
# License Section page and the current VFH Driver Application
# (08-27-26; category checkboxes include "Livery"). The verbatim
# Ch. 589 code text could not be retrieved (Municode returned
# 403), so the list rests on the licensing-office sources, not a
# code quote. The Experience Columbus Insider accreditation is
# Professional-license-only (conditional, not gated); the BCI
# background check is never built; the form's last-four SSN
# digits are a flag, not a slot; and the owner-license
# affiliation in CCC 589.02(a)(1) is a structural gap — the
# owner-review note stays ON.
CHICAGO_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "chicago_chauffeur_license",
    "chicago_livery_vehicle_license",
    "chicago_insurance_certificate",
]

ROCKFORD_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "rockford_taxi_driver_license",
]

SPRINGFIELD_IL_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "springfield_il_taxi_driver_license",
]

EVANSVILLE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "evansville_taxi_driver_license",
]

INDIANAPOLIS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "indianapolis_operator_license",
    "indianapolis_training_certificate",
    "indianapolis_bmv_record",
]

MINNEAPOLIS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "minneapolis_taxi_driver_license",
    "minneapolis_training_certificate",
]

ROCHESTER_MN_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "rochester_mn_taxi_driver_license",
]

SAINT_PAUL_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "saint_paul_taxi_driver_license",
    "saint_paul_training_proof",
]

COLUMBIA_MO_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "columbia_chauffeur_license",
]

INDEPENDENCE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "independence_vehicle_driver_permit",
]

JEFFERSON_CITY_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "jefferson_city_taxi_driver_permit",
    "jefferson_city_driving_record",
]

KANSAS_CITY_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "kansas_city_driver_certificate",
    "kansas_city_operating_record",
]

SAINT_LOUIS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "saint_louis_mtc_license",
    "saint_louis_driver_history",
]

LINCOLN_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "lincoln_taxi_driver_license",
]

KENOSHA_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "kenosha_taxi_driver_license",
]

MADISON_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "madison_ppv_permit",
]

MILWAUKEE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "milwaukee_ppv_license",
]

COLUMBUS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "columbus_vfh_license",
    "columbus_bmv_abstract",
]

# Northeast batch (owner order 2026-11-17, "every city ka wahan ke
# rules"). City-specific lists, each verified from official sources
# only — see the ledger (CITY_RESEARCH.md). No background check
# anywhere; no age/experience gate; no document count. Social
# Security and medical items are HELD for owner decisions wherever
# a city names them (Springfield MA, Philadelphia) — never gated
# silently, and the owner-review note stays ON for those cities.
# Newark, NJ and Rutland, VT were banked but DROPPED at build-time
# re-verification (Newark: no operative Ch. 34:2 text retrievable,
# no Ch. 34:3 OR-alternative found, no current issuance evidence;
# Rutland: no operative chapter text or definition retrieved, and
# the cited "Subch. 3" is a charter power grant, not a license
# requirement) — both keep the state-list fallback; see the ledger.
# Portland, ME: Livery Driver License (Ch. 30 §§30-31/30-32; the
# separate livery/taxi application forms and fees confirm a distinct
# livery license). Section 30-17A is "Service on Peaks Island" and
# imposes livery licensing there — it exempts nothing relevant;
# "Livery" (§30-16) means prearranged hourly/flat-rate service,
# exactly the app-dispatched model. The vehicle business-license
# coverage in §30-31(b) is a structural gap, so the owner-review
# note stays ON.
# South Portland, ME: Taxicab Driver License (Ch. 14 §§14-7/14-8;
# the application calls it a "Taxi Operator License"). The
# reciprocity exception is unverified, so the owner-review note
# stays ON.
# Lowell, MA: Hackney License (Ch. 243-3, Police Department; the
# application covers hackney driver + taxi/limo/PTV).
# Springfield, MA: Chauffeur License (Ch. 305 §305-3: no person
# shall drive a taxicab, livery vehicle, or other vehicle for hire
# without it). Citizenship/SSN/medical inputs are flagged but NOT
# slots, so the owner-review note stays ON.
# Worcester, MA: Taxi-Livery Driver License (city Taxi & Livery
# applications page; "Vehicles for Hire" rule §11).
# Jersey City, NJ: Limousine Driver License (Municipal Code
# §5-5.1(b): no person shall operate a limousine without a driver
# license; the livery/limousine scope is express). The state-law
# caveat (only the home municipality may license) is satisfied:
# the driver lives in Jersey City by definition of the picker.
# Philadelphia, PA: PPA Limousine Driver Certificate (Philadelphia
# Parking Authority; limousine class driver certificate). Social
# Security and work-authorization inputs are flagged but NOT slots,
# so the owner-review note stays ON.
PORTLAND_ME_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "portland_me_livery_license",
]

SOUTH_PORTLAND_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "south_portland_taxi_driver_license",
]

LOWELL_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "lowell_hackney_license",
]

SPRINGFIELD_MA_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "springfield_ma_chauffeur_license",
]

WORCESTER_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "worcester_taxi_livery_license",
]

JERSEY_CITY_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "jersey_city_limo_driver_license",
]

PHILADELPHIA_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "philadelphia_limo_certificate",
]

# South Central/Mountain batch (owner order 2026-11-17, "every city
# ka wahan ke rules"; Uber cross-check per the owner instruction of
# 2026-11-18). City-specific lists, each verified from official
# sources only — see the ledger (CITY_RESEARCH.md). No background
# check anywhere; no age/experience gate; no document count. Medical
# and Social Security items are HELD for owner decisions wherever a
# city names them (Oklahoma City, Tulsa, Gillette) — never gated
# silently, and the owner-review note stays ON for those cities.
# Norman, OK was banked but DROPPED at build-time re-verification
# (live Municode text unretrievable; unresolved Ch. 13 to Ch. 20
# renumbering question) and Denver, CO stays on the state-list
# fallback (current Ch. 55 text unretrievable) — see the ledger.
# Uber cross-check (2026-11-18): Uber city pages were retrieved
# in full only for Las Vegas (MATCH on the Clark County item, TNC
# framing only), Houston, San Antonio, Tulsa, and Oklahoma City;
# for the other cities only the generic Uber template page was
# retrieved, which names no city permit anywhere — partial
# evidence, recorded in the ledger, not treated as proof Uber has
# no requirement. The Las Vegas vehicle inspection form is NOT
# built (in-person step; flagged to the parent per the
# registration-ease rule). The Houston For Hire Permit named by
# Uber reads vehicle-level and Black-only, so it is NOT a driver
# slot; the banked driver license stands on the ARA source. Proof
# of residency (Uber template boilerplate) is NOT added to any
# city list.
# Little Rock, AR: Ground Transportation Service Driver Permit
# (Ch. 34, Ord. 19051; "ground transportation service" expressly
# includes limousine/luxury/pre-arranged service; currency
# confirmed by Res. 16,914 for 2026 permits).
# Springdale, AR: Taxicab Driver Permit (Ch. 122 Art. II
# §§122-26/122-27; "taxicab" defined broadly with no limousine
# exclusion).
# Boise, ID: Commercial Transportation Service Driver License
# (Title 3 Ch. 13B §3-13B-7; "Limousine Service" defined as
# prearranged luxury service).
# Idaho Falls, ID: Public Transportation Operator License (Title
# 4 Ch. 15 §4-15-4; prearranged appointment service within 25
# miles). The Operator OR Owner license alternative keeps the
# owner-review note ON.
# Oklahoma City, OK: Vehicle-for-Hire Driver Permit (Ch. 56 Div.
# 5; city regulates taxicabs/limos/shuttles on pickups within the
# city). The driver medical certification is HELD, so the
# owner-review note stays ON.
# Tulsa, OK: Chauffeur License + MVR Report (within 30 days),
# from the live Business Licensing page and the chauffeur new
# application (MVR required for NEW applications too). The SSN
# card and the physical exam form are HELD; the holder
# recommendation is an affiliation gap — the owner-review note
# stays ON. Title 36 Ch. 1 definitions text was not retrieved;
# the list rests on the licensing-office forms.
# Austin, TX: Chauffeur Permit (city chauffeur-permit page:
# allows driving a vehicle for hire, including limousines;
# issued same day on passing a written test). Defensive-driving
# proof is conditional (moving-violation convictions only), so
# the owner-review note stays ON.
# Houston, TX: City-Issued Vehicle-for-Hire Driver License (ARA:
# every person driving a vehicle for hire must obtain a city
# issued driver license; categories expressly include
# chauffeured limousine services).
# San Antonio, TX: Driver Permit (Ch. 33 Art. I §33-039;
# Limousine/Luxury Vehicle Rules §950). The approved driver
# training program question keeps the owner-review note ON.
# St. George, UT: For-Hire Driver Permit (Art. O §3-2O-6;
# "For-Hire Vehicle" expressly includes limousines). The
# verbatim code text was not retrieved, but official city
# checklists name the permit and the 2024 register shows live
# issuance — the owner-review note stays ON for the code-text
# gap.
# Cheyenne, WY: Public Transportation Driver Permit (Title 5
# Ch. 5.72; conveyance includes taxicab/limousine/carriage).
# Gillette, WY: Public Transportation Driver Permit (Ch. 19
# §19.3(A); §19.1(C) defines the conveyance to include
# limousine; current posted text read end to end). The
# SSN-adjacent application input is held, so the owner-review
# note stays ON.
# Henderson, Las Vegas, and North Las Vegas, NV: one shared
# county-level item, the Clark County Business License. The
# livery scope is evidenced for TNC drivers only, so the
# owner-review note stays ON for all three (owner question).
LITTLE_ROCK_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "little_rock_gt_driver_permit",
]

SPRINGDALE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "springdale_taxi_driver_permit",
]

BOISE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "boise_cts_driver_license",
]

IDAHO_FALLS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "idaho_falls_operator_license",
]

OKLAHOMA_CITY_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "okc_vfh_driver_permit",
]

TULSA_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "tulsa_chauffeur_license",
    "tulsa_mvr",
]

AUSTIN_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "austin_chauffeur_permit",
]

HOUSTON_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "houston_vfh_driver_license",
]

SAN_ANTONIO_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "san_antonio_driver_permit",
]

ST_GEORGE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "st_george_for_hire_permit",
]

CHEYENNE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "cheyenne_pt_driver_permit",
]

GILLETTE_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "gillette_pt_driver_permit",
]

HENDERSON_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "clark_county_business_license",
]

LAS_VEGAS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "clark_county_business_license",
]

NORTH_LAS_VEGAS_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "clark_county_business_license",
]

# West/Pacific batch (owner order 2026-11-17, "every city ka wahan
# ke rules"; Uber cross-check per the owner instruction of
# 2026-11-18). The last batch: Portland, OR only. Anchorage,
# Fairbanks, and Juneau, AK were banked but DROPPED at build-time
# re-verification (operative code text unretrievable in all three;
# Juneau limousine coverage unproven from Juneau sources) — all
# three keep the state-list fallback; see the ledger. No background
# check anywhere; no age/experience gate; no document count.
# Portland, OR: Executive Town Car Driver Certification +
# City of Portland Business License, from current City Code
# §16.40.370(A) (drivers must be certified/permitted by the City
# Administrator prior to operating; 1-year term; "Executive Town
# Car" includes 4-door sedans/SUVs) and §16.40.370(H)
# (independent-contractor drivers must comply with the Business
# License Law, Ch. 7.02; no certification without it). The LPT
# regime (§16.40.670) imposes the identical two requirements for
# stretch limousines. The code calls it certification via a
# company-submitted driver list, so the label says certification.
# Training/testing is process (no named certificate); the ASE
# inspection is conditional and vehicle-level. The FASTTRACK
# portal checklist itself is login-gated and unretrieved, so the
# owner-review note stays ON. Uber cross-check: Uber Portland
# pages MATCH the business license (free; upload artifact is the
# Certificate of Compliance, named in the slot hint) but name a
# display-only TNC for-hire permit instead of the certification —
# a regime difference, flagged in the ledger; the certification
# stands on the verbatim code text. The Uber-named vehicle
# inspection form is NOT built (in-person step; flagged to the
# parent per the registration-ease rule). Generic vehicle
# insurance is NOT added (Uber US-wide upload, not a
# Portland-named document; Oregon fallback cities keep the
# insurance slot via the generic state list).
PORTLAND_OR_DOC_TYPES = [
    "profile_picture",
    "dmv_license",
    "vehicle_registration",
    "portland_or_certification",
    "portland_or_business_license",
]

# (state, city) -> city-specific list. 62 cities today (Dallas,
# Buffalo, Rochester, Syracuse, Yonkers, the 16-city Southeast
# batch, the 18-city Midwest batch, the 7-city Northeast batch,
# the 15-city South Central/Mountain batch, and Portland, OR);
# a city is added here ONLY with a verified official source
# naming its items.
CITY_DOC_REQUIREMENTS = {
    ("Texas", "Dallas"): DALLAS_DOC_TYPES,
    ("New York", "Buffalo"): BUFFALO_DOC_TYPES,
    ("New York", "Rochester"): ROCHESTER_DOC_TYPES,
    ("New York", "Syracuse"): SYRACUSE_DOC_TYPES,
    ("New York", "Yonkers"): YONKERS_DOC_TYPES,
    ("Alabama", "Birmingham"): BIRMINGHAM_DOC_TYPES,
    ("Alabama", "Huntsville"): HUNTSVILLE_DOC_TYPES,
    ("Alabama", "Mobile"): MOBILE_DOC_TYPES,
    ("Alabama", "Montgomery"): MONTGOMERY_DOC_TYPES,
    ("Florida", "Miami"): MIAMI_DOC_TYPES,
    ("Florida", "Orlando"): ORLANDO_DOC_TYPES,
    ("Florida", "Tallahassee"): TALLAHASSEE_DOC_TYPES,
    ("Florida", "Tampa"): TAMPA_DOC_TYPES,
    ("Louisiana", "Baton Rouge"): BATON_ROUGE_DOC_TYPES,
    ("Louisiana", "New Orleans"): NEW_ORLEANS_DOC_TYPES,
    ("Mississippi", "Biloxi"): BILOXI_DOC_TYPES,
    ("Mississippi", "Gulfport"): GULFPORT_DOC_TYPES,
    ("North Carolina", "Charlotte"): CHARLOTTE_DOC_TYPES,
    ("North Carolina", "Durham"): DURHAM_DOC_TYPES,
    ("South Carolina", "Charleston"): CHARLESTON_DOC_TYPES,
    ("Tennessee", "Nashville"): NASHVILLE_DOC_TYPES,
    ("Illinois", "Chicago"): CHICAGO_DOC_TYPES,
    ("Illinois", "Rockford"): ROCKFORD_DOC_TYPES,
    ("Illinois", "Springfield"): SPRINGFIELD_IL_DOC_TYPES,
    ("Indiana", "Evansville"): EVANSVILLE_DOC_TYPES,
    ("Indiana", "Indianapolis"): INDIANAPOLIS_DOC_TYPES,
    ("Minnesota", "Minneapolis"): MINNEAPOLIS_DOC_TYPES,
    ("Minnesota", "Rochester"): ROCHESTER_MN_DOC_TYPES,
    ("Minnesota", "Saint Paul"): SAINT_PAUL_DOC_TYPES,
    ("Missouri", "Columbia"): COLUMBIA_MO_DOC_TYPES,
    ("Missouri", "Independence"): INDEPENDENCE_DOC_TYPES,
    ("Missouri", "Jefferson City"): JEFFERSON_CITY_DOC_TYPES,
    ("Missouri", "Kansas City"): KANSAS_CITY_DOC_TYPES,
    ("Missouri", "Saint Louis"): SAINT_LOUIS_DOC_TYPES,
    ("Nebraska", "Lincoln"): LINCOLN_DOC_TYPES,
    ("Ohio", "Columbus"): COLUMBUS_DOC_TYPES,
    ("Wisconsin", "Kenosha"): KENOSHA_DOC_TYPES,
    ("Wisconsin", "Madison"): MADISON_DOC_TYPES,
    ("Wisconsin", "Milwaukee"): MILWAUKEE_DOC_TYPES,
    ("Maine", "Portland"): PORTLAND_ME_DOC_TYPES,
    ("Maine", "South Portland"): SOUTH_PORTLAND_DOC_TYPES,
    ("Massachusetts", "Lowell"): LOWELL_DOC_TYPES,
    ("Massachusetts", "Springfield"): SPRINGFIELD_MA_DOC_TYPES,
    ("Massachusetts", "Worcester"): WORCESTER_DOC_TYPES,
    ("New Jersey", "Jersey City"): JERSEY_CITY_DOC_TYPES,
    ("Pennsylvania", "Philadelphia"): PHILADELPHIA_DOC_TYPES,
    ("Arkansas", "Little Rock"): LITTLE_ROCK_DOC_TYPES,
    ("Arkansas", "Springdale"): SPRINGDALE_DOC_TYPES,
    ("Idaho", "Boise"): BOISE_DOC_TYPES,
    ("Idaho", "Idaho Falls"): IDAHO_FALLS_DOC_TYPES,
    ("Oklahoma", "Oklahoma City"): OKLAHOMA_CITY_DOC_TYPES,
    ("Oklahoma", "Tulsa"): TULSA_DOC_TYPES,
    ("Texas", "Austin"): AUSTIN_DOC_TYPES,
    ("Texas", "Houston"): HOUSTON_DOC_TYPES,
    ("Texas", "San Antonio"): SAN_ANTONIO_DOC_TYPES,
    ("Utah", "St. George"): ST_GEORGE_DOC_TYPES,
    ("Wyoming", "Cheyenne"): CHEYENNE_DOC_TYPES,
    ("Wyoming", "Gillette"): GILLETTE_DOC_TYPES,
    ("Nevada", "Henderson"): HENDERSON_DOC_TYPES,
    ("Nevada", "Las Vegas"): LAS_VEGAS_DOC_TYPES,
    ("Nevada", "North Las Vegas"): NORTH_LAS_VEGAS_DOC_TYPES,
    ("Oregon", "Portland"): PORTLAND_OR_DOC_TYPES,
}

# City-specific lists that KEEP the owner-review note: Buffalo's
# city source names the worker's compensation / exemption
# certificate, which the gate cannot express (OR-alternative), so
# the owner reviews each Buffalo application. Rochester's, Syracuse's,
# and Yonkers' sources likewise name items the gate cannot express
# (Rochester: training + eligibility OR-alternative; Syracuse:
# medical form + inputs; Yonkers: SSN OR-alternative + unresolved
# city-license overlap + base affiliation), so the owner reviews
# each of those applications too. Dallas hides the note: its list
# is complete as named by Uber's official pages. The Southeast
# note-ON cities keep it for the same reason: a named item the
# gate cannot express (Birmingham: held medical certificate;
# Huntsville/Montgomery: unretrieved supporting documents;
# Miami/Charlotte/Durham/Charleston/Nashville: OR-alternatives
# and held SSN/medical items; Tallahassee: unverified currency).
# The Midwest note-ON cities keep it for held medical/SSN items
# (Kansas City, Saint Louis, Toledo, Springfield IL,
# Indianapolis), gaps the gate cannot express (Minneapolis,
# Columbia, Jefferson City), unretrieved checklists (Kenosha),
# or flagged livery scope (Rochester MN, Independence, Lincoln).
# The Northeast note-ON cities keep it for the same reason: a
# structural gap (Portland ME: vehicle business-license coverage),
# an unverified exception (South Portland: reciprocity), or held
# SSN/medical inputs (Springfield MA, Philadelphia).
# The South Central/Mountain note-ON cities keep it for held
# medical/SSN items (Oklahoma City, Tulsa, Gillette), an
# OR-alternative (Idaho Falls), conditional or unverified items
# (Austin, San Antonio), a code-text gap (St. George), or the
# Clark County livery-scope question (Henderson, Las Vegas,
# North Las Vegas). Portland, OR keeps it for the unretrieved
# FASTTRACK portal checklist.
CITY_LISTS_WITH_LOCAL_NOTE = frozenset({
    ("New York", "Buffalo"),
    ("New York", "Rochester"),
    ("New York", "Syracuse"),
    ("New York", "Yonkers"),
    ("Alabama", "Birmingham"),
    ("Alabama", "Huntsville"),
    ("Alabama", "Montgomery"),
    ("Florida", "Miami"),
    ("Florida", "Tallahassee"),
    ("North Carolina", "Charlotte"),
    ("North Carolina", "Durham"),
    ("South Carolina", "Charleston"),
    ("Tennessee", "Nashville"),
    ("Illinois", "Springfield"),
    ("Indiana", "Indianapolis"),
    ("Minnesota", "Minneapolis"),
    ("Minnesota", "Rochester"),
    ("Missouri", "Columbia"),
    ("Missouri", "Independence"),
    ("Missouri", "Jefferson City"),
    ("Missouri", "Kansas City"),
    ("Missouri", "Saint Louis"),
    ("Nebraska", "Lincoln"),
    ("Ohio", "Columbus"),
    ("Wisconsin", "Kenosha"),
    ("Maine", "Portland"),
    ("Maine", "South Portland"),
    ("Massachusetts", "Springfield"),
    ("Pennsylvania", "Philadelphia"),
    ("Idaho", "Idaho Falls"),
    ("Oklahoma", "Oklahoma City"),
    ("Oklahoma", "Tulsa"),
    ("Texas", "Austin"),
    ("Texas", "San Antonio"),
    ("Utah", "St. George"),
    ("Wyoming", "Gillette"),
    ("Nevada", "Henderson"),
    ("Nevada", "Las Vegas"),
    ("Nevada", "North Las Vegas"),
    ("Oregon", "Portland"),
})


def cities_for_state(state):
    """City names for the picker: the state's largest cities,
    alphabetical, with the "Other city" fallback last."""
    return list(CITIES_BY_STATE.get(state, [])) + [OTHER_CITY]


def required_docs_for(state, city=None):
    """Ordered compulsory doc types for a state + city. A city with a
    verified city-specific list overrides its state list; every other
    city — including "Other city" and no city on file — uses the
    state list unchanged."""
    if city:
        city_docs = CITY_DOC_REQUIREMENTS.get((state, city))
        if city_docs is not None:
            return city_docs
    return required_docs_for_state(state)


def local_note_for(state, city=None):
    """Whether the owner-review note shows for the effective list: it
    hides only for a verified list (a verified state, or a city with
    a verified city-specific list) — except a city list with a known
    gap the gate cannot express (Buffalo: the worker's compensation
    OR-alternative), which keeps the note on."""
    if city and (state, city) in CITY_DOC_REQUIREMENTS:
        return (state, city) in CITY_LISTS_WITH_LOCAL_NOTE
    return state not in VERIFIED_DOC_STATES


# Labels for every doc type in every state's list, in the same
# owner-words style as DOC_LABELS. DOC_LABELS above stays the
# New York list (existing tests pin it); this is the superset the
# gate and the states endpoint use.
ALL_DOC_LABELS = dict(DOC_LABELS)
ALL_DOC_LABELS.update({
    "nj_qualification": "MVC Letter of Qualification",
    "nj_municipal_license": "Municipal License to Operate",
    "nj_limo_registration": "Limousine Vehicle Registration",
    "nj_insurance": "Insurance Certificate",
    "vehicle_registration": "Vehicle Registration",
    "insurance_card": "Insurance Card",
    "al_certificate": "Certificate of Intrastate Authority (APSC)",
    "al_form_e": "Form E (Insurance Filing)",
    "ca_tcp_permit": "Charter-Party Carrier (TCP) Certificate/Permit (Class A, B or P)",
    "ca_driver_statement": "Driver Statement of Application (Form PL739-A)",
    "ca_commercial_registration": "Commercial Vehicle Registration (Form PL664)",
    "ca_inspection_declaration": "Vehicle Inspection Declaration (Form PL668)",
    "co_ll_permit": "Luxury Limousine (LL) Permit",
    "co_inspection": "Vehicle Inspection",
    "co_form_e": "Form E (Insurance Filing)",
    "ct_livery_permit": "Livery Permit (CT DOT)",
    "de_certificate": "Certificate of Public Convenience and Necessity",
    "de_limo_registration": "Limousine Registration",
    "de_inspection": "Vehicle Inspection",
    "dc_drivers_record": "Driver's Record",
    "dc_ssc": "Social Security Card",
    "dc_residency": "Proof of Residency",
    "dc_medical_form": "Medical History / Physical Examination Form",
    "dc_face_id": "For-Hire Operators (Face ID) License",
    "dc_public_vehicle_license": "Public Vehicle-for-Hire License",
    "dc_inspection": "DMV Inspection",
    "ga_carrier_certificate": "Limousine Carrier Certificate (Georgia DPS)",
    "ga_insurance_certificate": "Certificate of Insurance",
    "hi_carrier_certificate": "Motor Carrier Certificate / Permit (Form 92-001)",
    "hi_vehicle_inventory": "Vehicle Inventory List (Exhibit B)",
    "hi_tax_clearance": "Tax Clearance Certificate",
    "ks_certificate": "Certificate of Convenience and Necessity (KCC)",
    "ky_limousine_certificate": "Limousine Certificate",
    "ky_vehicle_license": "Motor Carrier Vehicle License",
    "ky_inspection": "Vehicle Inspection",
    "me_registration": "Vehicle Registration with HIRE Plates (Class TX)",
    "me_jb_filing": "Insurance Certificate for For-Hire Passenger Vehicle (JB Filing)",
    "md_for_hire_license": "Passenger-for-Hire Driver's License (PSC)",
    "md_inspection_certificate": "Vehicle Inspection Certificate",
    "mi_carrier_license": "Limousine Carrier License",
    "mn_permit": "Limousine Service Permit (MnDOT)",
    "mn_inspection": "Vehicle Inspection",
    "mn_form_e": "Form E (Insurance Filing)",
    "mo_authority": "Motor Carrier Operating Authority (MoDOT)",
    "ne_medical_certificate": "Medical Certificate",
    "ne_carrier_authority": "Common / Contract Carrier Authority (PSC)",
    "nv_drivers_permit": "Driver's Permit (NTA)",
    "nv_cpcn": "Certificate of Public Convenience and Necessity (CPCN)",
    "nm_inspection": "Vehicle Inspection",
    "oh_livery_registration": "Vehicle Registration (Livery Plates)",
    "pa_driving_history": "Driving History (3-Year Record)",
    "pa_criminal_history": "Criminal History Record",
    "pa_certificate": "Certificate of Public Convenience (PUC)",
    "pa_inspection": "Vehicle Inspection",
    "pa_form_e": "Form E (Insurance Filing)",
    "ri_operator_license": "Taxi-LPMV-PMV Operator's License",
    "ri_driving_record": "Driving Record",
    "ri_criminal_record": "Record of Criminal Convictions",
    "sc_driving_record": "Certified Driving Record (3 Years)",
    "sc_charter_certificate": "Class C Charter Certificate",
    "sc_ls_registration": "Vehicle Registration (LS Plates)",
    "sc_form_e": "Form E (Insurance Filing)",
    "tn_citizenship_proof": "Proof of Citizenship or Lawful Permanent Residency",
    "tn_residency_proof": "Proof of Tennessee Residency",
    "va_authority": "For-Hire Intrastate Operating Authority",
    "va_title": "Vehicle Title (Virginia)",
    "va_for_hire_registration": "For-Hire Vehicle Registration",
    "va_authority_registration": "Operating Authority Registration",
    "wa_medical_certificate": "Medical Examiner's Certificate",
    "wa_driving_record": "Driving Record",
    "wa_carrier_license": "Limousine Carrier License",
    "wa_vehicle_certificate": "Limousine Vehicle Certificate",
    "wa_chauffeur_addendum": "Limousine Carrier Chauffeur Addendum",
    "wa_fh_registration": "Vehicle Registration Certificate (Use Class F/H)",
    "wa_inspection_report": "Vehicle Inspection Report",
    "wa_insurance_certificate": "Certificate of Insurance",
    "dallas_commercial_insurance": "Commercial Insurance Certificate",
    "dallas_driver_permit": "Dallas Driver Permit",
    "dallas_limo_permit": "City Limo Permit (Dallas / Fort Worth)",
    "buffalo_taxi_driver_license": "City of Buffalo Taxi Driver License",
    "buffalo_insurance_certificate": "Certificate of Automobile Liability Insurance",
    "buffalo_inspection_report": "Vehicle Inspection Report",
    "rochester_taxi_driver_license": "City of Rochester Taxicab Driver License",
    "rochester_hack_certificate": "Taxicab License Certificate (Hack Plate Certificate)",
    "rochester_insurance": "Proof of Insurance",
    "syracuse_hack_license": "Taxi (Hack) License",
    "syracuse_ground_transportation": "Ground Transportation License",
    "syracuse_for_hire_insurance": "Proof of For-Hire Insurance",
    "wctlc_driver_permit": "WCTLC For-Hire Driver Permit",
    "wctlc_vehicle_permit": "WCTLC For-Hire Vehicle Permit",
    "wctlc_insurance": "Proof of Adequate Insurance",
    "wctlc_defensive_driving": "Defensive Driving Course Proof of Completion",
    "birmingham_operator_permit": "City of Birmingham Operator's Permit",
    "huntsville_chauffeur_license": "City of Huntsville Chauffeur License",
    "mobile_chauffeur_license": "City of Mobile Chauffeur License",
    "montgomery_chauffeur_license": "City of Montgomery Chauffeur License",
    "miami_chauffeur_registration": "Miami-Dade Chauffeur Registration",
    "orlando_driver_permit": "City of Orlando Driver Permit",
    "orlando_insurance": "Certificate of Insurance (City as Additional Insured)",
    "tallahassee_driver_permit": "City of Tallahassee Driver Permit",
    "tampa_pvdl": "Public Vehicle Driver License (Hillsborough County)",
    "tampa_transcript": "Seven-Year Driver License Transcript",
    "baton_rouge_chauffeur_license": "City of Baton Rouge Chauffeur License",
    "baton_rouge_driving_record": "Official Driving Record",
    "baton_rouge_clearance": "Clearance Certificate",
    "new_orleans_driver_permit": "CPNC Driver Permit (New Orleans)",
    "new_orleans_mvr": "Certified MVR (Within 30 Days)",
    "mvfha_driver_permit": "MVFHA Driver Permit",
    "charlotte_pvh_permit": "PVH Driver Permit (Charlotte)",
    "charlotte_driving_record": "Driving Record",
    "durham_pvfh_permit": "PVFH Driver Permit (Durham)",
    "charleston_chauffeur_license": "Chauffeur License (Charleston)",
    "charleston_driving_record": "Certified 10-Year Driving Record",
    "nashville_opvh_permit": "MTLC OPVH Driver Permit",
    "nashville_mvr": "Motor Vehicle Record (Within 30 Days)",
    "chicago_chauffeur_license": "Restricted Livery Public Chauffeur License (Chicago)",
    "chicago_livery_vehicle_license": "Livery Vehicle License (Chicago)",
    "chicago_insurance_certificate": "Commercial Insurance Certificate (Chicago)",
    "rockford_taxi_driver_license": "Taxi Cab Driver License (Rockford)",
    "springfield_il_taxi_driver_license": "Taxicab Driver License (Springfield, IL)",
    "evansville_taxi_driver_license": "City of Evansville Taxicab Driver License",
    "indianapolis_operator_license": "Operator License (Indianapolis)",
    "indianapolis_training_certificate": "Taxi Training Course Certificate (Indianapolis)",
    "indianapolis_bmv_record": "Certified BMV Driving Record (Within 10 Days)",
    "minneapolis_taxi_driver_license": "Taxi Driver License (Minneapolis)",
    "minneapolis_training_certificate": "Taxi Driver Training Certificate (Minneapolis)",
    "rochester_mn_taxi_driver_license": "Taxicab Driver License (Rochester, MN)",
    "saint_paul_taxi_driver_license": "Taxicab Driver License (Saint Paul)",
    "saint_paul_training_proof": "Taxicab Driver Training Course Completion Proof",
    "columbia_chauffeur_license": "Chauffeur License (Columbia)",
    "independence_vehicle_driver_permit": "Vehicle Driver Permit (Independence)",
    "jefferson_city_taxi_driver_permit": "Taxi Driver Permit (Jefferson City)",
    "jefferson_city_driving_record": "Certified Driving Record (Missouri DOR)",
    "kansas_city_driver_certificate": "Vehicle-for-Hire Driver Certificate (Kansas City)",
    "kansas_city_operating_record": "State Operating Record (Missouri)",
    "saint_louis_mtc_license": "MTC Driver License (Saint Louis)",
    "saint_louis_driver_history": "Missouri Driver History Report (Within 10 Days)",
    "lincoln_taxi_driver_license": "Taxicab Driver License (Lincoln)",
    "kenosha_taxi_driver_license": "Taxi Driver License (Kenosha)",
    "madison_ppv_permit": "Public Passenger Vehicle Driver Permit (Madison)",
    "milwaukee_ppv_license": "Public Passenger Vehicle Driver License (Milwaukee)",
    "columbus_vfh_license": "Vehicle for Hire Driver License (Columbus)",
    "columbus_bmv_abstract": "Certified Ohio BMV Driver Abstract (Within 30 Days)",
    "portland_me_livery_license": "Portland Livery Driver License",
    "south_portland_taxi_driver_license": "South Portland Taxicab Driver License",
    "lowell_hackney_license": "Hackney License (Lowell)",
    "springfield_ma_chauffeur_license": "Chauffeur License (Springfield, MA)",
    "worcester_taxi_livery_license": "Taxi-Livery Driver License (Worcester)",
    "jersey_city_limo_driver_license": "Jersey City Limousine Driver License",
    "philadelphia_limo_certificate": "PPA Limousine Driver Certificate",
    "little_rock_gt_driver_permit": "Ground Transportation Service Driver Permit (Little Rock)",
    "springdale_taxi_driver_permit": "Taxicab Driver Permit (Springdale)",
    "boise_cts_driver_license": "Commercial Transportation Service Driver License (Boise)",
    "idaho_falls_operator_license": "Public Transportation Operator License (Idaho Falls)",
    "okc_vfh_driver_permit": "Vehicle-for-Hire Driver Permit (Oklahoma City)",
    "tulsa_chauffeur_license": "City of Tulsa Chauffeur License",
    "tulsa_mvr": "MVR Report (Within 30 Days)",
    "austin_chauffeur_permit": "Chauffeur Permit (Austin)",
    "houston_vfh_driver_license": "City-Issued Vehicle-for-Hire Driver License (Houston)",
    "san_antonio_driver_permit": "City of San Antonio Driver Permit (Vehicles for Hire)",
    "st_george_for_hire_permit": "For-Hire Driver Permit (St. George)",
    "cheyenne_pt_driver_permit": "Public Transportation Driver Permit (Cheyenne)",
    "gillette_pt_driver_permit": "Public Transportation Driver Permit (Gillette)",
    "clark_county_business_license": "Clark County Business License",
    "portland_or_certification": "Executive Town Car Driver Certification (Portland)",
    "portland_or_business_license": "City of Portland Business License",
})
# Hint line under each document item in the registration form.
DOC_HINTS = {
    "profile_picture": "Passport-style photo: face forward, head and shoulders, face clearly visible. Take it upright (portrait), in good light — small or sideways photos are not accepted.",
    "dmv_license": "Photo of your DMV driving license, straight and fully visible.",
    "tlc_license": "Photo of your TLC license, straight and fully visible.",
    "fh1_insurance": "Photo of your FH-1 card, including the barcode — or upload a PDF.",
    "registration": "Photo of your registration, straight and fully visible.",
    "inspection": "Photo of your inspection document, straight and fully visible.",
    "vehicle_permit": "Photo of your vehicle permit, straight and fully visible.",
    "nj_qualification": "Photo of your MVC Letter of Qualification, straight and fully visible.",
    "nj_municipal_license": "Photo of your municipal license to operate, straight and fully visible.",
    "nj_limo_registration": "Photo of your limousine vehicle registration, straight and fully visible.",
    "nj_insurance": "Photo of your insurance certificate, straight and fully visible.",
    "vehicle_registration": "Photo of your vehicle registration, straight and fully visible.",
    "insurance_card": "Photo of your insurance card, straight and fully visible.",
    "al_certificate": "Photo of your Certificate of Intrastate Authority (APSC), straight and fully visible.",
    "al_form_e": "Photo of your Form E (Insurance Filing), straight and fully visible.",
    "ca_tcp_permit": "Photo of your TCP certificate or permit (Class A, B or P) in your own name or your company name, straight and fully visible.",
    "ca_driver_statement": "Photo of your Driver Statement of Application (Form PL739-A), straight and fully visible.",
    "ca_commercial_registration": "Photo of your Commercial Vehicle Registration (Form PL664), straight and fully visible.",
    "ca_inspection_declaration": "Photo of your Vehicle Inspection Declaration (Form PL668), straight and fully visible.",
    "co_ll_permit": "Photo of your Luxury Limousine (LL) Permit, straight and fully visible.",
    "co_inspection": "Photo of your Vehicle Inspection, straight and fully visible.",
    "co_form_e": "Photo of your Form E (Insurance Filing), straight and fully visible.",
    "ct_livery_permit": "Photo of your Livery Permit (CT DOT), straight and fully visible.",
    "de_certificate": "Photo of your Certificate of Public Convenience and Necessity, straight and fully visible.",
    "de_limo_registration": "Photo of your Limousine Registration, straight and fully visible.",
    "de_inspection": "Photo of your Vehicle Inspection, straight and fully visible.",
    "dc_drivers_record": "Photo of your Driver's Record, straight and fully visible.",
    "dc_ssc": "Photo of your Social Security Card, straight and fully visible.",
    "dc_residency": "Photo of your Proof of Residency, straight and fully visible.",
    "dc_medical_form": "Photo of your Medical History / Physical Examination Form, straight and fully visible.",
    "dc_face_id": "Photo of your For-Hire Operators (Face ID) License, straight and fully visible.",
    "dc_public_vehicle_license": "Photo of your Public Vehicle-for-Hire License, straight and fully visible.",
    "dc_inspection": "Photo of your DMV Inspection, straight and fully visible.",
    "ga_carrier_certificate": "Photo of your Limousine Carrier Certificate (Georgia DPS), straight and fully visible.",
    "ga_insurance_certificate": "Photo of your Certificate of Insurance, straight and fully visible.",
    "hi_carrier_certificate": "Photo of your Motor Carrier Certificate / Permit (Form 92-001), straight and fully visible.",
    "hi_vehicle_inventory": "Photo of your Vehicle Inventory List (Exhibit B), straight and fully visible.",
    "hi_tax_clearance": "Photo of your Tax Clearance Certificate, straight and fully visible.",
    "ks_certificate": "Photo of your Certificate of Convenience and Necessity (KCC), straight and fully visible.",
    "ky_limousine_certificate": "Photo of your Limousine Certificate, straight and fully visible.",
    "ky_vehicle_license": "Photo of your Motor Carrier Vehicle License, straight and fully visible.",
    "ky_inspection": "Photo of your Vehicle Inspection, straight and fully visible.",
    "me_registration": "Photo of your Vehicle Registration with HIRE Plates (Class TX), straight and fully visible.",
    "me_jb_filing": "Photo of your Insurance Certificate for For-Hire Passenger Vehicle (JB Filing), straight and fully visible.",
    "md_for_hire_license": "Photo of your Passenger-for-Hire Driver's License (PSC), straight and fully visible.",
    "md_inspection_certificate": "Photo of your Vehicle Inspection Certificate, straight and fully visible.",
    "mi_carrier_license": "Photo of your Limousine Carrier License, straight and fully visible.",
    "mn_permit": "Photo of your Limousine Service Permit (MnDOT), straight and fully visible.",
    "mn_inspection": "Photo of your Vehicle Inspection, straight and fully visible.",
    "mn_form_e": "Photo of your Form E (Insurance Filing), straight and fully visible.",
    "mo_authority": "Photo of your Motor Carrier Operating Authority (MoDOT), straight and fully visible.",
    "ne_medical_certificate": "Photo of your Medical Certificate, straight and fully visible.",
    "ne_carrier_authority": "Photo of your Common / Contract Carrier Authority (PSC), straight and fully visible.",
    "nv_drivers_permit": "Photo of your Driver's Permit (NTA), straight and fully visible.",
    "nv_cpcn": "Photo of your Certificate of Public Convenience and Necessity (CPCN), straight and fully visible.",
    "nm_inspection": "Photo of your Vehicle Inspection, straight and fully visible.",
    "oh_livery_registration": "Photo of your Vehicle Registration (Livery Plates), straight and fully visible.",
    "pa_driving_history": "Photo of your Driving History (3-Year Record), straight and fully visible.",
    "pa_criminal_history": "Photo of your Criminal History Record, straight and fully visible.",
    "pa_certificate": "Photo of your Certificate of Public Convenience (PUC), straight and fully visible.",
    "pa_inspection": "Photo of your Vehicle Inspection, straight and fully visible.",
    "pa_form_e": "Photo of your Form E (Insurance Filing), straight and fully visible.",
    "ri_operator_license": "Photo of your Taxi-LPMV-PMV Operator's License, straight and fully visible.",
    "ri_driving_record": "Photo of your Driving Record, straight and fully visible.",
    "ri_criminal_record": "Photo of your Record of Criminal Convictions, straight and fully visible.",
    "sc_driving_record": "Photo of your Certified Driving Record (3 Years), straight and fully visible.",
    "sc_charter_certificate": "Photo of your Class C Charter Certificate, straight and fully visible.",
    "sc_ls_registration": "Photo of your Vehicle Registration (LS Plates), straight and fully visible.",
    "sc_form_e": "Photo of your Form E (Insurance Filing), straight and fully visible.",
    "tn_citizenship_proof": "Photo of your Proof of Citizenship or Lawful Permanent Residency, straight and fully visible.",
    "tn_residency_proof": "Photo of your Proof of Tennessee Residency, straight and fully visible.",
    "va_authority": "Photo of your For-Hire Intrastate Operating Authority, straight and fully visible.",
    "va_title": "Photo of your Vehicle Title (Virginia), straight and fully visible.",
    "va_for_hire_registration": "Photo of your For-Hire Vehicle Registration, straight and fully visible.",
    "va_authority_registration": "Photo of your Operating Authority Registration, straight and fully visible.",
    "wa_medical_certificate": "Photo of your Medical Examiner's Certificate, straight and fully visible.",
    "wa_driving_record": "Photo of your Driving Record, straight and fully visible.",
    "wa_carrier_license": "Photo of your Limousine Carrier License, straight and fully visible.",
    "wa_vehicle_certificate": "Photo of your Limousine Vehicle Certificate, straight and fully visible.",
    "wa_chauffeur_addendum": "Photo of your Limousine Carrier Chauffeur Addendum, straight and fully visible.",
    "wa_fh_registration": "Photo of your Vehicle Registration Certificate (Use Class F/H), straight and fully visible.",
    "wa_inspection_report": "Photo of your Vehicle Inspection Report, straight and fully visible.",
    "wa_insurance_certificate": "Photo of your Certificate of Insurance, straight and fully visible.",
    "dallas_commercial_insurance": "Photo of your Commercial Insurance Certificate, straight and fully visible.",
    "dallas_driver_permit": "Photo of your Dallas Driver Permit, straight and fully visible.",
    "dallas_limo_permit": "Photo of your City Limo Permit (Dallas / Fort Worth), straight and fully visible.",
    "buffalo_taxi_driver_license": "Photo of your City of Buffalo Taxi Driver License, straight and fully visible.",
    "buffalo_insurance_certificate": "Photo of your Certificate of Automobile Liability Insurance, straight and fully visible.",
    "buffalo_inspection_report": "Photo of your Vehicle Inspection Report, straight and fully visible.",
    "rochester_taxi_driver_license": "Photo of your City of Rochester Taxicab Driver License, straight and fully visible.",
    "rochester_hack_certificate": "Photo of your Taxicab License Certificate (Hack Plate Certificate), straight and fully visible.",
    "rochester_insurance": "Photo of your Proof of Insurance, straight and fully visible.",
    "syracuse_hack_license": "Photo of your Taxi (Hack) License, straight and fully visible.",
    "syracuse_ground_transportation": "Photo of your Ground Transportation License, straight and fully visible.",
    "syracuse_for_hire_insurance": "Photo of your Proof of For-Hire Insurance, straight and fully visible.",
    "wctlc_driver_permit": "Photo of your WCTLC For-Hire Driver Permit, straight and fully visible.",
    "wctlc_vehicle_permit": "Photo of your WCTLC For-Hire Vehicle Permit, straight and fully visible.",
    "wctlc_insurance": "Photo of your Proof of Adequate Insurance, straight and fully visible.",
    "wctlc_defensive_driving": "Photo of your Defensive Driving Course Proof of Completion, straight and fully visible.",
    "birmingham_operator_permit": "Photo of your City of Birmingham Operator's Permit, straight and fully visible.",
    "huntsville_chauffeur_license": "Photo of your City of Huntsville Chauffeur License, straight and fully visible.",
    "mobile_chauffeur_license": "Photo of your City of Mobile Chauffeur License, straight and fully visible.",
    "montgomery_chauffeur_license": "Photo of your City of Montgomery Chauffeur License, straight and fully visible.",
    "miami_chauffeur_registration": "Photo of your Miami-Dade Chauffeur Registration, straight and fully visible.",
    "orlando_driver_permit": "Photo of your City of Orlando Driver Permit, straight and fully visible.",
    "orlando_insurance": "Photo of your Certificate of Insurance (City as Additional Insured), straight and fully visible.",
    "tallahassee_driver_permit": "Photo of your City of Tallahassee Driver Permit, straight and fully visible.",
    "tampa_pvdl": "Photo of your Public Vehicle Driver License (Hillsborough County), straight and fully visible.",
    "tampa_transcript": "Photo of your Seven-Year Driver License Transcript, straight and fully visible.",
    "baton_rouge_chauffeur_license": "Photo of your City of Baton Rouge Chauffeur License, straight and fully visible.",
    "baton_rouge_driving_record": "Photo of your Official Driving Record, straight and fully visible.",
    "baton_rouge_clearance": "Photo of your Clearance Certificate, straight and fully visible.",
    "new_orleans_driver_permit": "Photo of your CPNC Driver Permit (New Orleans), straight and fully visible.",
    "new_orleans_mvr": "Photo of your Certified MVR (Within 30 Days), straight and fully visible.",
    "mvfha_driver_permit": "Photo of your MVFHA Driver Permit, straight and fully visible.",
    "charlotte_pvh_permit": "Photo of your PVH Driver Permit (Charlotte), straight and fully visible.",
    "charlotte_driving_record": "Photo of your Driving Record, straight and fully visible.",
    "durham_pvfh_permit": "Photo of your PVFH Driver Permit (Durham), straight and fully visible.",
    "charleston_chauffeur_license": "Photo of your Chauffeur License (Charleston), straight and fully visible.",
    "charleston_driving_record": "Photo of your Certified 10-Year Driving Record, straight and fully visible.",
    "nashville_opvh_permit": "Photo of your MTLC OPVH Driver Permit, straight and fully visible.",
    "nashville_mvr": "Photo of your Motor Vehicle Record (Within 30 Days), straight and fully visible.",
    "chicago_chauffeur_license": "Photo of your Restricted Livery Public Chauffeur License (Chicago), straight and fully visible.",
    "chicago_livery_vehicle_license": "Photo of your Livery Vehicle License (Chicago), straight and fully visible.",
    "chicago_insurance_certificate": "Photo of your Commercial Insurance Certificate (Chicago), straight and fully visible.",
    "rockford_taxi_driver_license": "Photo of your Taxi Cab Driver License (Rockford), straight and fully visible.",
    "springfield_il_taxi_driver_license": "Photo of your Taxicab Driver License (Springfield, IL), straight and fully visible.",
    "evansville_taxi_driver_license": "Photo of your City of Evansville Taxicab Driver License, straight and fully visible.",
    "indianapolis_operator_license": "Photo of your Operator License (Indianapolis), straight and fully visible.",
    "indianapolis_training_certificate": "Photo of your Taxi Training Course Certificate (Indianapolis), straight and fully visible.",
    "indianapolis_bmv_record": "Photo of your Certified BMV Driving Record (Within 10 Days), straight and fully visible.",
    "minneapolis_taxi_driver_license": "Photo of your Taxi Driver License (Minneapolis), straight and fully visible.",
    "minneapolis_training_certificate": "Photo of your Taxi Driver Training Certificate (Minneapolis), straight and fully visible.",
    "rochester_mn_taxi_driver_license": "Photo of your Taxicab Driver License (Rochester, MN), straight and fully visible.",
    "saint_paul_taxi_driver_license": "Photo of your Taxicab Driver License (Saint Paul), straight and fully visible.",
    "saint_paul_training_proof": "Photo of your Taxicab Driver Training Course Completion Proof, straight and fully visible.",
    "columbia_chauffeur_license": "Photo of your Chauffeur License (Columbia), straight and fully visible.",
    "independence_vehicle_driver_permit": "Photo of your Vehicle Driver Permit (Independence), straight and fully visible.",
    "jefferson_city_taxi_driver_permit": "Photo of your Taxi Driver Permit (Jefferson City), straight and fully visible.",
    "jefferson_city_driving_record": "Photo of your Certified Driving Record (Missouri DOR), straight and fully visible.",
    "kansas_city_driver_certificate": "Photo of your Vehicle-for-Hire Driver Certificate (Kansas City), straight and fully visible.",
    "kansas_city_operating_record": "Photo of your State Operating Record (Missouri), straight and fully visible.",
    "saint_louis_mtc_license": "Photo of your MTC Driver License (Saint Louis), straight and fully visible.",
    "saint_louis_driver_history": "Photo of your Missouri Driver History Report (Within 10 Days), straight and fully visible.",
    "lincoln_taxi_driver_license": "Photo of your Taxicab Driver License (Lincoln), straight and fully visible.",
    "kenosha_taxi_driver_license": "Photo of your Taxi Driver License (Kenosha), straight and fully visible.",
    "madison_ppv_permit": "Photo of your Public Passenger Vehicle Driver Permit (Madison), straight and fully visible.",
    "milwaukee_ppv_license": "Photo of your Public Passenger Vehicle Driver License (Milwaukee), straight and fully visible.",
    "columbus_vfh_license": "Photo of your Vehicle for Hire Driver License (Columbus), straight and fully visible.",
    "columbus_bmv_abstract": "Photo of your Certified Ohio BMV Driver Abstract (Within 30 Days), straight and fully visible.",
    "portland_me_livery_license": "Photo of your Portland Livery Driver License, straight and fully visible.",
    "south_portland_taxi_driver_license": "Photo of your South Portland Taxicab Driver License, straight and fully visible.",
    "lowell_hackney_license": "Photo of your Hackney License (Lowell), straight and fully visible.",
    "springfield_ma_chauffeur_license": "Photo of your Chauffeur License (Springfield, MA), straight and fully visible.",
    "worcester_taxi_livery_license": "Photo of your Taxi-Livery Driver License (Worcester), straight and fully visible.",
    "jersey_city_limo_driver_license": "Photo of your Jersey City Limousine Driver License, straight and fully visible.",
    "philadelphia_limo_certificate": "Photo of your PPA Limousine Driver Certificate, straight and fully visible.",
    "little_rock_gt_driver_permit": "Photo of your Ground Transportation Service Driver Permit (Little Rock), straight and fully visible.",
    "springdale_taxi_driver_permit": "Photo of your Taxicab Driver Permit (Springdale), straight and fully visible.",
    "boise_cts_driver_license": "Photo of your Commercial Transportation Service Driver License (Boise), straight and fully visible.",
    "idaho_falls_operator_license": "Photo of your Public Transportation Operator License (Idaho Falls), straight and fully visible.",
    "okc_vfh_driver_permit": "Photo of your Vehicle-for-Hire Driver Permit (Oklahoma City), straight and fully visible.",
    "tulsa_chauffeur_license": "Photo of your City of Tulsa Chauffeur License, straight and fully visible.",
    "tulsa_mvr": "Photo of your MVR Report (Within 30 Days), straight and fully visible.",
    "austin_chauffeur_permit": "Photo of your Chauffeur Permit (Austin), straight and fully visible.",
    "houston_vfh_driver_license": "Photo of your City-Issued Vehicle-for-Hire Driver License (Houston), straight and fully visible.",
    "san_antonio_driver_permit": "Photo of your City of San Antonio Driver Permit (Vehicles for Hire), straight and fully visible.",
    "st_george_for_hire_permit": "Photo of your For-Hire Driver Permit (St. George), straight and fully visible.",
    "cheyenne_pt_driver_permit": "Photo of your Public Transportation Driver Permit (Cheyenne), straight and fully visible.",
    "gillette_pt_driver_permit": "Photo of your Public Transportation Driver Permit (Gillette), straight and fully visible.",
    "clark_county_business_license": "Photo of your Clark County Business License, straight and fully visible.",
    "portland_or_certification": "Photo of your Executive Town Car Driver Certification (Portland), straight and fully visible.",
    "portland_or_business_license": "Photo of your City of Portland Business License (Certificate of Compliance), straight and fully visible.",
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
    # Password hash for email+password sign-in (owner decision
    # 2026-11-18, "complete sign in process banao"). Nullable:
    # drivers registered before passwords existed have no hash and
    # keep signing in via the phone lookup exactly as before. Only
    # the hash is ever stored — never the plaintext password — and
    # it is never returned by any API response.
    password_hash = db.Column(db.String(255), nullable=True)
    # US state the driver drives in, picked from the searchable state
    # dropdown at registration (owner decision 2026-11-17). Nullable:
    # drivers registered before the state selector existed have no
    # state on file and keep working exactly as before.
    state = db.Column(db.String(40), nullable=True)
    # City the driver drives in, picked from the searchable city
    # dropdown right after the state (owner decision 2026-11-17,
    # "City picker bana do, Uber jaisa"). Nullable: drivers
    # registered before the city picker existed have no city on file
    # and keep working exactly as before, on their state list.
    city = db.Column(db.String(80), nullable=True)
    # Declared chat language, picked by the driver in the chat picker
    # (owner decision 2026-11-18: each side reads replies in their own
    # language). A code from translation.CHAT_LANGUAGES; NULL means
    # English, so drivers registered before the picker existed keep
    # working exactly as before.
    chat_language = db.Column(db.String(10), nullable=True)
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
    # Suspension end (owner decision 2026-11-18, voice call): when a
    # driver cancels inside the 2-hour window and the automatic
    # judgment finds the reason is his fault, the driver app is
    # blocked for 48 hours. NULL means no suspension; a timestamp in
    # the past means the suspension has auto-lifted (enforcement is
    # purely time-based — no cron, no manual step). Sign-in still
    # works while suspended so the driver sees the notice; he cannot
    # go available and gets no offers until it lifts. Nullable: the
    # column is added to the live database by the startup ALTER
    # below, and drivers registered before it existed read as
    # unsuspended.
    suspended_until = db.Column(db.DateTime(timezone=True), nullable=True)
    # Stable, unique driver referral code (owner decision 2026-11-18,
    # voice call: the driver referral is a shareable LINK, not a code
    # number — the friend clicks the link and lands straight in driver
    # registration). Minted at registration; drivers registered
    # before this existed get one on first referral-section load (see
    # ensure_driver_referral_code). Nullable: the column is added to
    # the live database by the startup ALTER below. Unique in the
    # model; the generation loop guarantees uniqueness on assignment.
    # Separate namespace from the customer ReferralCode table ("DRV-"
    # prefix vs "NOEL-"), so a customer code can never resolve to a
    # driver and vice versa.
    referral_code = db.Column(db.String(40), unique=True, nullable=True)
    # The driver who referred this driver, captured when registration
    # arrived via a referral link (NULL = registered without one).
    # Plain integer, deliberately NO foreign key — mirroring
    # EmergencyCancel.driver_id — so the link never blocks the
    # test-only driver clear and the record survives it. Nullable:
    # added by the startup ALTER below; reads use getattr with a
    # None default so a row read before the column existed degrades
    # to "no referrer" instead of raising.
    referred_by_driver_id = db.Column(db.Integer, nullable=True)
    bank_encrypted = db.Column(db.LargeBinary, nullable=True)
    bank_last4 = db.Column(db.String(4), nullable=True)
    # Stripe Connect Express account for driver payouts (owner
    # decision 2026-11-20, Uber-like instant payouts). NULL until
    # the driver finishes Stripe's hosted onboarding; the debit card
    # lives with Stripe, never here. Nullable: added by the startup
    # ALTER below, and drivers registered before it existed read as
    # not onboarded.
    stripe_connect_account_id = db.Column(db.String(60), nullable=True)
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
    # SHA-256 hex of the raw file bytes (driver document verification,
    # owner decision 2026-11-19): duplicate detection across drivers
    # and across slots. NULL on rows created before this existed —
    # those rows are never treated as duplicates.
    file_hash = db.Column(db.String(64), nullable=True)
    # Expiry date printed on the document, typed by the driver at
    # registration (owner decision 2026-11-19). NULL for document
    # types without an expiry, and for rows created before this
    # existed — those drivers are never blocked retroactively.
    expires_on = db.Column(db.Date, nullable=True)
    # When the 10-day expiry alert last fired for THIS expiry date
    # (owner decision 2026-11-19). NULL means no alert sent yet for
    # the stored expiry — the idempotency flag for run_expiry_alerts.
    # Resets only when the driver re-uploads the document with a
    # different expiry date, so a new expiry gets its own alert.
    expiry_alert_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (db.UniqueConstraint("driver_id", "doc_type"),)


class DocumentFlag(db.Model):
    """A registration attempt rejected by the document verification
    checks (owner decision 2026-11-19). Nothing is stored for the
    driver — registration never completes — but the attempt is
    recorded so the owner can see it read-only in the dashboard
    ("Flagged documents"). Rejected attempts only; successful
    registrations leave no flag."""
    __tablename__ = "document_flags"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    name = db.Column(db.String(120), nullable=False, default="")
    phone = db.Column(db.String(40), nullable=False, default="")
    email = db.Column(db.String(200), nullable=False, default="")
    doc_type = db.Column(db.String(40), nullable=False, default="")
    doc_label = db.Column(db.String(120), nullable=False, default="")
    # duplicate_other_driver | duplicate_same_driver | blank_photo |
    # tiny_photo | unreadable_photo | expired | missing_expiry |
    # invalid_expiry
    reason = db.Column(db.String(40), nullable=False)
    file_hash = db.Column(db.String(64), nullable=True)
    detail = db.Column(db.String(255), nullable=False, default="")


class RemovedDriver(db.Model):
    """Snapshot of a driver at the moment the owner removed him
    (owner decision 2026-11-23, voice call): \"if I remove drivers,
    removed drivers should be there in [the] removed driver list\" —
    plus a Restore button. Removal itself still hard-deletes the
    Driver row and every document (the snapshot is the only record
    left), so a removed driver can be brought back with the same
    name, phone, email and car. A new table, so create_all()
    creates it on the live database too. Drivers removed before
    this shipped have no snapshot and stay gone — nothing is
    invented for them."""
    __tablename__ = "removed_drivers"
    id = db.Column(db.Integer, primary_key=True)
    # The Driver.id the snapshot was taken from (plain integer, no
    # foreign key — the driver row is deleted, so an FK could never
    # point at it again).
    original_driver_id = db.Column(db.Integer, nullable=True)
    removed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    # "single" (one driver removed) or "bulk" (Remove all drivers).
    removed_via = db.Column(db.String(10), nullable=False, default="single")
    name = db.Column(db.String(120), nullable=False, default="")
    phone = db.Column(db.String(40), nullable=False, default="")
    email = db.Column(db.String(200), nullable=False, default="")
    state = db.Column(db.String(40), nullable=True)
    city = db.Column(db.String(80), nullable=True)
    car_model = db.Column(db.String(120), nullable=False, default="")
    car_year = db.Column(db.Integer, nullable=True)
    vehicle_class = db.Column(db.String(10), nullable=True)
    car_colour = db.Column(db.String(60), nullable=False, default="")
    plate = db.Column(db.String(40), nullable=False, default="")


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
    # True when this one-way booking was made through the "Book
    # your return trip" flow (owner decision 2026-11-20): the
    # return leg is a second one-way booking, but it displays as
    # "Return trip", not "One way". False for outward one-ways
    # and hourly rides. Added by the startup ALTER below; rows
    # created before it read as False via getattr.
    is_return = db.Column(db.Boolean, nullable=False, default=False)
    hours = db.Column(Numeric(5, 1), nullable=True)
    toll = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    referral_code_used = db.Column(db.String(40), nullable=True)
    # 5% first-ride referral discount actually granted on this booking
    # (owner decision 2026-11-18, voice call): the amount taken off
    # the total for a NEW customer's first one-way booking made with
    # a valid referral code. NULL on rows created before the discount
    # existed (no discount recorded); $0.00 when a code was used but
    # no discount applied (not a first booking). The referrer gets
    # nothing — there is no referrer reward.
    referral_discount = db.Column(Numeric(10, 2), nullable=True)
    # Optional flight number for airport rides, asked as a separate step
    # after the booking form; skippable, never blocks the booking. No
    # live flight tracking: the airline name is derived from the IATA
    # code in flights.py.
    flight_number = db.Column(db.String(20), nullable=True)
    # Receipt code: NC-<random 6 digits> (owner 2026-11-23, final
    # spec — random, never sequential; one booking one code, never
    # reused). Generated once, when the payment receipt is sent,
    # and stored here so the same booking always shows the same
    # code. Receipt-only — the website, apps and dashboard keep
    # showing the plain booking number.
    booking_code = db.Column(db.String(10), nullable=True)
    # Vehicle class: "sedan" (Business Class, the default the
    # customer sees pre-selected), "suv" (Business SUV) or "first"
    # (First Class). Hourly rides also carry a class now
    # (Blacklane-style hourly, owner decision 2026-11-20); hourly
    # rows created before that read as no class (None) and reach
    # every driver. Nullable: one-way bookings created before the
    # class system existed read as "sedan" (see booking_vehicle_class
    # below).
    vehicle_class = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="offered")
    fare_total = db.Column(Numeric(10, 2), nullable=False)
    driver_earnings = db.Column(Numeric(10, 2), nullable=False)
    gratuity = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    booking_fee = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    # Fare (miles x class rate) and the stored tax column. Tax and
    # gratuity were REMOVED from new bookings by owner orders
    # 2026-11-17, so new rows store $0.00 in both; rides booked
    # before the removal keep their stored values (history is not
    # rewritten). Nullable: bookings created before the class/tax
    # change read via the recompute fallback in
    # booking_fare/booking_tax below.
    fare = db.Column(Numeric(10, 2), nullable=True)
    tax = db.Column(Numeric(10, 2), nullable=True)
    waiting_minutes = db.Column(db.Integer, nullable=False, default=0)
    waiting_charge = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    # Extra miles driven beyond the booked route, entered by the driver
    # at completion (one-way rides only). extra_distance_charge is the
    # customer-side addition (added fare only — no gratuity, no tax);
    # the fare, fare_total and driver_earnings columns are all
    # increased by their share at completion, so the invoice and owner
    # breakdown stay consistent.
    extra_miles = db.Column(Numeric(6, 1), nullable=False, default=Decimal("0"))
    extra_distance_charge = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    # Dispatcher-lite: when the owner assigns a paid, not-yet-accepted
    # booking to one specific driver, only that driver sees it in
    # offers. NULL means the usual broadcast to all matching drivers.
    assigned_driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=True)
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
    # Declared chat language of the customer for this booking, picked
    # in the chat picker (owner decision 2026-11-18). A code from
    # translation.CHAT_LANGUAGES; NULL means English. Per-booking:
    # customers have no account, so the preference lives with the
    # ride it was picked for.
    customer_chat_language = db.Column(db.String(10), nullable=True)
    # When the 1-hour pickup reminder was queued for the accepted
    # driver (owner decision 2026-11-18: remind the assigned driver
    # 1 hour before pickup). NULL means no reminder has been queued
    # for the current acceptance; it is the idempotency flag — the
    # reminder fires once per acceptance. Reset when the booking
    # goes back to "offered" (driver cancel) or a new driver accepts,
    # so the next driver gets his own reminder.
    pickup_reminder_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)

    accepted_driver = db.relationship("Driver", foreign_keys=[accepted_driver_id])
    assigned_driver = db.relationship("Driver", foreign_keys=[assigned_driver_id])
    payments = db.relationship("Payment", backref="booking", cascade="all, delete-orphan")
    events = db.relationship("BookingEvent", backref="booking", cascade="all, delete-orphan")
    chat_messages = db.relationship("ChatMessage", backref="booking", cascade="all, delete-orphan")


class ChatMessage(db.Model):
    """In-app chat between driver and customer. Plain text only, no
    SMS, no number masking. Messages NEVER carry fare, miles,
    gratuity, tax or total figures — text only. A new table, so
    create_all() creates it on the live database too.

    Translation (owner decision 2026-11-18): `text` is always the
    message exactly as typed. At SEND time only, a translation into
    the RECIPIENT's declared language is stored in `translated_text`
    (+ `translated_language`); reads never translate. All three new
    columns are nullable, so messages stored before translation
    existed read exactly as before (original text, untranslated)."""
    __tablename__ = "chat_messages"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    sender = db.Column(db.String(10), nullable=False)  # driver | customer
    text = db.Column(db.Text, nullable=False)
    # Declared language the sender wrote in (translation.CHAT_LANGUAGES).
    sender_language = db.Column(db.String(10), nullable=True)
    # Send-time translation into the recipient's declared language, or
    # NULL when no translation was made (same language, no Azure key,
    # or any Azure failure — the original text is then shown).
    translated_text = db.Column(db.Text, nullable=True)
    translated_language = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


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
    # Live Stripe flow (owner decision 2026-11-20, "Uber jaisa bana
    # do"): authorized = hold placed at booking, captured = final
    # fare charged at ride end (or on a late cancel / no-show),
    # refunded = free cancel (hold released, or a captured charge
    # refunded), refund_pending = the Stripe cancel/refund failed and
    # the owner must retry it, capture_shortfall = the final fare was
    # higher than the hold and the top-up charge failed.
    # "succeeded" is the legacy test-mode status (rows from before
    # live Stripe): the money was never really charged.
    status = db.Column(db.String(20), nullable=False)  # authorized | captured | refunded | refund_pending | capture_shortfall | succeeded
    test = db.Column(db.Boolean, nullable=False, default=False)
    last4 = db.Column(db.String(4), nullable=True)
    brand = db.Column(db.String(20), nullable=True)
    # Live Stripe ids. stripe_test_id is the legacy test-mode id
    # ("pi_test_..."); live rows store "" there (the column stays NOT
    # NULL so no migration is needed) and the real id here.
    stripe_payment_intent_id = db.Column(db.String(80), nullable=True)
    stripe_customer_id = db.Column(db.String(60), nullable=True)
    # The PaymentMethod charged (saved card or the one-off card from
    # Stripe.js). Needed at ride end when the final fare is higher
    # than the hold: the difference is charged off-session to this
    # card. Brand/last4 only — the card itself lives with Stripe.
    stripe_payment_method_id = db.Column(db.String(60), nullable=True)
    # What was actually captured (NULL until captured). `amount` is
    # the authorized (held) amount; the captured amount can be lower
    # (final fare under the estimate) or equal.
    captured_amount = db.Column(Numeric(10, 2), nullable=True)
    stripe_test_id = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class CustomerCard(db.Model):
    """A customer's saved card (owner decision 2026-11-20, Uber-like
    payments). Customers have no accounts, so cards are keyed by
    phone. Only brand / last 4 / expiry are stored here — the card
    itself lives with Stripe (Stripe Customer + PaymentMethod) and
    is never stored by Noel. A new table, so create_all() creates it
    on the live database too."""
    __tablename__ = "customer_cards"
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(40), nullable=False, index=True)
    stripe_customer_id = db.Column(db.String(60), nullable=False)
    stripe_payment_method_id = db.Column(db.String(60), nullable=False, unique=True)
    brand = db.Column(db.String(20), nullable=True)
    last4 = db.Column(db.String(4), nullable=True)
    exp_month = db.Column(db.Integer, nullable=True)
    exp_year = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (db.UniqueConstraint("phone", "stripe_payment_method_id"),)


class InstantPayout(db.Model):
    """A driver's instant cash-out (owner decision 2026-11-20):
    completed-ride earnings paid out at once to his eligible debit
    card via Stripe Instant Payouts (1.5% fee). The standard 7-day
    weekly payout stays the free default. The cashed-out bookings
    are marked payout_paid so the weekly cycle never pays them
    twice. A new table, so create_all() creates it on the live
    database too."""
    __tablename__ = "instant_payouts"
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=False)
    amount = db.Column(Numeric(10, 2), nullable=False)  # gross cashed out
    fee = db.Column(Numeric(10, 2), nullable=False)  # Stripe 1.5% instant fee
    net = db.Column(Numeric(10, 2), nullable=False)  # what the driver receives
    stripe_transfer_id = db.Column(db.String(80), nullable=True)
    stripe_payout_id = db.Column(db.String(80), nullable=True)
    status = db.Column(db.String(20), nullable=False)  # succeeded | failed
    # Comma-separated booking ids cashed out in this payout.
    booking_ids = db.Column(db.Text, nullable=False, default="")
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
    # Optional HTML part of an email row (the plain-text `body`
    # stays the fallback and is what the owner dashboard shows).
    # Used by the payment receipt and the chauffeur-assigned email
    # (owner 2026-11-23, both step-by-step); NULL means text-only,
    # as before.
    html_body = db.Column(db.Text, nullable=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=True)
    # Set only when Resend confirms the email was sent (owner
    # decision 2026-11-18, Resend sender). NULL means queued only:
    # no key configured, a failed send, or an SMS row (Resend is
    # email-only, SMS is never sent). Nullable, so rows queued
    # before sending existed read as queued, exactly as before.
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class PasswordResetToken(db.Model):
    """Single-use password reset token (owner decision 2026-11-18,
    drivers keep forgetting passwords). Only the SHA-256 hash of
    the token is stored — never the token itself — plus a 5-minute
    expiry and a used flag. A new table, so create_all() creates
    it on the live database too. The reset link is queued via the
    existing outbox (recorded, not sent — no email service is
    connected) and never appears in any API response or log."""
    __tablename__ = "password_reset_tokens"
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class BookingEvent(db.Model):
    __tablename__ = "booking_events"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    type = db.Column(db.String(40), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class EmergencyCancel(db.Model):
    """One emergency cancel inside the 2-hour window (owner decision
    2026-11-18, voice call). The driver MUST give a reason; the
    reason is judged automatically by the rule-based judge below —
    never by the owner, never by an external AI service. One row per
    cancel, so a booking cancelled twice keeps both records. The
    owner dashboard shows these read-only (information only, no
    action, no approval). `driver_id` has no foreign key and
    `driver_name` is a snapshot, so the record survives the
    test-only driver clear. A new table, so create_all() creates it
    on the live database too."""
    __tablename__ = "emergency_cancels"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    driver_id = db.Column(db.Integer, nullable=True)
    driver_name = db.Column(db.String(120), nullable=False, default="")
    reason = db.Column(db.String(40), nullable=False)
    reason_label = db.Column(db.String(120), nullable=False, default="")
    detail = db.Column(db.Text, nullable=True)
    judgment = db.Column(db.String(10), nullable=False)  # genuine | fault
    # True when an "Other" free-text reason matched neither the
    # emergency nor the fault keywords: the benefit of the doubt
    # (genuine, no suspension) was given, and the case is flagged
    # for owner visibility.
    flagged = db.Column(db.Boolean, nullable=False, default=False)
    suspended_until = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class DriverReferralCredit(db.Model):
    """One $5 referral credit (owner decision 2026-11-18, voice call):
    Noel pays the referring driver $5 in cash for each job the
    referred driver completes, up to the referred driver's first 15
    jobs (max $75 per referred driver). One row per credited job, so
    the count is exact and auditable. Tracking only — no money moves
    here, like the existing payout tracking. `referrer_driver_id`
    and `referred_driver_id` have no foreign keys and the names are
    snapshots, mirroring EmergencyCancel, so the record survives the
    test-only driver clear. `booking_id` DOES reference the booking,
    so the test-only clear-rides reset deletes these rows with the
    rides (children first, like emergency cancels). A new table, so
    create_all() creates it on the live database too."""
    __tablename__ = "driver_referral_credits"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    referrer_driver_id = db.Column(db.Integer, nullable=True)
    referrer_name = db.Column(db.String(120), nullable=False, default="")
    referred_driver_id = db.Column(db.Integer, nullable=True)
    referred_driver_name = db.Column(db.String(120), nullable=False, default="")
    amount = db.Column(Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class SupportMessage(db.Model):
    """A typed message from the pre-booking 'Chat with us' widget.
    The widget is available always (no booking, no trip), and its
    scripted answers promise owner escalation and a reply within 24
    hours — so typed messages are stored here for the owner
    dashboard instead of vanishing. Text only, no name/phone/email
    fields; the widget never asks for them. `flagged` marks
    problem/escalation keywords (see SUPPORT_FLAG_KEYWORDS). A new
    table, so create_all() creates it on the live database too. It
    has no booking link, so the test-only clear-rides reset (which
    deletes ride-related rows) leaves it untouched."""
    __tablename__ = "support_messages"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    flagged = db.Column(db.Boolean, nullable=False, default=False)
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
    # Same pattern for the receipt booking code (owner 2026-11-23).
    # Nullable, so existing rows keep working with no code on file
    # (one is generated when their receipt is sent).
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _cols = [c["name"] for c in _sa_inspect(db.engine).get_columns("bookings")]
        if "booking_code" not in _cols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE bookings ADD COLUMN booking_code VARCHAR(10)")
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("booking_code column check failed: %s", exc)
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
    # Same pattern for the extra-distance + dispatcher-lite columns
    # (added 2026-11-16). DEFAULT 0 backfills existing rows, so the
    # NOT NULL columns read 0 on bookings that predate them.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _bcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("bookings")]
        _badds = {
            "extra_miles": "ALTER TABLE bookings ADD COLUMN extra_miles NUMERIC(6, 1) DEFAULT 0",
            "extra_distance_charge": "ALTER TABLE bookings ADD COLUMN extra_distance_charge NUMERIC(10, 2) DEFAULT 0",
            "assigned_driver_id": "ALTER TABLE bookings ADD COLUMN assigned_driver_id INTEGER",
        }
        for _name, _ddl in _badds.items():
            if _name not in _bcols:
                with db.engine.begin() as _conn:
                    _conn.execute(_sa_text(_ddl))
    except Exception as exc:  # logged, never fatal at startup
        log.warning("extra-distance/assigned-driver column check failed: %s", exc)
    # Same pattern for the driver state column (added with the
    # per-state document requirements, 2026-11-17). Nullable, so
    # existing driver rows keep working with no state on file.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _dcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("drivers")]
        if "state" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(_sa_text("ALTER TABLE drivers ADD COLUMN state VARCHAR(40)"))
    except Exception as exc:  # logged, never fatal at startup
        log.warning("state column check failed: %s", exc)
    # Same pattern for the driver city column (added with the
    # Uber-style city picker, 2026-11-17). Nullable, so existing
    # driver rows keep working with no city on file.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _dcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("drivers")]
        if "city" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(_sa_text("ALTER TABLE drivers ADD COLUMN city VARCHAR(80)"))
    except Exception as exc:  # logged, never fatal at startup
        log.warning("city column check failed: %s", exc)
    # Same pattern for the chat-translation columns (added with the
    # Azure Translator chat translation, 2026-11-18). All nullable,
    # so existing driver, booking and message rows keep working with
    # no language on file (English default, original text shown).
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _dcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("drivers")]
        if "chat_language" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE drivers ADD COLUMN chat_language VARCHAR(10)")
                )
        _bcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("bookings")]
        if "customer_chat_language" not in _bcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text(
                        "ALTER TABLE bookings ADD COLUMN customer_chat_language VARCHAR(10)"
                    )
                )
        _mcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("chat_messages")]
        _madds = {
            "sender_language": "ALTER TABLE chat_messages ADD COLUMN sender_language VARCHAR(10)",
            "translated_text": "ALTER TABLE chat_messages ADD COLUMN translated_text TEXT",
            "translated_language": "ALTER TABLE chat_messages ADD COLUMN translated_language VARCHAR(10)",
        }
        for _name, _ddl in _madds.items():
            if _name not in _mcols:
                with db.engine.begin() as _conn:
                    _conn.execute(_sa_text(_ddl))
    except Exception as exc:  # logged, never fatal at startup
        log.warning("chat-translation column check failed: %s", exc)
    # Same pattern for the 1-hour pickup reminder flag (added with the
    # driver pickup reminder, 2026-11-18). Nullable, so existing
    # booking rows keep working with no reminder queued.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _bcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("bookings")]
        if "pickup_reminder_sent_at" not in _bcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text(
                        "ALTER TABLE bookings ADD COLUMN pickup_reminder_sent_at "
                        "TIMESTAMP WITH TIME ZONE"
                    )
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("pickup-reminder column check failed: %s", exc)
    # Same pattern for the driver password hash (added with the
    # email+password sign-in, 2026-11-18). Nullable, so existing
    # driver rows keep working with no hash on file (phone lookup).
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _dcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("drivers")]
        if "password_hash" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE drivers ADD COLUMN password_hash VARCHAR(255)")
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("password-hash column check failed: %s", exc)
    # Same pattern for the outbox sent flag (added with the Resend
    # email sender, 2026-11-18). Nullable, so existing outbox rows
    # keep reading as queued-only.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _ocols = [c["name"] for c in _sa_inspect(db.engine).get_columns("outbox_messages")]
        if "sent_at" not in _ocols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text(
                        "ALTER TABLE outbox_messages ADD COLUMN sent_at "
                        "TIMESTAMP WITH TIME ZONE"
                    )
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("outbox sent_at column check failed: %s", exc)
    # Same pattern for the optional HTML part of an email row
    # (payment receipt, owner 2026-11-23). Nullable, so existing
    # rows keep reading as text-only.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _ocols = [c["name"] for c in _sa_inspect(db.engine).get_columns("outbox_messages")]
        if "html_body" not in _ocols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text(
                        "ALTER TABLE outbox_messages ADD COLUMN html_body TEXT"
                    )
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("outbox html_body column check failed: %s", exc)
    # Same pattern for the driver suspension end (added with the
    # AI-judged emergency cancel, 2026-11-18). Nullable, so existing
    # driver rows keep reading as unsuspended.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _dcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("drivers")]
        if "suspended_until" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text(
                        "ALTER TABLE drivers ADD COLUMN suspended_until "
                        "TIMESTAMP WITH TIME ZONE"
                    )
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("suspended_until column check failed: %s", exc)
    # Same pattern for the driver referral columns (added with the
    # driver referral link, 2026-11-18). Nullable, so existing driver
    # rows keep working with no referral code (minted on first
    # referral-section load) and no referrer.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _dcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("drivers")]
        if "referral_code" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE drivers ADD COLUMN referral_code VARCHAR(40)")
                )
        if "referred_by_driver_id" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE drivers ADD COLUMN referred_by_driver_id INTEGER")
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("driver referral column check failed: %s", exc)
    # Same pattern for the customer referral discount (added with the
    # 5% first-ride referral discount, owner decision 2026-11-18).
    # Nullable, so rows created before the discount existed keep
    # reading as "no discount recorded".
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _bcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("bookings")]
        if "referral_discount" not in _bcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE bookings ADD COLUMN referral_discount NUMERIC(10, 2)")
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("referral discount column check failed: %s", exc)
    # Same pattern for the live-Stripe payment columns (added with
    # Uber-like payments, owner decision 2026-11-20). All nullable,
    # so existing payment rows keep working; legacy test-mode rows
    # keep their pi_test_ id and "succeeded" status.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _pcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("payments")]
        _padds = {
            "brand": "ALTER TABLE payments ADD COLUMN brand VARCHAR(20)",
            "stripe_payment_intent_id": "ALTER TABLE payments ADD COLUMN stripe_payment_intent_id VARCHAR(80)",
            "stripe_customer_id": "ALTER TABLE payments ADD COLUMN stripe_customer_id VARCHAR(60)",
            "stripe_payment_method_id": "ALTER TABLE payments ADD COLUMN stripe_payment_method_id VARCHAR(60)",
            "captured_amount": "ALTER TABLE payments ADD COLUMN captured_amount NUMERIC(10, 2)",
        }
        for _name, _ddl in _padds.items():
            if _name not in _pcols:
                with db.engine.begin() as _conn:
                    _conn.execute(_sa_text(_ddl))
        _dcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("drivers")]
        if "stripe_connect_account_id" not in _dcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE drivers ADD COLUMN stripe_connect_account_id VARCHAR(60)")
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("live-Stripe column check failed: %s", exc)
    # Same pattern for the driver document verification columns
    # (added with the duplicate/expiry checks, owner decision
    # 2026-11-19). Nullable, so documents stored before this existed
    # keep working with no hash or expiry on file — existing drivers
    # are never blocked retroactively.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _ddcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("driver_documents")]
        if "file_hash" not in _ddcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE driver_documents ADD COLUMN file_hash VARCHAR(64)")
                )
        if "expires_on" not in _ddcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE driver_documents ADD COLUMN expires_on DATE")
                )
        if "expiry_alert_sent_at" not in _ddcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE driver_documents ADD COLUMN "
                             "expiry_alert_sent_at TIMESTAMP WITH TIME ZONE")
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("driver document verification column check failed: %s", exc)
    # Same pattern for the return-trip flag (added with the
    # return-trip label fix, owner decision 2026-11-20).
    # DEFAULT FALSE backfills existing rows, so bookings made
    # before the flag existed read as outward one-ways — the old
    # test return booking is NOT relabelled from thin air.
    try:
        from sqlalchemy import inspect as _sa_inspect
        from sqlalchemy import text as _sa_text

        _bcols = [c["name"] for c in _sa_inspect(db.engine).get_columns("bookings")]
        if "is_return" not in _bcols:
            with db.engine.begin() as _conn:
                _conn.execute(
                    _sa_text("ALTER TABLE bookings ADD COLUMN is_return BOOLEAN DEFAULT FALSE")
                )
    except Exception as exc:  # logged, never fatal at startup
        log.warning("return-trip flag column check failed: %s", exc)

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


# --- Customer referral 5% discount (owner decision 2026-11-18, voice
# call): the NEW customer gets 5% off their FIRST one-way booking made
# with a valid referral code. The referring customer gets NOTHING.
# First booking only, identified by phone number. If the referred
# friend later refers someone else, that next new customer gets 5%
# off their first booking too (every booking issues its own code);
# referrers never earn at any step.
def _phone_key(phone):
    """Normalize a phone number for first-booking comparison: digits
    only, US country code stripped, last 10 digits. Two spellings of
    the same number ("+1 929-385-7597" vs "9293857597") compare equal.
    """
    import re as _re

    digits = _re.sub(r"\D", "", str(phone or ""))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


def is_first_booking_by_phone(phone, exclude_booking_id=None):
    """True when no prior booking row exists for this phone number
    (any status — including a cancelled unpaid booking: the owner
    rule is 'if that phone already has a prior booking, no
    discount'). Called at booking creation, before the new booking
    is stored, so the booking being created is never counted. The
    contact step calls it after the booking is stored, so it passes
    its own id to exclude.
    """
    key = _phone_key(phone)
    if not key:
        return False
    for (stored, bid) in db.session.query(Booking.phone, Booking.id).all():
        if exclude_booking_id is not None and bid == exclude_booking_id:
            continue
        if _phone_key(stored) == key:
            return False
    return True


def booking_referral_discount_applies(booking):
    """True when this booking was granted the 5% first-ride referral
    discount at creation. The stored amount is the source of truth:
    NULL (rows created before the discount existed) or $0.00 (a code
    was used but no discount applied) both mean no discount, so
    recomputes (class change, toll change) preserve the
    creation-time decision instead of re-deciding it.
    """
    amount = getattr(booking, "referral_discount", None)
    return amount is not None and Decimal(str(amount)) > 0


# --- Driver referral link (owner decision 2026-11-18, voice call +
# chat confirmation 09:35 EST). The driver referral is a shareable
# LINK, not a code number: the driver sends the link to a friend, the
# friend clicks it and lands straight in driver registration, and
# Noel pays the referring driver $5 in cash for each job the referred
# driver completes, up to the referred driver's first 15 jobs (max
# $75). The new driver pays nothing. Tracking only — no money moves,
# like the existing payout tracking. SEPARATE from the customer
# referral: different table, different code namespace, different
# link; a customer code can never resolve to a driver.
# DEFAULTS (flagged for the owner — he can change any of them): the
# "DRV-" code prefix, the $5 / 15-job figures as constants, and the
# referral section living on the driver app's Profile screen.
DRIVER_REFERRAL_CREDIT = Decimal("5.00")
DRIVER_REFERRAL_MAX_JOBS = 15


def generate_driver_referral_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "DRV-" + "".join(secrets.choice(alphabet) for _ in range(6))
        if not Driver.query.filter_by(referral_code=code).first():
            return code


def driver_referral_code(driver):
    """The driver's stable referral code, or None. getattr-based so a
    driver row read before the column existed degrades to 'no code'
    instead of raising."""
    return getattr(driver, "referral_code", None)


def driver_referred_by_id(driver):
    """The id of the driver who referred this driver, or None.
    getattr-based, same degradation as driver_referral_code."""
    return getattr(driver, "referred_by_driver_id", None)


def ensure_driver_referral_code(driver):
    """The driver's stable referral code, minting one for drivers
    registered before referral codes existed. Returns (code, minted):
    the caller commits when a code was minted."""
    code = driver_referral_code(driver)
    if code:
        return code, False
    code = generate_driver_referral_code()
    driver.referral_code = code
    return code, True


def record_driver_referral_credit(booking, driver):
    """Credit $5 to the referrer when a referred driver completes a
    job, for the referred driver's first 15 completed jobs only.
    Called from the trip-complete branch, in the same transaction as
    the completion itself (the caller commits). A silent no-op when
    the driver has no referrer, when the referrer is the driver
    himself (self-referral earns nothing), or when the first 15 jobs
    are already counted. Jobs completed before this feature shipped
    never count: only drivers who registered via a referral link
    carry a referrer, and referral links only existed from this
    build on."""
    referrer_id = driver_referred_by_id(driver)
    if not referrer_id or referrer_id == driver.id:
        return None
    counted = DriverReferralCredit.query.filter_by(
        referred_driver_id=driver.id,
        referrer_driver_id=referrer_id).count()
    if counted >= DRIVER_REFERRAL_MAX_JOBS:
        return None
    referrer = db.session.get(Driver, referrer_id)
    credit = DriverReferralCredit(
        booking_id=booking.id,
        referrer_driver_id=referrer_id,
        referrer_name=referrer.name if referrer else "",
        referred_driver_id=driver.id,
        referred_driver_name=driver.name,
        amount=DRIVER_REFERRAL_CREDIT,
    )
    db.session.add(credit)
    return credit


def driver_referral_summary(driver):
    """The signed-in driver's own referral view: his code, his total
    referral earnings, and one row per driver he referred (jobs
    counted out of the first 15, dollars earned). His own earnings
    only — never another driver's fares or totals."""
    friends = Driver.query.filter(
        Driver.referred_by_driver_id == driver.id).order_by(
            Driver.created_at, Driver.id).all()
    breakdown = []
    total_jobs = 0
    for friend in friends:
        credits = DriverReferralCredit.query.filter_by(
            referred_driver_id=friend.id,
            referrer_driver_id=driver.id).all()
        jobs = len(credits)
        total_jobs += jobs
        breakdown.append({
            "name": friend.name,
            "jobs_counted": jobs,
            "registered_at": iso(friend.created_at),
        })
    return {
        "referral_code": driver_referral_code(driver),
        "max_jobs_per_driver": DRIVER_REFERRAL_MAX_JOBS,
        "jobs_counted": total_jobs,
        "referred_drivers": breakdown,
    }


def driver_referral_records():
    """Merged referral relationships for the owner dashboard: every
    driver who registered via a referral link (including friends with
    no completed jobs yet) plus every credit aggregate (which
    survives the test-only driver clear via its name snapshots).
    Read-only information — no action, no approval step."""
    rows = {}
    referred = Driver.query.filter(
        Driver.referred_by_driver_id.isnot(None)).order_by(
            Driver.created_at, Driver.id).all()
    for d in referred:
        referrer_id = driver_referred_by_id(d)
        referrer = db.session.get(Driver, referrer_id) if referrer_id else None
        rows[(referrer_id, d.id)] = {
            "referrer_driver_id": referrer_id,
            "referrer_name": referrer.name if referrer else "",
            "referred_driver_id": d.id,
            "referred_driver_name": d.name,
            "registered_at": iso(d.created_at),
            "jobs_counted": 0,
            "earned": Decimal("0.00"),
        }
    for c in DriverReferralCredit.query.order_by(DriverReferralCredit.id).all():
        key = (c.referrer_driver_id, c.referred_driver_id)
        row = rows.get(key)
        if row is None:
            row = {
                "referrer_driver_id": c.referrer_driver_id,
                "referrer_name": c.referrer_name,
                "referred_driver_id": c.referred_driver_id,
                "referred_driver_name": c.referred_driver_name,
                "registered_at": None,
                "jobs_counted": 0,
                "earned": Decimal("0.00"),
            }
            rows[key] = row
        if not row["referrer_name"]:
            row["referrer_name"] = c.referrer_name
        if not row["referred_driver_name"]:
            row["referred_driver_name"] = c.referred_driver_name
        row["jobs_counted"] += 1
        row["earned"] = row["earned"] + (c.amount or Decimal("0.00"))
    records = sorted(
        rows.values(),
        key=lambda r: (r["referrer_name"] or "", r["referred_driver_name"] or ""))
    for r in records:
        r["earned"] = num(r["earned"])
    return records


def add_event(booking_id, event_type, message):
    db.session.add(BookingEvent(booking_id=booking_id, type=event_type, message=message))


# --- Emergency cancel inside the 2-hour window (owner decision --------
# 2026-11-18, voice call — SUPERSEDES the 2026-11-17 deferral of the
# emergency flow). DRIVER ONLY: the customer is never penalised and
# never sees any of this; every driver cancel auto re-dispatches.
# Inside 2 hours the driver CAN cancel but MUST give a reason. The
# reason is judged AUTOMATICALLY by the rules below — no manual
# review by the owner, and NO external AI/LLM API call (no keys, no
# cost, no driver PII sent anywhere). A fault judgment blocks the
# driver's app for 48 hours; a genuine emergency never blocks.
# Owner decision 2026-11-24: Azher Mohammed and Sana Baga are
# exempt from the fault block entirely (see suspension_exempt_for).
# DEFAULTS (flagged for the owner — he can change any of them): the
# reason list, the keyword lists, the benefit-of-the-doubt default,
# and the 48-hour length are all defaults picked for this build.
EMERGENCY_CANCEL_REASONS = (
    ("breakdown", "Car breakdown or accident", "genuine"),
    ("medical", "Medical emergency", "genuine"),
    ("family", "Family emergency", "genuine"),
    ("other_job", "I took another job", "fault"),
    ("dont_want", "I do not want this trip", "fault"),
    ("running_late", "Running late / overslept", "fault"),
    ("other", "Other (please explain)", None),  # judged from free text
)
EMERGENCY_CANCEL_REASON_LABELS = {k: label for k, label, _ in EMERGENCY_CANCEL_REASONS}
_EMERGENCY_CANCEL_FIXED_JUDGMENT = {k: j for k, _, j in EMERGENCY_CANCEL_REASONS if j}
# "Other" free-text keyword match. Emergency signals win over fault
# signals (benefit of the doubt); neither matching also defaults to
# genuine, flagged for owner visibility.
EMERGENCY_CANCEL_FAULT_KEYWORDS = (
    "another job", "other job", "don't want", "do not want",
    "dont want", "too far", "pay too low", "not worth",
    "changed my mind", "overslept", "running late", "don't feel",
    "dont feel", "tired", "too tired",
)
EMERGENCY_CANCEL_EMERGENCY_KEYWORDS = (
    "accident", "breakdown", "broke down", "hospital", "emergency",
    "ambulance", "sick", "injured", "injury", "flat tire",
    "flat tyre", "car won't start", "car wont start", "police",
    "towed", "tow truck",
)
SUSPENSION_HOURS = 48


def judge_emergency_cancel(reason, detail):
    """Automatic judgment for an emergency cancel. Returns
    (judgment, flagged): judgment is \"genuine\" or \"fault\"; flagged
    is True only when an \"Other\" reason matched no keywords and
    the benefit of the doubt was given. Pure function — no I/O."""
    fixed = _EMERGENCY_CANCEL_FIXED_JUDGMENT.get(reason)
    if fixed:
        return fixed, False
    text = (detail or "").lower()
    if any(kw in text for kw in EMERGENCY_CANCEL_EMERGENCY_KEYWORDS):
        return "genuine", False
    if any(kw in text for kw in EMERGENCY_CANCEL_FAULT_KEYWORDS):
        return "fault", False
    return "genuine", True


def _as_aware(dt):
    """Naive datetimes (SQLite) read as UTC, same as iso() does."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def driver_suspension_end(driver):
    """The driver's suspension end as an aware datetime, or None.
    getattr-based so a driver row read before the column existed
    degrades to 'not suspended' instead of raising.
    Owner decision 2026-11-24: Azher Mohammed and Sana Baga are
    exempt from the 48-hour fault suspension, so their suspension
    end always reads as None here — a suspension already on their
    record is treated as lifted everywhere this helper is read
    (the driver app banner, go-online, offers and accept), and no
    new one is ever stored for them (see the cancel handler)."""
    if driver is not None and suspension_exempt_for(
            getattr(driver, "email", None)):
        return None
    return _as_aware(getattr(driver, "suspended_until", None))


def is_driver_suspended(driver, now=None):
    end = driver_suspension_end(driver)
    if end is None:
        return False
    return end > (now or utcnow())


def suspension_message(driver):
    """Plain-English suspension notice with the exact end date/time
    in New York time, for API errors and the driver app banner."""
    end = driver_suspension_end(driver)
    if end is None:
        return "Your driver app is paused."
    try:
        from zoneinfo import ZoneInfo
        shown = end.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        shown = end
    return ("Your driver app is paused until "
            + shown.strftime("%B %d, %Y at %I:%M %p")
            + " (New York time). You will not get job offers until then.")


def _redispatch_blocked_driver_jobs(driver, exclude_booking_id):
    """Owner decision 2026-11-24 ('Haan, bana do'): when a driver is
    blocked (48-hour fault block), his other accepted-but-not-yet-
    started jobs go back to "offered" for re-dispatch to other
    drivers — a blocked driver must not keep running jobs. A trip
    already in progress (status "in_progress": the driver started
    the trip, the customer is in the car) stays with the driver; it
    cannot be handed to another driver mid-way. Jobs only heading
    to pickup or waiting there ("en_route", "arrived") have not
    started, so they go back too. The cancelled job itself is
    excluded here — the caller already re-dispatched it. Returns
    the list of booking ids sent back."""
    others = (Booking.query.filter(
        Booking.accepted_driver_id == driver.id,
        Booking.status.in_(("accepted", "en_route", "arrived")),
        Booking.id != exclude_booking_id,
    ).order_by(Booking.id).all())
    redispatched = []
    for other in others:
        other.status = "offered"
        other.accepted_driver_id = None
        other.assigned_driver_id = None
        other.driver_lat = None
        other.driver_lng = None
        # The reminder flag resets with the re-dispatch, so the next
        # driver to accept gets his own 1-hour reminder.
        other.pickup_reminder_sent_at = None
        if not BookingExclusion.query.filter_by(
                booking_id=other.id, driver_id=driver.id).first():
            db.session.add(BookingExclusion(booking_id=other.id,
                                            driver_id=driver.id))
        add_event(other.id, "driver_blocked_redispatch",
                  f"Driver {driver.name} was blocked for 48 hours, so "
                  f"booking #{other.id} was sent back to other drivers.")
        redispatched.append(other.id)
    return redispatched


# --- Driver document expiry enforcement (owner decision 2026-11-19) ------
# Two owner decisions from the same voice call:
#   1. Ten-day advance alert ("poore documents ki expiry 10 din pehle
#      hi karna"): when a stored expiry date comes within 10 days, the
#      driver is alerted once per document per expiry (see
#      run_expiry_alerts below).
#   2. Expiry = registration deactivated ("jaisa expire ho jayega phir
#      bhi document hai to uska band kar dena... registration band kar
#      dena, phir wo registration paper upload karega, phir active
#      karna"): a driver with any stored expiry date in the past is
#      blocked — cannot go available, gets no offers — until he
#      re-uploads that document with a valid future expiry date, at
#      which point the block lifts AUTOMATICALLY (the block is computed
#      from the stored dates, never stored on the driver).
# Only a STORED expiry date can block: documents with no expiry on
# file (rows created before the verification build) never block, same
# as the existing registration-gate rule. Sign-in still works while
# blocked, exactly like the 48-hour fault suspension.
EXPIRY_ALERT_DAYS = 10


def expired_documents(driver, today=None):
    """DriverDocument rows whose stored expiry date has passed. A
    document expiring TODAY is still valid — only a date before today
    counts as expired, matching _parse_expiry at registration."""
    today = today or _today_ny()
    return [d for d in driver.documents
            if d.expires_on is not None and d.expires_on < today]


def expiring_documents(driver, today=None, days=EXPIRY_ALERT_DAYS):
    """DriverDocument rows whose stored expiry date is today or
    within the next `days` days — the 10-day advance-alert window."""
    today = today or _today_ny()
    return [d for d in driver.documents
            if d.expires_on is not None
            and 0 <= (d.expires_on - today).days <= days]


def is_driver_expiry_blocked(driver, today=None):
    return bool(expired_documents(driver, today))


def expiry_block_message(driver, today=None):
    """Plain-English block notice naming the expired document(s),
    for API errors and the driver app banner."""
    docs = expired_documents(driver, today)
    if not docs:
        return "Your driver registration is paused."
    labels = ", ".join(ALL_DOC_LABELS.get(d.doc_type, d.doc_type) for d in docs)
    return (f"Your driver registration is paused because your {labels} "
            "expired. Upload a new, valid document in the driver app "
            "to reactivate your registration.")


# Neutral subject for queued emails whose caller passes no subject
# of its own (the reset and reminder callers pass theirs).
DEFAULT_EMAIL_SUBJECT = "Noel Chauffer"


def _try_send_email(row, subject):
    """Best-effort Resend send for a queued email row. The row is
    always written first; sending never breaks the caller and never
    raises. On a confirmed send the row is marked sent_at (it
    persists with the caller's commit, like the row itself). SMS
    rows never reach here."""
    try:
        if send_email(row.recipient, subject or DEFAULT_EMAIL_SUBJECT,
                      row.body, html=row.html_body) == EMAIL_SENT:
            row.sent_at = utcnow()
    except Exception as exc:  # never break the caller
        log.warning("outbox email send failed: %s", exc)


def add_outbox(channel, recipient, body, booking_id=None, subject=None, html=None):
    row = OutboxMessage(channel=channel, recipient=recipient, body=body,
                        html_body=html, booking_id=booking_id)
    db.session.add(row)
    if channel == "email":
        _try_send_email(row, subject)
    return row


def outbox_to_customer(booking, sms_body, email_body=None, email_html=None):
    """Queue the SMS + email pair for a booking. The email defaults
    to the SMS text (text-only, as before); callers that need a
    richer email pass their own email_body and, optionally, an HTML
    part (the chauffeur-assigned email, owner 2026-11-23 — line by
    line in plain text AND as an HTML part, same rows). The subject
    stays the default "Noel Chauffer" unless the caller queues the
    email itself (the payment receipt does)."""
    add_outbox("sms", booking.phone, sms_body, booking.id)
    add_outbox("email", booking.email, email_body or sms_body, booking.id,
               html=email_html)


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
    # Statuses for the documents the driver's state + city require. A
    # city with a verified city-specific list (see
    # CITY_DOC_REQUIREMENTS) overrides its
    # state list; drivers registered before the state selector (no
    # state on file) read as New York, the list they registered under
    # — unchanged behaviour.
    present = {d.doc_type for d in driver.documents}
    status = {}
    for doc_type in required_docs_for(driver.state or "New York",
                                      getattr(driver, "city", None)):
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


def validate_routing_number(routing):
    """US bank routing number (owner decision 2026-11-20): a driver
    cannot complete payout setup without a VALID routing number —
    exactly 9 digits with a valid ABA checksum (3/7/1 weights).
    Returns an error string, or None when valid."""
    digits = (routing or "").strip()
    if not digits.isdigit() or len(digits) != 9:
        return "Routing number must be 9 digits."
    weights = (3, 7, 1, 3, 7, 1, 3, 7, 1)
    if sum(w * int(d) for w, d in zip(weights, digits)) % 10 != 0:
        return "Routing number is not valid. Please check it and try again."
    return None


def validate_bank_account_number(account):
    """US bank account number (owner decision 2026-11-20): compulsory
    for payout setup — digits only, 4 to 17 digits. Returns an error
    string, or None when valid."""
    digits = (account or "").strip()
    if not digits.isdigit() or not (4 <= len(digits) <= 17):
        return "Bank account number must be 4 to 17 digits."
    return None


def require_driver():
    token = request.headers.get("X-Driver-Token")
    if not token:
        return None, err("Missing X-Driver-Token header.", 401)
    driver = Driver.query.filter_by(token=token).first()
    if not driver:
        return None, err("Invalid driver token.", 401)
    return driver, None


def require_owner():
    """Every owner data endpoint requires a valid PIN session,
    server-side (owner decision 2026-11-23): the session is
    timestamped at login and expires OWNER_SESSION_MAX_AGE_SECONDS
    later. A session with no timestamp (from before the expiry was
    added) no longer counts — the owner types the PIN once and gets
    a fresh, timestamped session."""
    if not session.get("owner"):
        return err("Owner login required.", 401)
    authed_at = session.get("owner_authed_at")
    if not isinstance(authed_at, (int, float)):
        session.pop("owner", None)
        return err("Owner login required.", 401)
    if datetime.now(timezone.utc).timestamp() - authed_at > OWNER_SESSION_MAX_AGE_SECONDS:
        session.pop("owner", None)
        session.pop("owner_authed_at", None)
        return err("Owner login expired. Please enter your PIN again.", 401)
    return None


def require_owner_pin():
    """Re-confirm the owner PIN at the moment of a destructive action
    (owner decision 2026-11-19, voice call): whenever the owner clears
    anything — rides or drivers, website or owner app — the PIN must be
    typed again right then. A signed-in session alone is NOT enough.
    The PIN travels in the request body and is checked here,
    server-side, against OWNER_PIN — never trusted from the client.
    Returns an error response when the PIN is missing or wrong."""
    data = request.get_json(silent=True) or {}
    pin = data.get("pin")
    if pin is None or not hmac.compare_digest(str(pin), OWNER_PIN):
        return err("Wrong PIN.", 401)
    return None


def _normalize_customer_email(email):
    return (email or "").strip().lower()


def _customer_signin_email():
    """Email the browser is signed in as (None when not signed
    in). Stored in the Flask session after sign-in, so a signed-in
    customer stays signed in for later bookings on the same
    browser."""
    return _normalize_customer_email(session.get("customer_email")) or None


def _customer_signin_phone():
    return (session.get("customer_phone") or "").strip() or None


def _customer_signin_error(booking):
    """The compulsory customer sign-in gate (owner decision
    2026-11-22): a booking may only proceed to payment once the
    customer has signed in with the SAME email the booking
    carries, and a phone number has been given. Returns an error
    string when the gate is not met, else None. The check is
    deliberately strict about the email (the signed-in email must
    match the booking email) and lenient about which phone: any
    non-empty phone on the booking passes, because the phone is
    collected and validated at the contact step."""
    if not booking.email or not booking.phone:
        return "Please add your name, phone and email before paying."
    signed_in = _customer_signin_email()
    if not signed_in:
        return "Please sign in with your email to continue."
    if signed_in != _normalize_customer_email(booking.email):
        return ("Please sign in with the same email as this booking "
                f"({booking.email}).")
    return None


def driver_vehicle_class(driver):
    """A driver's vehicle class: derived from the car model via the
    current mapping in car_models.py, so a mapping change (owner
    decision 2026-11-21: only the 23 Uber Black SUV models are
    "suv", every other model is "sedan") reclasses existing drivers
    automatically — no data migration, no re-registration. The stored
    value is only a fallback for a car model the mapping no longer
    knows. Always "sedan" or "suv" for a validated car model."""
    derived = class_for_model(driver.car_model)
    if derived is not None:
        return derived
    if driver.vehicle_class in ("sedan", "suv"):
        return driver.vehicle_class
    return "sedan"


def booking_vehicle_class(booking):
    """A booking's vehicle class: the stored class for hourly rides
    (Blacklane-style hourly, owner decision 2026-11-20 — the customer
    picks Business / Business SUV / First Class, like Blacklane);
    None for hourly rows created before the class system existed;
    "sedan" for one-way bookings created before the class system
    existed; "first" for First Class bookings (owner decision
    2026-11-20 — First Class is open, Blacklane's four models plus
    eight owner-added flagships, 2026-11-21; see
    car_models.FIRST_CLASS_MODELS)."""
    if booking.ride_type == "hourly":
        if booking.vehicle_class in ("sedan", "suv", "first"):
            return booking.vehicle_class
        return None
    if booking.vehicle_class in ("sedan", "suv", "first"):
        return booking.vehicle_class
    return "sedan"


def driver_matches_booking_class(driver, booking):
    """True when this driver may take this booking's class.

    Business Class / Business SUV match by the driver's sedan/suv
    class; a First Class booking reaches ONLY drivers whose
    registered car model is a First Class model (the twelve in
    car_models.FIRST_CLASS_MODELS — Blacklane's four plus eight
    owner-added flagships, owner decisions 2026-11-20 and
    2026-11-21). Every First Class driver keeps his Business Class
    dispatch — First Class is an extra qualification by model, not
    a replacement class. (Owner decision 2026-11-21: Model X is
    Business Class, not Business SUV — only the 23 Uber Black SUV
    models are SUVs.) Hourly rides with a class
    (Blacklane-style hourly, owner decision 2026-11-20) are filtered
    the same way; hourly rows from before the class system (no class
    stored) reach every driver, as before.
    """
    if booking.ride_type == "hourly" and booking_vehicle_class(booking) is None:
        return True
    if booking_vehicle_class(booking) == "first":
        return is_first_class_model(driver.car_model)
    return booking_vehicle_class(booking) == driver_vehicle_class(driver)


def _recomputed_breakdown(booking):
    """Pricing breakdown recomputed from miles/hours + toll + class.

    Read-only fallback for rows created before fare/tax were stored.
    """
    if booking.ride_type == "hourly":
        return compute_hourly(booking.hours or Decimal("0"),
                              booking.vehicle_class or "sedan")
    if booking_vehicle_class(booking) == "first":
        # First Class has no legacy rate at all (the legacy engine
        # only knows sedan/suv): recompute it with the Blacklane
        # engine, the same engine that priced it at creation.
        return compute_blacklane_one_way(
            booking.miles or Decimal("0"),
            "first",
            booking.pickup, booking.dropoff,
            pickup_details=geo_module.geocode_address(booking.pickup),
            dropoff_details=geo_module.geocode_address(booking.dropoff),
            toll=booking.toll or Decimal("0"),
            referral=booking_referral_discount_applies(booking),
        )
    return compute_one_way(
        booking.miles or Decimal("0"),
        toll=booking.toll or Decimal("0"),
        vehicle_class=booking_vehicle_class(booking),
        referral=booking_referral_discount_applies(booking),
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
    # Owner profit per ride: total + waiting - driver pay - stored tax.
    # New rides store $0.00 tax (removed 2026-11-17), so this is
    # total + waiting - driver pay; rides booked before the removal
    # keep their stored tax subtracted so their profit stays exact.
    return (money(booking.fare_total) + money(booking.waiting_charge)
            - money(booking.driver_earnings) - booking_tax(booking))


# ---------------------------------------------------------- payout weeks ---

# --- Driver busy windows: no double-booking (owner decision 2026-11-16) ---
# A driver who has accepted a ride must not get a second job at the same
# time. A new offer reaches him only when its pickup falls AFTER the
# accepted ride's busy window ends. The window covers the estimated
# driving time (from the booked miles, so a driver coming from
# Connecticut for a JFK job is not offered an overlapping second job)
# plus a buffer for drop-off and getting to the next pickup.
#   one-way: duration = miles / 30 mph, at least 30 minutes.
#   hourly:  duration = the booked hours.
#   buffer:  30 minutes after the estimated end.
# The speeds and buffer are estimates the owner can change in one
# place; the rule itself (no overlapping jobs) is what he decided.
TRIP_AVG_MPH = 30.0
TRIP_MIN_MINUTES = 30
TRIP_BUFFER_MINUTES = 30
ACTIVE_TRIP_STATUSES = ("accepted", "en_route", "arrived", "in_progress")


def _pickup_dt(date_str, time_str):
    """Pickup datetime in America/New_York, or None if unparseable."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/New_York")
    except Exception:
        tz = timezone.utc
    try:
        naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None
    return naive.replace(tzinfo=tz)


def _booking_busy_window(booking):
    """(start, end) datetimes the driver is busy with this booking.

    Returns None when the pickup time cannot be parsed, in which case
    the booking never blocks another job (fail-open: a bad date must
    not hide every offer).
    """
    start = _pickup_dt(booking.date, booking.time)
    if start is None:
        return None
    if booking.ride_type == "hourly" and booking.hours:
        minutes = float(booking.hours) * 60.0
    else:
        miles = float(booking.miles) if booking.miles is not None else 0.0
        minutes = max(miles / TRIP_AVG_MPH * 60.0, TRIP_MIN_MINUTES)
    end = start + timedelta(minutes=minutes + TRIP_BUFFER_MINUTES)
    return (start, end)


def _windows_overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def _active_windows(driver_id):
    """Busy windows of the driver's active trips (accepted, not yet
    completed, cancelled or no-show)."""
    trips = (Booking.query
             .filter(Booking.accepted_driver_id == driver_id,
                     Booking.status.in_(ACTIVE_TRIP_STATUSES))
             .all())
    return [w for w in (_booking_busy_window(t) for t in trips) if w is not None]


def _driver_time_conflict(driver_id, candidate):
    """True if the candidate booking overlaps an active trip of this
    driver, so the driver must not be offered (or accept) it."""
    window = _booking_busy_window(candidate)
    if window is None:
        return False
    return any(_windows_overlap(window, w) for w in _active_windows(driver_id))


# ------------------------------------------------------- pickup reminder ---
# Owner decision 2026-11-18 (voice call): 1 hour before pickup, remind
# the ASSIGNED driver that his ride is about to start — in the driver
# app, by email, and by SMS to his phone number.
#
# HONEST LIMIT: no messaging service is connected. Like every other
# text/email in this app, the reminder email and SMS are written to
# the owner-dashboard outbox only and are NOT actually sent (the
# dashboard says so: "messages are recorded here, not sent yet").
# The in-app alert is the channel that actually reaches the driver,
# and only while he has the app open. When a messaging provider is
# connected, the outbox entries become sendable without changing
# this code. Scheduling is documented at
# run_pickup_reminders_endpoint below: the check fires from the
# app's existing contact points (driver-app polling, active-trip
# fetch, owner dashboard trigger) — no cron, no new infrastructure,
# no billing change.
PICKUP_REMINDER_WINDOW = timedelta(hours=1)


def pickup_reminder_body(booking):
    """Reminder text: pickup time + addresses ONLY. Never miles, fare,
    total, or any other money figure — the driver must never see them."""
    body = ("Noel Chauffer: your ride starts in about an hour. "
            f"Pickup {booking.date} at {booking.time} from {booking.pickup}.")
    if booking.ride_type != "hourly" and booking.dropoff:
        body += f" Drop-off: {booking.dropoff}."
    return body


def _pickup_reminder_due(booking, now):
    """True when the booking's pickup is within the next hour (and not
    already past). Unparseable pickup times never fire."""
    start = _pickup_dt(booking.date, booking.time)
    if start is None:
        return False
    delta = start - now
    return timedelta(0) <= delta <= PICKUP_REMINDER_WINDOW


def run_pickup_reminders(now=None, driver_id=None):
    """Queue the 1-hour pickup reminder for every qualifying booking.

    Qualifies: status "accepted" (an assigned driver, trip not yet
    started, not cancelled), pickup within the next hour, and no
    reminder queued yet for this acceptance (pickup_reminder_sent_at
    is NULL — the idempotency flag, so repeated runs fire once).
    Each firing queues one SMS + one email outbox entry to the driver
    (recorded, not sent — no messaging service is connected) and one
    owner-dashboard alert event. Returns the reminded booking ids.
    `driver_id` scopes the run to one driver; None runs every driver.
    """
    now = now or utcnow()
    query = (Booking.query
             .filter(Booking.status == "accepted",
                     Booking.accepted_driver_id.isnot(None),
                     Booking.pickup_reminder_sent_at.is_(None)))
    if driver_id is not None:
        query = query.filter(Booking.accepted_driver_id == driver_id)
    reminded = []
    for booking in query.all():
        if not _pickup_reminder_due(booking, now):
            continue
        driver = db.session.get(Driver, booking.accepted_driver_id)
        if not driver:
            continue
        body = pickup_reminder_body(booking)
        add_outbox("sms", driver.phone, body, booking.id)
        if driver.email:
            add_outbox("email", driver.email, body, booking.id,
                       subject="Your ride starts in about an hour")
        add_event(booking.id, "pickup_reminder",
                  f"Pickup reminder queued for driver {driver.name} "
                  f"(booking #{booking.id}).")
        booking.pickup_reminder_sent_at = now
        reminded.append(booking.id)
    if reminded:
        db.session.commit()
    return reminded


def _run_pickup_reminders_best_effort(driver_id=None):
    """Run the reminder check without ever breaking the caller's
    response: a reminder failure must not fail a driver poll or an
    active-trip fetch. Logs and rolls back on any error."""
    try:
        return run_pickup_reminders(driver_id=driver_id)
    except Exception as exc:
        db.session.rollback()
        log.warning("pickup reminder check failed: %s", exc)
        return []


def _due_pickup_reminder_for_driver(driver_id, now=None):
    """The driver's accepted booking whose pickup is within the next
    hour, for the in-app banner — or None. Driven by the time window
    alone (not the reminder flag), so the banner shows while the ride
    is about to start even after the reminder record was queued.
    Never references the flag column, so the banner keeps working
    even if the column migration has not run yet."""
    now = now or utcnow()
    bookings = (Booking.query
                .filter(Booking.accepted_driver_id == driver_id,
                        Booking.status == "accepted")
                .order_by(Booking.date, Booking.time, Booking.id)
                .all())
    for booking in bookings:
        if _pickup_reminder_due(booking, now):
            return booking
    return None


# --- Driver document expiry alerts (owner decision 2026-11-19) -----------
# Ten-day advance alert for EVERY document with a stored expiry date
# ("poore documents ki expiry 10 din pehle hi karna", "ten days
# before"). One alert per document per expiry, via the
# expiry_alert_sent_at flag on the DriverDocument row: the flag is
# set when the alert fires and resets only when the driver re-uploads
# that document with a different expiry date, so a new expiry gets
# its own alert. A document already inside the 10-day window when
# the check first runs alerts immediately; a document already expired
# (missed window) alerts once with the expired wording, so a blocked
# driver who never opens the app still hears why. No alert when the
# expiry is more than 10 days away.
#
# Channels (same as the 1-hour pickup reminder): an in-app notice in
# the driver app (from /api/drivers/me — expired_docs /
# expiring_docs), plus one SMS and one email in the owner-dashboard
# outbox via add_outbox. Email rows are actually sent by Resend when
# configured (see _try_send_email); SMS rows are recorded only —
# Resend is email-only, SMS is never sent. There is no BookingEvent
# for these alerts: BookingEvent.booking_id is NOT NULL and a
# document alert has no booking, so owner visibility is the outbox
# rows plus GET /api/owner/expiring-documents below.
# Scheduling follows the pickup-reminder pattern exactly: the check
# fires from the app's existing contact points (driver-app
# /api/drivers/me and /api/drivers/me/offers, owner dashboard load)
# plus a cron endpoint — no new infrastructure, no billing change.


def expiry_alert_body(driver, doc, days_left):
    """Alert text naming the document and its expiry date."""
    label = ALL_DOC_LABELS.get(doc.doc_type, doc.doc_type)
    exp = doc.expires_on.strftime("%B %d, %Y")
    if days_left < 0:
        return (f"Noel Chauffer: your {label} expired on {exp}. Your "
                "driver registration is paused — please upload a new, "
                "valid document in the driver app to reactivate it.")
    if days_left == 0:
        when = "today"
    elif days_left == 1:
        when = "tomorrow"
    else:
        when = f"in {days_left} days"
    return (f"Noel Chauffer: your {label} expires {when} ({exp}). "
            "Please upload a new, valid document in the driver app "
            "so your registration stays active.")


def run_expiry_alerts(now=None, driver_id=None):
    """Queue the 10-day expiry alert for every qualifying document.

    Qualifies: a stored expiry date within the next 10 days (or
    already past, if never alerted), and no alert sent yet for this
    expiry (expiry_alert_sent_at is NULL — the idempotency flag, so
    repeated runs fire once). Each firing queues one SMS + one email
    outbox entry to the driver (email actually sent via Resend when
    configured; SMS recorded only) and sets the flag. Returns the
    alerted documents as dicts. `driver_id` scopes the run to one
    driver; None runs every driver.
    """
    now = now or utcnow()
    today = _today_ny()
    query = (DriverDocument.query
             .filter(DriverDocument.expires_on.isnot(None),
                     DriverDocument.expiry_alert_sent_at.is_(None)))
    if driver_id is not None:
        query = query.filter(DriverDocument.driver_id == driver_id)
    alerted = []
    for doc in query.all():
        days_left = (doc.expires_on - today).days
        if days_left > EXPIRY_ALERT_DAYS:
            continue
        driver = db.session.get(Driver, doc.driver_id)
        if not driver:
            continue
        body = expiry_alert_body(driver, doc, days_left)
        add_outbox("sms", driver.phone, body)
        if driver.email:
            add_outbox("email", driver.email, body,
                       subject="Your Noel Chauffer document expires soon")
        doc.expiry_alert_sent_at = now
        alerted.append({
            "driver_id": driver.id,
            "doc_type": doc.doc_type,
            "expires_on": doc.expires_on.isoformat(),
            "days_left": days_left,
        })
    if alerted:
        db.session.commit()
    return alerted


def _run_expiry_alerts_best_effort(driver_id=None):
    """Run the expiry-alert check without ever breaking the caller's
    response: an alert failure must not fail a driver poll or a
    dashboard load. Logs and rolls back on any error."""
    try:
        return run_expiry_alerts(driver_id=driver_id)
    except Exception as exc:
        db.session.rollback()
        log.warning("expiry alert check failed: %s", exc)
        return []


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


def recompute_booking_fare(booking, referral=None):
    """Recompute fare/driver/gratuity/tax/fee from miles/hours +
    current toll + vehicle class, at the CURRENT pricing formula
    (legacy: total = fare + toll; gratuity and tax are $0.00 for new
    computations — see pricing.py. Blacklane mode, when
    NOEL_PRICING=blacklane: total = base fare + Blacklane fees, and
    tax holds the Blacklane sales-tax component — see
    blacklane_pricing.py).

    The 5% first-ride referral discount is NOT re-decided here by
    default: a booking granted it at creation keeps it (recomputed
    at 5% of the new total) and a booking without it never gains
    it — the stored referral_discount is the source of truth. Pass
    referral=True/False to re-decide it instead: the contact step
    does that, because creation could not decide it — the phone was
    not known yet.
    """
    referral_flag = referral if referral is not None else booking_referral_discount_applies(booking)
    if booking.ride_type == "hourly":
        result = compute_hourly(booking.hours or Decimal("0"),
                                booking.vehicle_class or "sedan")
    else:
        if pricing_mode() == "blacklane":
            # Pass the RAW stored class (booking_vehicle_class()
            # returns "first" for First Class now, but the raw
            # column is the source of truth here). First Class
            # driver pay is the flat slab (owner decision 2026-11-20
            # ~06:25 EST).
            raw_class = (booking.vehicle_class or "").strip().lower() or "sedan"
            result = compute_blacklane_one_way(
                booking.miles or Decimal("0"),
                raw_class,
                booking.pickup, booking.dropoff,
                pickup_details=geo_module.geocode_address(booking.pickup),
                dropoff_details=geo_module.geocode_address(booking.dropoff),
                toll=booking.toll or Decimal("0"),
                referral=referral_flag,
            )
        else:
            result = compute_one_way(
                booking.miles or Decimal("0"),
                toll=booking.toll or Decimal("0"),
                vehicle_class=booking_vehicle_class(booking),
                referral=referral_flag,
            )
        booking.vehicle_class = result["vehicle_class"]
    booking.fare_total = result["total"]
    booking.driver_earnings = result["driver_earnings"]
    booking.gratuity = result["gratuity"]
    booking.booking_fee = result["booking_fee"]
    booking.fare = result["fare"]
    booking.tax = result["tax"]
    # 5% first-ride referral discount granted on this booking
    # (one-way only; hourly rides never get one). None on hourly
    # rides, $0.00 when a code was used but no discount applied.
    booking.referral_discount = result.get("referral_discount")
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


@app.route("/robots.txt")
def robots_txt():
    return send_from_directory(app.static_folder, "robots.txt", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    return send_from_directory(app.static_folder, "sitemap.xml", mimetype="application/xml")


@app.route("/")
def home():
    return _serve_page("index.html", "customer booking")


@app.route("/driver")
def driver_page():
    return _serve_page("driver.html", "driver app")


@app.route("/app")
def customer_app_page():
    return _serve_page("customer-app.html", "customer app")


@app.route("/owner")
def owner_page():
    return _serve_page("owner.html", "owner dashboard")


@app.route("/privacy")
def privacy_page():
    return _serve_page("privacy.html", "privacy policy")


@app.route("/terms")
def terms_page():
    return _serve_page("terms.html", "terms and conditions")


@app.route("/jfk-airport-transfers")
def jfk_airport_transfers_page():
    return _serve_page("jfk-airport-transfers.html", "JFK airport transfers")


@app.route("/laguardia-airport-transfers")
def laguardia_airport_transfers_page():
    return _serve_page("laguardia-airport-transfers.html", "LaGuardia airport transfers")


@app.route("/newark-airport-transfers")
def newark_airport_transfers_page():
    return _serve_page("newark-airport-transfers.html", "Newark airport transfers")

@app.route("/teterboro-airport-transfers")
def teterboro_airport_transfers_page():
    return _serve_page("teterboro-airport-transfers.html", "Teterboro airport transfers")


@app.route("/manhattan-car-service")
def manhattan_car_service_page():
    return _serve_page("manhattan-car-service.html", "Manhattan car service")


@app.route("/brooklyn-car-service")
def brooklyn_car_service_page():
    return _serve_page("brooklyn-car-service.html", "Brooklyn car service")


@app.route("/queens-car-service")
def queens_car_service_page():
    return _serve_page("queens-car-service.html", "Queens car service")


@app.route("/long-island-car-service")
def long_island_car_service_page():
    return _serve_page("long-island-car-service.html", "Long Island car service")


@app.route("/westchester-car-service")
def westchester_car_service_page():
    return _serve_page("westchester-car-service.html", "Westchester car service")


@app.route("/new-jersey-car-service")
def new_jersey_car_service_page():
    return _serve_page("new-jersey-car-service.html", "New Jersey car service")


@app.route("/connecticut-car-service")
def connecticut_car_service_page():
    return _serve_page("connecticut-car-service.html", "Connecticut car service")


@app.route("/hamptons-car-service")
def hamptons_car_service_page():
    return _serve_page("hamptons-car-service.html", "Hamptons car service")


@app.route("/jfk-to-times-square")
def jfk_to_times_square_page():
    return _serve_page("jfk-to-times-square.html", "JFK to Times Square")


@app.route("/jfk-to-manhattan")
def jfk_to_manhattan_page():
    return _serve_page("jfk-to-manhattan.html", "JFK to Manhattan")


@app.route("/laguardia-to-manhattan")
def laguardia_to_manhattan_page():
    return _serve_page("laguardia-to-manhattan.html", "LaGuardia to Manhattan")


@app.route("/newark-to-manhattan")
def newark_to_manhattan_page():
    return _serve_page("newark-to-manhattan.html", "Newark to Manhattan")


@app.route("/valley-stream-to-jfk")
def valley_stream_to_jfk_page():
    return _serve_page("valley-stream-to-jfk.html", "Valley Stream to JFK")


@app.route("/jfk-to-brooklyn")
def jfk_to_brooklyn_page():
    return _serve_page("jfk-to-brooklyn.html", "JFK to Brooklyn")


@app.route("/hourly-chauffeur-service")
def hourly_chauffeur_service_page():
    return _serve_page("hourly-chauffeur-service.html", "hourly chauffeur service")


@app.route("/corporate-car-service")
def corporate_car_service_page():
    return _serve_page("corporate-car-service.html", "corporate car service")


@app.route("/wedding-car-service")
def wedding_car_service_page():
    return _serve_page("wedding-car-service.html", "wedding car service")


@app.route("/point-to-point-car-service")
def point_to_point_car_service_page():
    return _serve_page("point-to-point-car-service.html", "point to point car service")


@app.route("/airport-pickups")
def airport_pickups_page():
    return _serve_page("airport-pickups.html", "airport pickups")


@app.route("/your-rides-in-your-pocket")
def your_rides_in_your_pocket_page():
    return _serve_page("your-rides-in-your-pocket.html", "your rides in your pocket")


@app.route("/experience")
def experience_page():
    return _serve_page("experience.html", "experience")


@app.route("/why-ride-with-noel-chauffer")
def why_ride_with_noel_chauffer_page():
    return _serve_page("why-ride-with-noel-chauffer.html", "why ride with noel chauffer")


@app.route("/three-ways-to-ride")
def three_ways_to_ride_page():
    return _serve_page("three-ways-to-ride.html", "three ways to ride")


@app.route("/cancellation-and-waiting")
def cancellation_and_waiting_page():
    return _serve_page("cancellation-and-waiting.html", "cancellation and waiting")


@app.route("/frequently-asked-questions")
def frequently_asked_questions_page():
    return _serve_page("frequently-asked-questions.html", "frequently asked questions")


@app.route("/our-company")
def our_company_page():
    return _serve_page("our-company.html", "our company")


@app.route("/contacts")
def contacts_page():
    return _serve_page("contacts.html", "contacts")


@app.route("/your-ride-history")
def your_ride_history_page():
    return _serve_page("your-ride-history.html", "your ride history")


@app.route("/guides")
def guides_page():
    return _serve_page("guides.html", "guides hub")


@app.route("/guides/jfk-vs-laguardia-vs-newark")
def guide_jfk_vs_laguardia_vs_newark_page():
    return _serve_page("guides/jfk-vs-laguardia-vs-newark.html", "JFK vs LaGuardia vs Newark guide")


@app.route("/guides/black-car-vs-uber-black")
def guide_black_car_vs_uber_black_page():
    return _serve_page("guides/black-car-vs-uber-black.html", "black car vs Uber Black guide")


@app.route("/guides/jfk-terminal-pickup-guide")
def guide_jfk_terminal_pickup_page():
    return _serve_page("guides/jfk-terminal-pickup-guide.html", "JFK terminal pickup guide")


@app.route("/guides/how-much-is-a-black-car-in-nyc")
def guide_how_much_is_a_black_car_page():
    return _serve_page("guides/how-much-is-a-black-car-in-nyc.html", "how much is a black car in NYC guide")


# ------------------------------------------------------- place search ------

@app.route("/api/places/search", methods=["GET"])
def place_search():
    """USA-only address suggestions for the booking form (no API key).

    Always 200: an empty query, bad input, or an upstream failure all
    return an empty results list, so the form keeps working as plain
    text. Results carry address text + coordinates only: no fare,
    miles, or any pricing data. Optional lat/lon bias the ranking
    toward the customer's location (owner 2026-11-22: nearest-first,
    other states below); bad or missing coords fall back to the New
    York City default inside geo.search_places.
    """
    try:
        q = (request.args.get("q") or "").strip()[:200]
        try:
            limit = int(request.args.get("limit", "5"))
        except (TypeError, ValueError):
            limit = 5

        def _coord(name):
            raw = request.args.get(name)
            if raw is None:
                return None
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None

        lat = _coord("lat")
        lon = _coord("lon")
        results = geo_module.search_places(q, limit, lat, lon) if q else []
        return jsonify({"results": results})
    except Exception as exc:  # autocomplete must never break the page
        log.warning("place search endpoint failed: %s", exc)
        return jsonify({"results": []})


# ------------------------------------------------------- fare preview -----
# Blacklane-style fare preview (owner tool, 2026-11-20): compare the
# live legacy fare with the Blacklane-style fare for a route, without
# creating a booking. GET /api/fare-preview?pickup=...&dropoff=...
# [&class=sedan|suv|first]. The legacy total is fare + map toll; the
# Blacklane-style total is base fare + Blacklane fees (no map toll in
# the customer total — see blacklane_pricing.py). First Class driver
# pay is the flat slab (owner decision 2026-11-20 ~06:25 EST) and the
# qualifying models are Blacklane's four plus eight owner-added
# flagships (owner decisions 2026-11-20 ~03:00 EST and 2026-11-21;
# see car_models.FIRST_CLASS_MODELS).
# An address that cannot be resolved is a 400 — no distance is ever
# invented, same rule as booking creation. Read-only: nothing is
# stored, and the bookings pause does not apply.
@app.route("/api/fare-preview", methods=["GET"])
def fare_preview():
    pickup = (request.args.get("pickup") or "").strip()
    dropoff = (request.args.get("dropoff") or "").strip()
    if not pickup or not dropoff:
        return err("pickup and dropoff are required.")
    vehicle_class = (request.args.get("class") or "").strip().lower() or None
    if vehicle_class is not None and vehicle_class not in ("sedan", "suv", "first"):
        return err("class must be sedan, suv or first.")
    miles, pickup_coords, dropoff_coords = geo_module.distance_miles(pickup, dropoff)
    snapshot_fallback = False
    snap_pickup_details = None
    snap_dropoff_details = None
    if miles is None:
        # Live geocoding failed — on Render, Nominatim answers
        # empty for the shared egress IPs, so typed addresses
        # resolve to nothing. Fall back to the committed places
        # snapshot for the most-typed places (airports, terminals,
        # Times Square, ...): it holds real Nominatim coordinates,
        # so no distance is invented; a place outside the snapshot
        # still returns the 400 below.
        snap_pickup_coords, snap_pickup_details = geo_module.snapshot_coords(pickup)
        snap_dropoff_coords, snap_dropoff_details = geo_module.snapshot_coords(dropoff)
        if snap_pickup_coords is None or snap_dropoff_coords is None:
            return err("We couldn't find one of the addresses you entered. "
                       "Please pick the pickup and drop-off from the address "
                       "suggestions and try again.")
        miles = geo_module.route_miles(
            snap_pickup_coords[0], snap_pickup_coords[1],
            snap_dropoff_coords[0], snap_dropoff_coords[1])
        pickup_coords, dropoff_coords = snap_pickup_coords, snap_dropoff_coords
        snapshot_fallback = True
    geometry = None
    if pickup_coords and dropoff_coords:
        geometry = geo_module.route_geometry(
            pickup_coords[0], pickup_coords[1],
            dropoff_coords[0], dropoff_coords[1])
    toll = estimate_upfront_toll(
        geo_module.geocode_state(pickup),
        geo_module.geocode_state(dropoff),
        pickup,
        dropoff,
        geometry,
    )
    pickup_details = geo_module.geocode_address(pickup) or snap_pickup_details
    dropoff_details = geo_module.geocode_address(dropoff) or snap_dropoff_details
    miles_dec = Decimal(str(miles))

    def _legacy_view(cls):
        result = compute_one_way(miles_dec, toll=toll, vehicle_class=cls)
        return {
            "total": num(result["total"]),
            "fare": num(result["fare"]),
            "toll": num(result["toll"]),
            "driver_earnings": num(result["driver_earnings"]),
            "profit": num(result["profit"]),
            "vehicle_class": cls,
            "vehicle_class_label": class_label(cls),
        }

    def _blacklane_view(cls):
        result = compute_blacklane_one_way(
            miles_dec, cls, pickup, dropoff,
            pickup_details=pickup_details, dropoff_details=dropoff_details,
            toll=toll)
        fees = result["fees"]
        return {
            "total": num(result["total"]),
            "base": num(result["base"]),
            "fees": {k: num(v) for k, v in fees.items()},
            "toll": num(result["toll"]),
            "driver_earnings": num(result["driver_earnings"]),
            "profit": num(result["profit"]),
            "vehicle_class": cls,
            "vehicle_class_label": blacklane_class_label(cls),
            "first_class_driver_pay_tbd": result["first_class_driver_pay_tbd"],
            "tax_rate_estimated": result["tax_rate_estimated"],
            "meet_and_greet_unknown": result["meet_and_greet_unknown"],
        }

    classes = [vehicle_class] if vehicle_class else ["sedan", "suv", "first"]
    try:
        legacy = {cls: _legacy_view(cls) for cls in classes if cls != "first"}
    except ValueError as exc:
        # No driver pay slab above 400 miles (owner decision
        # 2026-11-20): refuse the preview instead of showing an
        # invented driver figure. (class=first previews skip the
        # legacy view, so they still work past 400 miles.)
        return err(str(exc))
    blacklane = {cls: _blacklane_view(cls) for cls in classes}
    return jsonify({
        "pickup": pickup,
        "dropoff": dropoff,
        "miles": num(miles_dec),
        "toll": num(toll),
        "pricing_mode": pricing_mode(),
        "snapshot_fallback": snapshot_fallback,
        "legacy": legacy,
        "blacklane": blacklane,
        "first_class_driver_pay": "Flat slab by distance + toll",
    })


# ------------------------------------------------------- customer booking ---

def _booking_create_view(booking, referral_code=None):
    """The booking shape returned on create and on class selection:
    single total (+ class totals and per-class fare breakdowns for
    the options page on one-way rides), never miles, driver pay or
    rates."""
    view = {
        "id": booking.id,
        "status": booking.status,
        "total": num(booking.fare_total),
        "pickup": booking.pickup,
        "dropoff": booking.dropoff,
        "date": booking.date,
        "time": booking.time,
        "ride_type": booking.ride_type,
        "is_return": bool(getattr(booking, "is_return", False)),
        "hours": num(booking.hours),
        "vehicle_class": booking_vehicle_class(booking),
        "vehicle_class_label": class_label(booking_vehicle_class(booking)),
        **flight_info(booking.flight_number, booking.pickup, booking.dropoff),
    }
    if booking.ride_type == "one_way":
        if pricing_mode() == "blacklane":
            # Blacklane mode: three class totals (Business, Business
            # SUV, First Class) + the per-class fare breakdown shown
            # on the options page (Blacklane-style, owner decision
            # 2026-11-20): base fare + fees + tax; no miles, no
            # driver pay, no profit — the customer never sees those.
            # First Class IS bookable now — the qualifying models
            # are decided (Blacklane's four plus eight owner-added
            # flagships; owner decisions 2026-11-20 ~03:00 EST and
            # 2026-11-21); driver pay is the flat slab.
            pickup_details = geo_module.geocode_address(booking.pickup)
            dropoff_details = geo_module.geocode_address(booking.dropoff)
            results = {
                cls: compute_blacklane_one_way(
                    booking.miles or Decimal("0"), cls, booking.pickup, booking.dropoff,
                    pickup_details=pickup_details, dropoff_details=dropoff_details,
                    toll=booking.toll or Decimal("0"),
                    referral=booking_referral_discount_applies(booking))
                for cls in ("sedan", "suv", "first")
            }
            view["class_totals"] = {k: num(v["total"]) for k, v in results.items()}
            view["class_breakdowns"] = {
                k: {
                    "base": num(v["base"]),
                    "airport_access": num(v["fees"]["airport_access"]),
                    "ny_congestion": num(v["fees"]["ny_congestion"]),
                    "mta_congestion": num(v["fees"]["mta_congestion"]),
                    "sales_tax": num(v["fees"]["sales_tax"]),
                    "black_car_fee": num(v["fees"]["black_car_fee"]),
                    "toll": num(v["toll"]),
                    "referral_discount": num(v["referral_discount"]),
                    "total": num(v["total"]),
                }
                for k, v in results.items()
            }
            view["first_class_bookable"] = True
        else:
            totals = compute_class_totals(
                booking.miles or Decimal("0"), toll=booking.toll or Decimal("0"),
                referral=booking_referral_discount_applies(booking))
            view["class_totals"] = {k: num(v) for k, v in totals.items()}
    elif booking.ride_type == "hourly":
        # Hourly rides get a breakdown too (owner decision
        # 2026-11-21 ~18:56 EST: every ride, one-way and hourly).
        # The hourly rate is all-in — taxes and tolls are inside
        # the per-hour rate — so the base fare is the full
        # hours x rate total and the fee lines are $0.00.
        _hourly = {}
        for _cls in ("sedan", "suv", "first"):
            _h = compute_hourly(booking.hours or Decimal("0"), _cls)
            _hourly[_cls] = {
                "base": num(_h["total"]),
                "airport_access": num(0),
                "ny_congestion": num(0),
                "mta_congestion": num(0),
                "sales_tax": num(0),
                "black_car_fee": num(0),
                "toll": num(0),
                "referral_discount": num(0),
                "total": num(_h["total"]),
            }
        view["class_breakdowns"] = _hourly
    # 5% first-ride referral discount granted on this booking
    # ($0.00 when a code was used but no discount applied; None on
    # hourly rides and rows created before the discount existed).
    view["referral_discount"] = num(getattr(booking, "referral_discount", None))
    if referral_code is not None:
        view["referral_code"] = referral_code
    return view


def _payload_coords(data, prefix):
    """(lat, lng) from a booking payload, or None.

    The booking form sends the picked suggestion's coordinates when
    the customer picked one; typed text sends none. Values must be
    finite numbers in range — anything else is ignored and the
    address text is geocoded instead. (The range check alone rejects
    NaN and infinities: both fail every comparison.)
    """
    try:
        lat = float(data.get(prefix + "_lat"))
        lng = float(data.get(prefix + "_lng"))
    except (TypeError, ValueError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return None
    return (lat, lng)


# Bookings LIVE (owner decision 2026-11-20: Blacklane prices + slab
# driver pay live — "Live kar do", "Driver aur customer dono live
# kar do"). New bookings are accepted. Setting BOOKINGS_PAUSED=true
# in the environment (or flipping app.BOOKINGS_PAUSED in-process, as
# the tests do) pauses them again, so no booking is stored and no
# charge can happen. Internal rates in pricing.py are untouched by
# the pause.
BOOKINGS_PAUSED = os.environ.get("BOOKINGS_PAUSED", "false").strip().lower() not in ("false", "0", "no", "")
BOOKINGS_PAUSED_MESSAGE = "Bookings are paused while we update our prices. Please check back soon."


def bookings_paused():
    """True while new bookings are paused. Live by default since the owner flipped prices live on 2026-11-20; set BOOKINGS_PAUSED=true to pause again."""
    return BOOKINGS_PAUSED


def booking_received_text(booking):
    """The "booking received" message: sent at creation when contact
    is known, or from the contact step when it was entered later
    (one-way rides, Blacklane-style)."""
    route_text = f"{booking.pickup} to {booking.dropoff}" if booking.dropoff else booking.pickup
    return (
        f"Noel Chauffer: booking received for {booking.date} at {booking.time}, {route_text}. "
        f"Your total is ${booking.fare_total}. Complete your card payment to confirm "
        "your ride — your chauffeur will be assigned right after payment, and we "
        "will message you the chauffeur's details once a driver accepts."
    )


# The receipt's first line doubles as its idempotency marker: a
# payment confirmation row is recognised by this heading.
PAYMENT_CONFIRMATION_PREFIX = "Payment received — your ride is confirmed."
# Rows sent before the step-by-step receipt (owner 2026-11-23)
# start with this instead; the idempotency check honours both so
# an old confirmation is never sent twice.
LEGACY_PAYMENT_CONFIRMATION_PREFIX = (
    "Noel Chauffer: payment received for booking #")


def receipt_number_for(payment):
    """The receipt's own number: NCL-<payment year>-<payment id,
    six digits> (e.g. NCL-2026-000035). Unique per payment, clearly
    different from the booking number, and stable — the same
    payment always yields the same number, so an idempotent resend
    keeps it. The year is the payment's own year."""
    created = getattr(payment, "created_at", None)
    year = created.year if created is not None else datetime.now(timezone.utc).year
    return f"NCL-{year}-{payment.id:06d}"


def _ensure_booking_code(booking):
    """The booking's receipt code: NC-<random 6 digits> (e.g.
    NC-482913). Final owner spec 2026-11-23: RANDOM, never
    sequential (the earlier 'start from 1000' idea is cancelled);
    one booking one code, never reused. Generated once, stored on
    the booking so the same booking always shows the same code,
    and checked unique in the database — on a collision a new
    number is drawn. The caller commits."""
    if getattr(booking, "booking_code", None):
        return booking.booking_code
    for _ in range(50):
        code = f"NC-{secrets.randbelow(900000) + 100000:06d}"
        clash = Booking.query.filter_by(booking_code=code).first()
        if clash is None:
            booking.booking_code = code
            return code
    # Unreachable in practice (50 collisions in a million-number
    # space); deterministic per booking so it still never repeats
    # a sequential id.
    booking.booking_code = (
        f"NC-{(booking.id * 2654435761) % 900000 + 100000:06d}")
    return booking.booking_code


def booking_number_for(booking):
    """The booking's display number in the receipt: its random
    NC code (e.g. NC-482913). Receipt-only — the website, apps
    and dashboard keep showing the plain booking number."""
    return _ensure_booking_code(booking)


def _format_pickup_datetime(booking):
    """'Monday, November 23, 2026 at 12:00 PM' from the booking's
    stored YYYY-MM-DD date and HH:MM time; falls back to the raw
    values when they do not parse."""
    try:
        dt = datetime.strptime(f"{booking.date} {booking.time}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return f"{booking.date} at {booking.time}"
    return (dt.strftime("%A, %B ") + str(dt.day) +
            dt.strftime(", %Y at ") + dt.strftime("%I:%M %p").lstrip("0"))


def _payment_confirmation_rows(booking, test=False, payment=None):
    """Receipt content, one row per detail, in order. Each row is a
    (label, value) pair for the detail lines, or ("", text) for the
    heading and the closing sentences. The plain-text body and the
    HTML receipt render the same rows. Only facts already on the
    booking (and its payment); nothing invented. The ride-end
    invoice email is separate and untouched."""
    rows = [("", PAYMENT_CONFIRMATION_PREFIX)]
    if payment is not None:
        rows.append(("Receipt No.", receipt_number_for(payment)))
    rows.append(("Booking", booking_number_for(booking)))
    rows.append(("Pickup", booking.pickup))
    if booking.ride_type == "hourly":
        if booking.hours is not None:
            try:
                hours_text = f"{float(booking.hours):g} hours"
            except (TypeError, ValueError):
                hours_text = f"{booking.hours} hours"
            rows.append(("Hours", hours_text))
    else:
        rows.append(("Drop-off", booking.dropoff))
    rows.append(("Date", _format_pickup_datetime(booking)))
    class_text = class_label(booking_vehicle_class(booking))
    if class_text:
        rows.append(("Class", class_text))
    rows.append(("Total paid", f"${booking.fare_total}"))
    rows.append(("", "Your chauffeur will be assigned shortly — we will message "
                    "you the chauffeur's details once a driver accepts."))
    if test:
        rows.append(("", "This was a test payment — no real charge was made."))
    return rows


def payment_confirmation_text(booking, test=False, payment=None):
    """The plain-text receipt: a clean, professional layout — the
    heading, a divider, every detail on its own line with labels
    aligned in one column, a divider, the total on its own, then
    the next-step and test-mode lines (owner 2026-11-23 — the old
    single-paragraph email was rejected, 'Aisa nahi'; the receipt
    must look like a big company's, 'ek dum professional')."""
    rows = _payment_confirmation_rows(booking, test=test, payment=payment)
    heading = rows[0][1]
    fields = [(label, value) for label, value in rows[1:] if label]
    notes = [value for label, value in rows[1:] if not label]
    width = max(len(label) + 1 for label, _ in fields)  # +1 for the colon
    divider = "-" * 40
    detail = [(label, value) for label, value in fields if label != "Total paid"]
    total = [(label, value) for label, value in fields if label == "Total paid"]
    lines = [heading, divider]
    lines += [f"{label}:".ljust(width) + " " + value for label, value in detail]
    lines.append(divider)
    lines += [f"{label}:".ljust(width) + " " + value for label, value in total]
    lines.append("")
    lines += notes
    return "\n".join(lines)


def _receipt_value_html(label, value):
    """One receipt value as HTML. The booking number's NC prefix
    is brand gold (owner 2026-11-23); everything else is dark."""
    if label == "Booking":
        prefix, _, rest = value.partition("-")
        return (f"<span style=\"color:#D4AF37;font-weight:bold;\">"
                f"{html_escape(prefix)}</span>-{html_escape(rest)}")
    return html_escape(value)


def payment_confirmation_html(booking, test=False, payment=None):
    """The HTML receipt: the same rows as the plain text, as a
    clean business receipt — Noel Chauffer letterhead, heading,
    divider, label/value table with aligned columns, the total
    set apart and bold, then the next-step and test-mode lines.
    No gradients, no images; the only gold is the brand wordmark
    and the booking number's NC prefix (owner 2026-11-23)."""
    rows = _payment_confirmation_rows(booking, test=test, payment=payment)
    heading = html_escape(rows[0][1])
    fields = [(label, value) for label, value in rows[1:] if label]
    notes = [value for label, value in rows[1:] if not label]
    detail = [(label, value) for label, value in fields if label != "Total paid"]
    total = [(label, value) for label, value in fields if label == "Total paid"]

    def _row(label, value, total_row=False):
        border = "border-top:1px solid #cccccc;" if total_row else ""
        size = "font-size:16px;" if total_row else ""
        rendered = _receipt_value_html(label, value)
        if total_row:
            rendered = f"<strong>{rendered}</strong>"
        return (
            "<tr>"
            f"<td style=\"padding:5px 16px 5px 0;font-weight:bold;"
            f"white-space:nowrap;vertical-align:top;{border}\">"
            f"{html_escape(label)}</td>"
            f"<td style=\"padding:5px 0;vertical-align:top;{border}{size}\">"
            f"{rendered}</td></tr>")

    detail_html = "".join(_row(label, value) for label, value in detail)
    total_html = "".join(_row(label, value, total_row=True)
                         for label, value in total)
    notes_html = ""
    for note in notes:
        style = "margin:12px 0 0 0;"
        if note.startswith("This was a test"):
            style += "color:#666666;"
        notes_html += f"<p style=\"{style}\">{html_escape(note)}</p>"
    return (
        "<!DOCTYPE html><html><body style=\"margin:0;padding:0;"
        "background:#ffffff;\">"
        "<div style=\"max-width:560px;margin:0 auto;padding:24px;"
        "font-family:Arial,Helvetica,sans-serif;color:#222222;"
        "font-size:15px;line-height:1.6;\">"
        "<div style=\"font-size:22px;font-weight:600;letter-spacing:0.02em;"
        "color:#111111;margin-bottom:12px;\">Noel "
        "<span style=\"color:#D4AF37;\">Chauffeur</span></div>"
        f"<h1 style=\"font-size:20px;line-height:1.4;margin:0 0 12px 0;"
        f"color:#111111;\">{heading}</h1>"
        "<hr style=\"border:none;border-top:1px solid #dddddd;"
        "margin:0 0 12px 0;\">"
        "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"width:100%;border-collapse:collapse;\">"
        f"{detail_html}{total_html}</table>{notes_html}"
        "</div></body></html>")


# The chauffeur-assigned email's heading (owner 2026-11-23): the
# customer must read every chauffeur detail on its own line.
CHAUFFEUR_ASSIGNED_HEADING = "Your chauffeur has been assigned."


def _chauffeur_assigned_rows(driver, booking):
    """Chauffeur details, one row per detail, in order. Each row is a
    (label, value) pair. The plain-text body and the HTML email render
    the same rows. Only facts already sent in the old single-paragraph
    email — chauffeur name, phone, car, plate, pickup date/time and
    pickup address — plus the drop-off address, which the owner added
    2026-11-24 ('Drop off bhi rehna na'): it goes on its own line
    after From, labelled 'To'. No total: the old email never carried
    one (owner 2026-11-23, 'line by line', every detail on its own
    line so it is easy to read). Hourly rides have no drop-off, so
    the 'To' row is omitted rather than printed blank."""
    rows = [
        ("Chauffeur", driver.name),
        ("Phone", driver.phone),
        ("Car", f"{driver.car_model} ({driver.car_colour})"),
        ("Plate", driver.plate),
        ("Pickup", f"{booking.date} at {booking.time}"),
        ("From", booking.pickup),
    ]
    if getattr(booking, "dropoff", None):
        rows.append(("To", booking.dropoff))
    return rows


def chauffeur_assigned_text(driver, booking):
    """The plain-text chauffeur email: the heading, a divider, every
    detail on its own line with labels aligned in one column — the
    same professional step-by-step layout as the payment receipt
    (owner 2026-11-23; the old single-paragraph email was hard to
    read)."""
    rows = _chauffeur_assigned_rows(driver, booking)
    width = max(len(label) + 1 for label, _ in rows)  # +1 for the colon
    divider = "-" * 40
    lines = [CHAUFFEUR_ASSIGNED_HEADING, divider]
    lines += [f"{label}:".ljust(width) + " " + value for label, value in rows]
    return "\n".join(lines)


def chauffeur_assigned_html(driver, booking):
    """The HTML chauffeur email: the same rows as the plain text, as
    a clean business message — Noel Chauffer letterhead, heading,
    divider, label/value table with aligned columns. No gradients,
    no images; the only gold is the brand wordmark (owner 2026-11-23)."""
    rows = _chauffeur_assigned_rows(driver, booking)
    detail_html = "".join(
        "<tr>"
        f"<td style=\"padding:5px 16px 5px 0;font-weight:bold;"
        f"white-space:nowrap;vertical-align:top;\">"
        f"{html_escape(label)}</td>"
        f"<td style=\"padding:5px 0;vertical-align:top;\">"
        f"{html_escape(value)}</td></tr>"
        for label, value in rows)
    return (
        "<!DOCTYPE html><html><body style=\"margin:0;padding:0;"
        "background:#ffffff;\">"
        "<div style=\"max-width:560px;margin:0 auto;padding:24px;"
        "font-family:Arial,Helvetica,sans-serif;color:#222222;"
        "font-size:15px;line-height:1.6;\">"
        "<div style=\"font-size:22px;font-weight:600;letter-spacing:0.02em;"
        "color:#111111;margin-bottom:12px;\">Noel "
        "<span style=\"color:#D4AF37;\">Chauffeur</span></div>"
        f"<h1 style=\"font-size:20px;line-height:1.4;margin:0 0 12px 0;"
        f"color:#111111;\">{html_escape(CHAUFFEUR_ASSIGNED_HEADING)}</h1>"
        "<hr style=\"border:none;border-top:1px solid #dddddd;"
        "margin:0 0 12px 0;\">"
        "<table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"width:100%;border-collapse:collapse;\">"
        f"{detail_html}</table>"
        "</div></body></html>")


def _send_payment_confirmation_email(booking, test=False):
    """Queue (and best-effort send via Resend) the one payment
    confirmation email for this booking. Idempotent: a second call
    for the same booking sends nothing, so a re-marked payment
    never double-mails the customer — and a resend keeps the same
    receipt number, because it is derived from the payment row.
    Returns the outbox row, or the existing one, or None when there
    is no email to send to."""
    if not booking.email:
        return None
    existing = (OutboxMessage.query
                .filter_by(channel="email", booking_id=booking.id)
                .filter(or_(OutboxMessage.body.startswith(
                            PAYMENT_CONFIRMATION_PREFIX),
                        OutboxMessage.body.startswith(
                            LEGACY_PAYMENT_CONFIRMATION_PREFIX)))
                .first())
    if existing is not None:
        return existing
    # The receipt number comes from the payment that just succeeded
    # (its own sequential id, not the booking number). Flush first
    # so the new row has its id and created year; the caller commits.
    db.session.flush()
    payment = _latest_payment(booking.id)
    return add_outbox(
        "email", booking.email,
        payment_confirmation_text(booking, test=test, payment=payment),
        booking.id,
        subject=(f"Noel Chauffer — payment received "
                 f"(booking {booking_number_for(booking)})"),
        html=payment_confirmation_html(booking, test=test, payment=payment))


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    if bookings_paused():
        return err(BOOKINGS_PAUSED_MESSAGE, 503)
    data = request.get_json(silent=True) or {}
    # Name, phone and email are NOT required here: on one-way rides
    # the customer enters them on the options page ("Choose your
    # experience", Blacklane-style) after picking a class, and saves
    # them with POST /api/bookings/<id>/contact before paying.
    # Hourly rides ask for contact on the booking form (the class is
    # picked on the separate class step), so they still need contact
    # up front.
    required = ["pickup", "date", "time", "ride_type"]
    for field in required:
        if not data.get(field):
            return err(f"Missing required field: {field}.")
    ride_type = data["ride_type"]
    if ride_type not in ("one_way", "hourly"):
        return err("ride_type must be one_way or hourly.")
    if ride_type == "hourly":
        for field in ("customer_name", "phone", "email"):
            if not data.get(field):
                return err(f"Missing required field: {field}.")
    try:
        datetime.strptime(data["date"], "%Y-%m-%d")
        datetime.strptime(data["time"], "%H:%M")
    except ValueError:
        return err("date must be YYYY-MM-DD and time must be HH:MM.")
    # Past pickups cannot be booked (owner decision 2026-11-20):
    # an old date — or today at a time already gone — is rejected.
    # Compared in America/New_York, the service area.
    pickup_dt = _pickup_dt(data["date"], data["time"])
    if pickup_dt is not None:
        from zoneinfo import ZoneInfo
        now_ny = datetime.now(ZoneInfo("America/New_York")).replace(second=0, microsecond=0)
        if pickup_dt < now_ny:
            return err("Pickup date and time are in the past. Please choose a future date and time.")

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

    # Return-trip flag (owner decision 2026-11-20): only a
    # one-way booking made through "Book your return trip"
    # carries it, so it displays as "Return trip" instead of
    # "One way". Hourly rides can never be return trips.
    is_return = bool(data.get("is_return")) and ride_type == "one_way"

    booking = Booking(
        customer_name=(data.get("customer_name") or "").strip(),
        phone=(data.get("phone") or "").strip(),
        email=(data.get("email") or "").strip(),
        pickup=data["pickup"],
        dropoff=data.get("dropoff") or "",
        date=data["date"],
        time=data["time"],
        passengers=int(data.get("passengers") or 1),
        ride_type=ride_type,
        is_return=is_return,
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
        if hours_dec < HOURLY_MIN_HOURS or hours_dec > HOURLY_MAX_HOURS:
            return err("Hourly bookings need 2 to 24 hours.")
        # Blacklane-style hourly (owner decision 2026-11-20): the
        # customer picks a vehicle class, like Blacklane.
        vehicle_class = (data.get("vehicle_class") or "").strip().lower()
        if vehicle_class not in ("sedan", "suv", "first"):
            return err("vehicle_class must be sedan, suv or first.")
        booking.hours = hours_dec
        booking.miles = None
        booking.vehicle_class = vehicle_class
        result = compute_hourly(hours_dec, vehicle_class)
    else:
        if not booking.dropoff:
            return err("dropoff is required for one-way rides.")
        # Coordinates from a picked suggestion are priced as-is (never
        # re-geocoded); a side without them is resolved from its text.
        # Coordinates are passed only when present, so the plain
        # two-argument call keeps working for typed addresses.
        geo_kwargs = {}
        payload_pickup = _payload_coords(data, "pickup")
        if payload_pickup is not None:
            geo_kwargs["pickup_coords"] = payload_pickup
        payload_dropoff = _payload_coords(data, "dropoff")
        if payload_dropoff is not None:
            geo_kwargs["dropoff_coords"] = payload_dropoff
        miles, pickup_coords, dropoff_coords = geo_module.distance_miles(
            booking.pickup, booking.dropoff, **geo_kwargs)
        if miles is None:
            # No invented distance: an address that cannot be resolved
            # to coordinates must not be priced. Nothing is stored;
            # the customer picks the address from the suggestions and
            # tries again.
            return err("We couldn't find one of the addresses you entered. "
                       "Please pick the pickup and drop-off from the address "
                       "suggestions and try again.")
        booking.miles = Decimal(str(miles))
        if miles_1dp(booking.miles) > DRIVER_PAY_MAX_MILES:
            # No driver pay slab exists above 400 miles (owner
            # decision 2026-11-20): refuse instead of pricing with
            # an invented rate. Nothing is stored.
            return err("Rides over 400 miles cannot be booked yet — "
                       "no driver pay rate exists for that distance.")
        if pickup_coords:
            booking.pickup_lat, booking.pickup_lng = pickup_coords
        if dropoff_coords:
            booking.dropoff_lat, booking.dropoff_lng = dropoff_coords
        # Up-front toll estimate from the map (owner decision
        # 2026-11-16, extended 2026-11-17): every tolled crossing
        # the route passes through is charged at the verified
        # E-ZPass rate, plus the $16.79 Port Authority return
        # crossing on NY -> NJ trips, so the driver sees the
        # separate Toll line BEFORE accepting. This stored toll is
        # the single source for the fare total AND the options-page
        # class totals (both read booking.toll), so quote and
        # charge always agree. The geocoder state cache is warm for
        # each side resolved from text (distance_miles above geocoded
        # it first); a side priced from picked-suggestion coordinates
        # skips geocoding, so its state resolves from the address
        # display text instead — and on a geocoding failure the helper
        # likewise falls back to the display text. The route cache is
        # warm too: distance_miles fetched the route first, so
        # route_geometry is cache-only
        # and never fetches upstream; when it returns None (OSRM
        # failure) the helper applies the compulsory NY<->NJ
        # fallback.
        geometry = None
        if pickup_coords and dropoff_coords:
            geometry = geo_module.route_geometry(
                pickup_coords[0], pickup_coords[1],
                dropoff_coords[0], dropoff_coords[1])
        booking.toll = estimate_upfront_toll(
            geo_module.geocode_state(booking.pickup),
            geo_module.geocode_state(booking.dropoff),
            booking.pickup,
            booking.dropoff,
            geometry,
        )
        # Default class is sedan (Business Class, pre-selected on the
        # options page); the customer may switch to SUV before paying.
        # 5% first-ride referral discount (owner decision 2026-11-18):
        # a valid code earns the discount ONLY on this phone's first
        # booking — a phone with any prior booking gets no discount,
        # and the referrer gets nothing. The discount is decided
        # here, at creation, and stored on the booking; class changes
        # and toll changes recompute it at 5% of the new total.
        booking.vehicle_class = "sedan"
        referral_eligible = referral_valid and is_first_booking_by_phone(booking.phone)
        if pricing_mode() == "blacklane":
            # Blacklane mode (NOEL_PRICING=blacklane): the customer
            # total is base fare + Blacklane fees (no map toll in the
            # total — see blacklane_pricing.py); driver pay stays
            # miles x driver rate + map toll.
            result = compute_blacklane_one_way(
                booking.miles, "sedan", booking.pickup, booking.dropoff,
                pickup_details=geo_module.geocode_address(booking.pickup),
                dropoff_details=geo_module.geocode_address(booking.dropoff),
                toll=booking.toll, referral=referral_eligible)
        else:
            result = compute_one_way(booking.miles, toll=booking.toll,
                                     vehicle_class="sedan", referral=referral_eligible)

    booking.fare_total = result["total"]
    booking.driver_earnings = result["driver_earnings"]
    booking.gratuity = result["gratuity"]
    booking.booking_fee = result["booking_fee"]
    booking.fare = result["fare"]
    booking.tax = result["tax"]
    # 5% first-ride referral discount granted on this booking
    # (one-way only; hourly rides never get one). None on hourly
    # rides, $0.00 when a code was used but no discount applied.
    booking.referral_discount = result.get("referral_discount")

    db.session.add(booking)
    db.session.flush()  # booking.id needed for the referral code + outbox

    if referral_row is not None:
        referral_row.used_count += 1

    new_code = generate_referral_code()
    db.session.add(ReferralCode(code=new_code, issued_booking_id=booking.id))

    route_text = f"{booking.pickup} to {booking.dropoff}" if booking.dropoff else booking.pickup
    # The "booking received" message can only go out once an address
    # exists: one-way rides created without contact get it from the
    # contact step instead.
    if booking.phone or booking.email:
        outbox_to_customer(booking, booking_received_text(booking))
    add_event(booking.id, "booking_received",
              f"New booking #{booking.id}: {route_text} on {booking.date} at {booking.time} "
              f"({booking.customer_name}, {booking.phone}).")
    db.session.commit()

    return jsonify({"booking": _booking_create_view(booking, referral_code=new_code)}), 201


@app.route("/api/bookings/<int:booking_id>/vehicle-class", methods=["POST"])
def select_vehicle_class(booking_id):
    """The customer picks a class on the options page ("Choose your
    experience") before paying — and, for hourly rides, on the booking
    form itself. Only while the booking is still awaiting payment:
    after payment the booking is already with drivers and its class
    is fixed."""
    if bookings_paused():
        return err(BOOKINGS_PAUSED_MESSAGE, 503)
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.status != "awaiting_payment":
        return err("The vehicle class can only be changed before payment.", 409)
    data = request.get_json(silent=True) or {}
    vehicle_class = data.get("vehicle_class")
    if vehicle_class == "first" and booking.ride_type == "one_way":
        # First Class is OPEN (owner decision 2026-11-20 ~03:00 EST):
        # Blacklane's four models plus eight owner-added flagships
        # (2026-11-21; see car_models.FIRST_CLASS_MODELS), driver pay
        # is the flat slab. But it exists ONLY in Blacklane mode — the
        # legacy engine has no First Class rate at all, so in legacy
        # mode there is nothing to price it with; refuse there.
        if pricing_mode() != "blacklane":
            return err("First Class needs the new Blacklane rates, "
                       "which are not live yet. Please choose Business "
                       "Class or Business SUV.", 400)
    if vehicle_class not in ("sedan", "suv", "first"):
        return err("vehicle_class must be sedan, suv or first.")
    booking.vehicle_class = vehicle_class
    try:
        recompute_booking_fare(booking)
    except ValueError as exc:
        # A ride booked before the slab change, over 400 miles, has
        # no slab to reprice with (owner decision 2026-11-20).
        return err(str(exc))
    add_event(booking.id, "class_selected",
              f"Customer selected {class_label(vehicle_class)} for booking "
              f"#{booking.id} (total ${booking.fare_total}).")
    db.session.commit()
    return jsonify({"booking": _booking_create_view(booking)})


@app.route("/api/bookings/<int:booking_id>/contact", methods=["POST"])
def save_booking_contact(booking_id):
    """The customer enters name, phone and email on the options page
    ("Choose your experience", Blacklane-style) — after the booking
    is created, before paying. Only while the booking is still
    awaiting payment. Saving the phone also decides the 5% first-ride
    referral discount, which creation could not decide because the
    phone was not known yet: a valid code earns it ONLY on this
    phone's first booking, and the booking itself is excluded from
    that check."""
    if bookings_paused():
        return err(BOOKINGS_PAUSED_MESSAGE, 503)
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.status != "awaiting_payment":
        return err("Contact details can only be added before payment.", 409)
    data = request.get_json(silent=True) or {}
    for field in ("customer_name", "phone", "email"):
        if not (data.get(field) or "").strip():
            return err(f"Missing required field: {field}.")
    if "@" not in data["email"]:
        return err("Please enter a valid email address.")
    # Compulsory customer sign-in (owner decision 2026-11-22):
    # contact can only be saved once the customer has signed in
    # with THIS email, and the phone number (compulsory too) is
    # already required above. The gate compares against the
    # SUBMITTED email here — the booking itself has no email yet
    # at this step.
    signed_in = _customer_signin_email()
    if not signed_in:
        return err("Please sign in with your email first.", 401)
    if signed_in != _normalize_customer_email(data["email"]):
        return err("Please sign in with the same email as this booking.", 401)
    had_contact = bool(booking.phone or booking.email)
    booking.customer_name = data["customer_name"].strip()
    booking.phone = data["phone"].strip()
    booking.email = data["email"].strip()
    if booking.ride_type == "one_way":
        referral_eligible = bool(booking.referral_code_used) and is_first_booking_by_phone(
            booking.phone, exclude_booking_id=booking.id)
        recompute_booking_fare(booking, referral=referral_eligible)
    add_event(booking.id, "contact_saved",
              f"Customer contact saved for booking #{booking.id} "
              f"({booking.customer_name}, {booking.phone}).")
    if not had_contact:
        # The "booking received" message could not go out at creation
        # (no address yet); it goes out now that we have one.
        outbox_to_customer(booking, booking_received_text(booking))
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
    # Amounts are hidden while prices are being updated (owner
    # decision 2026-11-20): no total, no class totals, no invoice
    # figures are ever sent to the customer.
    invoice = None
    view = {
        "id": booking.id,
        "status": booking.status,
        "pickup": booking.pickup,
        "dropoff": booking.dropoff,
        "date": booking.date,
        "time": booking.time,
        "ride_type": booking.ride_type,
        "is_return": bool(getattr(booking, "is_return", False)),
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
        "tracking": {
            "visible": tracking_visible,
            "lat": booking.driver_lat if tracking_visible else None,
            "lng": booking.driver_lng if tracking_visible else None,
        },
        "invoice": invoice,
        "referral_code": referral.code if referral else None,
        "chat_language": booking_customer_chat_language(booking),
    }
    return jsonify({"booking": view})


# ------------------------------------------------------- live Stripe -----
# Live Stripe payments (owner decision 2026-11-20, "Uber jaisa bana
# do"). Authorize the estimated fare at booking (a hold), capture
# the final fare automatically at ride end from the saved card.
# Free cancel (>1h before pickup) releases the hold with NO charge;
# late cancel / no-show captures the full fare. Bookings whose hold
# fails never reach drivers. When NO Stripe keys are configured the
# /pay endpoint keeps the pre-existing test-mode fake authorization
# (no real charge) so bookings keep working — live activation is
# currently BLOCKED because the merchant Stripe account is disabled
# (see the build report). With keys configured there is no fake
# fallback: every payment call goes to Stripe or refuses.

def _payment_view(payment):
    return {
        "id": payment.id,
        "amount": num(payment.amount),
        "status": payment.status,
        "test": bool(payment.test),
        "last4": payment.last4,
        "brand": payment.brand,
        "stripe_payment_intent_id": payment.stripe_payment_intent_id,
        "captured_amount": num(payment.captured_amount),
    }


def _saved_card_view(card):
    return {
        "id": card.id,
        "brand": card.brand,
        "last4": card.last4,
        "exp_month": card.exp_month,
        "exp_year": card.exp_year,
    }


def _latest_payment(booking_id):
    return (Payment.query.filter_by(booking_id=booking_id)
            .order_by(Payment.id.desc()).first())


def _stripe_customer_for_phone(phone, name, email):
    """The Stripe Customer id for a phone-keyed customer: reuse the
    one on their newest saved card, else create one. The card itself
    always lives with Stripe — Noel keeps only brand / last 4 /
    expiry."""
    existing = (CustomerCard.query.filter_by(phone=str(phone))
                .order_by(CustomerCard.id.desc()).first())
    if existing and existing.stripe_customer_id:
        return existing.stripe_customer_id
    return stripe_payments.create_customer(email, name, phone)["id"]


def _authorize_booking(booking, intent, customer_id, payment_method_id, save_card):
    """Record an authorized hold (PaymentIntent status
    requires_capture) as an "authorized" Payment row, optionally
    save the card, and send the booking to drivers. Returns the
    response payload. The caller commits."""
    card = intent.get("card") or {}
    if not card.get("last4") and payment_method_id:
        try:
            card = stripe_payments.get_payment_method(payment_method_id)
        except stripe_payments.StripePaymentsError:
            card = {}
    payment = Payment(
        booking_id=booking.id,
        amount=booking.fare_total,
        status="authorized",
        test=False,
        last4=card.get("last4"),
        brand=card.get("brand"),
        stripe_payment_intent_id=intent["id"],
        stripe_customer_id=customer_id,
        stripe_payment_method_id=payment_method_id,
        stripe_test_id="",
    )
    db.session.add(payment)
    saved_card = None
    if save_card and payment_method_id and customer_id:
        # setup_future_usage="off_session" on the PaymentIntent
        # already attaches the card to the customer at Stripe; the
        # row here only remembers brand / last 4 / expiry. A card
        # saved on an earlier ride is reused, never re-inserted
        # (phone + payment method is unique).
        saved_card = CustomerCard.query.filter_by(
            phone=str(booking.phone),
            stripe_payment_method_id=payment_method_id).first()
        if saved_card is None:
            saved_card = CustomerCard(
                phone=str(booking.phone),
                stripe_customer_id=customer_id,
                stripe_payment_method_id=payment_method_id,
                brand=card.get("brand"), last4=card.get("last4"),
                exp_month=card.get("exp_month"), exp_year=card.get("exp_year"))
            db.session.add(saved_card)
    booking.status = "offered"
    add_event(booking.id, "payment_received",
              f"Payment of ${booking.fare_total} authorized for booking #{booking.id} "
              f"(card ending {card.get('last4')}). Booking sent to drivers.")
    _send_payment_confirmation_email(booking)
    return {"payment": _payment_view(payment),
            "booking": {"status": booking.status},
            "saved_card": _saved_card_view(saved_card) if saved_card else None}


def _settle_booking_payment(booking, final_total):
    """Capture the authorized hold: at ride end `final_total` is the
    invoice total (fare + waiting); for a no-show / late cancel it
    is the full authorized fare. When the final fare is HIGHER than
    the hold, the hold is captured in full and the difference is
    charged off-session to the saved card. Returns (ok, note).
    Never raises: a Stripe failure marks the payment
    capture_shortfall for the owner to follow up — the ride itself
    is never blocked by a payment error."""
    payment = _latest_payment(booking.id)
    if payment is None or payment.status in ("captured", "refunded"):
        return True, "no authorized payment"
    if payment.test or payment.status == "succeeded":
        # Legacy test-mode rows: no real money ever moved.
        return True, "test payment"
    if not payment.stripe_payment_intent_id:
        return True, "no payment intent"
    if not stripe_payments.stripe_configured():
        payment.status = "capture_shortfall"
        add_event(booking.id, "payment_capture_failed",
                  f"Booking #{booking.id}: ${final_total} could not be captured — "
                  "card payments are not set up. Owner follow-up needed.")
        return False, "Card payments are not set up yet."
    final_cents = stripe_payments.to_cents(final_total)
    authorized_cents = stripe_payments.to_cents(payment.amount)
    try:
        if final_cents <= authorized_cents:
            captured = stripe_payments.capture_payment_intent(
                payment.stripe_payment_intent_id,
                amount_cents=(final_cents if final_cents != authorized_cents else None))
            payment.status = "captured"
            payment.captured_amount = stripe_payments.to_dollars(
                captured["amount_captured_cents"])
        else:
            captured = stripe_payments.capture_payment_intent(
                payment.stripe_payment_intent_id)
            payment.captured_amount = stripe_payments.to_dollars(
                captured["amount_captured_cents"])
            extra_cents = final_cents - authorized_cents
            try:
                stripe_payments.create_off_session_payment_intent(
                    extra_cents, payment.stripe_customer_id,
                    payment.stripe_payment_method_id, booking.id)
            except stripe_payments.StripePaymentsError as exc:
                payment.status = "capture_shortfall"
                add_event(booking.id, "payment_capture_shortfall",
                          f"Booking #{booking.id}: final fare ${final_total} was higher "
                          f"than the ${payment.amount} hold; the extra "
                          f"${stripe_payments.to_dollars(extra_cents)} could not be "
                          f"charged ({exc.user_message}). Owner follow-up needed.")
                return False, exc.user_message
            payment.status = "captured"
            payment.captured_amount = money(final_total)
        add_event(booking.id, "payment_captured",
                  f"Booking #{booking.id}: ${payment.captured_amount} captured "
                  f"(final fare ${final_total}).")
        return True, "captured"
    except stripe_payments.StripePaymentsError as exc:
        payment.status = "capture_shortfall"
        add_event(booking.id, "payment_capture_failed",
                  f"Booking #{booking.id}: ${final_total} could not be captured "
                  f"({exc.user_message}). Owner follow-up needed.")
        return False, exc.user_message


def _release_booking_payment(booking):
    """Free cancellation (>1h before pickup): release the hold, or
    refund a captured charge. Returns (refunded, pending): pending
    means the Stripe cancel/refund failed and the payment is marked
    refund_pending for the owner to retry. Never raises."""
    payment = _latest_payment(booking.id)
    if payment is None or payment.status == "refunded":
        return False, False
    if payment.test or payment.status == "succeeded":
        payment.status = "refunded"
        return True, False
    if payment.status not in ("authorized", "captured"):
        return False, False
    if not stripe_payments.stripe_configured():
        payment.status = "refund_pending"
        return False, True
    try:
        if payment.status == "authorized":
            stripe_payments.cancel_payment_intent(payment.stripe_payment_intent_id)
        else:
            stripe_payments.refund_payment_intent(payment.stripe_payment_intent_id)
    except stripe_payments.StripePaymentsError:
        payment.status = "refund_pending"
        return False, True
    payment.status = "refunded"
    return True, False


# --------------------------------------- customer sign-in (email-only) ------
# Owner decision 2026-11-22 (voice call): after "View options" /
# "Choose your experience", before the booking can proceed to
# payment, the customer MUST sign in. Sign-in is EMAIL ONLY — one
# email field + Continue, like Blacklane's first step; NO password,
# NO Google/Apple/Facebook buttons. NO CODES (owner correction
# 2026-11-22, "Nahi bhai, no codes"): the customer types their
# email, taps Continue, and is signed in — no code is emailed, no
# code is typed back, nothing is verified. Phone number is
# compulsory too (owner decision 2026-11-22): it is collected with
# the email at the sign-in step, and the booking cannot proceed
# without it. A sign-in lives in the Flask session, so the customer
# stays signed in for later bookings on the same browser.


@app.route("/api/customers/me", methods=["GET"])
def customer_me():
    """Who the browser is signed in as (for pre-filling the options
    page and skipping the code step on later bookings). Never
    errors: an unsigned browser just reports signed_in False."""
    email = _customer_signin_email()
    phone = _customer_signin_phone()
    return jsonify({"signed_in": bool(email),
                    "email": email, "phone": phone})


@app.route("/api/customers/signout", methods=["POST"])
def customer_signout():
    session.pop("customer_email", None)
    session.pop("customer_phone", None)
    return jsonify({"signed_in": False})


@app.route("/api/customers/signin", methods=["POST"])
def customer_signin():
    """Sign in with email + phone only (owner decision 2026-11-22,
    corrected same day: NO CODES). The customer types their email
    (and phone number, compulsory) and taps Continue — that is the
    whole sign-in. No code is emailed, no code is typed back, and
    nothing is stored except the Flask session.
    PERMANENT LOGIN (owner decision 2026-11-23): the session is
    marked permanent, so the browser keeps the customer signed in
    for ~365 days across visits, until they sign out — the customer
    is never asked to sign in again on that browser."""
    data = request.get_json(silent=True) or {}
    email = _normalize_customer_email(data.get("email"))
    phone = (data.get("phone") or "").strip()
    if not email or "@" not in email or len(email) > 200:
        return err("Please enter a valid email address.")
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not phone or len(digits) < 7:
        return err("Please enter a valid phone number.")
    session.permanent = True
    session["customer_email"] = email
    session["customer_phone"] = phone
    return jsonify({"signed_in": True, "email": email, "phone": phone})


@app.route("/api/stripe/publishable-key", methods=["GET"])
def stripe_publishable_key():
    """The Stripe.js publishable key for the customer frontends.
    The secret key is never exposed. configured=false means no keys
    are in Render yet — the frontend uses the test-mode card form
    and the server fakes the authorization (no real charge, exactly
    as before this build). Live payments stay blocked until the owner
    adds keys AND fixes the disabled merchant Stripe account (see
    the build report)."""
    configured = stripe_payments.stripe_configured()
    return jsonify({"configured": configured,
                    "test_mode": not configured,
                    "publishable_key": stripe_payments.get_publishable_key()})


@app.route("/api/bookings/<int:booking_id>/pay", methods=["POST"])
def pay_booking(booking_id):
    """Card payment BEFORE dispatch: the customer picks a class on the
    options page, sees the single total for that class, and pays; only
    then is the booking sent to drivers (status awaiting_payment ->
    offered). Live Stripe (owner decision 2026-11-20): the card is
    collected by Stripe.js in the browser, which hands us a
    PaymentMethod id — raw card numbers are rejected here. The call
    places a HOLD for the estimated fare (manual capture); the final
    fare is captured automatically at ride end.
    PAUSED (owner decision 2026-11-20): no payment is taken while
    prices are being updated."""
    if bookings_paused():
        return err(BOOKINGS_PAUSED_MESSAGE, 503)
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.status != "awaiting_payment":
        return err("Payment is taken before the booking is sent to drivers.", 409)
    # Name, phone and email are collected on the options page
    # (Blacklane-style) before paying: a booking that reached
    # payment without them cannot be charged or dispatched.
    if not booking.customer_name or not booking.phone or not booking.email:
        return err("Please add your name, phone and email before paying.", 400)
    # Compulsory customer sign-in (owner decision 2026-11-22): no
    # payment without an email sign-in for this booking's
    # email, and a phone number on the booking.
    gate = _customer_signin_error(booking)
    if gate:
        return err(gate, 401)
    data = request.get_json(silent=True) or {}
    if not stripe_payments.stripe_configured():
        # TEST MODE (no Stripe keys in Render). Live activation is
        # currently BLOCKED — the merchant Stripe account is
        # disabled (charges/payouts off) — so bookings must keep
        # working exactly as before this build: the pre-existing
        # fake authorization. Only the last 4 digits are stored;
        # the card number itself is never persisted; no Stripe API
        # call is ever made and no real charge happens. As soon as
        # keys ARE configured (test keys work; live keys need the
        # account fixed first) this branch is skipped and the live
        # path below runs.
        for field in ("card_number", "card_exp", "card_cvc", "card_name"):
            if not data.get(field):
                return err(f"Missing required field: {field}.")
        digits = "".join(ch for ch in str(data["card_number"]) if ch.isdigit())
        if not (12 <= len(digits) <= 19):
            return err("Invalid card number.")
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
        _send_payment_confirmation_email(booking, test=True)
        db.session.commit()
        return jsonify({"payment": _payment_view(payment),
                        "booking": {"status": booking.status},
                        "test_mode": True})
    # Live path (keys configured): raw card numbers never touch
    # this server — Stripe.js collects the card in the browser and
    # hands us a PaymentMethod id.
    if any(k in data for k in ("card_number", "card_exp", "card_cvc", "card_name")):
        return err("Card details must be entered in the secure card form. "
                   "Please reload the page and try again.")
    saved_card_id = data.get("saved_card_id")
    payment_method_id = (data.get("payment_method_id") or "").strip() or None
    customer_id = None
    if saved_card_id is not None:
        try:
            saved = db.session.get(CustomerCard, int(saved_card_id))
        except (TypeError, ValueError):
            saved = None
        if not saved or saved.phone != str(booking.phone):
            return err("Saved card not found.", 404)
        payment_method_id = saved.stripe_payment_method_id
        customer_id = saved.stripe_customer_id
    elif not payment_method_id:
        return err("payment_method_id is required.")
    if not payment_method_id.startswith("pm_"):
        return err("Invalid payment method. Please re-enter your card.")
    if customer_id is None:
        try:
            customer_id = _stripe_customer_for_phone(
                booking.phone, booking.customer_name, booking.email)
        except stripe_payments.StripePaymentsError as exc:
            return err(exc.user_message, 502)
    try:
        intent = stripe_payments.create_payment_intent(
            stripe_payments.to_cents(booking.fare_total),
            customer_id, payment_method_id, booking.id)
    except stripe_payments.StripePaymentsError as exc:
        return err(exc.user_message, 502)
    if intent["status"] == "requires_action":
        # 3-D Secure: the hold is NOT in place yet. No Payment row
        # and the booking stays awaiting_payment; the frontend
        # completes the check and calls /pay/confirm.
        card = intent.get("card") or {}
        return jsonify({
            "needs_action": True,
            "client_secret": intent.get("client_secret"),
            "payment_intent_id": intent["id"],
            "payment": {"status": "requires_action",
                        "amount": num(booking.fare_total),
                        "test": False, "last4": card.get("last4"),
                        "brand": card.get("brand")},
            "booking": {"status": booking.status},
        })
    if intent["status"] != "requires_capture":
        return err("Your card could not be authorized. Please try another card.", 502)
    payload = _authorize_booking(
        booking, intent, customer_id, payment_method_id,
        bool(data.get("save_card", True)))
    db.session.commit()
    return jsonify(payload)


@app.route("/api/bookings/<int:booking_id>/pay/confirm", methods=["POST"])
def confirm_booking_payment(booking_id):
    """After a 3-D Secure check: re-read the PaymentIntent. When the
    bank has approved it (requires_capture) the hold is recorded and
    the booking is sent to drivers, exactly as a direct /pay success.
    PAUSED (owner decision 2026-11-20): no payment is taken while
    prices are being updated."""
    if bookings_paused():
        return err(BOOKINGS_PAUSED_MESSAGE, 503)
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.status != "awaiting_payment":
        return err("Payment is taken before the booking is sent to drivers.", 409)
    # Same guard as /pay: name, phone and email are collected on the
    # options page before paying.
    if not booking.customer_name or not booking.phone or not booking.email:
        return err("Please add your name, phone and email before paying.", 400)
    # Compulsory customer sign-in (owner decision 2026-11-22): the
    # 3-D Secure confirmation is the same payment, so the same gate.
    gate = _customer_signin_error(booking)
    if gate:
        return err(gate, 401)
    data = request.get_json(silent=True) or {}
    pi_id = (data.get("payment_intent_id") or "").strip()
    if not pi_id:
        return err("payment_intent_id is required.")
    if not stripe_payments.stripe_configured():
        return err("Card payments are not set up yet. Please try again later.", 503)
    try:
        intent = stripe_payments.retrieve_payment_intent(pi_id)
    except stripe_payments.StripePaymentsError as exc:
        return err(exc.user_message, 502)
    intent_booking = intent.get("booking_id")
    if intent_booking not in (None, "", str(booking.id), booking.id):
        return err("This payment does not belong to this booking.", 409)
    if intent["status"] == "requires_action":
        return jsonify({
            "needs_action": True,
            "client_secret": intent.get("client_secret"),
            "payment_intent_id": pi_id,
            "payment": {"status": "requires_action",
                        "amount": num(booking.fare_total), "test": False},
            "booking": {"status": booking.status},
        })
    if intent["status"] != "requires_capture":
        return err("Your card could not be authorized. Please try another card.", 502)
    payload = _authorize_booking(
        booking, intent, intent.get("customer_id"),
        intent.get("payment_method_id"),
        bool(data.get("save_card", True)))
    db.session.commit()
    return jsonify(payload)


@app.route("/api/customers/cards", methods=["GET"])
def list_customer_cards():
    """A customer's saved cards (phone-keyed; customers have no
    accounts). Brand / last 4 / expiry only — the card itself lives
    with Stripe."""
    phone = (request.args.get("phone") or "").strip()
    if not phone:
        return err("phone query parameter is required.")
    cards = (CustomerCard.query.filter_by(phone=phone)
             .order_by(CustomerCard.id.desc()).all())
    return jsonify({"cards": [_saved_card_view(c) for c in cards]})


@app.route("/api/customers/cards", methods=["POST"])
def save_customer_card():
    """Save a card from Stripe.js (PaymentMethod id) for future
    rides. The card is attached to the customer's Stripe Customer —
    Noel never sees the card number."""
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    pm_id = (data.get("payment_method_id") or "").strip()
    if not phone:
        return err("phone is required.")
    if not pm_id.startswith("pm_"):
        return err("Invalid payment method. Please re-enter your card.")
    if not stripe_payments.stripe_configured():
        return err("Card payments are not set up yet. Please try again later.", 503)
    existing = CustomerCard.query.filter_by(
        phone=phone, stripe_payment_method_id=pm_id).first()
    if existing:
        return jsonify({"card": _saved_card_view(existing)})
    try:
        customer_id = _stripe_customer_for_phone(
            phone, data.get("name"), data.get("email"))
        attached = stripe_payments.attach_payment_method(pm_id, customer_id)
    except stripe_payments.StripePaymentsError as exc:
        return err(exc.user_message, 502)
    card = CustomerCard(
        phone=phone, stripe_customer_id=customer_id,
        stripe_payment_method_id=pm_id,
        brand=attached.get("brand"), last4=attached.get("last4"),
        exp_month=attached.get("exp_month"), exp_year=attached.get("exp_year"))
    db.session.add(card)
    db.session.commit()
    return jsonify({"card": _saved_card_view(card)}), 201


@app.route("/api/customers/cards/<int:card_id>", methods=["DELETE"])
def delete_customer_card(card_id):
    """Remove a saved card (detached at Stripe too)."""
    phone = (request.args.get("phone") or "").strip()
    card = db.session.get(CustomerCard, card_id)
    if not card or card.phone != phone:
        return err("Saved card not found.", 404)
    if stripe_payments.stripe_configured():
        try:
            stripe_payments.detach_payment_method(card.stripe_payment_method_id)
        except stripe_payments.StripePaymentsError:
            pass  # the local row is still removed
    db.session.delete(card)
    db.session.commit()
    return jsonify({"deleted": True})


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
    # Free-cancel window: 1 hour before pickup on one-way rides;
    # 24 hours on hourly bookings (Blacklane rule, owner decision
    # 2026-11-20).
    free_cancel_hours = 24 if booking.ride_type == "hourly" else 1
    refundable = cancellation_refundable(booking.date, booking.time,
                                         free_cancel_hours=free_cancel_hours)
    payment = _latest_payment(booking.id)
    refund = False
    charge_kept = False
    refund_pending = False
    payment_status = payment.status if payment else None
    if payment is not None:
        if refundable:
            # Free cancel: release the hold (or refund a captured
            # charge). A failed release/refund marks the payment
            # refund_pending for the owner to retry — the booking is
            # still cancelled.
            refund, refund_pending = _release_booking_payment(booking)
        else:
            # Late cancel: full price is kept — capture the
            # authorized hold in full (legacy test rows: no real
            # money ever moved).
            charge_kept, _note = _settle_booking_payment(booking, booking.fare_total)
        payment_status = payment.status
    booking.status = "cancelled"
    if payment is None:
        cancel_note = "No payment had been taken."
    elif refund:
        cancel_note = "Payment refunded."
    elif refund_pending:
        cancel_note = ("Refund failed — payment marked refund_pending "
                       "for owner follow-up.")
    elif charge_kept:
        cancel_note = "Full price kept."
    else:
        cancel_note = ("Full price kept (capture failed — payment marked "
                       "capture_shortfall for owner follow-up).")
    add_event(booking.id, "customer_cancelled",
              f"Booking #{booking.id} cancelled by customer. {cancel_note}")
    db.session.commit()
    return jsonify({"booking": {"status": "cancelled"}, "refund": refund,
                    "charge_kept": charge_kept, "refund_pending": refund_pending,
                    "payment_status": payment_status})


@app.route("/api/bookings", methods=["GET"])
def booking_history():
    phone = request.args.get("phone")
    if phone:
        bookings = (Booking.query.filter_by(phone=phone)
                    .order_by(Booking.created_at.desc(), Booking.id.desc()).all())
    else:
        # Signed-in customers see their own rides by email (owner
        # decision 2026-11-22: a signed-in customer stays signed in
        # for later bookings, and My Rides shows their rides). The
        # email must match the sign-in session — an email
        # query for anyone else's address is refused. The old
        # phone lookup still works exactly as before for rides
        # booked before sign-in existed.
        email = _normalize_customer_email(request.args.get("email"))
        signed_in = _customer_signin_email()
        if not email or not signed_in or email != signed_in:
            return err("phone query parameter is required.")
        bookings = (Booking.query.filter(func.lower(Booking.email) == email)
                    .order_by(Booking.created_at.desc(), Booking.id.desc()).all())
    return jsonify([{
        "id": b.id,
        "pickup": b.pickup,
        "dropoff": b.dropoff,
        "date": b.date,
        "time": b.time,
        "status": b.status,
        "ride_type": b.ride_type,
        "is_return": bool(getattr(b, "is_return", False)),
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


# ------------------------------------------------------------- chat -------

MAX_CHAT_TEXT = 500
# Chat is open once a driver has accepted and until the trip ends
# (completed rides keep their chat readable; cancelled/no-show rides
# do not). The same status set gates both sides.
CHAT_STATUSES = {"accepted", "en_route", "arrived", "in_progress", "completed"}


def driver_chat_language(driver):
    """A driver's declared chat language ("en" when unset/unknown)."""
    if driver is None:
        return "en"
    return normalize_chat_language(driver.chat_language)


def booking_customer_chat_language(booking):
    """A booking customer's declared chat language ("en" when unset)."""
    if booking is None:
        return "en"
    return normalize_chat_language(booking.customer_chat_language)


def _viewer_language(stored_language, requested):
    """The language a chat reader views in: an explicitly requested
    valid picker value wins for this read, else the stored declared
    preference. Reads never persist — the picker endpoints do that."""
    if isinstance(requested, str) and requested.strip() in CHAT_LANGUAGES:
        return requested.strip()
    return normalize_chat_language(stored_language)


def _chat_message_view(message, viewer, viewer_language):
    # Text only — never any money figure, by construction. `text`
    # stays the field every client already reads: your own messages
    # show exactly as typed; the other side's messages show the
    # stored send-time translation when one exists in YOUR language,
    # else the original text. `original_text` / `translated` are
    # additive — clients that ignore them see the same shape as before.
    display = message.text
    if (message.sender != viewer and message.translated_text
            and message.translated_language == viewer_language):
        display = message.translated_text
    return {
        "id": message.id,
        "sender": message.sender,
        "text": display,
        "original_text": message.text,
        "translated": display != message.text,
        "created_at": iso(message.created_at),
    }


def _chat_messages(booking_id, viewer, viewer_language):
    return [_chat_message_view(m, viewer, viewer_language) for m in
            ChatMessage.query.filter_by(booking_id=booking_id).order_by(ChatMessage.id).all()]


def _translate_at_send(text, source_language, target_language):
    """Translate once at send time. Returns (translated_text,
    translated_language) or (None, None) when no translation applies
    or Azure failed — the caller then stores the original only."""
    translated = translate_chat_text(text, source_language, target_language)
    if not translated:
        return None, None
    return translated, normalize_chat_language(target_language)


def _validate_chat_language(data):
    """A picker language from a request body: the valid code, or None
    when absent. An unknown code is a 400 — the picker only sends
    valid codes, so an unknown one is a bad client, not a guess."""
    value = data.get("language")
    if value is None or value == "":
        return None, None
    if isinstance(value, str) and value.strip() in CHAT_LANGUAGES:
        return value.strip(), None
    return None, err("Unknown chat language.")


def _validate_chat_text(data):
    text = (data.get("text") or "")
    if not isinstance(text, str):
        return None, err("text must be a string.")
    text = text.strip()
    if not text:
        return None, err("Message text is required.")
    if len(text) > MAX_CHAT_TEXT:
        return None, err(f"Message is too long (max {MAX_CHAT_TEXT} characters).")
    return text, None


def _require_chat_customer(booking, phone):
    """The customer side of the chat: same phone check as cancel, and
    only once a driver has accepted."""
    if not phone or str(phone) != str(booking.phone):
        return err("Phone number does not match this booking.", 403)
    if booking.status not in CHAT_STATUSES:
        return err("Chat opens once a driver has accepted your ride.", 409)
    return None


@app.route("/api/bookings/<int:booking_id>/messages", methods=["GET"])
def customer_chat_list(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    error = _require_chat_customer(booking, request.args.get("phone"))
    if error:
        return error
    viewer_language = _viewer_language(
        booking.customer_chat_language, request.args.get("language"))
    return jsonify({"messages": _chat_messages(booking.id, "customer", viewer_language)})


@app.route("/api/bookings/<int:booking_id>/chat-language", methods=["POST"])
def customer_chat_language(booking_id):
    """Save the customer's declared chat language for this booking.

    Phone check only — no chat-status gate, so the language can be
    picked as soon as the chat panel is reachable. The picker calls
    this on change; sending a message with a `language` also saves it.
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    data = request.get_json(silent=True) or {}
    if not data.get("phone") or str(data["phone"]) != str(booking.phone):
        return err("Phone number does not match this booking.", 403)
    language, error = _validate_chat_language(data)
    if error:
        return error
    if language is None:
        return err("language is required.")
    booking.customer_chat_language = language
    db.session.commit()
    return jsonify({"chat_language": language})


@app.route("/api/bookings/<int:booking_id>/messages", methods=["POST"])
def customer_chat_send(booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    data = request.get_json(silent=True) or {}
    error = _require_chat_customer(booking, data.get("phone"))
    if error:
        return error
    text, error = _validate_chat_text(data)
    if error:
        return error
    language, error = _validate_chat_language(data)
    if error:
        return error
    if language is not None:
        booking.customer_chat_language = language
    sender_language = booking_customer_chat_language(booking)
    translated_text, translated_language = _translate_at_send(
        text, sender_language, driver_chat_language(booking.accepted_driver))
    message = ChatMessage(booking_id=booking.id, sender="customer", text=text,
                          sender_language=sender_language,
                          translated_text=translated_text,
                          translated_language=translated_language)
    db.session.add(message)
    db.session.commit()
    return jsonify({"message": _chat_message_view(message, "customer", sender_language)}), 201


@app.route("/api/drivers/me/trip/<int:booking_id>/messages", methods=["GET"])
def driver_chat_list(booking_id):
    driver, error = require_driver()
    if error:
        return error
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.accepted_driver_id != driver.id:
        return err("This booking is not assigned to you.", 403)
    if booking.status not in CHAT_STATUSES:
        return err("Chat is not open for this ride.", 409)
    viewer_language = _viewer_language(driver.chat_language, request.args.get("language"))
    return jsonify({"messages": _chat_messages(booking.id, "driver", viewer_language)})


@app.route("/api/drivers/me/chat-language", methods=["POST"])
def driver_chat_language_save():
    """Save the driver's declared chat language (all rides).

    The picker calls this on change; sending a message with a
    `language` also saves it."""
    driver, error = require_driver()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    language, error = _validate_chat_language(data)
    if error:
        return error
    if language is None:
        return err("language is required.")
    driver.chat_language = language
    db.session.commit()
    return jsonify({"chat_language": language})


@app.route("/api/drivers/me/trip/<int:booking_id>/messages", methods=["POST"])
def driver_chat_send(booking_id):
    driver, error = require_driver()
    if error:
        return error
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.accepted_driver_id != driver.id:
        return err("This booking is not assigned to you.", 403)
    if booking.status not in CHAT_STATUSES:
        return err("Chat is not open for this ride.", 409)
    data = request.get_json(silent=True) or {}
    text, error = _validate_chat_text(data)
    if error:
        return error
    language, error = _validate_chat_language(data)
    if error:
        return error
    if language is not None:
        driver.chat_language = language
    sender_language = driver_chat_language(driver)
    translated_text, translated_language = _translate_at_send(
        text, sender_language, booking_customer_chat_language(booking))
    message = ChatMessage(booking_id=booking.id, sender="driver", text=text,
                          sender_language=sender_language,
                          translated_text=translated_text,
                          translated_language=translated_language)
    db.session.add(message)
    db.session.commit()
    return jsonify({"message": _chat_message_view(message, "driver", sender_language)}), 201


# ------------------------------------------- support widget ("Chat with us") --

# Keywords that flag a support message as needing the owner's
# attention (the problem/escalation + lost-item branches of the
# widget's scripted answers). Flagging only marks the row for the
# owner dashboard; every typed message is stored either way.
SUPPORT_FLAG_KEYWORDS = ("problem", "complaint", "issue", "unhappy",
                         "escalat", "manager", "owner",
                         "lost", "left", "forgot", "belonging", "item")


def _support_flagged(text):
    lowered = text.lower()
    return any(kw in lowered for kw in SUPPORT_FLAG_KEYWORDS)


@app.route("/api/support-messages", methods=["POST"])
def support_message_create():
    """Store one typed 'Chat with us' message for the owner. No
    login and no booking required — the widget is available before
    booking. Text only, same 500-character limit as the trip chat.
    The widget fires this and forgets: any failure here must never
    break the scripted answers, which are answered client-side."""
    data = request.get_json(silent=True) or {}
    text, error = _validate_chat_text(data)
    if error:
        return error
    message = SupportMessage(text=text, flagged=_support_flagged(text))
    db.session.add(message)
    db.session.commit()
    return jsonify({"message": {
        "id": message.id, "text": message.text,
        "flagged": message.flagged, "created_at": iso(message.created_at),
    }}), 201


# ---------------------------------------------------------------- drivers ---

# Profile-photo shape/size rules (owner decision 2026-11-17: "Profile
# photo should be passport photo jaisa rehna chahiye. Nake kuch bhi
# dadlo accept nahi karna. Bas face proper dikhna." — the profile
# photo must stay passport-style; just anything must not be accepted).
# The owner picked the LIGHT option: shape/size check + passport
# frame, NOT face detection. So this checks shape and size only — it
# cannot judge whether a face is actually in the photo. The floor is
# deliberately low so normal phone portrait photos pass, including
# tall 9:16 shots: portrait orientation (taller than wide, after
# EXIF orientation) and at least 300px on the short side.
PROFILE_PHOTO_MIN_SHORT_SIDE = 300


def _profile_photo_error(data):
    """Return an error message if profile-photo bytes fail the
    passport-style shape/size rules, else None."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            oriented = ImageOps.exif_transpose(im)
            width, height = oriented.size
    except Exception:
        return ("Profile photo could not be read — please upload a clear "
                "photo of your face.")
    if height <= width:
        return ("Profile photo must be a portrait photo (taller than it is "
                "wide) — please upload a passport-style photo of your face.")
    if width < PROFILE_PHOTO_MIN_SHORT_SIDE:
        return ("Profile photo is too small — please upload a larger, clear "
                "photo of your face (at least 300 pixels wide).")
    return None


# Plate format (owner decision 2026-11-17, "Format check laga do"):
# Uber-style generic US plate check for NEW registrations only.
# Spaces and dashes are ignored; what is left must be 2-8 letters or
# digits. The stored value is normalized to uppercase with spaces and
# dashes removed. No per-state patterns — nothing invented. Drivers
# registered before this change keep their stored plates untouched:
# this gate runs only inside register_driver.
PLATE_ERROR = "Please enter a valid plate number (letters and numbers only)."


def validate_plate(value):
    """Return (normalized_plate, None) or (None, error_message).

    The driver app enforces the same rule with the same wording
    before submitting; the server re-checks so a bypassed client
    cannot store an invalid plate.
    """
    plate = (value or "").strip().replace(" ", "").replace("-", "").upper()
    if len(plate) < 2 or len(plate) > 8:
        return None, PLATE_ERROR
    if not plate.isascii() or not plate.isalnum():
        return None, PLATE_ERROR
    return plate, None


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


# --- Driver document verification (owner decision 2026-11-19) -----------
def _blank_photo_error(data):
    """Return an error string if image bytes are effectively blank
    (nearly uniform AND nearly all white or all black), else None.
    Conservative on purpose: a normal document photo — white paper
    with dark text — has far more variance than the threshold, so it
    never trips. Unparseable bytes return None here; the callers'
    readability check owns that case."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            grey = im.convert("L").resize((64, 64))
            pixels = list(grey.getdata())
    except Exception:
        return None
    mean = sum(pixels) / len(pixels)
    var = sum((p - mean) ** 2 for p in pixels) / len(pixels)
    if var ** 0.5 < BLANK_PHOTO_MAX_STDDEV and (
            mean > BLANK_PHOTO_WHITE_MEAN or mean < BLANK_PHOTO_BLACK_MEAN):
        return "blank"
    return None


def _doc_photo_error(data, label):
    """Photo sanity for one uploaded document image (not PDFs).
    Returns a plain, non-accusing error string, or None when the
    photo is usable: must open as a real image, both sides at least
    DOC_PHOTO_MIN_SIDE pixels, and not effectively blank."""
    try:
        with Image.open(io.BytesIO(data)) as im:
            width, height = im.size
    except Exception:
        return (f"Your {label} photo could not be read — please upload "
                "a clear photo of the document.")
    if width < DOC_PHOTO_MIN_SIDE or height < DOC_PHOTO_MIN_SIDE:
        return (f"Your {label} photo is too small — please upload "
                "a clear photo of the document.")
    if _blank_photo_error(data):
        return (f"Your {label} photo looks blank or unreadable — please "
                "upload a clear photo of the document.")
    return None


def _today_ny():
    """Today's date in America/New_York (the service area)."""
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/New_York")).date()


def _parse_expiry(value, label):
    """Validate one typed expiry date (YYYY-MM-DD). Returns
    (date, None) or (None, error string). A past date is an expired
    document: the driver is told clearly and asked to upload a
    fresh, valid one."""
    text = (value or "").strip()
    if not text:
        return None, f"Please enter the expiry date for your {label}."
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return None, f"Please enter a valid expiry date for your {label}."
    if parsed < _today_ny():
        return None, (f"Your {label} is expired — please upload a new, "
                      "valid one.")
    return parsed, None


def _record_document_flag(form, doc_type, reason, file_hash=None, detail=""):
    """Record a rejected registration attempt for the owner dashboard.
    Best-effort: a flag that fails to save never blocks the rejection
    itself, and never leaks the driver's files."""
    try:
        label = ALL_DOC_LABELS.get(doc_type, doc_type)
        db.session.add(DocumentFlag(
            name=(form.get("name") or "").strip(),
            phone=(form.get("phone") or "").strip(),
            email=(form.get("email") or "").strip().lower(),
            doc_type=doc_type,
            doc_label=label,
            reason=reason,
            file_hash=file_hash,
            detail=detail or "",
        ))
        db.session.commit()
    except Exception as exc:  # logged, never fatal to the rejection
        db.session.rollback()
        log.warning("document flag record failed: %s", exc)


@app.route("/api/car-models", methods=["GET"])
def car_models():
    """Eligible car models for the driver registration dropdown.

    One list, served from car_models.py (the transcribed Uber Black
    list + the temporary Model 3 owner-trial exception). The driver
    app fetches this; the server validates against the same set.

    The Model 3 exception is only visible to the two allowed drivers
    (owner decision 2026-11-19): the form passes the email typed in
    the registration form as ?email=, and the list includes Model 3
    only for Azher Mohammed and Sana Baga. Without it (or for any
    other email) the list is the 132 Uber Black models and Model 3
    never appears.
    """
    return jsonify({
        "models": allowed_models(request.args.get("email", "")),
        "min_year": MIN_CAR_YEAR,
        "max_year": max_car_year(),
    })


@app.route("/api/states", methods=["GET"])
def list_states():
    """US states + per-state registration document requirements.

    One mapping, served from the same constants the server validates
    against. The driver app fetches this to build the searchable
    state dropdown (alphabetical, type to filter) and to show the
    document list for the chosen state. `local_note` marks every
    state whose list is not fully verified (partial lists and the
    generic base list), where requirements vary by locality and
    the owner reviews each application.

    The same payload serves the city picker (owner decision
    2026-11-17, Uber-style): `cities` lists each state's largest
    cities, alphabetical, with the "Other city" fallback last, and
    `city_requirements` carries the verified city-specific lists
    that override their state list (21 cities today; see
    CITY_DOC_REQUIREMENTS). Every other
    city uses its state list unchanged.
    """
    return jsonify({
        "states": US_STATES,
        "cities": {state: cities_for_state(state) for state in US_STATES},
        "city_requirements": {
            state: {
                city: {
                    "docs": docs,
                    "local_note": local_note_for(state, city),
                }
                for (s, city), docs in sorted(CITY_DOC_REQUIREMENTS.items())
                if s == state
            }
            for state in US_STATES
            if any(s == state for (s, _c) in CITY_DOC_REQUIREMENTS)
        },
        "documents": {
            doc_type: {
                "label": ALL_DOC_LABELS[doc_type],
                "hint": DOC_HINTS[doc_type],
                "field": FIELD_FOR_DOC_TYPE[doc_type],
                # FH-1 alone accepts a PDF, as in the registration form.
                "accept": ("image/*,.pdf,application/pdf"
                           if doc_type == "fh1_insurance" else "image/*"),
                # The driver types the expiry date printed on the
                # document (owner decision 2026-11-19); the form
                # shows a date input for these types only.
                "has_expiry": doc_type in EXPIRY_DOC_TYPES,
            }
            for doc_type in ALL_DOC_LABELS
        },
        "requirements": {
            state: {
                "docs": required_docs_for_state(state),
                "local_note": state not in VERIFIED_DOC_STATES,
            }
            for state in US_STATES
        },
    })


@app.route("/api/drivers/register", methods=["POST"])
def register_driver():
    form = request.form
    for field in ("name", "phone", "car_model", "car_year", "car_colour", "plate",
                  "bank_account_number", "bank_routing_number", "state"):
        if not (form.get(field) or "").strip():
            return err(f"Missing required field: {field}.")
    # Routing + account numbers are COMPULSORY and must be valid
    # (owner decision 2026-11-20): no driver can complete payout
    # setup — or receive weekly payouts — without them.
    routing_error = validate_routing_number(form.get("bank_routing_number"))
    if routing_error:
        return err(routing_error)
    account_error = validate_bank_account_number(form.get("bank_account_number"))
    if account_error:
        return err(account_error)
    phone = form["phone"].strip()
    if Driver.query.filter_by(phone=phone).first():
        return err("A driver with this phone number is already registered.", 409)

    # Email is normalized (trim + lowercase) so sign-in matching is
    # case-insensitive. A non-empty email already on another driver
    # is rejected, same pattern as the duplicate phone above; empty
    # emails (drivers registered before email was collected) are
    # never blocked.
    email = (form.get("email") or "").strip().lower()
    if email and Driver.query.filter(func.lower(Driver.email) == email).first():
        return err("A driver with this email address is already registered.", 409)

    # Driver referral link (owner decision 2026-11-18): registration
    # that arrived via /driver?ref=CODE carries the referrer's code in
    # a hidden form field — the form itself has no extra field or
    # step. An unknown code is ignored (fail-soft: registration
    # proceeds normally with no referrer, never blocked), and a code
    # belonging to the same person (same phone/email) earns nothing.
    # Customer "NOEL-" codes live in a separate table and never
    # resolve here.
    referrer = None
    ref_code = (form.get("referral_code") or "").strip().upper() or None
    if ref_code:
        try:
            referrer = Driver.query.filter_by(referral_code=ref_code).first()
        except Exception:
            referrer = None
        if referrer and (referrer.phone == phone or
                         (email and referrer.email and
                          referrer.email.lower() == email)):
            referrer = None

    # Password for email+password sign-in (owner decision 2026-11-18,
    # "complete sign in process banao"). The driver-app form always
    # sends it (required there); registrations that omit it keep
    # working with no hash, so drivers registered before passwords
    # existed and older clients are not broken. When provided it
    # must be at least 6 characters and match the confirmation;
    # only the hash is stored, never the plaintext password.
    password = form.get("password") or ""
    password_confirm = form.get("password_confirm") or ""
    password_hash = None
    if password or password_confirm:
        if len(password) < 6:
            return err("Password must be at least 6 characters.")
        if password != password_confirm:
            return err("Passwords do not match.")
        password_hash = generate_password_hash(password)

    # State must come from the dropdown list (USA only, exact match —
    # same rule as the car-model dropdown). The state decides which
    # documents are compulsory for this driver.
    state = form["state"].strip()
    if state not in US_STATES:
        return err("Please choose your state from the list.")

    # City must come from the dropdown list for that state (exact
    # match, same rule as the state). Optional in the API so drivers
    # registered before the city picker existed keep working, and so
    # older clients are not broken; the registration form always
    # sends it. A city with a verified city-specific list (Dallas,
    # Buffalo) overrides the state list; every other city — including "Other
    # city" — uses the state list unchanged.
    city = (form.get("city") or "").strip() or None
    if city is not None and city not in cities_for_state(state):
        return err("Please choose your city from the list.")

    # Car model must come from the eligible list (dropdown), and the
    # model year must be 2022 or newer (owner decision 2026-11-16).
    # The temporary Model 3 is rejected here for anyone but the two
    # allowed drivers (owner decision 2026-11-19), even if it is
    # posted directly instead of picked from the dropdown.
    car_model, model_error = validate_car_model(form.get("car_model"), email)
    if model_error:
        return err(model_error)
    car_year, year_error = validate_car_year(form.get("car_year"))
    if year_error:
        return err(year_error)

    # Plate format check (owner decision 2026-11-17, "Format check
    # laga do"): Uber-style generic US plate rule, new registrations
    # only. Placed after the duplicate-phone check above, so a
    # duplicate phone still reports 409. The normalized (uppercase,
    # no spaces/dashes) value is what gets stored.
    plate, plate_error = validate_plate(form.get("plate"))
    if plate_error:
        return err(plate_error)

    # Validate all uploaded files before creating anything.
    profile_photo = None
    if "profile_photo" in request.files and request.files["profile_photo"].filename:
        profile_photo, error = _validate_upload(request.files["profile_photo"], IMAGE_EXTS, "profile_photo")
        if error:
            return error
        # Passport-style shape/size check, profile photo only: the
        # other document photos keep today's rules (any orientation).
        shape_error = _profile_photo_error(profile_photo[0])
        if shape_error:
            return err(shape_error)
        # A blank profile photo is the same problem as a blank
        # document photo: the face must be visible, so it is
        # rejected too (owner decision 2026-11-19).
        if _blank_photo_error(profile_photo[0]):
            _record_document_flag(form, "profile_picture", "blank_photo",
                                  hashlib.sha256(profile_photo[0]).hexdigest())
            return err("Your Profile Picture photo looks blank or unreadable — "
                       "please upload a clear photo of yourself.")
    docs = {}
    for field_name, doc_type in DOC_FIELD_MAP.items():
        storage = request.files.get(field_name)
        if storage and storage.filename:
            allowed = IMAGE_EXTS | {".pdf"} if doc_type == "fh1_insurance" else IMAGE_EXTS
            parsed, error = _validate_upload(storage, allowed, field_name)
            if error:
                return error
            docs[doc_type] = parsed

    # Owner decision 2026-11-17: documents are COMPULSORY — registration
    # must not complete unless every item is uploaded ("Compulsory
    # documents un log upload karna hi zaroori hai. Nahi to registration
    # nahi hoga."). The rejection names each missing item in the
    # owner's words: "Missing document: ...". Which items are required
    # depends on the driver's state and city (New York keeps the
    # original 7; other states have their own verified list or the
    # generic base list; a city with a verified city-specific list,
    # 21 cities today, overrides its state list). This gates
    # only new
    # registrations: drivers registered before this change keep
    # signing in and going available exactly as before.
    missing = []
    for doc_type in required_docs_for(state, city):
        if doc_type == "profile_picture":
            present = profile_photo is not None
        else:
            present = doc_type in docs
        if not present:
            missing.append(ALL_DOC_LABELS[doc_type])
    if missing:
        return err("Missing document: " + ", ".join(missing) +
                   ". Please upload all required documents to complete registration.")

    # Driver document verification (owner decision 2026-11-19):
    # duplicate-file hashes, photo sanity, and expiry dates. Runs
    # AFTER the missing-documents gate, so "Missing document: ..."
    # behaviour is unchanged. Nothing is stored on rejection — only
    # a read-only flag row for the owner dashboard. Duplicate
    # detection covers the DriverDocument uploads only: the profile
    # photo has no document row (it lives on the driver) and gets
    # its own shape/size/blank checks above instead.
    uploads = [(doc_type, data) for doc_type, (data, _mime, _name)
               in docs.items()]
    hashes = {doc_type: hashlib.sha256(data).hexdigest()
              for doc_type, data in uploads}
    # Photo sanity for document images (PDFs skip it: the FH-1 PDF
    # has no pixels to judge).
    for doc_type, (data, mime, _name) in docs.items():
        if mime == "application/pdf":
            continue
        photo_error = _doc_photo_error(data, ALL_DOC_LABELS.get(doc_type, doc_type))
        if photo_error:
            reason = ("blank_photo" if "blank or unreadable" in photo_error
                      else "tiny_photo" if "too small" in photo_error
                      else "unreadable_photo")
            _record_document_flag(form, doc_type, reason, hashes[doc_type])
            return err(photo_error)
    # Same file bytes in two slots of one registration.
    seen_hashes = {}
    for doc_type, _data in uploads:
        h = hashes[doc_type]
        if h in seen_hashes:
            other_type = seen_hashes[h]
            _record_document_flag(form, doc_type, "duplicate_same_driver", h,
                                  "same file as " + other_type)
            return err(
                f"Your {ALL_DOC_LABELS.get(doc_type, doc_type)} photo is the same "
                f"as your {ALL_DOC_LABELS.get(other_type, other_type)} photo — "
                "please upload a different photo for each document.")
        seen_hashes[h] = doc_type
    # Same file bytes already submitted by a DIFFERENT driver (any
    # document type). Existing drivers are never re-checked: rows
    # stored before file_hash existed read as NULL and never match.
    existing = DriverDocument.query.filter(
        DriverDocument.file_hash.in_(list(seen_hashes))).first()
    if existing is not None:
        _record_document_flag(form, existing.doc_type, "duplicate_other_driver",
                              existing.file_hash)
        return err("This document photo was already used for another driver "
                   "account. Please upload your own document.")
    # Expiry dates, typed by the driver from the date printed on the
    # document. A past date is an expired document and the
    # registration is rejected — the driver is told clearly and asked
    # to upload a fresh, valid one.
    expiries = {}
    for doc_type in docs:
        if doc_type not in EXPIRY_DOC_TYPES:
            continue
        label = ALL_DOC_LABELS.get(doc_type, doc_type)
        expires, expiry_error = _parse_expiry(form.get("expiry_" + doc_type), label)
        if expiry_error:
            reason = ("expired" if "is expired" in expiry_error
                      else "missing_expiry" if "enter the expiry date" in expiry_error
                      else "invalid_expiry")
            _record_document_flag(form, doc_type, reason, hashes[doc_type])
            return err(expiry_error)
        expiries[doc_type] = expires

    account = form["bank_account_number"].strip()
    routing = form["bank_routing_number"].strip()
    driver = Driver(
        name=form["name"].strip(),
        phone=phone,
        email=email,
        password_hash=password_hash,
        state=state,
        city=city,
        # Every driver gets his own stable referral code at
        # registration, and the referrer (if any) is stored so his
        # first 15 completed jobs credit $5 each to the referrer.
        referral_code=generate_driver_referral_code(),
        referred_by_driver_id=referrer.id if referrer else None,
        car_model=car_model,
        car_year=car_year,
        # Vehicle class is derived from the car model, never typed in.
        vehicle_class=class_for_model(car_model),
        car_colour=form["car_colour"].strip(),
        plate=plate,
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
            mime=mime, original_name=original_name,
            file_hash=hashlib.sha256(data).hexdigest(),
            expires_on=expiries.get(doc_type)))
    db.session.commit()
    return jsonify({"driver": {
        "id": driver.id,
        "name": driver.name,
        "phone": driver.phone,
        "email": driver.email,
        "state": driver.state,
        "city": driver.city,
        "chat_language": driver_chat_language(driver),
        "car_model": driver.car_model,
        "car_year": driver.car_year,
        "vehicle_class": driver_vehicle_class(driver),
        "vehicle_class_label": class_label(driver_vehicle_class(driver)),
        "car_colour": driver.car_colour,
        "plate": driver.plate,
        "docs": driver_docs_status(driver),
        "bank_masked": bank_masked(driver),
    }, "token": driver.token}), 201


@app.route("/api/drivers/me/documents", methods=["POST"])
def driver_reupload_document():
    """Re-upload ONE document for a signed-in driver (owner decision
    2026-11-19): the renewal path for an expired or expiring document.
    The same checks as registration run — duplicate-file hash, photo
    sanity, and a valid future expiry date — and the stored row is
    replaced. The expiry block lifts AUTOMATICALLY: it is computed
    from the stored expiry dates, so a fresh future expiry unblocks
    the driver with no owner action. Works while blocked (this IS the
    unblock path); sign-in is unchanged."""
    driver, error = require_driver()
    if error:
        return error
    doc_type = (request.form.get("doc_type") or "").strip()
    required = [t for t in required_docs_for(driver.state or "New York",
                                             getattr(driver, "city", None))
                if t != "profile_picture"]
    if doc_type not in required:
        return err("Unknown document type.")
    label = ALL_DOC_LABELS.get(doc_type, doc_type)
    storage = request.files.get("document")
    if storage is None or not storage.filename:
        return err(f"Please choose a {label} photo to upload.")
    allowed = IMAGE_EXTS | {".pdf"} if doc_type == "fh1_insurance" else IMAGE_EXTS
    parsed, upload_error = _validate_upload(storage, allowed, "document")
    if upload_error:
        return upload_error
    data, mime, original_name = parsed
    # Photo sanity for document images (PDFs skip it), same as
    # registration.
    if mime != "application/pdf":
        photo_error = _doc_photo_error(data, label)
        if photo_error:
            return err(photo_error)
    new_hash = hashlib.sha256(data).hexdigest()
    # Same file bytes already submitted by a DIFFERENT driver.
    other = (DriverDocument.query
             .filter(DriverDocument.file_hash == new_hash,
                     DriverDocument.driver_id != driver.id)
             .first())
    if other is not None:
        return err("This document photo was already used for another driver "
                   "account. Please upload your own document.")
    # Same file bytes as one of THIS driver's OTHER documents.
    own_other = (DriverDocument.query
                 .filter(DriverDocument.file_hash == new_hash,
                         DriverDocument.driver_id == driver.id,
                         DriverDocument.doc_type != doc_type)
                 .first())
    if own_other is not None:
        other_label = ALL_DOC_LABELS.get(own_other.doc_type, own_other.doc_type)
        return err(f"Your {label} photo is the same as your {other_label} photo — "
                   "please upload a different photo for each document.")
    # Expiry date, typed by the driver from the date printed on the
    # document. A past date is rejected, same as registration.
    expires = None
    if doc_type in EXPIRY_DOC_TYPES:
        expires, expiry_error = _parse_expiry(
            request.form.get("expiry_" + doc_type), label)
        if expiry_error:
            return err(expiry_error)
    existing = DriverDocument.query.filter_by(
        driver_id=driver.id, doc_type=doc_type).first()
    if existing is not None:
        # The 10-day alert flag resets only when the expiry date
        # itself changes, so re-uploading the same document with the
        # same expiry never queues a duplicate alert.
        if existing.expires_on != expires:
            existing.expiry_alert_sent_at = None
        existing.file = data
        existing.mime = mime
        existing.original_name = original_name
        existing.file_hash = new_hash
        existing.expires_on = expires
        doc = existing
    else:
        doc = DriverDocument(
            driver_id=driver.id, doc_type=doc_type, file=data,
            mime=mime, original_name=original_name,
            file_hash=new_hash, expires_on=expires)
        db.session.add(doc)
    db.session.commit()
    return jsonify({
        "document": {
            "doc_type": doc.doc_type,
            "label": label,
            "expires_on": doc.expires_on.isoformat() if doc.expires_on else None,
        },
        "expiry_blocked": is_driver_expiry_blocked(driver),
    })


@app.route("/api/drivers/me", methods=["GET"])
def driver_me():
    driver, error = require_driver()
    if error:
        return error
    # Fire the 10-day expiry-alert check whenever the driver opens
    # the app (same contact-point pattern as the pickup reminder):
    # best-effort, never breaks this response.
    _run_expiry_alerts_best_effort(driver_id=driver.id)
    today = _today_ny()
    return jsonify({"driver": {
        "id": driver.id,
        "name": driver.name,
        "phone": driver.phone,
        "email": driver.email,
        "state": driver.state,
        "city": driver.city,
        "chat_language": driver_chat_language(driver),
        "car_model": driver.car_model,
        "car_year": driver.car_year,
        "vehicle_class": driver_vehicle_class(driver),
        "vehicle_class_label": class_label(driver_vehicle_class(driver)),
        "car_colour": driver.car_colour,
        "plate": driver.plate,
        "docs": driver_docs_status(driver),
        "bank_masked": bank_masked(driver),
        "available": driver.available,
        "suspended_until": iso(driver_suspension_end(driver)),
        # Document expiry state (owner decision 2026-11-19): the
        # driver app shows the in-app notice from these fields.
        # expired_docs pauses the registration; expiring_docs is the
        # 10-day advance warning. doc_expiries covers every stored
        # document (None where no expiry is on file).
        "expiry_blocked": is_driver_expiry_blocked(driver, today),
        "expired_docs": [{"doc_type": d.doc_type,
                          "label": ALL_DOC_LABELS.get(d.doc_type, d.doc_type),
                          "expires_on": d.expires_on.isoformat()}
                         for d in expired_documents(driver, today)],
        "expiring_docs": [{"doc_type": d.doc_type,
                           "label": ALL_DOC_LABELS.get(d.doc_type, d.doc_type),
                           "expires_on": d.expires_on.isoformat(),
                           "days_left": (d.expires_on - today).days}
                          for d in expiring_documents(driver, today)],
        "doc_expiries": {doc.doc_type: (doc.expires_on.isoformat()
                                        if doc.expires_on else None)
                         for doc in driver.documents},
        "expiry_doc_types": sorted(EXPIRY_DOC_TYPES),
    }})


@app.route("/api/drivers/me/referral", methods=["GET"])
def driver_referral():
    """The signed-in driver's own referral view: his stable referral
    code (the app builds the shareable /driver?ref=CODE link from it,
    same pattern as the customer referral link), his total referral
    earnings, and one row per driver he referred. Drivers registered
    before referral codes existed get a code minted here, on first
    load — the code is then stable across sessions. His own earnings
    only, never another driver's fares or totals."""
    driver, error = require_driver()
    if error:
        return error
    _, minted = ensure_driver_referral_code(driver)
    if minted:
        db.session.commit()
    return jsonify(driver_referral_summary(driver))


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
    return jsonify({"driver": {"id": driver.id, "name": driver.name,
                               "suspended_until": iso(driver_suspension_end(driver))},
                    "token": driver.token})


@app.route("/api/drivers/me/signin", methods=["POST"])
def driver_signin():
    """Email + password sign-in (owner decision 2026-11-18, complete
    sign-in process). Same token mechanism as the phone lookup: the
    token is re-issued, so signing in on a new phone signs the old
    one out. The error is deliberately generic — it never reveals
    whether the email or the password was wrong, or whether the
    driver has a password set at all (drivers registered before
    passwords existed have no hash and keep using the phone
    lookup). No forgot-password reset exists yet: no email service
    is connected, so no reset email can be sent."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    driver = None
    if email:
        driver = Driver.query.filter(func.lower(Driver.email) == email).first()
    if not driver or not driver.password_hash or not check_password_hash(
        driver.password_hash, password
    ):
        return err("Email or password is incorrect.", 401)
    driver.token = uuid.uuid4().hex  # re-issue token (same as lookup)
    db.session.commit()
    return jsonify({"driver": {"id": driver.id, "name": driver.name,
                               "suspended_until": iso(driver_suspension_end(driver))},
                    "token": driver.token})


# Password reset (owner decision 2026-11-18, drivers keep forgetting
# passwords). Tokens are single-use, expire after 5 minutes, and only
# their SHA-256 hash is stored. The reset link is queued via the
# existing outbox — recorded, not sent, until an email service is
# connected — and never appears in any API response or log.
RESET_TOKEN_TTL = timedelta(minutes=5)
RESET_REQUEST_MESSAGE = ("If an account exists for that email, "
                         "password reset instructions have been sent.")
RESET_INVALID_MESSAGE = "This reset link is invalid or has expired."


def _hash_reset_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.route("/api/drivers/me/forgot-password", methods=["POST"])
def driver_forgot_password():
    """Request a password link. ALWAYS returns the same generic
    message, whether or not the email matches a driver — it never
    reveals whether an email is registered. A token is created for
    ANY existing driver. A driver who already has a password gets
    the reset email; a driver registered before passwords existed
    (no password hash) gets a create-password email instead, so
    they can set a password for the first time. Issuing a token
    invalidates the driver's previous unused tokens, so only the
    newest link works."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    driver = None
    if email:
        driver = Driver.query.filter(func.lower(Driver.email) == email).first()
    if driver:
        now = utcnow()
        for old in PasswordResetToken.query.filter_by(
                driver_id=driver.id, used_at=None).all():
            old.used_at = now
        token = secrets.token_urlsafe(32)
        db.session.add(PasswordResetToken(
            driver_id=driver.id,
            token_hash=_hash_reset_token(token),
            expires_at=now + RESET_TOKEN_TTL,
        ))
        reset_link = request.host_url.rstrip("/") + "/driver?reset=" + token
        if driver.password_hash:
            add_outbox("email", driver.email,
                       "Noel Chauffer: reset your driver app password using "
                       "this link (it expires in 5 minutes): " + reset_link,
                       subject="Reset your Noel Chauffer password")
        else:
            add_outbox("email", driver.email,
                       "Noel Chauffer: create your driver app password using "
                       "this link (it expires in 5 minutes): " + reset_link,
                       subject="Create your Noel Chauffer driver password")
        db.session.commit()
    return jsonify({"message": RESET_REQUEST_MESSAGE})


@app.route("/api/drivers/me/reset-password", methods=["POST"])
def driver_reset_password():
    """Set a new password with a reset token. The token must match a
    stored hash, be unused, and not be expired — anything else gets
    the same generic error, with no details. On success the new
    password hash is stored, the token is marked used, any other
    outstanding tokens for the driver are invalidated, and the
    driver token rotates so old sessions stop working."""
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    password = data.get("password") or ""
    password_confirm = data.get("password_confirm") or ""
    row = None
    if token:
        row = PasswordResetToken.query.filter_by(
            token_hash=_hash_reset_token(token), used_at=None).first()
    now = utcnow()
    expires_at = row.expires_at if row else None
    if expires_at is not None and expires_at.tzinfo is None:
        # SQLite stores timezone-aware datetimes without the offset;
        # treat naive values as UTC, same as iso() does.
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not row or expires_at <= now:
        return err(RESET_INVALID_MESSAGE, 401)
    if len(password) < 6:
        return err("Password must be at least 6 characters.")
    if password != password_confirm:
        return err("Passwords do not match.")
    driver = db.session.get(Driver, row.driver_id)
    if not driver:
        return err(RESET_INVALID_MESSAGE, 401)
    driver.password_hash = generate_password_hash(password)
    row.used_at = now
    for old in PasswordResetToken.query.filter_by(
            driver_id=driver.id, used_at=None).all():
        if old.id != row.id:
            old.used_at = now
    driver.token = uuid.uuid4().hex  # rotate: old sessions stop working
    db.session.commit()
    return jsonify({"message": "Your password has been reset. "
                               "Please sign in with your new password."})


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
    # Piggyback the 1-hour reminder check (best-effort: never breaks
    # this response) so the reminder queues when the driver opens the
    # app and restores his trip, even before the reminder poll runs.
    _run_pickup_reminders_best_effort(driver_id=driver.id)
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
        "pickup_lat": booking.pickup_lat,
        "pickup_lng": booking.pickup_lng,
        "dropoff_lat": booking.dropoff_lat,
        "dropoff_lng": booking.dropoff_lng,
        "date": booking.date,
        "time": booking.time,
        "ride_type": booking.ride_type,
        "is_return": bool(getattr(booking, "is_return", False)),
        "hours": num(booking.hours),
        "vehicle_class": booking_vehicle_class(booking),
        "vehicle_class_label": class_label(booking_vehicle_class(booking)),
        "customer_name": booking.customer_name,
        "customer_phone": booking.phone,
        "route_url": route_url_for(booking),
        "route_waze_url": waze_url_for(booking),
        "free_waiting_minutes": free_waiting_minutes(booking.pickup),
        "airport_pickup": is_airport_pickup(booking.pickup),
        "status": booking.status,
        **flight_info(booking.flight_number, booking.pickup, booking.dropoff),
    }})


@app.route("/api/drivers/me/pickup-reminder", methods=["GET"])
def driver_pickup_reminder():
    """The 1-hour pickup reminder for the driver's own in-app banner.

    Runs the reminder check for this driver (queueing the outbox
    entries + alert once per acceptance), then returns the accepted
    booking whose pickup is within the next hour, if any — pickup
    time + addresses only, never miles, fare, or total. Polled by
    the driver app while the trip screen is open; the banner shows
    while the ride is about to start. The check is best-effort: it
    never breaks this response.
    """
    driver, error = require_driver()
    if error:
        return error
    _run_pickup_reminders_best_effort(driver_id=driver.id)
    booking = _due_pickup_reminder_for_driver(driver.id)
    if not booking:
        return jsonify({"reminder": None})
    return jsonify({"reminder": {
        "booking_id": booking.id,
        "date": booking.date,
        "time": booking.time,
        "pickup": booking.pickup,
        "dropoff": booking.dropoff,
        "ride_type": booking.ride_type,
        "is_return": bool(getattr(booking, "is_return", False)),
    }})


@app.route("/api/drivers/me/availability", methods=["POST"])
def driver_availability():
    driver, error = require_driver()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    if "available" not in data:
        return err("available is required.")
    # A suspended driver cannot go available (owner decision
    # 2026-11-18); going offline is always allowed.
    if data["available"] and is_driver_suspended(driver):
        return err(suspension_message(driver), 409)
    # An expired document pauses the registration (owner decision
    # 2026-11-19); going offline is always allowed.
    if data["available"] and is_driver_expiry_blocked(driver):
        return err(expiry_block_message(driver), 409)
    driver.available = bool(data["available"])
    db.session.commit()
    return jsonify({"available": driver.available})


@app.route("/api/drivers/me/offers", methods=["GET"])
def driver_offers():
    driver, error = require_driver()
    if error:
        return error
    # Fire the 10-day expiry-alert check on every offers poll (the
    # app polls while open): best-effort, never breaks this response.
    _run_expiry_alerts_best_effort(driver_id=driver.id)
    # A suspended driver gets no offers until the suspension lifts
    # (owner decision 2026-11-18). The app shows the suspension
    # notice from /api/drivers/me, so an empty list is enough here.
    if is_driver_suspended(driver):
        return jsonify([])
    # An expired document pauses the registration (owner decision
    # 2026-11-19): no offers until the driver re-uploads a valid one.
    if is_driver_expiry_blocked(driver):
        return jsonify([])
    # Owner decision 2026-11-16: job offers reach every registered
    # driver, available or offline — the "Go available" toggle no
    # longer gates offers. The time-conflict rule below still applies.
    excluded_ids = [e.booking_id for e in BookingExclusion.query.filter_by(driver_id=driver.id).all()]
    # Only PAID bookings reach drivers: status "offered" means payment
    # succeeded. Unpaid bookings (awaiting_payment) never appear here.
    # Class filtering: one-way and hourly bookings reach only drivers
    # whose car class matches the booking's class — First Class only
    # drivers with a First Class model (see
    # driver_matches_booking_class); hourly rows from before the
    # class system (no class stored) still reach every driver.
    # No double-booking: jobs overlapping a ride this driver already
    # accepted are hidden. Fetched once: the same busy windows apply
    # to every candidate offer.
    busy_windows = _active_windows(driver.id)
    query = Booking.query.filter_by(status="offered").order_by(Booking.created_at, Booking.id)
    if excluded_ids:
        query = query.filter(~Booking.id.in_(excluded_ids))
    offers = []
    for b in query.all():
        # Dispatcher-lite: a booking the owner assigned to one driver
        # appears only in that driver's offers.
        if b.assigned_driver_id is not None and b.assigned_driver_id != driver.id:
            continue
        # First Class dispatch (owner decisions 2026-11-20 ~03:00 EST
        # and 2026-11-21): a First Class booking reaches ONLY drivers
        # whose registered car is a First Class model (the twelve in
        # car_models.FIRST_CLASS_MODELS).
        # Checked on the RAW column: booking_vehicle_class() maps
        # unknown classes to "sedan", so the raw column is what
        # tells a First Class job apart. driver_matches_booking_
        # class() holds the full rule (First Class by model, the
        # other classes by sedan/suv).
        if not driver_matches_booking_class(driver, b):
            continue
        # No double-booking: hide jobs whose time overlaps a ride
        # this driver has already accepted (pickup time + driving
        # duration + buffer). A later, non-overlapping job still shows.
        candidate_window = _booking_busy_window(b)
        if candidate_window is not None and any(
                _windows_overlap(candidate_window, w) for w in busy_windows):
            continue
        # Amounts are hidden while prices are being updated (owner
        # decision 2026-11-20): offers show pickup, drop-off and
        # time only — no earnings, no toll.
        offers.append({
            "booking_id": b.id,
            "pickup": b.pickup,
            "dropoff": b.dropoff,
            "date": b.date,
            "time": b.time,
            "ride_type": b.ride_type,
            "is_return": bool(getattr(b, "is_return", False)),
            "hours": num(b.hours),
            "vehicle_class": booking_vehicle_class(b),
            "vehicle_class_label": class_label(booking_vehicle_class(b)),
            "route_url": route_url_for(b),
            "route_waze_url": waze_url_for(b),
        })
    return jsonify(offers)


@app.route("/api/drivers/me/offers/<int:booking_id>/accept", methods=["POST"])
def driver_accept(booking_id):
    driver, error = require_driver()
    if error:
        return error
    # Defense in depth: a suspended driver sees no offers, but a
    # direct accept call must fail too.
    if is_driver_suspended(driver):
        return err(suspension_message(driver), 409)
    # Same defense in depth for an expired document (owner decision
    # 2026-11-19): a blocked driver must never accept a job.
    if is_driver_expiry_blocked(driver):
        return err(expiry_block_message(driver), 409)
    if BookingExclusion.query.filter_by(booking_id=booking_id, driver_id=driver.id).first():
        return err("You have declined this booking.", 409)
    # Class match is enforced here too, so a driver can never accept a
    # booking of the other class even by calling this endpoint directly.
    # A First Class booking needs a First Class car model — an
    # E-Class driver calling accept directly gets the same 409.
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if not driver_matches_booking_class(driver, booking):
        if booking_vehicle_class(booking) == "first":
            # No model list here: twelve models qualify now (owner
            # decision 2026-11-21), too many to enumerate in an
            # error; the driver app shows the class only.
            return err("This ride needs a First Class car.", 409)
        return err("This ride is for a different vehicle class.", 409)
    # Dispatcher-lite: an owner-assigned booking can only be accepted
    # by the driver it was assigned to.
    if booking.assigned_driver_id is not None and booking.assigned_driver_id != driver.id:
        return err("This booking is assigned to another driver.", 409)
    # No double-booking: a driver with an accepted ride cannot accept
    # a second ride whose time overlaps it (owner decision 2026-11-16).
    if _driver_time_conflict(driver.id, booking):
        return err("This ride overlaps another ride you have accepted.", 409)
    # Atomic first-accept-wins: only one driver can flip offered -> accepted.
    # The reminder flag resets so the accepting driver gets his own
    # 1-hour reminder even if a previous acceptance queued one.
    rows = (db.session.query(Booking)
            .filter(Booking.id == booking_id, Booking.status == "offered")
            .update({"status": "accepted", "accepted_driver_id": driver.id,
                     "pickup_reminder_sent_at": None},
                    synchronize_session=False))
    if rows == 0:
        db.session.rollback()
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return err("Booking not found.", 404)
        return err("This booking has already been taken.", 409)
    db.session.commit()
    booking = db.session.get(Booking, booking_id)
    # The chauffeur email goes out line by line (owner 2026-11-23):
    # the SMS keeps the old one-paragraph text, but the email gets
    # the step-by-step format — plain text AND an HTML part, same
    # rows — so the customer reads every detail on its own line.
    # Subject stays the default "Noel Chauffer"; sender stays the
    # Resend default (info@noelchauffer.com since 2026-11-23).
    outbox_to_customer(
        booking,
        f"Noel Chauffer: your chauffeur is {driver.name} ({driver.phone}), "
        f"{driver.car_model} ({driver.car_colour}), plate {driver.plate}. "
        f"Pickup {booking.date} at {booking.time} from {booking.pickup}.",
        email_body=chauffeur_assigned_text(driver, booking),
        email_html=chauffeur_assigned_html(driver, booking),
    )
    add_event(booking.id, "driver_accepted",
              f"Driver {driver.name} accepted booking #{booking.id}.")
    db.session.commit()
    return jsonify({"booking": {
        "id": booking.id,
        "pickup": booking.pickup,
        "dropoff": booking.dropoff,
        "pickup_lat": booking.pickup_lat,
        "pickup_lng": booking.pickup_lng,
        "dropoff_lat": booking.dropoff_lat,
        "dropoff_lng": booking.dropoff_lng,
        "date": booking.date,
        "time": booking.time,
        "ride_type": booking.ride_type,
        "is_return": bool(getattr(booking, "is_return", False)),
        "vehicle_class": booking_vehicle_class(booking),
        "vehicle_class_label": class_label(booking_vehicle_class(booking)),
        "customer_name": booking.customer_name,
        "customer_phone": booking.phone,
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
    changed = False
    if not BookingExclusion.query.filter_by(booking_id=booking_id, driver_id=driver.id).first():
        db.session.add(BookingExclusion(booking_id=booking_id, driver_id=driver.id))
        changed = True
    # If the assigned driver declines, the assignment clears so the
    # booking broadcasts to the other drivers again instead of
    # sitting invisible to everyone.
    if booking.assigned_driver_id == driver.id:
        booking.assigned_driver_id = None
        add_event(booking.id, "assignment_cleared",
                  f"Driver {driver.name} declined booking #{booking.id}; "
                  "owner assignment cleared and the booking is broadcast again.")
        changed = True
    if changed:
        db.session.commit()
    return jsonify({"excluded": True, "booking_id": booking_id})


# Arrival / completion proximity gates (owner decision 2026-11-17,
# fraud prevention): a driver must actually be at the pickup to mark
# arrived, and at the drop-off to complete the trip. Hourly rides
# have no drop-off, so their completion stays ungated.
PROXIMITY_GATE_METERS = 100.0
METERS_PER_MILE = 1609.344


def proximity_gate_error(booking, event, data, driver=None):
    """Error message when a gated stage advance is attempted from
    outside 100 m of the relevant end, else None.

    Only 'arrived' and 'complete' are gated. A booking without stored
    coordinates for the relevant end cannot be verified, so the
    advance is allowed (old and test rides keep working). A request
    that carries no position is likewise allowed: the driver app
    requires location before it sends a gated advance and explains
    when location is unavailable, so the no-position case is the
    client's to enforce; the server rejects any position it IS
    given that is out of range.

    Owner decision 2026-11-20 (voice call): the gate does not apply
    to the owner (Azher Mohammed) or Sana Baga — their arrived /
    complete advances are never blocked, with or without a position.
    Every other driver keeps the 100 m gate exactly as it is.
    """
    if event == "arrived":
        target_lat, target_lng = booking.pickup_lat, booking.pickup_lng
        message = "You must be at the pickup location to mark arrived."
    elif event == "complete":
        if booking.ride_type == "hourly":
            return None
        target_lat, target_lng = booking.dropoff_lat, booking.dropoff_lng
        message = "You must be at the drop-off location to complete the trip."
    else:
        return None
    if driver is not None and location_exempt_for(driver.email):
        return None
    if target_lat is None or target_lng is None:
        return None
    if data.get("lat") is None or data.get("lng") is None:
        return None
    try:
        lat = float(data["lat"])
        lng = float(data["lng"])
    except (TypeError, ValueError):
        return None
    distance_m = (geo_module.haversine_miles(lat, lng, target_lat, target_lng)
                  * METERS_PER_MILE)
    if distance_m > PROXIMITY_GATE_METERS:
        return message
    return None


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
        gate_err = proximity_gate_error(booking, event, data, driver=driver)
        if gate_err:
            return err(gate_err, 409)
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
        gate_err = proximity_gate_error(booking, event, data, driver=driver)
        if gate_err:
            return err(gate_err, 409)
        waiting_minutes = int(data.get("waiting_minutes") or 0)
        booking.waiting_minutes = max(0, waiting_minutes)
        booking.waiting_charge = waiting_charge(booking.pickup, booking.waiting_minutes)
        # Extra miles driven beyond the booked route (one-way rides
        # only). Priced with the SAME formula as the booked fare:
        # added fare only (no gratuity, no tax) to the customer
        # total, driver rate per mile to the driver. Toll unchanged.
        extra_dec = Decimal("0")
        if data.get("extra_miles") is not None:
            if booking.ride_type != "one_way":
                return err("Extra miles apply to one-way rides only.", 400)
            try:
                extra_dec = miles_1dp(data["extra_miles"])
            except Exception:
                return err("extra_miles must be a number.")
            if extra_dec < 0 or extra_dec > 500:
                return err("extra_miles must be between 0 and 500.")
        if extra_dec > 0 and booking_vehicle_class(booking) == "first":
            # Extra miles have no First Class rate: the legacy
            # extra-distance formula only knows sedan/suv rates and
            # the Blacklane engine has no extra-miles step. Refuse
            # cleanly (400) instead of crashing on completion; the
            # driver is still paid the flat slab for the booked miles.
            return err("Extra miles cannot be added to a First Class ride yet.", 400)
        if extra_dec > 0:
            extra = compute_extra_distance(extra_dec, booking_vehicle_class(booking))
            booking.extra_miles = extra_dec
            booking.extra_distance_charge = extra["total"]
            booking.fare_total = money(booking.fare_total + extra["total"])
            booking.fare = money(booking_fare(booking) + extra["fare"])
            booking.gratuity = money(booking.gratuity + extra["gratuity"])
            booking.tax = money(booking_tax(booking) + extra["tax"])
            booking.driver_earnings = money(booking.driver_earnings + extra["driver_addition"])
        booking.status = "completed"
        booking.completed_at = utcnow()
        # Driver referral credit (owner decision 2026-11-18): if this
        # driver registered via a referral link, the referrer earns
        # $5 for this completed job, up to the driver's first 15
        # jobs. Same transaction as the completion (the caller
        # commits below); a silent no-op without a referrer.
        record_driver_referral_credit(booking, driver)
        total = invoice_total(booking.fare_total, booking.waiting_charge)
        outbox_to_customer(
            booking,
            # Amounts are hidden while prices are being updated (owner
            # decision 2026-11-20): no invoice figures in the message.
            "Noel Chauffer: thank you for riding with us. Your ride is complete.",
        )
        add_event(booking.id, "trip_completed",
                  f"Booking #{booking.id} completed. Invoice total ${total} "
                  f"(fare ${booking.fare_total} + waiting ${booking.waiting_charge})"
                  + (f", extra distance {extra_dec} miles (${booking.extra_distance_charge})" if extra_dec > 0 else "")
                  + ".")
        # Uber-like capture: the final fare (fare + waiting) is
        # charged automatically from the saved card — the customer
        # does nothing. A failed capture never blocks the completed
        # ride; the payment is marked capture_shortfall for the
        # owner to follow up. Test-mode bookings have no real hold.
        _ok, _note = _settle_booking_payment(booking, total)
        # Amounts are hidden from the driver while prices are being
        # updated (owner decision 2026-11-20): no invoice in the
        # driver's trip-complete response.
    elif event == "cancel":
        if booking.status not in ("accepted", "en_route", "arrived"):
            return err("Cannot cancel a ride in this state.", 409)
        # Owner rule 2026-11-18 (SUPERSEDES the 2026-11-17 lock that
        # blocked every cancel inside 2 hours): once pickup is
        # within 2 hours, the driver CAN still cancel, but MUST give
        # a reason, and the reason is judged automatically — no
        # manual review. A fault judgment blocks the driver's app
        # for 48 hours, except Azher Mohammed and Sana Baga, who
        # are exempt (owner decision 2026-11-24); a genuine
        # emergency never blocks. More than 2 hours out, cancelling works exactly as before: no reason
        # required, no judgment, no suspension. In EVERY case the
        # job goes back to the other drivers automatically and the
        # customer is never told about the cancel or re-dispatch.
        locked = driver_cancel_locked(booking.date, booking.time)
        emergency = None
        if locked:
            reason = (data.get("reason") or "").strip()
            detail = (data.get("detail") or "").strip()
            if reason not in EMERGENCY_CANCEL_REASON_LABELS:
                return err("Pickup is within 2 hours, so cancelling "
                           "needs a reason. Please pick a reason.", 409)
            if reason == "other" and not detail:
                return err("Please say what happened.", 409)
            judgment, flagged = judge_emergency_cancel(reason, detail)
            now = utcnow()
            # Owner decision 2026-11-24: Azher Mohammed and Sana
            # Baga are exempt from the 48-hour fault suspension — a
            # fault cancel by either of them still re-dispatches
            # the job, but no suspension is stored.
            suspended_until = (now + timedelta(hours=SUSPENSION_HOURS)
                               if judgment == "fault"
                               and not suspension_exempt_for(driver.email)
                               else None)
            redispatched_ids = []
            if suspended_until is not None:
                driver.suspended_until = suspended_until
                driver.available = False
                redispatched_ids = _redispatch_blocked_driver_jobs(
                    driver, booking.id)
            db.session.add(EmergencyCancel(
                booking_id=booking.id,
                driver_id=driver.id,
                driver_name=driver.name,
                reason=reason,
                reason_label=EMERGENCY_CANCEL_REASON_LABELS[reason],
                detail=detail or None,
                judgment=judgment,
                flagged=flagged,
                suspended_until=suspended_until,
            ))
            emergency = {
                "judgment": judgment,
                "flagged": flagged,
                "suspended_until": iso(suspended_until),
                "redispatched_booking_ids": redispatched_ids,
            }
        booking.status = "offered"
        booking.accepted_driver_id = None
        booking.assigned_driver_id = None
        booking.driver_lat = None
        booking.driver_lng = None
        # The reminder flag resets with the re-dispatch, so the next
        # driver to accept gets his own 1-hour reminder.
        booking.pickup_reminder_sent_at = None
        if not BookingExclusion.query.filter_by(booking_id=booking_id, driver_id=driver.id).first():
            db.session.add(BookingExclusion(booking_id=booking_id, driver_id=driver.id))
        # Payment was taken before dispatch, so it is kept; the booking
        # goes back to the other drivers automatically.
        if locked:
            add_event(booking.id, "emergency_cancel",
                      f"Driver {driver.name} cancelled booking #{booking.id} within 2 hours of pickup. "
                      f"Reason: {EMERGENCY_CANCEL_REASON_LABELS[reason]}"
                      + (f" — {detail}" if detail else "")
                      + f". Automatic judgment: {judgment}"
                      + (" (flagged for owner review)" if flagged else "")
                      + (f"; driver app blocked until {iso(suspended_until)}" if suspended_until is not None else "; no suspension")
                      + (f"; {len(redispatched_ids)} other job(s) sent back to other drivers: {redispatched_ids}" if redispatched_ids else "")
                      + ". Sent back to other drivers. Payment kept.")
            response_extra["emergency_cancel"] = emergency
        else:
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
        # No-show keeps the full price: capture the authorized hold
        # in full. A failed capture marks the payment
        # capture_shortfall for the owner to follow up.
        _settle_booking_payment(booking, booking.fare_total)
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
    # Only completed, non-refunded trips count toward payout weeks.
    # Amounts are hidden while prices are being updated (owner
    # decision 2026-11-20): rides list without amounts, weeks keep
    # dates + paid status only — never miles, fares, or totals.
    eligible = _payout_eligible(rides)
    weeks = [{k: v for k, v in summary.items() if k != "total_earnings"}
             for summary, _ in _group_payout_weeks(eligible)]
    ride_rows = []
    for b in eligible:
        w = _booking_week(b)
        ride_rows.append({
            "id": b.id,
            "date": b.date,
            "route": f"{b.pickup} to {b.dropoff}" if b.dropoff else b.pickup,
            "vehicle_class": booking_vehicle_class(b),
            "vehicle_class_label": class_label(booking_vehicle_class(b)),
            "completed_date": completion_date(b.completed_at, b.created_at).isoformat(),
            "week_start": w["start"].isoformat(),
            "week_end": w["end"].isoformat(),
            "due_date": w["due_date"].isoformat(),
            "payout_paid": bool(b.payout_paid),
            "payout_status": "paid" if b.payout_paid else "unpaid",
        })
    return jsonify({
        "completed_rides": len(eligible),
        "weeks": weeks,
        "rides": ride_rows,
    })


# ------------------------------------------------- driver payout setup ---
# Driver payout setup for Uber-like payments (owner decisions
# 2026-11-20, voice calls). Two separate pieces:
# - WEEKLY payout (free default, due 7 days after the week starts):
#   needs a valid BANK account — routing number + account number are
#   COMPULSORY. The driver enters them in Stripe's hosted Connect
#   onboarding flow, so the details go to Stripe only and are never
#   stored by Noel. (Drivers registered before this also have an
#   encrypted bank account on file from registration; that counts
#   as bank-on-file too.)
# - INSTANT cash-out (driver's choice, 1.5% Stripe fee): needs a
#   linked DEBIT card on the Connect account. Debit card alone
#   enables instant, but weekly payout needs the bank account.
# Without a linked card, only the free weekly payout is available.

def _driver_payout_setup(driver):
    """Current payout-setup state for a driver. Bank details are
    never returned beyond the masked last 4; debit cards are brand
    / last 4 / expiry only. Stripe is consulted live when a Connect
    account exists and keys are configured; otherwise the stored
    registration bank is what counts."""
    account_id = driver.stripe_connect_account_id
    payouts_enabled = False
    details_submitted = False
    debit_cards = []
    if account_id and stripe_payments.stripe_configured():
        try:
            account = stripe_payments.retrieve_account(account_id)
            payouts_enabled = bool(account.get("payouts_enabled"))
            details_submitted = bool(account.get("details_submitted"))
        except stripe_payments.StripePaymentsError:
            pass
        try:
            debit_cards = stripe_payments.list_payout_cards(account_id)
        except stripe_payments.StripePaymentsError:
            debit_cards = []
    bank_on_file = bool(driver.bank_last4)
    return {
        "connect_account": bool(account_id),
        "payouts_enabled": payouts_enabled,
        "details_submitted": details_submitted,
        "bank_on_file": bank_on_file,
        "bank_masked": bank_masked(driver),
        "debit_cards": debit_cards,
        "debit_card_linked": bool(debit_cards),
        "weekly_payout_available": bool(payouts_enabled or bank_on_file),
        "instant_payout_available": bool(payouts_enabled and debit_cards),
        "instant_payout_fee_rate": float(stripe_payments.INSTANT_PAYOUT_FEE_RATE),
    }


def _driver_payout_ready(driver):
    """A driver can receive weekly payouts only when payout setup is
    complete: a valid bank account on file (registration bank, or a
    Stripe Connect account with payouts enabled)."""
    return _driver_payout_setup(driver)["weekly_payout_available"]


def _driver_connect_onboarding(driver):
    """Create the driver's Stripe Connect account if needed and
    return a fresh hosted onboarding link. This is where the driver
    enters his bank routing + account numbers (compulsory there) and
    links a debit card — Stripe's hosted flow, so the details go to
    Stripe only and are never stored by Noel."""
    if not stripe_payments.stripe_configured():
        return None, err("Payouts are not set up yet. Please try again later.", 503)
    try:
        if not driver.stripe_connect_account_id:
            account = stripe_payments.create_connect_account(driver.email)
            driver.stripe_connect_account_id = account["id"]
            db.session.commit()
        link = stripe_payments.create_account_link(
            driver.stripe_connect_account_id,
            return_url="https://noelchauffer.com/driver#payout-setup-done",
            refresh_url="https://noelchauffer.com/driver#payout-setup",
        )
    except stripe_payments.StripePaymentsError as exc:
        return None, err(exc.user_message, 502)
    status = _driver_payout_setup(driver)
    status["onboarding_url"] = link["url"]
    return status, None


@app.route("/api/drivers/me/payout-setup", methods=["GET"])
def driver_payout_setup_status():
    driver, error = require_driver()
    if error:
        return error
    return jsonify(_driver_payout_setup(driver))


@app.route("/api/drivers/me/payout-setup", methods=["POST"])
def driver_payout_setup_start():
    """Start (or resume) payout setup: returns Stripe's hosted
    onboarding link where the driver enters his bank routing +
    account numbers and links a debit card."""
    driver, error = require_driver()
    if error:
        return error
    status, error = _driver_connect_onboarding(driver)
    if error:
        return error
    return jsonify(status)


@app.route("/api/drivers/me/payout-setup/link-card", methods=["POST"])
def driver_payout_link_card():
    """Link a debit card as the instant-payout destination. The card
    is added in Stripe's hosted onboarding flow (same link as payout
    setup) — Noel never sees the card details. Without a linked
    card, only the free weekly payout is available."""
    driver, error = require_driver()
    if error:
        return error
    status, error = _driver_connect_onboarding(driver)
    if error:
        return error
    return jsonify(status)


@app.route("/api/drivers/me/instant-payout", methods=["POST"])
def driver_instant_payout():
    """Cash out all unpaid completed-ride earnings at once to the
    driver's linked debit card via Stripe Instant Payouts (1.5% fee
    on the driver's side). The money first moves from the platform
    to the driver's Connect account, then out instantly. Cashed-out
    rides are marked payout_paid so the weekly cycle never pays them
    twice. A failed payout records a failed row and marks nothing
    paid, so the driver can retry."""
    driver, error = require_driver()
    if error:
        return error
    if bookings_paused():
        return err("Instant cash-out is paused while prices are being updated. Please check back soon.", 503)
    if not stripe_payments.stripe_configured():
        return err("Payouts are not set up yet. Please try again later.", 503)
    if not driver.stripe_connect_account_id:
        return err("Set up payouts first — link your bank account and debit card.", 409)
    try:
        account = stripe_payments.retrieve_account(driver.stripe_connect_account_id)
    except stripe_payments.StripePaymentsError as exc:
        return err(exc.user_message, 502)
    if not account.get("payouts_enabled"):
        return err("Payouts are not enabled yet. Please finish payout setup first.", 409)
    try:
        cards = stripe_payments.list_payout_cards(driver.stripe_connect_account_id)
    except stripe_payments.StripePaymentsError as exc:
        return err(exc.user_message, 502)
    if not cards:
        return err("Link an eligible debit card first — without one, only the "
                   "free weekly payout is available.", 409)
    rides = (Booking.query.filter_by(accepted_driver_id=driver.id, status="completed").all())
    eligible = [b for b in _payout_eligible(rides) if not b.payout_paid]
    gross = sum((money(b.driver_earnings) for b in eligible), Decimal("0.00"))
    if gross <= 0:
        return err("No unpaid earnings to cash out.", 409)
    gross_cents = stripe_payments.to_cents(gross)
    fee = stripe_payments.to_dollars(stripe_payments.instant_payout_fee_cents(gross_cents))
    net = stripe_payments.to_dollars(stripe_payments.instant_payout_net_cents(gross_cents))
    transfer_id = None
    try:
        transfer = stripe_payments.create_transfer(
            gross_cents, driver.stripe_connect_account_id)
        transfer_id = transfer["id"]
        payout = stripe_payments.create_instant_payout(
            driver.stripe_connect_account_id, gross_cents)
    except stripe_payments.StripePaymentsError as exc:
        record = InstantPayout(
            driver_id=driver.id, amount=gross, fee=fee, net=net,
            stripe_transfer_id=transfer_id, status="failed",
            booking_ids=",".join(str(b.id) for b in eligible))
        db.session.add(record)
        db.session.commit()
        return err(exc.user_message, 502)
    for b in eligible:
        b.payout_paid = True
    record = InstantPayout(
        driver_id=driver.id, amount=gross, fee=fee, net=net,
        stripe_transfer_id=transfer_id,
        stripe_payout_id=payout["id"], status="succeeded",
        booking_ids=",".join(str(b.id) for b in eligible))
    db.session.add(record)
    db.session.commit()
    return jsonify({"instant_payout": {
        "id": record.id, "amount": num(gross), "fee": num(fee),
        "net": num(net), "status": "succeeded",
        "booking_ids": [b.id for b in eligible]},
        "driver_receives": num(net)})


# ------------------------------------------------------- driver tax info ---
# Display-only tax information page for drivers (owner decision
# 2026-11-20, voice call: "dikhane wala" — an info page, NOT a fillable
# form). No fields, no SSN/TIN collection, no uploads, no IRS filing.
# The page shows the facts and the driver's own earnings for the year;
# the actual 1099 is issued by Noel Chauffer (Siahsolutions Inc).
TAX_YEAR = 2026
TAX_FORMS_AVAILABLE_BY = date(2027, 1, 31)
TAX_STATE_FILING_DEADLINE = date(2027, 4, 15)
TAX_NEC_THRESHOLD = Decimal("2000.00")


@app.route("/api/drivers/me/tax-info", methods=["GET"])
def driver_tax_info():
    driver, error = require_driver()
    if error:
        return error
    rides = (Booking.query.filter_by(accepted_driver_id=driver.id, status="completed").all())
    # Only completed, non-refunded trips count, and only those completed
    # in the tax year (America/New_York completion date).
    eligible = _payout_eligible(rides)
    year_rides = [b for b in eligible
                  if completion_date(b.completed_at, b.created_at).year == TAX_YEAR]
    # Amounts are hidden while prices are being updated (owner
    # decision 2026-11-20); the $2,000 1099-NEC threshold stays.
    return jsonify({
        "tax_year": TAX_YEAR,
        "forms_available_by": TAX_FORMS_AVAILABLE_BY.isoformat(),
        "state_filing_deadline": TAX_STATE_FILING_DEADLINE.isoformat(),
        "nec_threshold": num(TAX_NEC_THRESHOLD),
        "forms": [
            {
                "code": "1099-NEC",
                "title": "1099-NEC — Nonemployee Compensation",
                "description": "Reports what you earned as an independent contractor driving with Noel Chauffer. You receive one if your 2026 earnings are $2,000 or more.",
            },
            {
                "code": "1099-K",
                "title": "1099-K — Payment Card and Third-Party Network Transactions",
                "description": "Reports payments made to you through a card or payment network, if any apply to you.",
            },
        ],
        "issuer": "Noel Chauffer (Siahsolutions Inc)",
        "filing_note": "Noel Chauffer issues your 1099. This app does not file taxes for you — file your return yourself, or with an accountant or a tax-filing service.",
        "completed_rides_year": len(year_rides),
    })


# ------------------------------------------------------------------ owner ---

@app.route("/api/owner/login", methods=["POST"])
def owner_login():
    data = request.get_json(silent=True) or {}
    if str(data.get("pin")) != OWNER_PIN:
        return err("Wrong PIN.", 401)
    session["owner"] = True
    session["owner_authed_at"] = int(datetime.now(timezone.utc).timestamp())
    return jsonify({"ok": True})


@app.route("/api/owner/logout", methods=["POST"])
def owner_logout():
    session.pop("owner", None)
    session.pop("owner_authed_at", None)
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
            # paid_ids). New rides store $0.00 tax (removed
            # 2026-11-17); only pre-removal rides contribute. The
            # field stays in the API for the stored records; the
            # dashboard no longer shows a Tax card.
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


# --- Profit tab (owner decision 2026-11-23, voice call) ----------------------
# "owner dashboard mein ek profit wala hissa banao... khali profit ka
# hissa... to mere ko idea ho jaye na, main kitna bana raha hoon" — a
# DEDICATED Profit tab, separate from Money and Dashboard (owner
# 2026-11-23 ~06:06 EST: "profit alag, profit ke alag hisse mein na").
# Inside it, four sub-tabs (owner 2026-11-23 ~06:07 EST): DAILY,
# WEEKLY, MONTHLY and TILL-DATE ("ELD") — whichever sub-tab is open
# shows that period's profit plus that period's rides (customer paid,
# driver got, profit). "Today at a glance" on the Dashboard tab is
# untouched.
#
# Only completed rides whose payment actually landed count: status
# "completed" + a payment with status "succeeded" (test mode) or
# "captured" (live Stripe) + not refunded. Pending, awaiting-payment
# and cancelled rides earn nothing yet, so they are left out.
# Per ride, profit reuses booking_profit(): fare_total + waiting -
# driver_earnings - stored tax. Toll never counts as profit: it is
# inside BOTH the customer total and the driver earnings (slab pay +
# toll), so it cancels out. Rides are bucketed on their completion
# date (America/New_York, same rule as the daily summary and the
# payout weeks): daily = today, weekly = the current payout week
# (Mon-Sun, anchored 2026-11-16), monthly = the current calendar
# month, till-date = everything.

def _profit_paid_booking_ids():
    return {p.booking_id for p in Payment.query.filter(
        Payment.status.in_(("succeeded", "captured"))).all()}


def _profit_bucket(eligible):
    """Totals for a list of eligible (completed + paid) bookings."""
    customer_paid = sum((money(b.fare_total) + money(b.waiting_charge)
                         for b in eligible), Decimal("0.00"))
    driver_pay = sum((money(b.driver_earnings) for b in eligible),
                     Decimal("0.00"))
    profit = sum((booking_profit(b) for b in eligible), Decimal("0.00"))
    return {
        "profit": num(profit),
        "customer_paid": num(customer_paid),
        "driver_pay": num(driver_pay),
        "rides": len(eligible),
    }


def _profit_ride_row(b, done_date):
    return {
        "id": b.id,
        "date": done_date.isoformat(),
        "route": f"{b.pickup} to {b.dropoff}" if b.dropoff else b.pickup,
        "customer_name": b.customer_name,
        "vehicle_class_label": class_label(booking_vehicle_class(b)),
        "customer_paid": num(money(b.fare_total) + money(b.waiting_charge)),
        "driver_earnings": num(b.driver_earnings),
        "profit": num(booking_profit(b)),
        "status": b.status,
    }


PROFIT_PERIODS = ("daily", "weekly", "monthly", "tilldate")


@app.route("/api/owner/profit", methods=["GET"])
def owner_profit():
    error = require_owner()
    if error:
        return error
    period = (request.args.get("period") or "tilldate").strip().lower()
    if period not in PROFIT_PERIODS:
        period = "tilldate"
    paid_ids = _profit_paid_booking_ids()
    eligible = [b for b in _payout_eligible(Booking.query.all())
                if b.id in paid_ids]
    # Newest completion first; a ride with no completion timestamp
    # (pre-timestamp rows) falls back to its creation time.
    dated = []
    for b in eligible:
        try:
            done = completion_date(b.completed_at, b.created_at)
        except ValueError:
            continue
        dated.append((done, b))
    dated.sort(key=lambda item: (item[0], item[1].id), reverse=True)
    today = _today_ny()
    week = week_for(today)
    periods = {
        "daily": _profit_bucket([b for d, b in dated if d == today]),
        "weekly": _profit_bucket([b for d, b in dated
                                  if week["start"] <= d <= week["end"]]),
        "monthly": _profit_bucket([b for d, b in dated
                                   if d.year == today.year
                                   and d.month == today.month]),
        "tilldate": _profit_bucket([b for _, b in dated]),
    }
    if period == "daily":
        active = [(d, b) for d, b in dated if d == today]
    elif period == "weekly":
        active = [(d, b) for d, b in dated
                  if week["start"] <= d <= week["end"]]
    elif period == "monthly":
        active = [(d, b) for d, b in dated
                  if d.year == today.year and d.month == today.month]
    else:
        active = dated
    # Per-ride rows, 10 per page like the Rides tab.
    try:
        page = int(request.args.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)
    try:
        per_page = int(request.args.get("per_page") or 10)
    except (TypeError, ValueError):
        per_page = 10
    per_page = min(max(per_page, 1), 100)
    total_rides = len(active)
    pages = (total_rides + per_page - 1) // per_page if total_rides else 0
    if pages and page > pages:
        page = pages
    rows = [_profit_ride_row(b, d)
            for d, b in active[(page - 1) * per_page:page * per_page]]
    return jsonify({
        "period": period,
        "periods": periods,
        "week_start": week["start"].isoformat(),
        "week_end": week["end"].isoformat(),
        "month_label": today.strftime("%B %Y"),
        "rides": rows,
        "page": page,
        "per_page": per_page,
        "total_rides": total_rides,
        "pages": pages,
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
        "is_return": bool(getattr(b, "is_return", False)),
        "vehicle_class": booking_vehicle_class(b),
        "vehicle_class_label": class_label(booking_vehicle_class(b)),
        "customer_total": num(b.fare_total),
        "fare": num(booking_fare(b)),
        "tax": num(booking_tax(b)),
        "driver_earnings": num(b.driver_earnings),
        "toll": num(b.toll),
        "gratuity": num(b.gratuity),
        "booking_fee": num(b.booking_fee),
        "referral_discount": num(getattr(b, "referral_discount", None)),
        "referral_code_used": b.referral_code_used,
        "waiting_charge": num(b.waiting_charge),
        "extra_miles": num(b.extra_miles),
        "extra_distance_charge": num(b.extra_distance_charge),
        "profit": num(booking_profit(b)),
        "driver_name": b.accepted_driver.name if b.accepted_driver else None,
        "assigned_driver_id": b.assigned_driver_id,
        "assigned_driver_name": b.assigned_driver.name if b.assigned_driver else None,
        "payout_paid": bool(b.payout_paid),
    }
    row.update(flight_info(b.flight_number, b.pickup, b.dropoff))
    return row


@app.route("/api/owner/bookings", methods=["GET"])
def owner_bookings():
    error = require_owner()
    if error:
        return error
    # Server-side search + pagination (owner decision 2026-11-19):
    # at 10,000 rides the dashboard must NOT load every booking at
    # once. ?q= searches the database (customer name, phone, pickup,
    # drop-off, driver name, booking number/ID, date, status) and the
    # list comes back one page at a time, newest first, 50 per page.
    # A bare call (no ?q= and no ?page=) keeps returning the plain
    # list, so older callers keep working unchanged.
    q = (request.args.get("q") or "").strip()
    page_raw = request.args.get("page")
    per_page_raw = request.args.get("per_page")
    paginated = page_raw is not None or bool(q)
    try:
        page = int(page_raw) if page_raw is not None else 1
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)
    try:
        per_page = int(per_page_raw) if per_page_raw is not None else 50
    except (TypeError, ValueError):
        per_page = 50
    per_page = min(max(per_page, 1), 100)

    query = Booking.query
    if q:
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions = [
            Booking.customer_name.ilike(like, escape="\\"),
            Booking.phone.ilike(like, escape="\\"),
            Booking.pickup.ilike(like, escape="\\"),
            Booking.dropoff.ilike(like, escape="\\"),
            Booking.status.ilike(like, escape="\\"),
            Booking.date.ilike(like, escape="\\"),
        ]
        # Booking number/ID: "#123" or "123".
        digits = q.lstrip("#")
        if digits.isdigit():
            conditions.append(Booking.id == int(digits))
        # Driver name: whoever accepted the ride or was assigned it.
        driver_ids = db.session.query(Driver.id).filter(Driver.name.ilike(like, escape="\\"))
        conditions.append(Booking.accepted_driver_id.in_(driver_ids))
        conditions.append(Booking.assigned_driver_id.in_(driver_ids))
        query = query.filter(or_(*conditions))
    query = query.order_by(Booking.created_at.desc(), Booking.id.desc())
    if not paginated:
        return jsonify([_owner_booking_row(b) for b in query.all()])
    total = query.count()
    pages = (total + per_page - 1) // per_page if total else 0
    if pages and page > pages:
        page = pages
    bookings = query.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        "bookings": [_owner_booking_row(b) for b in bookings],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "q": q,
    })


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
        "is_return": bool(getattr(booking, "is_return", False)),
        "hours": num(booking.hours),
        "miles": num(booking.miles),
        "referral_code_used": booking.referral_code_used,
        "waiting_minutes": booking.waiting_minutes,
        "extra_miles": num(booking.extra_miles),
        "extra_distance_charge": num(booking.extra_distance_charge),
        "assigned_driver_id": booking.assigned_driver_id,
        "assigned_driver_name": booking.assigned_driver.name if booking.assigned_driver else None,
        "completed_at": iso(booking.completed_at),
        "payout_paid": bool(booking.payout_paid),
        "invoice": {
            "fare_total": num(booking.fare_total),
            "waiting_charge": num(booking.waiting_charge),
            "extra_distance_charge": num(booking.extra_distance_charge),
            "total": num(invoice_total(booking.fare_total, booking.waiting_charge)),
        },
        "payments": [{
            "id": p.id, "amount": num(p.amount), "status": p.status,
            "test": p.test, "last4": p.last4, "brand": p.brand,
            "stripe_test_id": p.stripe_test_id,
            "stripe_payment_intent_id": p.stripe_payment_intent_id,
            "captured_amount": num(p.captured_amount),
            "created_at": iso(p.created_at),
        } for p in booking.payments],
        "events": [{
            "id": e.id, "type": e.type, "message": e.message, "created_at": iso(e.created_at),
        } for e in sorted(booking.events, key=lambda e: e.id)],
        # Emergency cancels inside the 2-hour window (owner decision
        # 2026-11-18): read-only information for the owner — reason,
        # automatic judgment, suspension or not. No action required,
        # no approval step.
        "emergency_cancels": [{
            "id": c.id,
            "driver_id": c.driver_id,
            "driver_name": c.driver_name,
            "reason": c.reason,
            "reason_label": c.reason_label,
            "detail": c.detail,
            "judgment": c.judgment,
            "flagged": bool(c.flagged),
            "suspended_until": iso(_as_aware(c.suspended_until)),
            "created_at": iso(c.created_at),
        } for c in EmergencyCancel.query.filter_by(booking_id=booking.id).order_by(EmergencyCancel.id).all()],
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
    try:
        recompute_booking_fare(booking)
    except ValueError as exc:
        # A ride booked before the slab change, over 400 miles, has
        # no slab to reprice with (owner decision 2026-11-20).
        return err(str(exc))
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


@app.route("/api/owner/bookings/<int:booking_id>/assign", methods=["POST"])
def owner_assign_booking(booking_id):
    """Dispatcher-lite: assign a paid, not-yet-accepted booking to ONE
    specific driver. The booking then appears only in that driver's
    offers. Passing driver_id null clears the assignment and the
    booking broadcasts to all matching drivers again (the default).
    Only while status is "offered": once a driver has accepted, the
    assignment no longer applies."""
    error = require_owner()
    if error:
        return error
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    if booking.status != "offered":
        return err("Only a paid booking waiting for a driver can be assigned.", 409)
    data = request.get_json(silent=True) or {}
    driver_id = data.get("driver_id")
    if driver_id is None:
        booking.assigned_driver_id = None
        add_event(booking.id, "assignment_cleared",
                  f"Owner cleared the driver assignment for booking #{booking.id}; "
                  "the booking is broadcast to all matching drivers.")
        db.session.commit()
        return jsonify({"booking": _owner_booking_row(booking)})
    try:
        driver_id = int(driver_id)
    except (TypeError, ValueError):
        return err("driver_id must be an integer.")
    driver = db.session.get(Driver, driver_id)
    if not driver:
        return err("Driver not found.", 404)
    if not driver_matches_booking_class(driver, booking):
        return err("This driver’s vehicle class does not match the booking.", 409)
    # No double-booking: the owner cannot assign a ride that overlaps
    # a ride this driver has already accepted (owner decision 2026-11-16).
    if _driver_time_conflict(driver.id, booking):
        return err("This driver already has a ride at that time.", 409)
    booking.assigned_driver_id = driver.id
    add_event(booking.id, "booking_assigned",
              f"Owner assigned booking #{booking.id} to driver {driver.name}.")
    db.session.commit()
    return jsonify({"booking": _owner_booking_row(booking)})


@app.route("/api/owner/payouts", methods=["GET"])
def owner_payouts():
    """Per-driver, per-week payout totals. Owner PIN session required.

    Only completed, non-refunded trips appear. Each week's payout
    comes due 7 days after the week starts (week 0 due Nov 23,
    week 1 due Nov 30, week 2 due Dec 7, ...); a week is paid when
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
            "payout_ready": _driver_payout_ready(driver) if driver else False,
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
    # Weekly payouts need a valid bank account (owner decision
    # 2026-11-20): a driver who has not completed payout setup —
    # no bank routing + account number on file — cannot receive a
    # weekly payout, so the week cannot be marked paid.
    if not _driver_payout_ready(driver):
        return err("This driver has not completed payout setup yet — a valid "
                   "bank routing number and account number are required before "
                   "a weekly payout can be marked paid.", 409)
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
        "sent_at": iso(m.sent_at),
    } for m in messages])


@app.route("/api/owner/run-pickup-reminders", methods=["POST"])
def run_pickup_reminders_endpoint():
    """Trigger the 1-hour pickup reminder check for every driver.

    Called by the owner dashboard when it loads (fire-and-forget),
    so reminders queue whenever the owner has the dashboard open —
    no new infrastructure, no billing change. For fully automatic
    firing without anyone having an app open, point a scheduler at
    this endpoint (Render cron jobs have no free-plan guarantee, so
    no scheduler is configured by this code — the owner sets one up
    only if he wants it):

      POST https://noelchauffer.com/api/owner/run-pickup-reminders
      Authorization: Bearer <PICKUP_REMINDER_CRON_SECRET>
      every 5 minutes

    with PICKUP_REMINDER_CRON_SECRET set to the same value in
    Render's environment. Any external scheduler (Render cron job,
    cron-job.org, UptimeRobot) works the same way.

    Auth: the owner session, OR the bearer secret above. With
    PICKUP_REMINDER_CRON_SECRET unset, bearer auth is disabled and
    only the owner session works. The check is idempotent: repeated
    triggers never queue a second reminder for the same acceptance.
    """
    cron_secret = os.environ.get("PICKUP_REMINDER_CRON_SECRET") or ""
    auth = request.headers.get("Authorization", "")
    bearer_ok = bool(cron_secret) and hmac.compare_digest(auth, "Bearer " + cron_secret)
    if not bearer_ok:
        error = require_owner()
        if error:
            return error
    reminded = run_pickup_reminders()
    return jsonify({"reminded": reminded})


def _expiring_document_rows(today):
    """Every stored document expiring within the next 10 days, plus
    every expired one — expired means that driver's registration is
    paused until they upload a new document. Earliest expiry first.
    Shared by the owner dashboard endpoint and the daily summary
    email (owner decision 2026-11-19)."""
    rows = []
    for doc in (DriverDocument.query
                .filter(DriverDocument.expires_on.isnot(None))
                .order_by(DriverDocument.expires_on, DriverDocument.id)
                .all()):
        days_left = (doc.expires_on - today).days
        if days_left > EXPIRY_ALERT_DAYS:
            continue
        driver = db.session.get(Driver, doc.driver_id)
        if not driver:
            continue
        rows.append({
            "driver_id": driver.id,
            "driver_name": driver.name,
            "phone": driver.phone,
            "email": driver.email,
            "doc_type": doc.doc_type,
            "label": ALL_DOC_LABELS.get(doc.doc_type, doc.doc_type),
            "expires_on": doc.expires_on.isoformat(),
            "days_left": days_left,
            "status": "expired" if days_left < 0 else "expiring_soon",
            "alert_sent": doc.expiry_alert_sent_at is not None,
        })
    return rows


@app.route("/api/owner/expiring-documents", methods=["GET"])
def owner_expiring_documents():
    """Read-only expiring-soon + expired document list for the owner
    dashboard (owner decision 2026-11-19): every stored document
    expiring within the next 10 days, plus every expired one — expired
    means that driver's registration is paused until they upload a
    new document. Information only — no action, no approval step.
    Earliest expiry first."""
    error = require_owner()
    if error:
        return error
    return jsonify({"documents": _expiring_document_rows(_today_ny())})


@app.route("/api/owner/run-expiry-alerts", methods=["POST"])
def run_expiry_alerts_endpoint():
    """Trigger the 10-day document expiry alert check for every driver.

    Called by the owner dashboard when it loads (fire-and-forget),
    so alerts queue whenever the owner has the dashboard open — no
    new infrastructure, no billing change. For fully automatic firing
    without anyone having an app open, point a scheduler at this
    endpoint (Render cron jobs have no free-plan guarantee, so no
    scheduler is configured by this code — the owner sets one up only
    if he wants it):

      POST https://noelchauffer.com/api/owner/run-expiry-alerts
      Authorization: Bearer <EXPIRY_ALERT_CRON_SECRET>
      once a day

    with EXPIRY_ALERT_CRON_SECRET set to the same value in Render's
    environment. Any external scheduler (Render cron job,
    cron-job.org, UptimeRobot) works the same way.

    Auth: the owner session, OR the bearer <redacted> above. With
    EXPIRY_ALERT_CRON_SECRET unset, bearer <redacted> is disabled and
    only the owner session works. The check is idempotent: repeated
    triggers never queue a second alert for the same document expiry.
    """
    cron_secret = os.environ.get("EXPIRY_ALERT_CRON_SECRET", "")
    auth = request.headers.get("Authorization", "")
    bearer_ok = bool(cron_secret) and hmac.compare_digest(auth, "Bearer " + cron_secret)
    if not bearer_ok:
        error = require_owner()
        if error:
            return error
    alerted = run_expiry_alerts()
    return jsonify({"alerted": alerted})


# ------------------------------------------------------- daily summary -----
# Owner decision 2026-11-19 ("rozana summary bhej do"): every morning
# at 09:00 America/New_York the owner gets one short email covering
# the previous day (midnight-midnight NY time): rides completed,
# gross collected, profit, driver owed, new driver registrations,
# documents expiring soon, emergency cancels, and active/upcoming
# rides. The numbers come straight from the production database —
# owner notification emails are not reliably sent, so this is NOT
# built from Gmail.
#
# Trigger: Render cron jobs have no free-plan tier (billed per run
# from ~$1/month), so no Render cron is configured here. The
# endpoint below is called by the owner's external scheduler
# (a Muse cron) once a day:
#
#   POST https://noelchauffer.com/api/cron/daily-summary
#   Authorization: Bearer <DAILY_SUMMARY_CRON_SECRET>
#
# with DAILY_SUMMARY_CRON_SECRET set to the same value in Render's
# environment. A dry run — POST with {"dry_run": true} — returns the
# summary JSON and sends NO email, for verification.

# Booking statuses that still need doing (everything not completed,
# cancelled, or no-show).
ACTIVE_BOOKING_STATUSES = ("offered", "accepted", "en_route", "arrived", "in_progress")

# The owner's mailbox for the daily summary.
DAILY_SUMMARY_TO = os.environ.get("DAILY_SUMMARY_TO", "m.azherahmed1@gmail.com")


def _ny_date_of(dt):
    """New York date of a stored timestamp. Naive timestamps are
    read as UTC, matching completion_date() in payouts.py."""
    from zoneinfo import ZoneInfo

    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo("America/New_York")).date()


def compute_daily_summary(day=None):
    """One day's owner numbers (day = a New York date; default
    yesterday). Rides count on their completion date; gross counts
    completed rides with a succeeded, non-refunded payment (fare
    total + waiting charge — the same rule as the owner summary);
    profit is gross minus the driver share of those rides. A
    refunded ride still counts as completed, but contributes $0.
    Driver owed (yesterday) is the unpaid driver share of
    yesterday's completed rides; driver owed (total) is the same
    unpaid-share rule over all completed rides, as the owner
    summary computes it."""
    day = day or (_today_ny() - timedelta(days=1))
    paid_ids = {p.booking_id for p in Payment.query.filter_by(status="succeeded").all()}
    refunded_ids = _refunded_booking_ids()

    completed = []
    gross = Decimal("0.00")
    driver_cost = Decimal("0.00")
    driver_owed_yesterday = Decimal("0.00")
    for b in Booking.query.filter_by(status="completed").all():
        try:
            done = completion_date(b.completed_at, b.created_at)
        except ValueError:
            continue
        if done != day:
            continue
        completed.append(b)
        if b.id in refunded_ids:
            continue
        if b.id in paid_ids:
            gross += money(b.fare_total) + money(b.waiting_charge)
        driver_cost += money(b.driver_earnings)
        if not b.payout_paid:
            driver_owed_yesterday += money(b.driver_earnings)

    driver_owed_total = Decimal("0.00")
    for b in Booking.query.filter_by(status="completed").all():
        if b.id in refunded_ids or b.payout_paid:
            continue
        driver_owed_total += money(b.driver_earnings)

    new_drivers = [d for d in Driver.query.all() if _ny_date_of(d.created_at) == day]
    cancels = [c for c in EmergencyCancel.query.all() if _ny_date_of(c.created_at) == day]
    active = (Booking.query
              .filter(Booking.status.in_(ACTIVE_BOOKING_STATUSES))
              .order_by(Booking.date, Booking.time, Booking.id)
              .all())
    return {
        "date": day.isoformat(),
        "rides_completed": len(completed),
        "completed_rides": [{
            "id": b.id,
            "customer_name": b.customer_name,
            "route": f"{b.pickup} to {b.dropoff}" if b.dropoff else b.pickup,
            "date": b.date,
            "time": b.time,
            "driver_name": b.accepted_driver.name if b.accepted_driver else None,
            "customer_paid": num(money(b.fare_total) + money(b.waiting_charge)),
            "driver_earnings": num(b.driver_earnings),
            "profit": num(booking_profit(b)),
        } for b in completed],
        "gross": num(gross),
        "profit": num(gross - driver_cost),
        "driver_owed_yesterday": num(driver_owed_yesterday),
        "driver_owed_total": num(driver_owed_total),
        "new_drivers_count": len(new_drivers),
        "new_drivers": [{
            "id": d.id, "name": d.name, "phone": d.phone,
        } for d in new_drivers],
        "documents_expiring_soon": _expiring_document_rows(_today_ny()),
        "emergency_cancels_count": len(cancels),
        "emergency_cancels": [{
            "driver_name": c.driver_name,
            "reason": c.reason_label or c.reason,
            "judgment": c.judgment,
            "flagged": bool(c.flagged),
        } for c in cancels],
        "active_rides_count": len(active),
        "active_rides": [{
            "id": b.id,
            "customer_name": b.customer_name,
            "route": f"{b.pickup} to {b.dropoff}" if b.dropoff else b.pickup,
            "date": b.date,
            "time": b.time,
            "status": b.status,
            "driver_name": b.accepted_driver.name if b.accepted_driver else None,
        } for b in active],
    }


def format_daily_summary_email(summary):
    """Short plain-text email for the owner (Roman Urdu/English mix,
    like his other owner mail). Returns (subject, body)."""
    day = date.fromisoformat(summary["date"])
    subject = "Noel Chauffer — daily summary, " + day.strftime("%b %d, %Y")
    lines = [
        "Assalam-o-Alaikum Azher bhai — kal ka hisaab "
        f"({day.strftime('%b %d, %Y')}):",
        "",
        f"Rides completed: {summary['rides_completed']}",
        f"Gross collected: ${summary['gross']:.2f}",
        f"Profit: ${summary['profit']:.2f}",
        f"Driver owed (kal ki rides): ${summary['driver_owed_yesterday']:.2f}",
        f"Driver owed (total outstanding): ${summary['driver_owed_total']:.2f}",
        "",
        f"New drivers: {summary['new_drivers_count']}",
    ]
    for d in summary["new_drivers"]:
        lines.append(f"- {d['name']} ({d['phone']})")
    lines.append("")
    lines.append(f"Documents expiring soon: {len(summary['documents_expiring_soon'])}")
    for doc in summary["documents_expiring_soon"]:
        left = doc["days_left"]
        when = "expired" if left < 0 else (f"{left} din baaqi" if left != 1 else "1 din baaqi")
        lines.append(f"- {doc['driver_name']} — {doc['label']}, expires {doc['expires_on']} ({when})")
    lines.append("")
    lines.append(f"Emergency cancels: {summary['emergency_cancels_count']}")
    for c in summary["emergency_cancels"]:
        lines.append(f"- {c['driver_name']} — {c['reason']} ({c['judgment']})")
    lines.append("")
    lines.append(f"Active / upcoming rides: {summary['active_rides_count']}")
    for r in summary["active_rides"][:20]:
        driver = f", driver {r['driver_name']}" if r["driver_name"] else ""
        lines.append(f"- #{r['id']} — {r['route']}, {r['date']} {r['time']}, {r['status']}{driver}")
    if summary["active_rides_count"] > 20:
        lines.append(f"  ...aur {summary['active_rides_count'] - 20} rides")
    lines.append("")
    lines.append("— Noel Chauffer (noelchauffer.com)")
    return subject, "\n".join(lines)


@app.route("/api/cron/daily-summary", methods=["POST"])
def daily_summary_endpoint():
    """Send (or dry-run) the daily owner summary email.

    Auth: the owner session, OR the bearer secret
    Authorization: Bearer <DAILY_SUMMARY_CRON_SECRET>. With
    DAILY_SUMMARY_CRON_SECRET unset, bearer auth is disabled and
    only the owner session works. Body {"dry_run": true} (or
    ?dry_run=1) returns the summary JSON and sends NO email.
    Optional {"date": "YYYY-MM-DD"} summarises that NY date
    instead of yesterday (verification aid)."""
    cron_secret = os.environ.get("DAILY_SUMMARY_CRON_SECRET") or ""
    auth = request.headers.get("Authorization", "")
    bearer_ok = bool(cron_secret) and hmac.compare_digest(auth, "Bearer " + cron_secret)
    if not bearer_ok:
        error = require_owner()
        if error:
            return error
    data = request.get_json(silent=True) or {}
    dry_run = bool(data.get("dry_run")) or request.args.get("dry_run") in ("1", "true", "yes")
    day = None
    raw_date = data.get("date") or request.args.get("date")
    if raw_date:
        try:
            day = date.fromisoformat(str(raw_date))
        except ValueError:
            return err("date must be YYYY-MM-DD.", 400)
    summary = compute_daily_summary(day)
    if dry_run:
        return jsonify({"dry_run": True, "sent": False, "summary": summary})
    subject, body = format_daily_summary_email(summary)
    status = send_email(DAILY_SUMMARY_TO, subject, body)
    return jsonify({"sent": status == EMAIL_SENT,
                    "email_status": status, "summary": summary})


@app.route("/api/owner/support-messages", methods=["GET"])
def owner_support_messages():
    error = require_owner()
    if error:
        return error
    messages = (SupportMessage.query.order_by(SupportMessage.id.desc()).limit(200).all())
    return jsonify([{
        "id": m.id, "text": m.text, "flagged": m.flagged,
        "created_at": iso(m.created_at),
    } for m in messages])


# TEMPORARY TEST-ONLY endpoint (owner decision 2026-11-17, "filhal ke
# vaaste"): REMOVE this endpoint, the dashboard button, and their
# tests before real launch. It must never be called automatically and
# no automatic deletion/expiry of ride records may ever be added —
# driver ride history is retained for a minimum of one year.
@app.route("/api/owner/clear-rides", methods=["POST"])
def owner_clear_rides():
    """Owner-only MANUAL test reset: delete ALL rides and every
    ride-related row so the driver app starts empty again.

    TEMPORARY, testing only — see the banner comment above. This is
    only ever a manual, owner-PIN-confirmed reset from the dashboard
    button (itself guarded by a confirm dialog). Nothing calls it
    automatically, and ride history is otherwise retained for a
    minimum of one year.

    PIN re-confirmation (owner decision 2026-11-19): the request must
    carry the owner PIN in its JSON body ("pin") and it is checked
    server-side by require_owner_pin() — a signed-in session alone is
    not enough, and a missing or wrong PIN deletes nothing.

    Deleted: bookings, chat messages, booking events (alerts),
    emergency cancel records, driver referral credits, payments,
    decline exclusions and outbox messages. Kept untouched: drivers,
    their documents and profile photos.
    Referral codes stay valid: a code issued by a deleted booking
    keeps its code and used_count — only the link to the deleted
    booking is detached (issued_booking_id set to NULL) — because
    the code is what a customer holds and may still present.
    """
    error = require_owner()
    if error:
        return error
    error = require_owner_pin()
    if error:
        return error
    # Children first: their booking FKs have no ON DELETE CASCADE,
    # so the bookings themselves go last.
    deleted = {
        "chat_messages": ChatMessage.query.delete(synchronize_session=False),
        "booking_events": BookingEvent.query.delete(synchronize_session=False),
        "emergency_cancels": EmergencyCancel.query.delete(synchronize_session=False),
        "driver_referral_credits": DriverReferralCredit.query.delete(synchronize_session=False),
        "payments": Payment.query.delete(synchronize_session=False),
        "booking_exclusions": BookingExclusion.query.delete(synchronize_session=False),
        "outbox_messages": OutboxMessage.query.delete(synchronize_session=False),
    }
    detached = ReferralCode.query.filter(
        ReferralCode.issued_booking_id.isnot(None)
    ).update({"issued_booking_id": None}, synchronize_session=False)
    deleted["bookings"] = Booking.query.delete(synchronize_session=False)
    deleted["referral_codes_detached"] = detached
    db.session.commit()
    log.info("owner cleared all rides: %s", deleted)
    return jsonify({"cleared": True, "deleted": deleted})


# TEMPORARY TEST-ONLY endpoint (owner decision 2026-11-17, voice call):
# REMOVE this endpoint, the dashboard button, and their tests before
# real launch. The owner asked to remove every currently registered
# driver ("jitne bhi") so everyone re-registers fresh with the new
# state selector. It must never be called automatically. Ride history
# is KEPT — only the driver links are detached — because driver ride
# records are retained for a minimum of one year.
def _snapshot_removed_driver(driver, via):
    """Record a removed driver BEFORE his row is deleted (owner
    decision 2026-11-23): the snapshot is the only record left once
    the Driver row and every document are gone, and it is what the
    dashboard \"Removed drivers\" list shows and what Restore rebuilds
    from. Callers add it to the session and commit with the delete —
    the snapshot must land in the same transaction as the removal.
    No documents, photos, bank details or password are snapshotted:
    a restored driver re-uploads documents and sets a new password.
    """
    snap = RemovedDriver(
        original_driver_id=driver.id,
        removed_via=via,
        name=driver.name or "",
        phone=driver.phone or "",
        email=driver.email or "",
        state=driver.state,
        city=driver.city,
        car_model=driver.car_model or "",
        car_year=driver.car_year,
        vehicle_class=driver.vehicle_class,
        car_colour=driver.car_colour or "",
        plate=driver.plate or "",
    )
    db.session.add(snap)
    return snap


def _removed_driver_row(r):
    return {
        "id": r.id,
        "original_driver_id": r.original_driver_id,
        "removed_at": iso(r.removed_at),
        "removed_via": r.removed_via,
        "name": r.name,
        "phone": r.phone,
        "email": r.email,
        "state": r.state,
        "city": r.city,
        "car": f"{r.car_model} ({r.car_colour})" if r.car_model else "",
        "car_model": r.car_model,
        "car_year": r.car_year,
        "vehicle_class": r.vehicle_class,
        "car_colour": r.car_colour,
        "plate": r.plate,
    }


@app.route("/api/owner/clear-drivers", methods=["POST"])
def owner_clear_drivers():
    """Owner-only MANUAL test reset: remove ALL driver registrations
    so every driver re-registers fresh (e.g. with the state selector).

    TEMPORARY, testing only — see the banner comment above. This is
    only ever a manual, owner-PIN-confirmed reset from the dashboard
    button (itself guarded by a confirm dialog). Nothing calls it
    automatically.

    PIN re-confirmation (owner decision 2026-11-19): the request must
    carry the owner PIN in its JSON body ("pin") and it is checked
    server-side by require_owner_pin() — a signed-in session alone is
    not enough, and a missing or wrong PIN removes nothing.

    Removed: every Driver row, every DriverDocument row (via the ORM
    cascade on Driver.documents), and every BookingExclusion row
    (they reference drivers). Detached, never deleted: bookings keep
    their records — accepted_driver_id / assigned_driver_id are set
    to NULL — and payments, chat messages, booking events, outbox
    messages and referral codes are untouched. A removed driver's
    phone number becomes free to register again.
    """
    error = require_owner()
    if error:
        return error
    error = require_owner_pin()
    if error:
        return error
    # Bookings are KEPT: only the driver links are detached, so ride
    # history survives (retained for a minimum of one year).
    unlinked_accepted = Booking.query.filter(
        Booking.accepted_driver_id.isnot(None)
    ).update({"accepted_driver_id": None}, synchronize_session=False)
    unlinked_assigned = Booking.query.filter(
        Booking.assigned_driver_id.isnot(None)
    ).update({"assigned_driver_id": None}, synchronize_session=False)
    exclusions = BookingExclusion.query.delete(synchronize_session=False)
    # Per-driver ORM delete: Driver.documents cascades "all,
    # delete-orphan", so every DriverDocument row goes with its
    # driver. A bulk Driver.query.delete() would NOT cascade and
    # would orphan documents / hit the FK constraint.
    documents = DriverDocument.query.count()
    drivers = Driver.query.all()
    for driver in drivers:
        # Snapshot first: once the row is gone the only record of
        # this driver is the RemovedDriver snapshot (owner decision
        # 2026-11-23) — it feeds the dashboard "Removed drivers"
        # list and Restore.
        _snapshot_removed_driver(driver, "bulk")
        db.session.delete(driver)
    db.session.commit()
    removed = {
        "drivers": len(drivers),
        "documents": documents,
        "booking_exclusions": exclusions,
        "bookings_unlinked": unlinked_accepted + unlinked_assigned,
    }
    log.info("owner cleared all drivers: %s", removed)
    return jsonify({"cleared": True, "deleted": removed})


@app.route("/api/owner/drivers/<int:driver_id>/remove", methods=["POST"])
def owner_remove_driver(driver_id):
    """Owner-only MANUAL removal of ONE driver (owner decision
    2026-11-19, voice call): the owner can remove an individual
    driver from the dashboard or the owner app.

    Mirrors the bulk clear-drivers reset, scoped to one driver:
    the Driver row and every DriverDocument row go (ORM cascade),
    that driver's BookingExclusion rows go, and bookings keep their
    records — accepted_driver_id / assigned_driver_id are set to
    NULL. Referral credits are untouched (snapshots, no FKs), and a
    removed driver's phone number becomes free to register again.

    PIN re-confirmation (owner decision 2026-11-19): the request
    must carry the owner PIN in its JSON body ("pin") and it is
    checked server-side by require_owner_pin() — a signed-in session
    alone is not enough, and a missing or wrong PIN removes nothing.
    """
    error = require_owner()
    if error:
        return error
    error = require_owner_pin()
    if error:
        return error
    driver = db.session.get(Driver, driver_id)
    if not driver:
        return err("Driver not found.", 404)
    unlinked_accepted = Booking.query.filter(
        Booking.accepted_driver_id == driver.id
    ).update({"accepted_driver_id": None}, synchronize_session=False)
    unlinked_assigned = Booking.query.filter(
        Booking.assigned_driver_id == driver.id
    ).update({"assigned_driver_id": None}, synchronize_session=False)
    exclusions = BookingExclusion.query.filter_by(
        driver_id=driver.id
    ).delete(synchronize_session=False)
    documents = DriverDocument.query.filter_by(driver_id=driver.id).count()
    name = driver.name
    # Snapshot first: once the row is gone the only record of this
    # driver is the RemovedDriver snapshot (owner decision
    # 2026-11-23) — it feeds the dashboard "Removed drivers" list
    # and Restore.
    _snapshot_removed_driver(driver, "single")
    db.session.delete(driver)
    db.session.commit()
    removed = {
        "drivers": 1,
        "documents": documents,
        "booking_exclusions": exclusions,
        "bookings_unlinked": unlinked_accepted + unlinked_assigned,
    }
    log.info("owner removed driver %s (%s): %s", driver_id, name, removed)
    return jsonify({"removed": True, "deleted": removed})


@app.route("/api/owner/bookings/<int:booking_id>/remove", methods=["POST"])
def owner_remove_booking(booking_id):
    """Owner-only MANUAL removal of ONE ride (owner decision
    2026-11-19, voice call): the owner can remove an individual
    booking from the dashboard or the owner app.

    Mirrors the bulk clear-rides reset, scoped to one booking: the
    booking and its chat messages, booking events, emergency cancel
    records, driver referral credits, payments, decline exclusions
    and outbox messages go. Referral codes stay valid — a code
    issued by the deleted booking keeps its code and used_count,
    only the link to the booking is detached (issued_booking_id set
    to NULL). Drivers and their documents are untouched.

    PIN re-confirmation (owner decision 2026-11-19): the request
    must carry the owner PIN in its JSON body ("pin") and it is
    checked server-side by require_owner_pin() — a signed-in session
    alone is not enough, and a missing or wrong PIN deletes nothing.
    """
    error = require_owner()
    if error:
        return error
    error = require_owner_pin()
    if error:
        return error
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return err("Booking not found.", 404)
    deleted = {
        "chat_messages": ChatMessage.query.filter_by(
            booking_id=booking.id).delete(synchronize_session=False),
        "booking_events": BookingEvent.query.filter_by(
            booking_id=booking.id).delete(synchronize_session=False),
        "emergency_cancels": EmergencyCancel.query.filter_by(
            booking_id=booking.id).delete(synchronize_session=False),
        "driver_referral_credits": DriverReferralCredit.query.filter_by(
            booking_id=booking.id).delete(synchronize_session=False),
        "payments": Payment.query.filter_by(
            booking_id=booking.id).delete(synchronize_session=False),
        "booking_exclusions": BookingExclusion.query.filter_by(
            booking_id=booking.id).delete(synchronize_session=False),
        "outbox_messages": OutboxMessage.query.filter_by(
            booking_id=booking.id).delete(synchronize_session=False),
    }
    detached = ReferralCode.query.filter(
        ReferralCode.issued_booking_id == booking.id
    ).update({"issued_booking_id": None}, synchronize_session=False)
    deleted["referral_codes_detached"] = detached
    db.session.delete(booking)
    db.session.commit()
    deleted["bookings"] = 1
    log.info("owner removed booking %s: %s", booking_id, deleted)
    return jsonify({"removed": True, "deleted": deleted})


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
        "state": d.state,
        "city": d.city,
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
        # Expiry dates typed at registration (owner decision
        # 2026-11-19); NULL where the document has no expiry or
        # predates the check.
        "doc_expiries": {doc.doc_type: (doc.expires_on.isoformat()
                                        if doc.expires_on else None)
                         for doc in d.documents},
        "bank_masked": bank_masked(d),
    } for d in drivers])


@app.route("/api/owner/removed-drivers", methods=["GET"])
def owner_removed_drivers():
    """Read-only list of removed drivers for the owner dashboard
    (owner decision 2026-11-23): every driver removed from now on
    leaves a snapshot here, newest first. Drivers removed before
    this shipped left no snapshot and do not appear."""
    error = require_owner()
    if error:
        return error
    removed = (RemovedDriver.query
               .order_by(RemovedDriver.removed_at.desc(),
                         RemovedDriver.id.desc()).all())
    return jsonify([_removed_driver_row(r) for r in removed])


@app.route("/api/owner/removed-drivers/<int:removed_id>/restore", methods=["POST"])
def owner_restore_removed_driver(removed_id):
    """Restore one removed driver (owner decision 2026-11-23):
    re-create the Driver row from the removal snapshot with the
    same name, phone, email and car.

    PIN re-confirmation (same as removal): the request must carry
    the owner PIN in its JSON body ("pin"), checked server-side by
    require_owner_pin() — a signed-in session alone is not enough.

    Conflicts fail cleanly, never overwrite: if that phone or email
    is registered to another driver by now, restore returns 409 and
    nothing changes.

    Documents were deleted at removal and CANNOT come back: the
    restored driver has NO documents and NO password — he must
    re-upload all documents (the compulsory-document gate blocks
    him from going available until then) and set a new password
    via the forgot-password flow. Bookings stay unlinked; the
    snapshot row is deleted on a successful restore.
    """
    error = require_owner()
    if error:
        return error
    error = require_owner_pin()
    if error:
        return error
    snap = db.session.get(RemovedDriver, removed_id)
    if not snap:
        return err("Removed driver not found.", 404)
    if Driver.query.filter_by(phone=snap.phone).first():
        return err("A driver with this phone number is already registered.", 409)
    email = (snap.email or "").strip().lower()
    if email and Driver.query.filter(func.lower(Driver.email) == email).first():
        return err("A driver with this email address is already registered.", 409)
    driver = Driver(
        name=snap.name,
        phone=snap.phone,
        email=email,
        password_hash=None,
        state=snap.state,
        city=snap.city,
        # Fresh referral code and session token: the old ones died
        # with the driver row, and a code minted since could
        # collide — a restored driver is re-registered, so he gets
        # new ones, same as a new driver.
        referral_code=generate_driver_referral_code(),
        referred_by_driver_id=None,
        car_model=snap.car_model,
        car_year=snap.car_year,
        vehicle_class=snap.vehicle_class,
        car_colour=snap.car_colour,
        plate=snap.plate,
        available=False,
        token=secrets.token_urlsafe(32),
    )
    db.session.add(driver)
    db.session.delete(snap)
    db.session.commit()
    log.info("owner restored removed driver %s (%s) as driver %s",
             removed_id, snap.name, driver.id)
    return jsonify({"restored": True, "driver_id": driver.id,
                    "name": driver.name})


@app.route("/api/owner/document-flags", methods=["GET"])
def owner_document_flags():
    """Read-only flagged registration attempts for the owner dashboard
    (owner decision 2026-11-19): registrations rejected by the
    duplicate, photo-sanity or expiry checks. Information only — no
    action, no approval step. Newest first, latest 50."""
    error = require_owner()
    if error:
        return error
    flags = (DocumentFlag.query
             .order_by(DocumentFlag.created_at.desc(), DocumentFlag.id.desc())
             .limit(50).all())
    return jsonify({"flags": [{
        "id": f.id,
        "created_at": iso(f.created_at),
        "name": f.name,
        "phone": f.phone,
        "email": f.email,
        "doc_type": f.doc_type,
        "doc_label": f.doc_label,
        "reason": f.reason,
        "detail": f.detail,
    } for f in flags]})


@app.route("/api/owner/driver-referrals", methods=["GET"])
def owner_driver_referrals():
    """Read-only referral records for the owner dashboard: who
    referred whom, jobs counted (out of each referred driver's first
    15), and dollars earned. Information only — no action, no
    approval step. Tracking only; no money moves here."""
    error = require_owner()
    if error:
        return error
    records = driver_referral_records()
    return jsonify({
        "referrals": records,
        "total_jobs_counted": sum(r["jobs_counted"] for r in records),
        "total_earned": num(sum(
            ((c.amount or Decimal("0.00"))
             for c in DriverReferralCredit.query.all()), Decimal("0.00"))),
    })


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

# Popular-places warm-up: the committed snapshot in geo_places_snapshot.json
# already covers the first request; this background thread refreshes those
# entries from live data when the upstream answers. Production only:
# render.yaml sets NOEL_SEARCH_WARMUP=1. Never started in tests or local
# runs unless the variable is set explicitly.
if os.environ.get("NOEL_SEARCH_WARMUP") == "1":
    try:
        geo_module.start_popular_places_refresh()
    except Exception:
        app.logger.warning("places warm-up failed to start", exc_info=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
