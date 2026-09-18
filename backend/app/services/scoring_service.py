"""Project Readiness Score : calcul deterministe de la maturite d'un dossier.

Le score est un indicateur interne d'avancement du dossier. Il ne prejuge
d'aucune decision de financement et n'est jamais presente comme tel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.i18n import Locale, translate
from app.models.document import Document
from app.models.enums import DocumentType
from app.models.project import Project
from app.repositories.document import DocumentRepository
from app.schemas.project import ReadinessScore, ScoreCriterion

MIN_WORDS_SUBSTANTIAL = 120


@dataclass(slots=True)
class _Evaluation:
    """Note d'un critere, et les cles des phrases qui l'expliquent.

    Comme pour la compatibilite : le critere est evalue une fois, la phrase
    n'est choisie qu'au rendu.
    """

    earned: int
    detail_key: str
    detail_params: dict = field(default_factory=dict)
    improvement_key: str | None = None
    improvement_params: dict = field(default_factory=dict)


class ScoringService:
    def __init__(self, db: Session, locale: Locale = "fr") -> None:
        self.db = db
        self.locale = locale
        self.documents = DocumentRepository(db)

    def _t(self, key: str, **params: object) -> str:
        return translate(self.locale, key, **params)

    def _list(self, keys: list[str]) -> str:
        """Enumere des libelles de champs, chacun traduit."""
        return ", ".join(self._t(key) for key in keys)

    # ------------------------------------------------------------------
    def compute(self, project: Project, *, persist: bool = True) -> ReadinessScore:
        documents = {doc.document_type: doc for doc in self.documents.list_for_project(project.id)}

        criteria_definitions = [
            ("concept", "score.concept", 20, self._score_concept(project)),
            ("narration", "score.narration", 15, self._score_narration(project, documents)),
            ("characters", "score.characters", 15, self._score_characters(project, documents)),
            ("vision", "score.vision", 15, self._score_vision(project, documents)),
            ("feasibility", "score.feasibility", 10, self._score_feasibility(project)),
            ("budget", "score.budget", 10, self._score_budget(project)),
            ("funding_plan", "score.fundingPlan", 5, self._score_funding_plan(project)),
            ("market", "score.market", 5, self._score_market(project)),
            ("dossier", "score.dossier", 5, self._score_dossier(documents)),
        ]

        criteria: list[ScoreCriterion] = []
        improvements: list[str] = []
        total = 0

        for key, label_key, weight, evaluation in criteria_definitions:
            earned = max(0, min(evaluation.earned, weight))
            total += earned
            criteria.append(
                ScoreCriterion(
                    key=key,
                    label=self._t(label_key),
                    weight=weight,
                    earned=earned,
                    detail=self._t(evaluation.detail_key, **evaluation.detail_params),
                )
            )
            if evaluation.improvement_key and earned < weight:
                improvements.append(
                    self._t(evaluation.improvement_key, **evaluation.improvement_params)
                )

        total = max(0, min(total, 100))
        if persist:
            project.readiness_score = total
            self.db.commit()

        return ReadinessScore(
            total=total,
            criteria=criteria,
            improvements=improvements,
            computed_at=datetime.now(UTC),
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _filled(value: str | None, minimum: int = 1) -> bool:
        return bool(value and len(value.strip()) >= minimum)

    @staticmethod
    def _substantial(document: Document | None) -> bool:
        return bool(document and document.word_count >= MIN_WORDS_SUBSTANTIAL)

    # ------------------------------------------------------------------
    def _score_concept(self, project: Project) -> _Evaluation:
        earned = 0
        missing: list[str] = []
        for value, points, label in (
            (project.logline, 6, "score.field.logline"),
            (project.concept, 6, "score.field.concept"),
            (project.theme, 4, "score.field.theme"),
            (project.genre, 2, "score.field.genre"),
            (project.country, 2, "score.field.country"),
        ):
            if self._filled(value, 10 if points > 3 else 2):
                earned += points
            else:
                missing.append(label)
        if not missing:
            return _Evaluation(earned, "score.concept.complete")
        listed = self._list(missing)
        return _Evaluation(
            earned,
            "score.toFill",
            {"list": listed},
            "score.fillThem",
            {"list": listed},
        )

    def _score_narration(
        self, project: Project, documents: dict[DocumentType, Document]
    ) -> _Evaluation:
        earned = 0
        missing: list[str] = []
        if self._filled(project.short_synopsis, 200) or self._substantial(
            documents.get(DocumentType.SHORT_SYNOPSIS)
        ):
            earned += 7
        else:
            missing.append("score.field.shortSynopsis")
        if self._filled(project.long_synopsis, 600) or self._substantial(
            documents.get(DocumentType.LONG_SYNOPSIS)
        ):
            earned += 5
        else:
            missing.append("score.field.longSynopsis")
        if self._substantial(documents.get(DocumentType.TREATMENT)) or self._substantial(
            documents.get(DocumentType.SCREENPLAY)
        ):
            earned += 3
        else:
            missing.append("score.field.treatment")
        if not missing:
            return _Evaluation(earned, "score.narration.solid")
        listed = self._list(missing)
        return _Evaluation(earned, "score.missing", {"list": listed}, "score.addThem", {"list": listed})

    def _score_characters(
        self, project: Project, documents: dict[DocumentType, Document]
    ) -> _Evaluation:
        count = len(project.characters)
        described = sum(1 for c in project.characters if self._filled(c.description, 40))
        with_arc = sum(1 for c in project.characters if self._filled(c.arc, 30))

        earned = 0
        if count >= 1:
            earned += 4
        if count >= 3:
            earned += 2
        if described >= max(1, count // 2):
            earned += 4
        if with_arc >= 1:
            earned += 2
        if self._substantial(documents.get(DocumentType.CHARACTER_SHEET)):
            earned += 3

        if count == 0:
            return _Evaluation(
                earned, "score.characters.none", {}, "score.characters.noneImprovement"
            )
        if described < count:
            return _Evaluation(
                earned,
                "score.characters.partial",
                {"described": described, "count": count},
                "score.characters.partialImprovement",
            )
        return _Evaluation(
            earned,
            "score.characters.documented",
            {"count": count},
            "score.characters.documentedImprovement",
        )

    def _score_vision(
        self, project: Project, documents: dict[DocumentType, Document]
    ) -> _Evaluation:
        earned = 0
        missing: list[str] = []
        if self._filled(project.director_vision, 100):
            earned += 4
        else:
            missing.append("score.field.directorVision")
        if self._substantial(documents.get(DocumentType.INTENT_NOTE)):
            earned += 6
        else:
            missing.append("score.field.intentNote")
        if self._substantial(documents.get(DocumentType.DIRECTING_NOTE)):
            earned += 5
        else:
            missing.append("score.field.directingNote")
        if not missing:
            return _Evaluation(earned, "score.vision.documented")
        listed = self._list(missing)
        return _Evaluation(
            earned, "score.missing", {"list": listed}, "score.completeThem", {"list": listed}
        )

    def _score_feasibility(self, project: Project) -> _Evaluation:
        earned = 0
        missing: list[str] = []
        if project.duration:
            earned += 4
        else:
            missing.append("score.field.duration")
        if self._filled(project.country, 2):
            earned += 3
        else:
            missing.append("score.field.productionCountry")
        if self._filled(project.objectives, 40):
            earned += 3
        else:
            missing.append("score.field.objectives")
        if not missing:
            return _Evaluation(earned, "score.feasibility.defined")
        listed = self._list(missing)
        return _Evaluation(
            earned, "score.missing", {"list": listed}, "score.specifyThem", {"list": listed}
        )

    def _score_budget(self, project: Project) -> _Evaluation:
        budget = project.budget
        if budget is None or budget.total_amount <= 0:
            return _Evaluation(
                0, "score.budget.missing", {}, "score.budget.missingImprovement"
            )
        item_count = len(budget.items)
        earned = 5 + min(5, item_count)
        return _Evaluation(
            earned,
            "score.budget.detail",
            {
                "amount": f"{budget.total_amount:,.0f}",
                "currency": budget.currency,
                "items": item_count,
            },
            "score.budget.detailImprovement" if item_count < 5 else None,
        )

    def _score_funding_plan(self, project: Project) -> _Evaluation:
        plan = project.funding_plan
        if plan is None or not plan.lines:
            return _Evaluation(
                0, "score.fundingPlan.missing", {}, "score.fundingPlan.missingImprovement"
            )
        earned = 3 if plan.total_budget > 0 else 1
        if plan.funded_percentage > 0:
            earned += 2
        return _Evaluation(
            earned,
            "score.fundingPlan.detail",
            {"percentage": f"{plan.funded_percentage:.0f}"},
            "score.fundingPlan.detailImprovement",
        )

    def _score_market(self, project: Project) -> _Evaluation:
        earned = 0
        missing: list[str] = []
        if self._filled(project.target_audience, 40):
            earned += 3
        else:
            missing.append("score.field.audience")
        if self._filled(project.stakes, 40):
            earned += 2
        else:
            missing.append("score.field.stakes")
        if not missing:
            return _Evaluation(earned, "score.market.defined")
        listed = self._list(missing)
        return _Evaluation(
            earned, "score.missing", {"list": listed}, "score.describeThem", {"list": listed}
        )

    def _score_dossier(self, documents: dict[DocumentType, Document]) -> _Evaluation:
        core = [
            DocumentType.SHORT_SYNOPSIS,
            DocumentType.INTENT_NOTE,
            DocumentType.DIRECTING_NOTE,
            DocumentType.CHARACTER_SHEET,
            DocumentType.WRITTEN_PITCH,
        ]
        present = [doc_type for doc_type in core if self._substantial(documents.get(doc_type))]
        earned = min(5, len(present))
        missing_count = len(core) - len(present)
        return _Evaluation(
            earned,
            "score.dossier.detail",
            {"present": len(present), "total": len(core)},
            "score.dossier.improvement" if missing_count else None,
            {"count": missing_count},
        )
