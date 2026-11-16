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

Flow: booking form (+ flight-number step for airport rides) →
"Choose your experience" options page (Business Class / Business SUV,
one single total each) → card payment → booking sent to drivers →
chauffeur accepts → driver details + live map. Payment always comes
BEFORE any driver sees the booking; unpaid bookings never appear in
driver offers. The form button says "View options" and opens the
separate options page; picking a class proceeds to payment.

- Booking form, One way / By the hour tabs
  → `POST /api/bookings` (returns the booking with its single `total`,
  status `awaiting_payment`, and — for one-way rides — `class_totals`
  with one total per class and the default `vehicle_class` "sedan")
- "Choose your experience" options page (one-way rides only): trip
  summary (pickup, drop-off, date, time) + two selectable class pills,
  Business Class pre-selected, each showing its own single total (no
  breakdown, no rates, no miles). Back returns to the form to edit and
  cancels the unpaid booking. Picking a class calls
  → `POST /api/bookings/<id>/vehicle-class` (only while
  `awaiting_payment`; rejected after payment) and then the payment box
  opens with the chosen total. Hourly rides skip this page (no class).
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
- Single total shown on the options page and with the payment box
  (single total only, no breakdown)
  → `total` and `class_totals` fields returned on booking create, on
  class selection, and on `GET /api/bookings/<id>` (always present for
  the customer)
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
  Uber Black list, 23 makes). The driver's vehicle class is DERIVED
  from the chosen model via the explicit mapping in `car_models.py`
  (`VEHICLE_CLASS_BY_MAKE`, all 133 models) and stored on the driver
  record; it is shown in the driver profile and in the owner driver
  views as "Business Class" / "Business SUV". The driver never types
  a class. Model year is a select from 2022 through
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
  → `GET /api/drivers/me/offers`; earnings value displayed as returned.
  One-way offers are filtered by vehicle class (sedan bookings only to
  sedan drivers, SUV bookings only to SUV drivers); hourly offers reach
  every available driver. Offers carry the class display name, never
  miles, fare, tax, or total.
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
  by document type, e.g. `dmv_license: "completed"`). The document list
  has 7 items, headed by the single "DMV driving license" item (the old
  duplicate license item was merged into it 2026-11-16).
- Profile tab → `GET /api/drivers/me` (bank shown masked, last 4 only)
- "Register a different driver" clears the stored token.

## Owner dashboard — section to API mapping

- PIN gate → `POST /api/owner/login` (session cookie); session checked
  with `GET /api/owner/summary`; `POST /api/owner/logout`
- Summary cards → `GET /api/owner/summary` (gross, profit, driver
  owed, tax collected, per-status counts)
- Bookings table with full per-ride breakdown, as returned by the API
  (customer total, fare, tax, driver share, toll, gratuity, waiting,
  profit = total + waiting − driver − tax, plus the class display name)
  → `GET /api/owner/bookings`
- Booking detail view → `GET /api/owner/bookings/<id>`
- Toll entry per booking → `POST /api/owner/bookings/<id>/toll`
- Driver payouts: per-driver, per-week totals
  → `GET /api/owner/payouts`; mark a week paid
  → `POST /api/owner/payouts/mark-paid` with `driver_id` + `week_index`
- Alerts feed → `GET /api/owner/alerts`
- Messages outbox → `GET /api/owner/outbox`
- Drivers list → `GET /api/owner/drivers` (`docs` statuses, `doc_ids` for
  the viewer, `bank_masked`, combined `car` string, vehicle class
  display name); document viewer →
  `GET /api/owner/documents/<doc_id>`; driver photo (also the profile
  picture document) → `GET /api/owner/drivers/<id>/photo`

## Pricing & vehicle classes (settled by the owner, 2026-11-16)

All pricing lives in `pricing.py` (pure functions, Decimal). The
frontend never works out a price. The customer sees ONE single total
per class — never a breakdown, never rates, never miles. The owner
dashboard holds the full breakdown. The driver sees only earnings.

- TWO classes only: sedan ("Business Class") and SUV ("Business SUV").
  No S-Class / First Class. Internal keys stay `sedan`/`suv` everywhere;
  display names are `Business Class` / `Business SUV` on the options
  page, in trip summaries, and in owner/driver views.
- One-way: fare = miles × class rate (sedan $11/mile, SUV $12/mile);
  gratuity = 10% of the fare (owner profit, never driver pay); NYC tax
  = 8.875% of the fare (pass-through, neither profit nor driver pay);
  toll is added untaxed and passed to the driver. Customer total =
  fare + gratuity + tax + toll. Driver earnings = miles × driver rate
  (sedan $4/mile, SUV $7/mile) + toll. Owner profit = total − driver
  − tax (+ waiting, which goes to owner profit). NO booking fee ($0).
  This supersedes the old $20 fee + $7/mile formula entirely.
- NYC tax verification (checked 2026-11-16): NYC311/TLC confirm
  8.875% on car-service/limousine/black-car passenger fares, and
  Blacklane's own quote applied exactly 8.875% to the base fare.
  Tolls are not taxed (pass-through, as Blacklane shows fees untaxed).
- Referral codes are accepted but give a $0 discount for now: the old
  benefit (waiving the $20 booking fee) no longer applies since there
  is no fee. A new referral benefit is TBD pending the owner's
  decision — do not invent one.
- Hourly rides are UNCHANGED: $90/hour customer, $50/hour driver, no
  fee, no gratuity, no tax. Whether hourly rides get tax is TBD
  pending the owner's decision; do not add tax to hourly.
- Verified examples: 20-mile SUV = fare $240 + gratuity $24 + tax
  $21.30 = total $285.30, driver $140, profit $124. 20-mile sedan =
  fare $220 + gratuity $22 + tax $19.53 = total $261.53, driver $80,
  profit $162.

## Model → class mapping (car_models.py)

`VEHICLE_CLASS_BY_MAKE` maps all 133 eligible models to exactly one
class (85 SUVs, 48 sedans). Rule: SUV/crossover body styles are SUVs;
sedans, coupes, hatchbacks and wagons are sedans. All 23 Black SUV
models from `UBER_BLACK_LIST.md` are SUVs. Judgment calls:

- Wagons and hatchback sedans are sedans: Audi A6 Avant, Audi RS 6,
  Audi A7 / RS 7 / S7 (Sportback), Porsche Panamera and Taycan.
- Coupe-roof SUVs are SUVs: BMW X6, Mercedes-Benz GLC Coupe and GLE
  Coupe, Porsche Cayenne Coupe (SUV body style, coupe roofline).
- Audi e-tron (no Q prefix) is an SUV: the original e-tron is a
  midsize SUV, later renamed Q8 e-tron.
- Compact crossovers are SUVs: Audi Q4 e-tron, BMW X3, Cadillac
  Optiq, Genesis GV60, Lincoln Corsair, Mercedes-Benz EQB, Volvo
  XC60 (and their hybrid variants).
- Jeep Wagoneer S is an SUV (electric midsize SUV) even though it is
  not one of the 23 Black SUV models (source marks it SF Bay Area
  only).
- Lincoln MKT is an SUV (crossover).
- Mercedes-Benz GLC-Class / GLE-Class / GLS-Class (and 350e
  variants) are SUVs — naming variants of the GLC / GLE / GLS.
- Tesla Model 3 is a sedan (the temporary owner-trial exception);
  Model S is a sedan, Model X is the SUV.
