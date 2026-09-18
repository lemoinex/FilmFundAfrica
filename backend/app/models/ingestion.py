"""Candidats de la veille automatisee.

Le pipeline n8n n'ecrit JAMAIS dans `funding_opportunities`. Il depose ici des
candidats, qu'une personne valide ou rejette. C'est la traduction en base de
la regle produit : aucune donnee devinee ne doit atteindre un auteur qui
montera un dossier dessus.

L'empreinte de la source porte une contrainte d'unicite : une veille qui
retourne chaque semaine sur les memes pages ne remplit pas la file de doublons.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CandidateStatus

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class OpportunityCandidate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "opportunity_candidates"

    #: Nom lisible, tel qu'extrait de la source.
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    #: Tracabilite : sans elle, le candidat n'est pas accepte a l'entree.
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    #: SHA-256 de l'URL source : cle de deduplication entre deux passages.
    fingerprint: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    #: Champs extraits, tels quels. Rien n'est complete par defaut : un champ
    #: absent de la source reste absent.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    status: Mapped[CandidateStatus] = mapped_column(
        SAEnum(CandidateStatus, native_enum=False, length=20),
        default=CandidateStatus.PENDING,
        index=True,
        nullable=False,
    )
    reviewed_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Renseigne a l'approbation : le dispositif cree a partir de ce candidat.
    opportunity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("funding_opportunities.id", ondelete="SET NULL"), nullable=True
    )
    #: Derniere fois que la veille a revu ce candidat.
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    reviewed_by: Mapped[User | None] = relationship()
