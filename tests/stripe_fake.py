"""Deterministic fake Stripe backend for the test suite.

Install with `stripe_fake.install()` (after importing the app) and
every Stripe call in `stripe_payments` returns canned success — no
network, no keys, no real charge. `uninstall()` restores the real
functions. Behaviour switches, set by tests that need them:

- payment_method_id "pm_test_decline" -> create_payment_intent raises
  StripePaymentsError ("Your card was declined.").
- payment_method_id "pm_test_action" -> create_payment_intent returns
  status "requires_action" (3-D Secure); `retrieve_payment_intent`
  then reports "requires_capture" (the bank approved it).
- CONNECT_PAYOUTS_ENABLED = False -> retrieve_account reports the
  Connect account as not payout-ready.
- PAYOUT_FAIL = True -> create_instant_payout raises
  StripePaymentsError.
- DEBIT_CARD_LINKED = False -> list_payout_cards returns no debit
  card (the instant-payout destination is missing).

Created PaymentIntents are tracked in INTENTS so retrieve/capture/
cancel see the same id and status the create call produced. Call
`reset()` between tests that count intents.

This file is test-only: production code never imports it, and the
fake is never installed outside the test suite.
"""

from __future__ import annotations

import stripe_payments as sp

FAKE_PUBLISHABLE_KEY = "pk_test_fake"
FAKE_CUSTOMER_ID = "cus_fake_1"
FAKE_CONNECT_ACCOUNT_ID = "acct_fake_1"

# PaymentMethod ids the fake recognises.
DECLINE_PM = "pm_test_decline"
ACTION_PM = "pm_test_action"
DEFAULT_PM = "pm_test_4242"

# Test-controlled switches (reset by reset()).
CONNECT_PAYOUTS_ENABLED = True
PAYOUT_FAIL = False
# A debit card linked to the fake Connect account (the instant-payout
# destination). Tests flip it to exercise the no-card path.
DEBIT_CARD_LINKED = True

# Created intents: pi id -> dict(status, amount_cents, customer_id).
INTENTS = {}
_counter = {"n": 0}

_originals = {}
_installed = False


def _next_id(prefix):
    _counter["n"] += 1
    return "%s_fake_%d" % (prefix, _counter["n"])


def _card_for(pm_id):
    return {"id": pm_id, "brand": "visa", "last4": "4242",
            "exp_month": 12, "exp_year": 2030}


def _fake_configured():
    return True


def _fake_publishable_key():
    return FAKE_PUBLISHABLE_KEY


def _fake_create_customer(email, name, phone):
    return {"id": FAKE_CUSTOMER_ID}


def _fake_get_payment_method(payment_method_id):
    return _card_for(payment_method_id)


def _fake_attach_payment_method(payment_method_id, customer_id):
    return _card_for(payment_method_id)


def _fake_list_payment_methods(customer_id):
    return []


def _fake_detach_payment_method(payment_method_id):
    return {"id": payment_method_id}


def _fake_create_payment_intent(amount_cents, customer_id, payment_method_id,
                                booking_id, description="Noel Chauffer ride"):
    if payment_method_id == DECLINE_PM:
        raise sp.StripePaymentsError("Your card was declined.")
    pi_id = _next_id("pi")
    status = "requires_action" if payment_method_id == ACTION_PM else "requires_capture"
    INTENTS[pi_id] = {"status": status, "amount_cents": int(amount_cents),
                      "customer_id": customer_id,
                      "payment_method_id": payment_method_id,
                      "booking_id": booking_id}
    return {"id": pi_id, "status": status, "amount_cents": int(amount_cents),
            "client_secret": pi_id + "_secret", "card": _card_for(payment_method_id)}


def _fake_retrieve_payment_intent(payment_intent_id):
    intent = INTENTS.get(payment_intent_id)
    if intent is None:
        raise sp.StripePaymentsError("No such payment intent.")
    # A 3-D Secure flow the bank approved flips to requires_capture.
    status = "requires_capture" if intent["status"] == "requires_action" else intent["status"]
    return {"id": payment_intent_id, "status": status,
            "amount_cents": intent["amount_cents"],
            "amount_captured_cents": 0,
            "client_secret": payment_intent_id + "_secret",
            "customer_id": intent.get("customer_id"),
            "payment_method_id": intent.get("payment_method_id"),
            "booking_id": intent.get("booking_id")}


def _fake_capture_payment_intent(payment_intent_id, amount_cents=None):
    intent = INTENTS.get(payment_intent_id)
    if intent is None:
        raise sp.StripePaymentsError("No such payment intent.")
    captured = int(amount_cents) if amount_cents is not None else intent["amount_cents"]
    intent["status"] = "succeeded"
    intent["amount_captured_cents"] = captured
    return {"id": payment_intent_id, "status": "succeeded",
            "amount_captured_cents": captured}


def _fake_cancel_payment_intent(payment_intent_id):
    intent = INTENTS.get(payment_intent_id)
    if intent is not None:
        intent["status"] = "canceled"
    return {"id": payment_intent_id, "status": "canceled"}


def _fake_refund_payment_intent(payment_intent_id, amount_cents=None):
    intent = INTENTS.get(payment_intent_id)
    amount = int(amount_cents) if amount_cents is not None else (
        intent["amount_cents"] if intent else 0)
    return {"id": _next_id("re"), "status": "succeeded", "amount_cents": amount}


def _fake_create_off_session_payment_intent(amount_cents, customer_id,
                                            payment_method_id, booking_id,
                                            description="Noel Chauffer ride"):
    pi_id = _next_id("pi")
    INTENTS[pi_id] = {"status": "succeeded", "amount_cents": int(amount_cents),
                      "customer_id": customer_id}
    return {"id": pi_id, "status": "succeeded", "amount_cents": int(amount_cents),
            "card": _card_for(payment_method_id)}


def _fake_create_connect_account(email):
    return {"id": FAKE_CONNECT_ACCOUNT_ID}


def _fake_create_account_link(account_id, return_url, refresh_url):
    return {"url": "https://connect.stripe.com/setup/fake"}


def _fake_retrieve_account(account_id):
    return {"id": account_id, "charges_enabled": True,
            "payouts_enabled": CONNECT_PAYOUTS_ENABLED,
            "details_submitted": CONNECT_PAYOUTS_ENABLED}


def _fake_list_payout_cards(account_id):
    if not DEBIT_CARD_LINKED:
        return []
    return [{"id": "card_fake_1", "brand": "visa", "last4": "9876",
             "exp_month": 12, "exp_year": 2030}]


def _fake_create_transfer(amount_cents, destination_account_id,
                          description="Noel Chauffer driver payout"):
    return {"id": _next_id("tr"), "amount_cents": int(amount_cents)}


def _fake_create_instant_payout(account_id, amount_cents):
    if PAYOUT_FAIL:
        raise sp.StripePaymentsError("Instant payout failed.")
    return {"id": _next_id("po"), "status": "paid", "amount_cents": int(amount_cents)}


_PATCHES = {
    "stripe_configured": _fake_configured,
    "get_publishable_key": _fake_publishable_key,
    "create_customer": _fake_create_customer,
    "get_payment_method": _fake_get_payment_method,
    "attach_payment_method": _fake_attach_payment_method,
    "list_payment_methods": _fake_list_payment_methods,
    "detach_payment_method": _fake_detach_payment_method,
    "create_payment_intent": _fake_create_payment_intent,
    "retrieve_payment_intent": _fake_retrieve_payment_intent,
    "capture_payment_intent": _fake_capture_payment_intent,
    "cancel_payment_intent": _fake_cancel_payment_intent,
    "refund_payment_intent": _fake_refund_payment_intent,
    "create_off_session_payment_intent": _fake_create_off_session_payment_intent,
    "create_connect_account": _fake_create_connect_account,
    "create_account_link": _fake_create_account_link,
    "retrieve_account": _fake_retrieve_account,
    "list_payout_cards": _fake_list_payout_cards,
    "create_transfer": _fake_create_transfer,
    "create_instant_payout": _fake_create_instant_payout,
}


def install():
    """Patch stripe_payments with the fake (idempotent)."""
    global _installed
    if _installed:
        return
    for name, fake in _PATCHES.items():
        _originals[name] = getattr(sp, name)
        setattr(sp, name, fake)
    _installed = True


def uninstall():
    """Restore the real stripe_payments functions."""
    global _installed
    if not _installed:
        return
    for name, original in _originals.items():
        setattr(sp, name, original)
    _originals.clear()
    _installed = False


def reset():
    """Clear created-intent state and behaviour switches."""
    global CONNECT_PAYOUTS_ENABLED, PAYOUT_FAIL, DEBIT_CARD_LINKED
    INTENTS.clear()
    _counter["n"] = 0
    CONNECT_PAYOUTS_ENABLED = True
    PAYOUT_FAIL = False
    DEBIT_CARD_LINKED = True
