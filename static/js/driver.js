/* Noel Chauffer — driver app logic.
   The driver sees ONLY his own earnings per job. No other money figure
   is ever displayed. Offers show the earnings value from the API as-is. */
(function () {
  "use strict";

  var TOKEN_KEY = "noel_driver_token";
  var FILE_FIELDS = [
    "doc_dmv_license",
    "profile_photo",
    "doc_tlc_license",
    "doc_fh1",
    "doc_registration",
    "doc_inspection",
    "doc_vehicle_permit"
  ];
  var DOC_LABELS = {
    doc_dmv_license: "DMV driving license",
    profile_photo: "Profile Picture",
    doc_tlc_license: "TLC License",
    doc_fh1: "FH-1 Insurance Card",
    doc_registration: "Commercial Vehicle Registration",
    doc_inspection: "NYS DMV Inspection",
    doc_vehicle_permit: "TLC-for-hire Vehicle Permit"
  };
  var STAGES = ["en_route", "arrived", "start", "complete"];
  var STAGE_BUTTON = {
    en_route: "Head to pickup",
    arrived: "I have arrived",
    start: "Start trip",
    complete: "Complete trip"
  };

  var state = {
    token: null,
    driver: null,
    available: false,
    offersTimer: null,
    trip: null,
    stageIndex: 0,
    watchId: null
  };

  function $(id) { return document.getElementById(id); }
  function show(el) { el.classList.remove("hidden"); }
  function hide(el) { el.classList.add("hidden"); }
  function money(n) {
    if (n === null || n === undefined || isNaN(Number(n))) return "—";
    return "$" + Number(n).toFixed(2);
  }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function getToken() {
    try { return window.localStorage.getItem(TOKEN_KEY); } catch (e) { return state.token; }
  }
  function saveToken(t) {
    state.token = t;
    try { window.localStorage.setItem(TOKEN_KEY, t); } catch (e) { /* private mode */ }
  }
  function clearToken() {
    state.token = null;
    try { window.localStorage.removeItem(TOKEN_KEY); } catch (e) { /* private mode */ }
  }
  function authHeaders(extra) {
    var h = { "X-Driver-Token": state.token || "" };
    if (extra) { for (var k in extra) h[k] = extra[k]; }
    return h;
  }
  function unwrapDriver(j) {
    if (!j) return null;
    return j.driver || j;
  }
  function pickNumber(obj, keys) {
    for (var i = 0; i < keys.length; i++) {
      var v = obj ? obj[keys[i]] : undefined;
      if (v !== null && v !== undefined && !isNaN(Number(v))) return Number(v);
    }
    return null;
  }
  function maskBank(value) {
    var digits = String(value || "").replace(/\D/g, "");
    if (!digits) return "Saved";
    if (digits.length <= 4) return "••••" + digits;
    return "••••" + digits.slice(-4);
  }

  /* ---------- Screens ---------- */
  var SCREENS = ["register", "home", "trip", "earnings", "documents", "profile"];
  function showScreen(name) {
    SCREENS.forEach(function (s) {
      var el = $("screen-" + s);
      if (el) { if (s === name) show(el); else hide(el); }
    });
    if (name === "register" || name === "trip") {
      hide($("tabbar"));
    } else {
      show($("tabbar"));
      document.querySelectorAll("#tabbar button").forEach(function (b) {
        b.classList.toggle("active", b.getAttribute("data-screen") === name);
      });
    }
    window.scrollTo(0, 0);
    if (name === "home") { refreshOffers(); }
    if (name === "earnings") { loadEarnings(); }
    if (name === "documents") { renderDocuments(); }
    if (name === "profile") { renderProfile(); }
  }
  document.querySelectorAll("#tabbar button").forEach(function (b) {
    b.addEventListener("click", function () { showScreen(b.getAttribute("data-screen")); });
  });

  /* ---------- Boot: registered drivers never see registration again ---------- */
  function boot() {
    var token = getToken();
    if (!token) { showScreen("register"); return; }
    state.token = token;
    fetch("/api/drivers/me", { headers: authHeaders() })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok || !unwrapDriver(res.j)) {
          clearToken();
          showScreen("register");
          return;
        }
        enterApp(unwrapDriver(res.j));
      })
      .catch(function () {
        /* Offline: fall back to registration rather than a dead screen. */
        showScreen("register");
      });
  }

  function enterApp(driver) {
    state.driver = driver || {};
    state.available = !!state.driver.available;
    renderHello();
    renderAvailability();
    showScreen("home");
    startOffersPolling();
    restoreActiveTrip();
  }

  /* If the driver already has an assigned trip (e.g. after a reload),
     restore the trip screen at the right stage instead of losing it. */
  function tripFromBooking(b, fallbackId) {
    return {
      id: b.booking_id || b.id || fallbackId,
      pickup: b.pickup,
      dropoff: b.dropoff,
      date: b.date,
      time: b.time,
      ride_type: b.ride_type,
      hours: b.hours,
      earnings: pickNumber(b, ["earnings", "driver_earnings", "amount"]),
      route_url: b.route_url,
      customer_name: b.customer_name,
      customer_phone: b.customer_phone,
      flight_number: b.flight_number || null,
      airline_name: b.airline_name || null,
      terminal: b.terminal || null
    };
  }
  function restoreActiveTrip() {
    fetch("/api/drivers/me/active-trip", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var b = j && j.booking;
        if (!b || !b.id) return;
        state.trip = tripFromBooking(b);
        var stageByStatus = { accepted: 0, en_route: 1, arrived: 2, in_progress: 3 };
        state.stageIndex = stageByStatus[b.status] !== undefined ? stageByStatus[b.status] : 0;
        renderTrip();
        showScreen("trip");
        if (b.status === "en_route" || b.status === "arrived" || b.status === "in_progress") {
          startLocationSharing();
        }
      })
      .catch(function () { /* no active trip, or unreachable: stay on Home */ });
  }

  function renderHello() {
    var line = $("hello-line");
    if (state.driver && state.driver.name) {
      line.textContent = "Hello, " + state.driver.name;
      show(line);
    } else {
      hide(line);
    }
  }

  /* ---------- File previews (photo check before saving) ---------- */
  FILE_FIELDS.forEach(function (field) {
    var input = $("file-" + field);
    if (!input) return;
    input.addEventListener("change", function () {
      var box = $("preview-" + field);
      box.innerHTML = "";
      var file = input.files && input.files[0];
      if (!file) return;
      if (file.type && file.type.indexOf("image/") === 0) {
        var img = document.createElement("img");
        img.alt = "Preview — check it is clear and complete, retake if blurry";
        img.src = URL.createObjectURL(file);
        box.appendChild(img);
      } else {
        var p = document.createElement("p");
        p.className = "file-name";
        p.textContent = "Selected file: " + file.name + " — please check it is the right document.";
        box.appendChild(p);
      }
    });
  });

  /* ---------- Registration ---------- */
  $("register-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("register-error");
    err.textContent = "";
    var name = $("reg-name").value.trim();
    var phone = $("reg-phone").value.trim();
    var email = $("reg-email").value.trim();
    var carModel = $("reg-car-model").value.trim();
    var carYear = $("reg-car-year").value.trim();
    var carColour = $("reg-car-colour").value.trim();
    var plate = $("reg-plate").value.trim();
    var acct = $("reg-bank-account").value.trim();
    var routing = $("reg-bank-routing").value.trim();
    if (!name || !phone || !email || !carModel || !carYear || !carColour || !plate || !acct || !routing) {
      err.textContent = "Please fill in every field, including your bank details.";
      return;
    }
    if (carListLoaded && carModels.indexOf(carModel) === -1) {
      err.textContent = "Please choose your car model from the list.";
      return;
    }
    var fd = new FormData();
    fd.append("name", name);
    fd.append("phone", phone);
    fd.append("email", email);
    fd.append("car_model", carModel);
    fd.append("car_year", carYear);
    fd.append("car_colour", carColour);
    fd.append("plate", plate);
    fd.append("bank_account_number", acct);
    fd.append("bank_routing_number", routing);
    FILE_FIELDS.forEach(function (field) {
      var input = $("file-" + field);
      if (input && input.files && input.files[0]) fd.append(field, input.files[0]);
    });
    var btn = $("register-submit");
    btn.disabled = true;
    btn.textContent = "Registering…";
    fetch("/api/drivers/register", { method: "POST", body: fd })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        btn.textContent = "Complete registration";
        if (!res.ok || !res.j.token) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Registration could not be completed. Please check your details and try again.";
          return;
        }
        saveToken(res.j.token);
        enterApp(unwrapDriver(res.j) || {});
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "Complete registration";
        err.textContent = "Could not reach the service. Please check your connection and try again.";
      });
  });

  /* ---------- Lookup for a new device ---------- */
  $("lookup-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("lookup-error");
    err.textContent = "";
    var phone = $("lookup-phone").value.trim();
    if (!phone) { err.textContent = "Please enter your phone number."; return; }
    var btn = $("lookup-submit");
    btn.disabled = true;
    fetch("/api/drivers/me/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: phone })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok || !res.j.token) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "No registration was found for that number. Please register above.";
          return;
        }
        saveToken(res.j.token);
        /* Lookup returns only id + name: fetch the full record so the
           Documents and Profile tabs are populated on this device. */
        fetch("/api/drivers/me", { headers: authHeaders() })
          .then(function (r) { return r.json(); })
          .then(function (j) { enterApp(unwrapDriver(j) || unwrapDriver(res.j) || {}); })
          .catch(function () { enterApp(unwrapDriver(res.j) || {}); });
      })
      .catch(function () {
        btn.disabled = false;
        err.textContent = "Could not reach the service. Please try again.";
      });
  });

  /* ---------- Availability ---------- */
  function renderAvailability() {
    var st = $("avail-state");
    var btn = $("avail-toggle");
    if (state.available) {
      st.textContent = "You are available";
      st.classList.add("on");
      btn.textContent = "Go offline";
      btn.classList.add("on");
      $("avail-note").textContent = "Job offers will appear below as they arrive.";
    } else {
      st.textContent = "You are offline";
      st.classList.remove("on");
      btn.textContent = "Go available";
      btn.classList.remove("on");
      $("avail-note").textContent = "Go available to receive job offers.";
    }
  }
  $("avail-toggle").addEventListener("click", function () {
    var next = !state.available;
    fetch("/api/drivers/me/availability", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ available: next })
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        state.available = next;
        renderAvailability();
        refreshOffers();
      })
      .catch(function () { /* leave the toggle as it was */ });
  });

  /* ---------- Job offers (earnings only) ---------- */
  function startOffersPolling() {
    if (state.offersTimer) clearInterval(state.offersTimer);
    state.offersTimer = setInterval(function () {
      if (!$("screen-home").classList.contains("hidden") && state.available && !state.trip) {
        refreshOffers();
      }
    }, 5000);
  }
  function refreshOffers() {
    if (!state.token) return;
    fetch("/api/drivers/me/offers", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = Array.isArray(j) ? j : (j.offers || []);
        renderOffers(list);
      })
      .catch(function () { /* keep the current list on a failed check */ });
  }
  function offerId(o) { return o.booking_id || o.id; }
  function renderOffers(list) {
    var box = $("offers-list");
    box.innerHTML = "";
    if (!list.length) { show($("offers-empty")); return; }
    hide($("offers-empty"));
    list.forEach(function (o) {
      var card = document.createElement("div");
      card.className = "offer";
      var route = esc(o.pickup || "");
      if (o.dropoff) route += "  →  " + esc(o.dropoff);
      var when = [o.date, o.time].filter(Boolean).join(" · ");
      if (o.ride_type === "hourly") when += (when ? " · " : "") + "By the hour" + (o.hours ? " · " + o.hours + " hour(s)" : "");
      var earnings = pickNumber(o, ["earnings", "driver_earnings", "amount"]);
      var html = '<div class="route">' + route + "</div>" +
        '<div class="when">' + esc(when) + "</div>" +
        '<div class="earnings"><span class="label">Your earnings</span><span class="amount">' + esc(money(earnings)) + "</span></div>";
      if (o.route_url) {
        html += '<a class="route-link" href="' + esc(o.route_url) + '" target="_blank" rel="noopener">View route map ↗</a>';
      }
      html += '<div class="offer-actions">' +
        '<button type="button" class="btn-accept">Accept</button>' +
        '<button type="button" class="btn-decline">Decline</button></div>';
      card.innerHTML = html;
      card.querySelector(".btn-accept").addEventListener("click", function () { respondToOffer(offerId(o), "accept"); });
      card.querySelector(".btn-decline").addEventListener("click", function () { respondToOffer(offerId(o), "decline"); });
      box.appendChild(card);
    });
  }
  function respondToOffer(id, action) {
    fetch("/api/drivers/me/offers/" + encodeURIComponent(id) + "/" + action, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({})
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (action === "decline") { refreshOffers(); return; }
        if (!res.ok) { refreshOffers(); return; }
        var b = res.j.booking || res.j;
        state.trip = tripFromBooking(b, id);
        state.stageIndex = 0;
        renderTrip();
        showScreen("trip");
      })
      .catch(function () { refreshOffers(); });
  }

  /* ---------- Trip screen ---------- */
  function renderTrip() {
    var t = state.trip;
    if (!t) return;
    var route = esc(t.pickup || "");
    if (t.dropoff) route += "  →  " + esc(t.dropoff);
    $("trip-route").innerHTML = route;
    var when = [t.date, t.time].filter(Boolean).join(" · ");
    if (t.ride_type === "hourly") when += (when ? " · " : "") + "By the hour" + (t.hours ? " · " + t.hours + " hour(s)" : "");
    $("trip-when").textContent = when;
    var cust = "";
    if (t.customer_name) cust += esc(t.customer_name);
    if (t.customer_phone) {
      cust += (cust ? " · " : "") + '<a href="tel:' + esc(t.customer_phone.replace(/[^+0-9]/g, "")) + '">' + esc(t.customer_phone) + "</a>";
    }
    $("trip-customer").innerHTML = cust;
    /* Flight details for airport trips: flight number, airline name and
       terminal only — never miles, fare, or any other money figure. */
    var flightEl = $("trip-flight");
    if (t.flight_number) {
      var flightText = "Flight: " + t.flight_number;
      if (t.airline_name) flightText += " · " + t.airline_name;
      if (t.terminal) flightText += " · " + t.terminal;
      flightEl.textContent = flightText;
      show(flightEl);
    } else {
      flightEl.textContent = "";
      hide(flightEl);
    }
    $("trip-earnings").innerHTML =
      '<div class="earnings" style="background:#fffdf4;border:1px solid var(--gold);border-radius:8px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;">' +
      '<span class="label" style="font-size:13px;letter-spacing:0.05em;text-transform:uppercase;color:var(--grey);">Your earnings</span>' +
      '<span class="amount" style="font-family:Georgia,serif;font-size:26px;">' + esc(money(t.earnings)) + "</span></div>";
    $("trip-route-link").innerHTML = t.route_url
      ? '<a class="route-link" style="display:inline-block;margin-top:10px;font-weight:600;" href="' + esc(t.route_url) + '" target="_blank" rel="noopener">View route map ↗</a>'
      : "";
    renderStages();
    $("trip-error").textContent = "";
  }
  function renderStages() {
    var items = document.querySelectorAll("#stage-list li");
    items.forEach(function (li, i) {
      var tick = li.querySelector(".tick");
      li.classList.remove("done", "current");
      if (i < state.stageIndex) { li.classList.add("done"); tick.textContent = "✓"; }
      else if (i === state.stageIndex) { li.classList.add("current"); tick.textContent = "●"; }
      else { tick.textContent = ""; }
    });
    var current = STAGES[state.stageIndex];
    $("trip-next-btn").textContent = STAGE_BUTTON[current] || "Continue";
    if (current === "complete") { show($("waiting-field")); } else { hide($("waiting-field")); }
  }
  function postTripEvent(eventName, extra) {
    var payload = Object.assign({ event: eventName }, extra || {});
    return fetch("/api/drivers/me/trip/" + encodeURIComponent(state.trip.id) + "/event", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); });
  }
  $("trip-next-btn").addEventListener("click", function () {
    var current = STAGES[state.stageIndex];
    if (!current || !state.trip) return;
    var btn = $("trip-next-btn");
    btn.disabled = true;
    var extra = {};
    if (current === "complete") {
      var w = parseInt($("waiting-minutes").value, 10);
      if (!isNaN(w) && w > 0) extra.waiting_minutes = w;
    }
    postTripEvent(current, extra)
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok) {
          $("trip-error").textContent = (res.j && (res.j.error || res.j.message)) || "That step could not be saved. Please try again.";
          return;
        }
        if (current === "en_route") { startLocationSharing(); }
        if (current === "complete") { endTrip(); return; }
        state.stageIndex++;
        renderStages();
      })
      .catch(function () {
        btn.disabled = false;
        $("trip-error").textContent = "Could not reach the service. Please try again.";
      });
  });
  $("trip-cancel-btn").addEventListener("click", function () {
    if (!state.trip) return;
    if (!window.confirm("Cancel this job? The job goes to the next driver automatically.")) return;
    postTripEvent("cancel", {}).then(function () { endTrip(); }).catch(function () { endTrip(); });
  });
  $("trip-noshow-btn").addEventListener("click", function () {
    if (!state.trip) return;
    if (!window.confirm("Mark this ride as a customer no-show?")) return;
    postTripEvent("no_show", {}).then(function () { endTrip(); }).catch(function () { endTrip(); });
  });
  function endTrip() {
    stopLocationSharing();
    state.trip = null;
    state.stageIndex = 0;
    hide($("loc-note"));
    showScreen("home");
    refreshOffers();
  }

  /* ---------- Location sharing while heading to pickup ---------- */
  function startLocationSharing() {
    var note = $("loc-note");
    if (!("geolocation" in navigator)) {
      note.textContent = "Location sharing is not available on this device. The trip can continue without it.";
      show(note);
      return;
    }
    note.textContent = "Sharing your location while you head to pickup.";
    show(note);
    var send = function (pos) {
      if (!state.trip) return;
      fetch("/api/drivers/me/trip/" + encodeURIComponent(state.trip.id) + "/location", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ lat: pos.coords.latitude, lng: pos.coords.longitude })
      }).catch(function () { /* a missed update is harmless; the next one follows */ });
    };
    var onErr = function () {
      note.textContent = "Location sharing is off. The trip can continue without it — the customer will not see live movement.";
    };
    try {
      state.watchId = navigator.geolocation.watchPosition(send, onErr, { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 });
    } catch (e) {
      onErr();
    }
  }
  function stopLocationSharing() {
    if (state.watchId !== null && "geolocation" in navigator) {
      try { navigator.geolocation.clearWatch(state.watchId); } catch (e) { /* ignore */ }
    }
    state.watchId = null;
  }

  /* ---------- Earnings ---------- */
  function fmtDay(isoDate) {
    /* Format a YYYY-MM-DD date without timezone shifting. */
    var parts = String(isoDate || "").split("-");
    if (parts.length !== 3) return String(isoDate || "");
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var m = parseInt(parts[1], 10);
    if (!m || m < 1 || m > 12) return String(isoDate);
    return months[m - 1] + " " + parseInt(parts[2], 10) + ", " + parts[0];
  }
  function renderPayoutWeeks(weeks) {
    var box = $("payout-weeks");
    if (!box) return;
    box.innerHTML = "";
    (weeks || []).forEach(function (w) {
      var paid = w.paid === true || w.status === "paid";
      var count = pickNumber(w, ["ride_count", "rides", "rideCount"]);
      var card = document.createElement("div");
      card.className = "pay-week";
      card.innerHTML =
        '<div class="pw-top"><div class="pw-range">' + esc(fmtDay(w.start) + " – " + fmtDay(w.end)) + "</div>" +
        '<span class="badge ' + (paid ? "done" : "todo") + '">' + (paid ? "Paid" : "Unpaid") + "</span></div>" +
        '<div class="pw-meta">Due ' + esc(fmtDay(w.due_date)) +
        (count !== null ? " · " + count + " ride(s)" : "") + "</div>" +
        '<div class="pw-amount">' + esc(money(pickNumber(w, ["total_earnings", "total", "amount"]))) + "</div>";
      box.appendChild(card);
    });
  }
  function loadEarnings() {
    fetch("/api/drivers/me/earnings", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        renderPayoutWeeks(j.weeks || j.pay_periods || j.payouts || []);
        var list = Array.isArray(j) ? j : (j.earnings || j.rides || j.completed || []);
        var box = $("earnings-list");
        box.innerHTML = "";
        var sum = 0;
        var haveRows = false;
        list.forEach(function (r) {
          var val = pickNumber(r, ["earnings", "driver_earnings", "amount"]);
          if (val !== null) { sum += val; haveRows = true; }
          var route = esc(r.route || "");
          if (!route) {
            route = esc(r.pickup || "");
            if (r.dropoff) route += " → " + esc(r.dropoff);
          }
          var meta = [r.date, r.time].filter(Boolean).join(" · ");
          if (r.payout_status === "paid" || r.payout_paid === true) {
            meta += (meta ? " · " : "") + "Paid";
          } else if (r.payout_status === "unpaid" || r.payout_paid === false) {
            meta += (meta ? " · " : "") + "Unpaid";
          }
          var div = document.createElement("div");
          div.className = "earn-item";
          div.innerHTML = "<div><div class=\"r\">" + (route || "Ride") + "</div><div class=\"m\">" + esc(meta) + "</div></div>" +
            "<div class=\"a\">" + esc(money(val)) + "</div>";
          box.appendChild(div);
        });
        if (!list.length) {
          show($("earnings-empty"));
          var only = pickNumber(j, ["total_earnings", "earnings_sum", "sum", "earned", "amount", "total_earned"]);
          $("earnings-sum").textContent = only !== null ? money(only) : money(0);
        } else {
          hide($("earnings-empty"));
          var summary = pickNumber(j, ["total_earnings", "earnings_sum", "sum", "earned", "amount", "total_earned"]);
          $("earnings-sum").textContent = money(summary !== null ? summary : (haveRows ? sum : 0));
        }
      })
      .catch(function () { /* keep the previous view on a failed check */ });
  }

  /* ---------- Documents ---------- */
  function docIsComplete(value) {
    if (value === true) return true;
    if (!value) return false;
    if (typeof value === "string") {
      var v = value.toLowerCase();
      if (v === "completed" || v === "complete" || v === "approved" || v === "verified") return true;
      if (v.indexOf("http") === 0 || v.indexOf("/") === 0) return true;
      return false;
    }
    if (typeof value === "object") {
      var st = String(value.status || value.state || "").toLowerCase();
      if (st === "completed" || st === "complete" || st === "approved" || st === "verified") return true;
      if (st === "missing" || st === "pending" || st === "remaining" || st === "incomplete") return false;
      if (value.url || value.path || value.file || value.document_id || value.id) return true;
    }
    return false;
  }
  function renderDocuments() {
    var box = $("documents-list");
    box.innerHTML = "";
    /* The API returns document statuses as `docs` keyed by document
       type (e.g. dmv_license: "completed"). */
    var docs = (state.driver && (state.driver.docs || state.driver.documents)) || {};
    var byKey = {};
    if (Array.isArray(docs)) {
      docs.forEach(function (d) {
        var key = d.key || d.field || d.name || d.document || "";
        byKey[key] = d;
      });
    } else if (typeof docs === "object") {
      byKey = docs;
    }
    FILE_FIELDS.forEach(function (field) {
      var value = byKey[field];
      if (value === undefined) {
        /* Try common alternate spellings from the API payload. */
        var alts = {
          doc_dmv_license: ["dmv_license", "dmv_driving_license"],
          profile_photo: ["profile_picture", "photo", "profile"],
          doc_tlc_license: ["tlc_license"],
          doc_fh1: ["fh1", "fh1_insurance", "insurance"],
          doc_registration: ["registration", "commercial_registration"],
          doc_inspection: ["inspection", "dmv_inspection"],
          doc_vehicle_permit: ["vehicle_permit", "tlc_vehicle_permit"]
        };
        (alts[field] || []).forEach(function (a) { if (byKey[a] !== undefined) value = byKey[a]; });
      }
      var done = docIsComplete(value);
      var row = document.createElement("div");
      row.className = "doc-status";
      row.innerHTML = '<span class="name">' + esc(DOC_LABELS[field]) + "</span>" +
        '<span class="badge ' + (done ? "done" : "todo") + '">' + (done ? "Completed" : "Items remaining") + "</span>";
      box.appendChild(row);
    });
  }

  /* ---------- Profile ---------- */
  function renderProfile() {
    var d = state.driver || {};
    var carBits = [d.car_year, d.car_model, d.car_colour].filter(Boolean).join(" · ");
    var bank = d.bank_account_number || d.bank_account || d.account_number || d.masked_account || d.bank_masked || "";
    var bankText = bank ? maskBank(String(bank).indexOf("•") !== -1 || String(bank).indexOf("*") !== -1 ? bank.replace(/[^0-9]/g, "").slice(-4) : bank) : "Saved";
    if (String(bank).indexOf("•") !== -1 || String(bank).indexOf("*") !== -1) {
      bankText = String(bank);
    }
    var photo = d.profile_photo_url || d.photo_url || d.profile_photo || "";
    var html = "";
    if (photo && typeof photo === "string" && photo.indexOf("http") === 0) {
      html += '<img src="' + esc(photo) + '" alt="Profile photo">';
    }
    html += '<div class="profile-row"><span class="k">Name</span><span>' + esc(d.name || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Phone</span><span>' + esc(d.phone || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Email</span><span>' + esc(d.email || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Car</span><span>' + esc(carBits || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Plate</span><span>' + esc(d.plate || "—") + "</span></div>" +
      '<div class="profile-row"><span class="k">Bank account</span><span>' + esc(bankText) + "</span></div>";
    $("profile-card").innerHTML = html;
  }
  $("reset-driver-btn").addEventListener("click", function () {
    if (!window.confirm("Sign out this driver on this device and show registration again?")) return;
    stopLocationSharing();
    clearToken();
    state.driver = null;
    state.trip = null;
    window.location.reload();
  });

  /* ---------- Car model dropdown (registration) ---------- */
  /* Searchable dropdown fed by GET /api/car-models — the same single
     list the server validates against. Type to filter; tap a
     suggestion to choose it. Free text is not accepted: the chosen
     value must match a list entry exactly. The year select is filled
     from the same response (2022 through current year + 1). */
  var carModels = [];
  var carListLoaded = false;

  function fillYearSelect(minYear, maxYear) {
    var sel = $("reg-car-year");
    sel.innerHTML = '<option value="">Select year</option>';
    for (var y = maxYear; y >= minYear; y--) {
      var opt = document.createElement("option");
      opt.value = String(y);
      opt.textContent = String(y);
      sel.appendChild(opt);
    }
  }

  function initCarModelDropdown() {
    var input = $("reg-car-model");
    var list = $("car-model-list");
    var note = $("car-model-note");
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
    function choose(name) {
      input.value = name;
      closeList();
      input.focus();
    }
    function render(matches) {
      items = matches;
      activeIndex = -1;
      list.innerHTML = "";
      if (!matches.length) { closeList(); return; }
      matches.forEach(function (name, idx) {
        var li = document.createElement("li");
        var btn = document.createElement("button");
        btn.type = "button";
        btn.setAttribute("role", "option");
        btn.setAttribute("aria-selected", "false");
        btn.id = "car-model-list-opt-" + idx;
        btn.textContent = name;
        /* mousedown fires before the input loses focus, so a tap or
           click always lands on the suggestion. */
        btn.addEventListener("mousedown", function (e) {
          e.preventDefault();
          choose(name);
        });
        li.appendChild(btn);
        list.appendChild(li);
      });
      show(list);
      input.setAttribute("aria-expanded", "true");
    }
    function filter() {
      var q = input.value.trim().toLowerCase();
      var matches = carModels.filter(function (name) {
        return !q || name.toLowerCase().indexOf(q) !== -1;
      }).slice(0, 8);
      render(matches);
    }
    input.addEventListener("input", filter);
    input.addEventListener("focus", filter);
    input.addEventListener("blur", function () {
      /* A tap on a suggestion fires mousedown first; the short delay
         keeps that working on touch screens. */
      setTimeout(closeList, 150);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (!items.length) return;
        e.preventDefault();
        activeIndex = e.key === "ArrowDown"
          ? (activeIndex + 1) % items.length
          : (activeIndex - 1 + items.length) % items.length;
        paintActive();
      } else if (e.key === "Enter") {
        if (activeIndex >= 0 && items[activeIndex]) {
          e.preventDefault();
          choose(items[activeIndex]);
        }
      } else if (e.key === "Escape") {
        closeList();
      }
    });

    fetch("/api/car-models")
      .then(function (r) { return r.json(); })
      .then(function (j) {
        carModels = j.models || [];
        carListLoaded = carModels.length > 0;
        fillYearSelect(j.min_year || 2022, j.max_year || new Date().getFullYear() + 1);
        if (!carListLoaded) { throw new Error("empty list"); }
      })
      .catch(function () {
        note.textContent = "The car list could not be loaded. Please check your connection and reload this page.";
        input.disabled = true;
        $("register-submit").disabled = true;
      });
  }

  initCarModelDropdown();
  boot();
})();
