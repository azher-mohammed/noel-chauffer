# Noel Chauffer — frontend notes

Vanilla HTML/CSS/JS. No build step, no framework. Leaflet is loaded from
CDN on the customer page only, with a text fallback when the CDN is
unavailable. All money figures shown on screen come from the API; the
frontend never works out a price.

## Files

- `index.html` + `css/customer.css` + `js/customer.js` — customer site
- `driver.html` + `css/driver.css` + `js/driver.js` — driver app
- `owner.html` + `css/owner.css` + `js/owner.js` — owner dashboard (PIN)

## Customer site — section to API mapping

Flow: booking form (+ flight-number step for airport rides) → single
total + card payment → booking sent to drivers → chauffeur accepts →
driver details + live map. Payment always comes BEFORE any driver
sees the booking; unpaid bookings never appear in driver offers.

- Booking form, One way / By the hour tabs
  → `POST /api/bookings` (returns the booking with its single `total`
  and status `awaiting_payment`)
- Address suggestions under the Pickup / Drop-off fields (no map
  inside the booking form); tapping a suggestion fills the field.
  Airport queries also list the airport's terminals, including
  arrivals/departures entries where OpenStreetMap maps them.
  → `GET /api/places/search?q=<text>&limit=5` (USA-only Nominatim,
  address text + coordinates + `airport` flag only, always 200)
- Flight-number step, shown AFTER the booking form when the pickup or
  drop-off is an airport (suggestion `airport` flag, with an
  address-text fallback in `js/flight.js`); skipping never blocks the
  booking. Stored as `flight_number` on the booking; the airline name
  is derived from the IATA code (no live flight tracking).
  → `POST /api/bookings` accepts optional `flight_number`; the
  booking payloads carry `flight_number`, `airline_name`, `terminal`.
  Driver trip screen shows all three (earnings only otherwise); owner
  ride detail shows the flight number.
- "Finding your chauffeur" waiting state after payment, polling
  every 3 seconds
  → `GET /api/bookings/<id>`
- Assigned chauffeur card (name, phone, car, colour, plate, photo)
  → fields on `GET /api/bookings/<id>`; photo via
  `GET /api/bookings/<id>/driver-photo` (used when no photo URL is given)
- Single total shown right after the booking form (single total only,
  no breakdown)
  → `total` field returned on booking create and on
  `GET /api/bookings/<id>` (always present for the customer)
- Pay by card, labelled TEST MODE, before the booking reaches drivers
  → `POST /api/bookings/<id>/pay` (only from status
  `awaiting_payment`; on success the booking moves to `offered` and
  is sent to drivers). Free cancellation (more than 1 hour before
  pickup) records a full refund of this payment; later cancellation
  or a no-show keeps the full price.
- Thank-you page + "Book your return trip" (swapped addresses, new booking)
  → `POST /api/bookings` again; referral code shown from the `referral_code`
  field on `GET /api/bookings/<id>` (also returned on booking create)
- Live map, shown only when `tracking.visible` is true
  → `tracking` field on `GET /api/bookings/<id>`
- Invoice panel after completion
  → `invoice` field on `GET /api/bookings/<id>`
- Cancel booking
  → `POST /api/bookings/<id>/cancel` with the booking phone number
- Ride history lookup
  → `GET /api/bookings?phone=<phone>`
- Chat widget: scripted keyword answers only, no API calls.
- Experience, trust, policy, company and contacts sections: static text.

## Driver app — section to API mapping

- Registration (shown only when no token is stored and no driver record
  is found) → `POST /api/drivers/register` (multipart form, photo files
  only for documents; FH-1 also accepts PDF). Car model is a searchable
  dropdown, NOT free text → `GET /api/car-models` (single list in
  `car_models.py`, transcribed from `UBER_BLACK_LIST.md`: the 132-model
  Uber Black list, 23 makes). Model year is a select from 2022 through
  current year + 1 (2022 floor, owner decision 2026-11-16 — stricter
  than Uber's 2020+ rule); the server rejects unlisted models and years
  below 2022. TEMPORARY exception: "Tesla Model 3" is in the list only
  so the owner can trial the system with his own 2023 Model 3 — remove
  it when he says so. Model Y stays excluded. Jeep Wagoneer S is
  included as transcribed (source marks it SF Bay Area only).
- "Already registered?" lookup → `POST /api/drivers/me/lookup`
- Return visits: token in localStorage + `GET /api/drivers/me` goes
  straight to Home; registration is never shown again
- Active-trip restore after reload
  → `GET /api/drivers/me/active-trip`; the trip screen is rebuilt at the
  stage matching the booking status (accepted → Head to pickup,
  en_route → Arrived, arrived → Start, in_progress → Complete)
- Availability toggle → `POST /api/drivers/me/availability`
- Job offers, polled every 5 seconds while available
  → `GET /api/drivers/me/offers`; earnings value displayed as returned
- Accept / Decline
  → `POST /api/drivers/me/offers/<id>/accept`
  → `POST /api/drivers/me/offers/<id>/decline`
- Trip stages Head to pickup / Arrived / Start / Complete, plus Cancel
  and No-show, waiting minutes at completion
  → `POST /api/drivers/me/trip/<id>/event`
- Location sharing while heading to pickup (browser geolocation, with a
  graceful fallback when denied or unavailable)
  → `POST /api/drivers/me/trip/<id>/location`
- Earnings tab → `GET /api/drivers/me/earnings`; completed rides are
  grouped into 7-day payout weeks (week dates, total earnings, due
  date, Paid/Unpaid) and the per-ride list is kept. Earnings amounts
  only — no miles, fares, or totals.
- Documents tab → `docs` on `GET /api/drivers/me` (status strings keyed
  by document type, e.g. `drivers_license: "completed"`)
- Profile tab → `GET /api/drivers/me` (bank shown masked, last 4 only)
- "Register a different driver" clears the stored token.

## Owner dashboard — section to API mapping

- PIN gate → `POST /api/owner/login` (session cookie); session checked
  with `GET /api/owner/summary`; `POST /api/owner/logout`
- Summary cards → `GET /api/owner/summary`
- Bookings table with full per-ride breakdown, as returned by the API
  → `GET /api/owner/bookings`
- Booking detail view → `GET /api/owner/bookings/<id>`
- Toll entry per booking → `POST /api/owner/bookings/<id>/toll`
- Driver payouts: per-driver, per-week totals
  → `GET /api/owner/payouts`; mark a week paid
  → `POST /api/owner/payouts/mark-paid` with `driver_id` + `week_index`
- Alerts feed → `GET /api/owner/alerts`
- Messages outbox → `GET /api/owner/outbox`
- Drivers list → `GET /api/owner/drivers` (`docs` statuses, `doc_ids` for
  the viewer, `bank_masked`, combined `car` string); document viewer →
  `GET /api/owner/documents/<doc_id>`; driver photo (also the profile
  picture document) → `GET /api/owner/drivers/<id>/photo`
