/* Noel Chauffer — ride-history lookup.
   Moved verbatim out of static/js/customer.js when the "Your ride
   history" section got its own page (owner, 2026-11-21): customer.js
   is loaded only by the homepage and wires the booking form
   unguarded, so it cannot run here. This file wires only the
   phone-lookup form. Since the homepage restore (owner, 2026-11-22)
   the form lives on the homepage too, so index.html loads this file
   as well as /your-ride-history. */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
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
  /* Language picker (owner decision 2026-11-22): the history page
     header carries its own picker slot. */
  (function initHistoryLangPicker() {
    if (!(window.NoelI18n && window.NoelI18n.buildPicker)) return;
    var slot = $("history-lang-slot");
    if (slot) window.NoelI18n.buildPicker(slot);
  })();
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function rideLabel(b) {
    if (!b) return "";
    if (b.ride_type === "hourly") {
      return T("form.by_hour", "By the hour") + (b.hours ? " \u00b7 " + b.hours + T("class.hour_suffix", " hour(s)") : "") +
        T("status.pickup_prefix", " \u00b7 Pickup: ") + (b.pickup || "");
    }
    return (b.pickup || "") + "  \u2192  " + (b.dropoff || "");
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
    return parts.join(" \u00b7 ");
  }
  function statusLabel(status) {
    var map = {
      awaiting_payment: T("status.awaiting_payment", "Payment needed to confirm your ride"),
      offered: T("status.offered", "Finding your chauffeur\u2026"),
      accepted: T("status.accepted", "Chauffeur confirmed"),
      en_route: T("status.en_route", "Your chauffeur is on the way"),
      arrived: T("status.arrived", "Your chauffeur has arrived"),
      started: T("status.started", "Your ride is under way"),
      on_trip: T("status.on_trip", "Your ride is under way"),
      in_progress: T("status.in_progress", "Your ride is under way"),
      completed: T("status.completed", "Ride completed \u2014 thank you"),
      cancelled: T("status.cancelled", "This booking was cancelled"),
      canceled: T("status.cancelled", "This booking was cancelled"),
      no_show: T("status.no_show", "Marked as a no-show")
    };
    return map[status] || String(status || "");
  }
  /* ---------- Ride history ---------- */
  function renderHistoryList(list, emptyMsg) {
    var box = $("history-results");
    if (!list.length) {
      box.innerHTML = "<p>" + esc(emptyMsg) + "</p>";
      return;
    }
    box.innerHTML = list.map(function (b) {
      var driverName = b.driver && b.driver.name ? esc(b.driver.name) : "";
      return '<div class="history-item"><div class="h-top"><div>' +
        '<div class="h-route">' + esc(rideLabel(b)) + "</div>" +
        '<div class="h-meta">' + esc(whenLabel(b)) +
        " · " + rideTypeLabel(b) +
        (driverName ? T("status.chauffeur_prefix", " · Chauffeur: ") + driverName : "") + "</div>" +
        '<div style="margin-top:6px;"><span class="pill">' + esc(statusLabel(b.status)) + "</span></div>" +
        "</div></div></div>";
    }).join("");
  }
  /* Signed-in customers see their own rides by email (owner
     decision 2026-11-22); the phone lookup below stays for rides
     booked before sign-in existed. */
  (function loadSignedInHistory() {
    var note = $("history-signedin");
    if (!note) return;
    fetch("/api/customers/me")
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!(j && j.signed_in)) return;
        $("history-signedin-email").textContent = j.email;
        note.classList.remove("hidden");
        var box = $("history-results");
        box.innerHTML = "<p>" + esc(T("status.looking_up", "Looking up your rides…")) + "</p>";
        fetch("/api/bookings?email=" + encodeURIComponent(j.email))
          .then(function (r) { return r.json().then(function (jj) { return { ok: r.ok, j: jj }; }); })
          .then(function (res) {
            if (!res.ok) {
              box.innerHTML = "";
              return;
            }
            var list = Array.isArray(res.j) ? res.j : (res.j.bookings || res.j.rides || []);
            renderHistoryList(list, T("status.no_rides_email", "No rides found for this email yet."));
          })
          .catch(function () { box.innerHTML = ""; });
      })
      .catch(function () { /* Not signed in — phone lookup stays. */ });
  })();
  /* The form lives only on the ride-history page (owner 2026-11-22:
     the homepage section was removed); guard so this file stays
     silent on pages without it. */
  var historyForm = $("history-form");
  if (!historyForm) return;
  historyForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var phone = $("history-phone").value.trim();
    var err = $("history-error");
    var box = $("history-results");
    err.textContent = "";
    box.innerHTML = "";
    if (!phone) { err.textContent = T("status.enter_phone", "Please enter your phone number."); return; }
    box.innerHTML = "<p>" + esc(T("status.looking_up", "Looking up your rides…")) + "</p>";
    fetch("/api/bookings?phone=" + encodeURIComponent(phone))
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          box.innerHTML = "";
          err.textContent = (res.j && (res.j.error || res.j.message)) || T("status.lookup_failed", "Could not look up rides for that number.");
          return;
        }
        var list = Array.isArray(res.j) ? res.j : (res.j.bookings || res.j.rides || []);
        renderHistoryList(list, T("status.no_rides_number", "No rides found for that number yet."));
      })
      .catch(function () {
        box.innerHTML = "";
        err.textContent = T("status.reach_booking", "Could not reach the booking service. Please try again.");
      });
  });
})();
