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
    loadBookings();
    loadPayouts();
    loadAlerts();
    loadOutbox();
    loadDrivers();
  }

  $("logout-btn").addEventListener("click", function () {
    fetch("/api/owner/logout", { method: "POST", credentials: "same-origin" })
      .then(function () { window.location.reload(); })
      .catch(function () { window.location.reload(); });
  });

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
      driver: pick(b, ["driver_share", "driver_earnings", "driver_pay", "driver_amount"]),
      toll: pick(b, ["toll", "toll_amount"]) !== null ? pick(b, ["toll", "toll_amount"]) : pick(inv, ["toll"]),
      gratuity: pick(b, ["gratuity", "tip", "gratuity_amount"]),
      waiting: pick(b, ["waiting_charge", "waiting"]) !== null ? pick(b, ["waiting_charge", "waiting"]) : pick(inv, ["waiting_charge"]),
      profit: pick(b, ["profit", "owner_profit", "net"])
    };
  }

  function loadBookings() {
    fetch("/api/owner/bookings", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var list = asList(j, "bookings");
        var body = $("bookings-body");
        body.innerHTML = "";
        if (!list.length) { show($("bookings-empty")); return; }
        hide($("bookings-empty"));
        list.forEach(function (b) {
          var f = breakdownFields(b);
          var driverName = (b.driver && b.driver.name) || b.driver_name || "—";
          /* The API returns the ready-made `route` string on list rows. */
          var route = b.route ? esc(b.route) : (esc(b.pickup || "") + (b.dropoff ? " → " + esc(b.dropoff) : ""));
          var tr = document.createElement("tr");
          tr.innerHTML =
            "<td>" + route + '<div class="sub">' + esc(whenLabel(b)) +
            (b.ride_type === "hourly" ? " · By the hour" + (b.hours ? " · " + b.hours + " h" : "") : "") + "</div></td>" +
            "<td>" + esc(b.customer_name || b.name || "—") + '<div class="sub">' + esc(b.phone || "") + "</div></td>" +
            "<td>" + esc(driverName) + "</td>" +
            '<td><span class="pill">' + esc(b.status || "") + "</span></td>" +
            '<td class="num">' + esc(money(f.paid)) + "</td>" +
            '<td class="num">' + esc(money(f.driver)) + "</td>" +
            '<td class="num">' + esc(money(f.toll)) + "</td>" +
            '<td class="num">' + esc(money(f.gratuity)) + "</td>" +
            '<td class="num">' + esc(money(f.waiting)) + "</td>" +
            '<td class="num">' + esc(money(f.profit)) + "</td>" +
            "<td><input class=\"toll-input\" type=\"number\" min=\"0\" step=\"0.01\" value=\"" +
            esc(f.toll !== null && f.toll !== undefined ? f.toll : "") +
            "\" aria-label=\"Toll for this ride\"><button class=\"toll-save\" type=\"button\">Save</button></td>" +
            "<td><button class=\"row-btn\" type=\"button\">View</button></td>";
          tr.querySelector(".toll-save").addEventListener("click", function () {
            var val = tr.querySelector(".toll-input").value;
            saveToll(b.id, val, tr);
          });
          tr.querySelector(".row-btn").addEventListener("click", function () { loadBookingDetail(b.id); });
          body.appendChild(tr);
        });
      })
      .catch(function () {
        $("bookings-body").innerHTML = "";
        show($("bookings-empty"));
        $("bookings-empty").textContent = "Could not load bookings.";
      });
  }

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
          ["Flight", b.flight_number ? (b.flight_number + (b.airline_name ? " · " + b.airline_name : "") + (b.terminal ? " · " + b.terminal : "")) : "—"],
          ["Customer", b.customer_name || b.name || "—"],
          ["Customer phone", b.phone || b.customer_phone || "—"],
          ["Customer email", b.email || b.customer_email || "—"],
          ["Referral code", b.referral_code_used || b.referral_code || "—"],
          ["Driver", driver.name || b.driver_name || "—"],
          ["Driver phone", driver.phone || "—"],
          ["Car", [driver.car_year, driver.car_model, driver.car_colour].filter(Boolean).join(" · ") || "—"],
          ["Plate", driver.plate || "—"],
          ["Customer paid", money(f.paid)],
          ["Driver share", money(f.driver)],
          ["Toll", money(f.toll)],
          ["Gratuity", money(f.gratuity)],
          ["Waiting charge", money(f.waiting)],
          ["Profit", money(f.profit)]
        ];
        panel.innerHTML = "<h3>Booking detail</h3><div class=\"detail-grid\">" +
          rows.map(function (r) {
            return "<div><div class=\"k\">" + esc(r[0]) + "</div><div>" + esc(r[1]) + "</div></div>";
          }).join("") + "</div>";
        show(panel);
        panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      })
      .catch(function () { /* leave the previous detail view */ });
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
          return '<div class="feed-item"><div class="ch">' + esc(channel) + (to ? " → " + esc(to) : "") + "</div>" +
            subject + '<div class="body">' + esc(body) + '</div><div class="t">' + esc(when) + "</div></div>";
        }).join("");
      })
      .catch(function () { $("outbox-feed").innerHTML = '<div class="empty">Could not load the outbox.</div>'; });
  }

  /* ---------- Drivers + document viewer ---------- */
  /* Document types as the API returns them in `docs` (status strings)
     and `doc_ids` (row ids for the viewer). The profile picture has no
     document row: it is served from the driver photo endpoint. */
  var DOC_TYPES = [
    { key: "dmv_license", label: "DMV driving license" },
    { key: "profile_picture", label: "Profile Picture", photo: true },
    { key: "tlc_license", label: "TLC License" },
    { key: "fh1_insurance", label: "FH-1 Insurance Card" },
    { key: "registration", label: "Commercial Vehicle Registration" },
    { key: "inspection", label: "NYS DMV Inspection" },
    { key: "vehicle_permit", label: "TLC-for-hire Vehicle Permit" }
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
            '<div class="meta">Bank account: ' + esc(maskBank(bank)) + "</div></div></div>";
          card.innerHTML = head;
          var chips = document.createElement("div");
          chips.className = "doc-chips";
          var docs = d.docs || d.documents || {};
          var docIds = d.doc_ids || {};
          DOC_TYPES.forEach(function (spec) {
            var done = docIsComplete(docs[spec.key]);
            var chip = document.createElement("span");
            chip.className = "doc-chip";
            var label = esc(spec.label) + ' — <span class="' + (done ? "st-done" : "st-todo") + '">' +
              (done ? "Completed" : "Items remaining") + "</span>";
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
