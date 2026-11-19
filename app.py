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
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import quote_plus

from cryptography.fernet import Fernet
from flask import Flask, Response, jsonify, request, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageOps
from sqlalchemy import Numeric, func
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

import geo as geo_module
from car_models import (
    MIN_CAR_YEAR,
    allowed_models,
    class_for_model,
    max_car_year,
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
    total_earned = Decimal("0.00")
    for friend in friends:
        credits = DriverReferralCredit.query.filter_by(
            referred_driver_id=friend.id,
            referrer_driver_id=driver.id).all()
        jobs = len(credits)
        earned = sum((c.amount or Decimal("0.00") for c in credits),
                     Decimal("0.00"))
        total_jobs += jobs
        total_earned += earned
        breakdown.append({
            "name": friend.name,
            "jobs_counted": jobs,
            "earned": num(earned),
            "registered_at": iso(friend.created_at),
        })
    return {
        "referral_code": driver_referral_code(driver),
        "credit_per_job": num(DRIVER_REFERRAL_CREDIT),
        "max_jobs_per_driver": DRIVER_REFERRAL_MAX_JOBS,
        "total_earned": num(total_earned),
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
    degrades to 'not suspended' instead of raising."""
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
        if send_email(row.recipient, subject or DEFAULT_EMAIL_SUBJECT, row.body) == EMAIL_SENT:
            row.sent_at = utcnow()
    except Exception as exc:  # never break the caller
        log.warning("outbox email send failed: %s", exc)


def add_outbox(channel, recipient, body, booking_id=None, subject=None):
    row = OutboxMessage(channel=channel, recipient=recipient, body=body, booking_id=booking_id)
    db.session.add(row)
    if channel == "email":
        _try_send_email(row, subject)
    return row


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
    current toll + vehicle class, at the CURRENT pricing formula
    (total = fare + toll; gratuity and tax are $0.00 for new
    computations — see pricing.py).

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


@app.route("/app")
def customer_app_page():
    return _serve_page("customer-app.html", "customer app")


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
        booking.vehicle_class = "sedan"
        result = compute_one_way(booking.miles, toll=booking.toll,
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
            "extra_distance_charge": num(booking.extra_distance_charge),
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
        "chat_language": booking_customer_chat_language(booking),
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
    car_model, model_error = validate_car_model(form.get("car_model"))
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
            mime=mime, original_name=original_name))
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
    """Request a password reset link. ALWAYS returns the same generic
    message, whether or not the email matches a driver — it never
    reveals whether an email is registered. A token is created only
    for a driver who actually has a password hash (drivers
    registered before passwords existed keep using the phone
    lookup). Issuing a token invalidates the driver's previous
    unused tokens, so only the newest link works."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    driver = None
    if email:
        driver = Driver.query.filter(func.lower(Driver.email) == email).first()
    if driver and driver.password_hash:
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
        add_outbox("email", driver.email,
                   "Noel Chauffer: reset your driver app password using "
                   "this link (it expires in 5 minutes): " + reset_link,
                   subject="Reset your Noel Chauffer password")
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
        "hours": num(booking.hours),
        "vehicle_class": booking_vehicle_class(booking),
        "vehicle_class_label": class_label(booking_vehicle_class(booking)),
        "customer_name": booking.customer_name,
        "customer_phone": booking.phone,
        "earnings": num(booking.driver_earnings),
        "toll": num(booking.toll),
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
    driver.available = bool(data["available"])
    db.session.commit()
    return jsonify({"available": driver.available})


@app.route("/api/drivers/me/offers", methods=["GET"])
def driver_offers():
    driver, error = require_driver()
    if error:
        return error
    # A suspended driver gets no offers until the suspension lifts
    # (owner decision 2026-11-18). The app shows the suspension
    # notice from /api/drivers/me, so an empty list is enough here.
    if is_driver_suspended(driver):
        return jsonify([])
    # Owner decision 2026-11-16: job offers reach every registered
    # driver, available or offline — the "Go available" toggle no
    # longer gates offers. The time-conflict rule below still applies.
    excluded_ids = [e.booking_id for e in BookingExclusion.query.filter_by(driver_id=driver.id).all()]
    # Only PAID bookings reach drivers: status "offered" means payment
    # succeeded. Unpaid bookings (awaiting_payment) never appear here.
    # Class filtering: one-way bookings reach only drivers whose car
    # class matches the booking's class; hourly rides (no class) reach
    # every driver, available or offline.
    driver_class = driver_vehicle_class(driver)
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
        if b.ride_type == "one_way" and booking_vehicle_class(b) != driver_class:
            continue
        # No double-booking: hide jobs whose time overlaps a ride
        # this driver has already accepted (pickup time + driving
        # duration + buffer). A later, non-overlapping job still shows.
        candidate_window = _booking_busy_window(b)
        if candidate_window is not None and any(
                _windows_overlap(candidate_window, w) for w in busy_windows):
            continue
        # Driver sees ONLY his own pay — never miles, fare, total,
        # gratuity, tax, or the booking fee. Earnings include any toll;
        # the toll is also sent on its own so the app can show it as a
        # separate line (only when a toll applies).
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
            "toll": num(b.toll),
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
        "pickup_lat": booking.pickup_lat,
        "pickup_lng": booking.pickup_lng,
        "dropoff_lat": booking.dropoff_lat,
        "dropoff_lng": booking.dropoff_lng,
        "date": booking.date,
        "time": booking.time,
        "ride_type": booking.ride_type,
        "vehicle_class": booking_vehicle_class(booking),
        "vehicle_class_label": class_label(booking_vehicle_class(booking)),
        "customer_name": booking.customer_name,
        "customer_phone": booking.phone,
        "earnings": num(booking.driver_earnings),
        "toll": num(booking.toll),
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


def proximity_gate_error(booking, event, data):
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
        gate_err = proximity_gate_error(booking, event, data)
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
        gate_err = proximity_gate_error(booking, event, data)
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
            f"Noel Chauffer: thank you for riding with us. Your invoice total is ${total} "
            f"(including ${booking.waiting_charge} waiting charge"
            + (f" and ${booking.extra_distance_charge} extra distance" if extra_dec > 0 else "")
            + ").",
        )
        add_event(booking.id, "trip_completed",
                  f"Booking #{booking.id} completed. Invoice total ${total} "
                  f"(fare ${booking.fare_total} + waiting ${booking.waiting_charge})"
                  + (f", extra distance {extra_dec} miles (${booking.extra_distance_charge})" if extra_dec > 0 else "")
                  + ".")
        response_extra["invoice"] = {"total": num(total), "waiting_charge": num(booking.waiting_charge)}
    elif event == "cancel":
        if booking.status not in ("accepted", "en_route", "arrived"):
            return err("Cannot cancel a ride in this state.", 409)
        # Owner rule 2026-11-18 (SUPERSEDES the 2026-11-17 lock that
        # blocked every cancel inside 2 hours): once pickup is
        # within 2 hours, the driver CAN still cancel, but MUST give
        # a reason, and the reason is judged automatically — no
        # manual review. A fault judgment blocks the driver's app
        # for 48 hours; a genuine emergency never blocks. More than
        # 2 hours out, cancelling works exactly as before: no reason
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
            suspended_until = (now + timedelta(hours=SUSPENSION_HOURS)
                               if judgment == "fault" else None)
            if suspended_until is not None:
                driver.suspended_until = suspended_until
                driver.available = False
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
            "test": p.test, "last4": p.last4, "stripe_test_id": p.stripe_test_id,
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
    if (booking.ride_type == "one_way"
            and booking_vehicle_class(booking) != driver_vehicle_class(driver)):
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
@app.route("/api/owner/clear-drivers", methods=["POST"])
def owner_clear_drivers():
    """Owner-only MANUAL test reset: remove ALL driver registrations
    so every driver re-registers fresh (e.g. with the state selector).

    TEMPORARY, testing only — see the banner comment above. This is
    only ever a manual, owner-PIN-confirmed reset from the dashboard
    button (itself guarded by a confirm dialog). Nothing calls it
    automatically.

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
        "bank_masked": bank_masked(d),
    } for d in drivers])


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
