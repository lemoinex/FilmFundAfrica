"""Logique metier des projets et des personnages."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.project import Character, Project
from app.models.user import User
from app.repositories.project import CharacterRepository, ProjectRepository
from app.schemas.project import (
    CharacterCreate,
    CharacterUpdate,
    ProjectCreate,
    ProjectSummary,
    ProjectUpdate,
)
from app.services.credit_service import CreditService
from app.services.scoring_service import ScoringService

#: Champs du projet pouvant etre explicitement remis a vide par l'utilisateur.
NULLABLE_PROJECT_FIELDS = {
    "genre",
    "country",
    "duration",
    "logline",
    "short_synopsis",
    "long_synopsis",
    "theme",
    "target_audience",
    "concept",
    "stakes",
    "director_vision",
    "objectives",
}


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.characters = CharacterRepository(db)
        self.credits = CreditService(db)
        self.scoring = ScoringService(db)

    # ------------------------------------------------------------------
    def create(self, user: User, payload: ProjectCreate) -> Project:
        self.credits.check_project_quota(user, self.projects.count_for_user(user.id))

        data = payload.model_dump(exclude={"characters"})
        project = Project(user_id=user.id, **data)
        for index, character in enumerate(payload.characters):
            project.characters.append(
                Character(**character.model_dump(exclude={"sort_order"}), sort_order=index)
            )
        self.projects.add(project)
        self.db.commit()
        self.db.refresh(project)
        self.scoring.compute(project)
        return project

    # ------------------------------------------------------------------
    def update(self, project: Project, payload: ProjectUpdate) -> Project:
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            if value is None and field not in NULLABLE_PROJECT_FIELDS:
                continue
            setattr(project, field, value)
        self.db.commit()
        self.db.refresh(project)
        self.scoring.compute(project)
        return project

    # ------------------------------------------------------------------
    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.commit()

    # ------------------------------------------------------------------
    def list_summaries(
        self, user: User, *, limit: int = 50, offset: int = 0, search: str | None = None
    ) -> list[ProjectSummary]:
        projects = self.projects.list_for_user(
            user.id, limit=limit, offset=offset, search=search
        )
        counts = self.projects.document_counts([project.id for project in projects])
        summaries: list[ProjectSummary] = []
        for project in projects:
            summary = ProjectSummary.model_validate(project)
            summaries.append(
                summary.model_copy(update={"document_count": counts.get(project.id, 0)})
            )
        return summaries

    # ------------------------------------------------------------------
    def add_character(self, project: Project, payload: CharacterCreate) -> Character:
        character = Character(project_id=project.id, **payload.model_dump())
        if not payload.sort_order:
            character.sort_order = len(project.characters)
        self.characters.add(character)
        self.db.commit()
        self.db.refresh(character)
        self.scoring.compute(project)
        return character

    def update_character(
        self, project: Project, character_id: str, payload: CharacterUpdate
    ) -> Character:
        character = self.characters.get(character_id)
        if character is None or character.project_id != project.id:
            raise NotFoundError("character.notFound")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(character, field, value)
        self.db.commit()
        self.db.refresh(character)
        self.scoring.compute(project)
        return character

    def delete_character(self, project: Project, character_id: str) -> None:
        character = self.characters.get(character_id)
        if character is None or character.project_id != project.id:
            raise NotFoundError("character.notFound")
        self.db.delete(character)
        self.db.commit()
        self.scoring.compute(project)
