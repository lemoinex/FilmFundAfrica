"""Couche paiement : contrat, prestataires livres, erreurs."""

from app.services.payments.base import (
    CheckoutRequest,
    CheckoutSession,
    PaymentEvent,
    PaymentProvider,
)
from app.services.payments.providers import (
    PROVIDERS,
    ManualProvider,
    MockProvider,
    PaymentProviderError,
    get_provider,
    new_reference,
    sign_payload,
    verify_hmac_signature,
)

__all__ = [
    "CheckoutRequest",
    "CheckoutSession",
    "PaymentEvent",
    "PaymentProvider",
    "PaymentProviderError",
    "PROVIDERS",
    "ManualProvider",
    "MockProvider",
    "get_provider",
    "new_reference",
    "sign_payload",
    "verify_hmac_signature",
]
