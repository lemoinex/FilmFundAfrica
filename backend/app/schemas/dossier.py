"""Contrats d'entree/sortie du dossier construit par la chaine d'agents."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import AgentRole, Severity, ValidationVerdict
from app.schemas.common import ORMModel


class FindingRead(ORMModel):
    id: str
    severity: Severity
    element: str
    description: str
    #: Agent capable de corriger. Sans lui, le constat n'a pas de destinataire.
    owner: AgentRole | None
    suggested_correction: str | None
    #: Renseigne quand le constat a ete leve : un constat resolu est date, pas
    #: efface, pour qu'on sache qu'il a existe.
    resolved_at: datetime | None
    created_at: datetime


class ModificationRead(ORMModel):
    id: str
    agent: AgentRole
    element: str
    reason: str
    impact: str
    validation_status: ValidationVerdict | None
    created_at: datetime


class AgentStepRead(ORMModel):
    id: str
    sequence: int
    agent: AgentRole
    agent_version: str
    analysis: str
    rationale: str
    next_agent_instructions: str
    verdict: ValidationVerdict | None
    changeset: dict[str, Any]
    created_at: datetime


class AgentRunRead(ORMModel):
    id: str
    verdict: ValidationVerdict | None
    rounds: int
    exhausted: bool
    stalled: bool
    created_at: datetime
    finished_at: datetime | None


class AgentRunDetail(AgentRunRead):
    steps: list[AgentStepRead] = Field(default_factory=list)


class DossierRead(ORMModel):
    """Le dossier tel qu'il est, et ce qui reste a regler dessus."""

    id: str
    project_id: str
    project_identity: dict[str, Any]
    logline: dict[str, Any] | None
    concept: dict[str, Any]
    synopsis: dict[str, Any]
    characters: list[dict[str, Any]]
    screenplay: dict[str, Any]
    director_vision: dict[str, Any]
    production_plan: dict[str, Any]
    budget: dict[str, Any]
    financing_plan: dict[str, Any]
    cultural_analysis: dict[str, Any]
    impact_analysis: dict[str, Any]
    final_documents: list[str]
    updated_at: datetime


class DossierStatus(BaseModel):
    """Ce qu'il faut savoir avant de se demander si le dossier peut partir."""

    project_id: str
    #: Verdict du dernier passage, ou `null` si la chaine n'a jamais tourne.
    verdict: ValidationVerdict | None = None
    #: **Seul** critere d'export. Ni le nombre de passages ni l'absence
    #: d'erreur technique ne valent validation.
    exportable: bool = False
    open_findings: int = 0
    blocking_findings: int = 0
    last_run_at: datetime | None = None
    runs: int = 0


class AgentChainResult(BaseModel):
    """Resultat d'un passage de la chaine, porte par la tache qui l'a execute.

    Distinct d'une generation de document : une chaine ne produit pas un
    document mais un dossier, et son verdict n'est pas un statut technique.
    """

    run_id: str
    verdict: ValidationVerdict | None = None
    #: Ce que le verdict autorise. Une tache reussie peut tres bien avoir
    #: conclu au refus : les deux ne disent pas la meme chose.
    exportable: bool = False
    rounds: int = 0
    stalled: bool = False
    exhausted: bool = False
    #: Vrai quand l'utilisateur a arrete le passage en cours de route. Le
    #: dossier partiel est conserve, mais jamais exportable : la chaine de
    #: controle n'est pas allee a son terme.
    cancelled: bool = False
    steps: int = 0
    open_findings: int = 0
