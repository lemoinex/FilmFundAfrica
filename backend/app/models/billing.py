"""Plans, abonnements et consommation IA.

Les prix et les quotas de credits sont stockes en base afin d'etre
configurables depuis l'administration (jamais codes en dur cote frontend).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AIOperation, PlanCode, SubscriptionStatus

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class SubscriptionPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subscription_plans"

    code: Mapped[PlanCode] = mapped_column(
        SAEnum(PlanCode, native_enum=False, length=20), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    price_currency: Mapped[str] = mapped_column(String(10), default="XAF", nullable=False)
    billing_period: Mapped[str] = mapped_column(String(20), default="MONTHLY", nullable=False)

    max_projects: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    monthly_ai_credits: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    allows_export: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allows_matching: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allows_collaboration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allows_advanced_budget: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="plan")


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, native_enum=False, length=20),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="subscription")
    plan: Mapped[SubscriptionPlan] = relationship(back_populates="subscriptions")


class AIUsage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Journal de chaque appel IA : observabilite, couts et quotas."""

    __tablename__ = "ai_usage"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    operation: Mapped[AIOperation] = mapped_column(
        SAEnum(AIOperation, native_enum=False, length=30), nullable=False
    )
    document_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credits_consumed: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="ai_usage")
