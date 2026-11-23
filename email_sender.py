"""Outbound email via Resend for Noel Chauffer.

Owner decision 2026-11-18 ("Resend kar dena na"): queued email
messages are sent through Resend once the owner connects an account
(Resend account + noelchauffer.com domain verification + API key in
Render). Until then everything stays outbox-only, exactly as before.

Design (same pattern as translation.py):
* The API key comes from the ENVIRONMENT VARIABLE RESEND_API_KEY
  ONLY — never hardcoded, never logged. Without a key, send_email
  returns "not_configured" and makes ZERO HTTP calls.
* The sender address comes from RESEND_FROM, defaulting to
  "Noel Chauffer <support@noelchauffer.com>".
* Fail-soft everywhere: missing key, HTTP error, timeout, or a
  malformed response all return a non-sent status. send_email
  NEVER raises into the caller.
* Email only: SMS rows never reach this module (Resend is
  email-only) — the caller keeps SMS queued-only.

Endpoint (Resend REST API): POST https://api.resend.com/emails
body {"from": ..., "to": [...], "subject": ..., "text": ...}
— plus an optional "html" part when the caller passes one
(plain text stays the fallback). header Authorization: Bearer
<key>. A 2xx response means sent.

No new dependency: plain urllib, so nothing changes in
requirements.txt and Render needs no new install.
"""

from __future__ import annotations

import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

log = logging.getLogger("noel-chauffer.email")

RESEND_API_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "Noel Chauffer <support@noelchauffer.com>"
# 10s keeps a send from hanging the caller's request; a timeout
# fails soft and the message simply stays queued.
REQUEST_TIMEOUT = 10

# send_email return statuses.
SENT = "sent"
NOT_CONFIGURED = "not_configured"
FAILED = "failed"


def _api_key():
    return (os.environ.get("RESEND_API_KEY") or "").strip()


def _from_address():
    return (os.environ.get("RESEND_FROM") or "").strip() or DEFAULT_FROM


def is_configured():
    """True when a Resend key is set (sending is possible)."""
    return bool(_api_key())


def send_email(to, subject, body, html=None):
    """Send one email via Resend. Returns SENT only on a confirmed
    (2xx) send, NOT_CONFIGURED when no key is set (no HTTP call at
    all), FAILED on any error. Never raises; the key is never
    logged. When `html` is given it is sent as the HTML part
    alongside the plain-text `body` (the fallback); otherwise the
    email is text-only, exactly as before."""
    key = _api_key()
    if not key:
        return NOT_CONFIGURED
    payload = {
        "from": _from_address(),
        "to": [to],
        "subject": subject,
        "text": body,
    }
    if html:
        payload["html"] = html
    payload = json.dumps(payload).encode("utf-8")
    request = Request(
        RESEND_API_URL, data=payload, method="POST",
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 # Required: api.resend.com sits behind Cloudflare,
                 # which blocks urllib's default User-Agent with
                 # HTTP 403 "error code: 1010" before the key is
                 # ever checked (all sends failed this way until
                 # this header was added 2026-11-18).
                 "User-Agent": "NoelChauffer/1.0"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
            return SENT if 200 <= resp.status < 300 else FAILED
    except HTTPError as exc:
        # Log the status, Resend's error body (a JSON message — it
        # never contains the key), and the key length (a number
        # only). The key value itself is never logged.
        try:
            detail = exc.read().decode("utf-8", "replace").strip()[:300]
        except Exception:
            detail = ""
        log.warning("Resend send failed: HTTP %s: %s (key_len=%d)",
                    exc.code, detail, len(key))
        return FAILED
    except (URLError, OSError, ValueError) as exc:
        log.warning("Resend send failed: %s", exc)
        return FAILED
