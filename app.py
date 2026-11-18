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

import io
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
# Dallas, Texas is the FIRST and ONLY city-specific list. Its items
# come from Uber's official pages only — the Uber Help livery article
# (valid state-issued DMV driving license, commercial insurance,
# vehicle registration, and the City of Dallas or Fort Worth limo
# permit) and the Uber Dallas vehicle-requirements page (Dallas
# Driver Permit required, commercial insurance):
#   https://help.uber.com/en-GB/driving-and-delivering/article/becoming-a-driver-livery?nodeId=d17a342c-ad81-403b-8a4a-14e9ef7300af
#   https://www.uber.com/us/en/drive/requirements/vehicle-requirements/?city=dallas
# Fort Worth was researched the same night (Uber Help + City of Fort
# Worth Ground Transportation Office, Chapter 34 Article VI): Fort
# Worth licenses the OPERATING business, not the individual driver —
# no Fort Worth driver permit document is named anywhere — so Fort
# Worth has NO city-specific list and falls back to the Texas state
# list. Never assume Fort Worth = Dallas. Process-type requirements
# (background checks, exams, courses) are never upload slots, and no
# document count is ever shown ("Quantity nahi").
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

# (state, city) -> city-specific list. Only Dallas today; a city is
# added here ONLY with a verified official source naming its items.
CITY_DOC_REQUIREMENTS = {
    ("Texas", "Dallas"): DALLAS_DOC_TYPES,
}


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
    a verified city-specific list)."""
    if city and (state, city) in CITY_DOC_REQUIREMENTS:
        return False
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
    "ca_tcp_permit": "Charter-Party Carrier (TCP) Permit, Class P",
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
    "ca_tcp_permit": "Photo of your Charter-Party Carrier (TCP) Permit, Class P, straight and fully visible.",
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

    accepted_driver = db.relationship("Driver", foreign_keys=[accepted_driver_id])
    assigned_driver = db.relationship("Driver", foreign_keys=[assigned_driver_id])
    payments = db.relationship("Payment", backref="booking", cascade="all, delete-orphan")
    events = db.relationship("BookingEvent", backref="booking", cascade="all, delete-orphan")
    chat_messages = db.relationship("ChatMessage", backref="booking", cascade="all, delete-orphan")


class ChatMessage(db.Model):
    """In-app chat between driver and customer. Plain text only, no
    SMS, no number masking. Messages NEVER carry fare, miles,
    gratuity, tax or total figures — text only. A new table, so
    create_all() creates it on the live database too."""
    __tablename__ = "chat_messages"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    sender = db.Column(db.String(10), nullable=False)  # driver | customer
    text = db.Column(db.Text, nullable=False)
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
    # Statuses for the documents the driver's state + city require. A
    # city with a verified city-specific list (Dallas) overrides its
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


def _chat_message_view(message):
    # Text only — never any money figure, by construction.
    return {
        "id": message.id,
        "sender": message.sender,
        "text": message.text,
        "created_at": iso(message.created_at),
    }


def _chat_messages(booking_id):
    return [_chat_message_view(m) for m in
            ChatMessage.query.filter_by(booking_id=booking_id).order_by(ChatMessage.id).all()]


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
    return jsonify({"messages": _chat_messages(booking.id)})


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
    message = ChatMessage(booking_id=booking.id, sender="customer", text=text)
    db.session.add(message)
    db.session.commit()
    return jsonify({"message": _chat_message_view(message)}), 201


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
    return jsonify({"messages": _chat_messages(booking.id)})


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
    message = ChatMessage(booking_id=booking.id, sender="driver", text=text)
    db.session.add(message)
    db.session.commit()
    return jsonify({"message": _chat_message_view(message)}), 201


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
    that override their state list (Dallas only today). Every other
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
    # sends it. A city with a verified city-specific list (Dallas)
    # overrides the state list; every other city — including "Other
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
    # Dallas today, overrides its state list). This gates only new
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
        email=(form.get("email") or "").strip(),
        state=state,
        city=city,
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
        # Owner rule 2026-11-17: once pickup is within 2 hours, the
        # driver cannot cancel. Earlier, cancelling works as before
        # and the job goes back to the other drivers automatically.
        if driver_cancel_locked(booking.date, booking.time):
            return err("This job can no longer be cancelled because "
                       "pickup is within 2 hours.", 409)
        booking.status = "offered"
        booking.accepted_driver_id = None
        booking.assigned_driver_id = None
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
    payments, decline exclusions and outbox messages. Kept
    untouched: drivers, their documents and profile photos.
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
