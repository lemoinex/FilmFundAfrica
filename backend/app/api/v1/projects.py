"""Routes projets, personnages et score de maturité."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request, status

from app.core.deps import CurrentUser, DbSession, OwnedProject, Translator
from app.core.i18n import request_locale
from app.schemas.common import Message
from app.schemas.project import (
    CharacterCreate,
    CharacterRead,
    CharacterUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectSummary,
    ProjectUpdate,
    ReadinessScore,
)
from app.services.project_service import ProjectService
from app.services.scoring_service import ScoringService

router = APIRouter(prefix="/projects", tags=["Projets"])


@router.get("", response_model=list[ProjectSummary], summary="Lister mes projets")
def list_projects(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=120),
) -> list[ProjectSummary]:
    return ProjectService(db).list_summaries(
        current_user, limit=limit, offset=offset, search=search
    )


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un projet",
)
def create_project(payload: ProjectCreate, db: DbSession, current_user: CurrentUser) -> ProjectRead:
    project = ProjectService(db).create(current_user, payload)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead, summary="Détail d'un projet")
def get_project(project: OwnedProject) -> ProjectRead:
    return ProjectRead.model_validate(project)


@router.put("/{project_id}", response_model=ProjectRead, summary="Modifier un projet")
def update_project(payload: ProjectUpdate, project: OwnedProject, db: DbSession) -> ProjectRead:
    updated = ProjectService(db).update(project, payload)
    return ProjectRead.model_validate(updated)


@router.delete("/{project_id}", response_model=Message, summary="Supprimer un projet")
def delete_project(project: OwnedProject, db: DbSession, t: Translator) -> Message:
    ProjectService(db).delete(project)
    return Message(detail=t("project.deleted"))


# ---------------------------------------------------------------------------
# Score de maturité
# ---------------------------------------------------------------------------
@router.get(
    "/{project_id}/score",
    response_model=ReadinessScore,
    summary="Calculer le Project Readiness Score",
)
def project_score(request: Request, project: OwnedProject, db: DbSession) -> ReadinessScore:
    return ScoringService(db, locale=request_locale(request)).compute(project)


# ---------------------------------------------------------------------------
# Personnages
# ---------------------------------------------------------------------------
@router.get(
    "/{project_id}/characters",
    response_model=list[CharacterRead],
    summary="Lister les personnages",
)
def list_characters(project: OwnedProject) -> list[CharacterRead]:
    return [CharacterRead.model_validate(character) for character in project.characters]


@router.post(
    "/{project_id}/characters",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un personnage",
)
def create_character(
    payload: CharacterCreate, project: OwnedProject, db: DbSession
) -> CharacterRead:
    character = ProjectService(db).add_character(project, payload)
    return CharacterRead.model_validate(character)


@router.put(
    "/{project_id}/characters/{character_id}",
    response_model=CharacterRead,
    summary="Modifier un personnage",
)
def update_character(
    character_id: str, payload: CharacterUpdate, project: OwnedProject, db: DbSession
) -> CharacterRead:
    character = ProjectService(db).update_character(project, character_id, payload)
    return CharacterRead.model_validate(character)


@router.delete(
    "/{project_id}/characters/{character_id}",
    response_model=Message,
    summary="Supprimer un personnage",
)
def delete_character(
    character_id: str, project: OwnedProject, db: DbSession, t: Translator
) -> Message:
    ProjectService(db).delete_character(project, character_id)
    return Message(detail=t("character.deleted"))
