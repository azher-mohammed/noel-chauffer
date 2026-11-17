# Noel Chauffer — real booking system

Luxury car-with-chauffeur service in the USA. One app with three parts,
all connected:

- **Customer site** (`/`) — book a ride, choose a class on the
  "Choose your experience" page (Business Class / Business SUV, one
  single total each), pay by card (test mode), then the chauffeur is
  assigned; live map once the chauffeur is on the way, invoice, ride
  history.
- **Driver app** (`/driver`) — register once with photo-only documents
  and bank details, receive job offers whether available or offline
  (earnings only, filtered to the driver's vehicle class, and never
  overlapping a ride already accepted), run trips stage by stage,
  see earnings grouped in weekly pay periods. Each job card and the
  trip screen show an embedded map (Leaflet + OpenStreetMap, free)
  with 'Pick up' / 'Drop off' markers and the route line when
  geometry is available; endpoints + route shape only, never miles
  or money.
- **Owner dashboard** (`/owner`, PIN-protected) — per-ride revenue
  breakdown (fare, gratuity, tax, driver share, profit), tax collected,
  alerts, messages outbox, driver documents, toll entry, and driver
  payout weeks (mark paid).

Stack: Python + Flask + SQLAlchemy, vanilla HTML/CSS/JS, no build step.
Driver documents and photos are stored as BLOBs inside the database —
no files are written for uploads, so they survive restarts.

## Pricing (settled by the owner, 2026-11-16)

All pricing lives in `pricing.py`. Do not change the rates without
the owner's say-so. The customer sees ONE single total per class —
never a breakdown, never rates, never miles.

- **Two vehicle classes only:** sedan ("Business Class") and SUV
  ("Business SUV"). No S-Class / First Class. The customer picks a
  class on the separate "Choose your experience" page after the
  booking form (sedan pre-selected); each class shows its own single
  total. The form button says "View options".
- **One-way:** fare = miles × class rate (sedan $9/mile, SUV
  $10/mile); gratuity = 10% of the fare (owner profit, never driver
  pay); NYC tax = 8.875% of the fare (pass-through — not profit, not
  driver pay); toll added untaxed, passed to the driver. Customer
  total = fare + gratuity + tax + toll. Driver earnings = miles ×
  driver rate (sedan $4/mile, SUV $7/mile) + toll. Owner profit =
  total − driver − tax. **No booking fee ($0).** This supersedes the
  old $20 fee + $7/mile formula entirely.
- **NYC tax verification:** NYC311/TLC confirm 8.875% on car-service /
  limousine / black-car passenger fares, and Blacklane's own quote
  applied exactly 8.875% to the base fare. Tolls are not taxed.
- **Referral codes** are accepted but give a $0 discount for now (the
  old $20-fee waiver no longer applies since there is no fee). A new
  referral benefit is TBD pending the owner's decision.
- **Hourly rides are unchanged:** $90/hour customer, $50/hour driver,
  no fee, no gratuity, no tax. Whether hourly rides get tax is TBD.
- **Driver vehicle class** is derived from the registered car model
  via the explicit 133-model mapping in `car_models.py` (85 SUVs, 48
  sedans; judgment calls documented in `static/NOTES.md`). Dispatch
  is class-filtered: sedan bookings only to sedan drivers, SUV
  bookings only to SUV drivers; hourly rides reach every driver.
- **Verified examples:** 20-mile SUV = $237.75 total, driver $140,
  profit $80. 20-mile sedan = $213.98 total, driver $80, profit $118.

## Test-mode limits (read this first)

- **Payments are simulated.** No Stripe API call is ever made. The card
  form stores only the last 4 digits and a `pi_test_` id. No real
  charging happens. Connecting a real Stripe account is a later step.
- **No SMS or email is ever sent.** Customer messages are written to the
  owner-dashboard outbox only, so the owner can see exactly what would
  have been sent. Connecting a messaging service is a later step.
- **Tolls:** New York -> New Jersey trips get the $16.79 Port Authority
  return-crossing estimate automatically at booking creation (up
  front, like Uber), so the driver sees the separate Toll line before
  accepting. The owner can still adjust the toll per ride in the
  dashboard (not on completed rides). There is no toll API.
- **Fares use live geocoding/routing** (Nominatim + OSRM, no keys). If
  those services are unreachable, the app falls back to straight-line
  distance × 1.3, or 10.0 miles if an address cannot be geocoded at all.
- **Prices are settled business rules** in `pricing.py`. Do not change
  them without the owner's say-so.
- **Driver payouts are tracking only.** Every 14 days the driver gets
  seven days' money: trips tally in 7-day weeks anchored at
  2026-11-16 (see `payouts.py`), and each week's payout comes due
  14 days after the week starts (week 0, Nov 16–22, due Nov 30;
  week 1, Nov 23–29, due Dec 7; week 2, Nov 30–Dec 6, due Dec 14),
  so every trip is paid 8–14 days after it happens. The owner marks
  a week paid in the dashboard. No money moves in this app.

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000/ (customer), `/driver` (driver app),
`/owner` (owner dashboard, default PIN `1234`).

Environment variables (see `.env.example`): `DATABASE_URL` (default:
local `noel.db` SQLite file), `OWNER_PIN`, `SECRET_KEY`,
`ENCRYPTION_KEY`, `PORT`. For any run where a driver registers, set
`ENCRYPTION_KEY` to a persistent Fernet key first — otherwise stored
bank numbers cannot be decrypted after a restart. Generate one with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Checks

```bash
python -m unittest discover -s tests -v   # unit tests (309)
python smoke_test.py                       # backend flow checks (143)
```

`verify_e2e.py` runs the full HTTP checklist against a **running**
server with a **fresh** database:

```bash
DATABASE_URL="sqlite:////tmp/noel-verify.db" OWNER_PIN=4321 \
  SECRET_KEY=test-secret ENCRYPTION_KEY="<fernet key>" PORT=5055 python app.py &
NOEL_BASE_URL=http://127.0.0.1:5055 NOEL_OWNER_PIN=4321 python verify_e2e.py
# full HTTP checklist (235 checks)
```

### Temporary test reset — REMOVE BEFORE REAL LAUNCH

Owner decision 2026-11-17 ("filhal ke vaaste", testing only): the
owner dashboard has a **Clear all rides** button (POST
`/api/owner/clear-rides`, owner PIN session + confirm dialog) that
deletes all bookings, chat messages, alerts, payments, decline
exclusions and outbox messages so a test can restart fresh. Drivers,
their documents and profile photos are untouched, and referral codes
stay valid. This is a **manual test reset only** — nothing calls it
automatically, and **driver ride history is retained for a minimum
of one year**: no automatic deletion, expiry or retention cleanup of
ride records exists anywhere in this codebase, and none may be added.

To remove it before launch, delete: the `owner_clear_rides` endpoint
in `app.py` (marked TEMPORARY TEST-ONLY), the button in
`static/owner.html`, its handler in `static/js/owner.js`, the
`.danger-btn` style in `static/css/owner.css`,
`tests/test_clear_rides.py`, and the clear-rides sections in
`smoke_test.py` and `verify_e2e.py`.

### Free driver features (added 2026-11-16)

Four free Blacklane-style features, no paid services:

- **Digital name sign** — on airport pickups the driver trip screen
  shows a "Name sign" button; tapping it opens a full-screen overlay
  with the customer's name in very large type.
- **In-app chat** — driver and customer exchange plain-text messages
  (polling, no SMS, no number masking) once a driver has accepted.
  Messages never carry fare, miles, gratuity, tax or totals.
- **Extra distance at completion** — one-way rides only: the driver
  enters extra miles at completion; the customer total gains the
  extra fare + 10% gratuity + 8.875% tax, the driver gains the extra
  miles at his rate, and the owner dashboard shows an
  extra-distance line per ride. Hourly rides reject extra miles.
- **Dispatcher-lite** — on a paid, not-yet-accepted booking the owner
  can assign it to one specific registered driver (class must match);
  it then appears only in that driver's offers. Clearing the
  assignment, or the assigned driver declining, restores broadcast
  first-accept-wins.

## Deploy on Render (free tier, one-month trial)

You need: a **GitHub account** and a **Render account**. Creating
accounts is not part of this repo — the owner must do that part (or
provide access). Nothing here is deployed until the steps below are
done by a person.

### Step 1 — Push this repo to GitHub

```bash
cd noel-chauffer-live
git remote add origin https://github.com/<your-username>/noel-chauffer.git
git push -u origin main
```

(Use the repository URL GitHub shows you after creating the repo. The
repo is already committed locally; no remote is configured.)

### Step 2 — Create the Blueprint in Render

1. Log in at [render.com](https://render.com) and go to **Dashboard**.
2. Click **New +** → **Blueprint**.
3. Connect your GitHub account if asked, and pick the `noel-chauffer`
   repository.
4. Render reads `render.yaml` and shows two resources to create:
   a **Web Service** (free) and a **PostgreSQL** database (free).
   Click **Apply**.

### Step 3 — Set the environment variables

Render asks for the values marked `sync: false` in `render.yaml`.
Fill in all three before the first deploy finishes (or right after,
under the service's **Environment** tab, then redeploy):

| Variable | Value |
|---|---|
| `OWNER_PIN` | Your private owner-dashboard PIN (digits, e.g. a 4-digit PIN you choose). |
| `SECRET_KEY` | Any long random string, e.g. the output of `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `ENCRYPTION_KEY` | A Fernet key, generated once (command above). **Set this BEFORE any driver registers.** Changing it later makes stored bank numbers undecryptable. |

`DATABASE_URL` is wired automatically from the Blueprint database — do
not set it by hand. Do not set `PORT` on Render; Render sets it.

### Step 4 — Confirm it is live

1. Wait for the deploy to finish (first build takes a few minutes).
2. Open the service URL Render gives you (like
   `https://noel-chauffer.onrender.com/`). The customer site should
   load. Check `/driver` and `/owner` too.
3. Log in to `/owner` with your PIN and confirm the dashboard loads
   with empty bookings.

### How the free tier behaves

- **The web service sleeps after ~15 minutes idle.** The first request
  after sleep is slow (up to about a minute) while it wakes up. Later
  requests are normal speed.
- **The free Postgres database EXPIRES after 30 days and its data is
  deleted.** That is acceptable for this one-month trial, but bookings,
  drivers and documents will be gone when it expires. Before expiry,
  upgrade the database to a paid plan in Render (or accept a fresh
  start). There is no automatic backup on the free plan.
- **Uploads live in the database**, so driver documents and photos
  survive web-service restarts and redeploys — but not the 30-day
  database expiry.
- **Postgres was not verified locally.** The app was verified end to
  end on SQLite; the `postgres://` → `postgresql://` rewrite for
  Render's connection string is in the code but was not run against a
  real Postgres here. If the first Render deploy fails on the database
  connection, that rewrite is the first place to look.

## Connect noelchauffer.com afterwards (steps only — do not do this yet)

The domain `noelchauffer.com` is already owned (Namecheap). After the
Render service is live:

1. In Render, open the web service → **Settings** → **Custom Domain**
   → **Add Custom Domain**, and enter `noelchauffer.com` (and
   `www.noelchauffer.com` if you want both). Render shows the DNS
   record(s) it needs (a CNAME or A record).
2. In Namecheap, go to **Domain List** → **Manage** next to
   `noelchauffer.com` → **Advanced DNS**, and add exactly the record(s)
   Render showed. Save.
3. Wait for DNS to spread (usually minutes, sometimes up to a day).
   Render then provisions a free SSL certificate automatically.
4. Open `https://noelchauffer.com/` and confirm the customer site loads
   with a padlock. Check `/driver` and `/owner` on the domain too.

Do not change DNS until the Render service itself is confirmed working
on its Render URL.

## Project layout

```
app.py              Flask app: models + API endpoints + page routes
pricing.py          Settled pricing rules (Decimal, pure functions)
payouts.py          Weekly driver payout schedule (pure date math)
geo.py              Nominatim geocoding + OSRM routing, with fallbacks
car_models.py       Eligible car models (Uber Black list + Model 3 exception) + model -> vehicle-class mapping
flights.py          Flight-number parsing + IATA airline table (no live tracking)
UBER_BLACK_LIST.md  Source data for the car-model list (transcribed Oct 2026)
requirements.txt    Python dependencies (incl. gunicorn, psycopg2-binary, psycopg[binary] — SQLAlchemy 2.x needs the psycopg v3 driver for postgresql:// URLs)
smoke_test.py       Backend flow checks (in-process, throwaway DB)
verify_e2e.py       Full HTTP checklist against a running server
tests/              Pricing + payout-week unit/API tests
static/             Customer site, driver app, owner dashboard (HTML/CSS/JS)
static/NOTES.md     Frontend section-to-API mapping
render.yaml         Render Blueprint (free web + free Postgres)
.env.example        Environment variables template
```
