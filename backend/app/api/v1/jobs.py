"""Routes de suivi des taches de generation IA."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession, OwnedProject
from app.schemas.job import GenerationJobRead
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["AI Writer"])
project_router = APIRouter(prefix="/projects/{project_id}/jobs", tags=["AI Writer"])


@router.get("/{job_id}", response_model=GenerationJobRead, summary="État d'une génération")
def get_job(job_id: str, db: DbSession, current_user: CurrentUser) -> GenerationJobRead:
    """Interrogée par le frontend jusqu'à un état terminal.

    Une tâche appartenant à un autre compte renvoie 404, comme les projets et
    les documents : la réponse ne révèle pas son existence.
    """
    job = JobService(db).get_owned_job(job_id, current_user)
    return GenerationJobRead.model_validate(job)


@project_router.get(
    "",
    response_model=list[GenerationJobRead],
    summary="Générations récentes d'un projet",
)
def list_project_jobs(project: OwnedProject, db: DbSession) -> list[GenerationJobRead]:
    """Permet de retrouver une génération en cours après un rechargement de page."""
    return [
        GenerationJobRead.model_validate(job)
        for job in JobService(db).list_for_project(project)
    ]
