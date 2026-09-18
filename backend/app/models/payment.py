"""Paiements d'abonnement.

Une ligne par tentative de paiement, jamais ecrasee : un dossier de
facturation se relit, il ne se resume pas a l'etat courant de l'abonnement.

La reference du prestataire porte une contrainte d'unicite. C'est elle qui
rend le traitement des notifications idempotent : un meme paiement notifie
deux fois — ce que tous les prestataires font — ne cree pas deux lignes et ne
prolonge pas l'abonnement deux fois.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentStatus

if TYPE_CHECKING:  # pragma: no cover
    from app.models.billing import SubscriptionPlan
    from app.models.user import User


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payments"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False
    )

    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    #: Identifiant cote prestataire. Unique : c'est la cle d'idempotence.
    provider_reference: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, native_enum=False, length=20),
        default=PaymentStatus.PENDING,
        index=True,
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="XAF", nullable=False)
    #: Numero mobile money, quand le prestataire en demande un.
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    #: Derniere notification recue, telle quelle : une contestation se tranche
    #: sur ce que le prestataire a envoye, pas sur notre interpretation.
    provider_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship()
    plan: Mapped[SubscriptionPlan] = relationship()
