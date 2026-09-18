"""Cycle de vie des abonnements : paiement, activation, résiliation, échéance.

Trois règles portent ce module :

* **Un paiement donne des droits, il ne les suppose pas.** Tant qu'il n'est pas
  `SUCCEEDED`, rien n'est accordé : en mobile money, la personne doit encore
  valider sur son téléphone, et beaucoup ne le font pas.
* **Les notifications sont idempotentes.** Tous les prestataires renvoient la
  même notification plusieurs fois. La référence porte une contrainte
  d'unicité, et une notification déjà traitée ne prolonge pas l'abonnement une
  seconde fois.
* **Résilier n'est pas couper.** Une résiliation vaut jusqu'à la fin de la
  période déjà payée ; c'est l'échéance qui fait redescendre à l'offre
  gratuite.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.models.billing import Subscription, SubscriptionPlan
from app.models.enums import PaymentStatus, PlanCode, SubscriptionStatus
from app.models.payment import Payment
from app.models.user import User
from app.services.credit_service import CreditService
from app.services.payments import (
    CheckoutRequest,
    PaymentEvent,
    PaymentProvider,
    get_provider,
    new_reference,
)

logger = logging.getLogger("filmfund.subscriptions")

#: Durée d'une période d'abonnement. Les offres sont mensuelles.
PERIOD_DAYS = 30


@dataclass(slots=True)
class CheckoutResult:
    """Paiement ouvert, et marche à suivre quand il n'y a pas de page à ouvrir."""

    payment: Payment
    instructions: str | None = None


class SubscriptionService:
    def __init__(self, db: Session, provider: PaymentProvider | None = None) -> None:
        self.db = db
        self.credits = CreditService(db)
        self._provider = provider

    @property
    def provider(self) -> PaymentProvider:
        if self._provider is None:
            self._provider = get_provider()
        return self._provider

    # ------------------------------------------------------------------
    # Souscription
    # ------------------------------------------------------------------
    def start_checkout(
        self, user: User, plan_code: PlanCode, phone_number: str | None = None
    ) -> CheckoutResult:
        """Ouvre un paiement pour une offre, sans rien accorder encore."""
        plan = self.credits.get_plan(plan_code)
        if not plan.is_active:
            raise AppError("billing.planUnavailable", code="plan_unavailable")
        if plan.price_amount <= 0:
            raise AppError("billing.planIsFree", code="plan_is_free")

        current = self.credits.plan_for_user(user)
        if current.id == plan.id and self.is_renewing(user):
            raise AppError(
                "billing.planAlreadyActive",
                params={"plan": plan.name},
                code="plan_already_active",
            )

        reference = new_reference()
        session = self.provider.create_checkout(
            CheckoutRequest(
                reference=reference,
                amount=plan.price_amount,
                currency=plan.price_currency,
                plan_name=plan.name,
                customer_email=user.email,
                phone_number=phone_number,
                return_url=f"{settings.frontend_url}/abonnement",
            )
        )

        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            provider=self.provider.name,
            provider_reference=session.provider_reference,
            status=PaymentStatus.PENDING,
            amount=plan.price_amount,
            currency=plan.price_currency,
            phone_number=phone_number,
            checkout_url=session.checkout_url,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        logger.info("paiement ouvert", extra={"event": "payment_started"})
        return CheckoutResult(payment=payment, instructions=session.instructions)

    # ------------------------------------------------------------------
    # Notifications du prestataire
    # ------------------------------------------------------------------
    def apply_event(self, event: PaymentEvent) -> Payment:
        """Applique une notification. Rejouable sans effet supplémentaire."""
        payment = self.db.scalar(
            select(Payment).where(Payment.provider_reference == event.provider_reference)
        )
        if payment is None:
            raise NotFoundError("billing.paymentNotFound")

        payment.provider_payload = event.raw

        if payment.status.is_final:
            # Notification déjà traitée : on garde la trace, on ne rejoue rien.
            logger.info(
                "notification de paiement ignorée (déjà traitée)",
                extra={"event": "payment_event_replayed"},
            )
            self.db.commit()
            return payment

        payment.status = event.status
        payment.failure_reason = event.failure_reason

        if event.status is PaymentStatus.SUCCEEDED:
            payment.paid_at = datetime.now(UTC)
            self._activate(payment)
            logger.info("abonnement activé", extra={"event": "subscription_activated"})
        else:
            logger.info(
                "paiement non abouti : %s",
                event.status,
                extra={"event": "payment_not_completed"},
            )

        self.db.commit()
        self.db.refresh(payment)
        return payment

    def mark_paid_manually(self, payment: Payment, admin: User) -> Payment:
        """Valide un encaissement hors ligne, depuis l'administration."""
        if payment.status.is_final:
            raise AppError(
                "billing.paymentAlreadySettled",
                params={"status": payment.status},
                code="payment_already_settled",
            )
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = datetime.now(UTC)
        payment.provider_payload = {"validated_by": admin.email, "channel": "manual"}
        self._activate(payment)
        self.db.commit()
        self.db.refresh(payment)
        logger.info(
            "paiement validé manuellement", extra={"event": "payment_validated_manually"}
        )
        return payment

    # ------------------------------------------------------------------
    def _activate(self, payment: Payment) -> Subscription:
        """Bascule l'abonnement sur l'offre payée et recharge les crédits."""
        user = self.db.get(User, payment.user_id)
        plan = self.db.get(SubscriptionPlan, payment.plan_id)
        now = datetime.now(UTC)

        if user.subscription is None:
            user.subscription = Subscription(
                plan_id=plan.id, status=SubscriptionStatus.ACTIVE, started_at=now
            )
        subscription = user.subscription
        subscription.plan_id = plan.id
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.cancelled_at = None

        # Un renouvellement prolonge la période en cours au lieu de la
        # raccourcir : payer plus tôt ne doit jamais faire perdre des jours.
        base = self._period_end(subscription)
        start = base if base and base > now else now
        subscription.current_period_end = start + timedelta(days=PERIOD_DAYS)

        user.ai_credits_remaining = plan.monthly_ai_credits
        user.ai_credits_period_start = now
        self.db.flush()
        return subscription

    # ------------------------------------------------------------------
    # Résiliation et échéance
    # ------------------------------------------------------------------
    def cancel(self, user: User) -> Subscription:
        """Résilie : l'accès reste ouvert jusqu'à la fin de la période payée."""
        subscription = user.subscription
        if subscription is None or self.credits.plan_for_user(user).price_amount <= 0:
            raise AppError("billing.noPaidSubscription", code="no_paid_subscription")
        if subscription.status is SubscriptionStatus.CANCELLED:
            raise AppError("billing.subscriptionAlreadyCancelled", code="already_cancelled")

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(subscription)
        logger.info("abonnement résilié", extra={"event": "subscription_cancelled"})
        return subscription

    def expire_due(self) -> int:
        """Fait redescendre à l'offre gratuite les périodes échues.

        Appelée par la tâche planifiée : sans elle, un abonnement résilié —
        ou impayé — resterait ouvert indéfiniment.
        """
        now = datetime.now(UTC)
        free = self.credits.get_plan(PlanCode.FREE)
        downgraded = 0

        for subscription in self.db.scalars(
            select(Subscription).where(Subscription.plan_id != free.id)
        ):
            end = self._period_end(subscription)
            if end is None or end > now:
                continue
            subscription.plan_id = free.id
            subscription.status = SubscriptionStatus.EXPIRED
            user = self.db.get(User, subscription.user_id)
            if user is not None:
                user.ai_credits_remaining = min(
                    user.ai_credits_remaining, free.monthly_ai_credits
                )
            downgraded += 1

        if downgraded:
            self.db.commit()
            logger.info(
                "abonnements échus repassés à l'offre gratuite : %s",
                downgraded,
                extra={"event": "subscriptions_expired"},
            )
        return downgraded

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------
    def list_payments(self, user: User | None = None, limit: int = 50) -> list[Payment]:
        statement = select(Payment).order_by(Payment.created_at.desc()).limit(limit)
        if user is not None:
            statement = statement.where(Payment.user_id == user.id)
        return list(self.db.scalars(statement))

    def get_owned_payment(self, payment_id: str, user: User) -> Payment:
        payment = self.db.get(Payment, payment_id)
        if payment is None or payment.user_id != user.id:
            raise NotFoundError("billing.paymentNotFound")
        return payment

    def get_owned_payment_by_reference(self, reference: str, user: User) -> Payment:
        payment = self.db.scalar(
            select(Payment).where(Payment.provider_reference == reference)
        )
        if payment is None or payment.user_id != user.id:
            raise NotFoundError("billing.paymentNotFound")
        return payment

    def has_access(self, user: User) -> bool:
        """L'offre payée est-elle encore ouverte ?

        Une résiliation ne coupe pas : elle empêche le renouvellement. Tant que
        la période payée court, l'accès reste entier — c'est `expire_due` qui
        fait redescendre à l'offre gratuite, pas la résiliation.
        """
        subscription = user.subscription
        if subscription is None:
            return True  # Offre gratuite : rien à échoir.
        if subscription.status is SubscriptionStatus.EXPIRED:
            return False
        end = self._period_end(subscription)
        return end is None or end > datetime.now(UTC)

    def is_renewing(self, user: User) -> bool:
        """L'abonnement se reconduira-t-il ? Faux dès qu'il est résilié."""
        subscription = user.subscription
        return (
            subscription is not None
            and subscription.status is SubscriptionStatus.ACTIVE
            and self.has_access(user)
        )

    @staticmethod
    def _period_end(subscription: Subscription) -> datetime | None:
        """Fin de période, toujours comparable : SQLite rend des dates naïves."""
        end = subscription.current_period_end
        if end is not None and end.tzinfo is None:
            return end.replace(tzinfo=UTC)
        return end
