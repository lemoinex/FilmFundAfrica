"""Schemas des taches de generation IA."""

from __future__ import annotations

from datetime import datetime

from app.models.enums import DocumentType, JobKind, JobStatus
from app.schemas.common import ORMModel
from app.schemas.document import GenerationResult


class GenerationJobRead(ORMModel):
    """Etat d'une generation demandee.

    Le frontend interroge cette ressource jusqu'a un etat terminal :
    `SUCCEEDED` porte alors le `result` complet, `FAILED` la raison de l'echec.
    `completed_passes` / `total_passes` donnent l'avancement d'un scenario long.
    """

    id: str
    project_id: str
    document_id: str | None = None
    kind: JobKind
    document_type: DocumentType
    status: JobStatus
    total_passes: int
    completed_passes: int
    credits_reserved: int
    error_code: str | None = None
    error_message: str | None = None
    result: GenerationResult | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
