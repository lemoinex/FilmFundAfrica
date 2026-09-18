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
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

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
    state: str  # met | unmet | unknown
    detail: str
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

    def __init__(self, db: Session) -> None:
        self.db = db
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
            ("country", "Pays éligible", 25, self._check_country(project, opportunity)),
            ("project_type", "Type de projet", 20, self._check_project_type(project, opportunity)),
            ("genre", "Genre", 12, self._check_genre(project, opportunity)),
            ("language", "Langue", 8, self._check_language(project, opportunity)),
            ("duration", "Format et durée", 10, self._check_duration(project, opportunity)),
            ("deadline", "Échéance", 10, self._check_deadline(opportunity)),
            (
                "documents",
                "Documents exigés",
                15,
                self._check_documents(required_documents, missing_documents),
            ),
        ]

        criteria: list[MatchCriterion] = []
        earned = 0
        assessable = 0
        total_weight = 0
        eligible = True

        for key, label, weight, outcome in definitions:
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
                    label=label,
                    weight=weight,
                    earned=points,
                    state=outcome.state,
                    detail=outcome.detail,
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
            return _Outcome("met", "Dispositif ouvert à tous les pays.")
        if not project.country:
            return _Outcome(
                "unknown",
                "Pays du projet non renseigné : l'éligibilité géographique n'a pas pu être "
                "vérifiée.",
            )
        if contains(eligible, project.country):
            return _Outcome("met", f"{project.country} figure parmi les pays éligibles.")
        return _Outcome(
            "unmet",
            f"{project.country} ne figure pas parmi les pays éligibles "
            f"({', '.join(eligible[:6])}{'…' if len(eligible) > 6 else ''}).",
            blocking=True,
        )

    @staticmethod
    def _check_project_type(project: Project, opportunity: FundingOpportunity) -> _Outcome:
        accepted = csv_values(opportunity.project_types)
        if not accepted:
            return _Outcome("met", "Dispositif ouvert à tous les types de projet.")
        if contains(accepted, str(project.project_type)):
            return _Outcome("met", "Le type de projet correspond au dispositif.")
        return _Outcome(
            "unmet",
            "Le type de projet ne fait pas partie de ceux acceptés par ce dispositif.",
            blocking=True,
        )

    @staticmethod
    def _check_genre(project: Project, opportunity: FundingOpportunity) -> _Outcome:
        accepted = csv_values(opportunity.genres)
        if not accepted:
            return _Outcome("met", "Aucune restriction de genre.")
        if not project.genre:
            return _Outcome("unknown", "Genre du projet non renseigné.")
        if contains(accepted, project.genre):
            return _Outcome("met", f"Le genre « {project.genre} » est recherché.")
        # Correspondance partielle : « drame social » face à « drame ».
        needle = normalise(project.genre)
        if any(normalise(item) in needle or needle in normalise(item) for item in accepted):
            return _Outcome("met", f"Le genre « {project.genre} » est proche de la ligne éditoriale.")
        return _Outcome(
            "unmet",
            f"Le genre « {project.genre} » ne correspond pas à la ligne éditoriale "
            f"({', '.join(accepted[:5])}).",
        )

    @staticmethod
    def _check_language(project: Project, opportunity: FundingOpportunity) -> _Outcome:
        accepted = csv_values(opportunity.languages)
        if not accepted:
            return _Outcome("met", "Aucune restriction de langue.")
        if contains(accepted, project.language):
            return _Outcome("met", f"Le projet est en {project.language}.")
        return _Outcome(
            "unmet",
            f"Le dispositif attend un projet en {', '.join(accepted)} ; "
            f"le vôtre est en {project.language}.",
        )

    @staticmethod
    def _check_duration(project: Project, opportunity: FundingOpportunity) -> _Outcome:
        """Cohérence entre la durée du projet et le format visé par le dispositif.

        On n'utilise pas les montants : un budget de projet n'existe pas encore
        en base (module Phase 4), et l'inventer contredirait la règle produit.
        """
        if project.duration is None:
            return _Outcome("unknown", "Durée du projet non renseignée.")

        accepted = csv_values(opportunity.project_types)
        short_formats = {"SHORT_FILM", "WEB_SERIES"}
        long_formats = {"FEATURE_FILM", "DOCUMENTARY"}

        if accepted and set(accepted).issubset(short_formats) and project.duration > 40:
            return _Outcome(
                "unmet",
                f"Le dispositif cible les formats courts ; le projet fait {project.duration} min.",
            )
        if accepted and set(accepted).issubset(long_formats) and project.duration < 50:
            return _Outcome(
                "unmet",
                f"Le dispositif cible les formats longs ; le projet fait {project.duration} min.",
            )
        return _Outcome("met", f"La durée visée ({project.duration} min) est cohérente.")

    @staticmethod
    def _check_deadline(opportunity: FundingOpportunity) -> _Outcome:
        if opportunity.status == FundingStatus.CLOSED:
            return _Outcome("unmet", "Ce dispositif est clos.", blocking=True)
        if opportunity.deadline is None:
            return _Outcome(
                "unknown",
                "Aucune date limite renseignée : vérifiez le calendrier sur le site de "
                "l'organisme.",
            )

        days_left = (opportunity.deadline - date.today()).days
        if days_left < 0:
            return _Outcome(
                "unmet",
                f"La date limite est dépassée depuis le {opportunity.deadline:%d/%m/%Y}.",
                blocking=True,
            )
        if days_left <= TIGHT_DEADLINE_DAYS:
            return _Outcome(
                "met",
                f"Échéance dans {days_left} jour(s) : le délai est court pour finaliser "
                "un dossier.",
            )
        return _Outcome("met", f"Échéance le {opportunity.deadline:%d/%m/%Y}, soit {days_left} jours.")

    @staticmethod
    def _check_documents(required: list[str], missing: list[str]) -> _Outcome:
        """Critère à crédit partiel.

        Un dossier auquel il manque un document sur trois n'est pas dans la
        même situation qu'un dossier vide : le score doit bouger à mesure que
        l'auteur avance, sinon il ne lui donne aucun signal de progression.
        """
        if not required:
            return _Outcome(
                "unknown",
                "Pièces à fournir non détaillées : consultez le règlement du dispositif.",
            )
        if not missing:
            return _Outcome("met", "Tous les documents exigés sont rédigés dans votre dossier.")

        written = len(required) - len(missing)
        return _Outcome(
            "unmet",
            f"{written}/{len(required)} document(s) exigé(s) rédigé(s) — manquant(s) : "
            f"{', '.join(missing)}.",
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
