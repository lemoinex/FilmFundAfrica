"""Routes du dossier construit par la chaine d'agents.

Le lancement est une **tache**, pas une requete : un passage enchaine huit
appels au fournisseur, davantage avec les reprises. Le tenir dans la requete
HTTP la ferait expirer, et une coupure perdrait tout le travail.

La lecture, elle, est immediate : le dossier vit en base entre deux passages.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, OwnedProject
from app.core.rate_limit import rate_limit_ai
from app.models.agents import AgentRun, DossierFinding, DossierModification
from app.models.enums import Severity
from app.schemas.dossier import (
    AgentRunDetail,
    AgentRunRead,
    DossierRead,
    DossierStatus,
    FindingRead,
    ModificationRead,
)
from app.schemas.job import GenerationJobRead
from app.services.dossier_service import DossierService
from app.services.job_service import JobService

router = APIRouter(prefix="/projects/{project_id}/dossier", tags=["Dossier"])


@router.post(
    "/run",
    response_model=GenerationJobRead,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_ai)],
    summary="Lancer un passage de la chaîne d'agents",
)
def run_chain(
    project: OwnedProject, db: DbSession, current_user: CurrentUser
) -> GenerationJobRead:
    """Accepte la demande et renvoie la tâche qui l'exécute.

    Les crédits sont réservés pour **chaque agent** : un passage en coûte huit.
    Le frontend suit l'avancement sur `GET /jobs/{id}`, comme pour une
    génération de document.

    Sans worker disponible, le passage est exécuté immédiatement — la réponse
    est alors déjà terminée. Seul le temps d'attente change.
    """
    job = JobService(db).enqueue_agent_chain(current_user, project)
    return GenerationJobRead.model_validate(job)


@router.get("", response_model=DossierRead, summary="Le dossier du projet")
def read_dossier(project: OwnedProject, db: DbSession) -> DossierRead:
    """Le dossier tel que le dernier passage l'a laissé.

    Un projet dont la chaîne n'a jamais tourné a un dossier vide, pas une
    erreur : le dossier existe dès le projet, il est simplement à remplir.
    """
    return DossierRead.model_validate(DossierService(db).get_or_create(project.id))


@router.get("/status", response_model=DossierStatus, summary="Le dossier peut-il partir ?")
def read_status(project: OwnedProject, db: DbSession) -> DossierStatus:
    """Résume ce qui décide de l'export, sans avoir à lire tout le dossier."""
    dossier = DossierService(db).get_or_create(project.id)
    last = db.scalar(
        select(AgentRun)
        .where(AgentRun.dossier_id == dossier.id)
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    open_findings = list(
        db.scalars(
            select(DossierFinding).where(
                DossierFinding.dossier_id == dossier.id,
                DossierFinding.resolved_at.is_(None),
            )
        )
    )
    runs = len(dossier.runs)

    from app.agents import is_exportable

    return DossierStatus(
        project_id=project.id,
        verdict=last.verdict if last else None,
        # Un dossier n'est exportable que sur verdict favorable. L'absence
        # d'erreur technique n'a jamais valu validation.
        exportable=bool(last and last.verdict and is_exportable(last.verdict)),
        open_findings=len(open_findings),
        blocking_findings=sum(1 for f in open_findings if f.severity is Severity.CRITICAL),
        last_run_at=last.finished_at if last else None,
        runs=runs,
    )


@router.get("/findings", response_model=list[FindingRead], summary="Constats sur le dossier")
def list_findings(
    project: OwnedProject, db: DbSession, include_resolved: bool = False
) -> list[FindingRead]:
    """Constats ouverts, les plus graves d'abord.

    `include_resolved` montre aussi ceux qui ont été levés : ils sont datés,
    pas effacés, pour qu'on puisse savoir qu'un blocage a existé.
    """
    dossier = DossierService(db).get_or_create(project.id)
    stmt = select(DossierFinding).where(DossierFinding.dossier_id == dossier.id)
    if not include_resolved:
        stmt = stmt.where(DossierFinding.resolved_at.is_(None))

    order = {Severity.CRITICAL: 0, Severity.MAJOR: 1, Severity.MINOR: 2, Severity.PASS: 3}
    rows = sorted(db.scalars(stmt), key=lambda row: (order[row.severity], row.created_at))
    return [FindingRead.model_validate(row) for row in rows]


@router.get(
    "/modifications",
    response_model=list[ModificationRead],
    summary="Qui a modifié quoi, et pourquoi",
)
def list_modifications(
    project: OwnedProject, db: DbSession, limit: int = 200
) -> list[ModificationRead]:
    dossier = DossierService(db).get_or_create(project.id)
    rows = db.scalars(
        select(DossierModification)
        .where(DossierModification.dossier_id == dossier.id)
        .order_by(DossierModification.created_at.desc())
        .limit(min(limit, 500))
    )
    return [ModificationRead.model_validate(row) for row in rows]


@router.get("/runs", response_model=list[AgentRunRead], summary="Passages de la chaîne")
def list_runs(project: OwnedProject, db: DbSession, limit: int = 20) -> list[AgentRunRead]:
    dossier = DossierService(db).get_or_create(project.id)
    rows = db.scalars(
        select(AgentRun)
        .where(AgentRun.dossier_id == dossier.id)
        .order_by(AgentRun.created_at.desc())
        .limit(min(limit, 100))
    )
    return [AgentRunRead.model_validate(row) for row in rows]


@router.get(
    "/runs/{run_id}",
    response_model=AgentRunDetail,
    summary="Le détail d'un passage, agent par agent",
)
def read_run(run_id: str, project: OwnedProject, db: DbSession) -> AgentRunDetail:
    """Ce que chaque agent a dit, dans l'ordre où il l'a dit."""
    from app.core.errors import NotFoundError

    dossier = DossierService(db).get_or_create(project.id)
    run = db.scalar(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.dossier_id == dossier.id)
    )
    if run is None:
        # 404 et non 403 : dire « interdit » révélerait que ce passage existe
        # chez quelqu'un d'autre.
        raise NotFoundError("dossier.runNotFound", code="agent_run_not_found")
    return AgentRunDetail.model_validate(run)
