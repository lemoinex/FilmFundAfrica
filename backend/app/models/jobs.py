"""Taches de generation IA.

Une generation longue (un scenario de 110 pages enchaine plusieurs appels au
fournisseur) ne peut pas tenir une requete HTTP ouverte : la requete est
acceptee, une tache est enregistree, et un worker l'execute.

La table est la source de verite : Redis ne porte que le signal de reveil du
worker. Un Redis vide au redemarrage ne perd donc aucune tache — le worker les
retrouve en base.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DocumentType, JobKind, JobStatus

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class GenerationJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "generation_jobs"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: Renseigne des que le document existe : pour un retravail, des la creation
    #: de la tache ; pour une generation, quand elle aboutit.
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    kind: Mapped[JobKind] = mapped_column(
        SAEnum(JobKind, native_enum=False, length=30), nullable=False
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, native_enum=False, length=30), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, native_enum=False, length=20),
        default=JobStatus.QUEUED,
        index=True,
        nullable=False,
    )

    #: Passes prevues (> 1 pour un scenario long) et passes deja ecrites.
    total_passes: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    completed_passes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    #: Requete d'origine, rejouee telle quelle par le worker.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    #: `GenerationResult` serialise, renseigne en cas de succes.
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Credits debites a la mise en file, rembourses si la tache echoue. Sans
    #: cette reserve, on pourrait empiler des taches au-dela de son quota.
    credits_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship()
