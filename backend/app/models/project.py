"""Projets audiovisuels et personnages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ProjectStatus, ProjectType

if TYPE_CHECKING:  # pragma: no cover
    from app.models.budget import Budget, FundingPlan
    from app.models.document import Document
    from app.models.funding import ProjectFundingMatch
    from app.models.user import User


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "projects"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    project_type: Mapped[ProjectType] = mapped_column(
        SAEnum(ProjectType, native_enum=False, length=20), nullable=False
    )
    genre: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    language: Mapped[str] = mapped_column(String(60), default="Français", nullable=False)
    #: Duree cible en minutes (10, 30, 52, 90, 100, 110, 120...).
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)

    logline: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    theme: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Champs alimentes par l'assistant de creation en 7 etapes.
    concept: Mapped[str | None] = mapped_column(Text, nullable=True)
    stakes: Mapped[str | None] = mapped_column(Text, nullable=True)
    director_vision: Mapped[str | None] = mapped_column(Text, nullable=True)
    objectives: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus, native_enum=False, length=20),
        default=ProjectStatus.IDEA,
        nullable=False,
    )
    #: Dernier Project Readiness Score calcule (0-100), null si jamais calcule.
    readiness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    owner: Mapped[User] = relationship(back_populates="projects")
    characters: Mapped[list[Character]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Character.sort_order",
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    funding_matches: Mapped[list[ProjectFundingMatch]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    budget: Mapped[Budget | None] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    funding_plan: Mapped[FundingPlan | None] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )


class Character(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "characters"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    age: Mapped[str | None] = mapped_column(String(60), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    arc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    project: Mapped[Project] = relationship(back_populates="characters")
