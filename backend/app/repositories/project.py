"""Acces aux projets et personnages."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.project import Character, Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def list_for_user(
        self, user_id: str, *, limit: int = 50, offset: int = 0, search: str | None = None
    ) -> list[Project]:
        stmt = (
            select(Project)
            .options(selectinload(Project.characters))
            .where(Project.user_id == user_id)
        )
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(Project.title.ilike(pattern))
        stmt = stmt.order_by(Project.updated_at.desc()).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def count_for_user(self, user_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(Project).where(Project.user_id == user_id)
            )
            or 0
        )

    def get_for_user(self, project_id: str, user_id: str) -> Project | None:
        return self.db.scalar(
            select(Project)
            .options(selectinload(Project.characters))
            .where(Project.id == project_id, Project.user_id == user_id)
        )

    def document_counts(self, project_ids: list[str]) -> dict[str, int]:
        if not project_ids:
            return {}
        rows = self.db.execute(
            select(Document.project_id, func.count(Document.id))
            .where(Document.project_id.in_(project_ids))
            .group_by(Document.project_id)
        )
        return dict(rows.all())


class CharacterRepository(BaseRepository[Character]):
    model = Character

    def list_for_project(self, project_id: str) -> list[Character]:
        stmt = (
            select(Character)
            .where(Character.project_id == project_id)
            .order_by(Character.sort_order, Character.created_at)
        )
        return list(self.db.scalars(stmt))
