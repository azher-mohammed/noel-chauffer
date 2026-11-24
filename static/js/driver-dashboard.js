/* Noel Chauffer — driver dashboard website.
   Simple, like the driver app: jobs + earnings + driver app badges
   only. Same sign-in and same data as /driver, so a driver signed
   in on the driver app stays signed in here (same token key).
   A job offer shows pickup, drop-off and time only — no amounts —
   exactly like the driver app. Earnings are the driver's own pay
   only: no customer payment figures are ever rendered here, even
   if a payload carries them. */
(function () {
  "use strict";

  var TOKEN_KEY = "noel_driver_token";
  var SEEN_OFFERS_KEY = "noel_seen_offers";
  var MAX_SEEN_OFFERS = 200;
  /* A new offer rings for 30 seconds: the chime pattern repeats
     until the driver answers, the offer goes, or 30 seconds pass. */
  var TONE_DURATION_MS = 30000;
  var TONE_REPEAT_MS = 3000;
  var CLASS_LABELS = { sedan: "Business Class", suv: "Business SUV" };

  var state = {
    token: null,
    driver: null,
    available: false,
    offersTimer: null,
    seenOfferIds: {},
    toneTimer: null,
    toneStopAt: 0,
    toneOfferIds: {},
    lastOffersSig: "",
    audioCtx: null
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
  function fmtDay(isoDate) {
    /* Format a YYYY-MM-DD date without timezone shifting. */
    var parts = String(isoDate || "").split("-");
    if (parts.length !== 3) return String(isoDate || "");
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var m = parseInt(parts[1], 10);
    if (!m || m < 1 || m > 12) return String(isoDate);
    return months[m - 1] + " " + parseInt(parts[2], 10) + ", " + parts[0];
  }
  function classLabelFor(obj) {
    if (!obj) return "";
    return obj.vehicle_class_label || CLASS_LABELS[obj.vehicle_class] || "";
  }
  /* Route as two separate blocks: 'Pick up' and 'Drop off' each on
     its own line, with a down arrow between them. Hourly rides have
     no drop-off, so only the pickup block shows. */
  function routeHtml(pickup, dropoff) {
    var html = '<div class="route-leg"><span class="route-label">Pick up</span> ' + esc(pickup || "") + "</div>";
    if (dropoff) html += '<div class="route-sep" aria-hidden="true">↓</div>' +
      '<div class="route-leg"><span class="route-label">Drop off</span> ' + esc(dropoff) + "</div>";
    return html;
  }

  /* ---------- Sign in ---------- */
  function showSignin() {
    stopOffersPolling();
    stopOfferTone();
    hide($("dd-main"));
    hide($("dd-signout"));
    show($("dd-signin"));
  }
  function enterDashboard(driver) {
    state.driver = driver || {};
    state.available = !!state.driver.available;
    var hello = $("dd-hello");
    if (state.driver.name) { hello.textContent = "Hello, " + state.driver.name; show(hello); }
    show($("dd-signout"));
    hide($("dd-signin"));
    show($("dd-main"));
    loadSeenOfferIds();
    refreshDriverState();
    restoreActiveTrip();
    loadEarnings();
    startOffersPolling();
    refreshOffers();
  }

  $("dd-signin-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("dd-signin-error");
    err.textContent = "";
    var email = $("dd-signin-email").value.trim();
    var password = $("dd-signin-password").value;
    if (!email || !password) { err.textContent = "Please enter your email and password."; return; }
    var btn = $("dd-signin-submit");
    btn.disabled = true;
    fetch("/api/drivers/me/signin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok || !res.j.token) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Email or password is incorrect.";
          return;
        }
        saveToken(res.j.token);
        fetch("/api/drivers/me", { headers: authHeaders() })
          .then(function (r) { return r.json(); })
          .then(function (j) { enterDashboard(unwrapDriver(j) || unwrapDriver(res.j) || {}); })
          .catch(function () { enterDashboard(unwrapDriver(res.j) || {}); });
      })
      .catch(function () {
        btn.disabled = false;
        err.textContent = "Could not reach the service. Please try again.";
      });
  });

  /* Show/hide password (eye) toggle, inside the password field. */
  document.querySelectorAll(".password-eye").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var input = document.getElementById(btn.getAttribute("data-for"));
      if (!input) return;
      var showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.textContent = showing ? "Show" : "Hide";
    });
  });

  /* ---------- Forgot password ---------- */
  $("dd-forgot-link").addEventListener("click", function () {
    hide($("dd-signin-form"));
    hide($("dd-forgot-link"));
    show($("dd-forgot-form"));
  });
  $("dd-forgot-back-link").addEventListener("click", function () {
    hide($("dd-forgot-form"));
    show($("dd-signin-form"));
    show($("dd-forgot-link"));
  });
  $("dd-forgot-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var msg = $("dd-forgot-message");
    msg.textContent = "";
    var email = $("dd-forgot-email").value.trim();
    if (!email) { msg.textContent = "Please enter your email."; return; }
    var btn = $("dd-forgot-submit");
    btn.disabled = true;
    fetch("/api/drivers/me/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email })
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        btn.disabled = false;
        msg.textContent = (j && j.message) || "If an account exists for that email, password reset instructions have been sent.";
      })
      .catch(function () {
        btn.disabled = false;
        msg.textContent = "Could not reach the service. Please try again.";
      });
  });

  $("dd-signout").addEventListener("click", function () {
    clearToken();
    clearSeenOfferIds();
    showSignin();
  });

  /* ---------- New-offer tone ---------- */
  /* Browsers only allow sound after the driver has tapped something,
     so the audio context is unlocked on any tap on the page. The tone
     is a short chime made with the Web Audio API — no audio file
     needed. A new offer repeats that chime for 30 seconds so the
     driver cannot miss it; it stops the moment he accepts or
     declines, when the offer disappears, or when the 30 seconds are
     up. The tone only plays while this page is open in the browser. */
  function unlockAudio() {
    try {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      if (!state.audioCtx) state.audioCtx = new AC();
      if (state.audioCtx.state === "suspended") state.audioCtx.resume();
    } catch (e) { /* audio unavailable: offers still show silently */ }
  }
  document.addEventListener("pointerdown", unlockAudio);

  /* Offer IDs already alerted to, kept in localStorage across page
     refreshes — the same key as the driver app, so an offer that
     already rang there never rings again here. */
  function loadSeenOfferIds() {
    try {
      var raw = window.localStorage.getItem(SEEN_OFFERS_KEY);
      var ids = raw ? JSON.parse(raw) : [];
      var seen = {};
      if (Array.isArray(ids)) {
        ids.forEach(function (id) { seen[id] = true; });
      }
      state.seenOfferIds = seen;
    } catch (e) { state.seenOfferIds = {}; }
  }
  function saveSeenOfferIds() {
    try {
      var ids = Object.keys(state.seenOfferIds);
      if (ids.length > MAX_SEEN_OFFERS) ids = ids.slice(ids.length - MAX_SEEN_OFFERS);
      window.localStorage.setItem(SEEN_OFFERS_KEY, JSON.stringify(ids));
    } catch (e) { /* private mode: ringing still works for this session */ }
  }
  function clearSeenOfferIds() {
    state.seenOfferIds = {};
    try { window.localStorage.removeItem(SEEN_OFFERS_KEY); } catch (e) { /* ignore */ }
  }

  /* One chime burst: the three-note pattern plus a vibration. */
  function playOfferTone() {
    try {
      unlockAudio();
      var ctx = state.audioCtx;
      if (!ctx) return;
      var notes = [880, 1174.66, 880];
      notes.forEach(function (freq, i) {
        var t = ctx.currentTime + i * 0.18;
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.16);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.18);
      });
      if (navigator.vibrate) navigator.vibrate([180, 80, 180]);
    } catch (e) { /* keep silent on failure */ }
  }

  /* Ring for up to 30 seconds for the given offer IDs. A second new
     offer arriving while already ringing extends the window to 30
     seconds from its arrival; an offer already alerted to never
     starts the tone again. */
  function startOfferTone(ids) {
    ids.forEach(function (id) { state.toneOfferIds[id] = true; });
    state.toneStopAt = Date.now() + TONE_DURATION_MS;
    if (state.toneTimer) return;
    playOfferTone();
    state.toneTimer = setInterval(function () {
      if (Date.now() >= state.toneStopAt) { stopOfferTone(); return; }
      playOfferTone();
    }, TONE_REPEAT_MS);
  }
  function stopOfferTone() {
    if (state.toneTimer) clearInterval(state.toneTimer);
    state.toneTimer = null;
    state.toneOfferIds = {};
    state.toneStopAt = 0;
    try { if (navigator.vibrate) navigator.vibrate(0); } catch (e) { /* ignore */ }
  }

  /* ---------- Availability + pause notices ---------- */
  /* After a fault emergency cancel the driver app is blocked for 48
     hours. Sign-in still works so the driver sees this notice with
     the exact end date/time; he cannot go available and gets no
     offers until it lifts. The end time comes from /api/drivers/me. */
  function suspensionEnd() {
    var until = state.driver && state.driver.suspended_until;
    if (!until) return null;
    var d = new Date(until);
    if (isNaN(d.getTime()) || d.getTime() <= Date.now()) return null;
    return d;
  }
  function renderSuspension() {
    var banner = $("dd-suspension");
    var end = suspensionEnd();
    if (!end) { hide(banner); return; }
    var when = end.toLocaleString(undefined, {
      month: "long", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit"
    });
    banner.textContent = "Your driver app is paused until " + when + ". You will not get job offers until then.";
    show(banner);
  }
  /* A document expiring within 10 days warns here; an expired one
     pauses driving (no offers, cannot go available) until a new,
     valid one is uploaded in the driver app — the block then lifts
     automatically. Text only: this page has no upload button. */
  function renderExpiry() {
    var banner = $("dd-expiry");
    var d = state.driver || {};
    var expired = d.expired_docs || [];
    var expiring = d.expiring_docs || [];
    if (!expired.length && !expiring.length) { hide(banner); return; }
    banner.classList.remove("expired");
    var text = "";
    if (expired.length) {
      banner.classList.add("expired");
      text = "Your driving is paused — your " +
        expired.map(function (x) { return x.label + " (expired " + x.expires_on + ")"; }).join(", ") +
        " expired. Upload a new, valid one in the driver app to start again.";
    } else {
      text = "Your " +
        expiring.map(function (x) {
          return x.label + " expires " + x.expires_on +
            (x.days_left === 0 ? " (today)" : x.days_left === 1 ? " (tomorrow)" : " (in " + x.days_left + " days)");
        }).join(", ") +
        ". Upload a new one soon in the driver app so you keep getting jobs.";
    }
    banner.textContent = text;
    show(banner);
  }
  function renderAvailability() {
    var btn = $("dd-avail-toggle");
    renderSuspension();
    renderExpiry();
    if (suspensionEnd()) {
      btn.textContent = "Go online";
      btn.classList.remove("on");
      btn.disabled = true;
      return;
    }
    /* An expired document pauses driving: the toggle stays off until
       a new, valid one is uploaded in the driver app. */
    if (state.driver && state.driver.expiry_blocked) {
      btn.textContent = "Go online";
      btn.classList.remove("on");
      btn.disabled = true;
      return;
    }
    btn.disabled = false;
    if (state.available) {
      btn.textContent = "Go offline";
      btn.classList.add("on");
    } else {
      btn.textContent = "Go online";
      btn.classList.remove("on");
    }
  }
  function refreshDriverState() {
    return fetch("/api/drivers/me", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var d = unwrapDriver(j);
        if (d) {
          state.driver = d;
          state.available = !!d.available;
          renderAvailability();
        }
      })
      .catch(function () { /* leave the toggle as it was */ });
  }
  $("dd-avail-toggle").addEventListener("click", function () {
    unlockAudio();
    var next = !state.available;
    fetch("/api/drivers/me/availability", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ available: next })
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var d = unwrapDriver(j) || {};
        state.available = (d.available !== undefined) ? !!d.available : next;
        renderAvailability();
        refreshOffers();
      })
      .catch(function () { refreshDriverState(); });
  });

  /* ---------- Job offers (pickup, drop-off and time only) ---------- */
  function offerId(o) { return o.booking_id || o.id; }
  function startOffersPolling() {
    if (state.offersTimer) clearInterval(state.offersTimer);
    state.offersTimer = setInterval(function () {
      if (state.token) refreshOffers();
    }, 5000);
  }
  function stopOffersPolling() {
    if (state.offersTimer) clearInterval(state.offersTimer);
    state.offersTimer = null;
  }
  function refreshOffers() {
    if (!state.token) return;
    fetch("/api/drivers/me/offers", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = Array.isArray(j) ? j : (j.offers || []);
        /* Ring for every offer the driver has never been alerted to —
           including on the very first poll after a refresh, because
           the seen set is loaded from storage before polling starts.
           An offer already alerted to never rings again, even if it
           leaves the list and comes back. */
        var freshIds = [];
        list.forEach(function (o) {
          var id = offerId(o);
          if (!state.seenOfferIds[id]) {
            state.seenOfferIds[id] = true;
            freshIds.push(id);
          }
        });
        if (freshIds.length) {
          saveSeenOfferIds();
          startOfferTone(freshIds);
        }
        renderOffers(list);
      })
      .catch(function () { /* keep the previous view on a failed check */ });
  }
  function renderOffers(list) {
    var box = $("dd-offers");
    /* The job stays put until the driver accepts or declines it: when
       nothing about the offers changed, leave the cards untouched so
       the list never flickers or rebuilds under the driver's tap. */
    var sig = list.map(function (o) { return offerId(o); }).join("|");
    if (sig === state.lastOffersSig) return;
    state.lastOffersSig = sig;
    box.innerHTML = "";
    if (!list.length) { show($("dd-offers-empty")); return; }
    hide($("dd-offers-empty"));
    list.forEach(function (o) {
      var card = document.createElement("div");
      card.className = "offer";
      var route = routeHtml(o.pickup, o.dropoff);
      var when = [o.date, o.time].filter(Boolean).join(" · ");
      var cls = classLabelFor(o);
      if (cls) when += (when ? " · " : "") + cls;
      if (o.ride_type === "hourly") when += (when ? " · " : "") + "By the hour" + (o.hours ? " · " + o.hours + " hour(s)" : "");
      else if (o.is_return) when += (when ? " · " : "") + "Return trip";
      /* Offers show pickup, drop-off and time only — no amounts. */
      var html = '<div class="route">' + route + "</div>" +
        '<div class="when">' + esc(when) + "</div>";
      if (o.route_url) {
        html += '<a class="route-link" href="' + esc(o.route_url) + '" target="_blank" rel="noopener">Google Maps ↗</a>';
      }
      if (o.route_waze_url) {
        html += '<a class="route-link" href="' + esc(o.route_waze_url) + '" target="_blank" rel="noopener">Waze ↗</a>';
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
    /* The driver answered: stop the tone at once, for accept and
       decline alike, without waiting for the next poll. */
    stopOfferTone();
    fetch("/api/drivers/me/offers/" + encodeURIComponent(id) + "/" + action, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({})
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (action === "decline" || !res.ok) { refreshOffers(); return; }
        var b = res.j.booking || res.j;
        renderTripCard(b);
        refreshOffers();
      })
      .catch(function () { refreshOffers(); });
  }

  /* ---------- Current trip (read-only) ---------- */
  /* Stage actions and navigation stay in the driver app
     only — this card only shows the trip, with a link to open it
     there. */
  function renderTripCard(b) {
    var card = $("dd-trip-card");
    if (!b || !b.id) { hide(card); return; }
    $("dd-trip-route").innerHTML = routeHtml(b.pickup, b.dropoff);
    var when = [b.date, b.time].filter(Boolean).join(" · ");
    var cls = classLabelFor(b);
    if (cls) when += (when ? " · " : "") + cls;
    if (b.ride_type === "hourly") when += (when ? " · " : "") + "By the hour" + (b.hours ? " · " + b.hours + " hour(s)" : "");
    $("dd-trip-when").textContent = when;
    var cust = [b.customer_name, b.customer_phone].filter(Boolean).join(" · ");
    $("dd-trip-customer").textContent = cust;
    /* The driver's own pay for this trip only — never a customer
       payment figure. */
    var earn = $("dd-trip-earnings");
    if (b.earnings !== undefined && b.earnings !== null) {
      earn.innerHTML = '<div class="offer"><div class="earnings"><div class="label">Your earnings</div><div class="amount">' + esc(money(b.earnings)) + "</div></div></div>";
    } else {
      earn.innerHTML = "";
    }
    show(card);
  }
  function restoreActiveTrip() {
    fetch("/api/drivers/me/active-trip", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var b = j && j.booking;
        if (!b || !b.id) { hide($("dd-trip-card")); return; }
        renderTripCard(b);
      })
      .catch(function () { /* no active trip, or unreachable */ });
  }

  /* ---------- Earnings (the driver's own pay only) ---------- */
  function renderPayWeeks(weeks) {
    var box = $("dd-weeks");
    if (!box) return;
    box.innerHTML = "";
    (weeks || []).forEach(function (w) {
      var paid = w.paid === true || w.status === "paid";
      var count = pickNumber(w, ["ride_count", "rides", "rideCount"]);
      var amount = pickNumber(w, ["total_earnings", "amount", "total"]);
      var card = document.createElement("div");
      card.className = "pay-week";
      card.innerHTML =
        '<div class="pw-top"><div class="pw-range">' + esc(fmtDay(w.start) + " – " + fmtDay(w.end)) + "</div>" +
        '<span class="badge ' + (paid ? "done" : "todo") + '">' + (paid ? "Paid" : "Unpaid") + "</span></div>" +
        '<div class="pw-meta">Due ' + esc(fmtDay(w.due_date)) +
        (count !== null ? " · " + count + " ride(s)" : "") + "</div>" +
        (amount !== null ? '<div class="pw-amount">' + esc(money(amount)) + "</div>" : "");
      box.appendChild(card);
    });
  }
  function loadEarnings() {
    fetch("/api/drivers/me/earnings", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var weeks = j.weeks || j.pay_periods || j.payouts || [];
        renderPayWeeks(weeks);
        var total = pickNumber(j, ["total_earnings", "total", "amount"]);
        $("dd-earnings-sum").textContent = total !== null ? money(total) : "—";
        var list = Array.isArray(j) ? j : (j.earnings || j.rides || j.completed || []);
        var box = $("dd-earnings-list");
        box.innerHTML = "";
        list.forEach(function (r) {
          var route = esc(r.route || "");
          if (!route) {
            route = esc(r.pickup || "");
            if (r.dropoff) route += " → " + esc(r.dropoff);
          }
          var meta = [r.date, r.time].filter(Boolean).join(" · ");
          var rcls = classLabelFor(r);
          if (rcls) meta += (meta ? " · " : "") + rcls;
          if (r.payout_status === "paid" || r.payout_paid === true) {
            meta += (meta ? " · " : "") + "Paid";
          } else if (r.payout_status === "unpaid" || r.payout_paid === false) {
            meta += (meta ? " · " : "") + "Unpaid";
          }
          var div = document.createElement("div");
          div.className = "earn-item";
          /* The driver's own pay for the ride only. */
          var amount = pickNumber(r, ["earnings", "amount", "total_earnings"]);
          div.innerHTML = "<div><div class=\"r\">" + (route || "Ride") + "</div><div class=\"m\">" + esc(meta) + "</div></div>" +
            (amount !== null ? "<div class=\"a\">" + esc(money(amount)) + "</div>" : "");
          box.appendChild(div);
        });
        if (!list.length) {
          show($("dd-earnings-empty"));
        } else {
          hide($("dd-earnings-empty"));
        }
      })
      .catch(function () { /* keep the previous view on a failed check */ });
  }

  /* ---------- Boot ---------- */
  function boot() {
    var token = getToken();
    if (!token) { showSignin(); return; }
    state.token = token;
    fetch("/api/drivers/me", { headers: authHeaders() })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok || !unwrapDriver(res.j)) {
          clearToken();
          showSignin();
          return;
        }
        enterDashboard(unwrapDriver(res.j));
      })
      .catch(function () {
        /* Offline: fall back to sign-in rather than a dead screen. */
        showSignin();
      });
  }
  boot();
})();
