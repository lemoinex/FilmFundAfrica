"""Contrats echanges entre agents.

Un agent ne rend pas du texte libre : il rend une structure que l'orchestrateur
peut lire, comparer et router. C'est ce qui separe une chaine d'agents d'une
succession de generateurs.

Quatre garanties sont portees ici, et aucune n'est decorative :

* **Non-destruction** (`ChangeSet`) — un agent qui reecrit le travail d'un autre
  doit dire ce qu'il a garde, change, retire et ajoute, et pourquoi. Sans cela,
  une chaine de huit agents perd en route ce que l'auteur avait valide.
* **Protocole de decision** (`DecisionRecord`) — une modification sans
  observation ni risque identifie est une preference, pas une decision.
* **Tracabilite** (`ModificationTrace`) — qui, quand, quoi, pourquoi, avec quel
  impact. C'est ce qui permet de revenir en arriere sans deviner.
* **Incertitude** (`TrackedFact`) — aucune information n'est nue. Une hypothese
  reste une hypothese jusqu'a verification, y compris quand elle arrangerait le
  dossier.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import AgentRole, ConfidenceStatus, Severity, ValidationVerdict


class TrackedFact(BaseModel):
    """Une information et ce qu'on sait de sa provenance.

    Le statut n'est pas un commentaire : `assert_usable_for_funding()` s'en sert
    pour refuser qu'une hypothese serve de critere d'eligibilite.
    """

    value: str
    status: ConfidenceStatus = ConfidenceStatus.UNKNOWN
    source: str | None = None
    #: Renseigne des que le statut passe a `VERIFIED`.
    verified_at: datetime | None = None

    def is_usable_for_funding(self) -> bool:
        """Une information non etablie n'engage pas un dossier de financement."""
        return self.status in (ConfidenceStatus.VERIFIED, ConfidenceStatus.PROVIDED_BY_USER)


class ChangeSet(BaseModel):
    """Ce qu'un agent a fait du travail recu.

    Les quatre listes sont volontairement distinctes : « modifie » et
    « supprime puis ajoute » ne racontent pas la meme histoire a la relecture.
    """

    preserved: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    added: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)

    def is_destructive(self) -> bool:
        return bool(self.removed)

    def touches_anything(self) -> bool:
        return bool(self.preserved or self.modified or self.removed or self.added)


class DecisionRecord(BaseModel):
    """Une decision d'agent, du constat a la validation.

    OBSERVATION -> ANALYSIS -> RISK -> DECISION -> MODIFICATION -> VALIDATION.
    """

    observation: str
    analysis: str
    risk: str
    decision: str
    modification: str
    validation: str


class ModificationTrace(BaseModel):
    """Journal d'une modification : de quoi reconstituer l'histoire du dossier."""

    agent: AgentRole
    element: str
    previous_value: str | None
    new_value: str | None
    reason: str
    impact: str
    validation_status: ValidationVerdict | None = None
    version: int = 1
    recorded_at: datetime | None = None


class Finding(BaseModel):
    """Un constat de validateur, rattache a l'agent qui peut le corriger.

    `owner` est ce qui rend la boucle de correction possible : sans lui,
    l'orchestrateur saurait qu'un probleme existe sans savoir a qui le rendre.
    """

    severity: Severity
    element: str
    description: str
    owner: AgentRole | None = None
    suggested_correction: str | None = None

    def is_blocking(self) -> bool:
        return self.severity is Severity.CRITICAL


class ProjectState(BaseModel):
    """Etat partage du projet, enrichi a chaque etape.

    Chaque agent le recoit entier et en rend une version augmentee : c'est la
    memoire de la chaine. Les champs restent libres (`dict`) parce que le
    contenu d'un traitement ou d'un plan de financement n'a pas la meme forme
    d'un projet a l'autre ; ce qui est contraint, c'est la tracabilite autour.
    """

    project_id: str
    project_identity: dict[str, Any] = Field(default_factory=dict)
    concept: dict[str, Any] = Field(default_factory=dict)
    logline: TrackedFact | None = None
    synopsis: dict[str, Any] = Field(default_factory=dict)
    characters: list[dict[str, Any]] = Field(default_factory=list)
    screenplay: dict[str, Any] = Field(default_factory=dict)
    director_vision: dict[str, Any] = Field(default_factory=dict)
    production_plan: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=dict)
    financing_plan: dict[str, Any] = Field(default_factory=dict)
    cultural_analysis: dict[str, Any] = Field(default_factory=dict)
    impact_analysis: dict[str, Any] = Field(default_factory=dict)

    validation_history: list[ValidationVerdict] = Field(default_factory=list)
    modifications_history: list[ModificationTrace] = Field(default_factory=list)
    unresolved_issues: list[Finding] = Field(default_factory=list)
    final_documents: list[str] = Field(default_factory=list)

    def blocking_issues(self) -> list[Finding]:
        return [issue for issue in self.unresolved_issues if issue.is_blocking()]

    def record(self, trace: ModificationTrace) -> None:
        self.modifications_history.append(trace)


class AgentInput(BaseModel):
    """Ce qu'un agent recoit. Jamais moins : il ne travaille pas en silo."""

    project_state: ProjectState
    previous_agent_outputs: list[AgentOutput] = Field(default_factory=list)
    current_agent_role: AgentRole
    funding_requirements: dict[str, Any] = Field(default_factory=dict)
    project_context: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    """Ce qu'un agent rend.

    `next_agent_instructions` n'est pas une politesse : c'est par lui qu'un
    agent transmet ce qu'il a compris et qui ne tient pas dans l'etat, par
    exemple un arbitrage qu'il a laisse ouvert a dessein.
    """

    agent: AgentRole
    version: str
    analysis: str
    decisions: list[DecisionRecord] = Field(default_factory=list)
    modifications: ChangeSet = Field(default_factory=ChangeSet)
    rationale: str = ""
    updated_state: ProjectState | None = None
    next_agent_instructions: str = ""
    findings: list[Finding] = Field(default_factory=list)
    verdict: ValidationVerdict | None = None


# `AgentInput` cite `AgentOutput` avant sa definition : Pydantic a besoin d'un
# passage explicite une fois les deux connus.
AgentInput.model_rebuild()
