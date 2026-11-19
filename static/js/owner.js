/* Noel Chauffer — owner dashboard logic.
   Every money figure shown here comes from the API. Nothing is
   calculated in this file and no pricing figure is hard-coded. */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }
  function show(el) { el.classList.remove("hidden"); }
  function hide(el) { el.classList.add("hidden"); }
  function money(n) {
    if (n === null || n === undefined || n === "" || isNaN(Number(n))) return "—";
    return "$" + Number(n).toFixed(2);
  }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function pick(obj, keys) {
    for (var i = 0; i < keys.length; i++) {
      if (obj && obj[keys[i]] !== null && obj[keys[i]] !== undefined) return obj[keys[i]];
    }
    return null;
  }
  function asList(j, key) {
    if (Array.isArray(j)) return j;
    if (j && Array.isArray(j[key])) return j[key];
    return [];
  }
  function maskBank(value) {
    var s = String(value || "");
    if (!s) return "—";
    if (s.indexOf("•") !== -1 || s.indexOf("*") !== -1) return s;
    var digits = s.replace(/\D/g, "");
    if (!digits) return "Saved";
    if (digits.length <= 4) return "••••" + digits;
    return "••••" + digits.slice(-4);
  }
  function whenLabel(b) {
    return [b.date, b.time].filter(Boolean).join(" · ");
  }

  /* ---------- Session check + PIN login ---------- */
  function checkSession() {
    fetch("/api/owner/summary", { credentials: "same-origin" })
      .then(function (r) {
        if (r.ok) return r.json().then(function (j) { enterDashboard(j); });
        show($("pin-gate"));
        hide($("dashboard"));
      })
      .catch(function () { show($("pin-gate")); hide($("dashboard")); });
  }

  $("pin-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("pin-error");
    err.textContent = "";
    var pin = $("pin-input").value.trim();
    if (!pin) { err.textContent = "Please enter your PIN."; return; }
    var btn = $("pin-submit");
    btn.disabled = true;
    fetch("/api/owner/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ pin: pin })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }).catch(function () { return { ok: r.ok, j: {} }; }); })
      .then(function (res) {
        btn.disabled = false;
        if (!res.ok) {
          err.textContent = "Wrong PIN. Please try again.";
          $("pin-input").value = "";
          $("pin-input").focus();
          return;
        }
        $("pin-input").value = "";
        loadSummaryThenEnter();
      })
      .catch(function () {
        btn.disabled = false;
        err.textContent = "Could not reach the service. Please try again.";
      });
  });

  function loadSummaryThenEnter() {
    fetch("/api/owner/summary", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) { enterDashboard(j); })
      .catch(function () { enterDashboard({}); });
  }

  function enterDashboard(summary) {
    hide($("pin-gate"));
    show($("dashboard"));
    renderSummary(summary);
    runPickupReminders();
    loadBookings();
    loadPayouts();
    loadAlerts();
    loadOutbox();
    loadSupportMessages();
    loadDrivers();
    loadDriverReferrals();
    loadDocumentFlags();
    runExpiryAlerts();
    loadExpiringDocuments();
  }

  /* 1-hour pickup reminder trigger (owner decision 2026-11-18):
     when the dashboard loads, run the reminder check for every
     driver (fire-and-forget, silent) so reminders queue whenever
     the owner has the dashboard open — no cron, no new
     infrastructure. The check is idempotent; the outbox and alerts
     reload afterwards so queued reminders show at once. */
  function runPickupReminders() {
    fetch("/api/owner/run-pickup-reminders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: "{}"
    })
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function () { loadOutbox(); loadAlerts(); })
      .catch(function () { /* reminders never break the dashboard */ });
  }

  /* 10-day document expiry alerts (owner decision 2026-11-19):
     same fire-and-forget pattern as the pickup reminders — run the
     check when the dashboard loads, then reload the outbox and the
     expiring-documents list so queued alerts show at once. */
  function runExpiryAlerts() {
    fetch("/api/owner/run-expiry-alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: "{}"
    })
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function () { loadOutbox(); loadExpiringDocuments(); })
      .catch(function () { /* expiry alerts never break the dashboard */ });
  }

  /* ---------- Documents expiring soon ---------- */
  /* Owner decision 2026-11-19: every stored document expiring
     within 10 days, plus expired ones (registration paused).
     Read-only information — no action, no approval step. */
  function loadExpiringDocuments() {
    fetch("/api/owner/expiring-documents", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "documents");
        var feed = $("expiry-feed");
        if (!list.length) { feed.innerHTML = '<div class="empty">No documents expiring in the next 10 days.</div>'; return; }
        feed.innerHTML = list.map(function (d) {
          var who = [d.driver_name, d.phone].filter(Boolean).join(" · ") || "Unknown driver";
          var when = d.days_left < 0
            ? "Expired " + esc(d.expires_on) + " — registration paused"
            : d.days_left === 0 ? "Expires today"
            : d.days_left === 1 ? "Expires tomorrow"
            : "Expires in " + d.days_left + " days";
          return '<div class="feed-item"><div class="ch">' + (d.status === "expired" ? "Expired" : "Expiring soon") + "</div>" +
            '<div class="body"><strong>' + esc(d.label || d.doc_type || "") + "</strong> — " + esc(when) +
            "<br>" + esc(who) +
            (d.alert_sent ? ' · <span class="ch">Driver alerted</span>' : "") + "</div>" +
            '<div class="t">' + esc(d.expires_on || "") + "</div></div>";
        }).join("");
      })
      .catch(function () { $("expiry-feed").innerHTML = '<div class="empty">Could not load expiring documents.</div>'; });
  }

  $("logout-btn").addEventListener("click", function () {
    fetch("/api/owner/logout", { method: "POST", credentials: "same-origin" })
      .then(function () { window.location.reload(); })
      .catch(function () { window.location.reload(); });
  });

  /* ---------- PIN re-confirmation (owner decision 2026-11-19) ----------
     Every clear/remove action asks for the PIN again at that moment.
     The PIN is sent to the server with the action and checked there
     (require_owner_pin); a signed-in session alone is never enough.
     A wrong PIN leaves everything exactly as it was. */
  var pinConfirmAction = null;
  function openPinConfirm(title, text, action) {
    pinConfirmAction = action;
    $("pin-confirm-title").textContent = title;
    $("pin-confirm-text").textContent = text;
    $("pin-confirm-error").textContent = "";
    $("pin-confirm-input").value = "";
    show($("pin-confirm-modal"));
    $("pin-confirm-input").focus();
  }
  function closePinConfirm() {
    pinConfirmAction = null;
    hide($("pin-confirm-modal"));
  }
  $("pin-confirm-cancel").addEventListener("click", closePinConfirm);
  $("pin-confirm-modal").addEventListener("click", function (e) {
    if (e.target === $("pin-confirm-modal")) closePinConfirm();
  });
  $("pin-confirm-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var pin = $("pin-confirm-input").value.trim();
    if (!pin) { $("pin-confirm-error").textContent = "Please enter your PIN."; return; }
    var action = pinConfirmAction;
    if (!action) { closePinConfirm(); return; }
    /* The action posts the PIN and reports a wrong PIN back; the
       modal stays open so the owner can retry. */
    action(pin, function (wrongPin) {
      if (wrongPin) {
        $("pin-confirm-error").textContent = "Wrong PIN. Nothing was cleared or removed.";
        $("pin-confirm-input").value = "";
        $("pin-confirm-input").focus();
      } else {
        closePinConfirm();
      }
    });
  });

  /* POST a PIN-guarded destructive action. done receives
     { ok, status, j }; status 401 means the PIN was wrong. */
  function postWithPin(url, pin, done) {
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ pin: pin })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, j: j }; }).catch(function () { return { ok: r.ok, status: r.status, j: {} }; }); })
      .then(function (res) { done(res); })
      .catch(function () { done({ ok: false, status: 0, j: {} }); });
  }

  /* ---------- Clear all rides (TEMPORARY TEST-ONLY: remove before real launch) ---------- */
  $("clear-rides-btn").addEventListener("click", function () {
    openPinConfirm("Enter PIN to clear all rides",
      "This deletes every ride on the account — every booking, chat message, alert and outbox message. Drivers and their documents are kept. This cannot be undone.",
      function (pin, finish) {
        var btn = $("clear-rides-btn");
        btn.disabled = true;
        postWithPin("/api/owner/clear-rides", pin, function (res) {
          btn.disabled = false;
          if (res.status === 401) { finish(true); return; }
          finish(false);
          if (!res.ok) return;
          hide($("booking-detail"));
          $("booking-detail").innerHTML = "";
          loadSummaryThenEnterSoft();
          loadBookings();
          loadPayouts();
          loadAlerts();
          loadOutbox();
        });
      });
  });

  /* ---------- Remove all drivers (TEMPORARY TEST-ONLY: remove before real launch) ---------- */
  $("clear-drivers-btn").addEventListener("click", function () {
    openPinConfirm("Enter PIN to remove all drivers",
      "This removes every driver registration, document and profile photo. Ride history is kept, but bookings will no longer show a driver. Drivers must re-register. This cannot be undone.",
      function (pin, finish) {
        var btn = $("clear-drivers-btn");
        btn.disabled = true;
        postWithPin("/api/owner/clear-drivers", pin, function (res) {
          btn.disabled = false;
          if (res.status === 401) { finish(true); return; }
          finish(false);
          if (!res.ok) return;
          var d = res.j.deleted || {};
          window.alert("Removed " + (d.drivers || 0) + " driver(s), " + (d.documents || 0) + " document(s) and " + (d.booking_exclusions || 0) + " exclusion(s). " + (d.bookings_unlinked || 0) + " booking(s) unlinked. Ride history was kept.");
          loadSummaryThenEnterSoft();
          loadBookings();
          loadPayouts();
          loadAlerts();
          loadOutbox();
          loadDrivers();
        });
      });
  });

  /* ---------- Remove ONE driver (owner decision 2026-11-19) ---------- */
  function removeDriver(d) {
    openPinConfirm("Enter PIN to remove driver",
      "Remove " + (d.name || "this driver") + "? This deletes the driver registration, documents and profile photo. Ride history is kept, but bookings will no longer show this driver. The driver must re-register. This cannot be undone.",
      function (pin, finish) {
        postWithPin("/api/owner/drivers/" + encodeURIComponent(d.id) + "/remove", pin, function (res) {
          if (res.status === 401) { finish(true); return; }
          finish(false);
          if (!res.ok) return;
          loadDrivers();
          loadBookings();
          loadSummaryThenEnterSoft();
        });
      });
  }

  /* ---------- Remove ONE ride (owner decision 2026-11-19) ---------- */
  function removeBooking(b) {
    openPinConfirm("Enter PIN to remove ride",
      "Remove ride #" + b.id + " (" + (b.route || "") + ")? This deletes the booking and its messages. Drivers are kept. This cannot be undone.",
      function (pin, finish) {
        postWithPin("/api/owner/bookings/" + encodeURIComponent(b.id) + "/remove", pin, function (res) {
          if (res.status === 401) { finish(true); return; }
          finish(false);
          if (!res.ok) return;
          hide($("booking-detail"));
          $("booking-detail").innerHTML = "";
          loadBookings();
          loadSummaryThenEnterSoft();
        });
      });
  }

  /* ---------- Summary ---------- */
  function renderSummary(s) {
    s = s || {};
    var inner = s.summary || s;
    $("sum-gross").textContent = money(pick(inner, ["gross", "gross_revenue", "revenue", "total_collected"]));
    $("sum-profit").textContent = money(pick(inner, ["profit", "net_profit", "total_profit"]));
    $("sum-owed").textContent = money(pick(inner, ["driver_owed", "driver_payable", "owed_to_drivers", "unpaid_driver_earnings"]));
    var rides = pick(inner, ["ride_count", "rides", "total_rides", "booking_count", "bookings"]);
    var counts = inner.counts || {};
    if ((rides === null || rides === undefined) && counts && typeof counts === "object") {
      /* The API returns per-status counts: total them for the Rides card. */
      var total = 0;
      Object.keys(counts).forEach(function (k) { total += Number(counts[k]) || 0; });
      rides = total;
    }
    $("sum-rides").textContent = (rides === null || rides === undefined) ? "—" : String(rides);
    var bits = [];
    var completed = pick(inner, ["completed", "completed_rides"]);
    if (completed === null && counts.completed !== undefined) completed = counts.completed;
    var cancelled = pick(inner, ["cancelled", "cancelled_rides"]);
    if (cancelled === null && counts.cancelled !== undefined) cancelled = counts.cancelled;
    var active = pick(inner, ["active", "active_rides", "upcoming"]);
    if (active === null && counts) {
      var n = 0;
      ["awaiting_payment", "offered", "accepted", "en_route", "arrived", "in_progress"].forEach(function (k) {
        n += Number(counts[k]) || 0;
      });
      active = n;
    }
    if (completed !== null) bits.push(completed + " completed");
    if (active !== null) bits.push(active + " active");
    if (cancelled !== null) bits.push(cancelled + " cancelled");
    $("sum-rides-hint").textContent = bits.join(" · ");
  }

  /* ---------- Bookings table ---------- */
  function breakdownFields(b) {
    var inv = b.invoice || {};
    return {
      paid: pick(b, ["customer_paid", "total", "amount", "customer_total", "charged"]),
      fare: pick(b, ["fare", "fare_amount", "base_fare"]),
      driver: pick(b, ["driver_share", "driver_earnings", "driver_pay", "driver_amount"]),
      toll: pick(b, ["toll", "toll_amount"]) !== null ? pick(b, ["toll", "toll_amount"]) : pick(inv, ["toll"]),
      waiting: pick(b, ["waiting_charge", "waiting"]) !== null ? pick(b, ["waiting_charge", "waiting"]) : pick(inv, ["waiting_charge"]),
      extra: pick(b, ["extra_distance_charge", "extra_distance"]) !== null ? pick(b, ["extra_distance_charge", "extra_distance"]) : pick(inv, ["extra_distance_charge"]),
      profit: pick(b, ["profit", "owner_profit", "net"]),
      referral_discount: pick(b, ["referral_discount"])
    };
  }

  /* ---------- Bookings table: server-side search + pages ----------
     At 10,000 rides the dashboard must NOT load every booking at
     once (owner decision 2026-11-19). The list loads 50 rows at a
     time, newest first, and the search box queries the server
     (GET /api/owner/bookings?q=…&page=…), debounced 300 ms as the
     owner types — finding one trip among thousands is instant,
     with no scrolling through rides. */
  var bookingsPage = 1;
  var bookingsQuery = "";
  var bookingsTotalPages = 1;
  var bookingsTotal = 0;
  var bookingsSearchTimer = null;
  var BOOKINGS_PER_PAGE = 50;

  function bookingsUrl() {
    var url = "/api/owner/bookings?page=" + bookingsPage + "&per_page=" + BOOKINGS_PER_PAGE;
    if (bookingsQuery) url += "&q=" + encodeURIComponent(bookingsQuery);
    return url;
  }

  function renderBookingsPager() {
    var pager = $("bookings-pager");
    if (!pager) return;
    if (bookingsTotal === 0) { hide(pager); return; }
    show(pager);
    $("bookings-page-info").textContent =
      "Page " + bookingsPage + " of " + Math.max(bookingsTotalPages, 1) +
      " · " + bookingsTotal + " ride" + (bookingsTotal === 1 ? "" : "s");
    $("bookings-prev").disabled = bookingsPage <= 1;
    $("bookings-next").disabled = bookingsPage >= bookingsTotalPages;
  }

  function loadBookings() {
    fetch(bookingsUrl(), { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "bookings");
        if (j && typeof j === "object" && !Array.isArray(j)) {
          bookingsTotal = Number(j.total) || 0;
          bookingsTotalPages = Number(j.pages) || 1;
          /* The server clamps an out-of-range page; follow it. */
          if (j.page && Number(j.page) !== bookingsPage) bookingsPage = Number(j.page);
        }
        var body = $("bookings-body");
        body.innerHTML = "";
        if (!list.length) {
          show($("bookings-empty"));
          $("bookings-empty").textContent = bookingsQuery
            ? "No rides match that search."
            : "No bookings yet.";
          renderBookingsPager();
          return;
        }
        hide($("bookings-empty"));
        list.forEach(function (b) {
          var f = breakdownFields(b);
          var driverName = (b.driver && b.driver.name) || b.driver_name ||
            (b.assigned_driver_name ? "Assigned: " + b.assigned_driver_name : "—");
          /* The API returns the ready-made `route` string on list rows. */
          var route = b.route ? esc(b.route) : (esc(b.pickup || "") + (b.dropoff ? " → " + esc(b.dropoff) : ""));
          var tr = document.createElement("tr");
          var classBit = b.vehicle_class_label ? " · " + esc(b.vehicle_class_label) : "";
          tr.innerHTML =
            "<td>" + route + '<div class="sub">' + esc(whenLabel(b)) +
            (b.ride_type === "hourly" ? " · By the hour" + (b.hours ? " · " + b.hours + " h" : "") : classBit) + "</div></td>" +
            "<td>" + esc(b.customer_name || b.name || "—") + '<div class="sub">' + esc(b.phone || "") + "</div></td>" +
            "<td>" + esc(driverName) + "</td>" +
            '<td><span class="pill">' + esc(b.status || "") + "</span></td>" +
            '<td class="num">' + esc(money(f.paid)) + "</td>" +
            '<td class="num">' + esc(money(f.fare)) + "</td>" +
            '<td class="num">' + esc(money(f.driver)) + "</td>" +
            '<td class="num">' + esc(money(f.toll)) + "</td>" +
            '<td class="num">' + esc(money(f.waiting)) + "</td>" +
            '<td class="num">' + esc(money(f.extra)) + "</td>" +
            '<td class="num">' + esc(money(f.profit)) + "</td>" +
            "<td><input class=\"toll-input\" type=\"number\" min=\"0\" step=\"0.01\" value=\"" +
            esc(f.toll !== null && f.toll !== undefined ? f.toll : "") +
            "\" aria-label=\"Toll for this ride\"><button class=\"toll-save\" type=\"button\">Save</button></td>" +
            "<td><button class=\"row-btn\" type=\"button\">View</button>" +
            "<button class=\"row-btn danger-row-btn ride-remove-btn\" type=\"button\">Remove</button></td>";
          tr.querySelector(".toll-save").addEventListener("click", function () {
            var val = tr.querySelector(".toll-input").value;
            saveToll(b.id, val, tr);
          });
          tr.querySelector(".row-btn").addEventListener("click", function () { loadBookingDetail(b.id); });
          tr.querySelector(".ride-remove-btn").addEventListener("click", function () { removeBooking(b); });
          body.appendChild(tr);
        });
        renderBookingsPager();
      })
      .catch(function () {
        $("bookings-body").innerHTML = "";
        show($("bookings-empty"));
        $("bookings-empty").textContent = "Could not load bookings.";
        renderBookingsPager();
      });
  }

  /* Search as he types (300 ms debounce) + page buttons. A new
     search always starts back on page 1. */
  $("bookings-search").addEventListener("input", function () {
    clearTimeout(bookingsSearchTimer);
    bookingsSearchTimer = setTimeout(function () {
      bookingsQuery = $("bookings-search").value.trim();
      bookingsPage = 1;
      loadBookings();
    }, 300);
  });
  $("bookings-prev").addEventListener("click", function () {
    if (bookingsPage <= 1) return;
    bookingsPage -= 1;
    loadBookings();
  });
  $("bookings-next").addEventListener("click", function () {
    if (bookingsPage >= bookingsTotalPages) return;
    bookingsPage += 1;
    loadBookings();
  });

  function saveToll(id, value, row) {
    var toll = value === "" ? 0 : Number(value);
    if (isNaN(toll) || toll < 0) return;
    fetch("/api/owner/bookings/" + encodeURIComponent(id) + "/toll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ toll: toll })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok) { loadBookings(); loadSummaryThenEnterSoft(); }
      })
      .catch(function () { /* leave the row as it was */ });
  }
  function loadSummaryThenEnterSoft() {
    fetch("/api/owner/summary", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) { renderSummary(j); })
      .catch(function () { /* ignore */ });
  }

  /* ---------- Driver payouts (weekly tallies, each due 14 days after its week starts) ---------- */
  function loadPayouts() {
    fetch("/api/owner/payouts", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "payouts");
        var body = $("payouts-body");
        body.innerHTML = "";
        if (!list.length) { show($("payouts-empty")); return; }
        hide($("payouts-empty"));
        list.forEach(function (p) {
          var paid = p.paid === true || p.status === "paid";
          var driverName = p.driver_name || "Driver";
          var tr = document.createElement("tr");
          tr.innerHTML =
            "<td>" + esc(driverName) + '<div class="sub">' + esc(p.driver_phone || "") + "</div></td>" +
            "<td>" + esc((p.start || "") + " – " + (p.end || "")) + "</td>" +
            "<td>" + esc(p.due_date || "") + "</td>" +
            '<td class="num">' + esc(String(pick(p, ["ride_count", "rides"]) || 0)) + "</td>" +
            '<td class="num">' + esc(money(pick(p, ["total_earnings", "total", "amount"]))) + "</td>" +
            '<td><span class="pill">' + (paid ? "Paid" : "Unpaid") + "</span></td>" +
            "<td>" + (paid ? "" : '<button class="row-btn" type="button">Mark paid</button>') + "</td>";
          if (!paid) {
            tr.querySelector(".row-btn").addEventListener("click", function () {
              markPayoutPaid(p, driverName, tr);
            });
          }
          body.appendChild(tr);
        });
      })
      .catch(function () {
        $("payouts-body").innerHTML = "";
        show($("payouts-empty"));
        $("payouts-empty").textContent = "Could not load payouts.";
      });
  }

  function markPayoutPaid(p, driverName, row) {
    var label = (p.start || "") + " to " + (p.end || "");
    if (!window.confirm("Mark the week " + label + " paid for " + driverName + "?")) return;
    var btn = row.querySelector(".row-btn");
    if (btn) btn.disabled = true;
    fetch("/api/owner/payouts/mark-paid", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ driver_id: p.driver_id, week_index: p.index })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok) { loadPayouts(); loadSummaryThenEnterSoft(); loadBookings(); }
        else if (btn) { btn.disabled = false; }
      })
      .catch(function () { if (btn) btn.disabled = false; });
  }

  /* ---------- Booking detail ---------- */
  function loadBookingDetail(id) {
    fetch("/api/owner/bookings/" + encodeURIComponent(id), { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var b = j.booking || j;
        var f = breakdownFields(b);
        var driver = b.driver || {};
        var panel = $("booking-detail");
        var rows = [
          ["Booking", "#" + (b.id || "")],
          ["Status", b.status || "—"],
          ["Pickup", b.pickup || "—"],
          ["Drop-off", b.dropoff || (b.ride_type === "hourly" ? "By the hour" : "—")],
          ["Date / time", whenLabel(b) || "—"],
          ["Ride type", b.ride_type === "hourly" ? "By the hour" + (b.hours ? " · " + b.hours + " hour(s)" : "") : "One way"],
          ["Vehicle class", b.vehicle_class_label || "—"],
          ["Flight", b.flight_number ? (b.flight_number + (b.airline_name ? " · " + b.airline_name : "") + (b.terminal ? " · " + b.terminal : "")) : "—"],
          ["Customer", b.customer_name || b.name || "—"],
          ["Customer phone", b.phone || b.customer_phone || "—"],
          ["Customer email", b.email || b.customer_email || "—"],
          ["Referral code", b.referral_code_used || b.referral_code || "—"],
          ["Referral discount", money(f.referral_discount)],
          ["Driver", driver.name || b.driver_name || "—"],
          ["Driver phone", driver.phone || "—"],
          ["Car", [driver.car_year, driver.car_model, driver.car_colour].filter(Boolean).join(" · ") || "—"],
          ["Plate", driver.plate || "—"],
          ["Customer paid", money(f.paid)],
          ["Fare", money(f.fare)],
          ["Driver share", money(f.driver)],
          ["Toll", money(f.toll)],
          ["Waiting charge", money(f.waiting)],
          ["Extra miles", (b.extra_miles !== null && b.extra_miles !== undefined) ? String(b.extra_miles) : "—"],
          ["Extra distance charge", money(f.extra)],
          ["Assigned driver", b.assigned_driver_name || "— (broadcast to all matching drivers)"],
          ["Profit", money(f.profit)]
        ];
        panel.innerHTML = "<h3>Booking detail</h3><div class=\"detail-grid\">" +
          rows.map(function (r) {
            return "<div><div class=\"k\">" + esc(r[0]) + "</div><div>" + esc(r[1]) + "</div></div>";
          }).join("") + "</div>";
        /* Emergency cancels inside the 2-hour window (owner decision
           2026-11-18): read-only information — reason, automatic
           judgment, suspension or not. No action required, no
           approval step. */
        if (Array.isArray(b.emergency_cancels) && b.emergency_cancels.length) {
          var ecBox = document.createElement("div");
          ecBox.className = "emergency-cancels";
          var ecHtml = "<h4>Emergency cancels</h4>";
          b.emergency_cancels.forEach(function (c) {
            ecHtml += "<div class=\"emergency-cancel\">" +
              "<div><strong>" + esc(c.driver_name || "Driver") + "</strong> — " + esc(c.created_at || "") + "</div>" +
              "<div>Reason: " + esc(c.reason_label || c.reason || "") + (c.detail ? " — " + esc(c.detail) : "") + "</div>" +
              "<div>Automatic judgment: " + esc(c.judgment || "") +
              (c.flagged ? " (flagged for owner review)" : "") + "</div>" +
              "<div>" + (c.suspended_until ? "Driver app blocked until " + esc(c.suspended_until) : "No suspension") + "</div>" +
              "</div>";
          });
          ecBox.innerHTML = ecHtml;
          panel.appendChild(ecBox);
        }
        /* Dispatcher-lite: on a paid booking still waiting for a
           driver, the owner can assign it to one specific driver —
           or clear the assignment to broadcast it again. */
        if (b.status === "offered") {
          var assignBox = document.createElement("div");
          assignBox.className = "assign-box";
          var sel = document.createElement("select");
          sel.setAttribute("aria-label", "Assign to a driver");
          var none = document.createElement("option");
          none.value = "";
          none.textContent = "Choose a driver…";
          sel.appendChild(none);
          (allDrivers || []).forEach(function (d) {
            var opt = document.createElement("option");
            opt.value = String(d.id);
            opt.textContent = d.name + " — " + (d.car_model || d.car || "") + (d.vehicle_class_label ? " (" + d.vehicle_class_label + ")" : "");
            if (b.assigned_driver_id && Number(b.assigned_driver_id) === Number(d.id)) opt.selected = true;
            sel.appendChild(opt);
          });
          var assignBtn = document.createElement("button");
          assignBtn.className = "row-btn";
          assignBtn.type = "button";
          assignBtn.textContent = "Assign to this driver";
          assignBtn.addEventListener("click", function () {
            if (!sel.value) return;
            assignBooking(b.id, Number(sel.value));
          });
          assignBox.appendChild(sel);
          assignBox.appendChild(assignBtn);
          if (b.assigned_driver_id) {
            var clearBtn = document.createElement("button");
            clearBtn.className = "row-btn";
            clearBtn.type = "button";
            clearBtn.textContent = "Clear assignment (broadcast again)";
            clearBtn.addEventListener("click", function () { assignBooking(b.id, null); });
            assignBox.appendChild(clearBtn);
          }
          panel.appendChild(assignBox);
        }
        show(panel);
        panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      })
      .catch(function () { /* leave the previous detail view */ });
  }

  function assignBooking(id, driverId) {
    fetch("/api/owner/bookings/" + encodeURIComponent(id) + "/assign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ driver_id: driverId })
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok) { loadBookings(); loadBookingDetail(id); }
      })
      .catch(function () { /* leave the detail view as it was */ });
  }

  /* ---------- Alerts ---------- */
  function loadAlerts() {
    fetch("/api/owner/alerts", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "alerts");
        var feed = $("alerts-feed");
        if (!list.length) { feed.innerHTML = '<div class="empty">No alerts yet.</div>'; return; }
        feed.innerHTML = list.map(function (a) {
          var text = a.message || a.text || a.event || a.type || "";
          var when = a.created_at || a.timestamp || a.time || "";
          var ref = a.booking_id ? " · Booking #" + a.booking_id : "";
          return '<div class="feed-item"><div>' + esc(text) + '</div><div class="t">' + esc(when) + esc(ref) + "</div></div>";
        }).join("");
      })
      .catch(function () { $("alerts-feed").innerHTML = '<div class="empty">Could not load alerts.</div>'; });
  }

  /* ---------- Outbox ---------- */
  function loadOutbox() {
    fetch("/api/owner/outbox", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "messages");
        if (!list.length) list = asList(j, "outbox");
        var feed = $("outbox-feed");
        if (!list.length) { feed.innerHTML = '<div class="empty">No messages recorded yet.</div>'; return; }
        feed.innerHTML = list.map(function (m) {
          var channel = m.channel || m.type || "Message";
          var to = m.recipient || m.to || m.phone || m.email || "";
          var when = m.created_at || m.timestamp || m.time || "";
          var body = m.body || m.message || m.text || "";
          var subject = m.subject ? "<div><strong>" + esc(m.subject) + "</strong></div>" : "";
          var state = m.sent_at ? "Sent" : "Queued";
          return '<div class="feed-item"><div class="ch">' + esc(channel) + (to ? " → " + esc(to) : "") + " · " + state + "</div>" +
            subject + '<div class="body">' + esc(body) + '</div><div class="t">' + esc(when) + "</div></div>";
        }).join("");
      })
      .catch(function () { $("outbox-feed").innerHTML = '<div class="empty">Could not load the outbox.</div>'; });
  }

  /* ---------- Support messages ---------- */
  function loadSupportMessages() {
    fetch("/api/owner/support-messages", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "messages");
        var feed = $("support-feed");
        if (!list.length) { feed.innerHTML = '<div class="empty">No support messages yet.</div>'; return; }
        feed.innerHTML = list.map(function (m) {
          var flag = m.flagged ? '<div class="ch">Needs attention</div>' : "";
          var when = m.created_at || "";
          return '<div class="feed-item">' + flag +
            '<div class="body">' + esc(m.text || "") + '</div><div class="t">' + esc(when) + "</div></div>";
        }).join("");
      })
      .catch(function () { $("support-feed").innerHTML = '<div class="empty">Could not load support messages.</div>'; });
  }

  /* ---------- Driver referrals ---------- */
  /* Owner decision 2026-11-18: who referred whom, jobs counted (out
     of each referred driver's first 15), and dollars earned.
     Read-only information — no action, no approval step. */
  function loadDriverReferrals() {
    fetch("/api/owner/driver-referrals", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "referrals");
        var feed = $("referrals-feed");
        if (!list.length) { feed.innerHTML = '<div class="empty">No driver referrals yet.</div>'; return; }
        var total = pick(j, ["total_earned"]);
        var jobs = pick(j, ["total_jobs_counted"]);
        var head = "";
        if (total !== undefined && total !== null) {
          head = '<div class="feed-item"><div class="body">Total referral earnings: <strong>' +
            esc(money(total)) + "</strong>" +
            (jobs !== undefined && jobs !== null ? " · " + esc(String(jobs)) + " rides counted" : "") +
            "</div></div>";
        }
        feed.innerHTML = head + list.map(function (r) {
          var when = r.registered_at || "";
          return '<div class="feed-item">' +
            '<div class="body"><strong>' + esc(r.referrer_name || "Driver") + "</strong> → " +
            esc(r.referred_driver_name || "Driver") + " — " +
            esc(String(r.jobs_counted)) + " of 15 rides · " + esc(money(r.earned)) + "</div>" +
            (when ? '<div class="t">Registered ' + esc(when) + "</div>" : "") + "</div>";
        }).join("");
      })
      .catch(function () { $("referrals-feed").innerHTML = '<div class="empty">Could not load driver referrals.</div>'; });
  }

  /* ---------- Flagged documents ---------- */
  /* Owner decision 2026-11-19: registration attempts rejected by
     the duplicate, photo-sanity or expiry checks. Read-only
     information — no action, no approval step. */
  function loadDocumentFlags() {
    fetch("/api/owner/document-flags", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "flags");
        var feed = $("flags-feed");
        if (!list.length) { feed.innerHTML = '<div class="empty">No flagged documents yet.</div>'; return; }
        var reasons = {
          duplicate_other_driver: "Same photo already used on another driver account",
          duplicate_same_driver: "Same photo in two document slots",
          blank_photo: "Photo looks blank or unreadable",
          tiny_photo: "Photo too small",
          unreadable_photo: "Photo could not be read",
          expired: "Document expired",
          missing_expiry: "No expiry date given",
          invalid_expiry: "Expiry date not readable"
        };
        feed.innerHTML = list.map(function (f) {
          var when = f.created_at || "";
          var who = [f.name, f.phone].filter(Boolean).join(" · ") || "Unknown driver";
          return '<div class="feed-item"><div class="ch">Needs attention</div>' +
            '<div class="body"><strong>' + esc(reasons[f.reason] || f.reason || "Flagged") + "</strong> — " +
            esc(f.doc_label || f.doc_type || "") + "<br>" + esc(who) +
            (f.detail ? " · " + esc(f.detail) : "") + '</div>' +
            (when ? '<div class="t">' + esc(when) + "</div>" : "") + "</div>";
        }).join("");
      })
      .catch(function () { $("flags-feed").innerHTML = '<div class="empty">Could not load flagged documents.</div>'; });
  }

  /* ---------- Drivers + document viewer ---------- */
  /* The drivers list is kept for the dispatcher-lite assign control
     in the booking detail panel. */
  var allDrivers = [];
  /* Document types as the API returns them in `docs` (status strings)
     and `doc_ids` (row ids for the viewer). The profile picture has no
     document row: it is served from the driver photo endpoint. The
     New York list comes first; the items only other states require
     follow. Only the types present in a driver's own `docs` get a
     chip, so every driver shows exactly his state's list. */
  var DOC_TYPES = [
    { key: "profile_picture", label: "Profile Picture", photo: true },
    { key: "dmv_license", label: "DMV driving license" },
    { key: "tlc_license", label: "TLC License" },
    { key: "fh1_insurance", label: "FH-1 Insurance Card" },
    { key: "registration", label: "Commercial Vehicle Registration" },
    { key: "inspection", label: "NYS DMV Inspection" },
    { key: "vehicle_permit", label: "TLC-for-hire Vehicle Permit" },
    { key: "nj_qualification", label: "MVC Letter of Qualification" },
    { key: "nj_municipal_license", label: "Municipal License to Operate" },
    { key: "nj_limo_registration", label: "Limousine Vehicle Registration" },
    { key: "nj_insurance", label: "Insurance Certificate" },
    { key: "vehicle_registration", label: "Vehicle Registration" },
    { key: "insurance_card", label: "Insurance Card" },
    { key: "al_certificate", label: "Certificate of Intrastate Authority (APSC)" },
    { key: "al_form_e", label: "Form E (Insurance Filing)" },
    { key: "ca_tcp_permit", label: "Charter-Party Carrier (TCP) Certificate/Permit (Class A, B or P)" },
    { key: "ca_driver_statement", label: "Driver Statement of Application (Form PL739-A)" },
    { key: "ca_commercial_registration", label: "Commercial Vehicle Registration (Form PL664)" },
    { key: "ca_inspection_declaration", label: "Vehicle Inspection Declaration (Form PL668)" },
    { key: "co_ll_permit", label: "Luxury Limousine (LL) Permit" },
    { key: "co_inspection", label: "Vehicle Inspection" },
    { key: "co_form_e", label: "Form E (Insurance Filing)" },
    { key: "ct_livery_permit", label: "Livery Permit (CT DOT)" },
    { key: "de_certificate", label: "Certificate of Public Convenience and Necessity" },
    { key: "de_limo_registration", label: "Limousine Registration" },
    { key: "de_inspection", label: "Vehicle Inspection" },
    { key: "dc_drivers_record", label: "Driver's Record" },
    { key: "dc_ssc", label: "Social Security Card" },
    { key: "dc_residency", label: "Proof of Residency" },
    { key: "dc_medical_form", label: "Medical History / Physical Examination Form" },
    { key: "dc_face_id", label: "For-Hire Operators (Face ID) License" },
    { key: "dc_public_vehicle_license", label: "Public Vehicle-for-Hire License" },
    { key: "dc_inspection", label: "DMV Inspection" },
    { key: "ga_carrier_certificate", label: "Limousine Carrier Certificate (Georgia DPS)" },
    { key: "ga_insurance_certificate", label: "Certificate of Insurance" },
    { key: "hi_carrier_certificate", label: "Motor Carrier Certificate / Permit (Form 92-001)" },
    { key: "hi_vehicle_inventory", label: "Vehicle Inventory List (Exhibit B)" },
    { key: "hi_tax_clearance", label: "Tax Clearance Certificate" },
    { key: "ks_certificate", label: "Certificate of Convenience and Necessity (KCC)" },
    { key: "ky_limousine_certificate", label: "Limousine Certificate" },
    { key: "ky_vehicle_license", label: "Motor Carrier Vehicle License" },
    { key: "ky_inspection", label: "Vehicle Inspection" },
    { key: "me_registration", label: "Vehicle Registration with HIRE Plates (Class TX)" },
    { key: "me_jb_filing", label: "Insurance Certificate for For-Hire Passenger Vehicle (JB Filing)" },
    { key: "md_for_hire_license", label: "Passenger-for-Hire Driver's License (PSC)" },
    { key: "md_inspection_certificate", label: "Vehicle Inspection Certificate" },
    { key: "mi_carrier_license", label: "Limousine Carrier License" },
    { key: "mn_permit", label: "Limousine Service Permit (MnDOT)" },
    { key: "mn_inspection", label: "Vehicle Inspection" },
    { key: "mn_form_e", label: "Form E (Insurance Filing)" },
    { key: "mo_authority", label: "Motor Carrier Operating Authority (MoDOT)" },
    { key: "ne_medical_certificate", label: "Medical Certificate" },
    { key: "ne_carrier_authority", label: "Common / Contract Carrier Authority (PSC)" },
    { key: "nv_drivers_permit", label: "Driver's Permit (NTA)" },
    { key: "nv_cpcn", label: "Certificate of Public Convenience and Necessity (CPCN)" },
    { key: "nm_inspection", label: "Vehicle Inspection" },
    { key: "oh_livery_registration", label: "Vehicle Registration (Livery Plates)" },
    { key: "pa_driving_history", label: "Driving History (3-Year Record)" },
    { key: "pa_criminal_history", label: "Criminal History Record" },
    { key: "pa_certificate", label: "Certificate of Public Convenience (PUC)" },
    { key: "pa_inspection", label: "Vehicle Inspection" },
    { key: "pa_form_e", label: "Form E (Insurance Filing)" },
    { key: "ri_operator_license", label: "Taxi-LPMV-PMV Operator's License" },
    { key: "ri_driving_record", label: "Driving Record" },
    { key: "ri_criminal_record", label: "Record of Criminal Convictions" },
    { key: "sc_driving_record", label: "Certified Driving Record (3 Years)" },
    { key: "sc_charter_certificate", label: "Class C Charter Certificate" },
    { key: "sc_ls_registration", label: "Vehicle Registration (LS Plates)" },
    { key: "sc_form_e", label: "Form E (Insurance Filing)" },
    { key: "tn_citizenship_proof", label: "Proof of Citizenship or Lawful Permanent Residency" },
    { key: "tn_residency_proof", label: "Proof of Tennessee Residency" },
    { key: "va_authority", label: "For-Hire Intrastate Operating Authority" },
    { key: "va_title", label: "Vehicle Title (Virginia)" },
    { key: "va_for_hire_registration", label: "For-Hire Vehicle Registration" },
    { key: "va_authority_registration", label: "Operating Authority Registration" },
    { key: "wa_medical_certificate", label: "Medical Examiner's Certificate" },
    { key: "wa_driving_record", label: "Driving Record" },
    { key: "wa_carrier_license", label: "Limousine Carrier License" },
    { key: "wa_vehicle_certificate", label: "Limousine Vehicle Certificate" },
    { key: "wa_chauffeur_addendum", label: "Limousine Carrier Chauffeur Addendum" },
    { key: "wa_fh_registration", label: "Vehicle Registration Certificate (Use Class F/H)" },
    { key: "wa_inspection_report", label: "Vehicle Inspection Report" },
    { key: "wa_insurance_certificate", label: "Certificate of Insurance" },
    { key: "dallas_commercial_insurance", label: "Commercial Insurance Certificate" },
    { key: "dallas_driver_permit", label: "Dallas Driver Permit" },
    { key: "dallas_limo_permit", label: "City Limo Permit (Dallas / Fort Worth)" },
    { key: "buffalo_taxi_driver_license", label: "City of Buffalo Taxi Driver License" },
    { key: "buffalo_insurance_certificate", label: "Certificate of Automobile Liability Insurance" },
    { key: "buffalo_inspection_report", label: "Vehicle Inspection Report" },
    { key: "rochester_taxi_driver_license", label: "City of Rochester Taxicab Driver License" },
    { key: "rochester_hack_certificate", label: "Taxicab License Certificate (Hack Plate Certificate)" },
    { key: "rochester_insurance", label: "Proof of Insurance" },
    { key: "syracuse_hack_license", label: "Taxi (Hack) License" },
    { key: "syracuse_ground_transportation", label: "Ground Transportation License" },
    { key: "syracuse_for_hire_insurance", label: "Proof of For-Hire Insurance" },
    { key: "wctlc_driver_permit", label: "WCTLC For-Hire Driver Permit" },
    { key: "wctlc_vehicle_permit", label: "WCTLC For-Hire Vehicle Permit" },
    { key: "wctlc_insurance", label: "Proof of Adequate Insurance" },
    { key: "wctlc_defensive_driving", label: "Defensive Driving Course Proof of Completion" },
    { key: "birmingham_operator_permit", label: "City of Birmingham Operator's Permit" },
    { key: "huntsville_chauffeur_license", label: "City of Huntsville Chauffeur License" },
    { key: "mobile_chauffeur_license", label: "City of Mobile Chauffeur License" },
    { key: "montgomery_chauffeur_license", label: "City of Montgomery Chauffeur License" },
    { key: "miami_chauffeur_registration", label: "Miami-Dade Chauffeur Registration" },
    { key: "orlando_driver_permit", label: "City of Orlando Driver Permit" },
    { key: "orlando_insurance", label: "Certificate of Insurance (City as Additional Insured)" },
    { key: "tallahassee_driver_permit", label: "City of Tallahassee Driver Permit" },
    { key: "tampa_pvdl", label: "Public Vehicle Driver License (Hillsborough County)" },
    { key: "tampa_transcript", label: "Seven-Year Driver License Transcript" },
    { key: "baton_rouge_chauffeur_license", label: "City of Baton Rouge Chauffeur License" },
    { key: "baton_rouge_driving_record", label: "Official Driving Record" },
    { key: "baton_rouge_clearance", label: "Clearance Certificate" },
    { key: "new_orleans_driver_permit", label: "CPNC Driver Permit (New Orleans)" },
    { key: "new_orleans_mvr", label: "Certified MVR (Within 30 Days)" },
    { key: "mvfha_driver_permit", label: "MVFHA Driver Permit" },
    { key: "charlotte_pvh_permit", label: "PVH Driver Permit (Charlotte)" },
    { key: "charlotte_driving_record", label: "Driving Record" },
    { key: "durham_pvfh_permit", label: "PVFH Driver Permit (Durham)" },
    { key: "charleston_chauffeur_license", label: "Chauffeur License (Charleston)" },
    { key: "charleston_driving_record", label: "Certified 10-Year Driving Record" },
    { key: "nashville_opvh_permit", label: "MTLC OPVH Driver Permit" },
    { key: "nashville_mvr", label: "Motor Vehicle Record (Within 30 Days)" },
    { key: "chicago_chauffeur_license", label: "Restricted Livery Public Chauffeur License (Chicago)" },
    { key: "chicago_livery_vehicle_license", label: "Livery Vehicle License (Chicago)" },
    { key: "chicago_insurance_certificate", label: "Commercial Insurance Certificate (Chicago)" },
    { key: "rockford_taxi_driver_license", label: "Taxi Cab Driver License (Rockford)" },
    { key: "springfield_il_taxi_driver_license", label: "Taxicab Driver License (Springfield, IL)" },
    { key: "evansville_taxi_driver_license", label: "City of Evansville Taxicab Driver License" },
    { key: "indianapolis_operator_license", label: "Operator License (Indianapolis)" },
    { key: "indianapolis_training_certificate", label: "Taxi Training Course Certificate (Indianapolis)" },
    { key: "indianapolis_bmv_record", label: "Certified BMV Driving Record (Within 10 Days)" },
    { key: "minneapolis_taxi_driver_license", label: "Taxi Driver License (Minneapolis)" },
    { key: "minneapolis_training_certificate", label: "Taxi Driver Training Certificate (Minneapolis)" },
    { key: "rochester_mn_taxi_driver_license", label: "Taxicab Driver License (Rochester, MN)" },
    { key: "saint_paul_taxi_driver_license", label: "Taxicab Driver License (Saint Paul)" },
    { key: "saint_paul_training_proof", label: "Taxicab Driver Training Course Completion Proof" },
    { key: "columbia_chauffeur_license", label: "Chauffeur License (Columbia)" },
    { key: "independence_vehicle_driver_permit", label: "Vehicle Driver Permit (Independence)" },
    { key: "jefferson_city_taxi_driver_permit", label: "Taxi Driver Permit (Jefferson City)" },
    { key: "jefferson_city_driving_record", label: "Certified Driving Record (Missouri DOR)" },
    { key: "kansas_city_driver_certificate", label: "Vehicle-for-Hire Driver Certificate (Kansas City)" },
    { key: "kansas_city_operating_record", label: "State Operating Record (Missouri)" },
    { key: "saint_louis_mtc_license", label: "MTC Driver License (Saint Louis)" },
    { key: "saint_louis_driver_history", label: "Missouri Driver History Report (Within 10 Days)" },
    { key: "lincoln_taxi_driver_license", label: "Taxicab Driver License (Lincoln)" },
    { key: "kenosha_taxi_driver_license", label: "Taxi Driver License (Kenosha)" },
    { key: "madison_ppv_permit", label: "Public Passenger Vehicle Driver Permit (Madison)" },
    { key: "milwaukee_ppv_license", label: "Public Passenger Vehicle Driver License (Milwaukee)" },
    { key: "columbus_vfh_license", label: "Vehicle for Hire Driver License (Columbus)" },
    { key: "columbus_bmv_abstract", label: "Certified Ohio BMV Driver Abstract (Within 30 Days)" },
    { key: "portland_me_livery_license", label: "Portland Livery Driver License" },
    { key: "south_portland_taxi_driver_license", label: "South Portland Taxicab Driver License" },
    { key: "lowell_hackney_license", label: "Hackney License (Lowell)" },
    { key: "springfield_ma_chauffeur_license", label: "Chauffeur License (Springfield, MA)" },
    { key: "worcester_taxi_livery_license", label: "Taxi-Livery Driver License (Worcester)" },
    { key: "jersey_city_limo_driver_license", label: "Jersey City Limousine Driver License" },
    { key: "philadelphia_limo_certificate", label: "PPA Limousine Driver Certificate" },
    { key: "little_rock_gt_driver_permit", label: "Ground Transportation Service Driver Permit (Little Rock)" },
    { key: "springdale_taxi_driver_permit", label: "Taxicab Driver Permit (Springdale)" },
    { key: "boise_cts_driver_license", label: "Commercial Transportation Service Driver License (Boise)" },
    { key: "idaho_falls_operator_license", label: "Public Transportation Operator License (Idaho Falls)" },
    { key: "okc_vfh_driver_permit", label: "Vehicle-for-Hire Driver Permit (Oklahoma City)" },
    { key: "tulsa_chauffeur_license", label: "City of Tulsa Chauffeur License" },
    { key: "tulsa_mvr", label: "MVR Report (Within 30 Days)" },
    { key: "austin_chauffeur_permit", label: "Chauffeur Permit (Austin)" },
    { key: "houston_vfh_driver_license", label: "City-Issued Vehicle-for-Hire Driver License (Houston)" },
    { key: "san_antonio_driver_permit", label: "City of San Antonio Driver Permit (Vehicles for Hire)" },
    { key: "st_george_for_hire_permit", label: "For-Hire Driver Permit (St. George)" },
    { key: "cheyenne_pt_driver_permit", label: "Public Transportation Driver Permit (Cheyenne)" },
    { key: "gillette_pt_driver_permit", label: "Public Transportation Driver Permit (Gillette)" },
    { key: "clark_county_business_license", label: "Clark County Business License" },
    { key: "portland_or_certification", label: "Executive Town Car Driver Certification (Portland)" },
    { key: "portland_or_business_license", label: "City of Portland Business License" }
  ];

  function docIsComplete(value) {
    if (value === true) return true;
    if (!value) return false;
    if (typeof value === "string") {
      var v = value.toLowerCase();
      return v === "completed" || v === "complete" || v === "approved" || v === "verified";
    }
    if (typeof value === "object") {
      var st = String(value.status || value.state || "").toLowerCase();
      return st === "completed" || st === "complete" || st === "approved" || st === "verified" ||
        !!(value.url || value.path || value.document_id || value.id);
    }
    return false;
  }

  function loadDrivers() {
    fetch("/api/owner/drivers", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "drivers");
        allDrivers = list;
        var box = $("drivers-list");
        if (!list.length) { box.innerHTML = '<div class="empty">No drivers registered yet.</div>'; return; }
        box.innerHTML = "";
        list.forEach(function (d) {
          var card = document.createElement("div");
          card.className = "driver-card";
          var carBits = d.car || [d.car_year, d.car_model, d.car_colour].filter(Boolean).join(" · ");
          if (d.car && d.car_year) carBits = d.car_year + " · " + d.car;
          var bank = d.bank_masked || d.bank_account_number || d.bank_account || d.account_number || d.masked_account || "";
          var photoUrl = "/api/owner/drivers/" + encodeURIComponent(d.id) + "/photo";
          var head = '<div style="display:flex;gap:14px;align-items:center;">' +
            '<img src="' + esc(photoUrl) + '" alt="" onerror="this.style.visibility=\'hidden\'">' +
            "<div><h3>" + esc(d.name || "Driver") + "</h3>" +
            '<div class="meta">' + esc(d.phone || "") + (d.email ? " · " + esc(d.email) : "") + "</div>" +
            '<div class="meta">' + esc(carBits) + (d.plate ? " · Plate " + esc(d.plate) : "") + "</div>" +
            '<div class="meta">Vehicle class: ' + esc(d.vehicle_class_label || d.vehicle_class || "—") + "</div>" +
            (d.state ? '<div class="meta">State: ' + esc(d.state) + (d.city ? " · City: " + esc(d.city) : "") + "</div>" : "") +
            '<div class="meta">Bank account: ' + esc(maskBank(bank)) + "</div></div></div>";
          card.innerHTML = head;
          var chips = document.createElement("div");
          chips.className = "doc-chips";
          var docs = d.docs || d.documents || {};
          var docIds = d.doc_ids || {};
          DOC_TYPES.forEach(function (spec) {
            if (docs[spec.key] === undefined) return;
            var done = docIsComplete(docs[spec.key]);
            var chip = document.createElement("span");
            chip.className = "doc-chip";
            var label = esc(spec.label) + ' — <span class="' + (done ? "st-done" : "st-todo") + '">' +
              (done ? "Completed" : "Items remaining") + "</span>";
            var expiries = d.doc_expiries || {};
            if (done && expiries[spec.key]) {
              var expDate = expiries[spec.key];
              var todayStr = new Date().toISOString().slice(0, 10);
              var isPast = expDate < todayStr;
              var daysLeft = Math.round((new Date(expDate + "T00:00:00Z") - new Date(todayStr + "T00:00:00Z")) / 86400000);
              label += ' · Expires ' + esc(expDate) +
                (isPast ? ' — <span class="st-todo">expired</span>'
                        : (daysLeft <= 10 ? ' — <span class="st-todo">expiring soon (in ' + daysLeft + (daysLeft === 1 ? ' day' : ' days') + ')</span>' : ""));
            }
            var viewUrl = null;
            if (done) {
              if (spec.photo) {
                viewUrl = photoUrl;
              } else if (docIds[spec.key]) {
                viewUrl = "/api/owner/documents/" + encodeURIComponent(docIds[spec.key]);
              }
            }
            if (viewUrl) {
              label += ' <button type="button">View</button>';
              chip.innerHTML = label;
              chip.querySelector("button").addEventListener("click", function () {
                openViewer(spec.label + " — " + (d.name || "Driver"), viewUrl);
              });
            } else {
              chip.innerHTML = label;
            }
            chips.appendChild(chip);
          });
          card.appendChild(chips);
          var removeBtn = document.createElement("button");
          removeBtn.type = "button";
          removeBtn.className = "row-btn danger-row-btn driver-remove-btn";
          removeBtn.textContent = "Remove driver";
          removeBtn.addEventListener("click", function () { removeDriver(d); });
          card.appendChild(removeBtn);
          box.appendChild(card);
        });
      })
      .catch(function () { $("drivers-list").innerHTML = '<div class="empty">Could not load drivers.</div>'; });
  }

  function openViewer(title, url) {
    $("viewer-title").textContent = title;
    var body = $("viewer-body");
    body.innerHTML = "";
    var img = document.createElement("img");
    img.alt = title;
    img.src = url;
    img.onerror = function () {
      body.innerHTML = "";
      var frame = document.createElement("iframe");
      frame.src = url;
      frame.title = title;
      body.appendChild(frame);
      var p = document.createElement("p");
      p.innerHTML = 'If the document does not display, <a href="' + esc(url) + '" target="_blank" rel="noopener">open it in a new tab</a>.';
      body.appendChild(p);
    };
    body.appendChild(img);
    show($("viewer-backdrop"));
  }
  $("viewer-close").addEventListener("click", function () { hide($("viewer-backdrop")); });
  $("viewer-backdrop").addEventListener("click", function (e) {
    if (e.target === $("viewer-backdrop")) hide($("viewer-backdrop"));
  });

  checkSession();
})();
