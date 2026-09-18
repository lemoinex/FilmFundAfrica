"""Schemas projets, personnages et scoring."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ProjectStatus, ProjectType
from app.schemas.common import ORMModel

#: Durees cibles proposees par l'interface (minutes).
SUGGESTED_DURATIONS = [10, 26, 30, 52, 90, 100, 110, 120]


class CharacterBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    role: str | None = Field(default=None, max_length=120)
    age: str | None = Field(default=None, max_length=60)
    description: str | None = None
    arc: str | None = None
    sort_order: int = 0


class CharacterCreate(CharacterBase):
    pass


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    role: str | None = Field(default=None, max_length=120)
    age: str | None = Field(default=None, max_length=60)
    description: str | None = None
    arc: str | None = None
    sort_order: int | None = None


class CharacterRead(ORMModel, CharacterBase):
    id: str
    project_id: str


class ProjectBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    project_type: ProjectType
    genre: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    language: str = Field(default="Français", max_length=60)
    duration: int | None = Field(default=None, ge=1, le=1200)
    logline: str | None = None
    short_synopsis: str | None = None
    long_synopsis: str | None = None
    theme: str | None = None
    target_audience: str | None = None
    concept: str | None = None
    stakes: str | None = None
    director_vision: str | None = None
    objectives: str | None = None
    status: ProjectStatus = ProjectStatus.IDEA


class ProjectCreate(ProjectBase):
    characters: list[CharacterCreate] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    project_type: ProjectType | None = None
    genre: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, max_length=60)
    duration: int | None = Field(default=None, ge=1, le=1200)
    logline: str | None = None
    short_synopsis: str | None = None
    long_synopsis: str | None = None
    theme: str | None = None
    target_audience: str | None = None
    concept: str | None = None
    stakes: str | None = None
    director_vision: str | None = None
    objectives: str | None = None
    status: ProjectStatus | None = None


class ProjectSummary(ORMModel):
    """Carte projet du tableau de bord."""

    id: str
    title: str
    project_type: ProjectType
    genre: str | None = None
    status: ProjectStatus
    readiness_score: int | None = None
    updated_at: datetime
    document_count: int = 0


class ProjectRead(ORMModel, ProjectBase):
    id: str
    user_id: str
    readiness_score: int | None = None
    created_at: datetime
    updated_at: datetime
    characters: list[CharacterRead] = Field(default_factory=list)


class ScoreCriterion(BaseModel):
    key: str
    label: str
    weight: int
    earned: int
    detail: str


class ReadinessScore(BaseModel):
    """Project Readiness Score : indicateur interne d'avancement du dossier."""

    total: int = Field(ge=0, le=100)
    criteria: list[ScoreCriterion]
    improvements: list[str]
    computed_at: datetime
