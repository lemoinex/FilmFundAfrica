"""Prestataires livres : encaissement manuel et bac a sable.

`manual` est le comportement d'avant cette phase, rendu explicite : la
personne paie hors ligne (virement, dépôt mobile money sur le compte de
l'editeur) et l'administration valide. C'est le mode utilisable tout de suite,
sans contrat prestataire.

`mock` simule un prestataire complet pour le developpement et les tests : il
signe ses notifications avec le meme secret que celui attendu a l'entree, ce
qui permet d'exercer la chaine entiere — y compris le rejet d'une signature
invalide — sans compte chez qui que ce soit.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from app.core.config import settings
from app.core.errors import AppError
from app.models.enums import PaymentStatus
from app.services.payments.base import (
    CheckoutRequest,
    CheckoutSession,
    PaymentEvent,
    PaymentProvider,
)


class PaymentProviderError(AppError):
    status_code = 502
    code = "payment_provider_error"


class ManualProvider(PaymentProvider):
    """Encaissement hors ligne, valide par l'administration."""

    name = "manual"
    sends_webhooks = False

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        return CheckoutSession(
            provider_reference=request.reference,
            checkout_url=None,
            instructions=(
                f"Réglez {request.amount:,.0f} {request.currency} pour l'offre "
                f"« {request.plan_name} », puis transmettez la référence "
                f"{request.reference} à l'équipe. L'abonnement est activé dès "
                "vérification du paiement."
            ).replace(",", " "),
        )

    def verify_signature(self, body: bytes, signature: str | None) -> bool:
        # Ce prestataire ne notifie rien : aucune signature n'est acceptee.
        return False

    def parse_event(self, payload: dict[str, Any]) -> PaymentEvent:
        raise PaymentProviderError("payment.manualNoNotification")


class MockProvider(PaymentProvider):
    """Prestataire simule, deterministe et hors ligne."""

    name = "mock"

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        reference = f"mock_{request.reference}"
        return CheckoutSession(
            provider_reference=reference,
            checkout_url=f"{settings.frontend_url}/paiement/simulation?reference={reference}",
            instructions=(
                "Prestataire simulé (PAYMENT_PROVIDER=mock) : aucun paiement réel "
                "n'est encaissé."
            ),
        )

    def verify_signature(self, body: bytes, signature: str | None) -> bool:
        return verify_hmac_signature(body, signature)

    def parse_event(self, payload: dict[str, Any]) -> PaymentEvent:
        reference = str(payload.get("reference") or "").strip()
        if not reference:
            raise PaymentProviderError("payment.referenceMissing")

        raw_status = str(payload.get("status") or "").upper()
        try:
            status = PaymentStatus(raw_status)
        except ValueError as exc:
            raise PaymentProviderError(
                "payment.unknownStatus", params={"status": raw_status}
            ) from exc

        return PaymentEvent(
            provider_reference=reference,
            status=status,
            raw=payload,
            failure_reason=payload.get("failure_reason"),
        )


def sign_payload(body: bytes) -> str:
    """Signature HMAC-SHA256 d'une charge utile, avec le secret configuré."""
    return hmac.new(
        settings.payment_webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()


def verify_hmac_signature(body: bytes, signature: str | None) -> bool:
    """Compare la signature en temps constant.

    Sans secret configuré, aucune notification n'est acceptée : une
    vérification qui s'ouvre quand la configuration est incomplète ne protège
    rien du tout.
    """
    if not settings.payment_webhook_secret or not signature:
        return False
    return hmac.compare_digest(sign_payload(body), signature.strip())


PROVIDERS: dict[str, type[PaymentProvider]] = {
    ManualProvider.name: ManualProvider,
    MockProvider.name: MockProvider,
}


def get_provider(name: str | None = None) -> PaymentProvider:
    code = (name or settings.payment_provider).strip().lower()
    provider = PROVIDERS.get(code)
    if provider is None:  # pragma: no cover - verrouille par la configuration
        raise PaymentProviderError("payment.unknownProvider", params={"code": code})
    return provider()


def new_reference() -> str:
    """Référence interne d'un paiement, imprévisible et lisible."""
    return f"ffa_{secrets.token_hex(12)}"
