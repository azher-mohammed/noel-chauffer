/* Noel Chauffer — customer site logic.
   Talks only to the /api/* contract. The total is NEVER computed here:
   it is shown only when the API returns a number, after a chauffeur accepts. */
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
    mapReady: false
  };

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
      offered: "Finding your chauffeur…",
      accepted: "Chauffeur confirmed",
      paid: "Paid — your chauffeur is confirmed",
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
    if (!payload.customer_name || !payload.phone || !payload.email || !payload.pickup || !payload.date || !payload.time) {
      err.textContent = "Please fill in your name, phone, email, pickup, date and time.";
      return;
    }
    if (state.rideType === "one_way" && !payload.dropoff) {
      err.textContent = "Please enter a drop-off address.";
      return;
    }
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
        btn.textContent = "Request my chauffeur";
        if (!res.ok || !res.j.booking || !res.j.booking.id) {
          err.textContent = (res.j && (res.j.error || res.j.message)) || "Something went wrong. Please try again.";
          return;
        }
        startTracking(res.j.booking, payload.phone);
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = "Request my chauffeur";
        err.textContent = "Could not reach the booking service. Please check your connection and try again.";
      });
  });

  function startTracking(booking, phone) {
    stopPolling();
    state.bookingId = booking.id;
    state.bookingPhone = phone;
    state.booking = booking;
    state.paid = false;
    hide($("thankyou-block"));
    hide($("invoice-panel"));
    hide($("pay-panel"));
    hide($("driver-block"));
    hide($("total-box"));
    hide($("map-wrap"));
    hide($("cancel-result"));
    show($("status-finding"));
    show($("status-actions"));
    show($("status-card"));
    $("status-summary").textContent = rideLabel(booking) + (whenLabel(booking) ? " · " + whenLabel(booking) : "");
    $("status-card").scrollIntoView({ behavior: "smooth", block: "start" });
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
          var st = j.booking.status;
          if (st === "cancelled" || st === "canceled" || st === "completed" || st === "no_show") {
            stopPolling();
          }
        }
      })
      .catch(function () { /* keep polling; a failed check changes nothing on screen */ });
  }

  function renderBooking(b) {
    $("status-summary").textContent = rideLabel(b) + (whenLabel(b) ? " · " + whenLabel(b) : "");
    var hasDriver = !!(b.driver && b.driver.name);
    var st = b.status || "";

    if (hasDriver) {
      hide($("status-finding"));
      show($("driver-block"));
      $("driver-name").textContent = b.driver.name || "";
      var carBits = [];
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
      $("status-message").textContent = statusLabel(st) || "Your request is with us. Please keep this page open.";
    }

    /* The single total: shown ONLY when the API returns one. */
    if (b.total !== null && b.total !== undefined) {
      show($("total-box"));
      $("total-amount").textContent = money(b.total);
      $("pay-amount-label").textContent = money(b.total);
      if (st === "paid" || st === "en_route" || st === "arrived" || st === "started" || st === "on_trip" || st === "in_progress" || st === "completed") {
        hide($("pay-open-btn"));
      } else {
        show($("pay-open-btn"));
      }
    } else {
      hide($("total-box"));
    }

    /* Live map: ONLY when the API says tracking is visible. */
    var tr = b.tracking || {};
    if (tr.visible && tr.lat !== null && tr.lat !== undefined && tr.lng !== null && tr.lng !== undefined) {
      show($("map-wrap"));
      renderMap(Number(tr.lat), Number(tr.lng), b);
    } else {
      hide($("map-wrap"));
    }

    /* Thank-you + invoice after payment / completion. */
    if (state.paid || st === "paid" || st === "en_route" || st === "arrived" || st === "started" || st === "on_trip" || st === "in_progress" || st === "completed") {
      if (state.paid || st !== "offered") { showThankYou(b); }
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
      $("invoice-grand").textContent = money(invTotal);
    }

    if (st === "cancelled" || st === "canceled") {
      hide($("status-actions"));
      hide($("pay-panel"));
      $("status-message").textContent = "This booking was cancelled.";
      show($("status-finding"));
    }
    if (st === "completed") {
      hide($("status-actions"));
      hide($("pay-panel"));
    }
  }

  function showThankYou(b) {
    show($("thankyou-block"));
    $("thankyou-summary").textContent =
      "Ride confirmed: " + rideLabel(b) + (whenLabel(b) ? " · " + whenLabel(b) : "") + ".";
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
      return "You will see one single total after your chauffeur accepts — no breakdown, no hidden charges. You pay by card on this page before the ride.";
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
    if (has("car", "vehicle", "sedan", "suv", "type")) {
      return "Our rides use recent high-end sedans and SUVs — clean, comfortable, and prepared for every ride, with phone chargers on board.";
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
      return "To book: fill in the form at the top of this page — pickup, drop-off (or hours), date, time, and your name, phone and email — then tap “Request my chauffeur”. Keep the page open while we confirm your chauffeur.";
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
