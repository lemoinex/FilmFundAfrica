"""Routes d'abonnement : offres, souscription, paiements, notifications."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.core.rate_limit import rate_limit_auth
from app.models.billing import SubscriptionPlan
from app.models.enums import PaymentStatus, SubscriptionStatus
from app.schemas.billing import (
    CheckoutRequestBody,
    CheckoutResponse,
    PaymentRead,
    PlanRead,
    SubscriptionRead,
)
from app.schemas.common import Message
from app.services.credit_service import CreditService
from app.services.payments import PaymentEvent, get_provider
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger("filmfund.billing")

router = APIRouter(prefix="/billing", tags=["Abonnement"])


@router.get("/plans", response_model=list[PlanRead], summary="Offres disponibles")
def list_plans(db: DbSession) -> list[PlanRead]:
    """Les prix viennent de la base, jamais du frontend."""
    CreditService(db).ensure_plans()
    db.commit()
    plans = db.scalars(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.sort_order)
    )
    return [PlanRead.model_validate(plan) for plan in plans]


@router.get("/subscription", response_model=SubscriptionRead, summary="Mon abonnement")
def my_subscription(db: DbSession, current_user: CurrentUser) -> SubscriptionRead:
    service = SubscriptionService(db)
    plan = CreditService(db).plan_for_user(current_user)
    subscription = current_user.subscription

    return SubscriptionRead(
        plan=PlanRead.model_validate(plan),
        status=subscription.status if subscription else SubscriptionStatus.ACTIVE,
        started_at=subscription.started_at if subscription else None,
        current_period_end=subscription.current_period_end if subscription else None,
        cancelled_at=subscription.cancelled_at if subscription else None,
        is_active=service.has_access(current_user),
        is_renewing=service.is_renewing(current_user),
        ai_credits_remaining=current_user.ai_credits_remaining,
    )


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
    summary="Souscrire à une offre",
)
def start_checkout(
    payload: CheckoutRequestBody, db: DbSession, current_user: CurrentUser
) -> CheckoutResponse:
    """Ouvre un paiement. **Rien n'est accordé tant qu'il n'a pas abouti.**

    En mobile money, la personne doit encore valider sur son téléphone : c'est
    la notification du prestataire — ou la validation d'un administrateur pour
    un encaissement hors ligne — qui active l'offre.
    """
    result = SubscriptionService(db).start_checkout(
        current_user, payload.plan_code, payload.phone_number
    )
    return CheckoutResponse(
        payment=PaymentRead.model_validate(result.payment),
        instructions=result.instructions,
    )


@router.get("/payments", response_model=list[PaymentRead], summary="Mes paiements")
def my_payments(db: DbSession, current_user: CurrentUser) -> list[PaymentRead]:
    return [
        PaymentRead.model_validate(payment)
        for payment in SubscriptionService(db).list_payments(current_user)
    ]


@router.post("/cancel", response_model=Message, summary="Résilier mon abonnement")
def cancel(db: DbSession, current_user: CurrentUser) -> Message:
    """Résilier ne coupe pas l'accès : la période déjà payée va à son terme."""
    subscription = SubscriptionService(db).cancel(current_user)
    until = subscription.current_period_end
    return Message(
        detail=(
            "Abonnement résilié. Votre offre reste active jusqu'au "
            f"{until:%d/%m/%Y}." if until else "Abonnement résilié."
        )
    )


@router.post(
    "/simulate/{reference}",
    response_model=Message,
    summary="Simuler l'issue d'un paiement (développement)",
)
def simulate_payment(
    reference: str, db: DbSession, current_user: CurrentUser, succeed: bool = True
) -> Message:
    """Joue la notification à la place du prestataire simulé.

    Réservée à `ENVIRONMENT=development` **et** `PAYMENT_PROVIDER=mock` : sans
    ce double verrou, cette route offrirait des abonnements gratuits. Elle
    existe pour que le parcours complet soit cliquable sans compte prestataire.
    """
    if not settings.is_development or settings.payment_provider != "mock":
        raise AppError(
            "Route de simulation indisponible : elle n'existe qu'en développement "
            "avec le prestataire simulé.",
            status_code=status.HTTP_404_NOT_FOUND,
            code="simulation_unavailable",
        )

    service = SubscriptionService(db)
    payment = service.get_owned_payment_by_reference(reference, current_user)
    event = PaymentEvent(
        provider_reference=payment.provider_reference,
        status=PaymentStatus.SUCCEEDED if succeed else PaymentStatus.FAILED,
        raw={"simulated": True},
        failure_reason=None if succeed else "Paiement refusé (simulation).",
    )
    updated = service.apply_event(event)
    return Message(detail=f"Paiement simulé : {updated.status}.")


@router.post(
    "/webhook",
    response_model=Message,
    dependencies=[Depends(rate_limit_auth)],
    summary="Notification du prestataire de paiement",
)
async def payment_webhook(
    request: Request,
    db: DbSession,
    x_payment_signature: str | None = Header(default=None),
) -> Message:
    """Reçoit et applique une notification de paiement.

    La signature est vérifiée avant toute lecture du contenu : sans elle,
    n'importe qui s'offrirait un abonnement en appelant cette route. Une
    notification déjà traitée est acceptée sans être rejouée — tous les
    prestataires renvoient la même plusieurs fois.
    """
    body = await request.body()
    provider = get_provider()

    if not provider.verify_signature(body, x_payment_signature):
        logger.warning(
            "notification de paiement rejetée : signature invalide",
            extra={"event": "payment_webhook_rejected"},
        )
        raise AppError(
            "Signature de notification invalide.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_payment_signature",
        )

    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise AppError("Notification illisible.", code="invalid_payment_payload") from exc

    event = provider.parse_event(payload)
    payment = SubscriptionService(db, provider=provider).apply_event(event)
    return Message(detail=f"Notification traitée : paiement {payment.status}.")
