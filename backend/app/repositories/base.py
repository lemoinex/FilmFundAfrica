"""Repository generique : isole les requetes SQL de la couche service."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, entity_id: str) -> ModelT | None:
        return self.db.get(self.model, entity_id)

    def list_all(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def count(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(self.model)) or 0)

    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        self.db.delete(entity)
        self.db.flush()

    @staticmethod
    def apply_updates(entity: ModelT, updates: dict[str, Any]) -> ModelT:
        for field, value in updates.items():
            if value is not None or field in getattr(entity, "__nullable_fields__", ()):
                setattr(entity, field, value)
        return entity
