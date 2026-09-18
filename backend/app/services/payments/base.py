"""Contrat commun a tous les prestataires de paiement.

Aucune partie du code metier n'appelle un prestataire directement : tout passe
par `PaymentProvider`, comme l'IA passe par `AIProvider`. Brancher CinetPay,
PayDunya, Wave ou Flutterwave revient a ecrire une classe de plus et a changer
`PAYMENT_PROVIDER`, sans toucher au cycle d'abonnement.

Ce que doit fournir une implementation reelle :

1. `create_checkout` — ouvrir une transaction chez le prestataire et renvoyer
   l'URL (ou l'invite mobile money) vers laquelle envoyer la personne, plus une
   reference que le prestataire rappellera dans ses notifications ;
2. `verify_signature` — authentifier la notification recue. Sans cette
   verification, n'importe qui pourrait s'offrir un abonnement en appelant le
   webhook ;
3. `parse_event` — traduire la charge utile du prestataire en un statut et une
   reference, seuls elements dont le cycle d'abonnement a besoin.

Aucun prestataire reel n'est implemente ici : cela demande un compte, des
cles, et la documentation exacte de son API. Ecrire une integration « de
memoire » produirait un code qui compile et qui echoue en production.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.models.enums import PaymentStatus


@dataclass(slots=True)
class CheckoutRequest:
    """Ce que le cycle d'abonnement sait au moment d'ouvrir un paiement."""

    reference: str
    amount: float
    currency: str
    plan_name: str
    customer_email: str
    phone_number: str | None = None
    return_url: str = ""


@dataclass(slots=True)
class CheckoutSession:
    """Ou envoyer la personne, et sous quelle reference la retrouver."""

    #: Reference cote prestataire. Peut differer de celle demandee : c'est
    #: celle-ci qui fait foi dans les notifications.
    provider_reference: str
    #: `None` quand le prestataire declenche une invite sur le telephone au
    #: lieu d'ouvrir une page.
    checkout_url: str | None = None
    instructions: str | None = None


@dataclass(slots=True)
class PaymentEvent:
    """Notification du prestataire, traduite en termes du domaine."""

    provider_reference: str
    status: PaymentStatus
    raw: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None


class PaymentProvider(ABC):
    """Interface minimale d'un prestataire de paiement."""

    name: str = "abstract"
    #: Vrai si le prestataire notifie lui-meme le resultat (webhook). Faux pour
    #: un encaissement hors ligne, valide a la main par l'administration.
    sends_webhooks: bool = True

    @abstractmethod
    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        """Ouvre une transaction, ou leve `PaymentProviderError`."""

    @abstractmethod
    def verify_signature(self, body: bytes, signature: str | None) -> bool:
        """Authentifie une notification entrante."""

    @abstractmethod
    def parse_event(self, payload: dict[str, Any]) -> PaymentEvent:
        """Traduit la charge utile du prestataire, ou leve `PaymentProviderError`."""
