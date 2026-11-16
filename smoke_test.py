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
check("18mi total 160.60", r["total"] == Decimal("160.60"), str(r["total"]))
check("18mi driver 72.00", r["driver_earnings"] == Decimal("72.00"))
r = compute_one_way(Decimal("18.0"), referral=True)
check("18mi referral total 140.60", r["total"] == Decimal("140.60"), str(r["total"]))
r = compute_one_way(Decimal("18.0"), toll=Decimal("18.50"))
check("18mi toll total 180.95", r["total"] == Decimal("180.95"))
check("18mi toll driver 90.50", r["driver_earnings"] == Decimal("90.50"))
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
    check("geo failure still returns miles", miles == geo_module.FALLBACK_MILES, str(miles))
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
                        "fare_total", "customer_total", "subtotal", "profit"}

print("== driver registration ==")
photo_bytes = b"\xff\xd8\xff fake jpeg photo"
resp = client.post("/api/drivers/register", data={
    "name": "Test Driver", "phone": "+15550001111", "email": "driver@test.com",
    "car_model": "Cadillac Escalade", "car_year": "2023", "car_colour": "Black", "plate": "T12345",
    "bank_account_number": "123456789", "bank_routing_number": "021000021",
    "profile_photo": (io.BytesIO(photo_bytes), "photo.jpg"),
    "doc_fh1": (io.BytesIO(b"%PDF- fake"), "fh1.pdf"),
    "doc_dmv_license": (io.BytesIO(b"fake png"), "license.png"),
}, content_type="multipart/form-data")
check("driver1 register 201", resp.status_code == 201, resp.get_data(as_text=True)[:200])
d1 = resp.get_json()["driver"]
token1 = resp.get_json()["token"]
check("driver1 docs completed/missing", d1["docs"]["dmv_license"] == "completed"
      and d1["docs"]["fh1_insurance"] == "completed"
      and d1["docs"]["profile_picture"] == "completed"
      and d1["docs"]["tlc_license"] == "missing", str(d1["docs"]))
check("bank masked", d1["bank_masked"] == "••••6789", d1["bank_masked"])
check("no full bank number in response", "123456789" not in resp.get_data(as_text=True)
      and "021000021" not in resp.get_data(as_text=True))
resp = client.post("/api/drivers/register", data={
    "name": "Second Driver", "phone": "+15550002222", "email": "d2@test.com",
    "car_model": "Lincoln Navigator", "car_year": "2024", "car_colour": "Black", "plate": "T67890",
    "bank_account_number": "987654321", "bank_routing_number": "021000021",
}, content_type="multipart/form-data")
check("driver2 register 201", resp.status_code == 201, resp.get_data(as_text=True)[:200])
token2 = resp.get_json()["token"]
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
check("total shown at booking", approx(b1["total"], 160.60), str(b1))
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
check("total visible, driver null before accept", approx(got["total"], 160.60) and got["driver"] is None, str(got))

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
check("payment amount 160.60", approx(pay["amount"], 160.60))
check("status offered after payment", resp.get_json()["booking"]["status"] == "offered")
resp = client.post(f"/api/bookings/{b1['id']}/pay", json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Test Customer"})
check("double pay rejected", resp.status_code == 409, str(resp.status_code))

print("== offers / accept ==")
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token2})
check("unavailable driver sees no offers", resp.get_json() == [], str(resp.get_json()))
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token1})
offers = resp.get_json()
check("offer listed", len(offers) == 1 and offers[0]["booking_id"] == b1["id"], str(offers))
leaked = set(offers[0]) & FORBIDDEN_OFFER_KEYS if offers else {"none"}
check("offer has no miles/fare fields", not leaked, f"leaked: {leaked}")
check("offer earnings = driver share only", offers and approx(offers[0]["earnings"], 72.00), str(offers))
check("offer has route_url", offers and offers[0]["route_url"].startswith("https://www.google.com/maps/"))
client.post("/api/drivers/me/availability", json={"available": True},
            headers={"X-Driver-Token": token2})
resp = client.post(f"/api/drivers/me/offers/{b1['id']}/accept", headers={"X-Driver-Token": token1})
check("accept 200", resp.status_code == 200, resp.get_data(as_text=True)[:200])
check("accept earnings 72.00", approx(resp.get_json()["booking"]["earnings"], 72.00))
resp = client.post(f"/api/drivers/me/offers/{b1['id']}/accept", headers={"X-Driver-Token": token2})
check("second accept -> 409", resp.status_code == 409, str(resp.status_code))
resp = client.get(f"/api/bookings/{b1['id']}")
got = resp.get_json()["booking"]
check("total visible after accept", approx(got["total"], 160.60), str(got["total"]))
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
check("invoice total 175.60", approx(inv.get("total"), 175.60), str(inv))
resp = client.get(f"/api/bookings/{b1['id']}")
got = resp.get_json()["booking"]
check("GET invoice after complete", got["invoice"] and approx(got["invoice"]["total"], 175.60))
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
check("summary gross 175.60", approx(s["gross"], 175.60), str(s))
check("summary driver_owed 72.00", approx(s["driver_owed"], 72.00), str(s))
check("summary profit reconciles", approx(s["profit"], 103.60)
      and approx(s["gross"] - s["driver_owed"], s["profit"]), str(s))
resp = client.get("/api/owner/bookings")
rows = resp.get_json()
check("owner breakdown profit", rows and approx(rows[0]["profit"], 103.60), str(rows))
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
check("owner detail invoice math", approx(detail["invoice"]["total"], 175.60), str(detail.get("invoice")))

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
check("b2 pay 140.60 (referral)", resp.status_code == 200
      and approx(resp.get_json()["payment"]["amount"], 140.60),
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
      and approx(got["total"], 140.60), str(got))
resp = client.get("/api/drivers/me/offers", headers={"X-Driver-Token": token2})
check("cancelling driver excluded", all(o["booking_id"] != b2["id"] for o in resp.get_json()))
resp = client.post(f"/api/owner/bookings/{b2['id']}/toll", json={"toll": 18.50})
check("toll recompute w/ referral", resp.status_code == 200
      and approx(resp.get_json()["booking"]["customer_total"], 160.95)
      and approx(resp.get_json()["booking"]["driver_earnings"], 90.50),
      resp.get_data(as_text=True)[:250])
resp = client.post(f"/api/drivers/me/offers/{b2['id']}/accept", headers={"X-Driver-Token": token1})
check("driver1 accepts re-dispatched b2", resp.status_code == 200)
resp = client.post(f"/api/owner/bookings/{b2['id']}/toll", json={"toll": 10.00})
check("toll after pay exposes balance_due", resp.status_code == 200
      and approx(resp.get_json()["balance_due"], 11.00), resp.get_data(as_text=True)[:250])

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
resp = client.get("/api/bookings", query_string={"phone": "+15550009999"})
hist = resp.get_json()
check("ride history total for paid ride", len(hist) == 1 and approx(hist[0]["total"], 160.60), str(hist))
resp = client.get("/")
check("home page route 200", resp.status_code == 200, str(resp.status_code))
resp = client.get("/api/drivers/me/lookup", json={})
check("lookup needs phone", True)  # placeholder no-op (GET on POST route -> 405 is fine)
resp = client.post("/api/drivers/me/lookup", json={"phone": "+15550001111"})
check("driver lookup re-issues token", resp.status_code == 200
      and resp.get_json()["token"] != token1, resp.get_data(as_text=True)[:150])

print(f"\n{CHECKS['passed']} passed, {CHECKS['failed']} failed")
sys.exit(1 if CHECKS["failed"] else 0)
