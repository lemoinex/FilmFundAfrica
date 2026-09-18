"""Schemas des offres, abonnements et paiements."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PaymentStatus, PlanCode, SubscriptionStatus
from app.schemas.common import ORMModel


class PlanRead(ORMModel):
    id: str
    code: PlanCode
    name: str
    description: str
    price_amount: float
    price_currency: str
    billing_period: str
    max_projects: int
    monthly_ai_credits: int
    allows_export: bool
    allows_matching: bool
    allows_collaboration: bool
    allows_advanced_budget: bool
    sort_order: int


class SubscriptionRead(BaseModel):
    plan: PlanRead
    status: SubscriptionStatus
    started_at: datetime | None = None
    #: Date jusqu'à laquelle l'offre reste active, y compris après résiliation.
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None
    #: L'offre est-elle encore ouverte ? Reste vrai après une résiliation,
    #: jusqu'à la fin de la période déjà payée.
    is_active: bool
    #: L'abonnement se reconduira-t-il ? Faux dès qu'il est résilié.
    is_renewing: bool = False
    ai_credits_remaining: int


class CheckoutRequestBody(BaseModel):
    plan_code: PlanCode
    #: Numéro mobile money, quand le prestataire en demande un.
    phone_number: str | None = Field(default=None, max_length=32)


class PaymentRead(ORMModel):
    id: str
    provider: str
    provider_reference: str
    status: PaymentStatus
    amount: float
    currency: str
    phone_number: str | None = None
    #: `None` quand le prestataire déclenche une invite sur le téléphone.
    checkout_url: str | None = None
    failure_reason: str | None = None
    paid_at: datetime | None = None
    created_at: datetime


class CheckoutResponse(BaseModel):
    payment: PaymentRead
    #: Marche à suivre quand il n'y a pas de page de paiement à ouvrir.
    instructions: str | None = None
