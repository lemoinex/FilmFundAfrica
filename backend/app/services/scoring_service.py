"""Project Readiness Score : calcul deterministe de la maturite d'un dossier.

Le score est un indicateur interne d'avancement du dossier. Il ne prejuge
d'aucune decision de financement et n'est jamais presente comme tel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.enums import DocumentType
from app.models.project import Project
from app.repositories.document import DocumentRepository
from app.schemas.project import ReadinessScore, ScoreCriterion

MIN_WORDS_SUBSTANTIAL = 120


@dataclass(slots=True)
class _Evaluation:
    earned: int
    detail: str
    improvement: str | None = None


class ScoringService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)

    # ------------------------------------------------------------------
    def compute(self, project: Project, *, persist: bool = True) -> ReadinessScore:
        documents = {doc.document_type: doc for doc in self.documents.list_for_project(project.id)}

        criteria_definitions = [
            ("concept", "Concept", 20, self._score_concept(project)),
            ("narration", "Narration", 15, self._score_narration(project, documents)),
            ("characters", "Personnages", 15, self._score_characters(project, documents)),
            ("vision", "Vision artistique", 15, self._score_vision(project, documents)),
            ("feasibility", "Faisabilité", 10, self._score_feasibility(project)),
            ("budget", "Budget", 10, self._score_budget(project)),
            ("funding_plan", "Plan de financement", 5, self._score_funding_plan(project)),
            ("market", "Potentiel marché", 5, self._score_market(project)),
            ("dossier", "Dossier", 5, self._score_dossier(documents)),
        ]

        criteria: list[ScoreCriterion] = []
        improvements: list[str] = []
        total = 0

        for key, label, weight, evaluation in criteria_definitions:
            earned = max(0, min(evaluation.earned, weight))
            total += earned
            criteria.append(
                ScoreCriterion(
                    key=key,
                    label=label,
                    weight=weight,
                    earned=earned,
                    detail=evaluation.detail,
                )
            )
            if evaluation.improvement and earned < weight:
                improvements.append(evaluation.improvement)

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
            (project.logline, 6, "la logline"),
            (project.concept, 6, "le concept"),
            (project.theme, 4, "le thème"),
            (project.genre, 2, "le genre"),
            (project.country, 2, "le pays"),
        ):
            if self._filled(value, 10 if points > 3 else 2):
                earned += points
            else:
                missing.append(label)
        detail = "Concept complet." if not missing else "À renseigner : " + ", ".join(missing)
        return _Evaluation(
            earned,
            detail,
            f"Renseignez {', '.join(missing)}." if missing else None,
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
            missing.append("un synopsis court développé")
        if self._filled(project.long_synopsis, 600) or self._substantial(
            documents.get(DocumentType.LONG_SYNOPSIS)
        ):
            earned += 5
        else:
            missing.append("un synopsis long")
        if self._substantial(documents.get(DocumentType.TREATMENT)) or self._substantial(
            documents.get(DocumentType.SCREENPLAY)
        ):
            earned += 3
        else:
            missing.append("un traitement ou un scénario")
        detail = "Narration solide." if not missing else "Manquant : " + ", ".join(missing)
        return _Evaluation(
            earned, detail, f"Ajoutez {', '.join(missing)}." if missing else None
        )

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
            detail = "Aucun personnage saisi."
            improvement = "Saisissez au moins le protagoniste et la force antagoniste."
        elif described < count:
            detail = f"{described}/{count} personnage(s) décrit(s)."
            improvement = "Complétez la description et l'arc de chaque personnage."
        else:
            detail = f"{count} personnage(s) documenté(s)."
            improvement = "Générez la présentation des personnages."
        return _Evaluation(earned, detail, improvement)

    def _score_vision(
        self, project: Project, documents: dict[DocumentType, Document]
    ) -> _Evaluation:
        earned = 0
        missing: list[str] = []
        if self._filled(project.director_vision, 100):
            earned += 4
        else:
            missing.append("la vision du réalisateur")
        if self._substantial(documents.get(DocumentType.INTENT_NOTE)):
            earned += 6
        else:
            missing.append("la note d'intention")
        if self._substantial(documents.get(DocumentType.DIRECTING_NOTE)):
            earned += 5
        else:
            missing.append("la note de réalisation")
        detail = (
            "Vision artistique documentée." if not missing else "Manquant : " + ", ".join(missing)
        )
        return _Evaluation(
            earned, detail, f"Complétez {', '.join(missing)}." if missing else None
        )

    def _score_feasibility(self, project: Project) -> _Evaluation:
        earned = 0
        missing: list[str] = []
        if project.duration:
            earned += 4
        else:
            missing.append("la durée cible")
        if self._filled(project.country, 2):
            earned += 3
        else:
            missing.append("le pays de production")
        if self._filled(project.objectives, 40):
            earned += 3
        else:
            missing.append("les objectifs du projet")
        detail = "Cadre de production défini." if not missing else "Manquant : " + ", ".join(missing)
        return _Evaluation(
            earned, detail, f"Précisez {', '.join(missing)}." if missing else None
        )

    def _score_budget(self, project: Project) -> _Evaluation:
        budget = project.budget
        if budget is None or budget.total_amount <= 0:
            return _Evaluation(
                0,
                "Budget non renseigné.",
                "Budget non renseigné : construisez le budget prévisionnel.",
            )
        item_count = len(budget.items)
        earned = 5 + min(5, item_count)
        return _Evaluation(
            earned,
            f"Budget de {budget.total_amount:,.0f} {budget.currency} sur {item_count} poste(s).",
            "Détaillez davantage les postes budgétaires." if item_count < 5 else None,
        )

    def _score_funding_plan(self, project: Project) -> _Evaluation:
        plan = project.funding_plan
        if plan is None or not plan.lines:
            return _Evaluation(
                0,
                "Plan de financement absent.",
                "Plan de financement absent : listez les sources envisagées.",
            )
        earned = 3 if plan.total_budget > 0 else 1
        if plan.funded_percentage > 0:
            earned += 2
        return _Evaluation(
            earned,
            f"{plan.funded_percentage:.0f} % du budget couvert par des financements identifiés.",
            "Identifiez d'autres sources pour couvrir le financement recherché.",
        )

    def _score_market(self, project: Project) -> _Evaluation:
        earned = 0
        missing: list[str] = []
        if self._filled(project.target_audience, 40):
            earned += 3
        else:
            missing.append("le public cible")
        if self._filled(project.stakes, 40):
            earned += 2
        else:
            missing.append("les enjeux")
        detail = "Positionnement défini." if not missing else "Manquant : " + ", ".join(missing)
        return _Evaluation(
            earned, detail, f"Décrivez {', '.join(missing)}." if missing else None
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
            f"{len(present)}/{len(core)} documents clés rédigés.",
            f"Il manque {missing_count} document(s) clé(s) au dossier."
            if missing_count
            else None,
        )
