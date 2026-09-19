"""Persistance de la chaine d'agents : dossier, passages, constats, traces.

Deux formes de donnees cohabitent, et le decoupage n'est pas arbitraire.

Les **sections du dossier** sont gardees en JSON : un plan de production et une
analyse d'impact n'ont pas la meme forme d'un projet a l'autre, et les figer en
colonnes reviendrait a decider aujourd'hui de ce qu'un agent aura le droit de
produire demain.

Les **constats** et les **traces de modification** sont normalises. On veut
pouvoir demander « quels blocages restent ouverts » ou « qui a touche au
budget, et pourquoi » sans relire du JSON : c'est exactement ce que la
tracabilite exige pour servir a quelque chose.

`validation_history` n'est pas stockee : chaque etape de validateur porte deja
son verdict, et la recalculer evite deux sources de verite qui divergent.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AgentRole, JobStatus, Severity, ValidationVerdict

if TYPE_CHECKING:  # pragma: no cover
    from app.models.project import Project

_ROLE = SAEnum(AgentRole, native_enum=False, length=30)
_SEVERITY = SAEnum(Severity, native_enum=False, length=10)
_VERDICT = SAEnum(ValidationVerdict, native_enum=False, length=25)


class ProjectDossier(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Etat vivant du dossier, un par projet.

    Distinct de `projects` a dessein : ces sections sont produites par les
    agents, alors que la fiche projet porte ce que l'auteur a saisi. Les
    confondre ferait ecraser la saisie de l'auteur par une production d'agent.
    """

    __tablename__ = "project_dossiers"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    project_identity: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    #: `TrackedFact` serialise : la valeur et son statut de provenance.
    logline: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    concept: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    synopsis: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    characters: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    screenplay: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    director_vision: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    production_plan: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    budget: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    financing_plan: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    cultural_analysis: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    impact_analysis: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    final_documents: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    project: Mapped[Project] = relationship()
    runs: Mapped[list[AgentRun]] = relationship(
        back_populates="dossier",
        cascade="all, delete-orphan",
        order_by="AgentRun.created_at.desc()",
    )
    findings: Mapped[list[DossierFinding]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan"
    )
    modifications: Mapped[list[DossierModification]] = relationship(
        back_populates="dossier",
        cascade="all, delete-orphan",
        order_by="DossierModification.created_at",
    )


class AgentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Un passage complet de la chaine, reprises comprises."""

    __tablename__ = "agent_runs"

    dossier_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_dossiers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, native_enum=False, length=20), default=JobStatus.RUNNING, nullable=False
    )
    verdict: Mapped[ValidationVerdict | None] = mapped_column(_VERDICT, nullable=True)
    rounds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Arret sur la limite de tours.
    exhausted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: Arret parce qu'un tour n'a rien change.
    stalled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: Renseigne quand le passage echoue, pour ne pas avoir a fouiller les logs.
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dossier: Mapped[ProjectDossier] = relationship(back_populates="runs")
    steps: Mapped[list[AgentStep]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentStep.sequence",
    )


class AgentStep(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Une execution d'agent : ce qu'il a dit, et ce qu'elle a coute.

    La telemetrie est conservee ici plutot que deduite : comparer le cout d'une
    version de consigne a l'autre est la raison d'etre du versionnement des
    agents.
    """

    __tablename__ = "agent_steps"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: Rang dans le passage, reprises comprises : un meme agent y figure
    #: plusieurs fois, et l'ordre est ce qui permet de relire l'histoire.
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    agent: Mapped[AgentRole] = mapped_column(_ROLE, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), nullable=False)

    analysis: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    next_agent_instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verdict: Mapped[ValidationVerdict | None] = mapped_column(_VERDICT, nullable=True)
    changeset: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    decisions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    run: Mapped[AgentRun] = relationship(back_populates="steps")


class DossierFinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Un constat ouvert sur le dossier.

    Resolu, il n'est pas supprime mais date : savoir qu'un blocage a existe et
    qui l'a leve fait partie de l'histoire du dossier.
    """

    __tablename__ = "dossier_findings"

    dossier_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_dossiers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    severity: Mapped[Severity] = mapped_column(_SEVERITY, nullable=False)
    element: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    #: Agent capable de corriger. Sans lui, un constat n'est jamais traite.
    owner: Mapped[AgentRole | None] = mapped_column(_ROLE, nullable=True)
    suggested_correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dossier: Mapped[ProjectDossier] = relationship(back_populates="findings")


class DossierModification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Trace d'une modification : qui, quoi, pourquoi, avec quel impact."""

    __tablename__ = "dossier_modifications"

    dossier_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project_dossiers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    agent: Mapped[AgentRole] = mapped_column(_ROLE, nullable=False)
    element: Mapped[str] = mapped_column(String(255), nullable=False)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    validation_status: Mapped[ValidationVerdict | None] = mapped_column(_VERDICT, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    dossier: Mapped[ProjectDossier] = relationship(back_populates="modifications")
