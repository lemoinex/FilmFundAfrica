"""Schemas de la veille automatisee."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import CandidateStatus, FundingCategory
from app.schemas.common import ORMModel


class CandidateRead(ORMModel):
    id: str
    name: str
    source_url: str
    source_name: str
    status: CandidateStatus
    #: Champs extraits par la veille, tels quels.
    payload: dict[str, Any] = Field(default_factory=dict)
    review_note: str | None = None
    reviewed_at: datetime | None = None
    opportunity_id: str | None = None
    last_seen_at: datetime | None = None
    created_at: datetime


class CandidateApproval(BaseModel):
    """Corrections apportées avant publication.

    Tout champ renseigné ici l'emporte sur ce qu'a extrait la veille : c'est la
    personne qui a lu la source. `organization` est obligatoire au bout du
    compte — un dispositif sans organisme n'est pas exploitable.
    """

    name: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    description: str | None = None
    country: str | None = Field(default=None, max_length=120)
    eligible_countries: str | None = None
    project_types: str | None = None
    genres: str | None = None
    languages: str | None = None
    category: FundingCategory | None = None
    minimum_budget: float | None = Field(default=None, ge=0)
    maximum_budget: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    deadline: date | None = None
    opening_date: date | None = None
    application_url: str | None = Field(default=None, max_length=512)
    website: str | None = Field(default=None, max_length=512)
    requirements: str | None = None


class CandidateRejection(BaseModel):
    note: str | None = Field(default=None, max_length=500)
