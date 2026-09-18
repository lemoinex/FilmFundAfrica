"""Veille automatisee : depot des candidats, validation humaine.

Le pipeline n8n depose ici ce qu'il a trouve. Rien n'atteint la base vivante
sans qu'une personne l'ait approuve : c'est la regle produit (« aucune donnee
devinee ») appliquee a l'automatisation, et la raison d'etre de cette table
intermediaire.

Deux garde-fous a l'entree :

* **Pas de source, pas de candidat.** Un dispositif sans URL verifiable ne
  vaut rien pour un auteur qui montera un dossier dessus.
* **Deduplication par empreinte de la source.** Une veille hebdomadaire
  repasse sur les memes pages ; sans cela, la file de validation se remplirait
  de doublons jusqu'a devenir inutilisable.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.enums import CandidateStatus, FundingCategory, FundingStatus
from app.models.funding import FundingOpportunity
from app.models.ingestion import OpportunityCandidate
from app.models.user import User

logger = logging.getLogger("filmfund.ingestion")

#: Champs du candidat repris tels quels a l'approbation. Tout autre champ du
#: payload est ignore : la veille ne decide pas du schema de la base.
COPIED_FIELDS = (
    "organization",
    "description",
    "website",
    "country",
    "eligible_countries",
    "project_types",
    "genres",
    "languages",
    "category",
    "minimum_budget",
    "maximum_budget",
    "currency",
    "deadline",
    "opening_date",
    "application_url",
    "requirements",
)


#: Champs dont le type doit etre reconstruit : la veille parle JSON, ou une
#: date est une chaine et un montant peut en etre une.
_DATE_FIELDS = ("deadline", "opening_date")
_NUMBER_FIELDS = ("minimum_budget", "maximum_budget")


def _coerce(field: str, value: Any) -> Any:
    """Convertit une valeur du payload vers le type attendu par la base.

    Une valeur illisible est ecartee plutot que devinee : le champ reste vide,
    et la personne qui relit la source le complete si elle le juge utile. Une
    date inventee dans un dossier de financement coute un depot manque.
    """
    if value is None or value == "":
        return None
    if field in _DATE_FIELDS:
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            logger.warning(
                "date illisible écartée du candidat : %s=%r",
                field,
                value,
                extra={"event": "candidate_field_dropped"},
            )
            return None
    if field in _NUMBER_FIELDS:
        try:
            return float(value)
        except (TypeError, ValueError):
            logger.warning(
                "montant illisible écarté du candidat : %s=%r",
                field,
                value,
                extra={"event": "candidate_field_dropped"},
            )
            return None
    if field == "category":
        try:
            return FundingCategory(str(value).upper())
        except ValueError:
            return None
    return value


@dataclass(slots=True)
class SubmitResult:
    candidate: OpportunityCandidate
    #: Faux quand la source avait deja ete deposee : la veille est rejouable.
    created: bool


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    @staticmethod
    def fingerprint(source_url: str) -> str:
        return hashlib.sha256(source_url.strip().lower().encode("utf-8")).hexdigest()

    def submit(
        self, *, name: str, source_url: str, source_name: str, payload: dict[str, Any]
    ) -> SubmitResult:
        """Depose un candidat, ou rafraichit celui deja connu."""
        url = source_url.strip()
        if not url:
            raise AppError(
                "Un candidat sans URL source n'est pas recevable.",
                code="candidate_without_source",
            )

        digest = self.fingerprint(url)
        existing = self.db.scalar(
            select(OpportunityCandidate).where(OpportunityCandidate.fingerprint == digest)
        )
        now = datetime.now(UTC)

        if existing is not None:
            existing.last_seen_at = now
            # Un candidat deja tranche ne revient pas dans la file : la
            # decision humaine tient, meme si la veille repasse dessus.
            if existing.status is CandidateStatus.PENDING:
                existing.name = name.strip() or existing.name
                existing.payload = payload
            self.db.commit()
            self.db.refresh(existing)
            return SubmitResult(candidate=existing, created=False)

        candidate = OpportunityCandidate(
            name=name.strip(),
            source_url=url,
            source_name=source_name.strip(),
            fingerprint=digest,
            payload=payload,
            status=CandidateStatus.PENDING,
            last_seen_at=now,
        )
        self.db.add(candidate)
        self.db.commit()
        self.db.refresh(candidate)
        logger.info("candidat déposé par la veille", extra={"event": "candidate_submitted"})
        return SubmitResult(candidate=candidate, created=True)

    # ------------------------------------------------------------------
    def list_candidates(
        self, status: CandidateStatus | None = None, limit: int = 100
    ) -> list[OpportunityCandidate]:
        statement = (
            select(OpportunityCandidate)
            .order_by(OpportunityCandidate.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(OpportunityCandidate.status == status)
        return list(self.db.scalars(statement))

    def get(self, candidate_id: str) -> OpportunityCandidate:
        candidate = self.db.get(OpportunityCandidate, candidate_id)
        if candidate is None:
            raise NotFoundError("Candidat introuvable.")
        return candidate

    # ------------------------------------------------------------------
    def approve(
        self, candidate: OpportunityCandidate, reviewer: User, overrides: dict[str, Any]
    ) -> FundingOpportunity:
        """Cree le dispositif a partir du candidat, apres relecture humaine.

        Les corrections de la personne l'emportent sur ce qu'a extrait la
        veille : c'est elle qui a lu la source.
        """
        if candidate.status is not CandidateStatus.PENDING:
            raise AppError(
                f"Ce candidat est déjà « {candidate.status} ».",
                code="candidate_already_reviewed",
            )

        raw = {**candidate.payload, **{k: v for k, v in overrides.items() if v is not None}}
        fields = {key: _coerce(key, value) for key, value in raw.items()}
        opportunity = FundingOpportunity(
            name=str(fields.get("name") or candidate.name),
            source_url=candidate.source_url,
            source_name=candidate.source_name,
            source=candidate.source_name,
            # Le dispositif entre ouvert : une personne vient de le verifier.
            status=FundingStatus.OPEN,
            last_verified_at=datetime.now(UTC),
            is_demo=False,
        )
        for field in COPIED_FIELDS:
            value = fields.get(field)
            if value is not None and value != "":
                setattr(opportunity, field, value)

        if not opportunity.organization:
            raise AppError(
                "L'organisme est obligatoire : complétez-le avant de publier.",
                code="candidate_incomplete",
            )

        self.db.add(opportunity)
        self.db.flush()

        candidate.status = CandidateStatus.APPROVED
        candidate.reviewed_by_id = reviewer.id
        candidate.reviewed_at = datetime.now(UTC)
        candidate.opportunity_id = opportunity.id
        self.db.commit()
        self.db.refresh(opportunity)
        logger.info("candidat approuvé", extra={"event": "candidate_approved"})
        return opportunity

    def reject(
        self, candidate: OpportunityCandidate, reviewer: User, note: str | None
    ) -> OpportunityCandidate:
        if candidate.status is not CandidateStatus.PENDING:
            raise AppError(
                f"Ce candidat est déjà « {candidate.status} ».",
                code="candidate_already_reviewed",
            )
        candidate.status = CandidateStatus.REJECTED
        candidate.reviewed_by_id = reviewer.id
        candidate.reviewed_at = datetime.now(UTC)
        candidate.review_note = note
        self.db.commit()
        self.db.refresh(candidate)
        logger.info("candidat rejeté", extra={"event": "candidate_rejected"})
        return candidate

    def pending_count(self) -> int:
        return len(self.list_candidates(CandidateStatus.PENDING, limit=1000))
