"""Smoke test for the no-code customer sign-in (owner 2026-11-22).
Run from the worktree root. Uses a temp sqlite DB; touches nothing live.

Checks:
1. GET /, /app, /driver -> 200, with the new sign-in markers.
2. POST /api/bookings/<id>/contact without sign-in -> 401.
3. POST /api/customers/signin with email + phone -> 200 signed_in.
4. After sign-in, contact + pay proceed (test mode, no real charge).
5. No sign-in email is queued and no code endpoint exists.
"""
import os
import sys
import tempfile

_tmpdir = tempfile.mkdtemp(prefix="noel-smoke-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmpdir, "test.db")
os.environ["BOOKINGS_PAUSED"] = "false"
os.environ["OWNER_PIN"] = "9999"
os.environ["SECRET_KEY"] = "smoke-secret-key"
from cryptography.fernet import Fernet  # noqa: E402
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import geo as geo_module  # noqa: E402
geo_module.distance_miles = lambda p, d: (18.0, (40.6413, -73.7781), (40.7580, -73.9855))  # noqa: E731
import app as app_module  # noqa: E402

app_module.BOOKINGS_PAUSED = False
with app_module.app.app_context():
    app_module.db.drop_all()
    app_module.db.create_all()
client = app_module.app.test_client()

ok = True


def check(name, cond, extra=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + (" " + extra if extra else ""))
    if not cond:
        ok = False


for path in ("/", "/app", "/driver"):
    r = client.get(path)
    check("GET %s -> 200" % path, r.status_code == 200, str(r.status_code))

html = client.get("/").get_data(as_text=True)
check("homepage has Continue sign-in button", 'id="class-signin-continue"' in html)
check("homepage has NO code field", "class-code-field" not in html)
check("homepage has NO code input", "class-signin-code" not in html)
check("homepage has NO code text", "6-digit" not in html)
app_html = client.get("/app").get_data(as_text=True)
check("app has Continue sign-in button", 'id="ca-signin-continue"' in app_html)
check("app has NO code field", "ca-code-field" not in app_html)
js = client.get("/static/js/customer.js").get_data(as_text=True)
check("website JS calls /api/customers/signin", '"/api/customers/signin"' in js)
check("website JS has NO code endpoints", "signin/request" not in js and "signin/verify" not in js)

# Booking without contact, then contact without sign-in -> 401
r = client.post("/api/bookings", json={
    "pickup": "JFK Airport", "dropoff": "Times Square, New York",
    "date": "2030-06-01", "time": "12:00", "ride_type": "one_way"})
assert r.status_code == 201, r.get_data(as_text=True)[:200]
bid = r.get_json()["booking"]["id"]
r = client.post("/api/bookings/%d/contact" % bid, json={
    "customer_name": "Smoke", "phone": "+1 929-385-7597",
    "email": "smoke@example.com"})
check("contact without sign-in -> 401", r.status_code == 401, str(r.status_code))

# Old code endpoints are gone
r = client.post("/api/customers/signin/request",
                json={"email": "smoke@example.com", "phone": "+1 929-385-7597"})
check("POST /signin/request -> 404 (gone)", r.status_code == 404, str(r.status_code))
r = client.post("/api/customers/signin/verify",
                json={"email": "smoke@example.com", "code": "123456"})
check("POST /signin/verify -> 404 (gone)", r.status_code == 404, str(r.status_code))

# Email + Continue sign-in
r = client.post("/api/customers/signin",
                json={"email": "smoke@example.com", "phone": "+1 929-385-7597"})
check("email + Continue sign-in -> 200", r.status_code == 200, str(r.status_code))
check("signed_in true", r.get_json().get("signed_in") is True)
with app_module.app.app_context():
    check("no sign-in email queued", app_module.OutboxMessage.query.count() == 0)

# Contact + pay now proceed
r = client.post("/api/bookings/%d/contact" % bid, json={
    "customer_name": "Smoke", "phone": "+1 929-385-7597",
    "email": "smoke@example.com"})
check("contact after sign-in -> 200", r.status_code == 200, str(r.status_code))
r = client.post("/api/bookings/%d/pay" % bid, json={
    "card_number": "4242424242424242", "card_exp": "12/30",
    "card_cvc": "123", "card_name": "Smoke"})
check("pay after sign-in -> 200 (test mode)", r.status_code == 200, str(r.status_code))
if r.status_code == 200:
    check("booking offered after pay", r.get_json()["booking"]["status"] == "offered")

print("SMOKE " + ("OK" if ok else "FAILED"))
sys.exit(0 if ok else 1)
