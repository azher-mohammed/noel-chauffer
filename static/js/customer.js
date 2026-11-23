/* Noel Chauffer — customer site logic.
   Talks only to the /api/* contract. Bookings are LIVE (owner decision
   2026-11-20: Blacklane prices + slab driver pay): the booking form
   submits, the options screen shows each class total, and the card
   payment opens from the booking status. Existing rides keep their
   status, chauffeur, chat and map views. */
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
    /* Blacklane-style pickers (owner decision 2026-11-22): the date
       and time the customer picked in the custom calendar / time
       list, in server format (YYYY-MM-DD / HH:MM). The visible
       inputs show "Tue, Nov 24" / "07:10 AM". */
    dateIso: "",
    timeValue: "",
    flightNumber: null,
    flightResolved: false,
    pendingPayload: null,
    selectedClass: "sedan",
    /* Blacklane-style hourly (owner decision 2026-11-20): the class
       the customer picked on the form for a By-the-hour ride. */
    hourlyClass: "sedan",
    classBooking: null,
    classPhone: "",
    /* Compulsory customer sign-in (owner decision 2026-11-22):
       { email, phone } once the customer has signed in with
       email + Continue, else null. */
    customerSignedIn: null,
    lastChatSig: "",
    chatLanguage: "en",
    chatLangInitFor: null,
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
  /* Language switcher (owner decision 2026-11-22): T() translates a
     customer-facing string through /static/js/i18n.js when it is
     loaded, and falls back to the English literal otherwise — so the
     site behaves exactly as before with no dictionary present. */
  function T(key, fallback, vars) {
    try {
      if (window.NoelI18n && window.NoelI18n.t) {
        var out = window.NoelI18n.t(key, vars);
        if (out && out !== key) return out;
      }
    } catch (e) { /* fall through to the English literal */ }
    return fallback;
  }

  /* Language switcher: when the language changes, re-paint every
     JS-driven string (the static HTML is rewritten by i18n.js). */
  document.addEventListener("noel-language-changed", function () {
    try { paintClassDetails(); } catch (e) {}
    try { paintClassBreakdown(); } catch (e) {}
    try { paintHourlyTotals(); } catch (e) {}
    try { paintHourlyClassSelection(); } catch (e) {}
    if (state.booking) { try { renderBooking(state.booking); } catch (e) {} }
    if (state.dateIso) {
      var d = $("bk-date");
      if (d) d.value = fmtDateDisplay(state.dateIso);
    }
    var dp = $("bk-date-picker");
    if (dp && !dp.classList.contains("hidden")) { try { renderDatePicker(); } catch (e) {} }
  });
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
    var h = parseInt($("bk-hours").value, 10);
    if (isNaN(h) || h < 2) h = 2;
    if (h > 24) h = 24;
    ["sedan", "suv", "first"].forEach(function (cls) {
      var el = $("hr-total-" + cls);
      if (el) el.textContent = "$" + (hourlyTotalCents(cls, h) / 100).toFixed(2);
    });
    var note = $("hr-miles-note");
    if (note) note.textContent = T("class.hourly_miles_note", "Includes " + (h * HOURLY_MILES_PER_HOUR) + " miles of travel (" + HOURLY_MILES_PER_HOUR + " miles per hour) — taxes and tolls included.", { miles: h * HOURLY_MILES_PER_HOUR, mph: HOURLY_MILES_PER_HOUR });
    paintHourlyBreakdown();
  }
  /* Hourly price breakdown (owner decision 2026-11-21 ~18:56 EST:
     every ride gets a breakdown, one-way and hourly). The hourly
     rate is all-in — taxes and tolls are inside the per-hour rate —
     so the breakdown is Base fare (hours x rate) + Total. */
  function paintHourlyBreakdown() {
    var box = $("hourly-class-breakdown");
    if (!box) return;
    var h = parseInt($("bk-hours").value, 10);
    if (isNaN(h) || h < 2) h = 2;
    if (h > 24) h = 24;
    var total = hourlyTotalCents(state.hourlyClass, h) / 100;
    box.innerHTML = '<div class="breakdown-row"><span>' + T("class.base_fare", "Base fare") + '</span><span>' + esc(money(total)) + '</span></div>'
      + '<div class="breakdown-row breakdown-total"><span>' + T("class.total", "Total") + '</span><span>' + esc(money(total)) + '</span></div>';
  }
  function paintHourlyClassSelection() {
    ["sedan", "suv", "first"].forEach(function (cls) {
      var opt = $("hr-class-" + cls);
      if (!opt) return;
      var selected = state.hourlyClass === cls;
      opt.classList.toggle("selected", selected);
      opt.setAttribute("aria-checked", selected ? "true" : "false");
    });
    var cont = $("hourly-class-continue");
    if (cont) cont.textContent = T("class.select_class", "Select " + (CLASS_LABELS[state.hourlyClass] || "Business Class"), { label: CLASS_LABELS[state.hourlyClass] || "Business Class" });
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
  function show(el) { if (el) el.classList.remove("hidden"); syncFlowState(); }
  function hide(el) { if (el) el.classList.add("hidden"); syncFlowState(); }
  /* Second-page strip (owner 2026-11-22): once the customer has
     moved past the booking form — flight number, class choice,
     payment or confirmation — NOTHING shows below the booking flow:
     no homepage sections, no footer link columns. Only the
     "powered by" line and the black footer with the address stay.
     The homepage (booking-form state) is untouched — the owner
     decides its fate later. The signal is any post-form step being
     visible; show()/hide() are the single choke point, so every
     transition — back-buttons, cancel, and a reload with a live
     ride — re-syncs it automatically. */
  function syncFlowState() {
    var inFlow = ["flight-step", "hourly-class-step", "class-step",
                  "pay-panel", "thankyou-block", "status-card"].some(function (id) {
      var el = document.getElementById(id);
      return el && !el.classList.contains("hidden");
    });
    document.body.classList.toggle("in-booking-flow", inFlow);
  }
/* ---------- Hamburger menu (Blacklane-style, owner 2026-11-22) ---------- */
  /* Circular three-lines button, narrow width only; opens a
     full-screen dark overlay. Only one accordion section stays open
     at a time. "Sign in" is a plain item; the language is a working
     scroll-down picker (owner decision 2026-11-22) — the button
     shows the current language, the dropdown lists every language
     and filters as you type. */
  (function initMenu() {
    var menuBtn = $("menu-btn");
    var mobileMenu = $("mobile-menu");
    if (!menuBtn || !mobileMenu) return;
    function openMenu() {
      show(mobileMenu);
      document.body.style.overflow = "hidden";
      menuBtn.setAttribute("aria-expanded", "true");
    }
    function closeMenu() {
      hide(mobileMenu);
      document.body.style.overflow = "";
      menuBtn.setAttribute("aria-expanded", "false");
    }
    menuBtn.addEventListener("click", openMenu);
    var closeBtn = $("menu-close");
    if (closeBtn) closeBtn.addEventListener("click", closeMenu);
    mobileMenu.querySelectorAll(".menu-group-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var group = btn.getAttribute("data-menu-group");
        var sub = mobileMenu.querySelector('[data-menu-sub="' + group + '"]');
        var isOpen = sub && !sub.classList.contains("hidden");
        mobileMenu.querySelectorAll(".menu-sub").forEach(function (s) { s.classList.add("hidden"); });
        mobileMenu.querySelectorAll(".menu-group-btn").forEach(function (b) { b.setAttribute("aria-expanded", "false"); });
        if (!isOpen && sub) {
          sub.classList.remove("hidden");
          btn.setAttribute("aria-expanded", "true");
        }
      });
    });
    mobileMenu.querySelectorAll(".menu-sub a, .menu-link[href]").forEach(function (a) {
      a.addEventListener("click", closeMenu);
    });
    /* Language picker (owner decision 2026-11-22): built into the
       menu's language slot by i18n.js. */
    if (window.NoelI18n && window.NoelI18n.buildPicker) {
      var langSlot = $("menu-lang-slot");
      if (langSlot) window.NoelI18n.buildPicker(langSlot);
    }
  })();
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
      return T("form.by_hour", "By the hour") + (b.hours ? " · " + b.hours + T("class.hour_suffix", " hour(s)") : "") +
        T("status.pickup_prefix", " · Pickup: ") + (b.pickup || "");
    }
    return (b.pickup || "") + "  →  " + (b.dropoff || "");
  }
  /* "Return trip" is a second one-way booking made through
     the return-trip button (owner decision 2026-11-20): it
     must display as "Return trip", never "One way". */
  function rideTypeLabel(b) {
    if (!b) return "";
    if (b.ride_type === "hourly") return T("form.by_hour", "By the hour");
    if (b.is_return) return T("status.return_trip_label", "Return trip");
    return T("status.one_way_label", "One way");
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
      awaiting_payment: T("status.awaiting_payment", "Payment needed to confirm your ride"),
      offered: T("status.offered", "Finding your chauffeur…"),
      accepted: T("status.accepted", "Chauffeur confirmed"),
      en_route: T("status.en_route", "Your chauffeur is on the way"),
      arrived: T("status.arrived", "Your chauffeur has arrived"),
      started: T("status.started", "Your ride is under way"),
      on_trip: T("status.on_trip", "Your ride is under way"),
      in_progress: T("status.in_progress", "Your ride is under way"),
      completed: T("status.completed", "Ride completed — thank you"),
      cancelled: T("status.cancelled", "This booking was cancelled"),
      canceled: T("status.cancelled", "This booking was cancelled"),
      no_show: T("status.no_show", "Marked as a no-show")
    };
    return map[status] || String(status || "");
  }

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
        hide($("field-dropoff"));
        show($("field-hours"));
        hide($("hourly-class-step"));
        paintHourlyClassSelection();
        paintHourlyTotals();
        /* Hourly class/rates show ONLY after View options (owner
           decision 2026-11-21), on a separate step — never on the
           first screen. Name/phone/email stay on the booking form:
           one-way rides ask them on the options page instead
           (Blacklane-style). */
        show($("field-contact"));
      } else {
        show($("field-dropoff"));
        hide($("field-hours"));
        hide($("hourly-class-step"));
        hide($("field-contact"));
      }
      updateFlightField();
    });
  });

  /* Hourly class picker (Blacklane-style hourly, owner decision
     2026-11-20): the three class cards on the hourly class step
     (shown only after View options, owner decision 2026-11-21).
     Picking one sets the class sent with the booking; the totals
     on the cards follow the hours input. */
  ["sedan", "suv", "first"].forEach(function (cls) {
    var opt = $("hr-class-" + cls);
    if (opt) opt.addEventListener("click", function () {
      state.hourlyClass = cls;
      paintHourlyClassSelection();
    });
  });
  var hoursInput = $("bk-hours");
  if (hoursInput) hoursInput.addEventListener("input", paintHourlyTotals);

  /* ---------- Blacklane-style date + time pickers ---------- */
  /* Date: a dark November-calendar popup (owner decision 2026-11-22).
     Past dates are dimmed, struck through and unselectable; today is
     the first enabled date; picking a date sets "Tue, Nov 24" (no
     year) and closes the picker. Time: a dropdown list, every 10
     minutes, 12:00 AM–11:50 PM (144 options). The server still
     blocks past dates/times on submit, and the time field is full
     width like the Date field. */
  /* Language switcher: month/day names follow the site language
     (window.NOEL_CAL in i18n.js); English when i18n.js is absent. */
  function monthsFull() { var t = (window.NoelI18n && window.NoelI18n.cal) ? window.NoelI18n.cal("months_full") : null; return t || ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]; }
  function monthsShort() { var t = (window.NoelI18n && window.NoelI18n.cal) ? window.NoelI18n.cal("months_short") : null; return t || ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]; }
  function daysShort() { var t = (window.NoelI18n && window.NoelI18n.cal) ? window.NoelI18n.cal("days_short") : null; return t || ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]; }
  function fmtDateDisplay(iso) {
    var p = iso.split("-");
    var d = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
    return daysShort()[d.getDay()] + ", " + monthsShort()[d.getMonth()] + " " + d.getDate();
  }
  function isoParts(iso) {
    var p = (iso || "").split("-");
    return { y: Number(p[0]), m: Number(p[1]) - 1, d: Number(p[2]) };
  }
  var datePicker = $("bk-date-picker");
  var dateView = null; // {y, m} 0-based month, set on first open
  function renderDatePicker() {
    var today = todayNY();
    var tp = isoParts(today);
    if (!dateView) dateView = { y: tp.y, m: tp.m };
    var first = new Date(dateView.y, dateView.m, 1);
    var daysInMonth = new Date(dateView.y, dateView.m + 1, 0).getDate();
    var prevDisabled = dateView.y === tp.y && dateView.m === tp.m;
    var html = '<div class="dp-head">'
      + '<button type="button" class="dp-nav" id="bk-dp-prev" aria-label="' + T("form.prev_month", "Previous month") + '"' + (prevDisabled ? " disabled" : "") + '>&#8249;</button>'
      + '<span class="dp-title">' + monthsFull()[dateView.m] + " " + dateView.y + '</span>'
      + '<button type="button" class="dp-nav" id="bk-dp-next" aria-label="' + T("form.next_month", "Next month") + '">&#8250;</button></div>';
    html += '<div class="dp-grid">';
    daysShort().map(function (d) { return d.slice(0, 2); }).forEach(function (d) { html += '<span class="dp-dow">' + d + '</span>'; });
    var i;
    for (i = 0; i < first.getDay(); i++) html += '<span class="dp-day empty"></span>';
    for (i = 1; i <= daysInMonth; i++) {
      var iso = dateView.y + "-" + String(dateView.m + 1).padStart(2, "0") + "-" + String(i).padStart(2, "0");
      var cls = "dp-day";
      if (iso < today) cls += " past";
      if (iso === today) cls += " today";
      if (iso === state.dateIso) cls += " selected";
      html += '<button type="button" class="' + cls + '" data-date="' + iso + '"' + (iso < today ? " disabled" : "") + '>' + i + '</button>';
    }
    html += '</div>';
    datePicker.innerHTML = html;
    var prev = $("bk-dp-prev");
    if (prev) prev.addEventListener("click", function (e) {
      e.stopPropagation();
      if (dateView.m === 0) { dateView = { y: dateView.y - 1, m: 11 }; } else { dateView.m -= 1; }
      renderDatePicker();
    });
    var next = $("bk-dp-next");
    if (next) next.addEventListener("click", function (e) {
      e.stopPropagation();
      if (dateView.m === 11) { dateView = { y: dateView.y + 1, m: 0 }; } else { dateView.m += 1; }
      renderDatePicker();
    });
    datePicker.querySelectorAll(".dp-day[data-date]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.dateIso = btn.getAttribute("data-date");
        $("bk-date").value = fmtDateDisplay(state.dateIso);
        closeDatePicker();
      });
    });
  }
  function openDatePicker() { renderDatePicker(); show(datePicker); }
  function closeDatePicker() { hide(datePicker); }
  /* 144 options: every 10 minutes across the full day, 12-hour
     format with zero-padded hours ("07:10 AM"). */
  var TIME_OPTIONS = [];
  (function () {
    var h, m;
    for (h = 0; h < 24; h++) {
      for (m = 0; m < 60; m += 10) {
        var ap = h < 12 ? "AM" : "PM";
        var hh = h % 12; if (hh === 0) hh = 12;
        TIME_OPTIONS.push({
          value: String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0"),
          label: String(hh).padStart(2, "0") + ":" + String(m).padStart(2, "0") + " " + ap
        });
      }
    }
  })();
  var timeList = $("bk-time-list");
  function renderTimeList() {
    timeList.innerHTML = TIME_OPTIONS.map(function (o) {
      return '<li><button type="button" data-time="' + o.value + '"' + (o.value === state.timeValue ? ' class="selected"' : "") + '>' + o.label + '</button></li>';
    }).join("");
    timeList.querySelectorAll("button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.timeValue = btn.getAttribute("data-time");
        $("bk-time").value = btn.textContent;
        closeTimeList();
      });
    });
  }
  function openTimeList() {
    renderTimeList();
    show(timeList);
    var sel = timeList.querySelector("button.selected");
    if (sel) sel.scrollIntoView({ block: "nearest" });
  }
  function closeTimeList() { hide(timeList); }
  $("bk-date").addEventListener("click", function () {
    closeTimeList();
    if (datePicker.classList.contains("hidden")) { openDatePicker(); } else { closeDatePicker(); }
  });
  $("bk-time").addEventListener("click", function () {
    closeDatePicker();
    if (timeList.classList.contains("hidden")) { openTimeList(); } else { closeTimeList(); }
  });
  document.addEventListener("click", function (e) {
    if (datePicker && !datePicker.classList.contains("hidden")
        && !$("bk-date").contains(e.target) && !datePicker.contains(e.target)) closeDatePicker();
    if (timeList && !timeList.classList.contains("hidden")
        && !$("bk-time").contains(e.target) && !timeList.contains(e.target)) closeTimeList();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeDatePicker(); closeTimeList(); }
  });

  /* Flight-number field (Blacklane-style, owner decision 2026-11-22):
     shown between Date and Pickup time when ANY airport (or terminal)
     is picked, pickup or drop-off; hidden again otherwise. */
  function isAirportPlace(p) {
    return !!(p && (p.airport || p.kind === "airport" || p.kind === "terminal"));
  }
  function updateFlightField() {
    var showIt = state.rideType === "hourly"
      ? isAirportPlace(state.pickupPlace)
      : (isAirportPlace(state.pickupPlace) || isAirportPlace(state.dropoffPlace));
    if (showIt) { show($("field-flight")); }
    else { hide($("field-flight")); $("bk-flight").value = ""; }
  }
  /* Red "This field is required" under the field + red underline. */
  function setFieldError(inputId, errorId, on) {
    var input = $(inputId), errorEl = $(errorId);
    if (input) input.classList.toggle("field-invalid", on);
    if (errorEl) errorEl.classList.toggle("hidden", !on);
  }

  /* ---------- USA address search (autocomplete only) ---------- */
  /* Typing in Pickup / Drop-off shows USA-only suggestions below the
     field, including airport terminals (with arrivals/departures
     entries where the map data has them). Picking a suggestion fills
     the field and stores its coordinates, which are sent with the
     booking so the fare is priced for exactly the place picked.
     There is deliberately NO map inside the booking form and NO
     pin-drop. The post-accept live tracking map further down is
     separate and untouched. Suggestions show address text only —
     never any fare. */

  function clearBookingPlaces() {
    state.pickupPlace = null;
    state.dropoffPlace = null;
    state.flightNumber = null;
    state.flightResolved = false;
    state.pendingPayload = null;
  }

  /* A ride is live while a booking is being tracked and its status is
     not a terminal one. While a ride is live the customer sees ONLY
     that ride: the booking form stays hidden, and the form cannot be
     re-submitted into a duplicate booking. */
  var TERMINAL_RIDE_STATUSES = ["cancelled", "canceled", "completed", "no_show"];
  function hasActiveRide() {
    if (!state.bookingId) return false;
    if (!state.booking) return true;
    return TERMINAL_RIDE_STATUSES.indexOf(state.booking.status || "") === -1;
  }

  /* Fresh empty booking form: used whenever the customer starts a NEW
     booking (Book another ride, or after a cancellation) so the
     previous ride's values can never be re-submitted as a duplicate.
     The only pre-filled return is the return-trip button, which sets
     its swapped addresses itself, after this reset. */
  function clearBookingForm() {
    ["bk-name", "bk-phone", "bk-email", "bk-pickup", "bk-dropoff",
     "bk-date", "bk-time", "bk-referral"
    ].forEach(function (id) { var el = $(id); if (el) el.value = ""; });
    $("bk-hours").value = "2";
    state.dateIso = "";
    state.timeValue = "";
    $("bk-flight").value = "";
    setFieldError("bk-pickup", "bk-pickup-error", false);
    setFieldError("bk-dropoff", "bk-dropoff-error", false);
    hide($("field-flight"));
    document.body.classList.remove("class-step-open");
    state.hourlyClass = "sedan";
    paintHourlyClassSelection();
    paintHourlyTotals();
    $("booking-error").textContent = "";
    var btn = $("book-submit");
    btn.disabled = false;
    btn.textContent = T("form.view_options", "View options");
    tabs.forEach(function (t) {
      var active = t.getAttribute("data-ride-type") === "one_way";
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    state.rideType = "one_way";
    state.isReturnTrip = false;
    show($("field-dropoff"));
    hide($("field-hours"));
    hide($("hourly-class-step"));
    hide($("field-contact"));
    clearBookingPlaces();
  }

  /* Suggestion bias (owner 2026-11-22): nearest-first from the
     customer's location when the browser shares it; the server
     defaults to New York City when it does not. Asked once, on
     first focus of an address field — denied/unavailable falls back
     silently to the NYC default, never asked again. */
  var userLocation = null;
  var locationTried = false;
  function requestUserLocation() {
    if (locationTried || !navigator.geolocation) return;
    locationTried = true;
    try {
      navigator.geolocation.getCurrentPosition(function (pos) {
        if (pos && pos.coords) {
          userLocation = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        }
      }, function () { /* denied/unavailable: server defaults to NYC */ },
      { timeout: 5000, maximumAge: 600000 });
    } catch (e) { /* geolocation unavailable */ }
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
      updateFlightField();
      setFieldError(input.id, input.id === "bk-pickup" ? "bk-pickup-error" : "bk-dropoff-error", false);
    }
    function choose(item) {
      input.value = item.display_name;
      if (kind === "pickup") { state.pickupPlace = item; } else { state.dropoffPlace = item; }
      setFieldError(input.id, input.id === "bk-pickup" ? "bk-pickup-error" : "bk-dropoff-error", false);
      updateFlightField();
      closeList();
    }
    /* Suggestion type icon (Blacklane look): plane for airports and
       terminals, hotel for hotels, pin for plain addresses. */
    function placeIcon(item) {
      var k = item.kind || (item.airport ? "airport" : "address");
      if (k === "airport" || k === "terminal") {
        return '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/></svg>';
      }
      if (k === "hotel") {
        return '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M7 13c1.66 0 3-1.34 3-3S8.66 7 7 7s-3 1.34-3 3 1.34 3 3 3zm12-6h-8v7H3V5H1v15h2v-3h18v3h2v-9c0-2.21-1.79-4-4-4z"/></svg>';
      }
      return '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3z"/></svg>';
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
        /* Blacklane look: the FULL address as the bold main line and
           the same text smaller/grey beneath it, with a type icon on
           the left. Suggestions still come from Photon/Nominatim
           (owner dropped Google Places 2026-11-22) — no "powered by
           Google" line anywhere. */
        var li = document.createElement("li");
        var btn = document.createElement("button");
        btn.type = "button";
        btn.setAttribute("role", "option");
        btn.setAttribute("aria-selected", "false");
        btn.id = listId + "-opt-" + idx;
        var icon = document.createElement("span");
        icon.className = "places-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.innerHTML = placeIcon(item);
        btn.appendChild(icon);
        var textWrap = document.createElement("span");
        textWrap.className = "places-text";
        var mainEl = document.createElement("span");
        mainEl.className = "places-main";
        mainEl.textContent = item.display_name;
        textWrap.appendChild(mainEl);
        var detEl = document.createElement("span");
        detEl.className = "places-detail";
        detEl.textContent = item.display_name;
        textWrap.appendChild(detEl);
        btn.appendChild(textWrap);
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
      var url = "/api/places/search?q=" + encodeURIComponent(query) + "&limit=5";
      if (userLocation) {
        url += "&lat=" + userLocation.lat + "&lon=" + userLocation.lon;
      }
      fetch(url, { signal: controller.signal })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (mySeq !== seq) return;
          render((j && Array.isArray(j.results)) ? j.results : []);
        })
        .catch(function () {
          if (mySeq === seq) closeList();
        });
    }

    input.addEventListener("focus", requestUserLocation);
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

  attachPlaces("bk-pickup", "bk-pickup-list", "pickup");
  attachPlaces("bk-dropoff", "bk-dropoff-list", "dropoff");

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

  /* ---------- Create a booking ---------- */
  $("booking-form").addEventListener("submit", function (e) {
    e.preventDefault();
    /* While a ride is live the form is hidden; this guard stops any
       re-submit of the same ride (double tap, restored page) from
       creating a duplicate booking. A fresh booking first clears the
       ride state — see Book another ride / return trip / cancel. */
    if (hasActiveRide()) return;
    var err = $("booking-error");
    err.textContent = "";
    /* Bookings are PAUSED while prices are being updated (owner
       decision 2026-11-20): nothing is submitted. */
    if (BOOKINGS_PAUSED) {
      err.textContent = T("form.paused_msg", "Bookings are paused while we update our prices. Please check back soon.");
      return;
    }
    var payload = {
      pickup: $("bk-pickup").value.trim(),
      date: state.dateIso,
      time: state.timeValue,
      ride_type: state.rideType
    };
    /* Name, phone and email are asked on the options page for
       one-way rides (Blacklane-style). Hourly rides ask them on the
       form, and pick their class on the separate class step. */
    if (state.rideType === "hourly") {
      payload.customer_name = $("bk-name").value.trim();
      payload.phone = $("bk-phone").value.trim();
      payload.email = $("bk-email").value.trim();
    }
    if (state.rideType === "one_way") {
      payload.dropoff = $("bk-dropoff").value.trim();
      if (state.isReturnTrip) payload.is_return = true;
      var ref = $("bk-referral").value.trim();
      if (ref) payload.referral_code = ref;
    } else {
      /* Blacklane-style hourly (owner decision 2026-11-20): 2 to 24
         hours. The class is picked on the separate class step after
         View options (owner decision 2026-11-21), not here. */
      var h = parseInt($("bk-hours").value, 10);
      if (isNaN(h) || h < 2 || h > 24) {
        err.textContent = T("form.hourly_hours_error", "Hourly bookings need 2 to 24 hours.");
        return;
      }
      payload.hours = h;
    }
    /* When the customer picked a suggestion, send its coordinates so
       the fare is priced for exactly the place picked — the server
       never has to re-resolve the address text. Typed text without
       a pick is rejected above (a suggestion must be picked), and
       editing a field clears the stored pick (see clearStored). */
    if (state.pickupPlace && isFinite(state.pickupPlace.lat) && isFinite(state.pickupPlace.lon)) {
      payload.pickup_lat = state.pickupPlace.lat;
      payload.pickup_lng = state.pickupPlace.lon;
    }
    if (state.rideType === "one_way" && state.dropoffPlace && isFinite(state.dropoffPlace.lat) && isFinite(state.dropoffPlace.lon)) {
      payload.dropoff_lat = state.dropoffPlace.lat;
      payload.dropoff_lng = state.dropoffPlace.lon;
    }
    /* Flight number from the in-form field (Blacklane-style, owner
       order 2026-11-22): the field only shows for airport picks, so
       it is sent only when filled in. */
    var flightInput = $("bk-flight");
    if (flightInput && flightInput.value.trim()) payload.flight_number = flightInput.value.trim();
    /* A suggestion must be picked, not just typed (owner decision
       2026-11-22, Blacklane-style): typed-but-unselected text does
       not count — View options stops with a red "This field is
       required" under the field and a red underline on it. */
    var pickupPicked = !!state.pickupPlace;
    var dropoffPicked = state.rideType !== "one_way" || !!state.dropoffPlace;
    setFieldError("bk-pickup", "bk-pickup-error", !pickupPicked);
    setFieldError("bk-dropoff", "bk-dropoff-error", state.rideType === "one_way" && !dropoffPicked);
    if (!pickupPicked) { $("bk-pickup").focus(); return; }
    if (!dropoffPicked) { $("bk-dropoff").focus(); return; }
    if (!payload.date || !payload.time) {
      err.textContent = T("form.choose_date_time", "Please choose a date and time.");
      return;
    }
    /* Past dates and times cannot be booked (owner decision
       2026-11-20): an old date — or today at a time already gone —
       is refused here, before anything is sent. */
    var today = todayNY();
    if (payload.date < today) {
      err.textContent = T("form.past_date", "Please choose a date from today onwards. Past dates cannot be booked.");
      return;
    }
    if (payload.date === today && payload.time <= nowTimeNY()) {
      err.textContent = T("form.past_time", "Please choose a time later than now. Past times cannot be booked.");
      return;
    }
    if (state.rideType === "hourly" && (!payload.customer_name || !payload.phone || !payload.email)) {
      err.textContent = T("class.fill_details", "Please fill in your name, phone and email.");
      return;
    }
    /* Flight number: BACK in the booking form by owner order
       2026-11-22 (Blacklane-style, in-form field between Date and
       Pickup time, airport picks only). The separate step code below
       (showFlightStep and friends) stays in place, unused; the
       server still accepts flight_number. */
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
      $("flight-step-title").textContent = T("form.flight_title", "Add your flight number");
      $("flight-step-text").textContent = T("form.flight_text_pickup", "Your chauffeur will meet you at the right terminal.");
    } else {
      $("flight-step-title").textContent = T("form.flight_title_optional", "Add your flight number (optional)");
      $("flight-step-text").textContent = T("form.flight_text_dropoff", "This helps your chauffeur take you to the right departure terminal.");
    }
    $("flight-step-airport").textContent = sides.pickup ? payload.pickup : (payload.dropoff || "");
    $("flight-number").value = state.flightNumber || "";
    hide($("booking-card"));
    show($("flight-step"));
    $("flight-step").scrollIntoView({ behavior: "smooth", block: "start" });
    $("flight-number").focus();
  }

  function proceedFromFlightStep() {
    hide($("flight-step"));
    show($("booking-card"));
    var payload = state.pendingPayload;
    state.pendingPayload = null;
    if (!payload) return;
    if (state.flightNumber) payload.flight_number = state.flightNumber;
    sendBooking(payload);
  }

  $("flight-continue").addEventListener("click", function () {
    state.flightNumber = $("flight-number").value.trim() || null;
    state.flightResolved = true;
    proceedFromFlightStep();
  });
  $("flight-skip").addEventListener("click", function () {
    state.flightNumber = null;
    state.flightResolved = true;
    proceedFromFlightStep();
  });
  $("flight-back").addEventListener("click", function () {
    hide($("flight-step"));
    show($("booking-card"));
    $("booking-card").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  /* Hourly class step (owner decision 2026-11-21): the class, the
     per-class rates and the miles note show ONLY after View options.
     The booking does not exist yet — the class is picked here, then
     the booking is created with it. Back returns to the form with
     its values kept; nothing was created, so nothing is cancelled. */
  function showHourlyClassStep(payload) {
    state.pendingPayload = payload;
    $("hourly-class-trip-summary").textContent =
      T("form.by_hour", "By the hour") + " · " + payload.hours + T("class.hour_suffix", " hour(s)") + T("status.pickup_prefix", " · Pickup: ") + payload.pickup;
    $("hourly-class-error").textContent = "";
    paintHourlyTotals();
    paintHourlyClassSelection();
    hide($("booking-card"));
    /* No footer on the booking (class) page. */
    document.body.classList.add("class-step-open");
    show($("hourly-class-step"));
    $("hourly-class-step").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  $("hourly-class-continue").addEventListener("click", function () {
    var payload = state.pendingPayload;
    if (!payload) return;
    payload.vehicle_class = state.hourlyClass;
    state.pendingPayload = null;
    sendBooking(payload);
  });
  $("hourly-class-back").addEventListener("click", function () {
    state.pendingPayload = null;
    hide($("hourly-class-step"));
    document.body.classList.remove("class-step-open");
    show($("booking-card"));
    $("booking-card").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  /* Choose your experience: a SEPARATE options page after the booking
     form. The booking already exists, unpaid;
     the customer picks a class — each option shows its total —
     and then continues to the card payment. Sedan (Business Class)
     is pre-selected. Back cancels the unpaid booking and returns
     to the form to edit. */
  function paintClassSelection() {
    ["sedan", "suv", "first"].forEach(function (cls) {
      var opt = $("class-option-" + cls);
      var selected = state.selectedClass === cls;
      opt.classList.toggle("selected", selected);
      opt.setAttribute("aria-checked", selected ? "true" : "false");
    });
    paintClassBreakdown();
    paintClassDetails();
  }

  /* Blacklane-style class details (owner decision 2026-11-22):
     "Explore <Class> details" line, 5-slide highlights carousel
     (first slide: the class photo + "Clean, quiet, and
     executive-level comfort."; the rest are Noel's own short
     lines) and Capacity tabs. No pricing
     changed here — the breakdown values are the existing ones. */
  var CLASS_PHOTOS = { sedan: "/static/img/car-business.jpg", suv: "/static/img/car-suv.jpg", first: "/static/img/car-first.jpg" };
  var CLASS_CAPACITY = { sedan: { bags: 2, seats: 3 }, suv: { bags: 5, seats: 5 }, first: { bags: 2, seats: 3 } };
  var HIGHLIGHTS = [
    { photo: true, caption: "Clean, quiet, and executive-level comfort." },
    { title: "Professional chauffeurs", text: "Polite, experienced chauffeurs who know the roads and respect your time." },
    { title: "On-time pickups", text: "Your chauffeur plans the route and arrives on time, every time." },
    { title: "Recent high-end cars", text: "Clean, comfortable, recent cars, ready for every ride." },
    { title: "Arrive fully charged", text: "Phone chargers in every car, so your phone is full when you arrive." }
  ];
  var hlIndex = 0;
  function paintClassDetails() {
    var label = CLASS_LABELS[state.selectedClass] || "Business Class";
    var explore = $("class-explore");
    if (explore) explore.textContent = T("class.explore_class", "Explore " + label + " details", { label: label });
    var cap = CLASS_CAPACITY[state.selectedClass] || CLASS_CAPACITY.sedan;
    var bags = $("class-cap-luggage-count");
    if (bags) bags.textContent = T("class.carry_on", cap.bags + " x Carry-on", { n: cap.bags });
    var seats = $("class-cap-seating-count");
    if (seats) seats.textContent = T("class.passengers_count", cap.seats + " passengers", { n: cap.seats });
    var track = $("class-highlights-track");
    if (track) {
      var photo = CLASS_PHOTOS[state.selectedClass] || CLASS_PHOTOS.sedan;
      track.innerHTML = HIGHLIGHTS.map(function (h, i) {
        if (h.photo) {
          return '<div class="hl-slide"><figure><img src="' + esc(photo) + '" alt="' + esc(label) + ' car"><figcaption>' + esc(T("class.hl" + i + "_caption", h.caption)) + '</figcaption></figure></div>';
        }
        return '<div class="hl-slide"><div class="hl-slide-text"><h4>' + esc(T("class.hl" + i + "_title", h.title)) + '</h4><p>' + esc(T("class.hl" + i + "_text", h.text)) + '</p></div></div>';
      }).join("");
      track.style.transform = "translateX(-" + (hlIndex * 100) + "%)";
      /* Size the track to the active slide (owner 2026-11-23): the
         track mixes tall photo slides with short text slides; a
         flex track stays as tall as the tallest slide, so a text
         slide left a big dead gap above the dots. */
      var activeSlide = track.children[hlIndex];
      if (activeSlide) track.style.height = activeSlide.offsetHeight + "px";
    }
    var dots = $("class-hl-dots");
    if (dots) {
      dots.innerHTML = HIGHLIGHTS.map(function (h, i) {
        return '<button type="button" class="hl-dot' + (i === hlIndex ? " active" : "") + '" data-hl="' + i + '" role="tab" aria-label="' + T("class.highlight_n", "Highlight " + (i + 1), { n: i + 1 }) + '"></button>';
      }).join("");
      dots.querySelectorAll(".hl-dot").forEach(function (d) {
        d.addEventListener("click", function () {
          hlIndex = Number(d.getAttribute("data-hl"));
          paintClassDetails();
        });
      });
    }
  }
  var hlPrev = $("class-hl-prev");
  if (hlPrev) hlPrev.addEventListener("click", function () {
    hlIndex = (hlIndex + HIGHLIGHTS.length - 1) % HIGHLIGHTS.length;
    paintClassDetails();
  });
  var hlNext = $("class-hl-next");
  if (hlNext) hlNext.addEventListener("click", function () {
    hlIndex = (hlIndex + 1) % HIGHLIGHTS.length;
    paintClassDetails();
  });
  /* Keep the track sized to the active slide when the viewport
     changes (text reflows, slide heights change). */
  window.addEventListener("resize", function () {
    var tr = $("class-highlights-track");
    if (tr && tr.children[hlIndex]) tr.style.height = tr.children[hlIndex].offsetHeight + "px";
  });
  document.querySelectorAll("#class-step .cap-tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      var which = tab.getAttribute("data-cap-tab");
      document.querySelectorAll("#class-step .cap-tab").forEach(function (t) {
        var active = t === tab;
        t.classList.toggle("active", active);
        t.setAttribute("aria-selected", active ? "true" : "false");
      });
      var luggage = $("class-cap-luggage"), seating = $("class-cap-seating");
      if (luggage) luggage.classList.toggle("hidden", which !== "luggage");
      if (seating) seating.classList.toggle("hidden", which !== "seating");
    });
  });

  /* Price breakdown for the selected class (Blacklane-style): the
     fare composition the customer pays, in the owner's line order
     (2026-11-21 ~18:56 EST) — Base fare, Airport access fee (only
     on airport rides), Black car fee, Sales tax, Congestion (NY
     State + MTA), Toll (only when the route has one), then Total.
     Only lines above $0 are shown; the total always matches the
     class option's total. No refund line in the breakdown. */
  function paintClassBreakdown() {
    var box = $("class-breakdown");
    if (!box) return;
    var b = (state.classBreakdowns || {})[state.selectedClass];
    if (!b) { box.innerHTML = ""; return; }
    var rows = [[T("class.base_fare", "Base fare"), money(b.base)]];
    if (Number(b.airport_access) > 0) rows.push([T("class.airport_fee", "Airport access fee"), money(b.airport_access)]);
    if (Number(b.black_car_fee) > 0) rows.push([T("class.black_car_fee", "Black car fee"), money(b.black_car_fee)]);
    if (Number(b.sales_tax) > 0) rows.push([T("class.sales_tax", "Sales tax"), money(b.sales_tax)]);
    if (Number(b.ny_congestion) > 0) rows.push([T("class.ny_congestion", "NY State congestion surcharge"), money(b.ny_congestion)]);
    if (Number(b.mta_congestion) > 0) rows.push([T("class.mta_congestion", "MTA congestion surcharge"), money(b.mta_congestion)]);
    if (Number(b.toll) > 0) rows.push([T("class.toll", "Toll"), money(b.toll)]);
    if (Number(b.referral_discount) > 0) rows.push([T("class.referral_discount_row", "Referral discount"), "−" + money(b.referral_discount)]);
    var html = rows.map(function (r) {
      return '<div class="breakdown-row"><span>' + esc(r[0]) + '</span><span>' + esc(r[1]) + '</span></div>';
    }).join("");
    html += '<div class="breakdown-row breakdown-total"><span>' + T("class.total", "Total") + '</span><span>' + esc(money(b.total)) + '</span></div>';
    box.innerHTML = html;
  }

  function showClassStep(booking, phone) {
    state.classBooking = booking;
    state.classPhone = phone;
    state.selectedClass = booking.vehicle_class || "sedan";
    $("class-trip-summary").textContent = summaryText(booking);
    /* First Class is offered only when the booking's class totals
       include it (Blacklane mode — the legacy engine has no First
       Class rate, so the option stays hidden there). */
    var firstAvailable = !!(booking.class_totals && booking.class_totals.first != null);
    if (!firstAvailable && state.selectedClass === "first") state.selectedClass = "sedan";
    if (firstAvailable) { show($("class-option-first")); } else { hide($("class-option-first")); }
    /* Each option shows its total (Blacklane mode, owner decision
       2026-11-20): the total the customer will pay, with the 5%
       first-ride referral discount already applied when granted. */
    var totals = booking.class_totals || {};
    $("class-total-sedan").textContent = totals.sedan != null ? money(totals.sedan) : "";
    $("class-total-suv").textContent = totals.suv != null ? money(totals.suv) : "";
    $("class-total-first").textContent = totals.first != null ? money(totals.first) : "";
    /* Per-class fare breakdowns for the options page (Blacklane
       mode only; legacy bookings carry none). */
    state.classBreakdowns = booking.class_breakdowns || {};
    /* 5% first-ride referral discount (owner decision 2026-11-18):
       the note shows only when this booking actually got the
       discount. */
    if (booking.referral_discount && Number(booking.referral_discount) > 0) {
      show($("class-discount-note"));
    } else {
      hide($("class-discount-note"));
    }
    /* Contact is asked here (Blacklane-style): start empty — the
       booking was created without it. */
    $("class-name").value = "";
    $("class-phone").value = "";
    $("class-email").value = "";
    $("class-error").textContent = "";
    /* Compulsory sign-in (owner 2026-11-22): pre-fill the email and
       phone from the signed-in session when there is one, else show
       the sign-in button. */
    refreshCustomerSignin();
    paintClassSelection();
    hide($("booking-card"));
    /* No footer on the booking (class) page. */
    document.body.classList.add("class-step-open");
    show($("class-step"));
    $("class-step").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  ["sedan", "suv", "first"].forEach(function (cls) {
    $("class-option-" + cls).addEventListener("click", function () {
      state.selectedClass = cls;
      paintClassSelection();
    });
  });

  /* ---------- Customer sign-in + Continue (owner 2026-11-22) ----------
     Email only — no password, no Google/Apple/Facebook. NO CODES
     (owner correction 2026-11-22). ONE Continue button below the
     email field does both jobs: it signs the customer in with the
     email + phone above, then saves the contact and continues to
     payment with the selected class. No sign-in lines are shown on
     the page (owner 2026-11-22): no separate sign-in lines and no
     sticky Select bar below. Signed-in customers stay signed
     in (server session) for later bookings, and the email/phone
     pre-fill from it. */
  function refreshCustomerSignin() {
    return fetch("/api/customers/me")
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j && j.signed_in) {
          state.customerSignedIn = { email: j.email, phone: j.phone };
          if (j.email) $("class-email").value = j.email;
          if (j.phone) $("class-phone").value = j.phone;
        } else {
          state.customerSignedIn = null;
        }
        $("class-signin-error").textContent = "";
      })
      .catch(function () {
        state.customerSignedIn = null;
      });
  }
  $("class-signin-continue").addEventListener("click", function () {
    var booking = state.classBooking;
    if (!booking) return;
    var err = $("class-signin-error");
    err.textContent = "";
    var btn = $("class-signin-continue");
    /* Contact (Blacklane-style): name, phone and email are asked on
       this page, after the class is picked. They are saved first —
       the invoice and driver messages need them, and saving the
       phone decides the referral discount — then the class change
       (if any) and payment follow. */
    var contactName = $("class-name").value.trim();
    var contactPhone = $("class-phone").value.trim();
    var contactEmail = $("class-email").value.trim();
    if (!contactName || !contactPhone || !contactEmail || contactEmail.indexOf("@") === -1) {
      err.textContent = T("class.fill_details", "Please fill in your name, phone and email.");
      return;
    }
    function proceedWith(updated) {
      hide($("class-step"));
      document.body.classList.remove("class-step-open");
      /* The booking form stays hidden once the ride exists: the
         customer sees only the ride from here on. A new booking
         comes from the separate "Book another ride" button. */
      hide($("booking-card"));
      state.classBooking = null;
      startTracking(updated, state.classPhone);
    }
    function saveContact(next) {
      fetch("/api/bookings/" + encodeURIComponent(booking.id) + "/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_name: contactName, phone: contactPhone, email: contactEmail })
      })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, j: j }; }); })
        .then(function (res) {
          if (!res.ok || !res.j.booking) {
            btn.disabled = false;
            if (res.status === 401) {
              /* Sign-in expired or changed since the page loaded —
                 the gate is server-side, so tap Continue again. */
              state.customerSignedIn = null;
              err.textContent = T("class.signin_expired", "Your sign-in expired — please tap Continue again.");
              return;
            }
            err.textContent = (res.j && (res.j.error || res.j.message)) || T("class.details_save_failed", "Your details could not be saved. Please try again.");
            return;
          }
          state.classPhone = contactPhone;
          next(res.j.booking);
        })
        .catch(function () {
          btn.disabled = false;
          err.textContent = T("status.reach_booking", "Could not reach the booking service. Please try again.");
        });
    }
    function continueToPayment() {
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
              err.textContent = (res.j && (res.j.error || res.j.message)) || T("class.select_failed", "That class could not be selected. Please try again.");
              return;
            }
            proceedWith(res.j.booking);
          })
          .catch(function () {
            btn.disabled = false;
            err.textContent = T("status.reach_booking", "Could not reach the booking service. Please try again.");
          });
      });
    }
    /* One tap signs in AND continues (owner 2026-11-22): the sign-in
       is just the email + phone above — no code, no password — and
       signing in again with the same (or a changed) email simply
       replaces the session, so the server-side gate on /contact
       always sees the email the customer just typed. */
    btn.disabled = true;
    fetch("/api/customers/signin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: contactEmail, phone: contactPhone })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          btn.disabled = false;
          err.textContent = (res.j && (res.j.error || res.j.message)) || T("class.signin_failed", "Sign-in did not work. Please try again.");
          return;
        }
        state.customerSignedIn = { email: res.j.email || contactEmail, phone: res.j.phone || contactPhone };
        continueToPayment();
      })
      .catch(function () {
        btn.disabled = false;
        err.textContent = T("status.reach_booking", "Could not reach the booking service. Please try again.");
      });
  });

  $("class-back").addEventListener("click", function () {
    var booking = state.classBooking;
    var phone = state.classPhone;
    state.classBooking = null;
    state.classPhone = "";
    hide($("class-step"));
    document.body.classList.remove("class-step-open");
    show($("booking-card"));
    $("booking-card").scrollIntoView({ behavior: "smooth", block: "start" });
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
    var err = $("booking-error");
    var btn = $("book-submit");
    btn.disabled = true;
    btn.textContent = T("form.sending", "Sending your request…");
    fetch("/api/bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        btn.textContent = T("form.view_options", "View options");
        if (!res.ok || !res.j.booking || !res.j.booking.id) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || T("form.something_wrong", "Something went wrong. Please try again.");
          /* The error lives on the booking form: if the customer
             came from the hourly class step, bring the form back so
             the error is visible. (One-way failures already show
             the form, so this is a no-op there.) */
          hide($("hourly-class-step"));
          show($("booking-card"));
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
        btn.textContent = T("form.view_options", "View options");
        err.textContent = T("status.reach_payment_check", "Could not reach the booking service. Please check your connection and try again.");
        hide($("hourly-class-step"));
        show($("booking-card"));
      });
  }

  function startTracking(booking, phone) {
    stopPolling();
    document.body.classList.remove("class-step-open");
    state.bookingId = booking.id;
    state.bookingPhone = phone;
    state.booking = booking;
    state.paid = false;
    state.testModePaid = false;
    state.payInitForBooking = null;
    state.flightNumber = null;
    state.flightResolved = false;
    state.pendingPayload = null;
    /* The booking form stays hidden while the ride is live: the
       customer sees only this ride (status, chauffeur, chat, map)
       until it ends or they pick "Book another ride". */
    hide($("booking-card"));
    hide($("hourly-class-step"));
    hide($("thankyou-block"));
    hide($("invoice-panel"));
    hide($("pay-panel"));
    hide($("driver-block"));
    hide($("chat-panel"));
    hide($("total-box"));
    hide($("map-wrap"));
    hide($("cancel-result"));
    $("status-flight").textContent = "";
    hide($("status-flight"));
    show($("status-finding"));
    show($("status-actions"));
    show($("status-card"));
    $("status-summary").textContent = summaryText(booking);
    $("status-card").scrollIntoView({ behavior: "smooth", block: "start" });
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
    $("status-summary").textContent = summaryText(b);
    var flightEl = $("status-flight");
    if (b.flight_number) {
      var flightText = T("status.flight_prefix", "Flight: ") + b.flight_number;
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
      hide($("status-finding"));
      show($("driver-block"));
      $("driver-name").textContent = b.driver.name || "";
      var carBits = [];
      if (b.driver.car_year) carBits.push(b.driver.car_year);
      if (b.driver.car_model) carBits.push(b.driver.car_model);
      if (b.driver.car_colour) carBits.push(b.driver.car_colour);
      $("driver-car").textContent = carBits.join(" · ");
      $("driver-plate").textContent = b.driver.plate || "";
      var ph = $("driver-phone");
      ph.textContent = b.driver.phone || "";
      ph.href = b.driver.phone ? "tel:" + b.driver.phone.replace(/[^+0-9]/g, "") : "";
      var img = $("driver-photo");
      var src = b.driver.photo_url || ("/api/bookings/" + encodeURIComponent(b.id) + "/driver-photo");
      if (img.getAttribute("src") !== src) img.setAttribute("src", src);
      img.onerror = function () { img.style.visibility = "hidden"; };
      img.onload = function () { img.style.visibility = "visible"; };
      $("driver-status-line").textContent = statusLabel(st);
    } else {
      show($("status-finding"));
      hide($("driver-block"));
      if (st === "awaiting_payment") {
        $("status-heading").textContent = T("status.total_ready", "Your total is ready");
        $("status-message").textContent = T("status.pay_below", "Please pay by card below — your chauffeur will be assigned right after payment.");
      } else {
        $("status-heading").textContent = T("status.finding", "Finding your chauffeur…");
        $("status-message").textContent = statusLabel(st) || T("status.request_with_us", "Your request is with us. Please keep this page open.");
      }
    }

    /* The single total: shown from the moment the booking exists. The
       card payment box opens with it; only after payment is the
       booking sent to drivers, so no payment step exists later. */
    if (b.total !== null && b.total !== undefined) {
      show($("total-box"));
      $("total-amount").textContent = money(b.total);
      $("pay-amount-label").textContent = money(b.total);
    } else {
      hide($("total-box"));
    }
    if (st === "awaiting_payment") {
      hide($("pay-open-btn"));
      show($("pay-panel"));
      initPayment();
    } else {
      hide($("pay-panel"));
      hide($("pay-open-btn"));
    }

    /* Live map: ONLY when the API says tracking is visible. */
    var tr = b.tracking || {};
    if (tr.visible && tr.lat !== null && tr.lat !== undefined && tr.lng !== null && tr.lng !== undefined) {
      show($("map-wrap"));
      renderMap(Number(tr.lat), Number(tr.lng), b);
    } else {
      hide($("map-wrap"));
    }

    /* Thank-you once the ride is paid for (payment confirms the
       booking; the chauffeur is assigned after payment). */
    if (state.paid || st === "offered" || st === "accepted" || st === "en_route" || st === "arrived" || st === "started" || st === "on_trip" || st === "in_progress" || st === "completed") {
      showThankYou(b);
    }
    if (b.invoice) {
      show($("invoice-panel"));
      var invTotal = (b.invoice.total !== null && b.invoice.total !== undefined) ? b.invoice.total : b.total;
      $("invoice-total").textContent = money(invTotal);
      if (b.invoice.waiting_charge) {
        show($("invoice-waiting-row"));
        $("invoice-waiting").textContent = money(b.invoice.waiting_charge);
      } else {
        hide($("invoice-waiting-row"));
      }
      if (b.invoice.extra_distance_charge) {
        show($("invoice-extra-row"));
        $("invoice-extra").textContent = money(b.invoice.extra_distance_charge);
      } else {
        hide($("invoice-extra-row"));
      }
      $("invoice-grand").textContent = money(invTotal);
    }

    if (st === "cancelled" || st === "canceled") {
      hide($("status-actions"));
      hide($("pay-panel"));
      hide($("pay-open-btn"));
      hide($("total-box"));
      $("status-heading").textContent = T("status.booking_cancelled", "Booking cancelled");
      $("status-message").textContent = T("status.cancelled", "This booking was cancelled.");
      show($("status-finding"));
    }
    if (st === "completed") {
      hide($("status-actions"));
      hide($("pay-panel"));
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
     never translate. Same codes/labels as the driver picker and
     translation.CHAT_LANGUAGES — keep all three in step. */
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
    var sel = $("ride-chat-language");
    if (sel) sel.value = state.chatLanguage;
  }
  function saveChatLanguage() {
    var sel = $("ride-chat-language");
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
      hide($("chat-panel"));
      return;
    }
    show($("chat-panel"));
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
    var box = $("chat-messages");
    box.innerHTML = "";
    if (!messages.length) {
      box.innerHTML = '<p class="chat-empty">' + esc(T("status.chat_empty", "No messages yet. Your chauffeur can read your messages here.")) + '</p>';
      return;
    }
    messages.forEach(function (m) {
      var div = document.createElement("div");
      var mine = m.sender === "customer";
      div.className = "chat-msg " + (mine ? "mine" : "theirs");
      div.innerHTML = '<span class="who">' + (mine ? T("status.you", "You") : T("status.chauffeur_word", "Chauffeur")) + "</span>" +
        '<span class="txt">' + esc(m.text) + "</span>";
      box.appendChild(div);
    });
    box.scrollTop = box.scrollHeight;
  }
  function sendChat() {
    if (!state.bookingId || !state.bookingPhone) return;
    var input = $("chat-input");
    var text = input.value.trim();
    if (!text) return;
    var btn = $("chat-send");
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
  $("chat-send").addEventListener("click", sendChat);
  $("chat-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); sendChat(); }
  });
  var rideChatLang = $("ride-chat-language");
  if (rideChatLang) rideChatLang.addEventListener("change", saveChatLanguage);

  function showThankYou(b) {
    show($("thankyou-block"));
    $("thankyou-summary").textContent =
      "Ride confirmed: " + summaryText(b) + ".";
    /* Test-mode payments say so on the booked view — never presented
       as a real charge. */
    var testNote = $("thankyou-test-note");
    if (testNote) {
      if (state.testModePaid) show(testNote); else hide(testNote);
    }
    if (b.ride_type === "one_way") { show($("return-trip-btn")); } else { hide($("return-trip-btn")); }
  }

  /* ---------- Referral link prefill (no visible referral UI) ---------- */
  /* The visible referral UI was removed (owner decision 2026-11-21),
     but already-shared referral links keep working: the shareable
     link carries the same code the booking form accepts:
     https://noelchauffer.com/?ref=CODE (built from the current
     origin so it works on every host). The CUSTOMER shares the link
     himself (WhatsApp, message, etc.) — the system sends nothing to
     friends. A friend arriving via a referral link gets the code
     prefilled — no typing needed. No validation here: the booking
     endpoint rejects unknown codes as usual, so a bad link can never
     break the page. The 5% first-ride discount for the new customer
     still applies server-side. */
  (function prefillReferralFromUrl() {
    var ref = (new URLSearchParams(window.location.search).get("ref") || "").trim();
    if (!ref) return;
    var field = $("bk-referral");
    if (field && !field.value) field.value = ref;
  })();

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
    var err = $("pay-error");
    var unavailable = $("pay-unavailable");
    var loading = $("pay-loading");
    var submit = $("pay-submit");
    err.textContent = "";
    hide(unavailable);
    hide($("pay-test-mode"));
    hide($("pay-stripe-mode"));
    $("pay-saved-list").innerHTML = "";
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
          show($("pay-test-mode"));
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
          err.textContent = T("status.pay_start_failed", "Could not start the secure payment form. Please try again.");
          return;
        }
        if (!state.cardElement) {
          var elements = state.stripe.elements();
          state.cardElement = elements.create("card", {
            style: {
              base: {
                color: "#161617",
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
                fontSize: "16px",
                "::placeholder": { color: "#8a8a8a" }
              },
              invalid: { color: "#a83232" }
            }
          });
          state.cardElement.mount("#pay-card-element");
          state.cardElement.on("change", function (ev) {
            if (ev.error) err.textContent = ev.error.message;
          });
        } else {
          state.cardElement.clear();
        }
        hide(loading);
        show($("pay-stripe-mode"));
        show($("pay-save-card-row"));
        submit.disabled = false;
        loadSavedCards();
      })
      .catch(function () {
        if (state.payMode === false) return; /* not-set-up message already shown */
        hide(loading);
        err.textContent = T("status.reach_payment", "Could not reach the payment service. Please try again.");
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
    var checked = document.querySelector('input[name="pay-saved-card"]:checked');
    if (!checked || checked.value === "new") return null;
    return checked.value;
  }
  function updatePayMethodVisibility() {
    if (selectedSavedCardId()) {
      hide($("pay-new-card-field"));
      hide($("pay-save-card-row"));
    } else {
      show($("pay-new-card-field"));
      show($("pay-save-card-row"));
    }
  }
  /* Saved cards for this booking's phone, listed ABOVE the Card
     Element. "Use a different card" is the default, so a saved card
     is only ever charged when the customer picks it. Only brand /
     last4 / expiry are ever shown — no full card details exist here. */
  function loadSavedCards() {
    var box = $("pay-saved-cards");
    var list = $("pay-saved-list");
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
          radio.name = "pay-saved-card";
          radio.value = String(c.id);
          radio.addEventListener("change", updatePayMethodVisibility);
          label.appendChild(radio);
          label.appendChild(document.createTextNode(savedCardLabel(c)));
          var remove = document.createElement("button");
          remove.type = "button";
          remove.className = "remove-saved-card";
          remove.textContent = T("status.remove", "Remove");
          remove.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (!window.confirm(T("status.remove_card_confirm", "Remove this saved card?"))) return;
            fetch("/api/customers/cards/" + encodeURIComponent(c.id) + "?phone=" +
                  encodeURIComponent(state.bookingPhone), { method: "DELETE" })
              .then(function (r) {
                return r.json().catch(function () { return {}; }).then(function (jj) { return { ok: r.ok, j: jj }; });
              })
              .then(function (res) {
                if (!res.ok) {
                  $("pay-error").textContent = (res.j && (res.j.error || res.j.message)) || T("status.remove_card_failed", "That card could not be removed.");
                  return;
                }
                loadSavedCards();
              })
              .catch(function () {
                $("pay-error").textContent = T("status.reach_payment", "Could not reach the payment service. Please try again.");
              });
          });
          label.appendChild(remove);
          list.appendChild(label);
        });
        var fresh = document.createElement("label");
        fresh.className = "saved-card-option";
        var freshRadio = document.createElement("input");
        freshRadio.type = "radio";
        freshRadio.name = "pay-saved-card";
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
    var btn = $("pay-submit");
    var err = $("pay-error");
    if (res.j && res.j.needs_action && res.j.client_secret && !alreadyConfirmed) {
      if (!res.j.payment_intent_id) {
        btn.disabled = false;
        btn.textContent = T("status.pay", "Pay");
        err.textContent = T("status.pay_confirm_missing", "Payment needs confirmation, but no confirmation was provided. Please try again.");
        return Promise.resolve();
      }
      btn.textContent = T("status.confirming", "Confirming…");
      return state.stripe.confirmCardPayment(res.j.client_secret)
        .then(function (result) {
          if (result.error) {
            btn.disabled = false;
            btn.textContent = T("status.pay", "Pay");
            err.textContent = result.error.message || T("status.card_confirm_failed", "Your card could not be confirmed. Please try again.");
            return;
          }
          btn.textContent = T("status.processing", "Processing…");
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
              btn.textContent = T("status.pay", "Pay");
              err.textContent = T("status.reach_payment", "Could not reach the payment service. Please try again.");
            });
        })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = T("status.pay", "Pay");
          err.textContent = T("status.reach_payment", "Could not reach the payment service. Please try again.");
        });
    }
    btn.disabled = false;
    btn.textContent = T("status.pay", "Pay");
    if (!res.ok || !res.j || !res.j.payment) {
      /* Decline / Stripe error: the server's message, verbatim. The
         booking stays awaiting_payment and is never sent to drivers. */
      err.textContent = (res.j && (res.j.error || res.j.message)) || T("status.pay_failed", "Payment could not be completed. Please try again.");
      return Promise.resolve();
    }
    state.paid = true;
    /* The /pay response carries test_mode:true in test mode (or
       payment.test) — the booked view then says so, never passing
       a faked authorization off as a real charge. */
    state.testModePaid = !!(res.j.test_mode || (res.j.payment && res.j.payment.test));
    hide($("pay-panel"));
    hide($("pay-open-btn"));
    if (res.j.booking && res.j.booking.status) {
      state.booking = Object.assign({}, state.booking, res.j.booking);
    }
    showThankYou(state.booking || {});
    $("thankyou-block").scrollIntoView({ behavior: "smooth", block: "center" });
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

  var payOpenBtn = $("pay-open-btn");
  if (payOpenBtn) payOpenBtn.addEventListener("click", function () {
    show($("pay-panel"));
    $("pay-panel").scrollIntoView({ behavior: "smooth", block: "center" });
    initPayment();
  });

  /* Test mode: the old raw-card submit, exactly as before. Only used
     while the server reports test_mode=true (no Stripe keys
     configured). The server fakes the authorization; the booked view
     says "Test mode — no real charge". */
  function submitTestPayment() {
    var err = $("pay-error");
    var payload = {
      card_number: $("pay-number").value.replace(/[\s-]/g, ""),
      card_exp: $("pay-exp").value.trim(),
      card_cvc: $("pay-cvc").value.trim(),
      card_name: $("pay-name").value.trim()
    };
    if (!payload.card_number || !payload.card_exp || !payload.card_cvc || !payload.card_name) {
      err.textContent = T("status.fill_card_fields", "Please fill in all card fields.");
      return;
    }
    var btn = $("pay-submit");
    btn.disabled = true;
    btn.textContent = T("status.processing_test", "Processing (test mode)…");
    postPay(payload)
      .then(function (res) { return handlePayResponse(res, false); })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = T("status.pay", "Pay");
        err.textContent = T("status.reach_payment", "Could not reach the payment service. Please try again.");
      });
  }

  $("pay-form").addEventListener("submit", function (e) {
    e.preventDefault();
    if (!state.bookingId) return;
    var err = $("pay-error");
    err.textContent = "";
    if (state.payMode === false) {
      show($("pay-unavailable"));
      return;
    }
    if (state.payMode === "test") {
      submitTestPayment();
      return;
    }
    if (state.payMode !== "stripe") {
      err.textContent = T("status.pay_loading_wait", "The secure payment form is still loading. Please wait a moment and try again.");
      return;
    }
    if (!state.stripe || !state.cardElement) {
      err.textContent = T("status.pay_loading_wait", "The secure payment form is still loading. Please wait a moment and try again.");
      return;
    }
    var btn = $("pay-submit");
    btn.disabled = true;
    btn.textContent = T("status.processing", "Processing…");
    var savedId = selectedSavedCardId();
    if (savedId) {
      /* A saved card: only its server-side id is sent — never any
         card details. */
      postPay({ saved_card_id: parseInt(savedId, 10) })
        .then(function (res) { return handlePayResponse(res, false); })
        .catch(function () {
          btn.disabled = false;
          btn.textContent = T("status.pay", "Pay");
          err.textContent = T("status.reach_payment", "Could not reach the payment service. Please try again.");
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
          btn.textContent = T("status.pay", "Pay");
          err.textContent = result.error.message || T("status.check_card", "Please check your card details and try again.");
          return;
        }
        return postPay({
          payment_method_id: result.paymentMethod.id,
          save_card: $("pay-save-card").checked
        })
          .then(function (res) { return handlePayResponse(res, false); })
          .catch(function () {
            btn.disabled = false;
            btn.textContent = T("status.pay", "Pay");
            err.textContent = T("status.reach_payment", "Could not reach the payment service. Please try again.");
          });
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = T("status.pay", "Pay");
        err.textContent = T("status.reach_payment", "Could not reach the payment service. Please try again.");
      });
  });

  /* ---------- Cancel ---------- */
  $("cancel-booking-btn").addEventListener("click", function () {
    if (!state.bookingId) return;
    if (!window.confirm(T("status.cancel_confirm", "Cancel this booking? The cancellation rules on this page apply."))) return;
    fetch("/api/bookings/" + encodeURIComponent(state.bookingId) + "/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: state.bookingPhone })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        var line = $("cancel-result");
        show(line);
        if (!res.ok) {
          line.textContent = (res.j && (res.j.error || res.j.message)) || T("status.cancel_failed", "Cancellation could not be completed.");
          return;
        }
        stopPolling();
        /* The API returns booleans: refund / charge_kept, not amounts. */
        var bits = ["Booking cancelled."];
        if (res.j.refund) bits.push("Your payment will be refunded.");
        if (res.j.charge_kept) bits.push("The full price applies under the cancellation rules.");
        line.textContent = bits.join(" ");
        hide($("status-actions"));
        hide($("pay-panel"));
        hide($("total-box"));
        hide($("thankyou-block"));
        show($("status-finding"));
        $("status-message").textContent = T("status.cancelled", "This booking was cancelled.");
        /* No ride is live any more: the form returns, fresh and
           empty, so the customer can book again without the old
           ride's values — and the submit guard no longer blocks it. */
        state.bookingId = null;
        state.booking = null;
        state.paid = false;
        clearBookingForm();
        show($("booking-card"));
      })
      .catch(function () {
        var line = $("cancel-result");
        show(line);
        line.textContent = T("status.reach_booking", "Could not reach the booking service. Please try again.");
      });
  });

  /* ---------- Return trip / new booking ---------- */
  $("return-trip-btn").addEventListener("click", function () {
    var b = state.booking;
    if (!b) return;
    stopPolling();
    hide($("status-card"));
    hide($("thankyou-block"));
    hide($("invoice-panel"));
    show($("booking-card"));
    tabs.forEach(function (t) {
      var active = t.getAttribute("data-ride-type") === "one_way";
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    state.rideType = "one_way";
    state.isReturnTrip = true;
    show($("field-dropoff"));
    hide($("field-hours"));
    hide($("field-contact"));
    $("bk-pickup").value = b.dropoff || "";
    $("bk-dropoff").value = b.pickup || "";
    $("bk-date").value = "";
    $("bk-time").value = "";
    $("bk-referral").value = "";
    /* The swapped addresses keep their picked suggestions (with
       coordinates), so the must-pick rule still passes — the
       customer only re-picks if the page was reloaded since the
       first booking. The flight field follows the swapped places. */
    var prevPickup = state.pickupPlace;
    var prevDropoff = state.dropoffPlace;
    clearBookingPlaces();
    state.pickupPlace = prevDropoff;
    state.dropoffPlace = prevPickup;
    state.dateIso = "";
    state.timeValue = "";
    $("bk-flight").value = "";
    updateFlightField();
    state.bookingId = null;
    state.booking = null;
    state.paid = false;
    $("booking-card").scrollIntoView({ behavior: "smooth", block: "start" });
    $("bk-date").focus();
  });

  /* ---------- Book another ride: the SEPARATE option ---------- */
  /* The only way back to the booking form once a ride exists (the
     return-trip button is the other, for the ride home). It opens a
     FRESH EMPTY form — the previous ride's values are cleared, so
     tapping "View options" can only ever create a new booking. */
  $("new-booking-btn").addEventListener("click", function () {
    stopPolling();
    hide($("status-card"));
    hide($("thankyou-block"));
    hide($("invoice-panel"));
    state.bookingId = null;
    state.booking = null;
    state.paid = false;
    clearBookingForm();
    show($("booking-card"));
    $("booking-card").scrollIntoView({ behavior: "smooth", block: "start" });
    $("bk-date").focus();
  });

  /* ---------- Live map (Leaflet, with text fallback) ---------- */
  function renderMap(lat, lng, booking) {
    var fallback = $("map-fallback");
    var mapEl = $("map");
    if (typeof window.L === "undefined") {
      mapEl.classList.add("hidden");
      show(fallback);
      fallback.textContent = T("status.map_unavailable", "Live map is unavailable right now. Your chauffeur is on the way to {place}.", { place: booking.pickup || T("status.your_pickup_point", "your pickup point") });
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
      state.map = window.L.map("map", {
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

  /* ---------- Chat widget (scripted answers only) ---------- */
  /* The support widget is a SEPARATE chat from the ride chat above:
     it is available always, with no booking and no trip. Its element
     IDs are prefixed support-chat-* so they can never collide with
     the ride chat's chat-panel/chat-messages/chat-input IDs — the
     duplicate IDs were why tapping "Chat with us" looked dead:
     getElementById returned the ride-chat elements and the floating
     panel never opened. */
  var chatPanel = $("support-chat-panel");
  var chatMessages = $("support-chat-messages");
  var chatOpened = false;

  function openChat() {
    show(chatPanel);
    if (!chatOpened) {
      chatOpened = true;
      addMsg("bot", T("chat.greeting", "Hello, and welcome to Noel Chauffer. How can I help — cancellation, waiting time, or something about a ride?"));
    }
    $("support-chat-input").focus();
  }
  function closeChat() { hide(chatPanel); }
  function addMsg(who, text) {
    var div = document.createElement("div");
    div.className = "msg " + who;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
  function answer(text) {
    var t = text.toLowerCase();
    var has = function () {
      for (var i = 0; i < arguments.length; i++) {
        if (t.indexOf(arguments[i]) !== -1) return true;
      }
      return false;
    };
    if (has("paus")) {
      return T("chat.ans_paused", "No — bookings are open. Enter your pickup and drop-off in the booking form to see your fare.");
    }
    if (has("cancel", "refund")) {
      return T("chat.ans_cancel", "Cancellation is free if you cancel more than 1 hour before pickup. If you cancel 1 hour or less before pickup, the cancellation is not refundable.");
    }
    if (has("wait", "airport", "late", "delay")) {
      return T("chat.ans_wait", "Waiting is free for 60 minutes at airports and 15 minutes at other pickups. After that, waiting charges apply.");
    }
    if (has("price", "cost", "much", "total", "charge", "pay", "payment")) {
      return T("chat.ans_price", "Enter your pickup and drop-off in the booking form above, choose your experience, and you will see the total for each class before you pay.");
    }
    if (has("lost", "left", "forgot", "belonging", "item")) {
      return T("chat.ans_lost", "I am sorry to hear that. Please report it here as soon as you can, and within 7 days. The driver checks the car after every ride. Unclaimed items go to the police station after one week.");
    }
    if (has("problem", "complaint", "issue", "unhappy", "escalat", "manager", "owner")) {
      return T("chat.ans_problem", "I am sorry about that. I will escalate this to the owner, who will look into it personally. Please tell me your pickup date and time and what happened.");
    }
    if (has("driver", "chauffeur", "phone", "email", "detail", "contact")) {
      return T("chat.ans_driver", "As soon as your chauffeur accepts, you will see their name, phone number, car, colour and plate number on this page — and the same details are sent to your phone and email.");
    }
    if (has("car", "vehicle", "sedan", "suv", "type", "class")) {
      return T("chat.ans_car", "Our rides come in three classes — Business Class, Business SUV and First Class — recent high-end cars, clean, comfortable, and prepared for every ride, with phone chargers on board.");
    }
    if (has("return", "round trip", "back", "come back")) {
      return T("chat.ans_return", "For a return journey, simply book a second one-way ride. After you pay for your first ride, this page offers you a return booking with the addresses already swapped for you.");
    }
    if (has("hour", "hourly", "by the hour")) {
      return T("chat.ans_hourly", "Choose the “By the hour” tab in the booking form, pick a vehicle class and how many hours you need (minimum 2 hours). Your chauffeur stays with you for the hours you book, with 25 miles of travel included per hour.");
    }
    if (has("refer", "friend", "code")) {
      return T("chat.ans_refer", "If a friend referred you, open their referral link — it takes you to the booking form with their code already filled in, and your first booking gets 5% off.");
    }
    if (has("book", "reserve", "ride", "pickup", "how")) {
      return T("chat.ans_book", "Enter your pickup and drop-off, date and time in the booking form above, choose your experience, and pay by card — your chauffeur is assigned right after payment.");
    }
    if (has("hello", "hi", "hey", "salam")) {
      return T("chat.ans_hello", "Hello, and welcome to Noel Chauffer. Bookings are open — enter your pickup and drop-off in the booking form to see your fare. I can still help with prices, cancellation, waiting time, lost items, or a problem with a ride.");
    }
    if (has("human", "person", "agent", "support", "help")) {
      return T("chat.ans_human", "You are chatting with the Noel Chauffer team here. The team replies within 24 hours. If your matter is urgent, please describe it here and we will escalate it to the owner.");
    }
    return T("chat.ans_default", "Happy to help. Bookings are open. I can answer questions about prices, cancellation, waiting time, your chauffeur's details, cars, return trips, by-the-hour rides, or lost items — just ask.");
  }
  function handleQuestion(q) {
    if (!q) return;
    addMsg("user", q);
    setTimeout(function () { addMsg("bot", answer(q)); }, 350);
  }
  /* Typed messages also reach the owner (owner dashboard, "Support
     messages"), so a problem or lost item is actually seen — the
     scripted answers already promise owner escalation. Fire-and-
     forget: a failed POST changes nothing in the widget, and the
     scripted answer above is never gated on it. Chip taps are FAQ
     navigation, not messages, so only typed text is reported. */
  function reportToOwner(q) {
    if (!q) return;
    fetch("/api/support-messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: q })
    }).catch(function () { /* widget answers work with or without the server */ });
  }

  $("chat-fab").addEventListener("click", function () {
    if (chatPanel.classList.contains("hidden")) { openChat(); } else { closeChat(); }
  });
  $("chat-close").addEventListener("click", closeChat);
  if ($("open-chat-btn")) { $("open-chat-btn").addEventListener("click", openChat); }
  $("support-chat-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var input = $("support-chat-input");
    var q = input.value.trim();
    input.value = "";
    handleQuestion(q);
    reportToOwner(q);
  });
  document.querySelectorAll("#support-chat-chips button").forEach(function (chip) {
    chip.addEventListener("click", function () { handleQuestion(chip.getAttribute("data-q")); });
  });
})();
