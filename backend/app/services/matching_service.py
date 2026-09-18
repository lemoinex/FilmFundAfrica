"""Matching projet / financement — calcul déterministe.

Principes tenus ici :

1. **Le score est calculé par des règles, pas par l'IA.** Il est donc
   reproductible, explicable ligne à ligne, gratuit et instantané. L'IA
   n'intervient que pour rédiger l'explication, à la demande de l'utilisateur.
2. **Une information absente n'est jamais interprétée.** Un critère que les
   données du projet ne permettent pas d'évaluer est marqué `unknown`, retiré
   du dénominateur, et listé comme « à vérifier ». Le projet n'est ni
   récompensé ni puni pour une donnée qu'il n'a pas fournie ; en contrepartie,
   `assessed_ratio` dit quelle part de la grille a réellement pu être évaluée.
3. **Un critère bloquant non rempli rend la candidature inéligible.** Le
   dispositif reste affiché, avec la raison, plutôt que d'être masqué
   silencieusement.
4. **Le score n'est jamais présenté comme une garantie de financement.**
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.i18n import Locale, translate
from app.models.document import Document
from app.models.enums import DocumentType, FundingStatus
from app.models.funding import FundingOpportunity
from app.models.project import Project
from app.repositories.document import DocumentRepository
from app.schemas.funding import (
    MatchCriterion,
    MatchResult,
    OpportunitySummary,
    format_amount,
)

#: Nombre de mots en deçà duquel un document est considéré comme non abouti.
MIN_WORDS_FOR_REQUIRED_DOCUMENT = 120

#: Une échéance à moins de ce nombre de jours laisse peu de temps pour candidater.
TIGHT_DEADLINE_DAYS = 14


def normalise(value: str | None) -> str:
    """Compare sans tenir compte de la casse, des accents ni des espaces."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def csv_values(raw: str | None) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def contains(haystack: list[str], needle: str | None) -> bool:
    if not needle:
        return False
    target = normalise(needle)
    return any(normalise(item) == target for item in haystack)


@dataclass(slots=True)
class _Outcome:
    """Verdict d'un critere : un etat, et la cle du message qui l'explique.

    La phrase n'est choisie qu'au rendu : un critere est evalue une fois, et
    peut etre relu dans deux langues.
    """

    state: str  # met | unmet | unknown
    key: str
    params: dict = field(default_factory=dict)
    blocking: bool = False
    #: Part du poids obtenue quand le critere est partiellement rempli.
    #: None = tout ou rien (1.0 si `met`, 0 sinon).
    ratio: float | None = None

    def points(self, weight: int) -> int:
        if self.state == "met":
            return weight
        if self.state == "unmet" and self.ratio:
            return round(weight * max(0.0, min(self.ratio, 1.0)))
        return 0


class MatchingService:
    """Calcule la compatibilité d'un projet avec un dispositif de financement."""

    def __init__(self, db: Session, locale: Locale = "fr") -> None:
        self.db = db
        self.locale = locale
        self.documents = DocumentRepository(db)

    # ------------------------------------------------------------------
    def score_project(
        self, project: Project, opportunities: list[FundingOpportunity]
    ) -> list[MatchResult]:
        """Évalue un projet contre une liste de dispositifs, du plus au moins compatible."""
        documents = {
            document.document_type: document
            for document in self.documents.list_for_project(project.id)
        }
        results = [
            self.score_one(project, opportunity, documents) for opportunity in opportunities
        ]
        # Les dispositifs inéligibles restent visibles, mais après les autres.
        results.sort(key=lambda item: (item.eligible, item.compatibility), reverse=True)
        return results

    # ------------------------------------------------------------------
    def score_one(
        self,
        project: Project,
        opportunity: FundingOpportunity,
        documents: dict[DocumentType, Document] | None = None,
    ) -> MatchResult:
        if documents is None:
            documents = {
                document.document_type: document
                for document in self.documents.list_for_project(project.id)
            }

        required_documents, missing_documents = self._document_gap(opportunity, documents)

        definitions: list[tuple[str, str, int, _Outcome]] = [
            ("country", "criterion.country", 25, self._check_country(project, opportunity)),
            (
                "project_type",
                "criterion.projectType",
                20,
                self._check_project_type(project, opportunity),
            ),
            ("genre", "criterion.genre", 12, self._check_genre(project, opportunity)),
            ("language", "criterion.language", 8, self._check_language(project, opportunity)),
            ("duration", "criterion.duration", 10, self._check_duration(project, opportunity)),
            ("deadline", "criterion.deadline", 10, self._check_deadline(opportunity)),
            (
                "documents",
                "criterion.documents",
                15,
                self._check_documents(required_documents, missing_documents),
            ),
        ]

        criteria: list[MatchCriterion] = []
        earned = 0
        assessable = 0
        total_weight = 0
        eligible = True

        for key, label_key, weight, outcome in definitions:
            total_weight += weight
            points = outcome.points(weight)
            if outcome.state != "unknown":
                assessable += weight
                earned += points
            if outcome.state == "unmet" and outcome.blocking:
                eligible = False

            criteria.append(
                MatchCriterion(
                    key=key,
                    label=translate(self.locale, label_key),
                    weight=weight,
                    earned=points,
                    state=outcome.state,
                    detail=translate(self.locale, outcome.key, **outcome.params),
                    blocking=outcome.blocking,
                )
            )

        compatibility = round(earned / assessable * 100) if assessable else 0

        return MatchResult(
            opportunity=self.to_summary(opportunity),
            compatibility=compatibility,
            eligible=eligible,
            assessed_ratio=round(assessable / total_weight * 100) if total_weight else 0,
            criteria=criteria,
            met_conditions=[c.detail for c in criteria if c.state == "met"],
            missing_conditions=[c.detail for c in criteria if c.state == "unmet"],
            unknown_conditions=[c.detail for c in criteria if c.state == "unknown"],
            required_documents=required_documents,
            missing_documents=missing_documents,
            computed_at=datetime.now(UTC),
        )

    # ------------------------------------------------------------------
    # Critères
    # ------------------------------------------------------------------
    @staticmethod
    def _check_country(project: Project, opportunity: FundingOpportunity) -> _Outcome:
        eligible = csv_values(opportunity.eligible_countries)
        if not eligible:
            return _Outcome("met", "match.country.allOpen")
        if not project.country:
            return _Outcome("unknown", "match.country.unknown")
        if contains(eligible, project.country):
            return _Outcome("met", "match.country.met", {"country": project.country})
        return _Outcome(
            "unmet",
            "match.country.unmet",
            {
                "country": project.country,
                "list": ", ".join(eligible[:6]) + ("…" if len(eligible) > 6 else ""),
            },
            blocking=True,
        )

    @staticmethod
    def _check_project_type(project: Project, opportunity: FundingOpportunity) -> _Outcome:
        accepted = csv_values(opportunity.project_types)
        if not accepted:
            return _Outcome("met", "match.type.allOpen")
        if contains(accepted, str(project.project_type)):
            return _Outcome("met", "match.type.met")
        return _Outcome("unmet", "match.type.unmet", blocking=True)

    @staticmethod
    def _check_genre(project: Project, opportunity: FundingOpportunity) -> _Outcome:
        accepted = csv_values(opportunity.genres)
        if not accepted:
            return _Outcome("met", "match.genre.noRestriction")
        if not project.genre:
            return _Outcome("unknown", "match.genre.unknown")
        if contains(accepted, project.genre):
            return _Outcome("met", "match.genre.met", {"genre": project.genre})
        # Correspondance partielle : « drame social » face à « drame ».
        needle = normalise(project.genre)
        if any(normalise(item) in needle or needle in normalise(item) for item in accepted):
            return _Outcome("met", "match.genre.close", {"genre": project.genre})
        return _Outcome(
            "unmet",
            "match.genre.unmet",
            {"genre": project.genre, "list": ", ".join(accepted[:5])},
        )

    @staticmethod
    def _check_language(project: Project, opportunity: FundingOpportunity) -> _Outcome:
        accepted = csv_values(opportunity.languages)
        if not accepted:
            return _Outcome("met", "match.language.noRestriction")
        if contains(accepted, project.language):
            return _Outcome("met", "match.language.met", {"language": project.language})
        return _Outcome(
            "unmet",
            "match.language.unmet",
            {"list": ", ".join(accepted), "language": project.language},
        )

    @staticmethod
    def _check_duration(project: Project, opportunity: FundingOpportunity) -> _Outcome:
        """Cohérence entre la durée du projet et le format visé par le dispositif.

        On n'utilise pas les montants : un budget de projet n'existe pas encore
        en base (module Phase 4), et l'inventer contredirait la règle produit.
        """
        if project.duration is None:
            return _Outcome("unknown", "match.duration.unknown")

        accepted = csv_values(opportunity.project_types)
        short_formats = {"SHORT_FILM", "WEB_SERIES"}
        long_formats = {"FEATURE_FILM", "DOCUMENTARY"}

        if accepted and set(accepted).issubset(short_formats) and project.duration > 40:
            return _Outcome(
                "unmet", "match.duration.tooLong", {"minutes": project.duration}
            )
        if accepted and set(accepted).issubset(long_formats) and project.duration < 50:
            return _Outcome(
                "unmet", "match.duration.tooShort", {"minutes": project.duration}
            )
        return _Outcome("met", "match.duration.met", {"minutes": project.duration})

    @staticmethod
    def _check_deadline(opportunity: FundingOpportunity) -> _Outcome:
        if opportunity.status == FundingStatus.CLOSED:
            return _Outcome("unmet", "match.deadline.closed", blocking=True)
        if opportunity.deadline is None:
            return _Outcome("unknown", "match.deadline.unknown")

        days_left = (opportunity.deadline - date.today()).days
        if days_left < 0:
            return _Outcome(
                "unmet",
                "match.deadline.passed",
                {"date": f"{opportunity.deadline:%d/%m/%Y}"},
                blocking=True,
            )
        if days_left <= TIGHT_DEADLINE_DAYS:
            return _Outcome("met", "match.deadline.tight", {"days": days_left})
        return _Outcome(
            "met",
            "match.deadline.met",
            {"date": f"{opportunity.deadline:%d/%m/%Y}", "days": days_left},
        )

    @staticmethod
    def _check_documents(required: list[str], missing: list[str]) -> _Outcome:
        """Critère à crédit partiel.

        Un dossier auquel il manque un document sur trois n'est pas dans la
        même situation qu'un dossier vide : le score doit bouger à mesure que
        l'auteur avance, sinon il ne lui donne aucun signal de progression.
        """
        if not required:
            return _Outcome("unknown", "match.documents.unknown")
        if not missing:
            return _Outcome("met", "match.documents.met")

        written = len(required) - len(missing)
        return _Outcome(
            "unmet",
            "match.documents.unmet",
            {
                "written": written,
                "required": len(required),
                "missing": ", ".join(missing),
            },
            ratio=written / len(required),
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _document_gap(
        opportunity: FundingOpportunity, documents: dict[DocumentType, Document]
    ) -> tuple[list[str], list[str]]:
        """Documents exigés par le dispositif, et ceux qui manquent au dossier."""
        from app.prompts import get_prompt

        required: list[str] = []
        missing: list[str] = []

        for requirement in opportunity.requirement_items:
            if not requirement.required_document_type:
                continue
            try:
                document_type = DocumentType(requirement.required_document_type)
            except ValueError:
                continue

            label = get_prompt(document_type).document_label
            required.append(label)

            document = documents.get(document_type)
            if (
                document is None
                or document.word_count < MIN_WORDS_FOR_REQUIRED_DOCUMENT
            ) and requirement.is_mandatory:
                missing.append(label)

        return required, missing

    # ------------------------------------------------------------------
    @staticmethod
    def to_summary(opportunity: FundingOpportunity) -> OpportunitySummary:
        days_left = (
            (opportunity.deadline - date.today()).days if opportunity.deadline else None
        )
        return OpportunitySummary(
            id=opportunity.id,
            name=opportunity.name,
            organization=opportunity.organization,
            category=opportunity.category,
            country=opportunity.country,
            amount_label=format_amount(
                opportunity.minimum_budget, opportunity.maximum_budget, opportunity.currency
            ),
            deadline=opportunity.deadline,
            days_left=days_left,
            status=opportunity.status,
            is_demo=opportunity.is_demo,
            source_name=opportunity.source_name,
            source_url=opportunity.source_url,
            last_verified_at=opportunity.last_verified_at,
        )
