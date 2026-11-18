"""End-to-end HTTP verification for the Noel Chauffer booking system.

Runs against a REAL running server with a FRESH database — it asserts
the settled business rules over HTTP, it does not eyeball anything.

Usage:
  1. Boot the server with a throwaway DB, e.g.:
       DATABASE_URL="sqlite:////tmp/noel-verify.db" OWNER_PIN=4321 \
       SECRET_KEY=test-secret ENCRYPTION_KEY="$(python -c \
       'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
       PORT=5055 python app.py
  2. Run:  NOEL_BASE_URL=http://127.0.0.1:5055 NOEL_OWNER_PIN=4321 python verify_e2e.py

Exit code 0 = every check passed. The script expects an EMPTY database:
owner bookings must be [] at the start, otherwise it aborts.

Pricing assertions use the live geo result: miles are read back from the
owner booking detail and the expected totals are computed with the same
pricing module the server uses. When live geo returns 18.0 miles for
JFK Airport -> Times Square (as verified before), the exact figures
$162.00 / $72.00 / $162.00 / $180.50 / $90.50 / $177.00 are asserted too.
"""

import io
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import requests
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from payouts import completion_date, week_for  # noqa: E402
from pricing import compute_extra_distance, compute_hourly, compute_one_way, waiting_charge  # noqa: E402

BASE = os.environ.get("NOEL_BASE_URL", "http://127.0.0.1:5055").rstrip("/")
OWNER_PIN = os.environ.get("NOEL_OWNER_PIN", "4321")
TIMEOUT = 60

CHECKS = {"passed": 0, "failed": 0}
FAILURES = []


def check(name, condition, detail=""):
    if condition:
        CHECKS["passed"] += 1
        print(f"  PASS {name}")
    else:
        CHECKS["failed"] += 1
        FAILURES.append(name)
        print(f"  FAIL {name} {detail}")


def approx(a, b):
    return a is not None and b is not None and abs(float(a) - float(b)) < 0.005


def section(title):
    print(f"== {title} ==")


s = requests.Session()  # owner session (cookie jar)
anon = requests.Session()

FORBIDDEN_OFFER_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                        "fare_total", "customer_total", "subtotal", "profit", "tax"}

# ------------------------------------------------------------------ boot ---

section("server up + empty DB")
r = anon.get(BASE + "/", timeout=TIMEOUT)
check("home page 200", r.status_code == 200, str(r.status_code))
check("home page is the real customer page", "Noel Chauffer" in r.text and "Book your ride" in r.text)
r = anon.post(BASE + "/api/owner/login", json={"pin": "0000"}, timeout=TIMEOUT)
check("wrong owner PIN -> 401", r.status_code == 401, str(r.status_code))
r = s.post(BASE + "/api/owner/login", json={"pin": OWNER_PIN}, timeout=TIMEOUT)
check("correct owner PIN works", r.status_code == 200, r.text[:150])
r = s.get(BASE + "/api/owner/bookings", timeout=TIMEOUT)
check("owner bookings readable", r.status_code == 200, str(r.status_code))
if r.status_code == 200 and r.json():
    print("ABORT: database is not empty — re-run against a fresh DB.")
    sys.exit(2)
check("database starts empty", r.status_code == 200 and r.json() == [])

# ------------------------------------------------- driver registration -----

section("driver registration: all 8 docs, FH-1 PDF, masked bank")
# The profile photo must be a real portrait image (server shape/size
# rules: portrait, at least 300px on the short side).
_photo_buf = io.BytesIO()
Image.new("RGB", (400, 500), (200, 30, 30)).save(_photo_buf, format="JPEG")
photo = _photo_buf.getvalue()
fh1_pdf = b"%PDF-1.4 fake fh1 insurance card"
png = b"\x89PNG fake document image"
# All 7 compulsory registration uploads (owner decision 2026-11-17).
all_docs = {
    "profile_photo": ("photo.jpg", photo, "image/jpeg"),
    "doc_dmv_license": ("license.png", png, "image/png"),
    "doc_tlc_license": ("tlc.png", png, "image/png"),
    "doc_fh1": ("fh1.png", png, "image/png"),
    "doc_registration": ("reg.png", png, "image/png"),
    "doc_inspection": ("insp.png", png, "image/png"),
    "doc_vehicle_permit": ("permit.png", png, "image/png"),
}
files_before = set()
repo_dir = os.path.dirname(os.path.abspath(__file__))
for root, _dirs, names in os.walk(repo_dir):
    if "__pycache__" in root:
        continue
    for n in names:
        files_before.add(os.path.join(root, n))

resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Verify Driver One", "phone": "+15550001111", "email": "d1@test.com",
    "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black", "plate": "T11111",
    "state": "New York", "bank_account_number": "123456789", "bank_routing_number": "021000021",
}, files={
    "profile_photo": ("photo.jpg", photo, "image/jpeg"),
    "doc_dmv_license": ("license.png", png, "image/png"),
    "doc_tlc_license": ("tlc.png", png, "image/png"),
    "doc_fh1": ("fh1.pdf", fh1_pdf, "application/pdf"),
    "doc_registration": ("reg.png", png, "image/png"),
    "doc_inspection": ("insp.png", png, "image/png"),
    "doc_vehicle_permit": ("permit.png", png, "image/png"),
}, timeout=TIMEOUT)
check("driver1 register 201", resp.status_code == 201, resp.text[:200])
d1 = resp.json()["driver"]
token1 = resp.json()["token"]
check("all 7 docs completed", all(v == "completed" for v in d1["docs"].values())
      and len(d1["docs"]) == 7, str(d1["docs"]))
check("dmv_license is the first doc status key",
      list(d1["docs"])[:1] == ["dmv_license"], str(list(d1["docs"])))
check("bank masked in register response", d1["bank_masked"] == "••••6789", d1["bank_masked"])
check("full bank number never in register response",
      "123456789" not in resp.text and "021000021" not in resp.text)

resp = anon.get(BASE + "/api/drivers/me", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("token flow: /me works (no registration)", resp.status_code == 200, str(resp.status_code))
check("bank masked in /me", resp.json()["driver"]["bank_masked"] == "••••6789")
check("full bank number never in /me",
      "123456789" not in resp.text and "021000021" not in resp.text)

resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Verify Driver Two", "phone": "+15550002222", "email": "d2@test.com",
    "car_model": "Lincoln Continental", "car_year": "2024", "car_colour": "Black", "plate": "T22222",
    "state": "New York", "bank_account_number": "987654321", "bank_routing_number": "021000021",
}, files=all_docs, timeout=TIMEOUT)
check("driver2 register 201", resp.status_code == 201, resp.text[:200])
token2 = resp.json()["token"]

resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Verify Driver Three", "phone": "+15550001234", "email": "d3@test.com",
    "car_model": "Cadillac Escalade", "car_year": "2024", "car_colour": "Black", "plate": "T33333",
    "state": "New York", "bank_account_number": "111222333", "bank_routing_number": "021000021",
}, files=all_docs, timeout=TIMEOUT)
check("driver3 (SUV) register 201", resp.status_code == 201, resp.text[:200])
d3 = resp.json()["driver"]
token3 = resp.json()["token"]
check("driver3 class derived as SUV", d3["vehicle_class"] == "suv"
      and d3["vehicle_class_label"] == "Business SUV", str(d3))
check("driver1 class derived as sedan", d1["vehicle_class"] == "sedan"
      and d1["vehicle_class_label"] == "Business Class", str(d1))

resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Dup", "phone": "+15550001111", "car_model": "Cadillac Escalade",
    "car_year": "2023", "car_colour": "Y",
    "plate": "Z", "state": "New York", "bank_account_number": "1", "bank_routing_number": "2",
}, timeout=TIMEOUT)
check("duplicate phone -> 409", resp.status_code == 409, str(resp.status_code))
resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Bad", "phone": "+15550003333", "car_model": "Cadillac Escalade",
    "car_year": "2023", "car_colour": "Y",
    "plate": "Z", "state": "New York", "bank_account_number": "1", "bank_routing_number": "2",
}, files={"doc_dmv_license": ("license.pdf", fh1_pdf, "application/pdf")}, timeout=TIMEOUT)
check("PDF rejected for non-FH1 doc -> 400", resp.status_code == 400, str(resp.status_code))

# Compulsory documents (owner decision 2026-11-17): registration must
# not complete unless every item is uploaded, and the rejection must
# name each missing item ("Missing document: ...").
resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "No Docs", "phone": "+15550006666", "email": "nd@test.com",
    "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
    "plate": "T00000", "state": "New York", "bank_account_number": "1", "bank_routing_number": "2",
}, timeout=TIMEOUT)
check("no documents -> 400 naming every missing item",
      resp.status_code == 400
      and resp.json()["error"].startswith("Missing document: ")
      and all(label in resp.json()["error"] for label in
              ("Profile Picture", "DMV driving license", "TLC License",
               "FH-1 Insurance Card", "Commercial Vehicle Registration",
               "NYS DMV Inspection", "TLC-for-hire Vehicle Permit")),
      resp.text[:300])
partial_docs = dict(all_docs)
del partial_docs["doc_vehicle_permit"]
resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "One Missing", "phone": "+15550007777", "email": "om@test.com",
    "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black",
    "plate": "T00001", "state": "New York", "bank_account_number": "1", "bank_routing_number": "2",
}, files=partial_docs, timeout=TIMEOUT)
check("one document missing -> 400 naming only that item",
      resp.status_code == 400
      and resp.json()["error"] == "Missing document: TLC-for-hire Vehicle Permit. "
      "Please upload all required documents to complete registration.",
      resp.text[:300])
resp = anon.post(BASE + "/api/drivers/me/lookup", json={"phone": "+15550006666"},
                 timeout=TIMEOUT)
check("rejected registration leaves no driver record", resp.status_code == 404,
      str(resp.status_code))

# Car-model dropdown data + validation (2022 floor, eligible list only).
resp = anon.get(BASE + "/api/car-models", timeout=TIMEOUT)
check("car-models endpoint 200", resp.status_code == 200, str(resp.status_code))
models_payload = resp.json()
check("car-models: 133 entries (132 Uber Black + temporary Model 3)",
      len(models_payload["models"]) == 133, str(len(models_payload.get("models", []))))
check("car-models: Model 3 present (temporary exception), Model Y absent",
      "Tesla Model 3" in models_payload["models"]
      and "Tesla Model Y" not in models_payload["models"])
check("car-models: year bounds 2022..current+1",
      models_payload["min_year"] == 2022
      and models_payload["max_year"] == datetime.now(timezone.utc).year + 1,
      str(models_payload))
resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Old Car", "phone": "+15550004444", "car_model": "Cadillac Escalade",
    "car_year": "2021", "car_colour": "Black",
    "plate": "Z", "state": "New York", "bank_account_number": "1", "bank_routing_number": "2",
}, timeout=TIMEOUT)
check("year 2021 rejected (2022 floor)", resp.status_code == 400, str(resp.status_code))
resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Wrong Car", "phone": "+15550005555", "car_model": "Tesla Model Y",
    "car_year": "2024", "car_colour": "Black",
    "plate": "Z", "state": "New York", "bank_account_number": "1", "bank_routing_number": "2",
}, timeout=TIMEOUT)
check("unlisted model (Model Y) rejected", resp.status_code == 400, str(resp.status_code))

files_after = set()
for root, _dirs, names in os.walk(repo_dir):
    if "__pycache__" in root:
        continue
    for n in names:
        files_after.add(os.path.join(root, n))
check("uploads wrote no files (DB BLOBs only)", files_after == files_before,
      f"new files: {sorted(files_after - files_before)}")

# ------------------------------------------------------------- pricing -----

section("pricing via API (live geo JFK -> Times Square)")
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Verify Customer", "phone": "+15550009999", "email": "cust@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
check("booking1 create 201", resp.status_code == 201, resp.text[:200])
b1 = resp.json()["booking"]
referral_code = b1["referral_code"]
check("referral code issued on create", bool(referral_code), str(b1))
check("create status is awaiting_payment (pay before dispatch)",
      b1["status"] == "awaiting_payment", str(b1))

detail = s.get(BASE + f"/api/owner/bookings/{b1['id']}", timeout=TIMEOUT).json()
miles1 = Decimal(str(detail["miles"]))
# Live geo: the stored toll comes from the map (the OSRM route via
# the Midtown Tunnel detects $7.46). Expectations use the stored
# toll, so the formula check holds whatever the map returns.
toll1 = Decimal(str(detail["toll"]))
expected1 = compute_one_way(miles1, toll=toll1)
print(f"  INFO live geo miles for JFK->Times Square: {miles1}")
check("one-way total matches pricing formula for returned miles",
      approx(detail["customer_total"], expected1["total"]),
      f"got {detail['customer_total']} expected {expected1['total']} at {miles1} mi")
check("one-way driver matches pricing formula",
      approx(detail["driver_earnings"], expected1["driver_earnings"]),
      f"got {detail['driver_earnings']} expected {expected1['driver_earnings']}")
if miles1 == Decimal("18.0"):
    check("18.0 mi total is $162.00 + stored toll",
          approx(detail["customer_total"], Decimal("162.00") + toll1))
    check("18.0 mi fare/tax/gratuity", approx(detail["fare"], "162.00")
          and approx(detail["tax"], "0.00") and approx(detail["gratuity"], "0.00"), str(detail))
    check("18.0 mi driver is $72.00 + stored toll",
          approx(detail["driver_earnings"], Decimal("72.00") + toll1))

resp = anon.get(BASE + f"/api/bookings/{b1['id']}", timeout=TIMEOUT)
got = resp.json()["booking"]
check("customer GET before accept: total visible, driver null",
      approx(got["total"], expected1["total"]) and got["driver"] is None, str(got))
check("customer GET returns referral_code (thank-you page field)",
      got["referral_code"] == referral_code, str(got.get("referral_code")))
check("tracking hidden before en_route", got["tracking"]["visible"] is False)

# Referral booking
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Referral Customer", "phone": "+15550008888", "email": "ref@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-02", "time": "12:00", "ride_type": "one_way",
    "referral_code": referral_code,
}, timeout=TIMEOUT)
check("referral booking 201", resp.status_code == 201, resp.text[:200])
b_ref = resp.json()["booking"]
detail_ref = s.get(BASE + f"/api/owner/bookings/{b_ref['id']}", timeout=TIMEOUT).json()
toll_ref = Decimal(str(detail_ref["toll"]))
expected_ref = compute_one_way(Decimal(str(detail_ref["miles"])),
                               referral=True, toll=toll_ref)
check("referral total = formula (discount $0 for now)",
      approx(detail_ref["customer_total"], expected_ref["total"]),
      f"got {detail_ref['customer_total']} expected {expected_ref['total']}")
if Decimal(str(detail_ref["miles"])) == Decimal("18.0"):
    check("18.0 mi referral total is $162.00 + stored toll (no discount)",
          approx(detail_ref["customer_total"], Decimal("162.00") + toll_ref))

# Exact-miles regression (live 2026-11-17 booking NOEL-9TR127): the typed
# text "JFK Terminal 1 Arrivals" matches nothing in Nominatim, so the
# old code priced it on an invented 10.0 miles. Picked-suggestion
# coordinates are now priced as-is, so the same text WITH coordinates
# must book at the true road miles (~18) and match the pricing formula.
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Coords Customer", "phone": "+15550007777", "email": "coords@test.com",
    "pickup": "JFK Terminal 1 Arrivals", "dropoff": "Times Square, New York",
    "pickup_lat": 40.6434795, "pickup_lng": -73.7900299,
    "dropoff_lat": 40.7570095, "dropoff_lng": -73.9859724,
    "date": "2030-06-03", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
check("coords booking with unresolvable text 201", resp.status_code == 201, resp.text[:200])
b_coords = resp.json()["booking"]
detail_coords = s.get(BASE + f"/api/owner/bookings/{b_coords['id']}", timeout=TIMEOUT).json()
miles_coords = Decimal(str(detail_coords["miles"]))
toll_coords = Decimal(str(detail_coords["toll"]))
expected_coords = compute_one_way(miles_coords, toll=toll_coords)
print(f"  INFO coords-booking miles for JFK T1 -> Times Square: {miles_coords}")
check("coords booking uses true road miles (15-20, never the old 10.0)",
      Decimal("15") <= miles_coords <= Decimal("20"), f"miles={miles_coords}")
check("coords booking total matches pricing formula",
      approx(detail_coords["customer_total"], expected_coords["total"]),
      f"got {detail_coords['customer_total']} expected {expected_coords['total']} at {miles_coords} mi")

# Hourly booking
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Hourly Customer", "phone": "+15550006666", "email": "h@test.com",
    "pickup": "Central Park, New York", "date": "2030-06-04", "time": "14:00",
    "ride_type": "hourly", "hours": 3,
}, timeout=TIMEOUT)
check("hourly booking 201", resp.status_code == 201, resp.text[:200])
b_hourly = resp.json()["booking"]
detail_h = s.get(BASE + f"/api/owner/bookings/{b_hourly['id']}", timeout=TIMEOUT).json()
check("hourly 3h total $270.00", approx(detail_h["customer_total"], "270.00"), str(detail_h))
check("hourly 3h driver $150.00", approx(detail_h["driver_earnings"], "150.00"))
check("hourly has NO fee, NO gratuity, NO tax, NO class",
      approx(detail_h["booking_fee"], "0.00") and approx(detail_h["gratuity"], "0.00")
      and approx(detail_h["tax"], "0.00") and detail_h["vehicle_class"] is None,
      str(detail_h))

# Toll recompute on a fresh booking
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Toll Customer", "phone": "+15550005555", "email": "t@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-05", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
b_toll = resp.json()["booking"]
resp = s.post(BASE + f"/api/owner/bookings/{b_toll['id']}/toll", json={"toll": 18.50}, timeout=TIMEOUT)
check("toll update 200", resp.status_code == 200, resp.text[:200])
detail_t = s.get(BASE + f"/api/owner/bookings/{b_toll['id']}", timeout=TIMEOUT).json()
expected_t = compute_one_way(Decimal(str(detail_t["miles"])), toll=Decimal("18.50"))
check("toll $18.50 recomputes total per formula",
      approx(detail_t["customer_total"], expected_t["total"]),
      f"got {detail_t['customer_total']} expected {expected_t['total']}")
check("toll $18.50 recomputes driver per formula",
      approx(detail_t["driver_earnings"], expected_t["driver_earnings"]))
if Decimal(str(detail_t["miles"])) == Decimal("18.0"):
    check("18.0 mi + toll total is exactly $180.50", approx(detail_t["customer_total"], "180.50"))
    check("18.0 mi + toll driver is exactly $90.50", approx(detail_t["driver_earnings"], "90.50"))

# Up-front NJ return toll: NY -> NJ trips carry the $16.79 estimate
# from creation (live geo resolves the states); NJ -> NJ trips $0.
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "NJ Toll Customer", "phone": "+15550005454", "email": "nj@test.com",
    "pickup": "Terminal 1, JFK Access Road, Queens, New York, 11430, United States",
    "dropoff": "Jersey City, Hudson County, New Jersey, United States",
    "date": "2030-06-06", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
check("NJ booking 201", resp.status_code == 201, resp.text[:200])
b_nj = resp.json()["booking"]
detail_nj = s.get(BASE + f"/api/owner/bookings/{b_nj['id']}", timeout=TIMEOUT).json()
# The stored toll is the $16.79 return toll PLUS any toll the map
# detects on the outbound route (the OSRM route currently detects
# none, but the check must hold whatever the map returns).
toll_nj = Decimal(str(detail_nj["toll"]))
expected_nj = compute_one_way(Decimal(str(detail_nj["miles"])), toll=toll_nj)
check("NJ trip stored toll includes the $16.79 return toll at creation",
      toll_nj >= Decimal("16.79"), str(detail_nj.get("toll")))
check("NJ trip total matches formula incl. stored toll",
      approx(detail_nj["customer_total"], expected_nj["total"]),
      f"got {detail_nj['customer_total']} expected {expected_nj['total']}")
check("NJ trip driver matches formula incl. stored toll",
      approx(detail_nj["driver_earnings"], expected_nj["driver_earnings"]))
check("NJ trip options page totals include the toll",
      approx(b_nj["class_totals"]["sedan"], expected_nj["total"])
      and approx(b_nj["class_totals"]["suv"],
                 compute_one_way(Decimal(str(detail_nj["miles"])),
                                 toll=toll_nj,
                                 vehicle_class="suv")["total"]),
      str(b_nj.get("class_totals")))

resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "NJ Local Customer", "phone": "+15550005353", "email": "njl@test.com",
    "pickup": "Newark Liberty International Airport, Newark, Essex County, New Jersey, United States",
    "dropoff": "Jersey City, Hudson County, New Jersey, United States",
    "date": "2030-06-07", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
check("NJ->NJ booking 201", resp.status_code == 201, resp.text[:200])
b_njlocal = resp.json()["booking"]
detail_njlocal = s.get(BASE + f"/api/owner/bookings/{b_njlocal['id']}",
                       timeout=TIMEOUT).json()
check("NJ->NJ trip stored toll is $0.00",
      approx(detail_njlocal["toll"], "0.00"), str(detail_njlocal.get("toll")))

# ------------------------------------------------- class selection ---------

section("options page: form -> class totals -> pick class -> pay -> class-filtered dispatch")
anon.post(BASE + "/api/drivers/me/availability", json={"available": True},
          headers={"X-Driver-Token": token3}, timeout=TIMEOUT)
anon.post(BASE + "/api/drivers/me/availability", json={"available": True},
          headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Class Customer", "phone": "+15550004545", "email": "cc@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-06", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
check("class booking create 201", resp.status_code == 201, resp.text[:200])
b_class = resp.json()["booking"]
detail_c = s.get(BASE + f"/api/owner/bookings/{b_class['id']}", timeout=TIMEOUT).json()
miles_c = Decimal(str(detail_c["miles"]))
toll_c = Decimal(str(detail_c["toll"]))
exp_sedan = compute_one_way(miles_c, toll=toll_c)
exp_suv = compute_one_way(miles_c, vehicle_class="suv", toll=toll_c)
check("class booking defaults to sedan (Business Class)",
      b_class["vehicle_class"] == "sedan"
      and b_class["vehicle_class_label"] == "Business Class", str(b_class))
check("class_totals match both class formulas",
      approx(b_class["class_totals"]["sedan"], exp_sedan["total"])
      and approx(b_class["class_totals"]["suv"], exp_suv["total"]), str(b_class.get("class_totals")))
resp = anon.post(BASE + f"/api/bookings/{b_class['id']}/vehicle-class",
                 json={"vehicle_class": "suv"}, timeout=TIMEOUT)
check("switch to SUV 200", resp.status_code == 200, resp.text[:200])
check("SUV total + label after switch",
      approx(resp.json()["booking"]["total"], exp_suv["total"])
      and resp.json()["booking"]["vehicle_class_label"] == "Business SUV", str(resp.json()))
detail_c = s.get(BASE + f"/api/owner/bookings/{b_class['id']}", timeout=TIMEOUT).json()
check("owner breakdown matches SUV formula",
      approx(detail_c["fare"], exp_suv["fare"]) and approx(detail_c["tax"], exp_suv["tax"])
      and approx(detail_c["driver_earnings"], exp_suv["driver_earnings"])
      and approx(detail_c["profit"], exp_suv["profit"]), str(detail_c))
resp = anon.post(BASE + f"/api/bookings/{b_class['id']}/vehicle-class",
                 json={"vehicle_class": "luxury"}, timeout=TIMEOUT)
check("invalid class -> 400", resp.status_code == 400, str(resp.status_code))
resp = anon.post(BASE + f"/api/bookings/{b_hourly['id']}/vehicle-class",
                 json={"vehicle_class": "suv"}, timeout=TIMEOUT)
check("class switch on hourly -> 409", resp.status_code == 409, str(resp.status_code))
resp = anon.post(BASE + f"/api/bookings/{b_class['id']}/vehicle-class",
                 json={"vehicle_class": "sedan"}, timeout=TIMEOUT)
check("switch back to sedan restores sedan total",
      resp.status_code == 200 and approx(resp.json()["booking"]["total"], exp_sedan["total"]),
      resp.text[:200])
resp = anon.post(BASE + f"/api/bookings/{b_class['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Class Customer"}, timeout=TIMEOUT)
check("class booking pays sedan total", resp.status_code == 200
      and approx(resp.json()["payment"]["amount"], exp_sedan["total"]), resp.text[:200])
resp = anon.post(BASE + f"/api/bookings/{b_class['id']}/vehicle-class",
                 json={"vehicle_class": "suv"}, timeout=TIMEOUT)
check("class switch after payment -> 409", resp.status_code == 409, str(resp.status_code))
resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("sedan driver sees the sedan booking",
      any(o["booking_id"] == b_class["id"] for o in resp.json()), str(resp.json()))
resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token3}, timeout=TIMEOUT)
check("SUV driver does NOT see the sedan booking",
      all(o["booking_id"] != b_class["id"] for o in resp.json()), str(resp.json()))
resp = anon.post(BASE + f"/api/bookings/{b_class['id']}/cancel", json={"phone": "+15550004545"}, timeout=TIMEOUT)
check("class booking cancelled + refunded (keeps later checks clean)",
      resp.status_code == 200 and resp.json()["refund"] is True, resp.text[:150])

# SUV path: switch before paying, then only the SUV driver sees it.
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "SUV Customer", "phone": "+15550004646", "email": "suv@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-07", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
b_class2 = resp.json()["booking"]
anon.post(BASE + f"/api/bookings/{b_class2['id']}/vehicle-class",
          json={"vehicle_class": "suv"}, timeout=TIMEOUT)
anon.post(BASE + f"/api/bookings/{b_class2['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "SUV Customer"}, timeout=TIMEOUT)
resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token3}, timeout=TIMEOUT)
check("SUV driver sees the SUV booking",
      any(o["booking_id"] == b_class2["id"] for o in resp.json()), str(resp.json()))
resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("sedan driver does NOT see the SUV booking",
      all(o["booking_id"] != b_class2["id"] for o in resp.json()), str(resp.json()))
resp = anon.post(BASE + f"/api/drivers/me/offers/{b_class2['id']}/accept",
                 headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("sedan driver direct-accept of SUV booking -> 409", resp.status_code == 409, str(resp.status_code))
resp = anon.post(BASE + f"/api/bookings/{b_class2['id']}/cancel", json={"phone": "+15550004646"}, timeout=TIMEOUT)
check("SUV booking cancelled + refunded",
      resp.status_code == 200 and resp.json()["refund"] is True, resp.text[:150])

# ------------------------------------------------- pay / offers / accept ---

section("full flow: total -> pay -> offer -> accept -> trip -> invoice")
anon.post(BASE + "/api/drivers/me/availability", json={"available": True},
          headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("no offers before payment (unpaid booking never reaches drivers)",
      all(o["booking_id"] != b1["id"] for o in resp.json()), str(resp.json()))
resp = anon.post(BASE + f"/api/drivers/me/offers/{b1['id']}/accept",
                 headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("accept unpaid booking -> 409", resp.status_code == 409, str(resp.status_code))

resp = anon.post(BASE + f"/api/bookings/{b1['id']}/pay", json={
    "card_number": "4242 4242 4242 4242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Verify Customer"}, timeout=TIMEOUT)
check("pay 200", resp.status_code == 200, resp.text[:200])
pay = resp.json()["payment"]
check("payment test mode + last4 only",
      pay["test"] is True and pay["last4"] == "4242" and pay["status"] == "succeeded", str(pay))
check("payment amount = fare total", approx(pay["amount"], expected1["total"]))
check("full card number never in pay response", "4242424242424242" not in resp.text)
check("status offered after payment", resp.json()["booking"]["status"] == "offered")
detail = s.get(BASE + f"/api/owner/bookings/{b1['id']}", timeout=TIMEOUT).json()
check("owner detail payment has pi_test_ id",
      detail["payments"] and detail["payments"][0]["stripe_test_id"].startswith("pi_test_")
      and detail["payments"][0]["test"] is True, str(detail.get("payments")))

resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
offers = resp.json()
offer1 = [o for o in offers if o["booking_id"] == b1["id"]]
check("offer listed for booking1", len(offer1) == 1, str(offers))
if offer1:
    leaked = set(offer1[0]) & FORBIDDEN_OFFER_KEYS
    check("offer has NO miles/fare/total/gratuity/fee fields", not leaked, f"leaked: {leaked}")
    check("offer earnings = driver share only",
          approx(offer1[0]["earnings"], expected1["driver_earnings"]), str(offer1[0]))

resp = anon.post(BASE + f"/api/drivers/me/offers/{b1['id']}/accept",
                 headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("accept 200", resp.status_code == 200, resp.text[:200])
check("accept response has earnings only (no fare keys)",
      not (set(resp.json()["booking"]) & FORBIDDEN_OFFER_KEYS), str(resp.json()))
anon.post(BASE + "/api/drivers/me/availability", json={"available": True},
          headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
resp = anon.post(BASE + f"/api/drivers/me/offers/{b1['id']}/accept",
                 headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
check("second accept -> 409", resp.status_code == 409, str(resp.status_code))

# Active-trip endpoint (trip persistence across reloads)
resp = anon.get(BASE + "/api/drivers/me/active-trip", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
active = resp.json()["booking"]
check("active-trip returns accepted booking", active and active["id"] == b1["id"], str(active))
check("active-trip has no fare/miles keys",
      active and not (set(active) & FORBIDDEN_OFFER_KEYS), str(active))
resp = anon.get(BASE + "/api/drivers/me/active-trip", headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
check("active-trip null for driver with no trip", resp.json()["booking"] is None, str(resp.json()))
resp = anon.get(BASE + "/api/drivers/me/active-trip", timeout=TIMEOUT)
check("active-trip without token -> 401", resp.status_code == 401, str(resp.status_code))

resp = anon.get(BASE + f"/api/bookings/{b1['id']}", timeout=TIMEOUT)
got = resp.json()["booking"]
check("total still visible after accept (single total)",
      approx(got["total"], expected1["total"]), str(got["total"]))
check("driver visible after accept", got["driver"] and got["driver"]["name"] == "Verify Driver One")
check("tracking still hidden after accept", got["tracking"]["visible"] is False)

def trip_event(booking_id, event, token, **kw):
    return anon.post(BASE + f"/api/drivers/me/trip/{booking_id}/event",
                     json={"event": event, **kw}, headers={"X-Driver-Token": token}, timeout=TIMEOUT)


resp = trip_event(b1["id"], "en_route", token1, lat=40.64, lng=-73.78)
check("en_route ok", resp.status_code == 200, resp.text[:150])
resp = anon.post(BASE + f"/api/drivers/me/trip/{b1['id']}/location",
                 json={"lat": 40.70, "lng": -73.90}, headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("location update ok", resp.status_code == 200, str(resp.status_code))
resp = anon.get(BASE + f"/api/bookings/{b1['id']}", timeout=TIMEOUT)
got = resp.json()["booking"]
check("tracking visible only after en_route",
      got["tracking"]["visible"] is True and approx(got["tracking"]["lat"], 40.70), str(got["tracking"]))
resp = anon.get(BASE + "/api/drivers/me/active-trip", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("active-trip shows en_route status", resp.json()["booking"]["status"] == "en_route")
check("arrived ok", trip_event(b1["id"], "arrived", token1).status_code == 200)
check("start ok", trip_event(b1["id"], "start", token1).status_code == 200)
resp = anon.get(BASE + f"/api/bookings/{b1['id']}", timeout=TIMEOUT)
check("customer GET status in_progress after start",
      resp.json()["booking"]["status"] == "in_progress", resp.text[:200])
resp = trip_event(b1["id"], "complete", token1, waiting_minutes=75)
check("complete ok", resp.status_code == 200, resp.text[:200])
inv = resp.json().get("invoice", {})
expected_wait = waiting_charge("JFK Airport", 75)
check("waiting 75 min at airport = $15.00", approx(inv.get("waiting_charge"), expected_wait), str(inv))
check("invoice = fare + waiting",
      approx(inv.get("total"), Decimal(str(expected1["total"])) + expected_wait), str(inv))
if miles1 == Decimal("18.0"):
    check("invoice total is $177.00 + stored toll",
          approx(inv.get("total"), Decimal("177.00") + toll1))
resp = anon.get(BASE + f"/api/bookings/{b1['id']}", timeout=TIMEOUT)
got = resp.json()["booking"]
check("GET invoice after complete", got["invoice"] and approx(got["invoice"]["total"], inv.get("total")))
resp = anon.get(BASE + "/api/drivers/me/active-trip", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("active-trip null after completion", resp.json()["booking"] is None)
resp = anon.get(BASE + "/api/drivers/me/earnings", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
earn = resp.json()
check("driver earnings endpoint: 1 ride, driver share only",
      earn["completed_rides"] == 1 and approx(earn["total_earnings"], expected1["driver_earnings"])
      and earn["rides"][0]["route"] == "JFK Airport to Times Square, New York", str(earn))
resp = anon.get(BASE + f"/api/bookings/{b1['id']}/driver-photo", timeout=TIMEOUT)
check("driver photo bytes round-trip from DB", resp.status_code == 200 and resp.content == photo)

# ------------------------------------------------- owner docs + outbox -----

section("owner documents view + outbox")
resp = s.get(BASE + "/api/owner/drivers", timeout=TIMEOUT)
drivers = resp.json()
check("owner drivers list has 3 drivers", len(drivers) == 3, str(drivers))
d1row = [d for d in drivers if d["phone"] == "+15550001111"][0]
check("owner drivers: docs + doc_ids + masked bank + car",
      d1row["docs"]["fh1_insurance"] == "completed" and "fh1_insurance" in d1row["doc_ids"]
      and d1row["bank_masked"] == "••••6789" and d1row["car"] == "Cadillac CT6 (Black)",
      str(d1row))
check("full bank number never in owner drivers list",
      "123456789" not in resp.text and "021000021" not in resp.text)
doc_id = d1row["doc_ids"]["fh1_insurance"]
resp = s.get(BASE + f"/api/owner/documents/{doc_id}", timeout=TIMEOUT)
check("owner can fetch FH-1 PDF bytes", resp.status_code == 200 and resp.content == fh1_pdf,
      str(resp.status_code))
resp = s.get(BASE + f"/api/owner/drivers/{d1row['id']}/photo", timeout=TIMEOUT)
check("owner can fetch driver photo", resp.status_code == 200 and resp.content == photo)
resp = anon.get(BASE + f"/api/owner/documents/{doc_id}", timeout=TIMEOUT)
check("owner document without PIN session -> 401", resp.status_code == 401, str(resp.status_code))

resp = s.get(BASE + "/api/owner/outbox", timeout=TIMEOUT)
msgs = [m for m in resp.json() if m["booking_id"] == b1["id"]]
bodies = " ".join(m["body"] for m in msgs)
check("outbox has booking-received message", "booking received" in bodies, bodies[:300])
check("outbox has chauffeur-accepted message", "your chauffeur is" in bodies, bodies[:300])
check("outbox has invoice message", "invoice total" in bodies, bodies[:300])
check("outbox has sms + email channels", {"sms", "email"} <= {m["channel"] for m in msgs}, str(msgs))

# ------------------------------------------------- re-dispatch -------------

section("driver cancel -> auto re-dispatch, customer never knows")
resp = anon.post(BASE + f"/api/bookings/{b_ref['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Referral Customer"}, timeout=TIMEOUT)
check("referral booking paid before dispatch", resp.status_code == 200, resp.text[:150])
resp = anon.post(BASE + f"/api/drivers/me/offers/{b_ref['id']}/accept",
                 headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
check("driver2 accepts referral booking", resp.status_code == 200, resp.text[:150])
resp = trip_event(b_ref["id"], "cancel", token2)
check("driver cancel -> back to offered",
      resp.status_code == 200 and resp.json()["booking"]["status"] == "offered", resp.text[:150])
resp = anon.get(BASE + f"/api/bookings/{b_ref['id']}", timeout=TIMEOUT)
got = resp.json()["booking"]
check("customer view driver null + total still visible after re-dispatch",
      got["driver"] is None and approx(got["total"], expected_ref["total"]), str(got))
resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
check("cancelling driver excluded from offers",
      all(o["booking_id"] != b_ref["id"] for o in resp.json()))
resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("other driver still sees re-dispatched offer",
      any(o["booking_id"] == b_ref["id"] for o in resp.json()))
resp = anon.get(BASE + "/api/drivers/me/active-trip", headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
check("active-trip null for cancelling driver", resp.json()["booking"] is None)
resp = s.get(BASE + "/api/owner/outbox", timeout=TIMEOUT)
cancel_msgs = [m for m in resp.json()
               if m["booking_id"] == b_ref["id"] and "cancel" in m["body"].lower()]
check("no customer outbox message about the cancel", not cancel_msgs, str(cancel_msgs))
resp = s.get(BASE + "/api/owner/alerts", timeout=TIMEOUT)
check("owner alert records the re-dispatch",
      any(e["booking_id"] == b_ref["id"] and e["type"] == "driver_cancelled" for e in resp.json()))

# ------------------------------------------------- lookup / tokens ---------

section("registration-never-again + phone lookup")
resp = anon.get(BASE + "/api/drivers/me", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("stored token returns driver record (home, not registration)",
      resp.status_code == 200 and resp.json()["driver"]["name"] == "Verify Driver One")
resp = anon.post(BASE + "/api/drivers/me/lookup", json={"phone": "+15550001111"}, timeout=TIMEOUT)
check("phone lookup re-issues token", resp.status_code == 200
      and resp.json()["token"] != token1, resp.text[:150])
token1_new = resp.json()["token"]
resp = anon.get(BASE + "/api/drivers/me", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("old token invalid after re-issue -> 401", resp.status_code == 401, str(resp.status_code))
resp = anon.get(BASE + "/api/drivers/me", headers={"X-Driver-Token": token1_new}, timeout=TIMEOUT)
check("new token works, full record incl. docs + masked bank",
      resp.status_code == 200 and resp.json()["driver"]["docs"]["fh1_insurance"] == "completed"
      and resp.json()["driver"]["bank_masked"] == "••••6789", resp.text[:200])
token1 = token1_new
resp = anon.post(BASE + "/api/drivers/me/lookup", json={"phone": "+15550000000"}, timeout=TIMEOUT)
check("lookup unknown phone -> 404", resp.status_code == 404, str(resp.status_code))

# ------------------------------------------------- cancellation ------------

section("customer cancellation: >1h refund, <=1h full price")
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Far Customer", "phone": "+15550007777", "email": "far@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-07-01", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
b_far = resp.json()["booking"]
anon.post(BASE + f"/api/bookings/{b_far['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Far Customer"}, timeout=TIMEOUT)
anon.post(BASE + f"/api/drivers/me/offers/{b_far['id']}/accept",
          headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
resp = anon.post(BASE + f"/api/bookings/{b_far['id']}/cancel", json={"phone": "+15550000000"})
check("cancel wrong phone -> 403", resp.status_code == 403, str(resp.status_code))
resp = anon.post(BASE + f"/api/bookings/{b_far['id']}/cancel", json={"phone": "+15550007777"})
check("cancel >1h before pickup refunds",
      resp.status_code == 200 and resp.json()["refund"] is True
      and resp.json()["charge_kept"] is False, resp.text[:150])
detail = s.get(BASE + f"/api/owner/bookings/{b_far['id']}", timeout=TIMEOUT).json()
check("refunded payment marked refunded",
      detail["payments"] and detail["payments"][0]["status"] == "refunded", str(detail.get("payments")))

try:
    from zoneinfo import ZoneInfo
    now_ny = datetime.now(ZoneInfo("America/New_York")) + timedelta(minutes=30)
except Exception:
    now_ny = datetime.now(timezone.utc) + timedelta(minutes=30)  # noqa: F821
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Soon Customer", "phone": "+15550004444", "email": "soon@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": now_ny.strftime("%Y-%m-%d"), "time": now_ny.strftime("%H:%M"), "ride_type": "one_way",
}, timeout=TIMEOUT)
check("soon booking (pickup in ~30 min) 201", resp.status_code == 201, resp.text[:200])
b_soon = resp.json()["booking"]
anon.post(BASE + f"/api/bookings/{b_soon['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Soon Customer"}, timeout=TIMEOUT)
anon.post(BASE + f"/api/drivers/me/offers/{b_soon['id']}/accept",
          headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
resp = anon.post(BASE + f"/api/bookings/{b_soon['id']}/cancel", json={"phone": "+15550004444"})
check("cancel <=1h before pickup keeps full price",
      resp.status_code == 200 and resp.json()["refund"] is False
      and resp.json()["charge_kept"] is True, resp.text[:150])
detail = s.get(BASE + f"/api/owner/bookings/{b_soon['id']}", timeout=TIMEOUT).json()
check("kept payment stays succeeded",
      detail["payments"] and detail["payments"][0]["status"] == "succeeded", str(detail.get("payments")))

# ------------------------------------------------- toll after pay ----------

section("toll after payment exposes balance_due")
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Balance Customer", "phone": "+15550003333", "email": "bal@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-07-02", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
b_bal = resp.json()["booking"]
pay_resp = anon.post(BASE + f"/api/bookings/{b_bal['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Balance Customer"}, timeout=TIMEOUT)
anon.post(BASE + f"/api/drivers/me/offers/{b_bal['id']}/accept",
          headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
paid_amount = Decimal(str(pay_resp.json()["payment"]["amount"]))
detail_before = s.get(BASE + f"/api/owner/bookings/{b_bal['id']}", timeout=TIMEOUT).json()
resp = s.post(BASE + f"/api/owner/bookings/{b_bal['id']}/toll", json={"toll": 5.00}, timeout=TIMEOUT)
check("toll-after-pay 200 with balance_due", resp.status_code == 200
      and resp.json().get("balance_due") is not None, resp.text[:200])
expected_bal = compute_one_way(Decimal(str(detail_before["miles"])), toll=Decimal("5.00"))
check("balance_due = new total - paid amount",
      approx(resp.json()["balance_due"], expected_bal["total"] - paid_amount),
      f"got {resp.json().get('balance_due')} expected {expected_bal['total'] - paid_amount}")
check("paid_amount echoed", approx(resp.json().get("paid_amount"), paid_amount))

# ------------------------------------------------- reconciliation ----------

section("owner summary reconciliation")
summary = s.get(BASE + "/api/owner/summary", timeout=TIMEOUT).json()
check("summary: gross - driver_owed = profit",
      approx(Decimal(str(summary["gross"])) - Decimal(str(summary["driver_owed"])),
             summary["profit"]), str(summary))
rows = s.get(BASE + "/api/owner/bookings", timeout=TIMEOUT).json()
profit_sum = Decimal("0.00")
gross_sum = Decimal("0.00")
owed_sum = Decimal("0.00")
tax_sum = Decimal("0.00")
for row in rows:
    det = s.get(BASE + f"/api/owner/bookings/{row['id']}", timeout=TIMEOUT).json()
    statuses = [p["status"] for p in det["payments"]]
    # driver_owed counts only UNPAID completed, non-refunded trips: a
    # kept-price cancellation or no-show is never owed to a driver.
    counts_toward_owed = (row["status"] == "completed" and "refunded" not in statuses
                          and not row.get("payout_paid"))
    if counts_toward_owed:
        owed_sum += Decimal(str(row["driver_earnings"]))
    if "succeeded" in statuses:
        gross_sum += Decimal(str(row["customer_total"])) + Decimal(str(row["waiting_charge"]))
        # Profit contribution: the driver share is subtracted only for
        # trips still owed; kept-price fares count in full.
        contribution = Decimal(str(row["customer_total"])) + Decimal(str(row["waiting_charge"]))
        if counts_toward_owed:
            contribution -= Decimal(str(row["driver_earnings"]))
        profit_sum += contribution
        check(f"row profit reconciles (booking {row['id']})",
              approx(Decimal(str(row["customer_total"])) + Decimal(str(row["waiting_charge"]))
                     - Decimal(str(row["driver_earnings"])) - Decimal(str(row["tax"])),
                     row["profit"]), str(row))
        tax_sum += Decimal(str(row["tax"]))
check("per-ride profits sum to summary profit", approx(profit_sum, summary["profit"]),
      f"sum {profit_sum} vs summary {summary['profit']}")
check("per-ride gross sums to summary gross", approx(gross_sum, summary["gross"]),
      f"sum {gross_sum} vs summary {summary['gross']}")
check("per-ride driver sums to summary driver_owed", approx(owed_sum, summary["driver_owed"]),
      f"sum {owed_sum} vs summary {summary['driver_owed']}")
check("per-ride tax sums to summary tax_collected", approx(tax_sum, summary["tax_collected"]),
      f"sum {tax_sum} vs summary {summary['tax_collected']}")
check("driver_owed counts only the completed trip (kept-price cancel excluded)",
      approx(summary["driver_owed"], expected1["driver_earnings"]),
      f"owed {summary['driver_owed']} expected {expected1['driver_earnings']}")
print(f"  INFO summary: gross ${summary['gross']} profit ${summary['profit']} "
      f"driver_owed ${summary['driver_owed']} counts {summary['counts']}")

# --------------------------------------------------- payout weeks ----------

section("payout weeks: 7-day weeks, due 14 days after week start, mark paid, owed drops")
detail_b1 = s.get(BASE + f"/api/owner/bookings/{b1['id']}", timeout=TIMEOUT).json()
check("owner detail records completed_at + payout_paid false",
      detail_b1.get("completed_at") and detail_b1.get("payout_paid") is False,
      str(detail_b1.get("completed_at")))
completed_dt = datetime.fromisoformat(detail_b1["completed_at"])
expected_week = week_for(completion_date(completed_dt))
resp = anon.get(BASE + "/api/drivers/me/earnings", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
earn = resp.json()
check("earnings weeks present for completed ride", len(earn["weeks"]) == 1, str(earn.get("weeks")))
w = earn["weeks"][0] if earn["weeks"] else {}
check("week dates match completion week",
      w.get("start") == expected_week["start"].isoformat()
      and w.get("end") == expected_week["end"].isoformat()
      and w.get("due_date") == expected_week["due_date"].isoformat(), str(w))
check("week total = driver share, unpaid",
      approx(w.get("total_earnings"), expected1["driver_earnings"])
      and w.get("status") == "unpaid" and w.get("paid") is False, str(w))
check("week has no fare/miles keys", not (set(w) & FORBIDDEN_OFFER_KEYS), str(w))
check("ride row carries week + payout status",
      earn["rides"] and earn["rides"][0].get("week_start") == expected_week["start"].isoformat()
      and earn["rides"][0].get("payout_status") == "unpaid", str(earn.get("rides")))
resp = s.get(BASE + "/api/owner/payouts", timeout=TIMEOUT)
payouts = resp.json()
check("owner payouts lists the completed week", len(payouts) == 1, str(payouts))
p = payouts[0] if payouts else {}
check("owner payout row: driver, due date, total",
      p.get("driver_name") == "Verify Driver One"
      and p.get("due_date") == expected_week["due_date"].isoformat()
      and approx(p.get("total_earnings"), expected1["driver_earnings"]), str(p))
resp = anon.get(BASE + "/api/owner/payouts", timeout=TIMEOUT)
check("owner payouts without PIN -> 401", resp.status_code == 401, str(resp.status_code))
resp = anon.post(BASE + "/api/owner/payouts/mark-paid",
                 json={"driver_id": d1row["id"], "week_index": expected_week["index"]},
                 timeout=TIMEOUT)
check("mark-paid without PIN -> 401", resp.status_code == 401, str(resp.status_code))
resp = s.post(BASE + "/api/owner/payouts/mark-paid",
              json={"driver_id": d1row["id"], "week_index": expected_week["index"]},
              timeout=TIMEOUT)
check("mark-paid 200, week paid",
      resp.status_code == 200 and resp.json()["payout"]["paid"] is True, resp.text[:200])
resp = s.post(BASE + "/api/owner/payouts/mark-paid",
              json={"driver_id": d1row["id"], "week_index": expected_week["index"]},
              timeout=TIMEOUT)
check("mark-paid again idempotent (marked 0)",
      resp.status_code == 200 and resp.json()["payout"]["marked"] == 0, resp.text[:150])
resp = s.post(BASE + "/api/owner/payouts/mark-paid",
              json={"driver_id": d1row["id"], "week_index": 999}, timeout=TIMEOUT)
check("mark-paid empty week -> 404", resp.status_code == 404, str(resp.status_code))
summary2 = s.get(BASE + "/api/owner/summary", timeout=TIMEOUT).json()
check("driver_owed drops to 0 after mark-paid", approx(summary2["driver_owed"], 0), str(summary2))
check("profit equals gross once nothing owed",
      approx(summary2["profit"], summary2["gross"]), str(summary2))
resp = anon.get(BASE + "/api/drivers/me/earnings", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("driver week shows paid after mark-paid",
      resp.json()["weeks"] and resp.json()["weeks"][0]["status"] == "paid",
      str(resp.json().get("weeks")))

# --------------------------------- free features: name sign, chat, extra distance, assign ---

section("free features: name sign, chat, extra distance, assign")
resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Verify Driver SUV", "phone": "+15550004444", "email": "d3@test.com",
    "car_model": "Cadillac Escalade", "car_year": "2024", "car_colour": "Black", "plate": "T33333",
    "state": "New York", "bank_account_number": "555555555", "bank_routing_number": "021000021",
}, files=all_docs, timeout=TIMEOUT)
check("driver3 (SUV) register 201", resp.status_code == 201, resp.text[:200])
d3 = resp.json()["driver"]
token3 = resp.json()["token"]
anon.post(BASE + "/api/drivers/me/availability", json={"available": True},
          headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
anon.post(BASE + "/api/drivers/me/availability", json={"available": True},
          headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
anon.post(BASE + "/api/drivers/me/availability", json={"available": True},
          headers={"X-Driver-Token": token3}, timeout=TIMEOUT)
resp = anon.post(BASE + "/api/bookings", json={
    "customer_name": "Free Feature Customer", "phone": "+15550007777",
    "email": "ff@test.com", "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-06", "time": "12:00", "ride_type": "one_way",
}, timeout=TIMEOUT)
check("free-features booking 201", resp.status_code == 201, resp.text[:200])
bx = resp.json()["booking"]
resp = s.post(BASE + f"/api/owner/bookings/{bx['id']}/assign",
              json={"driver_id": d1["id"]}, timeout=TIMEOUT)
check("assign before payment -> 409", resp.status_code == 409, str(resp.status_code))
resp = anon.post(BASE + f"/api/bookings/{bx['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Free Feature Customer"}, timeout=TIMEOUT)
check("free-features booking paid", resp.status_code == 200, resp.text[:150])
resp = s.post(BASE + f"/api/owner/bookings/{bx['id']}/assign",
              json={"driver_id": 999999}, timeout=TIMEOUT)
check("assign unknown driver -> 404", resp.status_code == 404, str(resp.status_code))
resp = s.post(BASE + f"/api/owner/bookings/{bx['id']}/assign",
              json={"driver_id": d3["id"]}, timeout=TIMEOUT)
check("assign wrong-class (SUV) driver -> 409", resp.status_code == 409, str(resp.status_code))
resp = s.post(BASE + f"/api/owner/bookings/{bx['id']}/assign",
              json={"driver_id": d1["id"]}, timeout=TIMEOUT)
check("assign to driver1 200", resp.status_code == 200
      and resp.json()["booking"]["assigned_driver_id"] == d1["id"], resp.text[:200])
resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
check("assigned booking hidden from driver2",
      all(o["booking_id"] != bx["id"] for o in resp.json()), str(resp.json()))
resp = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("assigned booking visible to driver1",
      any(o["booking_id"] == bx["id"] for o in resp.json()), str(resp.json()))
resp = anon.post(BASE + f"/api/drivers/me/offers/{bx['id']}/accept", json={},
                 headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
check("other driver accept -> 409", resp.status_code == 409, str(resp.status_code))
resp = anon.post(BASE + f"/api/drivers/me/offers/{bx['id']}/accept", json={},
                 headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("assigned driver accepts", resp.status_code == 200, resp.text[:150])
trip = resp.json()["booking"]
check("accept payload carries customer name + airport flag (name sign)",
      trip["customer_name"] == "Free Feature Customer" and trip["airport_pickup"] is True, str(trip))
check("accept payload: no forbidden money keys",
      FORBIDDEN_OFFER_KEYS.isdisjoint(trip.keys()), str(sorted(trip.keys())))
resp = anon.get(BASE + f"/api/bookings/{bx['id']}/messages",
                params={"phone": "+10000000000"}, timeout=TIMEOUT)
check("customer chat wrong phone -> 403", resp.status_code == 403, str(resp.status_code))
resp = anon.post(BASE + f"/api/drivers/me/trip/{bx['id']}/messages",
                 json={"text": "I am at Terminal 4 arrivals."},
                 headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("driver chat send 201", resp.status_code == 201, resp.text[:150])
resp = anon.get(BASE + f"/api/bookings/{bx['id']}/messages",
                params={"phone": "+15550007777"}, timeout=TIMEOUT)
msgs = resp.json()["messages"]
check("customer reads driver message", resp.status_code == 200 and len(msgs) == 1
      and msgs[0]["sender"] == "driver", str(msgs))
check("chat message payload has no money keys",
      msgs and FORBIDDEN_OFFER_KEYS.isdisjoint(msgs[0].keys())
      and set(msgs[0].keys()) == {"id", "sender", "text", "created_at"}, str(msgs))
resp = anon.post(BASE + f"/api/bookings/{bx['id']}/messages",
                 json={"phone": "+15550007777", "text": "On my way out."}, timeout=TIMEOUT)
check("customer chat send 201", resp.status_code == 201, resp.text[:150])
resp = anon.get(BASE + f"/api/drivers/me/trip/{bx['id']}/messages",
                headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("driver reads both messages", resp.status_code == 200
      and len(resp.json()["messages"]) == 2, str(resp.json()))
resp = anon.get(BASE + f"/api/drivers/me/trip/{bx['id']}/messages",
                headers={"X-Driver-Token": token2}, timeout=TIMEOUT)
check("other driver chat -> 403", resp.status_code == 403, str(resp.status_code))
detail_before = s.get(BASE + f"/api/owner/bookings/{bx['id']}", timeout=TIMEOUT).json()
miles_x = Decimal(str(detail_before["miles"]))
expected_x = compute_one_way(miles_x, toll=Decimal(str(detail_before["toll"])))
extra = compute_extra_distance(Decimal("4"), "sedan")
check("extra distance pricing: 4mi sedan", extra["total"] == Decimal("36.00")
      and extra["gratuity"] == Decimal("0.00") and extra["tax"] == Decimal("0.00")
      and extra["driver_addition"] == Decimal("16.00"), str(extra))
check("trip en_route ok", trip_event(bx["id"], "en_route", token1).status_code == 200)
check("trip arrived ok", trip_event(bx["id"], "arrived", token1).status_code == 200)
check("trip start ok", trip_event(bx["id"], "start", token1).status_code == 200)
resp = trip_event(bx["id"], "complete", token1, waiting_minutes=0, extra_miles=4)
check("complete with 4 extra miles ok", resp.status_code == 200, resp.text[:150])
check("driver complete response has no extra-distance field",
      "extra_distance_charge" not in resp.json().get("invoice", {}), str(resp.json()))
detail_after = s.get(BASE + f"/api/owner/bookings/{bx['id']}", timeout=TIMEOUT).json()
check("owner total = formula + extra distance",
      approx(detail_after["customer_total"], expected_x["total"] + extra["total"]),
      f"got {detail_after['customer_total']} expected {expected_x['total'] + extra['total']}")
check("owner driver = formula + extra driver pay",
      approx(detail_after["driver_earnings"], expected_x["driver_earnings"] + extra["driver_addition"]),
      f"got {detail_after['driver_earnings']}")
check("owner extra-distance line stored",
      approx(detail_after["extra_distance_charge"], extra["total"])
      and approx(detail_after["extra_miles"], "4.0"), str(detail_after))
resp = anon.get(BASE + f"/api/bookings/{bx['id']}", timeout=TIMEOUT)
inv = resp.json()["booking"]["invoice"]
check("customer invoice total includes extra distance",
      approx(inv["total"], expected_x["total"] + extra["total"])
      and approx(inv["extra_distance_charge"], extra["total"]), str(inv))

# ------------------------------------------------- static + greps -----------

section("static pages + banned-string + no-sending greps")
for path, needle in (("/", "View options"), ("/driver", "Driver registration"),
                     ("/owner", "Owner dashboard")):
    r = anon.get(BASE + path, timeout=TIMEOUT)
    check(f"page {path} 200 with real HTML", r.status_code == 200 and needle in r.text,
          f"{r.status_code} {r.text[:80]}")
for path in ("/static/js/customer.js", "/static/js/driver.js", "/static/js/owner.js",
             "/static/css/customer.css", "/static/css/driver.css", "/static/css/owner.css"):
    r = anon.get(BASE + path, timeout=TIMEOUT)
    check(f"static {path} 200", r.status_code == 200 and len(r.content) > 100, str(r.status_code))
r = anon.get(BASE + "/static/js/driver.js", timeout=TIMEOUT)
check("served driver.js has Pick up / Drop off route labels",
      "route-label" in r.text and "Pick up" in r.text and "Drop off" in r.text
      and "routeHtml(o.pickup, o.dropoff)" in r.text
      and "routeHtml(t.pickup, t.dropoff)" in r.text,
      "labels or route render calls missing from served driver.js")
check("served driver.js stages trip navigation (pickup until picked up)",
      "function tripNavDestination(stageIndex, pickup, dropoff)" in r.text
      and "if (stageIndex < 3) return pickup || null;" in r.text
      and "return dropoff || null;" in r.text
      and "tripNavLinksHtml(state.stageIndex, t.pickup, t.dropoff)" in r.text
      and "renderTripNavLinks();" in r.text,
      "staged navigation helpers or wiring missing from served driver.js")
check("served driver.js keeps offer-card links, trip screen drops payload URLs",
      "esc(o.route_url)" in r.text
      and "esc(o.route_waze_url)" in r.text
      and "esc(t.route_url)" not in r.text
      and "esc(t.route_waze_url)" not in r.text,
      "offer-card links changed or trip screen still uses un-staged URLs")
check("served driver.js hides cancel button within 2 hours of pickup",
      "function refreshCancelButton()" in r.text
      and "pickup.getTime() - Date.now() <= 2 * 60 * 60000" in r.text
      and "trip-cancel-locked-note" in r.text
      and "refreshCancelButton();" in r.text,
      "cancel-lock gating missing from served driver.js")
r = anon.get(BASE + "/static/js/customer.js", timeout=TIMEOUT)
check("served customer.js sends picked-suggestion coordinates with bookings",
      "payload.pickup_lat = state.pickupPlace.lat" in r.text
      and "payload.pickup_lng = state.pickupPlace.lon" in r.text
      and "payload.dropoff_lat = state.dropoffPlace.lat" in r.text
      and "payload.dropoff_lng = state.dropoffPlace.lon" in r.text,
      "suggestion coordinates missing from served customer.js booking payload")
r = anon.get(BASE + "/driver", timeout=TIMEOUT)
check("driver page carries the cancel-locked note",
      "trip-cancel-locked-note" in r.text
      and "pickup is within 2 hours" in r.text,
      "cancel-locked note missing from served driver page")
r = anon.get(BASE + "/static/js/driver.js", timeout=TIMEOUT)
check("served driver.js pops a nav chooser on heading/pickup stages",
      "function showNavChooser(dest, title)" in r.text
      and "function maybeShowNavChooser(advancedStage)" in r.text
      and "maybeShowNavChooser(current);" in r.text
      and "nav-chooser-overlay" in r.text
      and 'window.open(urls.google, "_blank", "noopener");' in r.text
      and 'window.open(urls.waze, "_blank", "noopener");' in r.text,
      "nav chooser helpers or wiring missing from served driver.js")
check("served driver.js gates registration on all compulsory documents",
      "Missing document: " in r.text
      and "missingDocs.join" in r.text
      and "Please upload all required documents to complete registration." in r.text,
      "compulsory-documents gate missing from served driver.js")
r = anon.get(BASE + "/driver", timeout=TIMEOUT)
check("driver page carries the nav chooser overlay",
      "nav-chooser-overlay" in r.text
      and "nav-chooser-google" in r.text
      and "nav-chooser-waze" in r.text
      and "nav-chooser-close" in r.text,
      "nav chooser overlay missing from served driver page")
check("driver page states all documents are required, no count shown",
      "All items are required" in r.text
      and "All 7 items are required" not in r.text
      and "registration cannot be completed until every document is uploaded" in r.text,
      "compulsory-documents note missing from served driver page")
r = anon.get(BASE + "/static/css/driver.css", timeout=TIMEOUT)
check("served driver.css styles route labels",
      ".route-label" in r.text, "route-label rule missing from served driver.css")

banned = [r"\$9", r"\$10", r"\$7", r"\$20", r"\$4", r"\$90", r"\$50", r"\$11", r"\$12",
          "per mile", "booking fee", "gratuity", "dispatch", "Book a ride"]
customer_driver_files = ["static/index.html", "static/driver.html",
                         "static/css/customer.css", "static/css/driver.css",
                         "static/js/customer.js", "static/js/driver.js"]
hits = []
for rel in customer_driver_files:
    text = open(os.path.join(repo_dir, rel), encoding="utf-8").read()
    for pat in banned:
        for m in re.finditer(pat, text):
            hits.append(f"{rel}: {pat} @ {text[max(0, m.start()-30):m.end()+30]!r}")
check("zero banned rate strings in customer/driver files", not hits, "; ".join(hits[:3]))
dollar_literals = set()
for rel in customer_driver_files:
    text = open(os.path.join(repo_dir, rel), encoding="utf-8").read()
    for m in re.finditer(r"\$[0-9][^\s<\"']*", text):
        dollar_literals.add(m.group(0).rstrip(".,"))
check("only permitted dollar literal is $1/min",
      dollar_literals <= {"$1/min"}, str(sorted(dollar_literals)))
idx = open(os.path.join(repo_dir, "static/index.html"), encoding="utf-8").read()
check("options page present in index.html",
      "View options" in idx and "Choose your experience" in idx
      and "Business Class" in idx and "Business SUV" in idx
      and "class-step" in idx and "class-trip-summary" in idx, "missing options copy")

backend_files = ["app.py", "pricing.py", "geo.py"]
send_hits = []
for rel in backend_files:
    for i, line in enumerate(open(os.path.join(repo_dir, rel), encoding="utf-8"), 1):
        low = line.lower()
        if ("stripe_test_id" in low or "no stripe" in low or "test mode" in low
                or "sends sms or email" in low):
            continue
        if re.search(r"\bstripe\b|twilio|smtp|sendgrid|send_mail|smtplib|import requests", low):
            send_hits.append(f"{rel}:{i}: {line.strip()[:100]}")
check("zero real sending / Stripe calls in backend", not send_hits, "; ".join(send_hits[:3]))
app_src = open(os.path.join(repo_dir, "app.py"), encoding="utf-8").read()
check("postgres:// rewrite code path exists",
      'database_url.startswith("postgres://")' in app_src
      and 'database_url.replace("postgres://", "postgresql://", 1)' in app_src)
# Image.open() reads from in-memory bytes (BytesIO) for the
# profile-photo shape/size check — not a filesystem file write.
check("uploads stored as DB BLOBs (LargeBinary, no file writes)",
      "LargeBinary" in app_src and "open(" not in app_src.replace("openViewer", "").replace("Image.open(", ""))

# ------------------------------------------------- clear all rides --------
# TEMPORARY TEST-ONLY (remove with the endpoint, before real launch).
# Runs LAST: it deletes every booking, so nothing after it may need
# ride state. Owner decision 2026-11-17: clear the test rides and
# restart the same test fresh; drivers and documents stay untouched.

section("owner clear all rides")
r = anon.post(BASE + "/api/owner/clear-rides", json={}, timeout=TIMEOUT)
check("clear-rides without login -> 401", r.status_code == 401, str(r.status_code))
r = s.get(BASE + "/api/owner/bookings", timeout=TIMEOUT)
before = len(r.json()) if r.status_code == 200 else 0
check("bookings exist before clear", before > 0, str(before))
r = s.post(BASE + "/api/owner/clear-rides", json={}, timeout=TIMEOUT)
check("clear-rides ok", r.status_code == 200 and r.json().get("cleared") is True, r.text[:150])
deleted = r.json().get("deleted", {}) if r.status_code == 200 else {}
check("clear-rides deleted all bookings", deleted.get("bookings") == before, str(deleted))
check("clear-rides deleted chat/events/outbox/payments",
      deleted.get("chat_messages", 0) > 0 and deleted.get("booking_events", 0) > 0
      and deleted.get("outbox_messages", 0) > 0 and deleted.get("payments", 0) > 0, str(deleted))
r = s.get(BASE + "/api/owner/bookings", timeout=TIMEOUT)
check("owner bookings empty after clear", r.status_code == 200 and r.json() == [], r.text[:100])
r = s.get(BASE + "/api/owner/alerts", timeout=TIMEOUT)
check("owner alerts empty after clear", r.status_code == 200 and r.json() == [], r.text[:100])
r = s.get(BASE + "/api/owner/outbox", timeout=TIMEOUT)
check("owner outbox empty after clear", r.status_code == 200 and r.json() == [], r.text[:100])
r = s.get(BASE + "/api/owner/drivers", timeout=TIMEOUT)
drivers = r.json() if r.status_code == 200 else []
check("drivers kept after clear", len(drivers) >= 1, str(drivers)[:150])
r = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("driver token still works, offers empty after clear",
      r.status_code == 200 and r.json() == [], r.text[:100])
r = anon.get(BASE + "/owner", timeout=TIMEOUT)
check("owner page has Clear all rides button",
      r.status_code == 200 and 'id="clear-rides-btn"' in r.text and "Clear all rides" in r.text,
      str(r.status_code))
r = anon.get(BASE + "/static/js/owner.js", timeout=TIMEOUT)
check("owner.js wires clear-rides with confirm",
      r.status_code == 200 and "/api/owner/clear-rides" in r.text and "window.confirm(" in r.text,
      str(r.status_code))

# ------------------------------------------------- remove all drivers -----
# TEMPORARY TEST-ONLY (remove with the endpoint, before real launch).
# Runs LAST, after clear-rides: it removes every driver, so nothing
# after it may need driver state. Owner decision 2026-11-17: remove
# all registered drivers so everyone re-registers fresh with the
# state selector. Ride history is kept (bookings were already cleared
# above, so bookings_unlinked is 0 here).

section("owner remove all drivers")
r = anon.post(BASE + "/api/owner/clear-drivers", json={}, timeout=TIMEOUT)
check("clear-drivers without login -> 401", r.status_code == 401, str(r.status_code))
r = s.get(BASE + "/api/owner/drivers", timeout=TIMEOUT)
before_drivers = len(r.json()) if r.status_code == 200 else 0
check("drivers exist before clear", before_drivers > 0, str(before_drivers))
r = s.post(BASE + "/api/owner/clear-drivers", json={}, timeout=TIMEOUT)
check("clear-drivers ok", r.status_code == 200 and r.json().get("cleared") is True, r.text[:150])
deleted = r.json().get("deleted", {}) if r.status_code == 200 else {}
check("clear-drivers removed all drivers and documents",
      deleted.get("drivers") == before_drivers and deleted.get("documents", 0) > 0, str(deleted))
r = s.get(BASE + "/api/owner/drivers", timeout=TIMEOUT)
check("owner drivers empty after clear", r.status_code == 200 and r.json() == [], r.text[:100])
r = anon.get(BASE + "/api/drivers/me/offers", headers={"X-Driver-Token": token1}, timeout=TIMEOUT)
check("driver token rejected after removal", r.status_code == 401, str(r.status_code))
r = s.post(BASE + "/api/owner/clear-drivers", json={}, timeout=TIMEOUT)
check("clear-drivers idempotent on empty db",
      r.status_code == 200 and r.json()["deleted"]["drivers"] == 0, r.text[:150])
r = anon.get(BASE + "/owner", timeout=TIMEOUT)
check("owner page has Remove all drivers button",
      r.status_code == 200 and 'id="clear-drivers-btn"' in r.text and "Remove all drivers" in r.text,
      str(r.status_code))
r = anon.get(BASE + "/static/js/owner.js", timeout=TIMEOUT)
check("owner.js wires clear-drivers with confirm and counts",
      r.status_code == 200 and "/api/owner/clear-drivers" in r.text
      and "window.confirm(" in r.text and "window.alert(" in r.text,
      str(r.status_code))
# --- per-state document lists over HTTP (owner order 2026-11-17) ---
r = anon.get(BASE + "/api/states", timeout=TIMEOUT)
payload = r.json() if r.status_code == 200 else {}
reqs = payload.get("requirements", {})
check("states endpoint lists 51 jurisdictions",
      r.status_code == 200 and len(payload.get("states", [])) == 51, str(r.status_code))
check("every state serves its own list, profile first, license second",
      len(reqs) == 51 and all(
          req["docs"] and req["docs"][0] == "profile_picture"
          and req["docs"][1] == "dmv_license" for req in reqs.values()),
      str(len(reqs)))
check("DC serves the verified Face ID list",
      reqs.get("District of Columbia", {}).get("docs") == [
          "profile_picture", "dmv_license", "dc_drivers_record", "dc_ssc",
          "dc_residency", "dc_medical_form", "dc_face_id",
          "dc_public_vehicle_license", "vehicle_registration", "dc_inspection",
          "insurance_card"], str(reqs.get("District of Columbia")))
check("Washington serves the verified DOL list",
      reqs.get("Washington", {}).get("docs") == [
          "profile_picture", "dmv_license", "wa_medical_certificate",
          "wa_driving_record", "wa_carrier_license", "wa_vehicle_certificate",
          "wa_chauffeur_addendum", "wa_fh_registration", "wa_inspection_report",
          "wa_insurance_certificate"], str(reqs.get("Washington")))
check("Florida and Illinois stay generic, no city list statewide",
      reqs.get("Florida", {}).get("docs") == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "insurance_card"]
      and reqs.get("Illinois", {}).get("docs") == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "insurance_card"], str(reqs.get("Florida")))
check("owner-review note hidden only for the 6 verified states",
      all(reqs[s]["local_note"] is False for s in
          ("New York", "New Jersey", "District of Columbia", "Maine",
           "Rhode Island", "Washington"))
      and reqs.get("California", {}).get("local_note") is True
      and reqs.get("Alaska", {}).get("local_note") is True)
check("states payload carries no count or quantity field",
      "count" not in payload and "quantity" not in payload
      and all("count" not in req and "quantity" not in req
              for req in reqs.values()))
# --- city picker over HTTP (owner order 2026-11-17, Uber-style) ------
cities = payload.get("cities", {})
overrides = payload.get("city_requirements", {})
check("cities served for all 51 jurisdictions, Other city fallback last",
      len(cities) == 51
      and all(names and names[-1] == "Other city"
              and names[:-1] == sorted(names[:-1])
              for names in cities.values()), str(len(cities)))
check("Dallas, Buffalo, Rochester, Syracuse, Yonkers + Southeast + Midwest + Northeast + South Central + West batches are the city-specific lists, Fort Worth falls back",
      set(overrides) == {"Texas", "New York", "Alabama", "Florida",
                         "Louisiana", "Mississippi", "North Carolina",
                         "South Carolina", "Tennessee", "Illinois",
                         "Indiana", "Minnesota", "Missouri", "Nebraska",
                         "Ohio", "Wisconsin", "Maine", "Massachusetts",
                         "New Jersey", "Pennsylvania", "Arkansas", "Idaho",
                         "Nevada", "Oklahoma", "Utah", "Wyoming",
                         "Oregon"}
      and set(overrides["Texas"]) == {"Dallas", "Austin", "Houston",
                                         "San Antonio"}
      and set(overrides["New York"]) == {"Buffalo", "Rochester",
                                         "Syracuse", "Yonkers"}
      and set(overrides["Alabama"]) == {"Birmingham", "Huntsville",
                                        "Mobile", "Montgomery"}
      and set(overrides["Florida"]) == {"Miami", "Orlando",
                                        "Tallahassee", "Tampa"}
      and set(overrides["Louisiana"]) == {"Baton Rouge", "New Orleans"}
      and set(overrides["Mississippi"]) == {"Biloxi", "Gulfport"}
      and set(overrides["North Carolina"]) == {"Charlotte", "Durham"}
      and set(overrides["South Carolina"]) == {"Charleston"}
      and set(overrides["Tennessee"]) == {"Nashville"}
      and sum(len(c) for c in overrides.values()) == 62
      and overrides["Texas"]["Dallas"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "dallas_commercial_insurance", "dallas_driver_permit",
          "dallas_limo_permit"]
      and overrides["Texas"]["Dallas"]["local_note"] is False
      and overrides["New York"]["Buffalo"]["docs"] == [
          "profile_picture", "dmv_license",
          "buffalo_taxi_driver_license", "vehicle_registration",
          "buffalo_insurance_certificate", "buffalo_inspection_report"]
      and overrides["New York"]["Buffalo"]["local_note"] is True
      and overrides["New York"]["Rochester"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "rochester_taxi_driver_license", "rochester_hack_certificate",
          "rochester_insurance"]
      and overrides["New York"]["Rochester"]["local_note"] is True
      and overrides["New York"]["Syracuse"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "syracuse_hack_license", "syracuse_ground_transportation",
          "syracuse_for_hire_insurance"]
      and overrides["New York"]["Syracuse"]["local_note"] is True
      and overrides["New York"]["Yonkers"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "wctlc_driver_permit", "wctlc_vehicle_permit",
          "wctlc_insurance", "wctlc_defensive_driving"]
      and overrides["New York"]["Yonkers"]["local_note"] is True
      and overrides["Alabama"]["Birmingham"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "birmingham_operator_permit"]
      and overrides["Alabama"]["Birmingham"]["local_note"] is True
      and overrides["Alabama"]["Huntsville"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "huntsville_chauffeur_license"]
      and overrides["Alabama"]["Huntsville"]["local_note"] is True
      and overrides["Alabama"]["Mobile"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "mobile_chauffeur_license"]
      and overrides["Alabama"]["Mobile"]["local_note"] is False
      and overrides["Alabama"]["Montgomery"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "montgomery_chauffeur_license"]
      and overrides["Alabama"]["Montgomery"]["local_note"] is True
      and overrides["Florida"]["Miami"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "miami_chauffeur_registration"]
      and overrides["Florida"]["Miami"]["local_note"] is True
      and overrides["Florida"]["Orlando"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "orlando_driver_permit", "orlando_insurance"]
      and overrides["Florida"]["Orlando"]["local_note"] is False
      and overrides["Florida"]["Tallahassee"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "tallahassee_driver_permit"]
      and overrides["Florida"]["Tallahassee"]["local_note"] is True
      and overrides["Florida"]["Tampa"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "tampa_pvdl", "tampa_transcript"]
      and overrides["Florida"]["Tampa"]["local_note"] is False
      and overrides["Louisiana"]["Baton Rouge"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "baton_rouge_chauffeur_license", "baton_rouge_driving_record",
          "baton_rouge_clearance"]
      and overrides["Louisiana"]["Baton Rouge"]["local_note"] is False
      and overrides["Louisiana"]["New Orleans"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "new_orleans_driver_permit", "new_orleans_mvr"]
      and overrides["Louisiana"]["New Orleans"]["local_note"] is False
      and overrides["Mississippi"]["Biloxi"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "mvfha_driver_permit"]
      and overrides["Mississippi"]["Biloxi"]["local_note"] is False
      and overrides["Mississippi"]["Gulfport"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "mvfha_driver_permit"]
      and overrides["Mississippi"]["Gulfport"]["local_note"] is False
      and overrides["North Carolina"]["Charlotte"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "charlotte_pvh_permit", "charlotte_driving_record"]
      and overrides["North Carolina"]["Charlotte"]["local_note"] is True
      and overrides["North Carolina"]["Durham"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "durham_pvfh_permit"]
      and overrides["North Carolina"]["Durham"]["local_note"] is True
      and overrides["South Carolina"]["Charleston"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "charleston_chauffeur_license", "charleston_driving_record"]
      and overrides["South Carolina"]["Charleston"]["local_note"] is True
      and overrides["Tennessee"]["Nashville"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "nashville_opvh_permit", "nashville_mvr"]
      and overrides["Tennessee"]["Nashville"]["local_note"] is True,
      str(overrides))
check("Midwest batch overrides: 18 cities; Fort Wayne, Sioux Falls, Toledo fall back",
      set(overrides["Illinois"]) == {"Chicago", "Rockford", "Springfield"}
      and set(overrides["Indiana"]) == {"Evansville", "Indianapolis"}
      and set(overrides["Minnesota"]) == {"Minneapolis", "Rochester",
                                          "Saint Paul"}
      and set(overrides["Missouri"]) == {"Columbia", "Independence",
                                         "Jefferson City", "Kansas City",
                                         "Saint Louis"}
      and set(overrides["Nebraska"]) == {"Lincoln"}
      and set(overrides["Ohio"]) == {"Columbus"}
      and set(overrides["Wisconsin"]) == {"Kenosha", "Madison", "Milwaukee"}
      and "Fort Wayne" not in overrides["Indiana"]
      and "Toledo" not in overrides["Ohio"]
      and "South Dakota" not in overrides
      and overrides["Illinois"]["Chicago"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "chicago_chauffeur_license", "chicago_livery_vehicle_license",
          "chicago_insurance_certificate"]
      and overrides["Illinois"]["Chicago"]["local_note"] is False
      and overrides["Illinois"]["Rockford"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "rockford_taxi_driver_license"]
      and overrides["Illinois"]["Rockford"]["local_note"] is False
      and overrides["Illinois"]["Springfield"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "springfield_il_taxi_driver_license"]
      and overrides["Illinois"]["Springfield"]["local_note"] is True
      and overrides["Indiana"]["Evansville"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "evansville_taxi_driver_license"]
      and overrides["Indiana"]["Evansville"]["local_note"] is False
      and overrides["Indiana"]["Indianapolis"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "indianapolis_operator_license", "indianapolis_training_certificate",
          "indianapolis_bmv_record"]
      and overrides["Indiana"]["Indianapolis"]["local_note"] is True
      and overrides["Minnesota"]["Minneapolis"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "minneapolis_taxi_driver_license", "minneapolis_training_certificate"]
      and overrides["Minnesota"]["Minneapolis"]["local_note"] is True
      and overrides["Minnesota"]["Rochester"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "rochester_mn_taxi_driver_license"]
      and overrides["Minnesota"]["Rochester"]["local_note"] is True
      and overrides["Minnesota"]["Saint Paul"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "saint_paul_taxi_driver_license", "saint_paul_training_proof"]
      and overrides["Minnesota"]["Saint Paul"]["local_note"] is False
      and overrides["Missouri"]["Columbia"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "columbia_chauffeur_license"]
      and overrides["Missouri"]["Columbia"]["local_note"] is True
      and overrides["Missouri"]["Independence"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "independence_vehicle_driver_permit"]
      and overrides["Missouri"]["Independence"]["local_note"] is True
      and overrides["Missouri"]["Jefferson City"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "jefferson_city_taxi_driver_permit", "jefferson_city_driving_record"]
      and overrides["Missouri"]["Jefferson City"]["local_note"] is True
      and overrides["Missouri"]["Kansas City"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "kansas_city_driver_certificate", "kansas_city_operating_record"]
      and overrides["Missouri"]["Kansas City"]["local_note"] is True
      and overrides["Missouri"]["Saint Louis"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "saint_louis_mtc_license", "saint_louis_driver_history"]
      and overrides["Missouri"]["Saint Louis"]["local_note"] is True
      and overrides["Nebraska"]["Lincoln"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "lincoln_taxi_driver_license"]
      and overrides["Nebraska"]["Lincoln"]["local_note"] is True
      and overrides["Ohio"]["Columbus"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "columbus_vfh_license", "columbus_bmv_abstract"]
      and overrides["Ohio"]["Columbus"]["local_note"] is True
      and overrides["Wisconsin"]["Kenosha"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "kenosha_taxi_driver_license"]
      and overrides["Wisconsin"]["Kenosha"]["local_note"] is True
      and overrides["Wisconsin"]["Madison"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "madison_ppv_permit"]
      and overrides["Wisconsin"]["Madison"]["local_note"] is False
      and overrides["Wisconsin"]["Milwaukee"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "milwaukee_ppv_license"]
      and overrides["Wisconsin"]["Milwaukee"]["local_note"] is False,
      str(overrides))
check("Northeast batch overrides: 7 cities; Newark, Rutland fall back",
      set(overrides["Maine"]) == {"Portland", "South Portland"}
      and set(overrides["Massachusetts"]) == {"Lowell", "Springfield",
                                              "Worcester"}
      and set(overrides["New Jersey"]) == {"Jersey City"}
      and set(overrides["Pennsylvania"]) == {"Philadelphia"}
      and "Newark" not in overrides["New Jersey"]
      and "Vermont" not in overrides
      and overrides["Maine"]["Portland"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "portland_me_livery_license"]
      and overrides["Maine"]["Portland"]["local_note"] is True
      and overrides["Maine"]["South Portland"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "south_portland_taxi_driver_license"]
      and overrides["Maine"]["South Portland"]["local_note"] is True
      and overrides["Massachusetts"]["Lowell"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "lowell_hackney_license"]
      and overrides["Massachusetts"]["Lowell"]["local_note"] is False
      and overrides["Massachusetts"]["Springfield"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "springfield_ma_chauffeur_license"]
      and overrides["Massachusetts"]["Springfield"]["local_note"] is True
      and overrides["Massachusetts"]["Worcester"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "worcester_taxi_livery_license"]
      and overrides["Massachusetts"]["Worcester"]["local_note"] is False
      and overrides["New Jersey"]["Jersey City"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "jersey_city_limo_driver_license"]
      and overrides["New Jersey"]["Jersey City"]["local_note"] is False
      and overrides["Pennsylvania"]["Philadelphia"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "philadelphia_limo_certificate"]
      and overrides["Pennsylvania"]["Philadelphia"]["local_note"] is True,
      str(overrides))
check("South Central/Mountain batch overrides: 15 cities; Norman, Denver fall back",
      set(overrides["Arkansas"]) == {"Little Rock", "Springdale"}
      and set(overrides["Idaho"]) == {"Boise", "Idaho Falls"}
      and set(overrides["Oklahoma"]) == {"Oklahoma City", "Tulsa"}
      and set(overrides["Texas"]) == {"Dallas", "Austin", "Houston",
                                      "San Antonio"}
      and set(overrides["Utah"]) == {"St. George"}
      and set(overrides["Wyoming"]) == {"Cheyenne", "Gillette"}
      and set(overrides["Nevada"]) == {"Henderson", "Las Vegas",
                                       "North Las Vegas"}
      and "Norman" not in overrides["Oklahoma"]
      and "Colorado" not in overrides
      and overrides["Arkansas"]["Little Rock"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "little_rock_gt_driver_permit"]
      and overrides["Arkansas"]["Little Rock"]["local_note"] is False
      and overrides["Arkansas"]["Springdale"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "springdale_taxi_driver_permit"]
      and overrides["Arkansas"]["Springdale"]["local_note"] is False
      and overrides["Idaho"]["Boise"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "boise_cts_driver_license"]
      and overrides["Idaho"]["Boise"]["local_note"] is False
      and overrides["Idaho"]["Idaho Falls"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "idaho_falls_operator_license"]
      and overrides["Idaho"]["Idaho Falls"]["local_note"] is True
      and overrides["Oklahoma"]["Oklahoma City"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "okc_vfh_driver_permit"]
      and overrides["Oklahoma"]["Oklahoma City"]["local_note"] is True
      and overrides["Oklahoma"]["Tulsa"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "tulsa_chauffeur_license", "tulsa_mvr"]
      and overrides["Oklahoma"]["Tulsa"]["local_note"] is True
      and overrides["Texas"]["Austin"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "austin_chauffeur_permit"]
      and overrides["Texas"]["Austin"]["local_note"] is True
      and overrides["Texas"]["Houston"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "houston_vfh_driver_license"]
      and overrides["Texas"]["Houston"]["local_note"] is False
      and overrides["Texas"]["San Antonio"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "san_antonio_driver_permit"]
      and overrides["Texas"]["San Antonio"]["local_note"] is True
      and overrides["Utah"]["St. George"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "st_george_for_hire_permit"]
      and overrides["Utah"]["St. George"]["local_note"] is True
      and overrides["Wyoming"]["Cheyenne"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "cheyenne_pt_driver_permit"]
      and overrides["Wyoming"]["Cheyenne"]["local_note"] is False
      and overrides["Wyoming"]["Gillette"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "gillette_pt_driver_permit"]
      and overrides["Wyoming"]["Gillette"]["local_note"] is True
      and overrides["Nevada"]["Henderson"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "clark_county_business_license"]
      and overrides["Nevada"]["Henderson"]["local_note"] is True
      and overrides["Nevada"]["Las Vegas"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "clark_county_business_license"]
      and overrides["Nevada"]["Las Vegas"]["local_note"] is True
      and overrides["Nevada"]["North Las Vegas"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "clark_county_business_license"]
      and overrides["Nevada"]["North Las Vegas"]["local_note"] is True,
      str(overrides))
check("West/Pacific batch override: Portland, OR; Anchorage, Fairbanks, Juneau fall back",
      set(overrides["Oregon"]) == {"Portland"}
      and "Alaska" not in overrides
      and overrides["Oregon"]["Portland"]["docs"] == [
          "profile_picture", "dmv_license", "vehicle_registration",
          "portland_or_certification", "portland_or_business_license"]
      and overrides["Oregon"]["Portland"]["local_note"] is True,
      str(overrides))
r = anon.get(BASE + "/driver", timeout=TIMEOUT)
check("served driver page has the city picker after the state picker",
      r.status_code == 200 and 'id="reg-city"' in r.text
      and 'id="city-list"' in r.text
      and r.text.index('id="reg-state"') < r.text.index('id="reg-city"')
      < r.text.index('id="reg-car-model"'), str(r.status_code))
r = anon.get(BASE + "/static/js/driver.js", timeout=TIMEOUT)
check("served driver.js shows no document count in the required note",
      r.status_code == 200 and "required.length" not in r.text
      and "All items are required" in r.text, str(r.status_code))
r = anon.get(BASE + "/static/js/owner.js", timeout=TIMEOUT)
check("served owner.js carries the new state document labels",
      r.status_code == 200
      and "Taxi-LPMV-PMV Operator's License" in r.text
      and "For-Hire Operators (Face ID) License" in r.text
      and "Form E (Insurance Filing)" in r.text, str(r.status_code))

print(f"\n{CHECKS['passed']} passed, {CHECKS['failed']} failed")
if FAILURES:
    print("Failures:", "; ".join(FAILURES))
sys.exit(1 if CHECKS["failed"] else 0)
