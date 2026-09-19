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


@router.post(
    "/{job_id}/cancel",
    response_model=GenerationJobRead,
    summary="Arrêter une génération",
)
def cancel_job(job_id: str, db: DbSession, current_user: CurrentUser) -> GenerationJobRead:
    """Arrête une génération, ou demande son arrêt si elle a déjà commencé.

    En file d'attente, l'arrêt est immédiat et les crédits reviennent en
    entier. En cours, la tâche s'interrompt **entre deux passes** : c'est la
    seule frontière où l'état est cohérent, et un appel déjà parti est de
    toute façon déjà facturé. Le travail produit jusque-là est conservé, et
    seules les passes qui n'ont pas tourné sont rendues.

    Une génération en un seul appel n'a pas de frontière avant sa fin : la
    demande est enregistrée, mais elle ira à son terme.
    """
    service = JobService(db)
    job = service.get_owned_job(job_id, current_user)
    return GenerationJobRead.model_validate(service.request_cancel(job))


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
