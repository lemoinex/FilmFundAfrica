"""Routes appelees par l'automatisation (n8n ou tout ordonnanceur).

Authentifiees par une cle partagee (`N8N_API_KEY`) plutot que par un compte :
un robot n'a pas de session, et lui creer un compte administrateur reviendrait
a laisser trainer des identifiants humains dans un workflow.

Sans cle configuree, ces routes sont fermees. Une automatisation ouverte par
defaut serait une porte d'entree sur la base de financements.
"""

from __future__ import annotations

import logging
import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.deps import DbSession, Translator
from app.core.errors import AppError
from app.core.rate_limit import rate_limit_auth
from app.schemas.common import Message
from app.services.ingestion_service import IngestionService
from app.workers.tasks import SCHEDULED_TASKS

logger = logging.getLogger("filmfund.automation")

router = APIRouter(prefix="/automation", tags=["Automatisation"])


def require_automation_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Verifie la cle partagee, en temps constant.

    `secrets.compare_digest` et non `==` : une comparaison qui s'arrete au
    premier caractere different laisse deviner la cle, octet par octet.
    """
    if not settings.n8n_api_key:
        raise AppError(
            "automation.disabled",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="automation_disabled",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.n8n_api_key):
        logger.warning(
            "appel d'automatisation rejeté : clé invalide",
            extra={"event": "automation_key_rejected"},
        )
        raise AppError(
            "automation.invalidKey",
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_api_key",
        )


AutomationKey = Depends(require_automation_key)


class CandidateIn(BaseModel):
    """Un dispositif reperé par la veille, avant toute relecture humaine."""

    name: str = Field(min_length=1, max_length=255)
    #: Obligatoire : un dispositif sans source vérifiable ne vaut rien.
    source_url: str = Field(min_length=5, max_length=512)
    source_name: str = Field(min_length=1, max_length=255)
    #: Champs extraits. Un champ absent de la source reste absent : la veille
    #: ne comble aucun trou.
    payload: dict[str, Any] = Field(default_factory=dict)


class IngestReport(BaseModel):
    received: int
    created: int
    duplicates: int
    rejected: int
    details: list[str] = Field(default_factory=list)


@router.post(
    "/opportunities",
    response_model=IngestReport,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[AutomationKey, Depends(rate_limit_auth)],
    summary="Déposer des dispositifs repérés par la veille",
)
def ingest_opportunities(candidates: list[CandidateIn], db: DbSession) -> IngestReport:
    """Dépose des candidats **en file de validation**, jamais dans la base vivante.

    Une opportunité proposée à un auteur engage son dossier de financement :
    elle ne peut pas venir d'une classification automatique non relue.
    """
    service = IngestionService(db)
    created = duplicates = rejected = 0
    details: list[str] = []

    for candidate in candidates:
        try:
            result = service.submit(
                name=candidate.name,
                source_url=candidate.source_url,
                source_name=candidate.source_name,
                payload=candidate.payload,
            )
        except AppError as exc:
            rejected += 1
            details.append(f"{candidate.name} : {exc.detail}")
            continue
        if result.created:
            created += 1
        else:
            duplicates += 1

    logger.info(
        "veille : %s candidat(s) reçu(s), %s nouveau(x)",
        len(candidates),
        created,
        extra={"event": "candidates_ingested"},
    )
    return IngestReport(
        received=len(candidates),
        created=created,
        duplicates=duplicates,
        rejected=rejected,
        details=details,
    )


@router.get(
    "/tasks",
    response_model=list[str],
    dependencies=[AutomationKey],
    summary="Tâches planifiées disponibles",
)
def list_tasks() -> list[str]:
    return sorted(SCHEDULED_TASKS)


@router.post(
    "/tasks/{task_name}",
    response_model=Message,
    dependencies=[AutomationKey],
    summary="Déclencher une tâche planifiée",
)
def run_task(task_name: str, t: Translator) -> Message:
    """Exécute une tâche de la liste fermée.

    Les tâches sont idempotentes : les rejouer ne produit pas de doublons.
    """
    task = SCHEDULED_TASKS.get(task_name)
    if task is None:
        raise AppError(
            "automation.unknownTask",
            params={"task": task_name, "available": ", ".join(sorted(SCHEDULED_TASKS))},
            status_code=status.HTTP_404_NOT_FOUND,
            code="unknown_task",
        )
    count = task()
    logger.info("tâche planifiée exécutée : %s", task_name, extra={"event": "task_run"})
    return Message(detail=t("automation.taskRun", task=task_name, count=count))
