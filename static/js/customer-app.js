/* Noel Chauffer — customer app logic (browser-based, /app).
   Talks only to the /api/* contract — the SAME endpoints and flow as
   the customer website (static/js/customer.js). Bookings are LIVE
   (owner decision 2026-11-20: Blacklane prices + slab driver pay):
   the booking form submits, the options screen shows each class
   total, and the card payment opens from the booking status.
   Existing rides keep their status, chauffeur, chat and map views.
   Ride tracking lives in the My Rides tab; the support chat is
   scripted answers only (no AI); the referral tab mirrors the
   website's referral display exactly.
   No customer accounts
   exist: rides are looked up by phone number, as on the website. */
(function () {
  "use strict";

  var state = {
    rideType: "one_way",
    isReturnTrip: false,
    bookingId: null,
    bookingPhone: "",
    booking: null,
    pollTimer: null,
    paid: false,
    map: null,
    marker: null,
    mapReady: false,
    pickupPlace: null,
    dropoffPlace: null,
    flightNumber: null,
    flightResolved: false,
    pendingPayload: null,
    selectedClass: "sedan",
    /* Blacklane-style hourly (owner decision 2026-11-20): the class
       the customer picked on the form for a By-the-hour ride. */
    hourlyClass: "sedan",
    classBooking: null,
    classPhone: "",
    lastChatSig: "",
    chatLanguage: "en",
    chatLangInitFor: null,
    historyPhone: "",
    /* Stripe.js payment state. payMode: null = not decided yet,
       false = card payments unavailable, "test" = test mode (old
       raw-card form, server fakes the authorization), "stripe" =
       configured (Stripe.js Card Element; raw card details are
       NEVER read — Stripe's iframe holds them and only a
       PaymentMethod id (pm_...) ever leaves the browser). */
    stripe: null,
    cardElement: null,
    payMode: null,
    testModePaid: false,
    payInitForBooking: null,
    savedCards: []
  };

  /* Customer-facing class names. Internal keys stay "sedan"/"suv". */
  var CLASS_LABELS = { sedan: "Business Class", suv: "Business SUV", first: "First Class" };
  /* Blacklane-style hourly rates, in cents (owner decision 2026-11-20,
     "same same Blacklane jaisa"): per-class totals from the live
     Blacklane quote 2026-11-20 (2-hour totals Business $218.32, SUV
     $269.46, First $343.31). First is 17165.5 cents/hour ($343.31 / 2),
     kept at half-cent precision so the 2-hour total is exactly
     Blacklane's $343.31 — the server prices the same way. Totals are
     computed in whole cents so the card totals always match the
     server to the cent. */
  var HOURLY_RATE_CENTS = { sedan: 10916, suv: 13473, first: 17165.5 };
  var HOURLY_MILES_PER_HOUR = 25;
  function hourlyTotalCents(cls, hours) {
    return Math.round(HOURLY_RATE_CENTS[cls] * hours);
  }
  function paintHourlyTotals() {
    var h = parseInt($("ca-hours").value, 10);
    if (isNaN(h) || h < 2) h = 2;
    if (h > 24) h = 24;
    ["sedan", "suv", "first"].forEach(function (cls) {
      var el = $("ca-hr-total-" + cls);
      if (el) el.textContent = "$" + (hourlyTotalCents(cls, h) / 100).toFixed(2);
    });
    var note = $("ca-hr-miles-note");
    if (note) note.textContent = "Includes " + (h * HOURLY_MILES_PER_HOUR) + " miles of travel (" + HOURLY_MILES_PER_HOUR + " miles per hour) — taxes and tolls included.";
    paintHourlyBreakdown();
  }
  /* Hourly price breakdown (owner decision 2026-11-21 ~18:56 EST:
     every ride gets a breakdown, one-way and hourly). The hourly
     rate is all-in — taxes and tolls are inside the per-hour rate —
     so the breakdown is Base fare (hours x rate) + Total. */
  function paintHourlyBreakdown() {
    var box = $("ca-hourly-class-breakdown");
    if (!box) return;
    var h = parseInt($("ca-hours").value, 10);
    if (isNaN(h) || h < 2) h = 2;
    if (h > 24) h = 24;
    var total = hourlyTotalCents(state.hourlyClass, h) / 100;
    box.innerHTML = '<div class="breakdown-row"><span>Base fare</span><span>' + esc(money(total)) + '</span></div>'
      + '<div class="breakdown-row breakdown-total"><span>Total</span><span>' + esc(money(total)) + '</span></div>';
  }
  function paintHourlyClassSelection() {
    ["sedan", "suv", "first"].forEach(function (cls) {
      var opt = $("ca-hr-class-" + cls);
      if (!opt) return;
      var selected = state.hourlyClass === cls;
      opt.classList.toggle("selected", selected);
      opt.setAttribute("aria-checked", selected ? "true" : "false");
    });
    var cont = $("ca-hourly-class-continue");
    if (cont) cont.textContent = "Select " + (CLASS_LABELS[state.hourlyClass] || "Business Class");
    paintHourlyBreakdown();
  }
  function classLabelFor(b) {
    if (!b) return "";
    return b.vehicle_class_label || CLASS_LABELS[b.vehicle_class] || "";
  }
  function summaryText(b) {
    var text = rideLabel(b);
    var cls = classLabelFor(b);
    if (cls) text += " · " + cls;
    if (b.ride_type !== "hourly") text += " · " + rideTypeLabel(b);
    if (whenLabel(b)) text += " · " + whenLabel(b);
    return text;
  }

  function $(id) { return document.getElementById(id); }
  function show(el) { if (el) el.classList.remove("hidden"); }
  function hide(el) { if (el) el.classList.add("hidden"); }
  /* Bookings are LIVE (owner decision 2026-11-20: Blacklane prices
     + slab driver pay, "Driver aur customer dono live kar do").
     The server still enforces the pause either way. */
  var BOOKINGS_PAUSED = false;
  function money(n) {
    if (n === null || n === undefined || isNaN(Number(n))) return "";
    return "$" + Number(n).toFixed(2);
  }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function rideLabel(b) {
    if (!b) return "";
    if (b.ride_type === "hourly") {
      return "By the hour" + (b.hours ? " · " + b.hours + " hour(s)" : "") +
        " · Pickup: " + (b.pickup || "");
    }
    return (b.pickup || "") + "  →  " + (b.dropoff || "");
  }
  /* "Return trip" is a second one-way booking made through
     the return-trip button (owner decision 2026-11-20): it
     must display as "Return trip", never "One way". */
  function rideTypeLabel(b) {
    if (!b) return "";
    if (b.ride_type === "hourly") return "By the hour";
    if (b.is_return) return "Return trip";
    return "One way";
  }
  function whenLabel(b) {
    if (!b) return "";
    var parts = [];
    if (b.date) parts.push(b.date);
    if (b.time) parts.push(b.time);
    return parts.join(" · ");
  }
  function statusLabel(status) {
    var map = {
      awaiting_payment: "Payment needed to confirm your ride",
      offered: "Finding your chauffeur…",
      accepted: "Chauffeur confirmed",
      en_route: "Your chauffeur is on the way",
      arrived: "Your chauffeur has arrived",
      started: "Your ride is under way",
      on_trip: "Your ride is under way",
      in_progress: "Your ride is under way",
      completed: "Ride completed — thank you",
      cancelled: "This booking was cancelled",
      canceled: "This booking was cancelled",
      no_show: "Marked as a no-show"
    };
    return map[status] || String(status || "");
  }

  /* ---------- Tab bar / screens (driver-app pattern) ---------- */
  var SCREENS = ["book", "rides", "support", "referral"];
  function showScreen(name) {
    /* While a ride is live, the Book tab does not open the form: the
       ride stays in front of the customer. The separate "Book another
       ride" button (which clears the ride first) is the only way to
       a fresh form. */
    if (name === "book" && hasActiveRide()) name = "rides";
    SCREENS.forEach(function (n) {
      var section = $("screen-" + n);
      if (section) section.classList.toggle("hidden", n !== name);
    });
    document.querySelectorAll("#ca-tabbar button").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-screen") === name);
    });
    var section = $("screen-" + name);
    if (section) section.scrollTop = 0;
    window.scrollTo(0, 0);
  }
  document.querySelectorAll("#ca-tabbar button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      showScreen(btn.getAttribute("data-screen"));
    });
  });

  /* ---------- Ride-type tabs ---------- */
  var tabs = document.querySelectorAll(".ride-tab");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(function (t) {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });
      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      state.rideType = tab.getAttribute("data-ride-type");
      state.isReturnTrip = false;
      if (state.rideType === "hourly") {
        hide($("ca-field-dropoff"));
        show($("ca-field-hours"));
        hide($("ca-hourly-class-step"));
        paintHourlyClassSelection();
        paintHourlyTotals();
        state.dropoffPlace = null;
        /* Hourly class/rates show ONLY after View options (owner
           decision 2026-11-21), on a separate step — never on the
           first screen. Name/phone/email stay on the booking form:
           one-way rides ask them on the options page instead
           (Blacklane-style). */
        show($("ca-field-contact"));
      } else {
        show($("ca-field-dropoff"));
        hide($("ca-field-hours"));
        hide($("ca-hourly-class-step"));
        hide($("ca-field-contact"));
      }
    });
  });

  /* Hourly class picker (Blacklane-style hourly, owner decision
     2026-11-20): the three class cards on the hourly class step
     (shown only after View options, owner decision 2026-11-21).
     Picking one sets the class sent with the booking; the totals
     on the cards follow the hours input. */
  ["sedan", "suv", "first"].forEach(function (cls) {
    var opt = $("ca-hr-class-" + cls);
    if (opt) opt.addEventListener("click", function () {
      state.hourlyClass = cls;
      paintHourlyClassSelection();
    });
  });
  var hoursInput = $("ca-hours");
  if (hoursInput) hoursInput.addEventListener("input", paintHourlyTotals);

  /* Date input: no past dates. */
  (function () {
    var d = new Date();
    var iso = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
    $("ca-date").setAttribute("min", iso);
  })();

  /* ---------- USA address search (autocomplete only) ---------- */
  /* Same as the website: typing shows USA-only suggestions below the
     field, including airport terminals from real map data. Picking a
     suggestion stores its coordinates, which are sent with the
     booking. There is deliberately NO map inside the booking form
     and NO pin-drop. Suggestions show address text only — never
     any fare. */

  function clearBookingPlaces() {
    state.pickupPlace = null;
    state.dropoffPlace = null;
    state.flightNumber = null;
    state.flightResolved = false;
    state.pendingPayload = null;
  }

  /* A ride is live while a booking is being tracked and its status is
     not a terminal one. While a ride is live the customer sees ONLY
     that ride: the Book tab does not open the form, and the form
     cannot be re-submitted into a duplicate booking. */
  var TERMINAL_RIDE_STATUSES = ["cancelled", "canceled", "completed", "no_show"];
  function hasActiveRide() {
    if (!state.bookingId) return false;
    if (!state.booking) return true;
    return TERMINAL_RIDE_STATUSES.indexOf(state.booking.status || "") === -1;
  }

  /* Fresh empty booking form: used whenever the customer starts a NEW
     booking (Book another ride, All rides, or after a cancellation)
     so the previous ride's values can never be re-submitted as a
     duplicate. The only pre-filled return is the return-trip button,
     which sets its swapped addresses itself, after this reset. */
  function clearBookingForm() {
    ["ca-name", "ca-phone", "ca-email", "ca-pickup", "ca-dropoff",
     "ca-date", "ca-time", "ca-referral"
    ].forEach(function (id) { var el = $(id); if (el) el.value = ""; });
    $("ca-hours").value = "2";
    state.hourlyClass = "sedan";
    paintHourlyClassSelection();
    paintHourlyTotals();
    $("ca-booking-error").textContent = "";
    var btn = $("ca-book-submit");
    if (btn) { btn.disabled = false; btn.textContent = "View options"; }
    tabs.forEach(function (t) {
      var active = t.getAttribute("data-ride-type") === "one_way";
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    state.rideType = "one_way";
    state.isReturnTrip = false;
    show($("ca-field-dropoff"));
    hide($("ca-field-hours"));
    hide($("ca-hourly-class-step"));
    hide($("ca-field-contact"));
    clearBookingPlaces();
  }

  function attachPlaces(inputId, listId, kind) {
    var input = $(inputId);
    var list = $(listId);
    var timer = null;
    var seq = 0;
    var controller = null;
    var activeIndex = -1;
    var items = [];

    function closeList() {
      hide(list);
      list.innerHTML = "";
      items = [];
      activeIndex = -1;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    function clearStored() {
      if (kind === "pickup") { state.pickupPlace = null; } else { state.dropoffPlace = null; }
      /* Editing an address re-arms the flight-number step, so a changed
         airport address is asked about again on the next submit. */
      state.flightResolved = false;
    }
    function choose(item) {
      input.value = item.display_name;
      if (kind === "pickup") { state.pickupPlace = item; } else { state.dropoffPlace = item; }
      closeList();
    }
    function paintActive() {
      var btns = list.querySelectorAll("button");
      btns.forEach(function (b, i) {
        b.classList.toggle("active", i === activeIndex);
        b.setAttribute("aria-selected", i === activeIndex ? "true" : "false");
      });
      if (activeIndex >= 0 && btns[activeIndex]) {
        input.setAttribute("aria-activedescendant", btns[activeIndex].id);
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }
    function render(results) {
      items = results;
      activeIndex = -1;
      list.innerHTML = "";
      if (!results.length) { closeList(); return; }
      results.forEach(function (item, idx) {
        var parts = String(item.display_name).split(",");
        var main = parts.shift().trim();
        var detail = parts.join(",").trim();
        var li = document.createElement("li");
        var btn = document.createElement("button");
        btn.type = "button";
        btn.setAttribute("role", "option");
        btn.setAttribute("aria-selected", "false");
        btn.id = listId + "-opt-" + idx;
        var mainEl = document.createElement("span");
        mainEl.className = "places-main";
        mainEl.textContent = main || item.display_name;
        btn.appendChild(mainEl);
        if (detail) {
          var detEl = document.createElement("span");
          detEl.className = "places-detail";
          detEl.textContent = detail;
          btn.appendChild(detEl);
        }
        /* mousedown fires before the input loses focus, so a tap or
           click always lands on the suggestion. */
        btn.addEventListener("mousedown", function (e) {
          e.preventDefault();
          choose(item);
        });
        li.appendChild(btn);
        list.appendChild(li);
      });
      show(list);
      input.setAttribute("aria-expanded", "true");
    }
    function search(query) {
      var mySeq = ++seq;
      if (controller) controller.abort();
      controller = new AbortController();
      fetch("/api/places/search?q=" + encodeURIComponent(query) + "&limit=5",
        { signal: controller.signal })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (mySeq !== seq) return;
          render((j && Array.isArray(j.results)) ? j.results : []);
        })
        .catch(function () {
          if (mySeq === seq) closeList();
        });
    }

    input.addEventListener("input", function () {
      clearStored();
      if (timer) clearTimeout(timer);
      var q = input.value.trim();
      if (q.length < 3) { closeList(); return; }
      timer = setTimeout(function () { search(input.value.trim()); }, 350);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { closeList(); return; }
      if (list.classList.contains("hidden") || !items.length) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        var dir = e.key === "ArrowDown" ? 1 : -1;
        activeIndex = (activeIndex + dir + items.length) % items.length;
        paintActive();
      } else if (e.key === "Enter" && activeIndex >= 0) {
        e.preventDefault();
        choose(items[activeIndex]);
      }
    });
    input.addEventListener("blur", function () {
      setTimeout(function () {
        if (!list.contains(document.activeElement)) closeList();
      }, 150);
    });
    document.addEventListener("click", function (e) {
      if (!list.contains(e.target) && e.target !== input) closeList();
    });
  }

  attachPlaces("ca-pickup", "ca-pickup-list", "pickup");
  attachPlaces("ca-dropoff", "ca-dropoff-list", "dropoff");

  /* Past dates and times cannot be booked (owner decision
     2026-11-20). All comparisons use America/New_York, the service
     area: the date picker starts at today, and submitting a past
     date — or today at a time already gone — is refused. */
  function todayNY() {
    var parts = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
    var y, m, d;
    parts.forEach(function (p) { if (p.type === "year") y = p.value; if (p.type === "month") m = p.value; if (p.type === "day") d = p.value; });
    return y + "-" + m + "-" + d;
  }
  function nowTimeNY() {
    var parts = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date());
    var h, mi;
    parts.forEach(function (p) { if (p.type === "hour") h = p.value; if (p.type === "minute") mi = p.value; });
    return h + ":" + mi;
  }
  $("ca-date").min = todayNY();

  /* ---------- Create a booking ---------- */
  $("ca-booking-form").addEventListener("submit", function (e) {
    e.preventDefault();
    /* While a ride is live the Book tab does not open this form; this
       guard stops any re-submit of the same ride (double tap,
       restored page) from creating a duplicate booking. A fresh
       booking first clears the ride state — see Book another ride /
       return trip / cancel / All rides. */
    if (hasActiveRide()) return;
    var err = $("ca-booking-error");
    err.textContent = "";
    /* Bookings are PAUSED while prices are being updated (owner
       decision 2026-11-20): nothing is submitted. */
    if (BOOKINGS_PAUSED) {
      err.textContent = "Bookings are paused while we update our prices. Please check back soon.";
      return;
    }
    var payload = {
      pickup: $("ca-pickup").value.trim(),
      date: $("ca-date").value,
      time: $("ca-time").value,
      ride_type: state.rideType
    };
    /* Name, phone and email are asked on the options page for
       one-way rides (Blacklane-style). Hourly rides ask them on the
       form, and pick their class on the separate class step. */
    if (state.rideType === "hourly") {
      payload.customer_name = $("ca-name").value.trim();
      payload.phone = $("ca-phone").value.trim();
      payload.email = $("ca-email").value.trim();
    }
    if (state.rideType === "one_way") {
      payload.dropoff = $("ca-dropoff").value.trim();
      if (state.isReturnTrip) payload.is_return = true;
      var ref = $("ca-referral").value.trim();
      if (ref) payload.referral_code = ref;
    } else {
      /* Blacklane-style hourly (owner decision 2026-11-20): 2 to 24
         hours. The class is picked on the separate class step after
         View options (owner decision 2026-11-21), not here. */
      var h = parseInt($("ca-hours").value, 10);
      if (isNaN(h) || h < 2 || h > 24) {
        err.textContent = "Hourly bookings need 2 to 24 hours.";
        return;
      }
      payload.hours = h;
    }
    /* When the customer picked a suggestion, send its coordinates so
       the fare is priced for exactly the place picked. */
    if (state.pickupPlace && isFinite(state.pickupPlace.lat) && isFinite(state.pickupPlace.lon)) {
      payload.pickup_lat = state.pickupPlace.lat;
      payload.pickup_lng = state.pickupPlace.lon;
    }
    if (state.rideType === "one_way" && state.dropoffPlace && isFinite(state.dropoffPlace.lat) && isFinite(state.dropoffPlace.lon)) {
      payload.dropoff_lat = state.dropoffPlace.lat;
      payload.dropoff_lng = state.dropoffPlace.lon;
    }
    if (!payload.pickup || !payload.date || !payload.time) {
      err.textContent = "Please fill in your pickup, date and time.";
      return;
    }
    /* Past dates and times cannot be booked (owner decision
       2026-11-20): an old date — or today at a time already gone —
       is refused here, before anything is sent. */
    var today = todayNY();
    if (payload.date < today) {
      err.textContent = "Please choose a date from today onwards. Past dates cannot be booked.";
      return;
    }
    if (payload.date === today && payload.time <= nowTimeNY()) {
      err.textContent = "Please choose a time later than now. Past times cannot be booked.";
      return;
    }
    if (state.rideType === "hourly" && (!payload.customer_name || !payload.phone || !payload.email)) {
      err.textContent = "Please fill in your name, phone and email.";
      return;
    }
    if (state.rideType === "one_way" && !payload.dropoff) {
      err.textContent = "Please enter a drop-off address.";
      return;
    }
    /* Flight number: REMOVED from the booking form and the separate
       step by owner order 2026-11-20 ("flight number nahi aana
       chahiye abhi"). The step code below (showFlightStep and
       friends) stays in place, unused, so the field can come back on
       his word; the server still accepts flight_number. */
    if (state.rideType === "hourly") {
      /* Hourly rides go to the class step first: the class, the
         per-class rates and the miles note show ONLY after View
         options (owner decision 2026-11-21). The booking is created
         from the class step, with the class picked there. */
      showHourlyClassStep(payload);
    } else {
      sendBooking(payload);
    }
  });

  /* Flight-number step: shown after the booking form for airport rides. */
  function showFlightStep(sides, payload) {
    state.pendingPayload = payload;
    if (sides.pickup) {
      $("ca-flight-step-title").textContent = "Add your flight number";
      $("ca-flight-step-text").textContent = "Your chauffeur will meet you at the right terminal.";
    } else {
      $("ca-flight-step-title").textContent = "Add your flight number (optional)";
      $("ca-flight-step-text").textContent = "This helps your chauffeur take you to the right departure terminal.";
    }
    $("ca-flight-step-airport").textContent = sides.pickup ? payload.pickup : (payload.dropoff || "");
    $("ca-flight-number").value = state.flightNumber || "";
    hide($("ca-booking-card"));
    show($("ca-flight-step"));
    $("screen-book").scrollTop = 0;
    $("ca-flight-number").focus();
  }

  function proceedFromFlightStep() {
    hide($("ca-flight-step"));
    show($("ca-booking-card"));
    var payload = state.pendingPayload;
    state.pendingPayload = null;
    if (!payload) return;
    if (state.flightNumber) payload.flight_number = state.flightNumber;
    sendBooking(payload);
  }

  $("ca-flight-continue").addEventListener("click", function () {
    state.flightNumber = $("ca-flight-number").value.trim() || null;
    state.flightResolved = true;
    proceedFromFlightStep();
  });
  $("ca-flight-skip").addEventListener("click", function () {
    state.flightNumber = null;
    state.flightResolved = true;
    proceedFromFlightStep();
  });
  $("ca-flight-back").addEventListener("click", function () {
    hide($("ca-flight-step"));
    show($("ca-booking-card"));
    $("screen-book").scrollTop = 0;
  });

  /* Hourly class step (owner decision 2026-11-21): the class, the
     per-class rates and the miles note show ONLY after View options.
     The booking does not exist yet — the class is picked here, then
     the booking is created with it. Back returns to the form with
     its values kept; nothing was created, so nothing is cancelled. */
  function showHourlyClassStep(payload) {
    state.pendingPayload = payload;
    $("ca-hourly-class-trip-summary").textContent =
      "By the hour · " + payload.hours + " hour(s) · Pickup: " + payload.pickup;
    $("ca-hourly-class-error").textContent = "";
    paintHourlyTotals();
    paintHourlyClassSelection();
    hide($("ca-booking-card"));
    show($("ca-hourly-class-step"));
    $("screen-book").scrollTop = 0;
  }

  $("ca-hourly-class-continue").addEventListener("click", function () {
    var payload = state.pendingPayload;
    if (!payload) return;
    payload.vehicle_class = state.hourlyClass;
    state.pendingPayload = null;
    sendBooking(payload);
  });
  $("ca-hourly-class-back").addEventListener("click", function () {
    state.pendingPayload = null;
    hide($("ca-hourly-class-step"));
    show($("ca-booking-card"));
    $("screen-book").scrollTop = 0;
  });

  /* Choose your experience: a SEPARATE options screen after the booking
     form. The booking already exists, unpaid;
     the customer picks a class — each option shows its total —
     and then continues to the card payment. Sedan (Business Class)
     is pre-selected. Back cancels the unpaid booking and returns
     to the form to edit. */
  function paintClassSelection() {
    ["sedan", "suv", "first"].forEach(function (cls) {
      var opt = $("ca-class-option-" + cls);
      var selected = state.selectedClass === cls;
      opt.classList.toggle("selected", selected);
      opt.setAttribute("aria-checked", selected ? "true" : "false");
    });
    $("ca-class-continue").textContent = "Select " + (CLASS_LABELS[state.selectedClass] || "Business Class");
    paintClassBreakdown();
  }

  /* Price breakdown for the selected class (Blacklane-style): the
     fare composition the customer pays, in the owner's line order
     (2026-11-21 ~18:56 EST) — Base fare, Airport access fee (only
     on airport rides), Black car fee, Sales tax, Congestion (NY
     State + MTA), Toll (only when the route has one), then Total.
     Only lines above $0 are shown; the total always matches the
     class option's total. No refund line in the breakdown. */
  function paintClassBreakdown() {
    var box = $("ca-class-breakdown");
    if (!box) return;
    var b = (state.classBreakdowns || {})[state.selectedClass];
    if (!b) { box.innerHTML = ""; return; }
    var rows = [["Base fare", money(b.base)]];
    if (Number(b.airport_access) > 0) rows.push(["Airport access fee", money(b.airport_access)]);
    if (Number(b.black_car_fee) > 0) rows.push(["Black car fee", money(b.black_car_fee)]);
    if (Number(b.sales_tax) > 0) rows.push(["Sales tax", money(b.sales_tax)]);
    if (Number(b.ny_congestion) > 0) rows.push(["NY State congestion surcharge", money(b.ny_congestion)]);
    if (Number(b.mta_congestion) > 0) rows.push(["MTA congestion surcharge", money(b.mta_congestion)]);
    if (Number(b.toll) > 0) rows.push(["Toll", money(b.toll)]);
    if (Number(b.referral_discount) > 0) rows.push(["Referral discount", "−" + money(b.referral_discount)]);
    var html = rows.map(function (r) {
      return '<div class="breakdown-row"><span>' + esc(r[0]) + '</span><span>' + esc(r[1]) + '</span></div>';
    }).join("");
    html += '<div class="breakdown-row breakdown-total"><span>Total</span><span>' + esc(money(b.total)) + '</span></div>';
    box.innerHTML = html;
  }

  function showClassStep(booking, phone) {
    state.classBooking = booking;
    state.classPhone = phone;
    state.selectedClass = booking.vehicle_class || "sedan";
    $("ca-class-trip-summary").textContent = summaryText(booking);
    /* First Class is offered only when the booking's class totals
       include it (Blacklane mode — the legacy engine has no First
       Class rate, so the option stays hidden there). */
    var firstAvailable = !!(booking.class_totals && booking.class_totals.first != null);
    if (!firstAvailable && state.selectedClass === "first") state.selectedClass = "sedan";
    if (firstAvailable) { show($("ca-class-option-first")); } else { hide($("ca-class-option-first")); }
    /* Each option shows its total (Blacklane mode, owner decision
       2026-11-20): the total the customer will pay, with the 5%
       first-ride referral discount already applied when granted. */
    var totals = booking.class_totals || {};
    $("ca-class-total-sedan").textContent = totals.sedan != null ? money(totals.sedan) : "";
    $("ca-class-total-suv").textContent = totals.suv != null ? money(totals.suv) : "";
    $("ca-class-total-first").textContent = totals.first != null ? money(totals.first) : "";
    /* Per-class fare breakdowns for the options page (Blacklane
       mode only; legacy bookings carry none). */
    state.classBreakdowns = booking.class_breakdowns || {};
    /* 5% first-ride referral discount (owner decision 2026-11-18):
       the note shows only when this booking actually got the
       discount. */
    if (booking.referral_discount && Number(booking.referral_discount) > 0) {
      show($("ca-class-discount-note"));
    } else {
      hide($("ca-class-discount-note"));
    }
    /* Contact is asked here (Blacklane-style): start empty — the
       booking was created without it. */
    $("ca-class-name").value = "";
    $("ca-class-phone").value = "";
    $("ca-class-email").value = "";
    $("ca-class-error").textContent = "";
    paintClassSelection();
    hide($("ca-booking-card"));
    show($("ca-class-step"));
    $("screen-book").scrollTop = 0;
  }

  ["sedan", "suv", "first"].forEach(function (cls) {
    $("ca-class-option-" + cls).addEventListener("click", function () {
      state.selectedClass = cls;
      paintClassSelection();
    });
  });

  $("ca-class-continue").addEventListener("click", function () {
    var booking = state.classBooking;
    if (!booking) return;
    var err = $("ca-class-error");
    err.textContent = "";
    var btn = $("ca-class-continue");
    /* Contact (Blacklane-style): name, phone and email are asked on
       this page, after the class is picked. They are saved first —
       the invoice and driver messages need them, and saving the
       phone decides the referral discount — then the class change
       (if any) and payment follow. */
    var contactName = $("ca-class-name").value.trim();
    var contactPhone = $("ca-class-phone").value.trim();
    var contactEmail = $("ca-class-email").value.trim();
    if (!contactName || !contactPhone || !contactEmail || contactEmail.indexOf("@") === -1) {
      err.textContent = "Please fill in your name, phone and email.";
      return;
    }
    function proceedWith(updated) {
      hide($("ca-class-step"));
      show($("ca-booking-card"));
      state.classBooking = null;
      startTracking(updated, state.classPhone);
    }
    function saveContact(next) {
      fetch("/api/bookings/" + encodeURIComponent(booking.id) + "/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_name: contactName, phone: contactPhone, email: contactEmail })
      })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (!res.ok || !res.j.booking) {
            btn.disabled = false;
            err.textContent = (res.j && (res.j.error || res.j.message)) || "Your details could not be saved. Please try again.";
            return;
          }
          state.classPhone = contactPhone;
          next(res.j.booking);
        })
        .catch(function () {
          btn.disabled = false;
          err.textContent = "Could not reach the booking service. Please try again.";
        });
    }
    btn.disabled = true;
    saveContact(function (withContact) {
      if (state.selectedClass === (withContact.vehicle_class || "sedan")) {
        proceedWith(withContact);
        return;
      }
      fetch("/api/bookings/" + encodeURIComponent(withContact.id) + "/vehicle-class", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ vehicle_class: state.selectedClass })
      })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          btn.disabled = false;
          if (!res.ok || !res.j.booking) {
            err.textContent = (res.j && (res.j.error || res.j.message)) || "That class could not be selected. Please try again.";
            return;
          }
          proceedWith(res.j.booking);
        })
        .catch(function () {
          btn.disabled = false;
          err.textContent = "Could not reach the booking service. Please try again.";
        });
    });
  });

  $("ca-class-back").addEventListener("click", function () {
    var booking = state.classBooking;
    var phone = state.classPhone;
    state.classBooking = null;
    state.classPhone = "";
    hide($("ca-class-step"));
    show($("ca-booking-card"));
    $("screen-book").scrollTop = 0;
    /* The booking was created but never paid: cancel it so it never
       reaches drivers, then the customer edits the form and submits
       again. A failed cancel is harmless — unpaid bookings are never
       sent to drivers. */
    if (booking && booking.id && phone) {
      fetch("/api/bookings/" + encodeURIComponent(booking.id) + "/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone })
      }).catch(function () { /* ignore */ });
    }
  });

  function sendBooking(payload) {
    var err = $("ca-booking-error");
    var btn = $("ca-book-submit");
    btn.disabled = true;
    btn.textContent = "Sending your request…";
    fetch("/api/bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        btn.textContent = "View options";
        if (!res.ok || !res.j.booking || !res.j.booking.id) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Something went wrong. Please try again.";
          /* The error lives on the booking form: if the customer
             came from the hourly class step, bring the form back so
             the error is visible. (One-way failures already show
             the form, so this is a no-op there.) */
          hide($("ca-hourly-class-step"));
          show($("ca-booking-card"));
          return;
        }
        var booking = res.j.booking;
        /* One-way rides go to the separate options screen first (pick a
           class); hourly rides picked their class on the class step
           and go straight to the payment step. */
        if (booking.ride_type === "one_way" && booking.class_totals) {
          showClassStep(booking, payload.phone);
        } else {
          startTracking(booking, payload.phone);
        }
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "View options";
        err.textContent = "Could not reach the booking service. Please check your connection and try again.";
        hide($("ca-hourly-class-step"));
        show($("ca-booking-card"));
      });
  }

  /* ---------- Ride tracking (My Rides tab) ---------- */
  function startTracking(booking, phone) {
    stopPolling();
    state.bookingId = booking.id;
    state.bookingPhone = phone;
    state.booking = booking;
    state.paid = false;
    state.testModePaid = false;
    state.payInitForBooking = null;
    state.flightNumber = null;
    state.flightResolved = false;
    state.pendingPayload = null;
    hide($("ca-thankyou-block"));
    hide($("ca-invoice-panel"));
    hide($("ca-pay-panel"));
    hide($("ca-driver-block"));
    hide($("ca-chat-panel"));
    hide($("ca-total-box"));
    hide($("ca-map-wrap"));
    hide($("ca-cancel-result"));
    $("ca-status-flight").textContent = "";
    hide($("ca-status-flight"));
    show($("ca-status-finding"));
    show($("ca-status-actions"));
    hide($("ca-history-block"));
    show($("ca-status-card"));
    showScreen("rides");
    /* The Book tab form is cleared the moment a ride exists, so it
       can never be re-submitted with the old ride's values — the
       ride stays in front of the customer until "Book another ride". */
    clearBookingForm();
    $("ca-status-summary").textContent = summaryText(booking);
    /* The total and the card payment box open from renderBooking. */
    renderBooking(booking);
    pollOnce();
    state.pollTimer = setInterval(pollOnce, 3000);
  }

  function stopPolling() {
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
  }

  function pollOnce() {
    if (!state.bookingId) return;
    fetch("/api/bookings/" + encodeURIComponent(state.bookingId))
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.booking) {
          state.booking = j.booking;
          renderBooking(j.booking);
          loadChatIfOpen(j.booking);
          var st = j.booking.status;
          if (st === "cancelled" || st === "canceled" || st === "completed" || st === "no_show") {
            stopPolling();
          }
        }
      })
      .catch(function () { /* keep polling; a failed check changes nothing on screen */ });
  }

  function renderBooking(b) {
    $("ca-status-summary").textContent = summaryText(b);
    var flightEl = $("ca-status-flight");
    if (b.flight_number) {
      var flightText = "Flight: " + b.flight_number;
      if (b.airline_name) flightText += " · " + b.airline_name;
      if (b.terminal) flightText += " · " + b.terminal;
      flightEl.textContent = flightText;
      show(flightEl);
    } else {
      flightEl.textContent = "";
      hide(flightEl);
    }
    var hasDriver = !!(b.driver && b.driver.name);
    var st = b.status || "";

    if (hasDriver) {
      hide($("ca-status-finding"));
      show($("ca-driver-block"));
      $("ca-driver-name").textContent = b.driver.name || "";
      var carBits = [];
      if (b.driver.car_year) carBits.push(b.driver.car_year);
      if (b.driver.car_model) carBits.push(b.driver.car_model);
      if (b.driver.car_colour) carBits.push(b.driver.car_colour);
      $("ca-driver-car").textContent = carBits.join(" · ");
      $("ca-driver-plate").textContent = b.driver.plate || "";
      var ph = $("ca-driver-phone");
      ph.textContent = b.driver.phone || "";
      ph.href = b.driver.phone ? "tel:" + b.driver.phone.replace(/[^+0-9]/g, "") : "";
      var img = $("ca-driver-photo");
      var src = b.driver.photo_url || ("/api/bookings/" + encodeURIComponent(b.id) + "/driver-photo");
      if (img.getAttribute("src") !== src) img.setAttribute("src", src);
      img.onerror = function () { img.style.visibility = "hidden"; };
      img.onload = function () { img.style.visibility = "visible"; };
      $("ca-driver-status-line").textContent = statusLabel(st);
    } else {
      show($("ca-status-finding"));
      hide($("ca-driver-block"));
      if (st === "awaiting_payment") {
        $("ca-status-heading").textContent = "Your total is ready";
        $("ca-status-message").textContent = "Please pay by card below — your chauffeur will be assigned right after payment.";
      } else {
        $("ca-status-heading").textContent = "Finding your chauffeur…";
        $("ca-status-message").textContent = statusLabel(st) || "Your request is with us. Please keep this page open.";
      }
    }

    /* The single total: shown from the moment the booking exists. The
       card payment box opens with it; only after payment is the
       booking sent to drivers, so no payment step exists later. */
    if (b.total !== null && b.total !== undefined) {
      show($("ca-total-box"));
      $("ca-total-amount").textContent = money(b.total);
      $("ca-pay-amount-label").textContent = money(b.total);
    } else {
      hide($("ca-total-box"));
    }
    if (st === "awaiting_payment") {
      show($("ca-pay-panel"));
      initPayment();
    } else {
      hide($("ca-pay-panel"));
    }

    /* Live map: ONLY when the API says tracking is visible. */
    var tr = b.tracking || {};
    if (tr.visible && tr.lat !== null && tr.lat !== undefined && tr.lng !== null && tr.lng !== undefined) {
      show($("ca-map-wrap"));
      renderMap(Number(tr.lat), Number(tr.lng), b);
    } else {
      hide($("ca-map-wrap"));
    }

    /* Thank-you once the ride is paid for (payment confirms the
       booking; the chauffeur is assigned after payment). */
    if (state.paid || st === "offered" || st === "accepted" || st === "en_route" || st === "arrived" || st === "started" || st === "on_trip" || st === "in_progress" || st === "completed") {
      showThankYou(b);
    }
    if (b.invoice) {
      show($("ca-invoice-panel"));
      var invTotal = (b.invoice.total !== null && b.invoice.total !== undefined) ? b.invoice.total : b.total;
      $("ca-invoice-total").textContent = money(invTotal);
      if (b.invoice.waiting_charge) {
        show($("ca-invoice-waiting-row"));
        $("ca-invoice-waiting").textContent = money(b.invoice.waiting_charge);
      } else {
        hide($("ca-invoice-waiting-row"));
      }
      if (b.invoice.extra_distance_charge) {
        show($("ca-invoice-extra-row"));
        $("ca-invoice-extra").textContent = money(b.invoice.extra_distance_charge);
      } else {
        hide($("ca-invoice-extra-row"));
      }
      $("ca-invoice-grand").textContent = money(invTotal);
    }

    if (st === "cancelled" || st === "canceled") {
      hide($("ca-status-actions"));
      hide($("ca-pay-panel"));
      hide($("ca-total-box"));
      $("ca-status-heading").textContent = "Booking cancelled";
      $("ca-status-message").textContent = "This booking was cancelled.";
      show($("ca-status-finding"));
    }
    if (st === "completed") {
      hide($("ca-status-actions"));
      hide($("ca-pay-panel"));
    }
  }

  /* ---------- In-app chat with the chauffeur (text only) ---------- */
  /* Opens once a driver has accepted; messages carry text only and
     the customer sees no prices anywhere. The
     chat rides on the same polling loop as the booking status. */
  var CHAT_OPEN_STATUSES = ["accepted", "en_route", "arrived", "in_progress"];
  function chatOpenFor(b) {
    return !!(b && b.driver && b.driver.name && CHAT_OPEN_STATUSES.indexOf(b.status || "") !== -1);
  }
  /* Declared chat language: one picker, plain labels, default
     English. The server translates each message ONCE at send time
     into the other side's picked language and stores it; reads
     never translate. Same codes/labels as the website and driver
     pickers and translation.CHAT_LANGUAGES — keep all four in step. */
  var CHAT_LANGUAGES = ["en", "ur-Latn", "es", "fr", "ar", "hi", "bn", "pt"];
  var CHAT_LANG_KEY = "noel-chat-language";
  function validChatLanguage(v) {
    return CHAT_LANGUAGES.indexOf(v) !== -1 ? v : "en";
  }
  function initChatLanguage(b) {
    if (state.chatLangInitFor === state.bookingId) return;
    state.chatLangInitFor = state.bookingId;
    var saved = null;
    try { saved = window.localStorage.getItem(CHAT_LANG_KEY); } catch (e) { /* private mode */ }
    state.chatLanguage = validChatLanguage(saved || (b && b.chat_language) || "en");
    var sel = $("ca-ride-chat-language");
    if (sel) sel.value = state.chatLanguage;
  }
  function saveChatLanguage() {
    var sel = $("ca-ride-chat-language");
    if (!sel) return;
    state.chatLanguage = validChatLanguage(sel.value);
    try { window.localStorage.setItem(CHAT_LANG_KEY, state.chatLanguage); } catch (e) { /* private mode */ }
    /* Persist for this booking so the chauffeur's replies are
       translated into the picked language. Failures are silent:
       the picker value still travels with every send and poll. */
    if (state.bookingId && state.bookingPhone) {
      fetch("/api/bookings/" + encodeURIComponent(state.bookingId) + "/chat-language", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: state.bookingPhone, language: state.chatLanguage })
      }).catch(function () { /* keep chatting; language rides along anyway */ });
    }
    state.lastChatSig = "";
    loadChatIfOpen(state.booking);
  }
  function loadChatIfOpen(b) {
    if (!chatOpenFor(b) || !state.bookingId || !state.bookingPhone) {
      hide($("ca-chat-panel"));
      return;
    }
    show($("ca-chat-panel"));
    initChatLanguage(b);
    fetch("/api/bookings/" + encodeURIComponent(state.bookingId) + "/messages?phone=" +
          encodeURIComponent(state.bookingPhone) + "&language=" +
          encodeURIComponent(state.chatLanguage))
      .then(function (r) { return r.json(); })
      .then(function (j) { renderChat(j.messages || []); })
      .catch(function () { /* keep the current messages on a failed check */ });
  }
  function renderChat(messages) {
    var sig = messages.map(function (m) { return m.id + ":" + (m.text || "").length + ":" + (m.translated ? "1" : "0"); }).join("|");
    if (sig === state.lastChatSig) return;
    state.lastChatSig = sig;
    var box = $("ca-chat-messages");
    box.innerHTML = "";
    if (!messages.length) {
      box.innerHTML = '<p class="chat-empty">No messages yet. Your chauffeur can read your messages here.</p>';
      return;
    }
    messages.forEach(function (m) {
      var div = document.createElement("div");
      var mine = m.sender === "customer";
      div.className = "chat-msg " + (mine ? "mine" : "theirs");
      div.innerHTML = '<span class="who">' + (mine ? "You" : "Chauffeur") + "</span>" +
        '<span class="txt">' + esc(m.text) + "</span>";
      box.appendChild(div);
    });
    box.scrollTop = box.scrollHeight;
  }
  function sendChat() {
    if (!state.bookingId || !state.bookingPhone) return;
    var input = $("ca-chat-input");
    var text = input.value.trim();
    if (!text) return;
    var btn = $("ca-chat-send");
    btn.disabled = true;
    fetch("/api/bookings/" + encodeURIComponent(state.bookingId) + "/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: state.bookingPhone, text: text, language: state.chatLanguage })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (res.ok) {
          input.value = "";
          loadChatIfOpen(state.booking);
        }
      })
      .catch(function () { btn.disabled = false; });
  }
  $("ca-chat-send").addEventListener("click", sendChat);
  $("ca-chat-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); sendChat(); }
  });
  var rideChatLang = $("ca-ride-chat-language");
  if (rideChatLang) rideChatLang.addEventListener("change", saveChatLanguage);

  function showThankYou(b) {
    show($("ca-thankyou-block"));
    $("ca-thankyou-summary").textContent =
      "Ride confirmed: " + summaryText(b) + ".";
    /* Test-mode payments say so on the booked view — never presented
       as a real charge. */
    var testNote = $("ca-thankyou-test-note");
    if (testNote) {
      if (state.testModePaid) show(testNote); else hide(testNote);
    }
    /* The API returns the issued code as `referral_code` on the booking. */
    var code = b.referral_code || b.customer_referral_code || b.share_code || b.own_referral_code || null;
    if (code) {
      show($("ca-referral-code-line"));
      $("ca-referral-code-value").textContent = code;
      showReferralLink(code, THANKYOU_REFERRAL_IDS);
      showReferralCode(code);
    } else {
      hide($("ca-referral-code-line"));
      hide($("ca-referral-show-btn"));
      hide($("ca-referral-link-line"));
      hide($("ca-referral-link-actions"));
    }
    if (b.ride_type === "one_way") { show($("ca-return-trip-btn")); } else { hide($("ca-return-trip-btn")); }
  }

  /* ---------- Payment: test mode or Stripe.js, decided by the server ---------- */
  /* The owner's merchant Stripe account is DISABLED (charges and
     payouts off, rejected.fraud), so live card payments CANNOT
     activate until he resolves that with Stripe. Until then the
     site keeps working in TEST MODE: GET /api/stripe/publishable-key
     returns configured=false + test_mode=true, and the OLD raw-card
     form is shown with its TEST MODE label; the server fakes the
     authorization exactly as before and the booking proceeds to
     drivers. When configured=true (keys added — test keys work,
     live keys are blocked by the disabled account), the Stripe.js
     flow below is used instead and raw card fields are NEVER sent.
     If the server reports neither (configured=false, no test_mode),
     card payment is unavailable: the not-set-up message shows and
     Pay stays disabled. No fake success is ever claimed as real. */
  var STRIPE_NOT_CONFIGURED = "Card payments are not set up yet. Please try again later.";
  var stripeJsPromise = null;
  function loadStripeJs() {
    if (window.Stripe) return Promise.resolve();
    if (stripeJsPromise) return stripeJsPromise;
    stripeJsPromise = new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = "https://js.stripe.com/v3";
      s.async = true;
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error("Stripe.js failed to load")); };
      document.head.appendChild(s);
    });
    return stripeJsPromise;
  }

  /* Fetch the publishable key, then show the right payment form.
     Runs at most once per booking; renderBooking calls it on every
     poll, so the guard below is what keeps it cheap. */
  function initPayment() {
    if (!state.bookingId || state.payInitForBooking === state.bookingId) return;
    state.payInitForBooking = state.bookingId;
    var err = $("ca-pay-error");
    var unavailable = $("ca-pay-unavailable");
    var loading = $("ca-pay-loading");
    var submit = $("ca-pay-submit");
    err.textContent = "";
    hide(unavailable);
    hide($("ca-pay-test-mode"));
    hide($("ca-pay-stripe-mode"));
    $("ca-pay-saved-list").innerHTML = "";
    show(loading);
    submit.disabled = true;
    fetch("/api/stripe/publishable-key")
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; });
      })
      .then(function (res) {
        if (!res.ok) throw new Error("publishable key request failed");
        if (res.j && res.j.configured === true && res.j.publishable_key) {
          state.payMode = "stripe";
          return loadStripeJs().then(function () { return res.j.publishable_key; });
        }
        if (res.j && res.j.configured === false && res.j.test_mode === true) {
          /* Test mode: the old raw-card form, with its TEST MODE
             label. The server fakes the authorization. */
          state.payMode = "test";
          hide(loading);
          show($("ca-pay-test-mode"));
          submit.disabled = false;
          return null;
        }
        state.payMode = false;
        hide(loading);
        show(unavailable);
        unavailable.textContent = STRIPE_NOT_CONFIGURED;
        submit.disabled = true;
        return null;
      })
      .then(function (pk) {
        if (!pk) return;
        if (!state.stripe) {
          try { state.stripe = window.Stripe(pk); } catch (e) { state.stripe = null; }
        }
        if (!state.stripe) {
          hide(loading);
          err.textContent = "Could not start the secure payment form. Please try again.";
          return;
        }
        if (!state.cardElement) {
          var elements = state.stripe.elements();
          state.cardElement = elements.create("card", {
            style: {
              base: {
                color: "#ffffff",
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
                fontSize: "16px",
                "::placeholder": { color: "#8e8e93" }
              },
              invalid: { color: "#ff9d9d" }
            }
          });
          state.cardElement.mount("#ca-pay-card-element");
          state.cardElement.on("change", function (ev) {
            if (ev.error) err.textContent = ev.error.message;
          });
        } else {
          state.cardElement.clear();
        }
        hide(loading);
        show($("ca-pay-stripe-mode"));
        show($("ca-pay-save-card-row"));
        submit.disabled = false;
        loadSavedCards();
      })
      .catch(function () {
        if (state.payMode === false) return; /* not-set-up message already shown */
        hide(loading);
        err.textContent = "Could not reach the payment service. Please try again.";
        submit.disabled = true;
      });
  }

  function savedCardLabel(c) {
    var brand = c.brand ? String(c.brand).charAt(0).toUpperCase() + String(c.brand).slice(1) : "Card";
    var exp = (c.exp_month && c.exp_year) ? " · Expires " + c.exp_month + "/" + c.exp_year : "";
    return brand + " •••• " + (c.last4 || "••••") + exp;
  }
  /* Which saved card (if any) the customer picked; null = a new card. */
  function selectedSavedCardId() {
    var checked = document.querySelector('input[name="ca-pay-saved-card"]:checked');
    if (!checked || checked.value === "new") return null;
    return checked.value;
  }
  function updatePayMethodVisibility() {
    if (selectedSavedCardId()) {
      hide($("ca-pay-new-card-field"));
      hide($("ca-pay-save-card-row"));
    } else {
      show($("ca-pay-new-card-field"));
      show($("ca-pay-save-card-row"));
    }
  }
  /* Saved cards for this booking's phone, listed ABOVE the Card
     Element. "Use a different card" is the default, so a saved card
     is only ever charged when the customer picks it. Only brand /
     last4 / expiry are ever shown — no full card details exist here. */
  function loadSavedCards() {
    var box = $("ca-pay-saved-cards");
    var list = $("ca-pay-saved-list");
    if (!state.bookingPhone) { hide(box); return; }
    fetch("/api/customers/cards?phone=" + encodeURIComponent(state.bookingPhone))
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (j) {
        var cards = (j && Array.isArray(j.cards)) ? j.cards : [];
        state.savedCards = cards;
        list.innerHTML = "";
        if (!cards.length) { hide(box); return; }
        show(box);
        cards.forEach(function (c) {
          var label = document.createElement("label");
          label.className = "saved-card-option";
          var radio = document.createElement("input");
          radio.type = "radio";
          radio.name = "ca-pay-saved-card";
          radio.value = String(c.id);
          radio.addEventListener("change", updatePayMethodVisibility);
          label.appendChild(radio);
          label.appendChild(document.createTextNode(savedCardLabel(c)));
          var remove = document.createElement("button");
          remove.type = "button";
          remove.className = "remove-saved-card";
          remove.textContent = "Remove";
          remove.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (!window.confirm("Remove this saved card?")) return;
            fetch("/api/customers/cards/" + encodeURIComponent(c.id) + "?phone=" +
                  encodeURIComponent(state.bookingPhone), { method: "DELETE" })
              .then(function (r) {
                return r.json().catch(function () { return {}; }).then(function (jj) { return { ok: r.ok, j: jj }; });
              })
              .then(function (res) {
                if (!res.ok) {
                  $("ca-pay-error").textContent = (res.j && (res.j.error || res.j.message)) || "That card could not be removed.";
                  return;
                }
                loadSavedCards();
              })
              .catch(function () {
                $("ca-pay-error").textContent = "Could not reach the payment service. Please try again.";
              });
          });
          label.appendChild(remove);
          list.appendChild(label);
        });
        var fresh = document.createElement("label");
        fresh.className = "saved-card-option";
        var freshRadio = document.createElement("input");
        freshRadio.type = "radio";
        freshRadio.name = "ca-pay-saved-card";
        freshRadio.value = "new";
        freshRadio.checked = true;
        freshRadio.addEventListener("change", updatePayMethodVisibility);
        fresh.appendChild(freshRadio);
        fresh.appendChild(document.createTextNode("Use a different card"));
        list.appendChild(fresh);
        updatePayMethodVisibility();
      })
      .catch(function () { hide(box); });
  }

  /* One pay attempt against the server. `alreadyConfirmed` stops a
     second needs_action round-trip from looping forever. */
  function handlePayResponse(res, alreadyConfirmed) {
    var btn = $("ca-pay-submit");
    var err = $("ca-pay-error");
    if (res.j && res.j.needs_action && res.j.client_secret && !alreadyConfirmed) {
      if (!res.j.payment_intent_id) {
        btn.disabled = false;
        btn.textContent = "Pay";
        err.textContent = "Payment needs confirmation, but no confirmation was provided. Please try again.";
        return Promise.resolve();
      }
      btn.textContent = "Confirming…";
      return state.stripe.confirmCardPayment(res.j.client_secret)
        .then(function (result) {
          if (result.error) {
            btn.disabled = false;
            btn.textContent = "Pay";
            err.textContent = result.error.message || "Your card could not be confirmed. Please try again.";
            return;
          }
          btn.textContent = "Processing…";
          return fetch("/api/bookings/" + encodeURIComponent(state.bookingId) + "/pay/confirm", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ payment_intent_id: res.j.payment_intent_id })
          })
            .then(function (r) {
              return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; });
            })
            .then(function (res2) { return handlePayResponse(res2, true); })
            .catch(function () {
              btn.disabled = false;
              btn.textContent = "Pay";
              err.textContent = "Could not reach the payment service. Please try again.";
            });
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = "Pay";
          err.textContent = "Could not reach the payment service. Please try again.";
        });
    }
    btn.disabled = false;
    btn.textContent = "Pay";
    if (!res.ok || !res.j || !res.j.payment) {
      /* Decline / Stripe error: the server's message, verbatim. The
         booking stays awaiting_payment and is never sent to drivers. */
      err.textContent = (res.j && (res.j.error || res.j.message)) || "Payment could not be completed. Please try again.";
      return Promise.resolve();
    }
    state.paid = true;
    /* The /pay response carries test_mode:true in test mode (or
       payment.test) — the booked view then says so, never passing
       a faked authorization off as a real charge. */
    state.testModePaid = !!(res.j.test_mode || (res.j.payment && res.j.payment.test));
    hide($("ca-pay-panel"));
    if (res.j.booking && res.j.booking.status) {
      state.booking = Object.assign({}, state.booking, res.j.booking);
    }
    showThankYou(state.booking || {});
    $("screen-rides").scrollTop = 0;
    pollOnce();
    return Promise.resolve();
  }

  function postPay(body) {
    return fetch("/api/bookings/" + encodeURIComponent(state.bookingId) + "/pay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; });
      });
  }

  /* Test mode: the old raw-card submit, exactly as before. Only used
     while the server reports test_mode=true (no Stripe keys
     configured). The server fakes the authorization; the booked view
     says "Test mode — no real charge". */
  function submitTestPayment() {
    var err = $("ca-pay-error");
    var payload = {
      card_number: $("ca-pay-number").value.replace(/[\s-]/g, ""),
      card_exp: $("ca-pay-exp").value.trim(),
      card_cvc: $("ca-pay-cvc").value.trim(),
      card_name: $("ca-pay-name").value.trim()
    };
    if (!payload.card_number || !payload.card_exp || !payload.card_cvc || !payload.card_name) {
      err.textContent = "Please fill in all card fields.";
      return;
    }
    var btn = $("ca-pay-submit");
    btn.disabled = true;
    btn.textContent = "Processing (test mode)…";
    postPay(payload)
      .then(function (res) { return handlePayResponse(res, false); })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "Pay";
        err.textContent = "Could not reach the payment service. Please try again.";
      });
  }

  $("ca-pay-form").addEventListener("submit", function (e) {
    e.preventDefault();
    if (!state.bookingId) return;
    var err = $("ca-pay-error");
    err.textContent = "";
    if (state.payMode === false) {
      show($("ca-pay-unavailable"));
      return;
    }
    if (state.payMode === "test") {
      submitTestPayment();
      return;
    }
    if (state.payMode !== "stripe") {
      err.textContent = "The secure payment form is still loading. Please wait a moment and try again.";
      return;
    }
    if (!state.stripe || !state.cardElement) {
      err.textContent = "The secure payment form is still loading. Please wait a moment and try again.";
      return;
    }
    var btn = $("ca-pay-submit");
    btn.disabled = true;
    btn.textContent = "Processing…";
    var savedId = selectedSavedCardId();
    if (savedId) {
      /* A saved card: only its server-side id is sent — never any
         card details. */
      postPay({ saved_card_id: parseInt(savedId, 10) })
        .then(function (res) { return handlePayResponse(res, false); })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = "Pay";
          err.textContent = "Could not reach the payment service. Please try again.";
        });
      return;
    }
    /* A new card: Stripe.js turns the Card Element into a
       PaymentMethod id in the browser. Only that id (pm_...) is
       sent to the server — never the card number, expiry or CVC. */
    state.stripe.createPaymentMethod({
      type: "card",
      card: state.cardElement,
      billing_details: { name: (state.booking && state.booking.customer_name) || undefined }
    })
      .then(function (result) {
        if (result.error) {
          btn.disabled = false;
          btn.textContent = "Pay";
          err.textContent = result.error.message || "Please check your card details and try again.";
          return;
        }
        return postPay({
          payment_method_id: result.paymentMethod.id,
          save_card: $("ca-pay-save-card").checked
        })
          .then(function (res) { return handlePayResponse(res, false); })
          .catch(function () {
            btn.disabled = false;
            btn.textContent = "Pay";
            err.textContent = "Could not reach the payment service. Please try again.";
          });
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "Pay";
        err.textContent = "Could not reach the payment service. Please try again.";
      });
  });

  /* ---------- Cancel ---------- */
  $("ca-cancel-booking-btn").addEventListener("click", function () {
    if (!state.bookingId) return;
    if (!window.confirm("Cancel this booking? The cancellation rules apply.")) return;
    fetch("/api/bookings/" + encodeURIComponent(state.bookingId) + "/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: state.bookingPhone })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        var line = $("ca-cancel-result");
        show(line);
        if (!res.ok) {
          line.textContent = (res.j && (res.j.error || res.j.message)) || "Cancellation could not be completed.";
          return;
        }
        stopPolling();
        /* The API returns booleans: refund / charge_kept, not amounts. */
        var bits = ["Booking cancelled."];
        if (res.j.refund) bits.push("Your payment will be refunded.");
        if (res.j.charge_kept) bits.push("The full price applies under the cancellation rules.");
        line.textContent = bits.join(" ");
        hide($("ca-status-actions"));
        hide($("ca-pay-panel"));
        hide($("ca-total-box"));
        hide($("ca-thankyou-block"));
        show($("ca-status-finding"));
        $("ca-status-message").textContent = "This booking was cancelled.";
        /* No ride is live any more: the Book tab form is emptied and
           the submit guard no longer blocks a fresh booking. */
        state.bookingId = null;
        state.booking = null;
        state.paid = false;
        clearBookingForm();
      })
      .catch(function () {
        var line = $("ca-cancel-result");
        show(line);
        line.textContent = "Could not reach the booking service. Please try again.";
      });
  });

  /* ---------- Return trip / new booking ---------- */
  $("ca-return-trip-btn").addEventListener("click", function () {
    var b = state.booking;
    if (!b) return;
    stopPolling();
    hide($("ca-status-card"));
    show($("ca-history-block"));
    show($("ca-booking-card"));
    tabs.forEach(function (t) {
      var active = t.getAttribute("data-ride-type") === "one_way";
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    state.rideType = "one_way";
    state.isReturnTrip = true;
    show($("ca-field-dropoff"));
    hide($("ca-field-hours"));
    hide($("ca-field-contact"));
    $("ca-pickup").value = b.dropoff || "";
    $("ca-dropoff").value = b.pickup || "";
    $("ca-date").value = "";
    $("ca-time").value = "";
    $("ca-referral").value = "";
    clearBookingPlaces();
    state.bookingId = null;
    state.booking = null;
    state.paid = false;
    showScreen("book");
    $("ca-date").focus();
  });

  /* ---------- Book another ride: the SEPARATE option ---------- */
  /* The only way back to the booking form once a ride exists (the
     return-trip button is the other, for the ride home). It opens a
     FRESH EMPTY form — the previous ride's values are cleared, so
     tapping "View options" can only ever create a new booking. */
  $("ca-new-booking-btn").addEventListener("click", function () {
    stopPolling();
    hide($("ca-status-card"));
    show($("ca-history-block"));
    state.bookingId = null;
    state.booking = null;
    state.paid = false;
    clearBookingForm();
    show($("ca-booking-card"));
    showScreen("book");
  });

  $("ca-status-back").addEventListener("click", function () {
    stopPolling();
    hide($("ca-status-card"));
    show($("ca-history-block"));
    state.bookingId = null;
    state.booking = null;
    state.paid = false;
    /* The ride stays in history; the Book tab form is emptied so it
       can never be re-submitted with the old ride's values. */
    clearBookingForm();
    if (state.historyPhone) loadHistory(state.historyPhone);
  });

  /* ---------- Live map (Leaflet, with text fallback) ---------- */
  function renderMap(lat, lng, booking) {
    var fallback = $("ca-map-fallback");
    var mapEl = $("ca-map");
    if (typeof window.L === "undefined") {
      mapEl.classList.add("hidden");
      show(fallback);
      fallback.textContent = "Live map is unavailable right now. Your chauffeur is on the way to " +
        (booking.pickup || "your pickup point") + ".";
      return;
    }
    hide(fallback);
    mapEl.classList.remove("hidden");
    if (!state.mapReady) {
      /* USA-only map (owner order 2026-11-21): maxBounds keeps the
         view inside the USA (continental US + Alaska + Hawaii), so
         the user cannot pan away to France or anywhere else abroad.
         The initial view is still the chauffeur's position at
         zoom 14; tiles, markers and behaviour are unchanged. */
      state.map = window.L.map("ca-map", {
        maxBounds: [[18.9, -171.8], [71.4, -66.9]],
        maxBoundsViscosity: 1.0
      }).setView([lat, lng], 14);
      /* CARTO dark basemap (free, no key): a proper CDN, so tiles load
         without the OSM tile server's rate limits, and the dark tiles
         match the site's black-and-gold luxury look. Markers, popups
         and behaviour are unchanged. */
      window.L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 19,
        subdomains: "abcd",
        attribution: "© OpenStreetMap contributors © CARTO"
      }).addTo(state.map);
      state.marker = window.L.marker([lat, lng]).addTo(state.map);
      state.marker.bindPopup("Your chauffeur").openPopup();
      state.mapReady = true;
    } else {
      state.marker.setLatLng([lat, lng]);
      state.map.panTo([lat, lng]);
    }
    setTimeout(function () { if (state.map) state.map.invalidateSize(); }, 150);
  }

  /* ---------- Ride history ---------- */
  function loadHistory(phone) {
    var err = $("ca-history-error");
    var box = $("ca-history-results");
    err.textContent = "";
    box.innerHTML = "";
    if (!phone) { err.textContent = "Please enter your phone number."; return; }
    state.historyPhone = phone;
    box.innerHTML = "<p>Looking up your rides…</p>";
    fetch("/api/bookings?phone=" + encodeURIComponent(phone))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          box.innerHTML = "";
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Could not look up rides for that number.";
          return;
        }
        var list = Array.isArray(res.j) ? res.j : (res.j.bookings || res.j.rides || []);
        if (!list.length) {
          box.innerHTML = "<p>No rides found for that number yet.</p>";
          return;
        }
        box.innerHTML = "";
        list.forEach(function (b) {
          var item = document.createElement("div");
          item.className = "history-item";
          item.innerHTML = '<div class="h-top"><div>' +
            '<div class="h-route">' + esc(rideLabel(b)) + "</div>" +
            '<div class="h-meta">' + esc(whenLabel(b)) +
            " · " + rideTypeLabel(b) + "</div>" +
            '<div><span class="pill">' + esc(statusLabel(b.status)) + "</span></div>" +
            "</div></div>";
          var viewBtn = document.createElement("button");
          viewBtn.type = "button";
          viewBtn.className = "btn-ghost h-view";
          viewBtn.textContent = "View this ride";
          viewBtn.addEventListener("click", function () { openRide(b.id, phone); });
          item.appendChild(viewBtn);
          box.appendChild(item);
        });
      })
      .catch(function () {
        box.innerHTML = "";
        err.textContent = "Could not reach the booking service. Please try again.";
      });
  }

  /* Open one ride from history in the same status view a fresh
     booking uses: full detail + polling while the ride is live. */
  function openRide(bookingId, phone) {
    fetch("/api/bookings/" + encodeURIComponent(bookingId))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok || !res.j.booking) {
          $("ca-history-error").textContent = (res.j && (res.j.error || res.j.message)) || "That ride could not be opened.";
          return;
        }
        startTracking(res.j.booking, phone);
      })
      .catch(function () {
        $("ca-history-error").textContent = "Could not reach the booking service. Please try again.";
      });
  }

  $("ca-history-form").addEventListener("submit", function (e) {
    e.preventDefault();
    loadHistory($("ca-history-phone").value.trim());
  });

  /* ---------- Support chat (scripted answers only) ---------- */
  /* The same scripted support chat as the website's "Chat with us"
     widget, as a full tab: available always, with no booking and no
     trip. Scripted answers only — NOT AI. Typed messages are stored
     via POST /api/support-messages so the owner sees them, exactly
     as on the website. Wording mirrors the website's answers, with
     page references adapted to the app's tabs. */
  var supportMessages = $("ca-support-messages");
  var supportOpened = false;

  function supportAddMsg(who, text) {
    var div = document.createElement("div");
    div.className = "msg " + who;
    div.textContent = text;
    supportMessages.appendChild(div);
    supportMessages.scrollTop = supportMessages.scrollHeight;
  }
  function supportGreet() {
    if (supportOpened) return;
    supportOpened = true;
    supportAddMsg("bot", "Hello, and welcome to Noel Chauffer. How can I help — booking, cancellation, waiting time, or something about a ride?");
  }
  function supportAnswer(text) {
    var t = text.toLowerCase();
    var has = function () {
      for (var i = 0; i < arguments.length; i++) {
        if (t.indexOf(arguments[i]) !== -1) return true;
      }
      return false;
    };
    if (has("paus")) {
      return "No — bookings are open. Enter your pickup and drop-off in the booking form to see your fare.";
    }
    if (has("cancel", "refund")) {
      return "Cancellation is free if you cancel more than 1 hour before pickup. If you cancel 1 hour or less before pickup, the cancellation is not refundable.";
    }
    if (has("wait", "airport", "late", "delay")) {
      return "Waiting is free for 60 minutes at airports and 15 minutes at other pickups. After that, waiting charges apply.";
    }
    if (has("price", "cost", "much", "total", "charge", "pay", "payment")) {
      return "Enter your pickup and drop-off in the Book tab, choose your experience, and you will see the total for each class before you pay.";
    }
    if (has("lost", "left", "forgot", "belonging", "item")) {
      return "I am sorry to hear that. Please report it here as soon as you can, and within 7 days. The driver checks the car after every ride. Unclaimed items go to the police station after one week.";
    }
    if (has("problem", "complaint", "issue", "unhappy", "escalat", "manager", "owner")) {
      return "I am sorry about that. I will escalate this to the owner, who will look into it personally. Please tell me your pickup date and time and what happened.";
    }
    if (has("driver", "chauffeur", "phone", "email", "detail", "contact")) {
      return "As soon as your chauffeur accepts, you will see their name, phone number, car, colour and plate number in the My Rides tab — and the same details are sent to your phone and email.";
    }
    if (has("car", "vehicle", "sedan", "suv", "type", "class")) {
      return "Our rides come in three classes — Business Class, Business SUV and First Class — recent high-end cars, clean, comfortable, and prepared for every ride, with phone chargers on board.";
    }
    if (has("return", "round trip", "back", "come back")) {
      return "For a return journey, simply book a second one-way ride. After you pay for your first ride, the app offers you a return booking with the addresses already swapped for you.";
    }
    if (has("hour", "hourly", "by the hour")) {
      return "Choose the “By the hour” tab in the booking form, pick a vehicle class and how many hours you need (minimum 2 hours). Your chauffeur stays with you for the hours you book, with 25 miles of travel included per hour.";
    }
    if (has("refer", "friend", "code")) {
      return "If a friend referred you, open their referral link — it takes you to the booking form with their code already filled in, and your first booking gets 5% off. After your ride, the Referral tab shows you how to refer a friend too.";
    }
    if (has("book", "reserve", "ride", "pickup", "how")) {
      return "Enter your pickup and drop-off, date and time in the Book tab, choose your experience, and pay by card — your chauffeur is assigned right after payment.";
    }
    if (has("hello", "hi", "hey", "salam")) {
      return "Hello, and welcome to Noel Chauffer. Bookings are open — enter your pickup and drop-off in the booking form to see your fare. I can still help with prices, cancellation, waiting time, lost items, or a problem with a ride.";
    }
    if (has("human", "person", "agent", "support", "help")) {
      return "You are chatting with the Noel Chauffer team here. The team replies within 24 hours. If your matter is urgent, please describe it here and we will escalate it to the owner.";
    }
    return "Happy to help. Bookings are open. I can answer questions about prices, cancellation, waiting time, your chauffeur's details, cars, return trips, by-the-hour rides, or lost items — just ask.";
  }
  function supportHandleQuestion(q) {
    if (!q) return;
    supportAddMsg("user", q);
    setTimeout(function () { supportAddMsg("bot", supportAnswer(q)); }, 350);
  }
  /* Typed messages also reach the owner (owner dashboard, "Support
     messages"), so a problem or lost item is actually seen.
     Fire-and-forget: a failed POST changes nothing in the chat, and
     the scripted answer above is never gated on it. Chip taps are
     FAQ navigation, not messages, so only typed text is reported. */
  function supportReportToOwner(q) {
    if (!q) return;
    fetch("/api/support-messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: q })
    }).catch(function () { /* chat answers work with or without the server */ });
  }

  $("ca-support-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var input = $("ca-support-input");
    var q = input.value.trim();
    input.value = "";
    supportHandleQuestion(q);
    supportReportToOwner(q);
  });
  document.querySelectorAll("#ca-support-chips button").forEach(function (chip) {
    chip.addEventListener("click", function () { supportHandleQuestion(chip.getAttribute("data-q")); });
  });
  /* Greet the first time the Support tab opens. */
  document.querySelector('#ca-tabbar button[data-screen="support"]').addEventListener("click", supportGreet);

  /* ---------- Referral link ---------- */
  /* The shareable link carries the same code the booking form
     accepts: https://noelchauffer.com/app?ref=CODE (built from
     the current origin so it works on every host). Tapping the
     "Refer a Friend" button reveals the link with Copy and native
     Share options; the CUSTOMER shares it himself (WhatsApp,
     message, etc.) — the system sends nothing to friends.
     Clicking the link opens the Book tab with the code prefilled
     — see prefillReferralFromUrl below. Booking-time validation
     is unchanged: an unknown code is rejected exactly as a
     mistyped one. No benefit or amount is stated anywhere — the
     benefit is TBD, as on the website. */
  var THANKYOU_REFERRAL_IDS = {
    reveal: "ca-referral-show-btn", line: "ca-referral-link-line",
    anchor: "ca-referral-link-anchor", actions: "ca-referral-link-actions",
    copy: "ca-referral-copy-btn", share: "ca-referral-share-btn"
  };
  var TAB_REFERRAL_IDS = {
    reveal: "ca-tab-referral-show-btn", line: "ca-tab-referral-link-line",
    anchor: "ca-tab-referral-link-anchor", actions: "ca-tab-referral-link-actions",
    copy: "ca-tab-referral-copy-btn", share: "ca-tab-referral-share-btn"
  };
  function referralLinkFor(code) {
    return window.location.origin + "/app?ref=" + encodeURIComponent(code);
  }
  function copyTextToClipboard(text, btn) {
    var label = btn ? btn.textContent : "";
    function done() {
      if (!btn) return;
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = label; }, 2000);
    }
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (e) { /* clipboard unavailable */ }
      document.body.removeChild(ta);
      done();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, fallback);
    } else {
      fallback();
    }
  }
  function showReferralLink(code, ids) {
    var link = referralLinkFor(code);
    var anchor = $(ids.anchor);
    anchor.href = link;
    anchor.textContent = link;
    var copyBtn = $(ids.copy);
    copyBtn.onclick = function () { copyTextToClipboard(link, copyBtn); };
    var shareBtn = $(ids.share);
    if (navigator.share) {
      show(shareBtn);
      shareBtn.onclick = function () {
        navigator.share({ title: "Noel Chauffer", url: link }).catch(function () {});
      };
    } else {
      hide(shareBtn);
    }
    var revealBtn = $(ids.reveal);
    revealBtn.onclick = function () {
      show($(ids.line));
      show($(ids.actions));
      hide(revealBtn);
    };
    show(revealBtn);
  }
  /* A friend arriving via a referral link lands on the Book tab
     with the code prefilled — no typing needed. No validation
     here: the booking endpoint rejects unknown codes as usual,
     so a bad link can never break the page. */
  (function prefillReferralFromUrl() {
    var ref = (new URLSearchParams(window.location.search).get("ref") || "").trim();
    if (!ref) return;
    var field = $("ca-referral");
    if (field && !field.value) field.value = ref;
    showScreen("book");
  })();

  /* ---------- Referral tab ---------- */
  /* Mirrors the website's referral display exactly: the same
     explainer text, the same "Your referral code:" line. A code is
     issued for every booking, so the latest booking for the phone
     number carries the customer's code. No benefit or amount is
     stated anywhere — the benefit is TBD, as on the website. */
  function showReferralCode(code) {
    if (!code) return;
    hide($("ca-tab-referral-empty"));
    show($("ca-tab-referral-line"));
    $("ca-tab-referral-value").textContent = code;
    showReferralLink(code, TAB_REFERRAL_IDS);
  }
  $("ca-referral-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var phone = $("ca-referral-phone").value.trim();
    var err = $("ca-referral-error");
    err.textContent = "";
    if (!phone) { err.textContent = "Please enter your phone number."; return; }
    fetch("/api/bookings?phone=" + encodeURIComponent(phone))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Could not look up rides for that number.";
          return;
        }
        var list = Array.isArray(res.j) ? res.j : (res.j.bookings || res.j.rides || []);
        if (!list.length || !list[0].id) {
          err.textContent = "No rides found for that number yet.";
          return;
        }
        return fetch("/api/bookings/" + encodeURIComponent(list[0].id))
          .then(function (r) { return r.json(); })
          .then(function (j) {
            var code = j && j.booking && j.booking.referral_code;
            if (code) {
              showReferralCode(code);
            } else {
              err.textContent = "No referral code found yet.";
            }
          });
      })
      .catch(function () {
        err.textContent = "Could not reach the booking service. Please try again.";
      });
  });
})();
