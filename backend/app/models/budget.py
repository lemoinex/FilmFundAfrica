"""Budget, lignes budgetaires et plan de financement (structure Phase 4)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BudgetCategory, FundingSourceType

if TYPE_CHECKING:  # pragma: no cover
    from app.models.project import Project


class Budget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "budgets"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(10), default="XAF", nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship(back_populates="budget")
    items: Mapped[list[BudgetItem]] = relationship(
        back_populates="budget", cascade="all, delete-orphan", order_by="BudgetItem.sort_order"
    )


class BudgetItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "budget_items"

    budget_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("budgets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[BudgetCategory] = mapped_column(
        SAEnum(BudgetCategory, native_enum=False, length=25), nullable=False
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    budget: Mapped[Budget] = relationship(back_populates="items")


class FundingPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "funding_plans"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(10), default="XAF", nullable=False)
    total_budget: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    project: Mapped[Project] = relationship(back_populates="funding_plan")
    lines: Mapped[list[FundingPlanLine]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )

    @property
    def secured_amount(self) -> float:
        return sum(line.amount for line in self.lines if line.is_secured)

    @property
    def sought_amount(self) -> float:
        return max(self.total_budget - self.secured_amount, 0.0)

    @property
    def funded_percentage(self) -> float:
        if self.total_budget <= 0:
            return 0.0
        return round(self.secured_amount / self.total_budget * 100, 2)


class FundingPlanLine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "funding_plan_lines"

    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("funding_plans.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_type: Mapped[FundingSourceType] = mapped_column(
        SAEnum(FundingSourceType, native_enum=False, length=25), nullable=False
    )
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_secured: Mapped[bool] = mapped_column(default=False, nullable=False)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    plan: Mapped[FundingPlan] = relationship(back_populates="lines")


class ProductionSchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Calendrier simple : une ligne par phase de production."""

    __tablename__ = "production_schedules"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    phase: Mapped[BudgetCategory] = mapped_column(
        SAEnum(BudgetCategory, native_enum=False, length=25), nullable=False
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
