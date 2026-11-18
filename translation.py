"""Azure Translator chat translation for Noel Chauffer (TEXT only).

Owner decision 2026-11-18: each side of the driver-customer chat reads
replies in their OWN language. A driver writing Roman Urdu must get
replies IN Roman Urdu; other languages are included too. Speech/voice
was explicitly declined twice — this module does text only, and no
speech feature exists anywhere in the chat.

Design (approved research, 2026-11-18):
* Azure Translator F0 free tier ($0, 2M chars/month, hard-stops).
  Credentials come from ENVIRONMENT VARIABLES ONLY — never hardcoded,
  never logged. Without a key, every function here returns None and
  the chat behaves exactly as it did before translation existed.
* Translation happens ONCE at send time and the result is STORED.
  Nothing in this module is ever called on a read/poll: the chat
  polls every 3-4 seconds, so translate-on-read would re-translate
  (and re-bill characters) on every poll.
* Language is a DECLARED preference picked by each user in the chat
  (one picker, plain labels, default English). No auto-detection is
  ever used: the declared source language is always sent as `from`.
* Fail-soft everywhere: missing key, HTTP error, timeout, quota
  reached, or a malformed response all return None. The caller then
  stores and shows the ORIGINAL text and the chat never breaks.

Roman Urdu (Urdu in Latin script) via the Azure two-hop, verified
against the official Translator REST API v3.0 docs and the live
/languages transliteration scope on 2026-11-18 (Urdu `ur` supports
scripts Arab <-> Latn in both directions):
* Roman Urdu IN:  transliterate ur Latn -> Arab, then translate
  from=ur to the target language.
* Roman Urdu OUT: translate from the source language to=ur, then
  transliterate ur Arab -> Latn.
* Any other pair: one direct translate call.

Endpoints (Translator REST API v3.0):
* POST {endpoint}/translate?api-version=3.0&from={from}&to={to}
  body [{"Text": "..."}] -> [{"translations": [{"text": "..."}]}]
* POST {endpoint}/transliterate?api-version=3.0&language=ur
  &fromScript={Latn|Arab}&toScript={Arab|Latn}
  body [{"Text": "..."}] -> [{"text": "...", "script": "..."}]
Headers: Ocp-Apim-Subscription-Key (required),
Ocp-Apim-Subscription-Region (required for multi-service/regional
resources, optional for a single-service Translator resource — sent
only when AZURE_TRANSLATOR_REGION is set), Content-Type
application/json. Default endpoint:
https://api.cognitive.microsofttranslator.com

No new dependency: plain urllib, so nothing changes in
requirements.txt and Render needs no new install.
"""

from __future__ import annotations

import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger("noel-chauffer.translation")

DEFAULT_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
API_VERSION = "3.0"
# One chat message is at most 500 chars; 5s per hop keeps a send from
# hanging the chat. A timeout fails soft to the original text.
REQUEST_TIMEOUT = 5

# Chat languages: code -> plain picker label. "ur-Latn" is Roman Urdu
# (Urdu in Latin script) — a distinct choice from every other language.
# The same list (same codes, same order, same labels) is in the driver
# and customer pickers; keep all three in step.
CHAT_LANGUAGES = {
    "en": "English",
    "ur-Latn": "Roman Urdu",
    "es": "Spanish",
    "fr": "French",
    "ar": "Arabic",
    "hi": "Hindi",
    "bn": "Bengali",
    "pt": "Portuguese",
}
DEFAULT_CHAT_LANGUAGE = "en"
ROMAN_URDU = "ur-Latn"
URDU = "ur"


def normalize_chat_language(value):
    """A declared chat language code, or the English default.

    Unknown, empty or non-string values fall back to English — the
    picker only ever sends valid codes, so this is a safety net, not
    a guess about what the user wrote.
    """
    if isinstance(value, str) and value.strip() in CHAT_LANGUAGES:
        return value.strip()
    return DEFAULT_CHAT_LANGUAGE


def get_translator_config():
    """(key, region, endpoint) from env vars, read on every call.

    Read at call time (not import time) so tests can set/unset the
    env vars per test and a key rotation needs no code change. The
    key is returned only to the caller that puts it in the request
    header — it is never logged.
    """
    key = (os.environ.get("AZURE_TRANSLATOR_KEY") or "").strip() or None
    region = (os.environ.get("AZURE_TRANSLATOR_REGION") or "").strip() or None
    endpoint = (os.environ.get("AZURE_TRANSLATOR_ENDPOINT") or "").strip() or DEFAULT_ENDPOINT
    return key, region, endpoint.rstrip("/")


def _post_json(url, key, region, payload, timeout):
    """POST one JSON body to Azure and return the parsed JSON, or None.

    Never raises: HTTP errors (including quota-exhausted 403/429),
    timeouts, network errors and malformed responses all return None
    so the caller can fail soft to the original text.
    """
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json",
    }
    if region:
        headers["Ocp-Apim-Subscription-Region"] = region
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        # Includes quota-exhausted responses: the F0 tier hard-stops
        # instead of charging, so this is an expected fail-soft case.
        log.warning("Azure Translator HTTP error: %s", exc.code)
        return None
    except (URLError, TimeoutError, OSError) as exc:
        log.warning("Azure Translator request failed: %s", exc)
        return None
    except Exception as exc:  # never let translation break the chat
        log.warning("Azure Translator unexpected error: %s", exc)
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        log.warning("Azure Translator returned unparseable JSON.")
        return None


def _first_text(data, path):
    """First non-empty string found by walking `path` through `data`.

    path is a list of dict keys / list indices, e.g. [0, "translations",
    0, "text"]. Anything missing or the wrong shape returns None.
    """
    current = data
    for step in path:
        try:
            current = current[step]
        except (KeyError, IndexError, TypeError):
            return None
    if isinstance(current, str) and current.strip():
        return current
    return None


def _azure_translate(text, source, target, config, timeout):
    """One direct translate call. Returns the translated text or None."""
    key, region, endpoint = config
    query = urlencode({"api-version": API_VERSION, "from": source, "to": target})
    data = _post_json(
        f"{endpoint}/translate?{query}", key, region, [{"Text": text}], timeout
    )
    if data is None:
        return None
    return _first_text(data, [0, "translations", 0, "text"])


def _azure_transliterate(text, from_script, to_script, config, timeout):
    """One transliterate call for Urdu. Returns the converted text or None."""
    key, region, endpoint = config
    query = urlencode({
        "api-version": API_VERSION,
        "language": URDU,
        "fromScript": from_script,
        "toScript": to_script,
    })
    data = _post_json(
        f"{endpoint}/transliterate?{query}", key, region, [{"Text": text}], timeout
    )
    if data is None:
        return None
    return _first_text(data, [0, "text"])


def translate_chat_text(text, source, target, timeout=REQUEST_TIMEOUT):
    """Translate one chat message at send time, or return None.

    Returns None (caller shows the original text) when: the text is
    empty, source and target are the same language (no API call is
    made), no Azure key is configured (no API call is made), or any
    hop fails. Never raises.
    """
    try:
        if not isinstance(text, str) or not text.strip():
            return None
        source = normalize_chat_language(source)
        target = normalize_chat_language(target)
        if source == target:
            return None
        config = get_translator_config()
        if not config[0]:
            return None
        if source == ROMAN_URDU:
            # Hop 1: Roman Urdu -> Urdu script. Hop 2: Urdu -> target.
            script_text = _azure_transliterate(text, "Latn", "Arab", config, timeout)
            if script_text is None:
                return None
            return _azure_translate(script_text, URDU, target, config, timeout)
        if target == ROMAN_URDU:
            # Hop 1: source -> Urdu script. Hop 2: Urdu script -> Roman Urdu.
            script_text = _azure_translate(text, source, URDU, config, timeout)
            if script_text is None:
                return None
            return _azure_transliterate(script_text, "Arab", "Latn", config, timeout)
        return _azure_translate(text, source, target, config, timeout)
    except Exception as exc:  # last-resort guard: chat must never break
        log.warning("Chat translation failed: %s", exc)
        return None
