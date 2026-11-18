/* Noel Chauffer — customer site logic.
   Talks only to the /api/* contract. The total is NEVER computed here:
   it comes from the API with the booking. Flow: booking form (+ the
   flight-number step for airport rides) -> "Choose your experience"
   options page (Business Class / Business SUV, one single total each)
   -> card payment -> only then is the booking sent to drivers. The
   customer picks a class, sees the single total, pays by card, and
   only then is the booking sent to drivers. */
(function () {
  "use strict";

  var state = {
    rideType: "one_way",
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
    classBooking: null,
    classPhone: "",
    lastChatSig: "",
    chatLanguage: "en",
    chatLangInitFor: null
  };

  /* Customer-facing class names. Internal keys stay "sedan"/"suv". */
  var CLASS_LABELS = { sedan: "Business Class", suv: "Business SUV" };
  function classLabelFor(b) {
    if (!b || b.ride_type !== "one_way") return "";
    return b.vehicle_class_label || CLASS_LABELS[b.vehicle_class] || "";
  }
  function summaryText(b) {
    var text = rideLabel(b);
    var cls = classLabelFor(b);
    if (cls) text += " · " + cls;
    if (whenLabel(b)) text += " · " + whenLabel(b);
    return text;
  }

  function $(id) { return document.getElementById(id); }
  function show(el) { el.classList.remove("hidden"); }
  function hide(el) { el.classList.add("hidden"); }
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
      if (state.rideType === "hourly") {
        hide($("field-dropoff"));
        hide($("field-passengers"));
        show($("field-hours"));
        state.dropoffPlace = null;
      } else {
        show($("field-dropoff"));
        show($("field-passengers"));
        hide($("field-hours"));
      }
    });
  });

  /* Date input: no past dates. */
  (function () {
    var d = new Date();
    var iso = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
    $("bk-date").setAttribute("min", iso);
  })();

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

  attachPlaces("bk-pickup", "bk-pickup-list", "pickup");
  attachPlaces("bk-dropoff", "bk-dropoff-list", "dropoff");

  /* ---------- Create a booking ---------- */
  $("booking-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("booking-error");
    err.textContent = "";
    var payload = {
      customer_name: $("bk-name").value.trim(),
      phone: $("bk-phone").value.trim(),
      email: $("bk-email").value.trim(),
      pickup: $("bk-pickup").value.trim(),
      date: $("bk-date").value,
      time: $("bk-time").value,
      ride_type: state.rideType
    };
    if (state.rideType === "one_way") {
      payload.dropoff = $("bk-dropoff").value.trim();
      var p = parseInt($("bk-passengers").value, 10);
      if (!isNaN(p) && p > 0) payload.passengers = p;
      var ref = $("bk-referral").value.trim();
      if (ref) payload.referral_code = ref;
    } else {
      var h = parseInt($("bk-hours").value, 10);
      if (!isNaN(h) && h > 0) payload.hours = h;
    }
    /* When the customer picked a suggestion, send its coordinates so
       the fare is priced for exactly the place picked — the server
       never has to re-resolve the address text. Typed text without a
       pick sends no coordinates and the server resolves the text;
       editing a field clears the stored pick (see clearStored). */
    if (state.pickupPlace && isFinite(state.pickupPlace.lat) && isFinite(state.pickupPlace.lon)) {
      payload.pickup_lat = state.pickupPlace.lat;
      payload.pickup_lng = state.pickupPlace.lon;
    }
    if (state.rideType === "one_way" && state.dropoffPlace && isFinite(state.dropoffPlace.lat) && isFinite(state.dropoffPlace.lon)) {
      payload.dropoff_lat = state.dropoffPlace.lat;
      payload.dropoff_lng = state.dropoffPlace.lon;
    }
    if (!payload.customer_name || !payload.phone || !payload.email || !payload.pickup || !payload.date || !payload.time) {
      err.textContent = "Please fill in your name, phone, email, pickup, date and time.";
      return;
    }
    if (state.rideType === "one_way" && !payload.dropoff) {
      err.textContent = "Please enter a drop-off address.";
      return;
    }
    /* Airport rides ask for the flight number as a SEPARATE step after
       this form — never a field inside it. Skipping never blocks the
       booking. Detection: the chosen suggestion's airport flag, with
       an address-text fallback (see flight.js). */
    var sides = { any: false, pickup: false, dropoff: false };
    if (window.NoelFlight) {
      sides = window.NoelFlight.airportSides(
        state.pickupPlace, state.dropoffPlace,
        payload.pickup, payload.dropoff || "");
    }
    if (sides.any && !state.flightResolved) {
      showFlightStep(sides, payload);
      return;
    }
    if (state.flightNumber) payload.flight_number = state.flightNumber;
    sendBooking(payload);
  });

  /* Flight-number step: shown after the booking form for airport rides. */
  function showFlightStep(sides, payload) {
    state.pendingPayload = payload;
    if (sides.pickup) {
      $("flight-step-title").textContent = "Add your flight number";
      $("flight-step-text").textContent = "Your chauffeur will meet you at the right terminal.";
    } else {
      $("flight-step-title").textContent = "Add your flight number (optional)";
      $("flight-step-text").textContent = "This helps your chauffeur take you to the right departure terminal.";
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

  /* Choose your experience: a SEPARATE options page after the booking
     form (and the flight step). The booking already exists, unpaid;
     the customer picks a class — each option shows its own single
     total, no breakdown, no rates, no miles — and then continues to
     the card payment. Sedan (Business Class) is pre-selected. Back
     cancels the unpaid booking and returns to the form to edit. */
  function paintClassSelection() {
    ["sedan", "suv"].forEach(function (cls) {
      var opt = $("class-option-" + cls);
      var selected = state.selectedClass === cls;
      opt.classList.toggle("selected", selected);
      opt.setAttribute("aria-checked", selected ? "true" : "false");
    });
    $("class-continue").textContent = "Select " + (CLASS_LABELS[state.selectedClass] || "Business Class");
  }

  function showClassStep(booking, phone) {
    state.classBooking = booking;
    state.classPhone = phone;
    state.selectedClass = booking.vehicle_class || "sedan";
    $("class-trip-summary").textContent = summaryText(booking);
    var totals = booking.class_totals || {};
    $("class-total-sedan").textContent = money(totals.sedan !== undefined ? totals.sedan : booking.total);
    $("class-total-suv").textContent = money(totals.suv);
    $("class-error").textContent = "";
    paintClassSelection();
    hide($("booking-card"));
    show($("class-step"));
    $("class-step").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  ["sedan", "suv"].forEach(function (cls) {
    $("class-option-" + cls).addEventListener("click", function () {
      state.selectedClass = cls;
      paintClassSelection();
    });
  });

  $("class-continue").addEventListener("click", function () {
    var booking = state.classBooking;
    if (!booking) return;
    var err = $("class-error");
    err.textContent = "";
    var btn = $("class-continue");
    function proceedWith(updated) {
      hide($("class-step"));
      show($("booking-card"));
      state.classBooking = null;
      startTracking(updated, state.classPhone);
    }
    if (state.selectedClass === (booking.vehicle_class || "sedan")) {
      proceedWith(booking);
      return;
    }
    btn.disabled = true;
    fetch("/api/bookings/" + encodeURIComponent(booking.id) + "/vehicle-class", {
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

  $("class-back").addEventListener("click", function () {
    var booking = state.classBooking;
    var phone = state.classPhone;
    state.classBooking = null;
    state.classPhone = "";
    hide($("class-step"));
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
          return;
        }
        var booking = res.j.booking;
        /* One-way rides go to the separate options page first (pick a
           class, each with its own single total); hourly rides have
           no class and go straight to the payment step. */
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
      });
  }

  function startTracking(booking, phone) {
    stopPolling();
    state.bookingId = booking.id;
    state.bookingPhone = phone;
    state.booking = booking;
    state.paid = false;
    state.flightNumber = null;
    state.flightResolved = false;
    state.pendingPayload = null;
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
    /* The create response already carries the single total: show it
       and open the card payment box at once, before any polling. */
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
        $("status-heading").textContent = "Your total is ready";
        $("status-message").textContent = "Please pay by card below — your chauffeur will be assigned right after payment.";
      } else {
        $("status-heading").textContent = "Finding your chauffeur…";
        $("status-message").textContent = statusLabel(st) || "Your request is with us. Please keep this page open.";
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
      $("status-heading").textContent = "Booking cancelled";
      $("status-message").textContent = "This booking was cancelled.";
      show($("status-finding"));
    }
    if (st === "completed") {
      hide($("status-actions"));
      hide($("pay-panel"));
    }
  }

  /* ---------- In-app chat with the chauffeur (text only) ---------- */
  /* Opens once a driver has accepted; messages carry text only and
     the customer still sees only the single total elsewhere. The
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
    /* The API returns the issued code as `referral_code` on the booking. */
    var code = b.referral_code || b.customer_referral_code || b.share_code || b.own_referral_code || null;
    if (code) {
      show($("referral-code-line"));
      $("referral-code-value").textContent = code;
    } else {
      hide($("referral-code-line"));
    }
    if (b.ride_type === "one_way") { show($("return-trip-btn")); } else { hide($("return-trip-btn")); }
  }

  /* ---------- Payment (test mode) ---------- */
  $("pay-open-btn").addEventListener("click", function () {
    show($("pay-panel"));
    $("pay-panel").scrollIntoView({ behavior: "smooth", block: "center" });
    $("pay-name").focus();
  });

  $("pay-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("pay-error");
    err.textContent = "";
    var payload = {
      card_number: $("pay-number").value.replace(/[\s-]/g, ""),
      card_exp: $("pay-exp").value.trim(),
      card_cvc: $("pay-cvc").value.trim(),
      card_name: $("pay-name").value.trim()
    };
    if (!payload.card_number || !payload.card_exp || !payload.card_cvc || !payload.card_name) {
      err.textContent = "Please fill in all card fields.";
      return;
    }
    var btn = $("pay-submit");
    btn.disabled = true;
    btn.textContent = "Processing (test mode)…";
    fetch("/api/bookings/" + encodeURIComponent(state.bookingId) + "/pay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        btn.textContent = "Pay";
        if (!res.ok || !res.j.payment) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Payment could not be completed. Please try again.";
          return;
        }
        state.paid = true;
        hide($("pay-panel"));
        hide($("pay-open-btn"));
        if (res.j.booking && res.j.booking.status) {
          state.booking = Object.assign({}, state.booking, res.j.booking);
        }
        showThankYou(state.booking || {});
        $("thankyou-block").scrollIntoView({ behavior: "smooth", block: "center" });
        pollOnce();
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "Pay";
        err.textContent = "Could not reach the payment service. Please try again.";
      });
  });

  /* ---------- Cancel ---------- */
  $("cancel-booking-btn").addEventListener("click", function () {
    if (!state.bookingId) return;
    if (!window.confirm("Cancel this booking? The cancellation rules on this page apply.")) return;
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
          line.textContent = (res.j && (res.j.error || res.j.message)) || "Cancellation could not be completed.";
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
        show($("status-finding"));
        $("status-message").textContent = "This booking was cancelled.";
      })
      .catch(function () {
        var line = $("cancel-result");
        show(line);
        line.textContent = "Could not reach the booking service. Please try again.";
      });
  });

  /* ---------- Return trip / new booking ---------- */
  $("return-trip-btn").addEventListener("click", function () {
    var b = state.booking;
    if (!b) return;
    stopPolling();
    hide($("status-card"));
    tabs.forEach(function (t) {
      var active = t.getAttribute("data-ride-type") === "one_way";
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    state.rideType = "one_way";
    show($("field-dropoff"));
    show($("field-passengers"));
    hide($("field-hours"));
    $("bk-pickup").value = b.dropoff || "";
    $("bk-dropoff").value = b.pickup || "";
    $("bk-date").value = "";
    $("bk-time").value = "";
    $("bk-referral").value = "";
    clearBookingPlaces();
    state.bookingId = null;
    state.booking = null;
    state.paid = false;
    $("booking-card").scrollIntoView({ behavior: "smooth", block: "start" });
    $("bk-date").focus();
  });

  $("new-booking-btn").addEventListener("click", function () {
    stopPolling();
    hide($("status-card"));
    state.bookingId = null;
    state.booking = null;
    state.paid = false;
    $("booking-card").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  /* ---------- Live map (Leaflet, with text fallback) ---------- */
  function renderMap(lat, lng, booking) {
    var fallback = $("map-fallback");
    var mapEl = $("map");
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
      state.map = window.L.map("map").setView([lat, lng], 14);
      window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "© OpenStreetMap contributors"
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
  $("history-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var phone = $("history-phone").value.trim();
    var err = $("history-error");
    var box = $("history-results");
    err.textContent = "";
    box.innerHTML = "";
    if (!phone) { err.textContent = "Please enter your phone number."; return; }
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
        box.innerHTML = list.map(function (b) {
          var driverName = b.driver && b.driver.name ? esc(b.driver.name) : "";
          var totalHtml = (b.total !== null && b.total !== undefined)
            ? '<div class="h-total">' + esc(money(b.total)) + "</div>" : "";
          return '<div class="history-item"><div class="h-top"><div>' +
            '<div class="h-route">' + esc(rideLabel(b)) + "</div>" +
            '<div class="h-meta">' + esc(whenLabel(b)) +
            (b.ride_type === "hourly" ? " · By the hour" : " · One way") +
            (driverName ? " · Chauffeur: " + driverName : "") + "</div>" +
            '<div style="margin-top:6px;"><span class="pill">' + esc(statusLabel(b.status)) + "</span></div>" +
            "</div>" + totalHtml + "</div></div>";
        }).join("");
      })
      .catch(function () {
        box.innerHTML = "";
        err.textContent = "Could not reach the booking service. Please try again.";
      });
  });

  /* ---------- Chat widget (scripted answers only) ---------- */
  var chatPanel = $("chat-panel");
  var chatMessages = $("chat-messages");
  var chatOpened = false;

  function openChat() {
    show(chatPanel);
    if (!chatOpened) {
      chatOpened = true;
      addMsg("bot", "Hello, and welcome to Noel Chauffer. How can I help — booking, cancellation, waiting time, or something about a ride?");
    }
    $("chat-input").focus();
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
    if (has("cancel", "refund")) {
      return "Cancellation is free if you cancel more than 1 hour before pickup. If you cancel 1 hour or less before pickup, the full price of the ride applies.";
    }
    if (has("wait", "airport", "late", "delay")) {
      return "Waiting is free for 60 minutes at airports and 15 minutes at other pickups. After that, waiting is charged at $1/min. A no-show is charged the full price.";
    }
    if (has("price", "cost", "much", "total", "charge", "pay", "payment")) {
      return "After you complete the booking form, choose Business Class or Business SUV — each class shows its own single total, with no breakdown and no hidden charges. You pay by card on this page, and then your chauffeur is assigned.";
    }
    if (has("lost", "left", "forgot", "belonging", "item")) {
      return "I am sorry to hear that. Please report it here as soon as you can, and within 7 days. The driver checks the car after every ride. Unclaimed items go to the police station after one week.";
    }
    if (has("problem", "complaint", "issue", "unhappy", "escalat", "manager", "owner")) {
      return "I am sorry about that. I will escalate this to the owner, who will look into it personally. Please tell me your pickup date and time and what happened.";
    }
    if (has("driver", "chauffeur", "phone", "email", "detail", "contact")) {
      return "As soon as your chauffeur accepts, you will see their name, phone number, car, colour and plate number on this page — and the same details are sent to your phone and email.";
    }
    if (has("car", "vehicle", "sedan", "suv", "type", "class")) {
      return "Our rides come in two classes — Business Class and Business SUV — recent high-end cars, clean, comfortable, and prepared for every ride, with phone chargers on board.";
    }
    if (has("return", "round trip", "back", "come back")) {
      return "For a return journey, simply book a second one-way ride. After you pay for your first ride, this page offers you a return booking with the addresses already swapped for you.";
    }
    if (has("hour", "hourly", "by the hour")) {
      return "Choose the “By the hour” tab in the booking form, enter your pickup, date, time and how many hours you need. Your chauffeur stays with you for the hours you book.";
    }
    if (has("refer", "friend", "code")) {
      return "If a friend referred you, enter their referral code in the booking form. After your ride, this page shows you how to refer a friend too.";
    }
    if (has("book", "reserve", "ride", "pickup", "how")) {
      return "To book: fill in the form at the top of this page — pickup, drop-off (or hours), date, time, and your name, phone and email — then tap “View options” to choose your class. Each class shows its own single total — you pay by card, and then your chauffeur will be assigned.";
    }
    if (has("hello", "hi", "hey", "salam")) {
      return "Hello, and welcome to Noel Chauffer. I can help with booking, the total, cancellation, waiting time, lost items, or a problem with a ride.";
    }
    if (has("human", "person", "agent", "support", "help")) {
      return "You are chatting with the Noel Chauffer team here. The team replies within 24 hours. If your matter is urgent, please describe it here and we will escalate it to the owner.";
    }
    return "Happy to help. I can answer questions about booking a ride, when you see the total, cancellation, waiting time, your chauffeur's details, cars, return trips, by-the-hour rides, or lost items — just ask.";
  }
  function handleQuestion(q) {
    if (!q) return;
    addMsg("user", q);
    setTimeout(function () { addMsg("bot", answer(q)); }, 350);
  }

  $("chat-fab").addEventListener("click", function () {
    if (chatPanel.classList.contains("hidden")) { openChat(); } else { closeChat(); }
  });
  $("chat-close").addEventListener("click", closeChat);
  $("open-chat-btn").addEventListener("click", openChat);
  $("chat-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var input = $("chat-input");
    var q = input.value.trim();
    input.value = "";
    handleQuestion(q);
  });
  document.querySelectorAll("#chat-chips button").forEach(function (chip) {
    chip.addEventListener("click", function () { handleQuestion(chip.getAttribute("data-q")); });
  });
})();
