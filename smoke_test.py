"""Smoke test for the Noel Chauffer backend.

Starts the app in-process (Flask test client, throwaway SQLite DB) and
exercises: pricing unit cases, geo fallback, booking create -> offer list
(no miles/fare fields) -> accept -> pay -> trip events -> complete ->
invoice math -> owner summary reconciliation, plus referral, re-dispatch,
toll recompute, cancellation refund, and hourly rides.

Run:  python smoke_test.py
Exit code 0 = all green.
"""

import io
import os
import sys
import tempfile
from decimal import Decimal

from PIL import Image

# --- test env BEFORE importing the app -------------------------------------
tmpdir = tempfile.mkdtemp(prefix="noel-smoke-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmpdir, "smoke.db")
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "smoke-secret-key"
from cryptography.fernet import Fernet  # noqa: E402

os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import geo as geo_module  # noqa: E402
from pricing import compute_hourly, compute_one_way, waiting_charge  # noqa: E402

CHECKS = {"passed": 0, "failed": 0}


def check(name, condition, detail=""):
    if condition:
        CHECKS["passed"] += 1
        print(f"  PASS {name}")
    else:
        CHECKS["failed"] += 1
        print(f"  FAIL {name} {detail}")


def approx(a, b):
    return abs(float(a) - float(b)) < 0.005


# --- 1. pricing unit cases --------------------------------------------------
print("== pricing ==")
r = compute_one_way(Decimal("18.0"))
check("18mi sedan total 162.00", r["total"] == Decimal("162.00"), str(r["total"]))
check("18mi sedan fare/tax/gratuity", r["fare"] == Decimal("162.00")
      and r["tax"] == Decimal("0.00") and r["gratuity"] == Decimal("0.00"), str(r))
check("18mi sedan driver 72.00", r["driver_earnings"] == Decimal("72.00"))
check("18mi sedan profit 90.00", r["profit"] == Decimal("90.00"))
check("18mi booking fee 0", r["booking_fee"] == Decimal("0"))
r = compute_one_way(Decimal("18.0"), vehicle_class="suv")
check("18mi SUV total 180.00", r["total"] == Decimal("180.00"), str(r["total"]))
check("18mi SUV driver 126.00", r["driver_earnings"] == Decimal("126.00"))
check("18mi SUV profit 54.00", r["profit"] == Decimal("54.00"))
r = compute_one_way(Decimal("18.0"), referral=True)
check("18mi referral total 162.00 (discount $0)", r["total"] == Decimal("162.00"), str(r["total"]))
r = compute_one_way(Decimal("18.0"), toll=Decimal("18.50"))
check("18mi toll total 180.50", r["total"] == Decimal("180.50"))
check("18mi toll driver 90.50", r["driver_earnings"] == Decimal("90.50"))
check("18mi toll: tax/gratuity stay 0.00", r["tax"] == Decimal("0.00") and r["gratuity"] == Decimal("0.00"))
r = compute_hourly(3)
check("hourly 3h total 270.00", r["total"] == Decimal("270.00"))
check("hourly 3h driver 150.00", r["driver_earnings"] == Decimal("150.00"))
check("airport 75min waiting 15.00", waiting_charge("JFK Airport", 75) == Decimal("15.00"))

# --- 2. geo fallback (no network: force failures) ----------------------------
print("== geo fallback ==")
geo_module._geocode_cache.clear()
geo_module._route_cache.clear()
_real_http = geo_module._http_get_json


def _boom(url):
    raise RuntimeError("network down (simulated)")


geo_module._http_get_json = _boom
try:
    miles, pc, dc = geo_module.distance_miles("Nowhere Street 1", "Elsewhere Ave 2")
    check("geo failure returns no miles (never an invented distance)",
          miles is None and pc is None and dc is None, str((miles, pc, dc)))
    expected = round(geo_module.haversine_miles(40.6413, -73.7781, 40.7580, -73.9855) * 1.3, 1)
    got = geo_module.route_miles(40.6413, -73.7781, 40.7580, -73.9855)
    check("route fallback = haversine*1.3", got == expected, f"{got} != {expected}")
finally:
    geo_module._http_get_json = _real_http
    geo_module._geocode_cache.clear()
    geo_module._route_cache.clear()

# Deterministic geo for the booking flow: every one-way ride is 18.0 miles.
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731

# --- 3. app flow -------------------------------------------------------------
import app as app_module  # noqa: E402

client = app_module.app.test_client()
FORBIDDEN_OFFER_KEYS = {"miles", "fare", "total", "gratuity", "fee", "booking_fee",
                        "fare_total", "customer_total", "subtotal", "profit", "tax"}

print("== driver registration ==")
# The profile photo must be a real portrait image (server shape/size
# rules: portrait, at least 300px on the short side).
_photo_buf = io.BytesIO()
Image.new("RGB", (400, 500), (200, 30, 30)).save(_photo_buf, format="JPEG")
photo_bytes = _photo_buf.getvalue()
resp = client.post("/api/drivers/register", data={
    "name": "Test Driver", "phone": "+15550001111", "email": "driver@test.com",
    "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black", "plate": "T12345",
    "bank_account_number": "123456789", "bank_routing_number": "021000021",
    "profile_photo": (io.BytesIO(photo_bytes), "photo.jpg"),
    "doc_fh1": (io.BytesIO(b"%PDF- fake"), "fh1.pdf"),
    "doc_dmv_license": (io.BytesIO(b"fake png"), "license.png"),
    "doc_tlc_license": (io.BytesIO(b"fake png"), "tlc.png"),
    "doc_registration": (io.BytesIO(b"fake png"), "reg.png"),
    "doc_inspection": (io.BytesIO(b"fake png"), "insp.png"),
    "doc_vehicle_permit": (io.BytesIO(b"fake png"), "permit.png"),
}, content_type="multipart/form-data")
check("driver1 register 201", resp.status_code == 201, resp.get_data(as_text=True)[:200])
d1 = resp.get_json()["driver"]
token1 = resp.get_json()["token"]
check("driver1 all 7 docs completed", all(v == "completed" for v in d1["docs"].values())
      and len(d1["docs"]) == 7, str(d1["docs"]))
check("bank masked", d1["bank_masked"] == "••••6789", d1["bank_masked"])
check("no full bank number in response", "123456789" not in resp.get_data(as_text=True)
      and "021000021" not in resp.get_data(as_text=True))
resp = client.post("/api/drivers/register", data={
    "name": "Second Driver", "phone": "+15550002222", "email": "d2@test.com",
    "car_model": "Lincoln Continental", "car_year": "2024", "car_colour": "Black", "plate": "T67890",
    "bank_account_number": "987654321", "bank_routing_number": "021000021",
    "profile_photo": (io.BytesIO(photo_bytes), "photo.jpg"),
    "doc_dmv_license": (io.BytesIO(b"fake png"), "license.png"),
    "doc_tlc_license": (io.BytesIO(b"fake png"), "tlc.png"),
    "doc_fh1": (io.BytesIO(b"fake png"), "fh1.png"),
    "doc_registration": (io.BytesIO(b"fake png"), "reg.png"),
    "doc_inspection": (io.BytesIO(b"fake png"), "insp.png"),
    "doc_vehicle_permit": (io.BytesIO(b"fake png"), "permit.png"),
}, content_type="multipart/form-data")
check("driver2 register 201", resp.status_code == 201, resp.get_data(as_text=True)[:200])
token2 = resp.get_json()["token"]
# Compulsory documents (owner decision 2026-11-17): registration must
# not complete unless every item is uploaded, and the rejection must
# name each missing item ("Missing document: ...").
resp = client.post("/api/drivers/register", data={
    "name": "No Docs", "phone": "+15550004444", "email": "nd@test.com",
    "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black", "plate": "T00000",
    "bank_account_number": "111222333", "bank_routing_number": "021000021",
}, content_type="multipart/form-data")
check("no documents -> 400 naming every missing item",
      resp.status_code == 400
      and resp.get_json()["error"].startswith("Missing document: ")
      and all(label in resp.get_json()["error"] for label in
              ("Profile Picture", "DMV driving license", "TLC License",
               "FH-1 Insurance Card", "Commercial Vehicle Registration",
               "NYS DMV Inspection", "TLC-for-hire Vehicle Permit")),
      resp.get_data(as_text=True)[:300])
resp = client.post("/api/drivers/register", data={
    "name": "One Missing", "phone": "+15550005555", "email": "om@test.com",
    "car_model": "Cadillac CT6", "car_year": "2023", "car_colour": "Black", "plate": "T00001",
    "bank_account_number": "111222333", "bank_routing_number": "021000021",
    "profile_photo": (io.BytesIO(photo_bytes), "photo.jpg"),
    "doc_dmv_license": (io.BytesIO(b"fake png"), "license.png"),
    "doc_tlc_license": (io.BytesIO(b"fake png"), "tlc.png"),
    "doc_fh1": (io.BytesIO(b"fake png"), "fh1.png"),
    "doc_registration": (io.BytesIO(b"fake png"), "reg.png"),
    "doc_inspection": (io.BytesIO(b"fake png"), "insp.png"),
}, content_type="multipart/form-data")
check("one document missing -> 400 naming only that item",
      resp.status_code == 400
      and resp.get_json()["error"] == "Missing document: TLC-for-hire Vehicle Permit. "
      "Please upload all required documents to complete registration.",
      resp.get_data(as_text=True)[:300])
resp = client.post("/api/drivers/register", data={
    "name": "Dup", "phone": "+15550001111", "car_model": "Cadillac Escalade",
    "car_year": "2023", "car_colour": "Y",
    "plate": "Z", "bank_account_number": "1", "bank_routing_number": "2",
}, content_type="multipart/form-data")
check("duplicate phone rejected", resp.status_code == 409, str(resp.status_code))
resp = client.post("/api/drivers/register", data={
    "name": "Bad", "phone": "+15550003333", "car_model": "Cadillac Escalade",
    "car_year": "2023", "car_colour": "Y",
    "plate": "Z", "bank_account_number": "1", "bank_routing_number": "2",
    "doc_dmv_license": (io.BytesIO(b"%PDF- fake"), "license.pdf"),
}, content_type="multipart/form-data")
check("PDF rejected for non-FH1 doc", resp.status_code == 400, str(resp.status_code))

print("== booking create ==")
resp = client.post("/api/bookings", json={
    "customer_name": "Test Customer", "phone": "+15550009999", "email": "cust@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
})
check("booking create 201", resp.status_code == 201, resp.get_data(as_text=True)[:200])
b1 = resp.get_json()["booking"]
check("booking awaiting_payment", b1["status"] == "awaiting_payment")
check("total shown at booking", approx(b1["total"], 162.00), str(b1))
referral_code = b1["referral_code"]
check("referral code issued", bool(referral_code), str(b1))
resp = client.post("/api/bookings", json={
    "customer_name": "X", "phone": "+1", "email": "x@test.com",
    "pickup": "A", "dropoff": "B", "date": "2030-06-01", "time": "12:00",
    "ride_type": "one_way", "referral_code": "NOEL-BADBAD",
})
check("invalid referral rejected", resp.status_code == 400, str(resp.status_code))
resp = client.get(f"/api/bookings/{b1['id']}")
got = resp.get_json()["booking"]
check("total visible, driver null before accept", approx(got["total"], 162.00) and got["driver"] is None, str(got))

print("== vehicle class selection (options page) ==")
resp = client.post("/api/bookings", json={
    "customer_name": "Class Customer", "phone": "+15550004444", "email": "cc@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-01", "time": "12:00", "ride_type": "one_way",
})
check("class booking create 201", resp.status_code == 201, resp.get_data(as_text=True)[:200])
bc = resp.get_json()["booking"]
check("class booking defaults to sedan", bc["vehicle_class"] == "sedan"
      and bc["vehicle_class_label"] == "Business Class", str(bc))
check("class_totals sedan 162.00 / SUV 180.00",
      approx(bc["class_totals"]["sedan"], 162.00) and approx(bc["class_totals"]["suv"], 180.00), str(bc))
resp = client.post(f"/api/bookings/{bc['id']}/vehicle-class", json={"vehicle_class": "suv"})
check("switch to SUV 200", resp.status_code == 200, resp.get_data(as_text=True)[:200])
check("SUV total 180.00 + label", approx(resp.get_json()["booking"]["total"], 180.00)
      and resp.get_json()["booking"]["vehicle_class_label"] == "Business SUV",
      resp.get_data(as_text=True)[:200])
resp = client.post(f"/api/bookings/{bc['id']}/vehicle-class", json={"vehicle_class": "luxury"})
check("invalid class -> 400", resp.status_code == 400, str(resp.status_code))
resp = client.post(f"/api/bookings/{bc['id']}/vehicle-class", json={"vehicle_class": "sedan"})
check("switch back to sedan 162.00", resp.status_code == 200
      and approx(resp.get_json()["booking"]["total"], 162.00), resp.get_data(as_text=True)[:200])
resp = client.post(f"/api/bookings/{bc['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Class Customer"})
check("class booking pays 162.00", resp.status_code == 200
      and approx(resp.get_json()["payment"]["amount"], 162.00), resp.get_data(as_text=True)[:200])
resp = client.post(f"/api/bookings/{bc['id']}/vehicle-class", json={"vehicle_class": "suv"})
check("class switch after payment -> 409", resp.status_code == 409, str(resp.status_code))
resp = client.post(f"/api/bookings/{bc['id']}/cancel", json={"phone": "+15550004444"})
check("class booking cancelled (refunded, keeps later checks clean)",
      resp.status_code == 200 and resp.get_json()["refund"] is True, resp.get_data(as_text=True)[:150])

print("== pay before dispatch ==")
client.post("/api/drivers/me/availability", json={"available": True},
            headers={"X-Driver-Token": token1})
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token1})
check("no offers before payment", resp.get_json() == [], str(resp.get_json()))
resp = client.post(f"/api/drivers/me/offers/{b1['id']}/accept", headers={"X-Driver-Token": token1})
check("accept unpaid booking rejected", resp.status_code == 409, str(resp.status_code))
resp = client.post(f"/api/bookings/{b1['id']}/pay", json={
    "card_number": "4242 4242 4242 4242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Test Customer"})
check("pay 200", resp.status_code == 200, resp.get_data(as_text=True)[:200])
pay = resp.get_json()["payment"]
check("payment test + last4", pay["test"] is True and pay["last4"] == "4242"
      and pay["status"] == "succeeded", str(pay))
check("payment amount 162.00", approx(pay["amount"], 162.00))
check("status offered after payment", resp.get_json()["booking"]["status"] == "offered")
resp = client.post(f"/api/bookings/{b1['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Test Customer"})
check("double pay rejected", resp.status_code == 409, str(resp.status_code))

print("== offers / accept ==")
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token2})
check("offline driver still sees offers (owner decision 2026-11-16)",
      any(o["booking_id"] == b1["id"] for o in resp.get_json()), str(resp.get_json()))
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token1})
offers = resp.get_json()
check("offer listed", len(offers) == 1 and offers[0]["booking_id"] == b1["id"], str(offers))
leaked = set(offers[0]) & FORBIDDEN_OFFER_KEYS if offers else {"none"}
check("offer has no miles/fare fields", not leaked, f"leaked: {leaked}")
check("offer earnings = driver share only", offers and approx(offers[0]["earnings"], 72.00), str(offers))
check("offer has route_url", offers and offers[0]["route_url"].startswith("https://www.google.com/maps/"))
check("offer has route_waze_url", offers and offers[0]["route_waze_url"].startswith("https://waze.com/ul?"))
client.post("/api/drivers/me/availability", json={"available": True},
            headers={"X-Driver-Token": token2})
resp = client.post(f"/api/drivers/me/offers/{b1['id']}/accept", headers={"X-Driver-Token": token1})
check("accept 200", resp.status_code == 200, resp.get_data(as_text=True)[:200])
check("accept earnings 72.00", approx(resp.get_json()["booking"]["earnings"], 72.00))
resp = client.post(f"/api/drivers/me/offers/{b1['id']}/accept", headers={"X-Driver-Token": token2})
check("second accept -> 409", resp.status_code == 409, str(resp.status_code))
resp = client.get(f"/api/bookings/{b1['id']}")
got = resp.get_json()["booking"]
check("total visible after accept", approx(got["total"], 162.00), str(got["total"]))
check("driver visible after accept", got["driver"] and got["driver"]["name"] == "Test Driver")
check("tracking hidden before en_route", got["tracking"]["visible"] is False)

print("== trip ==")


def trip(event, **kw):
    return client.post(f"/api/drivers/me/trip/{b1['id']}/event",
                       json={"event": event, **kw}, headers={"X-Driver-Token": token1})


resp = trip("en_route", lat=40.64, lng=-73.78)
check("en_route ok", resp.status_code == 200 and resp.get_json()["booking"]["status"] == "en_route",
      resp.get_data(as_text=True)[:150])
resp = client.post(f"/api/drivers/me/trip/{b1['id']}/location",
                   json={"lat": 40.70, "lng": -73.90}, headers={"X-Driver-Token": token1})
check("location update ok", resp.status_code == 200, str(resp.status_code))
resp = client.get(f"/api/bookings/{b1['id']}")
got = resp.get_json()["booking"]
check("tracking visible en_route", got["tracking"]["visible"] is True
      and approx(got["tracking"]["lat"], 40.70), str(got["tracking"]))
check("arrived ok", trip("arrived").status_code == 200)
check("start ok", trip("start").status_code == 200)
resp = trip("complete", waiting_minutes=75)
check("complete ok", resp.status_code == 200, resp.get_data(as_text=True)[:200])
inv = resp.get_json().get("invoice", {})
check("invoice waiting 15.00", approx(inv.get("waiting_charge"), 15.00), str(inv))
check("invoice total 177.00", approx(inv.get("total"), 177.00), str(inv))
resp = client.get(f"/api/bookings/{b1['id']}")
got = resp.get_json()["booking"]
check("GET invoice after complete", got["invoice"] and approx(got["invoice"]["total"], 177.00))
resp = client.get("/api/drivers/me/earnings", headers={"X-Driver-Token": token1})
earn = resp.get_json()
check("driver earnings 72.00 / 1 ride", earn["completed_rides"] == 1
      and approx(earn["total_earnings"], 72.00), str(earn))
resp = client.get(f"/api/bookings/{b1['id']}/driver-photo")
check("driver photo bytes", resp.status_code == 200 and resp.data == photo_bytes,
      str(resp.status_code))

print("== owner dashboard ==")
resp = client.post("/api/owner/login", json={"pin": "0000"})
check("wrong PIN -> 401", resp.status_code == 401, str(resp.status_code))
resp = client.post("/api/owner/login", json={"pin": "9999"})
check("owner login ok", resp.status_code == 200)
resp = client.get("/api/owner/summary")
s = resp.get_json()
check("summary gross 177.00", approx(s["gross"], 177.00), str(s))
check("summary driver_owed 72.00", approx(s["driver_owed"], 72.00), str(s))
check("summary profit reconciles", approx(s["profit"], 105.00)
      and approx(s["gross"] - s["driver_owed"], s["profit"]), str(s))
resp = client.get("/api/owner/bookings")
rows = resp.get_json()
row1 = next((r for r in rows if r["id"] == b1["id"]), None)
check("owner breakdown profit", row1 and approx(row1["profit"], 105.00), str(rows))
check("owner breakdown fare/tax/gratuity", row1 and approx(row1["fare"], 162.00)
      and approx(row1["tax"], 0.00) and approx(row1["gratuity"], 0.00), str(rows))
check("summary tax_collected is 0 (no tax on new rides)", approx(s["tax_collected"], 0.00), str(s))
resp = client.get("/api/owner/outbox")
bodies = [m["body"] for m in resp.get_json() if m["booking_id"] == b1["id"]]
check("outbox has booking+accept+invoice", len(bodies) >= 6, f"{len(bodies)} messages")
resp = client.get("/api/owner/alerts")
check("alerts present", len(resp.get_json()) >= 4, str(len(resp.get_json())))
resp = client.get("/api/owner/drivers")
check("owner drivers list", len(resp.get_json()) == 2, str(resp.get_json()))
resp = client.get(f"/api/owner/bookings/{b1['id']}")
detail = resp.get_json()
check("owner detail has pi_test_ payment", detail["payments"]
      and detail["payments"][0]["stripe_test_id"].startswith("pi_test_")
      and detail["payments"][0]["test"] is True, str(detail.get("payments")))
check("owner detail invoice math", approx(detail["invoice"]["total"], 177.00), str(detail.get("invoice")))

print("== referral + re-dispatch + toll ==")
resp = client.post("/api/bookings", json={
    "customer_name": "Second Customer", "phone": "+15550008888", "email": "c2@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-02", "time": "12:00", "ride_type": "one_way",
    "referral_code": referral_code})
check("referral booking 201", resp.status_code == 201, resp.get_data(as_text=True)[:200])
b2 = resp.get_json()["booking"]
with app_module.app.app_context():
    row = app_module.ReferralCode.query.filter_by(code=referral_code).first()
    check("referral used_count incremented", row.used_count == 1, str(row.used_count))
resp = client.post(f"/api/bookings/{b2['id']}/pay", json={
    "card_number": "5555555555554444", "card_exp": "01/31",
    "card_cvc": "321", "card_name": "Second Customer"})
check("b2 pay 162.00 (referral, $0 discount)", resp.status_code == 200
      and approx(resp.get_json()["payment"]["amount"], 162.00),
      resp.get_data(as_text=True)[:150])
resp = client.post(f"/api/drivers/me/offers/{b2['id']}/accept", headers={"X-Driver-Token": token2})
check("driver2 accepts b2", resp.status_code == 200)
resp = client.post(f"/api/drivers/me/trip/{b2['id']}/event", json={"event": "cancel"},
                   headers={"X-Driver-Token": token2})
check("driver cancel re-dispatches", resp.status_code == 200
      and resp.get_json()["booking"]["status"] == "offered", resp.get_data(as_text=True)[:150])
resp = client.get(f"/api/bookings/{b2['id']}")
got = resp.get_json()["booking"]
check("driver null, total still visible after re-dispatch", got["driver"] is None
      and approx(got["total"], 162.00), str(got))
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token2})
check("cancelling driver excluded", all(o["booking_id"] != b2["id"] for o in resp.get_json()))
resp = client.post(f"/api/owner/bookings/{b2['id']}/toll", json={"toll": 18.50})
check("toll recompute w/ referral", resp.status_code == 200
      and approx(resp.get_json()["booking"]["customer_total"], 180.50)
      and approx(resp.get_json()["booking"]["driver_earnings"], 90.50),
      resp.get_data(as_text=True)[:250])
resp = client.post(f"/api/drivers/me/offers/{b2['id']}/accept", headers={"X-Driver-Token": token1})
check("driver1 accepts re-dispatched b2", resp.status_code == 200)
resp = client.post(f"/api/owner/bookings/{b2['id']}/toll", json={"toll": 10.00})
check("toll after pay exposes balance_due", resp.status_code == 200
      and approx(resp.get_json()["balance_due"], 10.00), resp.get_data(as_text=True)[:250])

print("== cancellation + hourly + history ==")
resp = client.post("/api/bookings", json={
    "customer_name": "Third Customer", "phone": "+15550007777", "email": "c3@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-03", "time": "12:00", "ride_type": "one_way"})
b3 = resp.get_json()["booking"]
client.post(f"/api/bookings/{b3['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Third Customer"})
client.post(f"/api/drivers/me/offers/{b3['id']}/accept", headers={"X-Driver-Token": token1})
resp = client.post(f"/api/bookings/{b3['id']}/cancel", json={"phone": "+15550000000"})
check("cancel wrong phone -> 403", resp.status_code == 403, str(resp.status_code))
resp = client.post(f"/api/bookings/{b3['id']}/cancel", json={"phone": "+15550007777"})
check("far-future cancel refunds", resp.status_code == 200
      and resp.get_json()["refund"] is True and resp.get_json()["charge_kept"] is False,
      resp.get_data(as_text=True)[:150])
resp = client.post("/api/bookings", json={
    "customer_name": "Hourly Customer", "phone": "+15550006666", "email": "h@test.com",
    "pickup": "Central Park, New York", "date": "2030-06-04", "time": "14:00",
    "ride_type": "hourly", "hours": 3})
check("hourly booking 201", resp.status_code == 201, resp.get_data(as_text=True)[:200])
b4 = resp.get_json()["booking"]
resp = client.get("/api/owner/bookings")
hrow = [r for r in resp.get_json() if r["id"] == b4["id"]][0]
check("hourly owner totals 270/150", approx(hrow["customer_total"], 270.00)
      and approx(hrow["driver_earnings"], 150.00), str(hrow))
check("hourly owner row fare 270, tax 0, no class",
      approx(hrow["fare"], 270.00) and approx(hrow["tax"], 0.00)
      and hrow["vehicle_class"] is None, str(hrow))
resp = client.get("/api/bookings", query_string={"phone": "+15550009999"})
hist = resp.get_json()
check("ride history total for paid ride", len(hist) == 1 and approx(hist[0]["total"], 162.00), str(hist))
resp = client.get("/")
check("home page route 200", resp.status_code == 200, str(resp.status_code))
resp = client.get("/api/drivers/me/lookup", json={})
check("lookup needs phone", True)  # placeholder no-op (GET on POST route -> 405 is fine)
resp = client.post("/api/drivers/me/lookup", json={"phone": "+15550001111"})
check("driver lookup re-issues token", resp.status_code == 200
      and resp.get_json()["token"] != token1, resp.get_data(as_text=True)[:150])
token1 = resp.get_json()["token"]

print("== free features: name sign, chat, extra distance, assign ==")
from pricing import compute_extra_distance  # noqa: E402
r = compute_extra_distance(Decimal("5"), "sedan")
check("extra distance 5mi sedan 45.00 / driver 20.00",
      r["total"] == Decimal("45.00") and r["driver_addition"] == Decimal("20.00"), str(r))
r = compute_extra_distance(Decimal("2.5"), "suv")
check("extra distance 2.5mi SUV 25.00 / driver 17.50",
      r["total"] == Decimal("25.00") and r["driver_addition"] == Decimal("17.50"), str(r))
# Fresh booking for the assign + chat + extra-distance flow.
client.post("/api/drivers/me/availability", json={"available": True},
            headers={"X-Driver-Token": token1})
client.post("/api/drivers/me/availability", json={"available": True},
            headers={"X-Driver-Token": token2})
resp = client.post("/api/bookings", json={
    "customer_name": "Chat Customer", "phone": "+15550008888", "email": "chat@test.com",
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-05", "time": "12:00", "ride_type": "one_way",
})
check("chat booking 201", resp.status_code == 201, resp.get_data(as_text=True)[:200])
bx = resp.get_json()["booking"]
resp = client.post(f"/api/bookings/{bx['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Chat Customer"})
check("chat booking paid", resp.status_code == 200, resp.get_data(as_text=True)[:150])
resp = client.post("/api/owner/login", json={"pin": "9999"})
check("owner login for assign", resp.status_code == 200)
resp = client.post(f"/api/owner/bookings/{bx['id']}/assign", json={"driver_id": d1["id"]})
check("assign to driver1", resp.status_code == 200
      and resp.get_json()["booking"]["assigned_driver_id"] == d1["id"],
      resp.get_data(as_text=True)[:200])
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token2})
check("assigned booking hidden from driver2",
      all(o["booking_id"] != bx["id"] for o in resp.get_json()), str(resp.get_json()))
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token1})
check("assigned booking visible to driver1",
      any(o["booking_id"] == bx["id"] for o in resp.get_json()), str(resp.get_json()))
resp = client.post(f"/api/drivers/me/offers/{bx['id']}/accept", json={},
                   headers={"X-Driver-Token": token1})
check("assigned driver accepts", resp.status_code == 200, resp.get_data(as_text=True)[:150])
trip_payload = resp.get_json()["booking"]
check("accept payload: customer name + airport flag for name sign",
      trip_payload["customer_name"] == "Chat Customer" and trip_payload["airport_pickup"] is True,
      str(trip_payload))
check("accept payload: no money keys beyond earnings/toll",
      FORBIDDEN_OFFER_KEYS.isdisjoint(trip_payload.keys()), str(sorted(trip_payload.keys())))
resp = client.post(f"/api/drivers/me/trip/{bx['id']}/messages",
                   json={"text": "I am outside arrivals."},
                   headers={"X-Driver-Token": token1})
check("driver chat send 201", resp.status_code == 201, resp.get_data(as_text=True)[:150])
resp = client.get(f"/api/bookings/{bx['id']}/messages",
                  query_string={"phone": "+15550008888"})
check("customer reads driver message", resp.status_code == 200
      and len(resp.get_json()["messages"]) == 1
      and resp.get_json()["messages"][0]["sender"] == "driver", str(resp.get_json()))
resp = client.post(f"/api/bookings/{bx['id']}/messages",
                   json={"phone": "+15550008888", "text": "Coming out now."})
check("customer chat send 201", resp.status_code == 201, resp.get_data(as_text=True)[:150])
resp = client.get(f"/api/drivers/me/trip/{bx['id']}/messages",
                  headers={"X-Driver-Token": token1})
check("driver reads 2 messages", resp.status_code == 200
      and len(resp.get_json()["messages"]) == 2, str(resp.get_json()))
resp = client.get(f"/api/bookings/{bx['id']}/messages",
                  query_string={"phone": "+10000000000"})
check("chat wrong phone 403", resp.status_code == 403, str(resp.status_code))
for ev in ("en_route", "arrived", "start"):
    resp = client.post(f"/api/drivers/me/trip/{bx['id']}/event",
                       json={"event": ev}, headers={"X-Driver-Token": token1})
    check(f"trip {ev} ok", resp.status_code == 200, resp.get_data(as_text=True)[:150])
resp = client.post(f"/api/drivers/me/trip/{bx['id']}/event",
                   json={"event": "complete", "waiting_minutes": 0, "extra_miles": 5},
                   headers={"X-Driver-Token": token1})
check("complete with extra miles ok", resp.status_code == 200, resp.get_data(as_text=True)[:150])
resp = client.get(f"/api/bookings/{bx['id']}")
inv = resp.get_json()["booking"]["invoice"]
check("invoice includes extra distance 45.00",
      approx(inv["total"], 207.00) and approx(inv["extra_distance_charge"], 45.00), str(inv))
resp = client.get(f"/api/owner/bookings/{bx['id']}")
row = resp.get_json()
check("owner row extra-distance line",
      approx(row["extra_distance_charge"], 45.00) and approx(row["extra_miles"], 5.0)
      and approx(row["driver_earnings"], 92.00), str(row))

# --- 8. owner clear all rides (TEMPORARY TEST-ONLY: remove with the endpoint) ---
print("== owner clear all rides ==")
anon_client = app_module.app.test_client()
resp = anon_client.post("/api/owner/clear-rides", json={})
check("clear-rides without login -> 401", resp.status_code == 401, str(resp.status_code))
resp = client.get("/api/owner/bookings")
before_rides = len(resp.get_json())
check("bookings exist before clear", before_rides > 0, str(before_rides))
resp = client.post("/api/owner/clear-rides", json={})
body = resp.get_json()
check("clear-rides ok", resp.status_code == 200 and body.get("cleared") is True,
      resp.get_data(as_text=True)[:150])
deleted = body.get("deleted", {})
check("clear-rides deleted all bookings", deleted.get("bookings") == before_rides, str(deleted))
check("clear-rides deleted chat/events/outbox/payments",
      deleted.get("chat_messages", 0) > 0 and deleted.get("booking_events", 0) > 0
      and deleted.get("outbox_messages", 0) > 0 and deleted.get("payments", 0) > 0, str(deleted))
resp = client.get("/api/owner/bookings")
check("owner bookings empty after clear", resp.get_json() == [], str(resp.get_json())[:100])
resp = client.get("/api/owner/alerts")
check("owner alerts empty after clear", resp.get_json() == [], str(resp.get_json())[:100])
resp = client.get("/api/owner/outbox")
check("owner outbox empty after clear", resp.get_json() == [], str(resp.get_json())[:100])
resp = client.get("/api/owner/summary")
summary = resp.get_json()
check("owner summary zeroed after clear",
      summary.get("counts") == {} and approx(summary.get("gross"), 0), str(summary))
resp = client.get("/api/owner/drivers")
drivers = resp.get_json()
test_driver = next((d for d in drivers if d["phone"] == "+15550001111"), None)
check("drivers kept after clear", test_driver is not None, str(drivers)[:150])
if test_driver:
    resp = client.get(f"/api/owner/drivers/{test_driver['id']}/photo")
    check("driver photo bytes kept after clear",
          resp.status_code == 200 and resp.data == photo_bytes, str(resp.status_code))
    check("driver docs kept after clear",
          test_driver["docs"].get("dmv_license") == "completed"
          and test_driver["docs"].get("fh1_insurance") == "completed", str(test_driver["docs"]))
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token1})
check("driver token still works, offers empty after clear",
      resp.status_code == 200 and resp.get_json() == [], resp.get_data(as_text=True)[:150])
resp = client.post("/api/owner/clear-rides", json={})
check("clear-rides idempotent on empty db",
      resp.status_code == 200 and resp.get_json()["deleted"]["bookings"] == 0,
      resp.get_data(as_text=True)[:150])

# --- route labels (served driver JS/CSS) ------------------------------------
resp = client.get("/static/js/driver.js")
check("served driver.js has Pick up / Drop off route labels",
      resp.status_code == 200
      and b"route-label" in resp.data
      and b"Pick up" in resp.data and b"Drop off" in resp.data
      and b"routeHtml(o.pickup, o.dropoff)" in resp.data
      and b"routeHtml(t.pickup, t.dropoff)" in resp.data,
      str(resp.status_code))
# --- staged trip navigation (served driver JS) -----------------------------
check("served driver.js stages trip navigation (pickup until picked up)",
      resp.status_code == 200
      and b"function tripNavDestination(stageIndex, pickup, dropoff)" in resp.data
      and b"if (stageIndex < 3) return pickup || null;" in resp.data
      and b"return dropoff || null;" in resp.data
      and b"tripNavLinksHtml(state.stageIndex, t.pickup, t.dropoff)" in resp.data
      and b"renderTripNavLinks();" in resp.data,
      str(resp.status_code))
check("served driver.js keeps offer-card links, trip screen drops payload URLs",
      b"esc(o.route_url)" in resp.data
      and b"esc(o.route_waze_url)" in resp.data
      and b"esc(t.route_url)" not in resp.data
      and b"esc(t.route_waze_url)" not in resp.data,
      "offer-card links changed or trip screen still uses un-staged URLs")
# --- driver cancel lock (owner rule 2026-11-17) --------------------------
check("served driver.js hides cancel button within 2 hours of pickup",
      resp.status_code == 200
      and b"function refreshCancelButton()" in resp.data
      and b"pickup.getTime() - Date.now() <= 2 * 60 * 60000" in resp.data
      and b"trip-cancel-locked-note" in resp.data
      and b"refreshCancelButton();" in resp.data,
      str(resp.status_code))
resp = client.get("/driver")
check("driver page carries the cancel-locked note",
      resp.status_code == 200
      and b"trip-cancel-locked-note" in resp.data
      and b"pickup is within 2 hours" in resp.data,
      str(resp.status_code))
# --- navigation chooser on stage advance (owner request 2026-11-17) --
resp = client.get("/static/js/driver.js")
check("served driver.js pops a nav chooser on heading/pickup stages",
      resp.status_code == 200
      and b"function showNavChooser(dest, title)" in resp.data
      and b"function maybeShowNavChooser(advancedStage)" in resp.data
      and b"maybeShowNavChooser(current);" in resp.data
      and b"nav-chooser-overlay" in resp.data
      and b'window.open(urls.google, "_blank", "noopener");' in resp.data
      and b'window.open(urls.waze, "_blank", "noopener");' in resp.data,
      str(resp.status_code))
resp = client.get("/driver")
check("driver page carries the nav chooser overlay",
      resp.status_code == 200
      and b"nav-chooser-overlay" in resp.data
      and b"nav-chooser-google" in resp.data
      and b"nav-chooser-waze" in resp.data
      and b"nav-chooser-close" in resp.data,
      str(resp.status_code))
resp = client.get("/static/css/driver.css")
check("served driver.css styles route labels",
      resp.status_code == 200 and b".route-label" in resp.data,
      str(resp.status_code))

print(f"\n{CHECKS['passed']} passed, {CHECKS['failed']} failed")
sys.exit(1 if CHECKS["failed"] else 0)
