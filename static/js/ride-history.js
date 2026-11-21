/* Noel Chauffer — ride-history lookup (own page).
   Moved verbatim out of static/js/customer.js when the "Your ride
   history" section got its own page (owner, 2026-11-21): customer.js
   is loaded only by the homepage and wires the booking form
   unguarded, so it cannot run here. This file wires only the
   phone-lookup form on /your-ride-history. */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function rideLabel(b) {
    if (!b) return "";
    if (b.ride_type === "hourly") {
      return "By the hour" + (b.hours ? " \u00b7 " + b.hours + " hour(s)" : "") +
        " \u00b7 Pickup: " + (b.pickup || "");
    }
    return (b.pickup || "") + "  \u2192  " + (b.dropoff || "");
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
      awaiting_payment: "Payment needed to confirm your ride",
      offered: "Finding your chauffeur\u2026",
      accepted: "Chauffeur confirmed",
      en_route: "Your chauffeur is on the way",
      arrived: "Your chauffeur has arrived",
      started: "Your ride is under way",
      on_trip: "Your ride is under way",
      in_progress: "Your ride is under way",
      completed: "Ride completed \u2014 thank you",
      cancelled: "This booking was cancelled",
      canceled: "This booking was cancelled",
      no_show: "Marked as a no-show"
    };
    return map[status] || String(status || "");
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
          return '<div class="history-item"><div class="h-top"><div>' +
            '<div class="h-route">' + esc(rideLabel(b)) + "</div>" +
            '<div class="h-meta">' + esc(whenLabel(b)) +
            (b.ride_type === "hourly" ? " · By the hour" : " · One way") +
            (driverName ? " · Chauffeur: " + driverName : "") + "</div>" +
            '<div style="margin-top:6px;"><span class="pill">' + esc(statusLabel(b.status)) + "</span></div>" +
            "</div></div></div>";
        }).join("");
      })
      .catch(function () {
        box.innerHTML = "";
        err.textContent = "Could not reach the booking service. Please try again.";
      });
  });
})();
