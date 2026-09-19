"""Schemas des taches de generation IA."""

from __future__ import annotations

from datetime import datetime

from app.models.enums import DocumentType, JobKind, JobStatus
from app.schemas.common import ORMModel
from app.schemas.document import GenerationResult
from app.schemas.dossier import AgentChainResult


class GenerationJobRead(ORMModel):
    """Etat d'une generation demandee.

    Le frontend interroge cette ressource jusqu'a un etat terminal :
    `SUCCEEDED` porte alors le `result` complet, `FAILED` la raison de l'echec.
    `CANCELLED` porte le travail conserve jusqu'a l'arret. `completed_passes`
    / `total_passes` donnent l'avancement d'un scenario long.
    """

    id: str
    project_id: str
    document_id: str | None = None
    kind: JobKind
    #: Nul pour un passage de la chaine d'agents, qui ne vise aucun
    #: document en particulier.
    document_type: DocumentType | None = None
    status: JobStatus
    total_passes: int
    completed_passes: int
    credits_reserved: int
    error_code: str | None = None
    error_message: str | None = None
    #: La forme depend de `kind` : un document genere, ou le bilan d'un
    #: passage de la chaine.
    result: GenerationResult | AgentChainResult | None = None
    #: Renseigne des qu'un arret a ete demande, meme si la tache n'est pas
    #: encore arretee : elle ne s'interrompt qu'entre deux passes.
    cancel_requested_at: datetime | None = None
    created_at: datetime
    started_at: datetime | None = None
    heartbeat_at: datetime | None = None
    finished_at: datetime | None = None
