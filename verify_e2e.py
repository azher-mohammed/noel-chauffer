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
$160.60 / $72.00 / $140.60 / $180.95 / $90.50 / $175.60 are asserted too.
"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from payouts import completion_date, week_for  # noqa: E402
from pricing import compute_hourly, compute_one_way, waiting_charge  # noqa: E402

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
                        "fare_total", "customer_total", "subtotal", "profit"}

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
photo = b"\xff\xd8\xff fake jpeg photo driver1"
fh1_pdf = b"%PDF-1.4 fake fh1 insurance card"
png = b"\x89PNG fake document image"
files_before = set()
repo_dir = os.path.dirname(os.path.abspath(__file__))
for root, _dirs, names in os.walk(repo_dir):
    if "__pycache__" in root:
        continue
    for n in names:
        files_before.add(os.path.join(root, n))

resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Verify Driver One", "phone": "+15550001111", "email": "d1@test.com",
    "car_model": "Cadillac Escalade", "car_year": "2023", "car_colour": "Black", "plate": "T11111",
    "bank_account_number": "123456789", "bank_routing_number": "021000021",
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
    "car_model": "Lincoln Navigator", "car_year": "2024", "car_colour": "Black", "plate": "T22222",
    "bank_account_number": "987654321", "bank_routing_number": "021000021",
}, files={"profile_photo": ("photo.jpg", photo, "image/jpeg")}, timeout=TIMEOUT)
check("driver2 register 201", resp.status_code == 201, resp.text[:200])
token2 = resp.json()["token"]

resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Dup", "phone": "+15550001111", "car_model": "Cadillac Escalade",
    "car_year": "2023", "car_colour": "Y",
    "plate": "Z", "bank_account_number": "1", "bank_routing_number": "2",
}, timeout=TIMEOUT)
check("duplicate phone -> 409", resp.status_code == 409, str(resp.status_code))
resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Bad", "phone": "+15550003333", "car_model": "Cadillac Escalade",
    "car_year": "2023", "car_colour": "Y",
    "plate": "Z", "bank_account_number": "1", "bank_routing_number": "2",
}, files={"doc_dmv_license": ("license.pdf", fh1_pdf, "application/pdf")}, timeout=TIMEOUT)
check("PDF rejected for non-FH1 doc -> 400", resp.status_code == 400, str(resp.status_code))

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
    "plate": "Z", "bank_account_number": "1", "bank_routing_number": "2",
}, timeout=TIMEOUT)
check("year 2021 rejected (2022 floor)", resp.status_code == 400, str(resp.status_code))
resp = anon.post(BASE + "/api/drivers/register", data={
    "name": "Wrong Car", "phone": "+15550005555", "car_model": "Tesla Model Y",
    "car_year": "2024", "car_colour": "Black",
    "plate": "Z", "bank_account_number": "1", "bank_routing_number": "2",
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
expected1 = compute_one_way(miles1)
print(f"  INFO live geo miles for JFK->Times Square: {miles1}")
check("one-way total matches pricing formula for returned miles",
      approx(detail["customer_total"], expected1["total"]),
      f"got {detail['customer_total']} expected {expected1['total']} at {miles1} mi")
check("one-way driver matches pricing formula",
      approx(detail["driver_earnings"], expected1["driver_earnings"]),
      f"got {detail['driver_earnings']} expected {expected1['driver_earnings']}")
if miles1 == Decimal("18.0"):
    check("18.0 mi total is exactly $160.60", approx(detail["customer_total"], "160.60"))
    check("18.0 mi driver is exactly $72.00", approx(detail["driver_earnings"], "72.00"))

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
expected_ref = compute_one_way(Decimal(str(detail_ref["miles"])), referral=True)
check("referral total = formula minus exactly $20",
      approx(detail_ref["customer_total"], expected_ref["total"]),
      f"got {detail_ref['customer_total']} expected {expected_ref['total']}")
if Decimal(str(detail_ref["miles"])) == Decimal("18.0"):
    check("18.0 mi referral total is exactly $140.60",
          approx(detail_ref["customer_total"], "140.60"))

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
check("hourly has NO fee and NO gratuity",
      approx(detail_h["booking_fee"], "0.00") and approx(detail_h["gratuity"], "0.00"),
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
    check("18.0 mi + toll total is exactly $180.95", approx(detail_t["customer_total"], "180.95"))
    check("18.0 mi + toll driver is exactly $90.50", approx(detail_t["driver_earnings"], "90.50"))

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
    check("invoice total is exactly $175.60", approx(inv.get("total"), "175.60"))
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
check("owner drivers list has 2 drivers", len(drivers) == 2, str(drivers))
d1row = [d for d in drivers if d["phone"] == "+15550001111"][0]
check("owner drivers: docs + doc_ids + masked bank + car",
      d1row["docs"]["fh1_insurance"] == "completed" and "fh1_insurance" in d1row["doc_ids"]
      and d1row["bank_masked"] == "••••6789" and d1row["car"] == "Cadillac Escalade (Black)",
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
                     - Decimal(str(row["driver_earnings"])), row["profit"]), str(row))
check("per-ride profits sum to summary profit", approx(profit_sum, summary["profit"]),
      f"sum {profit_sum} vs summary {summary['profit']}")
check("per-ride gross sums to summary gross", approx(gross_sum, summary["gross"]),
      f"sum {gross_sum} vs summary {summary['gross']}")
check("per-ride driver sums to summary driver_owed", approx(owed_sum, summary["driver_owed"]),
      f"sum {owed_sum} vs summary {summary['driver_owed']}")
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

# ------------------------------------------------- static + greps -----------

section("static pages + banned-string + no-sending greps")
for path, needle in (("/", "Arrive"), ("/driver", "Driver registration"),
                     ("/owner", "Owner dashboard")):
    r = anon.get(BASE + path, timeout=TIMEOUT)
    check(f"page {path} 200 with real HTML", r.status_code == 200 and needle in r.text,
          f"{r.status_code} {r.text[:80]}")
for path in ("/static/js/customer.js", "/static/js/driver.js", "/static/js/owner.js",
             "/static/css/customer.css", "/static/css/driver.css", "/static/css/owner.css"):
    r = anon.get(BASE + path, timeout=TIMEOUT)
    check(f"static {path} 200", r.status_code == 200 and len(r.content) > 100, str(r.status_code))

banned = [r"\$7", r"\$20", r"\$4", r"\$90", r"\$50", "per mile", "booking fee",
          "gratuity", "dispatch"]
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
check("uploads stored as DB BLOBs (LargeBinary, no file writes)",
      "LargeBinary" in app_src and "open(" not in app_src.replace("openViewer", ""))

print(f"\n{CHECKS['passed']} passed, {CHECKS['failed']} failed")
if FAILURES:
    print("Failures:", "; ".join(FAILURES))
sys.exit(1 if CHECKS["failed"] else 0)
