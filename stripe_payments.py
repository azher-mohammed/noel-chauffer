"""Live Stripe payments for Noel Chauffer (owner decision 2026-11-20,
voice call: "Uber jaisa bana do"). This RESTARTS the live Stripe build
that was deferred on 2026-11-18 — until now payments were test-mode
only and no Stripe API call was ever made.

Rules this module enforces:
- Keys come ONLY from the Render environment (STRIPE_SECRET_KEY /
  STRIPE_PUBLISHABLE_KEY). They are never in code, never logged, never
  returned by any API. The owner adds them himself in the Render
  dashboard; until then `stripe_configured()` is False and every
  payment call refuses — there is NO fake-success fallback anywhere.
- Card numbers never touch this app: Stripe.js collects the card in
  the browser and hands us a PaymentMethod id (pm_...). Raw card
  numbers sent to the server are rejected by the pay endpoint.
- Cards are stored by Stripe only (Stripe Customer + PaymentMethod),
  never by Noel — only brand, last 4 and expiry are kept on file.
- Statement descriptor is always "NOEL CHAUFFER".
- The Stripe SDK is imported lazily inside `_stripe()` so the app
  still boots (and tests still run) when the package or the keys are
  absent; in that state every call raises StripePaymentsError.
- Every function raises StripePaymentsError on failure with a
  customer-safe `user_message`. Callers must never invent a success
  when a call raises.
"""

from __future__ import annotations

import os
from decimal import Decimal, ROUND_HALF_UP

STATEMENT_DESCRIPTOR = "NOEL CHAUFFER"
CURRENCY = "usd"

# Driver instant payout (owner decision 2026-11-20): cash out to an
# eligible debit card via Stripe Instant Payouts. Stripe charges 1.5%
# of the payout; the standard 7-day weekly payout stays free.
INSTANT_PAYOUT_FEE_RATE = Decimal("0.015")

SECRET_ENV = "STRIPE_SECRET_KEY"
PUBLISHABLE_ENV = "STRIPE_PUBLISHABLE_KEY"


class StripePaymentsError(Exception):
    """A Stripe call failed. `user_message` is safe to show to a
    customer or driver; the original error stays chained for logs."""

    def __init__(self, user_message, *args, **kwargs):
        super().__init__(user_message, *args)
        self.user_message = user_message


def stripe_configured() -> bool:
    """True only when both live keys are present in the environment.
    False means real payments are not active yet — the owner has not
    added the keys in Render. Callers must refuse payment work then,
    never fake it."""
    return bool(os.environ.get(SECRET_ENV) and os.environ.get(PUBLISHABLE_ENV))


def get_publishable_key():
    """The publishable key for Stripe.js, or None when unconfigured.
    The secret key is never exposed."""
    return os.environ.get(PUBLISHABLE_ENV) or None


def to_cents(amount) -> int:
    """Decimal dollars -> integer cents, ROUND_HALF_UP."""
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_dollars(cents) -> Decimal:
    """Integer cents -> Decimal dollars."""
    return (Decimal(int(cents)) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _stripe():
    """The Stripe SDK, configured with the secret key. Raises
    StripePaymentsError when the package or the keys are missing."""
    if not stripe_configured():
        raise StripePaymentsError(
            "Card payments are not set up yet. Please try again later.")
    try:
        import stripe
    except ImportError as exc:  # pragma: no cover - package installed in prod
        raise StripePaymentsError(
            "Card payments are not set up yet. Please try again later.") from exc
    stripe.api_key = os.environ[SECRET_ENV]
    return stripe


def _wrap_error(exc):
    """Convert a Stripe SDK error into StripePaymentsError with a
    customer-safe message. Anything else becomes a generic payment
    service error (original chained for the logs)."""
    try:
        import stripe as _stripe_module
        if isinstance(exc, _stripe_module.error.StripeError):
            message = getattr(exc, "user_message", None) or str(exc) or \
                "Your card could not be charged. Please try another card."
            raise StripePaymentsError(message) from exc
    except StripePaymentsError:
        raise
    except Exception:
        pass
    raise StripePaymentsError(
        "The payment service is unavailable right now. Please try again.") from exc


def _card_view(payment_method) -> dict:
    """Brand / last4 / expiry from a Stripe PaymentMethod object.
    Only these four fields are ever stored or shown."""
    card = getattr(payment_method, "card", None) or {}
    get = (lambda k: card.get(k) if isinstance(card, dict) else getattr(card, k, None))
    return {
        "id": getattr(payment_method, "id", None),
        "brand": get("brand"),
        "last4": get("last4"),
        "exp_month": get("exp_month"),
        "exp_year": get("exp_year"),
    }


def create_customer(email, name, phone) -> dict:
    """Create a Stripe Customer for a phone-keyed customer. Returns
    {"id": "cus_..."}. The customer id is what saved cards hang off."""
    stripe = _stripe()
    try:
        customer = stripe.Customer.create(
            email=email or None, name=name or None, phone=phone or None,
            metadata={"phone": phone or ""},
        )
    except Exception as exc:
        _wrap_error(exc)
    return {"id": customer.id}


def get_payment_method(payment_method_id) -> dict:
    """Brand / last4 / expiry for a PaymentMethod id."""
    stripe = _stripe()
    try:
        pm = stripe.PaymentMethod.retrieve(payment_method_id)
    except Exception as exc:
        _wrap_error(exc)
    return _card_view(pm)


def attach_payment_method(payment_method_id, customer_id) -> dict:
    """Attach a PaymentMethod to a Customer (this is what saves the
    card for future rides). Returns the card view."""
    stripe = _stripe()
    try:
        pm = stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
    except Exception as exc:
        _wrap_error(exc)
    return _card_view(pm)


def list_payment_methods(customer_id) -> list:
    """Saved cards on a Stripe Customer (type card only)."""
    stripe = _stripe()
    try:
        methods = stripe.PaymentMethod.list(customer=customer_id, type="card")
    except Exception as exc:
        _wrap_error(exc)
    return [_card_view(pm) for pm in methods.data]


def detach_payment_method(payment_method_id) -> dict:
    """Remove a saved card from its customer."""
    stripe = _stripe()
    try:
        pm = stripe.PaymentMethod.detach(payment_method_id)
    except Exception as exc:
        _wrap_error(exc)
    return {"id": getattr(pm, "id", payment_method_id)}


def create_payment_intent(amount_cents, customer_id, payment_method_id,
                          booking_id, description="Noel Chauffer ride") -> dict:
    """Authorize (hold) the estimated fare at booking: a PaymentIntent
    with manual capture, confirmed now. Returns {"id", "status",
    "amount_cents", "client_secret", "card"}. "requires_capture" means
    the hold is in place; "requires_action" means the customer's bank
    wants 3-D Secure — the frontend completes it with the returned
    client_secret and then calls the confirm endpoint."""
    stripe = _stripe()
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount_cents),
            currency=CURRENCY,
            customer=customer_id,
            payment_method=payment_method_id,
            capture_method="manual",
            confirm=True,
            setup_future_usage="off_session",
            payment_method_types=["card"],
            statement_descriptor=STATEMENT_DESCRIPTOR,
            description=description,
            metadata={"booking_id": str(booking_id)},
        )
    except Exception as exc:
        _wrap_error(exc)
    card = _card_view(intent.payment_method) if getattr(intent, "payment_method", None) else {}
    if not card or not card.get("last4"):
        try:
            card = get_payment_method(payment_method_id)
        except StripePaymentsError:
            card = {}
    return {
        "id": intent.id,
        "status": intent.status,
        "amount_cents": int(intent.amount),
        "client_secret": getattr(intent, "client_secret", None),
        "card": card,
    }


def retrieve_payment_intent(payment_intent_id) -> dict:
    """Current status of a PaymentIntent."""
    stripe = _stripe()
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except Exception as exc:
        _wrap_error(exc)
    return {
        "id": intent.id,
        "status": intent.status,
        "amount_cents": int(intent.amount),
        "amount_captured_cents": int(getattr(intent, "amount_captured", 0) or 0),
        "client_secret": getattr(intent, "client_secret", None),
        "customer_id": getattr(intent, "customer", None),
        "payment_method_id": getattr(intent, "payment_method", None),
    }


def capture_payment_intent(payment_intent_id, amount_cents=None) -> dict:
    """Capture a held authorization: the final fare is charged now.
    `amount_cents` may be less than the authorized amount (partial
    capture — the rest of the hold is released). Returns {"id",
    "status", "amount_captured_cents"}."""
    stripe = _stripe()
    kwargs = {}
    if amount_cents is not None:
        kwargs["amount_to_capture"] = int(amount_cents)
    try:
        intent = stripe.PaymentIntent.capture(payment_intent_id, **kwargs)
    except Exception as exc:
        _wrap_error(exc)
    return {
        "id": intent.id,
        "status": intent.status,
        "amount_captured_cents": int(getattr(intent, "amount_captured", 0) or 0),
    }


def cancel_payment_intent(payment_intent_id) -> dict:
    """Cancel an uncaptured authorization: the hold is released and
    the customer is never charged. Used for free cancellations
    (more than 1 hour before pickup)."""
    stripe = _stripe()
    try:
        intent = stripe.PaymentIntent.cancel(payment_intent_id)
    except Exception as exc:
        _wrap_error(exc)
    return {"id": intent.id, "status": intent.status}


def refund_payment_intent(payment_intent_id, amount_cents=None) -> dict:
    """Refund an already-captured charge (full refund when no amount
    is given). Returns {"id", "status", "amount_cents"}."""
    stripe = _stripe()
    kwargs = {"payment_intent": payment_intent_id}
    if amount_cents is not None:
        kwargs["amount"] = int(amount_cents)
    try:
        refund = stripe.Refund.create(**kwargs)
    except Exception as exc:
        _wrap_error(exc)
    return {
        "id": refund.id,
        "status": refund.status,
        "amount_cents": int(refund.amount),
    }


def create_off_session_payment_intent(amount_cents, customer_id,
                                      payment_method_id, booking_id,
                                      description="Noel Chauffer ride") -> dict:
    """Charge a saved card without the customer present — used only
    when the final fare at ride end is HIGHER than the authorized
    hold (extra miles / waiting): the authorized amount is captured
    first and the difference is charged here. Returns {"id",
    "status", "amount_cents", "card"}."""
    stripe = _stripe()
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount_cents),
            currency=CURRENCY,
            customer=customer_id,
            payment_method=payment_method_id,
            confirm=True,
            off_session=True,
            payment_method_types=["card"],
            statement_descriptor=STATEMENT_DESCRIPTOR,
            description=description,
            metadata={"booking_id": str(booking_id)},
        )
    except Exception as exc:
        _wrap_error(exc)
    return {
        "id": intent.id,
        "status": intent.status,
        "amount_cents": int(intent.amount),
        "card": _card_view(intent.payment_method) if getattr(intent, "payment_method", None) else {},
    }


# ------------------------------------------------------- Connect: drivers --

def create_connect_account(email) -> dict:
    """Create a Stripe Connect Express account for a driver, so he can
    receive payouts (weekly or instant) to his own debit card. The
    driver finishes onboarding in Stripe's hosted flow — Noel never
    sees his bank details."""
    stripe = _stripe()
    try:
        account = stripe.Account.create(
            type="express", country="US", email=email or None,
            capabilities={"transfers": {"requested": True}},
        )
    except Exception as exc:
        _wrap_error(exc)
    return {"id": account.id}


def create_account_link(account_id, return_url, refresh_url) -> dict:
    """Hosted onboarding link for a Connect account."""
    stripe = _stripe()
    try:
        link = stripe.AccountLink.create(
            account=account_id, return_url=return_url, refresh_url=refresh_url,
            type="account_onboarding",
        )
    except Exception as exc:
        _wrap_error(exc)
    return {"url": link.url}


def retrieve_account(account_id) -> dict:
    """Onboarding / payout readiness of a Connect account."""
    stripe = _stripe()
    try:
        account = stripe.Account.retrieve(account_id)
    except Exception as exc:
        _wrap_error(exc)
    return {
        "id": account.id,
        "charges_enabled": bool(getattr(account, "charges_enabled", False)),
        "payouts_enabled": bool(getattr(account, "payouts_enabled", False)),
        "details_submitted": bool(getattr(account, "details_submitted", False)),
    }


def list_payout_cards(account_id) -> list:
    """Debit cards on a Connect account that can receive instant
    payouts (external accounts of type "card"). Bank accounts are
    NOT listed here — they are the weekly-payout destination and
    are never shown beyond the masked last 4 the driver already
    gave at registration. Returns card views (brand / last4 /
    expiry only)."""
    stripe = _stripe()
    try:
        external = stripe.Account.list_external_accounts(
            account_id, object="card", limit=100)
    except Exception as exc:
        _wrap_error(exc)
    cards = []
    for acct in getattr(external, "data", []) or []:
        if getattr(acct, "object", None) != "card":
            continue
        cards.append({
            "id": getattr(acct, "id", None),
            "brand": getattr(acct, "brand", None),
            "last4": getattr(acct, "last4", None),
            "exp_month": getattr(acct, "exp_month", None),
            "exp_year": getattr(acct, "exp_year", None),
        })
    return cards


def create_transfer(amount_cents, destination_account_id, description="Noel Chauffer driver payout") -> dict:
    """Move money from the platform balance to a driver's Connect
    account, so it can be paid out to his debit card."""
    stripe = _stripe()
    try:
        transfer = stripe.Transfer.create(
            amount=int(amount_cents), currency=CURRENCY,
            destination=destination_account_id, description=description,
        )
    except Exception as exc:
        _wrap_error(exc)
    return {"id": transfer.id, "amount_cents": int(transfer.amount)}


def create_instant_payout(account_id, amount_cents) -> dict:
    """Pay out a Connect account's balance to the driver's eligible
    debit card immediately (Stripe Instant Payouts). Stripe deducts
    its 1.5% fee from the payout. Returns {"id", "status",
    "amount_cents"} — status "paid" means the money is on its way."""
    stripe = _stripe()
    try:
        payout = stripe.Payout.create(
            amount=int(amount_cents), currency=CURRENCY, method="instant",
            stripe_account=account_id,
        )
    except Exception as exc:
        _wrap_error(exc)
    return {
        "id": payout.id,
        "status": payout.status,
        "amount_cents": int(payout.amount),
    }


def instant_payout_fee_cents(amount_cents) -> int:
    """Stripe's 1.5% instant-payout fee, in cents."""
    return int((Decimal(int(amount_cents)) * INSTANT_PAYOUT_FEE_RATE).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP))


def instant_payout_net_cents(amount_cents) -> int:
    """What the driver receives from an instant payout of
    `amount_cents` (gross minus the 1.5% fee)."""
    return int(amount_cents) - instant_payout_fee_cents(amount_cents)
