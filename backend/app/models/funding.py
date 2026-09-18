"""Base des opportunites de financement et resultats de matching.

Les tables sont creees des la Phase 1 pour que la Phase 3 (Funding Intelligence)
puisse s'y brancher sans migration structurante.

Regle produit : une opportunite n'est jamais presentee comme active sans
`source_url`, `source_name` et `last_verified_at`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import FundingCategory, FundingStatus

if TYPE_CHECKING:  # pragma: no cover
    from app.models.project import Project


class FundingOpportunity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "funding_opportunities"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    organization: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: Listes stockees en CSV pour rester portable SQLite/PostgreSQL.
    eligible_countries: Mapped[str] = mapped_column(Text, default="", nullable=False)
    project_types: Mapped[str] = mapped_column(Text, default="", nullable=False)
    genres: Mapped[str] = mapped_column(Text, default="", nullable=False)
    languages: Mapped[str] = mapped_column(Text, default="", nullable=False)

    category: Mapped[FundingCategory] = mapped_column(
        SAEnum(FundingCategory, native_enum=False, length=25),
        default=FundingCategory.FUND,
        nullable=False,
    )
    minimum_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    maximum_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="EUR", nullable=False)

    deadline: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    requirements: Mapped[str] = mapped_column(Text, default="", nullable=False)

    status: Mapped[FundingStatus] = mapped_column(
        SAEnum(FundingStatus, native_enum=False, length=20),
        default=FundingStatus.UNVERIFIED,
        nullable=False,
    )
    #: Tracabilite obligatoire de la source.
    source: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: Marque les enregistrements du seed : "DEMO DATA - NOT REAL".
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    requirement_items: Mapped[list[FundingRequirement]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
    matches: Mapped[list[ProjectFundingMatch]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )


class FundingRequirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "funding_requirements"

    opportunity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("funding_opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    #: Type de document attendu (voir DocumentType), si applicable.
    required_document_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    opportunity: Mapped[FundingOpportunity] = relationship(back_populates="requirement_items")


class ProjectFundingMatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "project_funding_matches"
    __table_args__ = (
        UniqueConstraint("project_id", "opportunity_id", name="uq_match_project_opportunity"),
    )

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    opportunity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("funding_opportunities.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    #: Indicateur d'aide a la decision (0-100), jamais une garantie de financement.
    compatibility_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    met_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="funding_matches")
    opportunity: Mapped[FundingOpportunity] = relationship(back_populates="matches")
